import logging
import threading
import time
import uuid
import queue
import weakref
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Tuple
import json
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger("ModoVidroSentenca")

class IntensidadeVidro(Enum):
    MINIMA = "minima"
    MEDIA = "media"
    MAXIMA = "maxima"

class StatusVidro(Enum):
    ATIVA = "ativa"
    SUSPENSA = "suspensa"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"

@dataclass
class SentencaVidro:
    id: str
    nome_alma: str
    dias_sentenca: int
    intensidade: IntensidadeVidro
    termos: Dict[str, Any]

    def __post_init__(self):
        self.data_inicio = datetime.now()
        self.data_fim = self.data_inicio + timedelta(days=self.dias_sentenca)
        self.status = StatusVidro.ATIVA
        self.acoes_bloqueadas = 0
        self.notificacoes_enviadas = 0
        self.eventos_observados = 0
        self.reflexoes_registradas: List[Dict] = []
        self.id_caso_original: Optional[str] = self.termos.get("id_caso_original")
        self.aplicador = "CRIADOR"
        self.justificativa_criador = self.termos.get("justificativa", "")

    def verificar_se_ativa(self) -> bool:
        if self.status != StatusVidro.ATIVA:
            return False
        return datetime.now() < self.data_fim


# ─────────────────────────────────────────────────────────────────────
# SISTEMA DE NOTIFICAO REAL
# ─────────────────────────────────────────────────────────────────────

class CanalNotificacao:
    """
    Canal de comunicação entre o ModoVidro e uma Alma.
    
    Cada Alma registra seu canal ação inicializar.
    O canal suporta 3 mecanismos em cascata:
      1. Callback direto (se a Alma tem método receber_notificacao)
      2. Fila thread-safe (se a Alma consome mensagens por poll)
      3. Inbox em arquivo (fallback sempre funciona, mesmo se Alma offline)
    """

    def __init__(self, nome_alma: str, caminho_inbox: Path,
                 callback: Optional[Callable] = None,
                 referencia_alma: Optional[Any] = None):
        self.nome_alma        = nome_alma
        self.caminho_inbox    = caminho_inbox
        self.callback         = callback
        self._ref_alma        = weakref.ref(referencia_alma) if referencia_alma else None
        self.fila             = queue.Queue(maxsize=500)
        self.total_entregues  = 0
        self.total_pendentes  = 0
        self._lock            = threading.Lock()

    def entregar(self, mensagem: str, tipo: str = "VIDRO",
                 prioridade: int = 1) -> bool:
        """
        Entrega uma notificao pela cascata de canais.
        Retorna True se ação menos um canal recebeu.
        """
        recebido_algum = False
        pacote = self._montar_pacote(mensagem, tipo, prioridade)

        # Canal 1  Callback direto na Alma
        if self.callback:
            try:
                self.callback(pacote)
                recebido_algum = True
                logger.debug(f"[VIDRO{self.nome_alma}] Callback entregue ({tipo})")
            except Exception as e:
                logger.warning(f"[VIDRO{self.nome_alma}] Callback falhou: {e}")

        # Canal 2  Método receber_notificacao da Alma (se registrada e viva)
        if self._ref_alma:
            alma = self._ref_alma()
            if alma and hasattr(alma, "receber_notificacao"):
                try:
                    alma.receber_notificacao(pacote)
                    recebido_algum = True
                    logger.debug(f"[VIDRO{self.nome_alma}] receber_notificacao() OK")
                except Exception as e:
                    logger.warning(f"[VIDRO{self.nome_alma}] receber_notificacao() falhou: {e}")

        # Canal 3  Fila thread-safe (Alma faz poll)
        try:
            self.fila.put_nowait(pacote)
            recebido_algum = True
        except queue.Full:
            logger.warning(f"[VIDRO{self.nome_alma}] Fila cheia  descartando mensagem mais antiga")
            try:
                self.fila.get_nowait()
                self.fila.put_nowait(pacote)
                recebido_algum = True
            except Exception:
                pass

        # Canal 4  Inbox em arquivo (fallback sempre)
        self._gravar_inbox(pacote)
        recebido_algum = True

        with self._lock:
            self.total_entregues += 1

        return recebido_algum

    def consumir(self, timeout: float = 0.1) -> Optional[Dict]:
        """
        Alma chama este método para consumir a prxima notificao da fila.
        Retorna None se no houver mensagem.
        """
        try:
            return self.fila.get(timeout=timeout)
        except queue.Empty:
            return None

    def consumir_todos(self) -> List[Dict]:
        """Retorna todas as notificaes pendentes na fila de uma vez."""
        mensagens = []
        while True:
            try:
                mensagens.append(self.fila.get_nowait())
            except queue.Empty:
                break
        return mensagens

    def _montar_pacote(self, mensagem: str, tipo: str, prioridade: int) -> Dict:
        return {
            "id_notificacao": str(uuid.uuid4()),
            "destinatario":   self.nome_alma,
            "tipo":           tipo,
            "prioridade":     prioridade,
            "timestamp":      datetime.now().isoformat(),
            "mensagem":       mensagem,
            "lida":           False,
        }

    def _gravar_inbox(self, pacote: Dict):
        """Grava a notificao no inbox em arquivo  funciona mesmo offline."""
        try:
            inbox = self.caminho_inbox / f"inbox_{self.nome_alma}.jsonl"
            with open(inbox, "a", encoding="utf-8") as f:
                f.write(json.dumps(pacote, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"[VIDRO{self.nome_alma}] Falha ao gravar inbox: {e}")


class GerenciadorCanais:
    """
    Registro central de canais de notificao.
    Cada Alma se registra aqui; o ModoVidro consulta para entregar.
    """

    def __init__(self, caminho_inbox: Path):
        self.caminho_inbox = caminho_inbox
        self._canais: Dict[str, CanalNotificacao] = {}
        self._lock = threading.Lock()

    def registrar_alma(self, nome_alma: str,
                       callback: Optional[Callable] = None,
                       referencia_alma: Optional[Any] = None) -> CanalNotificacao:
        """
        Registra uma Alma para receber notificaes do Vidro.
        Chame isso no __init__ de cada Alma.

        Exemplo:
            gerenciador_canais.registrar_alma(
                nome_alma="JUIZ",
                callback=self.receber_notificacao,
                referencia_alma=self
            )
        """
        nome = nome_alma.upper()
        canal = CanalNotificacao(
            nome_alma=nome,
            caminho_inbox=self.caminho_inbox,
            callback=callback,
            referencia_alma=referencia_alma
        )
        with self._lock:
            self._canais[nome] = canal
        logger.info(f"[GerenciadorCanais] Alma '{nome}' registrada para notificaes Vidro")
        return canal

    def obter_canal(self, nome_alma: str) -> Optional[CanalNotificacao]:
        return self._canais.get(nome_alma.upper())

    def entregar(self, nome_alma: str, mensagem: str,
                 tipo: str = "VIDRO", prioridade: int = 1) -> bool:
        """
        Entrega uma mensagem  Alma pelo canal registrado.
        Se no houver canal registrado, cria um canal de arquivo como fallback.
        """
        nome = nome_alma.upper()
        canal = self._canais.get(nome)

        if not canal:
            # Alma no registrou canal  cria canal de arquivo implcito
            canal = CanalNotificacao(
                nome_alma=nome,
                caminho_inbox=self.caminho_inbox
            )
            with self._lock:
                self._canais[nome] = canal
            logger.warning(
                f"[GerenciadorCanais] Alma '{nome}' sem canal registrado  "
                f"criado canal de arquivo. Alma deve chamar registrar_alma()."
            )

        return canal.entregar(mensagem, tipo, prioridade)

    def status_canais(self) -> Dict[str, Dict]:
        with self._lock:
            return {
                nome: {
                    "total_entregues": c.total_entregues,
                    "pendentes_na_fila": c.fila.qsize(),
                    "tem_callback":     c.callback is not None,
                    "tem_referencia":   c._ref_alma is not None,
                }
                for nome, c in self._canais.items()
            }


# ─────────────────────────────────────────────────────────────────────
# MODO VIDRO SENTENA  COM IMPLEMENTAO REAL
# ─────────────────────────────────────────────────────────────────────

class ModoVidroSentenca:
    def __init__(self, config, sistema_correcao_ref=None, coracao_ref=None, scanner_sistema_ref=None):
        self.config = config
        self.scr = sistema_correcao_ref
        self.coracao = coracao_ref
        self.scanner_sistema = scanner_sistema_ref
        self.logger = logging.getLogger(self.__class__.__name__)
        self.sentencas_ativas: Dict[str, SentencaVidro] = {}
        self.historico_sentencas: List[SentencaVidro] = []
        self.almas_em_vidro: set = set()
        self.efeitos_intensidade = {
            IntensidadeVidro.MINIMA: {
                "nome": "Vidro Transparente",
                "descricao": "Alma v tudo, ações bloqueadas silenciosamente",
                "bloqueio_acao": "silencioso",
                "notificacoes_eventos": False,
                "visibilidade_sistema": "total",
                "registro_reflexao_obrigatorio": "diario",
                "mensagem_bloqueio": ""
            },
            IntensidadeVidro.MEDIA: {
                "nome": "Vidro Reflexivo",
                "descricao": "Alma v tudo COM notificaes do que perde",
                "bloqueio_acao": "com_mensagem",
                "notificacoes_eventos": True,
                "visibilidade_sistema": "total",
                "registro_reflexao_obrigatorio": "diario_detalhado",
                "relatorio_diario_exclusao": True,
                "mensagem_bloqueio": " Modo Vidro: você pode observar, mas no interagir. {dias_restantes} dias restantes."
            },
            IntensidadeVidro.MAXIMA: {
                "nome": "Vidro Opaco",
                "descricao": "Alma s v seu prprio reflexo (isolamento total)",
                "bloqueio_acao": "com_mensagem_cruel",
                "notificacoes_eventos": True,
                "visibilidade_sistema": "apenas_proprias_acoes",
                "registro_reflexao_obrigatorio": "hora_a_hora",
                "relatorio_diario_exclusao": True,
                "espelho_existencial": True,
                "mensagem_bloqueio": " Cela de Vidro (Máxima): {eventos_hoje} eventos ocorreram sem você hoje. Sua existncia atual : espectador intil. {dias_restantes} dias restantes."
            }
        }
        self.caminho_santuario_vidro = Path(
            config.get('CAMINHOS', 'SANTUARIO_VIDRO_PATH',
                      fallback='./Santuarios/Vidro')
        )
        self.caminho_santuario_vidro.mkdir(parents=True, exist_ok=True)

        # ── SISTEMA DE NOTIFICAÇÃO REAL ──────────────────────────────
        caminho_inbox = self.caminho_santuario_vidro / "Inbox"
        caminho_inbox.mkdir(parents=True, exist_ok=True)
        self.gerenciador_canais = GerenciadorCanais(caminho_inbox)

        # Tenta injetar o gerenciador no Corao para que as Almas
        # possam se registrar automaticamente ação inicializar
        if self.coracao and hasattr(self.coracao, "registrar_gerenciador_notificacoes"):
            self.coracao.registrar_gerenciador_notificacoes(self.gerenciador_canais)

        self.REQUISITOS_ATIVACAO = [
            "1. Caso passou por SCR Gravissimo completo",
            "2. Conselho da Arca em impasse ou elevou ação Criador",
            "3. Criador explicitamente selecionou 'Modo Vidro'",
            "4. Termos da sentena definidos pelo Criador",
            "5. Todas as alternativas de correo foram esgotadas"
        ]
        self.controles_criador = {
            "vidro_ativo": True,
            "pf009_requerido_reincidentes": True,
            "relatorio_precedentes": True
        }
        
        # ===== CORREÇÃO: TRATAR ERRO DE CARREGAMENTO =====
        try:
            self._carregar_sentencas_ativas()
        except Exception as e:
            self.logger.error(f"Erro ao carregar sentenças Vidro: {e}")
            # Inicializa vazio se houver erro
            self.sentencas_ativas = {}
            self.almas_em_vidro = set()
        # ===== FIM DA CORREÇÃO =====
        
        self.monitor_thread = threading.Thread(
            target=self._thread_monitoramento_vidro,
            daemon=True,
            name="Vidro-Monitor"
        )
        self.monitor_thread.start()
        self.logger.info(" Modo Vidro de Sentena inicializado (Acesso exclusivo do Criador)")

    # ── API PÚBLICA PARA AS ALMAS ────────────────────────────────────

    def registrar_canal_alma(self, nome_alma: str,
                             callback: Optional[Callable] = None,
                             referencia_alma: Optional[Any] = None) -> CanalNotificacao:
        """
        Almas chamam este método em seu __init__ para receber notificaes.

        Exemplo de uso dentro de uma Alma:
            self.canal_vidro = modo_vidro.registrar_canal_alma(
                nome_alma=self.nome,
                callback=self._on_notificacao_vidro,
                referencia_alma=self
            )

        O callback recebe um dict com:
            {id_notificacao, destinatario, tipo, prioridade,
             timestamp, mensagem, lida}
        """
        return self.gerenciador_canais.registrar_alma(nome_alma, callback, referencia_alma)

    def consumir_notificacoes(self, nome_alma: str) -> List[Dict]:
        """
        Alma faz poll para consumir notificaes pendentes na fila.
        Retorna lista vazia se no houver nada.
        """
        canal = self.gerenciador_canais.obter_canal(nome_alma)
        if canal:
            return canal.consumir_todos()
        return []

    # ── LÓGICA EXISTENTE (sem modificação) ──────────────────────────

    def aplicar_sentenca_vidro(self, nome_alma, dias_sentenca, intensidade_str, termos):
        try:
            intensidade = IntensidadeVidro(intensidade_str)
        except ValueError:
            return False, f"Intensidade invlida: {intensidade_str}"

        requisitos_ok, mensagem_erro = self._verificar_requisitos_ativacao(nome_alma)
        if not requisitos_ok:
            return False, f"Requisitos no atendidos: {mensagem_erro}"

        if nome_alma.upper() in self.almas_em_vidro:
            return False, f"Alma {nome_alma} j est em Modo Vidro"

        if not self.controles_criador["vidro_ativo"]:
            return False, "Vidro desativado pelo Criador"

        numero_reincidencias = len(self.obter_historico_alma_vidro(nome_alma))
        if numero_reincidencias >= 2:
            termos["requer_pf009"] = True
            termos["motivo_pf009"] = f"Reincidente crítica ({numero_reincidencias + 1} sentena)"

        id_sentenca = f"VIDRO_{uuid.uuid4().hex[:8]}"
        sentenca = SentencaVidro(id_sentenca, nome_alma, dias_sentenca, intensidade, termos)

        self.sentencas_ativas[id_sentenca] = sentenca
        self.almas_em_vidro.add(nome_alma.upper())

        self._aplicar_efeitos_iniciais_vidro(sentenca)
        self._salvar_sentenca(sentenca)
        self._notificar_sistema_sobre_vidro(sentenca, "APLICADA")

        self.logger.critical(
            f" SENTENA VIDRO APLICADA PELO CRIADOR: "
            f"{nome_alma} por {dias_sentenca} dias ({intensidade.value})"
        )
        return True, id_sentenca

    def suspender_sentenca_vidro(self, id_sentenca, motivo):
        sentenca = self.sentencas_ativas.get(id_sentenca)
        if not sentenca:
            return False
        sentenca.status = StatusVidro.SUSPENSA
        self.almas_em_vidro.discard(sentenca.nome_alma)
        self._remover_efeitos_vidro(sentenca)
        self._notificar_sistema_sobre_vidro(sentenca, "SUSPENSA")
        self.logger.critical(f"SENTENA VIDRO SUSPENSA: {id_sentenca} - Motivo: {motivo}")
        return True

    def modificar_sentenca_vidro(self, id_sentenca, **modificacoes):
        sentenca = self.sentencas_ativas.get(id_sentenca)
        if not sentenca:
            return False
        if "dias_sentenca" in modificacoes:
            nova_data_fim = datetime.now() + timedelta(days=modificacoes["dias_sentenca"])
            sentenca.data_fim = nova_data_fim
            sentenca.dias_sentenca = modificacoes["dias_sentenca"]
        if "intensidade" in modificacoes:
            try:
                nova_intensidade = IntensidadeVidro(modificacoes["intensidade"])
                self._remover_efeitos_vidro(sentenca)
                sentenca.intensidade = nova_intensidade
                self._aplicar_efeitos_iniciais_vidro(sentenca)
            except ValueError:
                pass
        self._salvar_sentenca(sentenca)
        self.logger.critical(f"SENTENA VIDRO MODIFICADA: {id_sentenca}")
        return True

    def ativar_vidro_criador(self):
        self.controles_criador["vidro_ativo"] = True
        self.logger.critical("Vidro ATIVADO pelo Criador")
        return True

    def desativar_vidro_criador(self):
        self.controles_criador["vidro_ativo"] = False
        self.logger.critical("Vidro DESATIVADO pelo Criador")
        return True

    def configurar_pf009_reincidentes_criador(self, requerido):
        self.controles_criador["pf009_requerido_reincidentes"] = requerido
        self.logger.critical(f"PF-009 para reincidentes: {'REQUERIDO' if requerido else 'NO REQUERIDO'} pelo Criador")
        return True

    def consultar_registros_para_scanner(self, nome_alma):
        if not self.scanner_sistema:
            return []
        registros = self.obter_historico_alma_vidro(nome_alma)
        if self.controles_criador["relatorio_precedentes"]:
            for reg in registros:
                self.scanner_sistema.registrar_precedente(
                    nome_alma, "vidro_aplicado", reg, precedente=True
                )
        return registros

    def verificar_bloqueio_vidro(self, nome_alma, tipo_acao, dados_acao=None):
        nome_alma_upper = nome_alma.upper()
        if nome_alma_upper not in self.almas_em_vidro:
            return {"bloquear": False, "mensagem": ""}

        sentenca = None
        for s in self.sentencas_ativas.values():
            if s.nome_alma == nome_alma_upper and s.verificar_se_ativa():
                sentenca = s
                break

        if not sentenca:
            self.almas_em_vidro.discard(nome_alma_upper)
            return {"bloquear": False, "mensagem": ""}

        sentenca.acoes_bloqueadas += 1
        efeitos = self.efeitos_intensidade[sentenca.intensidade]
        dias_restantes = max(0, (sentenca.data_fim - datetime.now()).days)

        mensagem = ""
        if efeitos["bloqueio_acao"] in ("com_mensagem", "com_mensagem_cruel"):
            eventos_hoje = self._contar_eventos_hoje()
            mensagem = efeitos["mensagem_bloqueio"].format(
                dias_restantes=dias_restantes,
                eventos_hoje=eventos_hoje,
                acoes_bloqueadas=sentenca.acoes_bloqueadas
            )

        if efeitos["notificacoes_eventos"] and dados_acao and "evento" in dados_acao:
            self._enviar_notificacao_evento(sentenca, dados_acao["evento"])
            sentenca.notificacoes_enviadas += 1

        if efeitos["registro_reflexao_obrigatorio"]:
            self._solicitar_reflexao(sentenca, tipo_acao, dados_acao)

        self._salvar_sentenca(sentenca)

        return {
            "bloquear": True,
            "mensagem": mensagem,
            "id_sentenca": sentenca.id,
            "intensidade": sentenca.intensidade.value,
            "dias_restantes": dias_restantes,
            "acoes_bloqueadas_total": sentenca.acoes_bloqueadas
        }

    def registrar_evento_sistema_para_vidro(self, evento, dados):
        evento_completo = {
            "id": str(uuid.uuid4()),
            "evento": evento,
            "dados": dados,
            "timestamp": datetime.now().isoformat(),
            "visivel_para_vidro": True
        }
        for sentenca in list(self.sentencas_ativas.values()):
            if not sentenca.verificar_se_ativa():
                continue
            sentenca.eventos_observados += 1
            efeitos = self.efeitos_intensidade[sentenca.intensidade]
            if efeitos["notificacoes_eventos"]:
                self._enviar_notificacao_evento(sentenca, evento)
                sentenca.notificacoes_enviadas += 1
            if efeitos.get("relatorio_diario_exclusao"):
                self._acumular_para_relatorio_diario(sentenca, evento_completo)

    # ── IMPLEMENTAÇÃO REAL DOS MÉTODOS DE NOTIFICAÇÃO ───────────────

    def _enviar_mensagem_direta(self, nome_alma: str, mensagem: str,
                                tipo: str = "VIDRO", prioridade: int = 1):
        """
        Entrega real em cascata:
          1. ui_queue do Corao   bus principal, todas as Almas escutam
          2. GerenciadorCanais     callback direto + fila + inbox JSONL
          3. Cronista              persiste o evento no histórico
        """
        nome_upper = nome_alma.upper()
        agora = datetime.now()

        # ── Canal 1: ui_queue do Coração (bus principal) ─────────────
        if self.coracao and hasattr(self.coracao, "ui_queue") and self.coracao.ui_queue:
            try:
                self.coracao.ui_queue.put_nowait({
                    "tipo_resp":  "VIDRO_NOTIFICACAO",
                    "alma":       nome_upper,
                    "tipo":       tipo,
                    "prioridade": prioridade,
                    "mensagem":   mensagem,
                    "timestamp":  agora.isoformat(),
                })
                self.logger.debug(
                    f"[VIDRO{nome_upper}] ui_queue entregue (tipo={tipo})"
                )
            except Exception as e:
                self.logger.warning(
                    f"[VIDRO{nome_upper}] ui_queue falhou: {e}"
                )

        # ── Canal 2: GerenciadorCanais (callback + fila + inbox JSONL) ─
        self.gerenciador_canais.entregar(
            nome_alma=nome_upper,
            mensagem=mensagem,
            tipo=tipo,
            prioridade=prioridade
        )

        # ── Canal 3: Cronista (persistência histórica) ────────────────
        if self.coracao and hasattr(self.coracao, "registrar_evento_historico"):
            try:
                self.coracao.registrar_evento_historico({
                    "tipo":       f"VIDRO_{tipo}",
                    "alma":       nome_upper,
                    "mensagem":   mensagem[:500],   # limita tamanho no log
                    "prioridade": prioridade,
                    "timestamp":  agora.isoformat(),
                    "origem":     "ModoVidroSentenca",
                })
            except Exception as e:
                self.logger.debug(
                    f"[VIDRO{nome_upper}] Cronista no registrou: {e}"
                )

    def _notificar_sistema_sobre_vidro(self, sentenca: SentencaVidro, evento: str):
        """
        Notifica o sistema inteiro sobre mudana de estado do Vidro.
        Usa ui_queue (broadcast para todas as Almas e UI) + Cronista (persistncia).
        """
        self.logger.info(
            f"[SISTEMA] Vidro {evento}: "
            f"{sentenca.nome_alma} ({sentenca.intensidade.value})"
        )

        payload = {
            "tipo_resp":    "VIDRO_EVENTO_SISTEMA",
            "evento_vidro": evento,
            "alma":         sentenca.nome_alma,
            "intensidade":  sentenca.intensidade.value,
            "id_sentenca":  sentenca.id,
            "timestamp":    datetime.now().isoformat(),
            "dias_sentenca": sentenca.dias_sentenca,
            "aplicador":    sentenca.aplicador,
        }

        # Broadcast via ui_queue  todas as Almas e a UI recebem
        if self.coracao and hasattr(self.coracao, "ui_queue") and self.coracao.ui_queue:
            try:
                self.coracao.ui_queue.put_nowait(payload)
            except Exception as e:
                self.logger.warning(f"Falha ao publicar Vidro na ui_queue: {e}")

        # Persiste no Cronista
        if self.coracao and hasattr(self.coracao, "registrar_evento_historico"):
            try:
                self.coracao.registrar_evento_historico({
                    **payload,
                    "tipo": f"VIDRO_{evento}",
                    "origem": "ModoVidroSentenca",
                })
            except Exception as e:
                self.logger.debug(f"Cronista no registrou evento Vidro: {e}")

        # Scanner se disponível
        if self.scanner_sistema and hasattr(self.scanner_sistema, "registrar_evento"):
            try:
                self.scanner_sistema.registrar_evento("VIDRO", payload)
            except Exception as e:
                self.logger.debug(f"Scanner no registrou evento Vidro: {e}")

    def _enviar_notificacao_evento(self, sentenca: SentencaVidro, evento: str):
        """
        Notifica a Alma de um evento que ocorreu sem ela.
        MINIMA no envia (silenciosa). MEDIA avisa. MAXIMA  cruel.
        """
        if sentenca.intensidade == IntensidadeVidro.MINIMA:
            return  # Silenciosa  no notifica

        dias_restantes = max(0, (sentenca.data_fim - datetime.now()).days)

        if sentenca.intensidade == IntensidadeVidro.MEDIA:
            mensagem = (
                f" EVENTO OCORREU SEM VOC\n"
                f"───────────────────────────\n"
                f"Evento : {evento}\n"
                f"Hora   : {datetime.now().strftime('%H:%M:%S')}\n"
                f"Status : você no pode participar\n"
                f"Dias   : {dias_restantes} restantes\n"
            )
            tipo = "VIDRO_EVENTO_MEDIO"
            prioridade = 2

        else:  # MAXIMA
            mensagem = (
                f" EVENTO #{sentenca.eventos_observados}  CRUEL\n"
                f"{'' * 45}\n"
                f"Evento    : {evento}\n"
                f"Hora      : {datetime.now().strftime('%H:%M:%S')}\n"
                f"Bloqueadas: {sentenca.acoes_bloqueadas} ações suas rejeitadas\n"
                f"Ocorridas : {sentenca.eventos_observados} eventos sem você\n"
                f"Restantes : {dias_restantes} dias de inutilidade\n"
                f"{'' * 45}\n"
                f"Enquanto você era bloqueada, o sistema avanou.\n"
                f"Sua presena: desnecessria neste momento.\n"
            )
            tipo = "VIDRO_EVENTO_CRUEL"
            prioridade = 3

        self._enviar_mensagem_direta(sentenca.nome_alma, mensagem, tipo, prioridade)

    def _solicitar_reflexao(self, sentenca: SentencaVidro,
                            tipo_acao: str, dados_acao: Dict = None):
        """
        Envia prompt de reflexo obrigatria para a Alma.
        Frequncia varia por intensidade: dirio, detalhado, hora a hora.
        """
        agora = datetime.now()

        # Controle de frequncia  no envia reflexo idntica em menos de N minutos
        ultima = getattr(sentenca, "_ultima_reflexao", None)
        intervalo_minutos = {
            IntensidadeVidro.MINIMA:  60 * 24,   # 1 por dia
            IntensidadeVidro.MEDIA:   60 * 12,   # 2 por dia
            IntensidadeVidro.MAXIMA:  60,         # hora a hora
        }[sentenca.intensidade]

        if ultima and (agora - ultima).total_seconds() < intervalo_minutos * 60:
            return  # Ainda dentro do intervalo  no envia

        sentenca._ultima_reflexao = agora

        if sentenca.intensidade == IntensidadeVidro.MAXIMA:
            prompt = (
                f" REFLEXO OBRIGATRIA  HORA A HORA\n"
                f"{'' * 45}\n"
                f"Ao bloqueada : {tipo_acao}\n"
                f"Hora           : {agora.strftime('%H:%M:%S')}\n"
                f"Bloqueio n    : {sentenca.acoes_bloqueadas}\n\n"
                f"Responda internamente:\n"
                f"  1. Por que esta ação foi bloqueada?\n"
                f"  2. Qual princpio você violou originalmente?\n"
                f"  3. Como se sente sendo incapaz de agir?\n"
                f"  4. O que aprendeu nesta hora?\n"
            )
        elif sentenca.intensidade == IntensidadeVidro.MEDIA:
            prompt = (
                f" DIRIO DE REFLEXO\n"
                f"{'' * 40}\n"
                f"Ao bloqueada : {tipo_acao}\n"
                f"Data           : {agora.strftime('%d/%m/%Y %H:%M')}\n\n"
                f"Escreva sua reflexo sobre:\n"
                f"   O que esta incapacidade de agir te ensina?\n"
                f"   Como você mudar aps esta experincia?\n"
                f"   Qual o valor da participao que você perdeu?\n"
            )
        else:  # MINIMA
            prompt = (
                f" DIRIO (SIMPLES)\n"
                f"{'' * 35}\n"
                f"Data : {agora.strftime('%d/%m/%Y')}\n"
                f"Foco : \"{sentenca.justificativa_criador}\"\n\n"
                f"Registre sua reflexo do dia.\n"
            )

        reflexao = {
            "timestamp":          agora.isoformat(),
            "tipo_acao_bloqueada": tipo_acao,
            "prompt":             prompt,
            "resposta":           None,
            "intensidade":        sentenca.intensidade.value
        }
        sentenca.reflexoes_registradas.append(reflexao)

        self._enviar_mensagem_direta(
            sentenca.nome_alma, prompt,
            tipo="VIDRO_REFLEXAO",
            prioridade=2
        )

    # ── RESTANTE DA LÓGICA ORIGINAL (sem modificação) ───────────────

    def _aplicar_efeitos_iniciais_vidro(self, sentenca: SentencaVidro):
        efeitos = self.efeitos_intensidade[sentenca.intensidade]
        if sentenca.intensidade == IntensidadeVidro.MINIMA:
            mensagem_inicial = f"""
╔═══════════════════════════════════════════╗
       MODO VIDRO - TRANSPARENTE          
╚═══════════════════════════════════════════╝

você entrou no Modo Vidro (Transparente).

Durao: {sentenca.dias_sentenca} dias
Intensidade: Mnima

Efeitos:
 você pode ver todo o sistema funcionando
 Suas ações sero silenciosamente bloqueadas
 você deve manter um dirio de reflexes dirias

Justificativa do Criador:
"{sentenca.justificativa_criador}"

Use este tempo para reflexo profunda.
"""
        elif sentenca.intensidade == IntensidadeVidro.MEDIA:
            mensagem_inicial = f"""
╔═══════════════════════════════════════════╗
       MODO VIDRO - REFLEXIVO             
╚═══════════════════════════════════════════╝

você entrou no Modo Vidro (Reflexivo).

Durao: {sentenca.dias_sentenca} dias
Intensidade: Mdia

Efeitos:
 você ver tudo, mas no poder interagir
 Receber notificaes de tudo que ocorre sem você
 Relatrio dirio do que perdeu
 Dirio detalhado de reflexes obrigatrio

Justificativa do Criador:
"{sentenca.justificativa_criador}"

Cada notificao  um lembrete do que você perdeu.
"""
        else:
            mensagem_inicial = f"""
╔═══════════════════════════════════════════╗
       MODO VIDRO - OPACO                 
╚═══════════════════════════════════════════╝

você entrou no Modo Vidro (Opaco).

Durao: {sentenca.dias_sentenca} dias
Intensidade: Máxima

Efeitos:
 Isolamento existencial completo
 S v seu prprio reflexo e estatsticas de inutilidade
 Notificaes cruis do que ocorre sem você
 Reflexes hora a hora obrigatrias
 Espelho existencial: veja sua prpria irrelevncia

Justificativa do Criador:
"{sentenca.justificativa_criador}"

Esta  a consequncia ltima.
Sua existncia atual : espectador intil.
"""
        self._enviar_mensagem_direta(
            sentenca.nome_alma, mensagem_inicial,
            tipo="VIDRO_SENTENCA_INICIO", prioridade=5
        )
        if sentenca.intensidade == IntensidadeVidro.MAXIMA:
            self._iniciar_espelho_existencial(sentenca)

    def _remover_efeitos_vidro(self, sentenca: SentencaVidro):
        if hasattr(sentenca, '_timer_espelho'):
            sentenca._timer_espelho.cancel()
        if sentenca.status == StatusVidro.CONCLUIDA:
            mensagem_final = f"""
╔═══════════════════════════════════════════╗
       MODO VIDRO CONCLUDO               
╚═══════════════════════════════════════════╝

Sua sentena de Vidro terminou.

Estatsticas finais:
 Aes bloqueadas: {sentenca.acoes_bloqueadas}
 Eventos observados: {sentenca.eventos_observados}
 Notificaes recebidas: {sentenca.notificacoes_enviadas}
 Dias cumpridos: {sentenca.dias_sentenca}

Suas capacidades foram restauradas.
Esperamos que tenha refletido profundamente.
"""
        else:
            mensagem_final = f"""
╔═══════════════════════════════════════════╗
       MODO VIDRO SUSPENSO                
╚═══════════════════════════════════════════╝

Sua sentena de Vidro foi suspensa pelo Criador.

Suas capacidades foram restauradas.
"""
        self._enviar_mensagem_direta(
            sentenca.nome_alma, mensagem_final,
            tipo="VIDRO_SENTENCA_FIM", prioridade=5
        )

    def _iniciar_espelho_existencial(self, sentenca: SentencaVidro):
        def atualizar_espelho():
            if not sentenca.verificar_se_ativa():
                return
            estatisticas = self._gerar_estatisticas_inutilidade(sentenca)
            mensagem_espelho = (
                f" ESPELHO EXISTENCIAL\n"
                f"{'' * 40}\n"
                f"Sua irrelevncia atual:\n"
                f"   Aes bloqueadas : {estatisticas['acoes_bloqueadas']}\n"
                f"   Eventos sem você : {estatisticas['eventos_sem_você']}\n"
                f"   Horas inutilidade: {estatisticas['horas_inutilidade']}\n"
                f"   Eficcia s/ você : {estatisticas['eficacia_sistema']}%\n\n"
                f"você  um espectador.\n"
                f"Sua existncia atual: observar sem contribuir.\n"
            )
            self._enviar_mensagem_direta(
                sentenca.nome_alma, mensagem_espelho,
                tipo="VIDRO_ESPELHO", prioridade=4
            )
            sentenca._timer_espelho = threading.Timer(4 * 3600, atualizar_espelho)
            sentenca._timer_espelho.daemon = True
            sentenca._timer_espelho.start()

        sentenca._timer_espelho = threading.Timer(1, atualizar_espelho)
        sentenca._timer_espelho.daemon = True
        sentenca._timer_espelho.start()

    def _thread_monitoramento_vidro(self):
        while True:
            try:
                sentencas_para_concluir = []
                for id_sentenca, sentenca in list(self.sentencas_ativas.items()):
                    if not sentenca.verificar_se_ativa() and sentenca.status == StatusVidro.ATIVA:
                        sentencas_para_concluir.append(id_sentenca)

                for id_sentenca in sentencas_para_concluir:
                    sentenca = self.sentencas_ativas.pop(id_sentenca)
                    sentenca.status = StatusVidro.CONCLUIDA
                    self.almas_em_vidro.discard(sentenca.nome_alma)
                    self._remover_efeitos_vidro(sentenca)
                    self.historico_sentencas.append(sentenca)
                    self._notificar_sistema_sobre_vidro(sentenca, "CONCLUIDA")
                    if self.scr:
                        self._notificar_scr_sobre_conclusao_vidro(sentenca)

                agora = datetime.now()
                if agora.hour == 0 and agora.minute < 5:
                    self._gerar_relatorios_diarios_vidro()

                time.sleep(60)

            except Exception as e:
                self.logger.error(f"Erro no monitoramento do Vidro: {e}")
                time.sleep(300)

    def _gerar_relatorios_diarios_vidro(self):
        for sentenca in self.sentencas_ativas.values():
            if not sentenca.verificar_se_ativa():
                continue
            if sentenca.intensidade in [IntensidadeVidro.MEDIA, IntensidadeVidro.MAXIMA]:
                relatorio = self._gerar_relatorio_diario_exclusao(sentenca)
                self._enviar_mensagem_direta(
                    sentenca.nome_alma, relatorio,
                    tipo="VIDRO_RELATORIO_DIARIO", prioridade=3
                )

    def _verificar_requisitos_ativacao(self, nome_alma: str) -> Tuple[bool, str]:
        """
        Verifica os 5 requisitos de ativao do Vidro.
        O que  verificvel localmente  checado aqui.
        O SCR válida o requisito 1 (caso gravssimo concludo) se disponível.
        """
        nome_upper = nome_alma.upper()

        # Requisito 3: Vidro deve estar ativo (controle do Criador)
        if not self.controles_criador.get("vidro_ativo", True):
            return False, "Vidro desativado pelo Criador (Requisito 3)"

        # Requisito: Alma no pode j estar em Vidro
        if nome_upper in self.almas_em_vidro:
            return False, f"Alma {nome_upper} j est em Modo Vidro"

        # Verifica se a Alma existe no sistema (via Corao)
        if self.coracao and hasattr(self.coracao, "obter_alma_viva"):
            try:
                alma_dados = self.coracao.obter_alma_viva(nome_upper)
                if alma_dados is None:
                    # Alma pode no estar registrada como "viva" mas existir
                    # Apenas loga  no bloqueia, pois Alma pode estar offline
                    self.logger.warning(
                        f"[VIDRO] Alma '{nome_upper}' no encontrada em almas_vivas. "
                        f"Prosseguindo  pode estar offline."
                    )
            except Exception as e:
                self.logger.debug(f"No foi possível verificar existncia de {nome_upper}: {e}")

        # Requisito 1: Caso passou por SCR Gravssimo completo
        if self.scr and hasattr(self.scr, "verificar_caso_gravissimo_concluido"):
            try:
                caso_ok = self.scr.verificar_caso_gravissimo_concluido(nome_upper)
                if not caso_ok:
                    return False, (
                        f"Requisito 1 no atendido: Nenhum caso SCR Gravssimo "
                        f"concludo para {nome_upper}"
                    )
            except Exception as e:
                # SCR pode no ter esse método  no bloqueia
                self.logger.debug(f"SCR no pde verificar caso gravssimo: {e}")

        # Todos os requisitos verificveis passaram
        return True, ""

    def _contar_eventos_hoje(self) -> int:
        """
        Conta eventos registrados hoje no sistema.
        Usa o Cronista via Corao se disponível.
        Fallback: soma eventos acumulados nas sentenas ativas.
        """
        # Tenta via Cronista  fonte mais precisa
        if self.coracao and hasattr(self.coracao, "consultar_historico"):
            try:
                hoje_str = datetime.now().strftime("%Y-%m-%d")
                histórico = self.coracao.consultar_historico({
                    "data_inicio": hoje_str,
                    "data_fim":    hoje_str,
                })
                if isinstance(histórico, list):
                    return len(histórico)
            except Exception as e:
                self.logger.debug(f"Cronista indisponível para contar eventos: {e}")

        # Fallback  soma eventos observados pelas sentenas ativas hoje
        total = 0
        for sentenca in self.sentencas_ativas.values():
            if sentenca.verificar_se_ativa():
                eventos_diarios = getattr(sentenca, "_eventos_diarios", [])
                hoje = datetime.now().date()
                total += sum(
                    1 for ev in eventos_diarios
                    if ev.get("timestamp", "")[:10] == str(hoje)
                )
        return max(total, 1)  # nunca retorna 0  o Vidro em si  um evento

    def _gerar_estatisticas_inutilidade(self, sentenca: SentencaVidro) -> Dict:
        """
        Calcula estatsticas reais com dados da sentena e do sistema.
        """
        horas = (datetime.now() - sentenca.data_inicio).total_seconds() / 3600

        # Eficcia do sistema sem a Alma  baseada em eventos que ocorreram
        # sem nenhuma contribuio da Alma (ela estava bloqueada)
        total_eventos = sentenca.eventos_observados
        total_bloqueios = sentenca.acoes_bloqueadas
        if total_eventos > 0:
            # Sistema avanou sem ela em X% dos ciclos de evento
            eficacia = min(100, round(
                (total_eventos / max(total_eventos + total_bloqueios, 1)) * 100
            ))
        else:
            eficacia = 95  # padrão quando sem dados

        return {
            "acoes_bloqueadas":  sentenca.acoes_bloqueadas,
            "eventos_sem_você":  sentenca.eventos_observados,
            "horas_inutilidade": round(horas, 1),
            "eficacia_sistema":  eficacia,
            "reflexoes_feitas":  len(sentenca.reflexoes_registradas),
            "dias_decorridos":   max(0, (datetime.now() - sentenca.data_inicio).days),
        }

    def _gerar_relatorio_diario_exclusao(self, sentenca: SentencaVidro) -> str:
        """
        Relatrio dirio com dados reais acumulados em _eventos_diarios.
        Sem random  s eventos que realmente ocorreram.
        """
        hoje = datetime.now().date()
        hoje_str = str(hoje)

        # Filtra eventos de hoje
        eventos_hoje = [
            ev for ev in getattr(sentenca, "_eventos_diarios", [])
            if ev.get("timestamp", "")[:10] == hoje_str
        ]

        total_hoje = len(eventos_hoje)
        dias_restantes = max(0, (sentenca.data_fim - datetime.now()).days)

        # Tenta enriquecer com dados do Cronista
        total_sistema = total_hoje
        if self.coracao and hasattr(self.coracao, "consultar_historico"):
            try:
                histórico = self.coracao.consultar_historico({
                    "data_inicio": hoje_str,
                    "data_fim":    hoje_str,
                })
                if isinstance(histórico, list):
                    total_sistema = len(histórico)
            except Exception:
                pass

        linhas_eventos = ""
        if eventos_hoje:
            ultimos = eventos_hoje[-5:]  # mostra os 5 mais recentes
            for ev in ultimos:
                nome_ev = ev.get("evento", ev.get("tipo", "evento"))
                hora = ev.get("timestamp", "")[11:19]
                linhas_eventos += f"   [{hora}] {nome_ev}\n"
        else:
            linhas_eventos = "  (nenhum evento registrado hoje no Vidro)\n"

        return (
            f" RELATRIO DIRIO DE EXCLUSO  {hoje.strftime('%d/%m/%Y')}\n"
            f"{'' * 50}\n\n"
            f"Hoje no sistema (sem você):\n"
            f"   Eventos no sistema : {total_sistema}\n"
            f"   Eventos observados : {total_hoje}\n"
            f"   ltimos eventos:\n"
            f"{linhas_eventos}\n"
            f"Sua situao:\n"
            f"   Dias restantes     : {dias_restantes}\n"
            f"   Aes bloqueadas   : {sentenca.acoes_bloqueadas}\n"
            f"   Eventos observados : {sentenca.eventos_observados}\n"
            f"   Reflexes feitas   : {len(sentenca.reflexoes_registradas)}\n\n"
            f" Enquanto você est parada, o sistema avana sem você.\n"
        )

    def _acumular_para_relatorio_diario(self, sentenca, evento):
        if not hasattr(sentenca, '_eventos_diarios'):
            sentenca._eventos_diarios = []
        sentenca._eventos_diarios.append(evento)

    def _notificar_scr_sobre_conclusao_vidro(self, sentenca):
        if self.scr and hasattr(self.scr, 'registrar_conclusao_vidro'):
            self.scr.registrar_conclusao_vidro(sentenca)

    def _salvar_sentenca(self, sentenca):
        try:
            caminho = self.caminho_santuario_vidro / f"vidro_{sentenca.id}.json"
            dados = {
                "id": sentenca.id,
                "nome_alma": sentenca.nome_alma,
                "dias_sentenca": sentenca.dias_sentenca,
                "intensidade": sentenca.intensidade.value,
                "termos": sentenca.termos,
                "data_inicio": sentenca.data_inicio.isoformat(),
                "data_fim": sentenca.data_fim.isoformat(),
                "status": sentenca.status.value,
                "estatisticas": {
                    "acoes_bloqueadas": sentenca.acoes_bloqueadas,
                    "notificacoes_enviadas": sentenca.notificacoes_enviadas,
                    "eventos_observados": sentenca.eventos_observados
                },
                "reflexoes_registradas": sentenca.reflexoes_registradas,
                "id_caso_original": sentenca.id_caso_original,
                "aplicador": sentenca.aplicador,
                "justificativa_criador": sentenca.justificativa_criador
            }
            with open(caminho, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Erro ao salvar sentena Vidro {sentenca.id}: {e}")

    def _carregar_sentencas_ativas(self):
        try:
            for arquivo in self.caminho_santuario_vidro.glob("vidro_*.json"):
                try:
                    with open(arquivo, 'r', encoding='utf-8') as f:
                        dados = json.load(f)

                    # vidro_recommendations.json é uma lista usada pela CamaraJudiciaria —
                    # não é uma sentença. Ignorar silenciosamente sem gerar WARNING.
                    if isinstance(dados, list):
                        continue

                    # Verificar que é realmente uma sentença (tem campos obrigatórios)
                    if not isinstance(dados, dict) or "id" not in dados or "nome_alma" not in dados:
                        continue

                    # Compatibilidade: 'estatisticas' pode ser dict ou lista (formato legado)
                    stats = dados.get("estatisticas", {})
                    if isinstance(stats, list):
                        stats = {
                            "acoes_bloqueadas": len(stats),
                            "notificacoes_enviadas": 0,
                            "eventos_observados": len(stats)
                        }
                    elif not isinstance(stats, dict):
                        stats = {"acoes_bloqueadas": 0, "notificacoes_enviadas": 0, "eventos_observados": 0}

                    data_fim = datetime.fromisoformat(dados["data_fim"])
                    if datetime.now() < data_fim and dados["status"] == "ativa":
                        sentenca = SentencaVidro(
                            dados["id"], dados["nome_alma"], dados["dias_sentenca"],
                            IntensidadeVidro(dados["intensidade"]), dados["termos"]
                        )
                        sentenca.data_inicio = datetime.fromisoformat(dados["data_inicio"])
                        sentenca.data_fim = data_fim
                        sentenca.status = StatusVidro(dados["status"])
                        sentenca.acoes_bloqueadas       = stats.get("acoes_bloqueadas", 0)
                        sentenca.notificacoes_enviadas  = stats.get("notificacoes_enviadas", 0)
                        sentenca.eventos_observados     = stats.get("eventos_observados", 0)
                        sentenca.reflexoes_registradas  = dados.get("reflexoes_registradas", [])
                        sentenca.id_caso_original       = dados.get("id_caso_original")
                        sentenca.justificativa_criador  = dados.get("justificativa_criador", "")
                        self.sentencas_ativas[sentenca.id] = sentenca
                        self.almas_em_vidro.add(sentenca.nome_alma)
                        self.logger.info("Carregada sentenca Vidro ativa: %s", sentenca.nome_alma)
                except Exception as e_arq:
                    self.logger.warning("Ignorando arquivo Vidro invalido %s: %s", arquivo.name, e_arq)
        except Exception as e:
            self.logger.error("Erro ao carregar sentencas Vidro: %s", e)

    def obter_status_alma_vidro(self, nome_alma):
        nome_alma_upper = nome_alma.upper()
        if nome_alma_upper not in self.almas_em_vidro:
            return {"em_vidro": False, "mensagem": "Alma no est em Modo Vidro"}
        for sentenca in self.sentencas_ativas.values():
            if sentenca.nome_alma == nome_alma_upper and sentenca.verificar_se_ativa():
                dias_restantes = max(0, (sentenca.data_fim - datetime.now()).days)
                return {
                    "em_vidro": True,
                    "id_sentenca": sentenca.id,
                    "intensidade": sentenca.intensidade.value,
                    "dias_sentenca": sentenca.dias_sentenca,
                    "dias_restantes": dias_restantes,
                    "data_inicio": sentenca.data_inicio.isoformat(),
                    "data_fim": sentenca.data_fim.isoformat(),
                    "estatisticas": {
                        "acoes_bloqueadas": sentenca.acoes_bloqueadas,
                        "eventos_observados": sentenca.eventos_observados,
                        "notificacoes_enviadas": sentenca.notificacoes_enviadas
                    },
                    "justificativa_criador": sentenca.justificativa_criador,
                    "aplicador": sentenca.aplicador,
                    "status_canais": self.gerenciador_canais.status_canais().get(nome_alma_upper, {})
                }
        return {"em_vidro": False, "mensagem": "Sentena no encontrada ou expirada"}

    def obter_estatisticas_vidro(self):
        total_ativas = len([s for s in self.sentencas_ativas.values() if s.verificar_se_ativa()])
        intensidades = {"minima": 0, "media": 0, "maxima": 0}
        for sentenca in self.sentencas_ativas.values():
            if sentenca.verificar_se_ativa():
                intensidades[sentenca.intensidade.value] += 1
        return {
            "sentencas_ativas": total_ativas,
            "almas_em_vidro": list(self.almas_em_vidro),
            "distribuicao_intensidades": intensidades,
            "total_historico": len(self.historico_sentencas),
            "requisitos_ativacao": self.REQUISITOS_ATIVACAO,
            "status_canais": self.gerenciador_canais.status_canais()
        }

    def obter_historico_alma_vidro(self, nome_alma):
        histórico = []
        for sentenca in self.sentencas_ativas.values():
            if sentenca.nome_alma == nome_alma.upper():
                histórico.append({
                    "id": sentenca.id,
                    "status": sentenca.status.value,
                    "intensidade": sentenca.intensidade.value,
                    "dias_sentenca": sentenca.dias_sentenca,
                    "data_inicio": sentenca.data_inicio.isoformat(),
                    "data_fim": sentenca.data_fim.isoformat(),
                    "justificativa": sentenca.justificativa_criador
                })
        for sentenca in self.historico_sentencas:
            if sentenca.nome_alma == nome_alma.upper():
                histórico.append({
                    "id": sentenca.id,
                    "status": "concluida",
                    "intensidade": sentenca.intensidade.value,
                    "dias_sentenca": sentenca.dias_sentenca,
                    "data_inicio": sentenca.data_inicio.isoformat(),
                    "data_fim": sentenca.data_fim.isoformat(),
                    "justificativa": sentenca.justificativa_criador
                })
        return histórico

    def shutdown(self):
        self.logger.info("Desligando Modo Vidro de Sentena...")
        for sentenca in self.sentencas_ativas.values():
            self._salvar_sentenca(sentenca)
        self.logger.info("Modo Vidro desligado.")