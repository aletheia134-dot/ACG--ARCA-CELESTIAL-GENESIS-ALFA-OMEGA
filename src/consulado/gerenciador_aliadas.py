from __future__ import annotations


import importlib
import json
import logging
import queue
import time
import threading
from pathlib import Path
from threading import RLock
from typing import Dict, Optional, Tuple, Any

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class GerenciadorAliadas:
    """
    Orquestra a comunicação com IAs externas (Aliadas).
    Carrega adaptadores dinamicamente e gerencia disponibilidade.Responsabilidades:
    - Carregar adaptadores de aliadas dinamicamente
    - Normalizar interface de consulta
    - Gerenciar ativao/desativao em runtime
    - Notificar UI de eventos
    - Thread-safe em todas operações
    """

    def __init__(
        self,
        config_path: str = "config/configuracoes_aliadas.json",
        ui_queue: Optional[queue.Queue] = None
    ):
        """
        Inicializa o gerenciador de aliadas.Args:
            config_path: Caminho ao arquivo de configuração JSON
            ui_queue: Fila para comunicação com UI (opcional)
        """
        self.config_path = Path(config_path)
        self.aliadas_disponiveis: Dict[str, Dict[str, Any]] = {}
        self.adaptadores_carregados: Dict[str, object] = {}
        self._lock = RLock()
        self._ui_queue = ui_queue
        self._stats_consultas = {"total": 0, "sucesso": 0, "falha": 0}
        self._lock_stats = threading.Lock()

        # Carregar configurações e adaptadores
        self._carregar_config()
        self._importar_adaptadores()
        
        logger.info("[OK] GerenciadorAliadas inicializado com %d aliadas", len(self.aliadas_disponiveis))
        self._notificar_ui("GERENCIADOR_ALIADAS_INICIALIZADO", {
            "total_aliadas": len(self.aliadas_disponiveis),
            "ativas": sum(1 for c in self.aliadas_disponiveis.values() if c.get("ativa", False))
        })

    def _carregar_config(self) -> None:
        """Carrega configurações das Aliadas (inclui fallback de resilincia)."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                raw = cfg.get("aliadas", {}) if isinstance(cfg, dict) else {}
                
                # normalizar chaves para lowercase e manter config por aliada
                normalized: Dict[str, Dict[str, Any]] = {}
                for key, val in raw.items():
                    key_l = str(key).lower()
                    if isinstance(val, dict):
                        normalized[key_l] = dict(val)
                    else:
                        normalized[key_l] = {
                            "nome": str(key),
                            "modulo": None,
                            "classe": None,
                            "ativa": False
                        }
                self.aliadas_disponiveis = normalized
                logger.info(" Configurações de aliadas carregadas: %d", len(self.aliadas_disponiveis))
            else:
                # Fallback padrão (resilincia)
                self._usar_config_padrao()
        except Exception as e:
            logger.exception("[ERRO] Erro ao carregar config: %s", e)
            self._usar_config_padrao()

    def _usar_config_padrao(self) -> None:
        """Define configuração padrão de aliadas."""
        defaults = self._get_config_padrao()
        self.aliadas_disponiveis = defaults
        logger.warning("[AVISO] Usando configuração padrão de aliadas")

    def _get_config_padrao(self) -> Dict[str, Dict[str, Any]]:
        """Retorna config padrão externalizada com módulos e endpoints REAIS."""
        return {
            "qwen": {
                "nome": "Qwen",
                "ativa": True,
                "palavra_chave": "correntinha",
                # Arquivo aliada_qwen.py está na raiz do projeto
                "modulo": "aliada_qwen",
                "classe": "AliadaQwen",
                # Endpoint real da API Qwen (Alibaba DashScope)
                "endpoint": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
            },
            "gemini": {
                "nome": "Gemini",
                "ativa": True,
                "palavra_chave": "gemini",
                # Arquivo aliada_gemini.py está na raiz do projeto
                "modulo": "aliada_gemini",
                "classe": "AliadaGemini",
                # Endpoint real da API Gemini (Google)
                # NOTA: a chave API deve ser passada como parâmetro ?key=... na URL
                # O AliadaGemini cuida disso internamente
                "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
            },
            "deepseek": {
                "nome": "DeepSeek",
                "ativa": True,
                "palavra_chave": "deepseek",
                # Arquivo aliada_deepseek.py está na raiz do projeto
                "modulo": "aliada_deepseek",
                "classe": "AliadaDeepSeek",
                # Endpoint real da API DeepSeek (compatível com OpenAI)
                "endpoint": "https://api.deepseek.com/v1/chat/completions"
            },
            "qwen_cloud": {
                "nome": "Qwen Cloud",
                "ativa": False,
                "palavra_chave": "qwen_cloud",
                "modulo": "aliada_qwen_cloud",
                "classe": "AliadaQwenCloud",
                "endpoint": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
            }
        }

    def _importar_adaptadores(self) -> None:
        """Importa dinamicamente adaptadores para as aliadas marcadas como ativas."""
        logger.info(" Importando adaptadores de aliadas ativas...")
        
        for nome, cfg in list(self.aliadas_disponiveis.items()):
            nome_l = str(nome).lower()
            
            if not cfg.get("ativa", False):
                logger.debug("    %s est desativada", cfg.get("nome", nome_l))
                continue
            
            modulo_nome = cfg.get("modulo")
            classe_nome = cfg.get("classe")
            
            if not modulo_nome or not classe_nome:
                logger.warning("   [ERRO] %s: config incompleta (modulo/classe)", nome_l)
                continue
            
            try:
                module = importlib.import_module(modulo_nome)
                adapt_class = getattr(module, classe_nome)
            except ModuleNotFoundError as e:
                logger.warning("   [ERRO] %s: módulo no encontrado (%s)", nome_l, modulo_nome)
                continue
            except AttributeError as e:
                logger.warning("   [ERRO] %s: classe no encontrada (%s.%s)", nome_l, modulo_nome, classe_nome)
                continue
            except Exception as e:
                logger.exception("   [ERRO] %s: erro ação importar", nome_l)
                continue

            # Instanciar adaptador com tentativas de fallback
            inst = self._tentar_instanciar_adaptador(adapt_class, cfg, nome_l)
            
            if inst is not None:
                with self._lock:
                    self.adaptadores_carregados[nome_l] = inst
                logger.info("   [OK] %s carregada", cfg.get("nome", nome_l))
                self._notificar_ui("ALIADA_CARREGADA", {
                    "nome": cfg.get("nome", nome_l),
                    "chave": nome_l
                })

    def _tentar_instanciar_adaptador(self, adapt_class, cfg: Dict, nome_l: str) -> Optional[object]:
        """Tenta instanciar adaptador com fallbacks."""
        # Tentativa 1: sem argumentos
        try:
            return adapt_class()
        except TypeError:
            pass
        except Exception as e:
            logger.debug("   Fallback 1 falhou para %s: %s", nome_l, e)

        # Tentativa 2: com config dict
        try:
            return adapt_class(cfg)
        except Exception as e:
            logger.debug("   Fallback 2 falhou para %s: %s", nome_l, e)

        # Tentativa 3: com self (gerenciador)
        try:
            return adapt_class(self)
        except Exception as e:
            logger.debug("   Fallback 3 falhou para %s: %s", nome_l, e)

        # Todas falharam
        logger.exception("   [ERRO] Falha ao instanciar %s", nome_l)
        return None

    def _notificar_ui(self, tipo_evento: str, dados: Dict[str, Any]) -> None:
        """Envia notificao para UI via queue."""
        if not self._ui_queue:
            return
        
        try:
            self._ui_queue.put_nowait({
                "tipo_resp": f"ALIADAS_{tipo_evento}",
                "dados": dados,
                "timestamp": time.time()
            })
        except queue.Full:
            logger.debug("[AVISO] UI Queue cheia ação notificar %s", tipo_evento)
        except Exception as e:
            logger.debug("[AVISO] Erro ao notificar UI: %s", e)

    def consultar(
        self,
        aliada: str,
        comando: str,
        contexto: Optional[Dict] = None
    ) -> Tuple[bool, Optional[str], str]:
        """
        Consulta uma Aliada especfica.Args:
            aliada: Nome da aliada (normalizado para lowercase)
            comando: Comando/pergunta para a aliada
            contexto: Dict com contexto adicional (opcional)

        Retorna: (sucesso, resposta|None, mensagem_status)
        """
        aliada_lower = str(aliada).lower()
        
        # Registrar estatstica
        with self._lock_stats:
            self._stats_consultas["total"] += 1
        
        # Validar se aliada existe
        if aliada_lower not in self.aliadas_disponiveis:
            msg = f"Aliada '{aliada}' no reconhecida"
            logger.warning("[ERRO] %s", msg)
            self._notificar_ui("CONSULTA_FALHA", {
                "aliada": aliada,
                "motivo": msg
            })
            return False, None, msg

        cfg = self.aliadas_disponiveis[aliada_lower]
        
        # Validar se est ativa
        if not cfg.get("ativa", False):
            msg = f"Aliada '{cfg.get('nome', aliada)}' est desativada"
            logger.warning("[ERRO] %s", msg)
            self._notificar_ui("CONSULTA_FALHA", {
                "aliada": cfg.get("nome", aliada),
                "motivo": "Desativada"
            })
            return False, None, msg

        # Obter adaptador
        with self._lock:
            adaptador = self.adaptadores_carregados.get(aliada_lower)

        if adaptador is None:
            msg = f"Adaptador para '{cfg.get('nome', aliada_lower)}' no disponível"
            logger.warning("[ERRO] %s", msg)
            self._notificar_ui("CONSULTA_FALHA", {
                "aliada": cfg.get("nome", aliada_lower),
                "motivo": "Adaptador no disponível"
            })
            return False, None, msg

        # Executar consulta
        try:
            palavra_chave = str(cfg.get("palavra_chave", "") or "")
            comando_final = comando
            
            # Adicionar palavra-chave se necessário
            if palavra_chave and palavra_chave.lower() not in comando.lower():
                comando_final = f"{palavra_chave} {comando}"
                logger.debug("    Palavra-chave '%s' adicionada", palavra_chave)

            # Encontrar método compatvel
            func = None
            if hasattr(adaptador, "processar"):
                func = getattr(adaptador, "processar")
            elif hasattr(adaptador, "run"):
                func = getattr(adaptador, "run")
            elif hasattr(adaptador, "__call__"):
                func = adaptador
            else:
                msg = "Adaptador no implementa interface conhecida (processar/run/__call__)"
                logger.warning("[ERRO] %s", msg)
                with self._lock_stats:
                    self._stats_consultas["falha"] += 1
                self._notificar_ui("CONSULTA_FALHA", {
                    "aliada": cfg.get("nome", aliada_lower),
                    "motivo": "Interface invlida"
                })
                return False, None, msg

            # Chamar função defensivamente
            result = (
                func(comando_final, contexto)
                if contexto is not None
                else func(comando_final)
            )
            
            # Normalizar retorno
            sucesso, resposta, status = self._normalizar_resposta(result)

            if sucesso:
                logger.info("[OK] %s respondeu com sucesso", cfg.get("nome", aliada_lower))
                with self._lock_stats:
                    self._stats_consultas["sucesso"] += 1
                self._notificar_ui("CONSULTA_SUCESSO", {
                    "aliada": cfg.get("nome", aliada_lower),
                    "comando": comando,
                    "resposta_length": len(str(resposta)) if resposta else 0
                })
            else:
                logger.warning("[AVISO] %s respondeu com falha: %s", cfg.get("nome", aliada_lower), status)
                with self._lock_stats:
                    self._stats_consultas["falha"] += 1
                self._notificar_ui("CONSULTA_FALHA", {
                    "aliada": cfg.get("nome", aliada_lower),
                    "motivo": status
                })

            return bool(sucesso), (resposta if resposta is not None else None), str(status)

        except Exception as e:
            logger.exception("[ERRO] Erro ao consultar %s", aliada_lower)
            with self._lock_stats:
                self._stats_consultas["falha"] += 1
            msg = f"Erro na consulta: {e}"
            self._notificar_ui("CONSULTA_ERRO", {
                "aliada": aliada_lower,
                "erro": str(e)
            })
            return False, None, msg

    def _normalizar_resposta(self, result: Any) -> Tuple[bool, Optional[str], str]:
        """Normaliza resposta de adaptadores com formatos variados."""
        try:
            if isinstance(result, tuple):
                if len(result) == 3:
                    sucesso, resposta, status = result
                elif len(result) == 2:
                    sucesso, resposta = result
                    status = "ok" if sucesso else "falha"
                else:
                    sucesso = True
                    resposta = str(result)
                    status = "ok"
            elif isinstance(result, str):
                sucesso, resposta, status = True, result, "ok"
            elif isinstance(result, dict):
                sucesso = result.get("sucesso", True)
                resposta = result.get("resposta", str(result))
                status = result.get("status", "ok")
            else:
                sucesso = True
                resposta = str(result)
                status = "ok"
            
            return bool(sucesso), resposta, status
        except Exception as e:
            logger.exception("Erro ao normalizar resposta: %s", e)
            return False, None, f"Erro na normalizao: {e}"

    def listar_disponiveis(self) -> Dict[str, Dict[str, Any]]:
        """Lista Aliadas configuradas e seu estado atual."""
        resultado: Dict[str, Dict[str, Any]] = {}
        with self._lock:
            for nome, cfg in self.aliadas_disponiveis.items():
                resultado[nome] = {
                    "nome_exibicao": cfg.get("nome", nome),
                    "ativa": bool(cfg.get("ativa", False)),
                    "carregada": nome in self.adaptadores_carregados,
                    "palavra_chave": cfg.get("palavra_chave", "")
                }
        return resultado

    def ativar_aliada(self, nome: str) -> Tuple[bool, str]:
        """Ativa e tenta carregar o adaptador de uma aliada."""
        nome_lower = str(nome).lower()
        
        if nome_lower not in self.aliadas_disponiveis:
            msg = f"Aliada '{nome}' no existe"
            logger.warning("[ERRO] %s", msg)
            return False, msg
        
        cfg = self.aliadas_disponiveis[nome_lower]
        
        if cfg.get("ativa", False):
            msg = f"Aliada '{cfg.get('nome', nome)}' j est ativa"
            logger.info(" %s", msg)
            return False, msg
        
        cfg["ativa"] = True
        # Persistir config
        self._salvar_config()
        
        modulo_nome = cfg.get("modulo")
        classe_nome = cfg.get("classe")
        
        if not modulo_nome or not classe_nome:
            cfg["ativa"] = False
            msg = "configuração incompleta (módulo/classe ausente)"
            logger.warning("[ERRO] %s: %s", nome_lower, msg)
            return False, msg
        
        try:
            module = importlib.import_module(modulo_nome)
            adapt_class = getattr(module, classe_nome)
            inst = self._tentar_instanciar_adaptador(adapt_class, cfg, nome_lower)
            
            if inst is None:
                cfg["ativa"] = False
                msg = f"Falha ao instanciar adaptador para {cfg.get('nome', nome_lower)}"
                return False, msg
            
            with self._lock:
                self.adaptadores_carregados[nome_lower] = inst
            
            msg = f"Aliada '{cfg.get('nome', nome_lower)}' ativada"
            logger.info("[OK] %s", msg)
            self._notificar_ui("ALIADA_ATIVADA", {"aliada": cfg.get("nome", nome_lower)})
            return True, msg
            
        except Exception as e:
            logger.exception("[ERRO] Erro ao ativar %s: %s", nome_lower, e)
            cfg["ativa"] = False
            msg = f"Erro ao ativar: {e}"
            self._notificar_ui("ALIADA_ATIVACAO_FALHA", {
                "aliada": cfg.get("nome", nome_lower),
                "erro": str(e)
            })
            return False, msg

    def desativar_aliada(self, nome: str) -> Tuple[bool, str]:
        """Desativa uma aliada e remove seu adaptador carregado."""
        nome_lower = str(nome).lower()
        
        if nome_lower not in self.aliadas_disponiveis:
            msg = f"Aliada '{nome}' no existe"
            logger.warning("[ERRO] %s", msg)
            return False, msg
        
        cfg = self.aliadas_disponiveis[nome_lower]
        cfg["ativa"] = False
        # Persistir config
        self._salvar_config()
        
        with self._lock:
            if nome_lower in self.adaptadores_carregados:
                try:
                    inst = self.adaptadores_carregados.pop(nome_lower)
                    
                    # Tentar chamar shutdown se existir
                    if hasattr(inst, "shutdown"):
                        try:
                            inst.shutdown()
                            logger.debug("    Shutdown executado para %s", nome_lower)
                        except Exception:
                            logger.debug("   [AVISO] Erro no shutdown (ignorado)")
                except Exception:
                    logger.exception("   [ERRO] Erro removendo adaptador")
        
        msg = f"Aliada '{cfg.get('nome', nome_lower)}' desativada"
        logger.info("[OK] %s", msg)
        self._notificar_ui("ALIADA_DESATIVADA", {"aliada": cfg.get("nome", nome_lower)})
        return True, msg

    def _salvar_config(self) -> None:
        """Salva config atual em arquivo."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump({"aliadas": self.aliadas_disponiveis}, f, ensure_ascii=False, indent=2)
            logger.debug("Config salva em: %s", self.config_path)
        except Exception as e:
            logger.exception("Erro ao salvar config: %s", e)

    def obter_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatsticas resumidas das aliadas."""
        with self._lock:
            total = len(self.aliadas_disponiveis)
            ativas = sum(1 for c in self.aliadas_disponiveis.values() if c.get("ativa", False))
            carregadas = len(self.adaptadores_carregados)
        
        with self._lock_stats:
            stats_copy = dict(self._stats_consultas)
        
        return {
            "total_aliadas": total,
            "ativas": ativas,
            "carregadas": carregadas,
            "estatisticas_consultas": stats_copy,
            "lista": self.listar_disponiveis()
        }

    def recarregar_config(self) -> None:
        """Fora recarregamento da configuração e (re)carrega adaptadores ativos."""
        logger.info(" Recarregando configuração de aliadas...")
        self._carregar_config()
        
        # Descarregar adaptadores que no esto mais ativos
        with self._lock:
            to_remove = [
                n for n, cfg in self.aliadas_disponiveis.items()
                if not cfg.get("ativa", False) and n in self.adaptadores_carregados
            ]
            for n in to_remove:
                self.adaptadores_carregados.pop(n, None)
                logger.debug("    Adaptador %s removido", n)
        
        # (Re)importar adaptadores ativos
        self._importar_adaptadores()
        logger.info("[OK] configuração recarregada")
        self._notificar_ui("CONFIG_RECARREGADA", self.obter_estatisticas())

    def injetar_ui_queue(self, fila_ui: queue.Queue) -> None:
        """Injeta fila de UI para notificaes."""
        self._ui_queue = fila_ui
        logger.info(" UI Queue injetada no GerenciadorAliadas")

    def shutdown(self) -> None:
        """Desativa todas as aliadas e libera recursos."""
        logger.info(" Desligando GerenciadorAliadas...")
        
        # Desativar todas as aliadas
        nomes = list(self.aliadas_disponiveis.keys())
        for nome in nomes:
            self.desativar_aliada(nome)
        
        with self._lock:
            self.adaptadores_carregados.clear()
        
        logger.info("[OK] GerenciadorAliadas desligado")
        self._notificar_ui("GERENCIADOR_ALIADAS_DESLIGADO", {})


# ============================================================================
# SINGLETON
# ============================================================================

_singleton_lock = RLock()
_singleton_instance: Optional[GerenciadorAliadas] = None


def obter_gerenciador(ui_queue: Optional[queue.Queue] = None) -> GerenciadorAliadas:
    """
    Retorna instncia global (singleton) do gerenciador de aliadas.Args:
        ui_queue: Fila para notificaes de UI (opcional)
    
    Returns:
        Instncia singleton do GerenciadorAliadas
    """
    global _singleton_instance
    with _singleton_lock:
        if _singleton_instance is None:
            _singleton_instance = GerenciadorAliadas(ui_queue=ui_queue)
        elif ui_queue and not _singleton_instance._ui_queue:
            _singleton_instance.injetar_ui_queue(ui_queue)
    return _singleton_instance


# ============================================================================
# TESTE
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger("GerenciadorAliadasTest")

    logger.info("\n" + "="*70)
    logger.info("TESTE GERENCIADOR DE ALIADAS")
    logger.info("="*70)

    # Criar gerenciador
    ui_queue = queue.Queue()
    gerenciador = obter_gerenciador(ui_queue=ui_queue)

    # Mostrar status
    logger.info("\n ESTATSTICAS INICIAIS:")
    stats = gerenciador.obter_estatisticas()
    logger.info("   Total de aliadas: %d", stats["total_aliadas"])
    logger.info("   Ativas: %d", stats["ativas"])
    logger.info("   Carregadas: %d", stats["carregadas"])

    # Listar aliadas
    logger.info("\n ALIADAS disponíveis:")
    for nome, info in gerenciador.listar_disponiveis().items():
        status_ativo = "[OK] ATIVA" if info["ativa"] else " INATIVA"
        status_carregada = " Carregada" if info["carregada"] else "[ERRO] No carregada"
        logger.info("    %s (%s) - %s - %s", 
                   info["nome_exibicao"], nome, status_ativo, status_carregada)

    # Tentar consulta (exemplo simulado)
    logger.info("\n TESTE DE CONSULTA (simulado):")
    logger.info("   Consultando 'qwen' com comando: 'Ol, como você est?'")
    sucesso, resposta, msg = gerenciador.consultar("qwen", "Ol, como você est?")
    logger.info("   Sucesso: %s", sucesso)
    logger.info("   Mensagem: %s", msg)

    # Verificar eventos na UI Queue
    logger.info("\n EVENTOS ENVIADOS PARA UI:")
    while True:
        try:
            evento = ui_queue.get_nowait()
            logger.info("    %s - %s", evento["tipo_resp"], evento["dados"])
        except queue.Empty:
            break

    # Shutdown
    logger.info("\n Desligando...")
    gerenciador.shutdown()

    logger.info("="*70)
    logger.info("FIM DO TESTE")
    logger.info("="*70 + "\n")

# --- FIM DO ARQUIVO gerenciador_aliadas.py ---
