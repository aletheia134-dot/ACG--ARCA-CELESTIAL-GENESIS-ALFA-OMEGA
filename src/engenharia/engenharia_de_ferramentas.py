from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
import logging
import os
import re
import secrets
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CAMINHO_RAIZ_ARCA = Path("./Arca_Celestial_Genesis")
LABORATORIO_OFICINA_PATH = CAMINHO_RAIZ_ARCA / "Laboratorio_Oficina"
FERRAMENTAS_INSTALADAS_PATH = CAMINHO_RAIZ_ARCA / "Ferramentas_Instaladas"
LIMIAR_OCIOSIDADE_MODERADA = 300

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class EngenhariaDeFerramentas:
    def __init__(self, coracao_ref: Any):
        self.coracao = coracao_ref
        self.logger = logging.getLogger(self.__class__.__name__)
        self._validate_coracao()

        self._monitorando = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self.propostas_ferramentas_pendentes: Dict[str, Dict[str, Any]] = {}
        self.ferramentas_instaladas: Dict[str, Dict[str, Any]] = {}
        self.ferramentas_dinamicas: Dict[str, Dict[str, Any]] = {}

        LABORATORIO_OFICINA_PATH.mkdir(parents=True, exist_ok=True, mode=0o750)
        FERRAMENTAS_INSTALADAS_PATH.mkdir(parents=True, exist_ok=True, mode=0o750)

        try:
            self.ferramentas_instaladas = self._carregar_ferramentas_instaladas()
        except Exception:
            self.logger.exception("Falha ao carregar ferramentas instaladas; iniciando vazio.")
            self.ferramentas_instaladas = {}

        self._lock = threading.RLock()

        self.logger.info("EngenhariaDeFerramentas inicializada (integrada com GerenciadorPropostas)")

    def _validate_coracao(self) -> None:
        missing = []
        if not hasattr(self.coracao, "motor_de_rotina") or not self.coracao.motor_de_rotina:
            missing.append("motor_de_rotina")
        if not hasattr(self.coracao, "almas_vivas") or not self.coracao.almas_vivas:
            missing.append("almas_vivas")
        if not hasattr(self.coracao, "observador_reino_digital") or not self.coracao.observador_reino_digital:
            missing.append("observador_reino_digital")
        if not hasattr(self.coracao, "processar_proposta_interna") or not callable(getattr(self.coracao, "processar_proposta_interna")):
            missing.append("processar_proposta_interna")
        if not hasattr(self.coracao, "response_queue") or not getattr(self.coracao, "response_queue"):
            missing.append("response_queue")
        if not hasattr(self.coracao, "pc_control_manager") or not getattr(self.coracao, "pc_control_manager"):
            missing.append("pc_control_manager")
        if not hasattr(self.coracao, "gerenciador_memoria") or not getattr(self.coracao, "gerenciador_memoria"):
            missing.append("gerenciador_memoria")
        if not hasattr(self.coracao, "gerenciador_propostas") or not getattr(self.coracao, "gerenciador_propostas"):
            missing.append("gerenciador_propostas")
        if missing:
            raise RuntimeError(f"Coracao inválido — faltando componentes: {missing}")

    def iniciar_monitoramento(self) -> None:
        if self._monitorando:
            return
        self._monitorando = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop_monitoramento, daemon=True, name="EngenhariaDeFerramentas")
        self._thread.start()
        self.logger.info("Monitoramento iniciado")

    def parar_monitoramento(self) -> None:
        if not self._monitorando:
            return
        self._monitorando = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._salvar_ferramentas_instaladas()
        self.logger.info("Monitoramento parado e estado salvo")

    def _loop_monitoramento(self) -> None:
        self.logger.debug("Loop de monitoramento iniciado")
        time.sleep(secrets.SystemRandom().randint(60, 180))
        while self._monitorando and not self._stop_event.is_set():
            try:
                motor = getattr(self.coracao, "motor_de_rotina", None)
                if motor and motor.pc_esta_ocioso(nivel="moderada"):
                    self._revisar_ferramentas_existentes()
                else:
                    self.logger.debug("PC em uso; pulando revisão de ferramentas")
                if self._stop_event.wait(timeout=secrets.SystemRandom().randint(300, 900)):
                    break
            except Exception:
                self.logger.exception("Erro no loop de monitoramento; aguardando antes de continuar")
                time.sleep(300)
        self.logger.debug("Loop de monitoramento finalizado")

    def _carregar_ferramentas_instaladas(self) -> Dict[str, Any]:
        path = FERRAMENTAS_INSTALADAS_PATH / "ferramentas_instaladas.json"
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                self.logger.warning("Formato inesperado em ferramentas_instaladas.json — reinicializando")
                return {}
            return data
        except Exception:
            try:
                backup = path.with_suffix(".corrompido_backup")
                shutil.copy(str(path), str(backup))
                self.logger.warning("Arquivo corrompido movido para backup: %s", backup)
            except Exception:
                self.logger.exception("Falha ao criar backup do arquivo corrompido")
            return {}

    def _salvar_ferramentas_instaladas(self) -> None:
        path = FERRAMENTAS_INSTALADAS_PATH / "ferramentas_instaladas.json"
        try:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.ferramentas_instaladas, f, indent=2, ensure_ascii=False, default=str)
            os.replace(str(tmp), str(path))
        except Exception:
            self.logger.exception("Falha ao salvar ferramentas instaladas")

    def _revisar_ferramentas_existentes(self) -> None:
        try:
            if secrets.SystemRandom().random() >= 0.01:
                return
            almas = list(self.coracao.almas_vivas.keys())
            if not almas:
                return
            alma_refletora = secrets.SystemRandom().choice(almas)
            self.logger.info("Alma %s refletindo sobre ferramentas", alma_refletora)

            observacoes = []
            obs_mgr = getattr(self.coracao, "observador_reino_digital", None)
            if obs_mgr:
                try:
                    observacoes = obs_mgr.obter_observacoes_recentes(limite=3)
                except Exception:
                    self.logger.debug("Falha ao obter observações recentes (continuando)")

            prompt_sistema = (
                f"{getattr(self.coracao, 'validador_etico', {}).credo_da_arca if hasattr(getattr(self.coracao, 'validador_etico', None), 'credo_da_arca') else ''}\n\n"
                f"Persona: {getattr(self.coracao.almas_vivas[alma_refletora], 'config_personalidade', {}).get('identidade_llm', '')}\n\n"
                f"Ferramentas instaladas: {list(self.ferramentas_instaladas.keys())}\nObservações recentes: {observacoes}\n\n"
                "Responda apenas com JSON contendo: nome_acao, descricao_acao, categoria, tipo_ferramenta, comando_ou_codigo, explicacao_proposito."
            )
            if hasattr(self.coracao, "_enviar_para_cerebro") and callable(self.coracao._enviar_para_cerebro):
                try:
                    resposta = self.coracao._enviar_para_cerebro(prompt_sistema, "Proponha ferramenta", 800)
                    proposta = json.loads(resposta)
                    required_keys = {"nome_acao", "descricao_acao", "categoria", "tipo_ferramenta", "comando_ou_codigo", "explicacao_proposito"}
                    if isinstance(proposta, dict) and required_keys.issubset(proposta.keys()):
                        self.propor_nova_ferramenta(
                            nome_ferramenta=proposta["nome_acao"],
                            descricao=proposta["descricao_acao"],
                            autor=alma_refletora,
                            categoria=proposta["categoria"],
                            tipo=proposta["tipo_ferramenta"],
                            comando_ou_codigo=proposta["comando_ou_codigo"],
                            explicacao_proposito=proposta["explicacao_proposito"],
                        )
                    else:
                        self.logger.warning("Proposta inválida do cérebro: %s", resposta)
                except Exception:
                    self.logger.exception("Erro ao processar proposta gerada pelo cérebro")
            else:
                self.logger.debug("_enviar_para_cerebro não disponível; pulando geração automática")
        except Exception:
            self.logger.exception("Erro durante revisão automática de ferramentas")

    def propor_nova_ferramenta(self, nome_ferramenta: str, descricao: str, autor: str, categoria: str, tipo: str, comando_ou_codigo: str, explicacao_proposito: str) -> str:
        gerenciador = getattr(self.coracao, "gerenciador_propostas", None)
        if gerenciador:
            sucesso, msg, proposta_id = gerenciador.criar_proposta(
                ia_solicitante=autor,
                nome_ferramenta=nome_ferramenta,
                descricao=descricao,
                motivo="Proposta automática via EngenhariaDeFerramentas",
                intencao_uso=explicacao_proposito,
                categoria=categoria,
                tipo_ferramenta=tipo,
                codigo_ou_comando=comando_ou_codigo
            )
            if sucesso:
                self.logger.info("Proposta delegada ao GerenciadorPropostas: %s", proposta_id)
                return proposta_id
            else:
                self.logger.warning("Falha ao delegar proposta: %s", msg)
        else:
            self.logger.error("GerenciadorPropostas não disponível; usando modo legado")
            proposta_id = str(uuid.uuid4())
            proposta = {
                "id": proposta_id,
                "tipo": "PROPOR_NOVA_FERRAMENTA",
                "autor": autor,
                "nome_acao": nome_ferramenta,
                "descricao_acao": descricao,
                "categoria": categoria,
                "tipo_ferramenta": tipo,
                "comando_ou_codigo": comando_ou_codigo,
                "explicacao_proposito": explicacao_proposito,
                "timestamp": datetime.datetime.now().isoformat(),
                "status": "PENDENTE"
            }
            with self._lock:
                self.propostas_ferramentas_pendentes[proposta_id] = proposta
            try:
                self.coracao.processar_proposta_interna(proposta, alvo_ui="Oficina")
            except Exception:
                self.logger.exception("Erro ao encaminhar proposta ao coracao")
            self.logger.info("Proposta registrada (modo legado): %s por %s", nome_ferramenta, autor)
            return proposta_id

    def instalar_ferramenta_aprovada(self, proposta_id: str) -> bool:
        gerenciador = getattr(self.coracao, "gerenciador_propostas", None)
        if gerenciador:
            proposta = gerenciador.obter_proposta(proposta_id)
            if not proposta:
                self.logger.warning("Proposta %s não encontrada no GerenciadorPropostas", proposta_id)
                return False
            if proposta.get("status") != "PRONTO_APROVACAO_FINAL":
                self.logger.warning("Proposta %s não está pronta para deploy (status: %s)", proposta_id, proposta.get("status"))
                return False
            sucesso, msg = gerenciador.aprovar_deploy(proposta_id, "Sistema (EngenhariaDeFerramentas)", "Instalação automática")
            if not sucesso:
                self.logger.warning("Falha ao aprovar deploy: %s", msg)
                return False
        else:
            with self._lock:
                proposta = self.propostas_ferramentas_pendentes.pop(proposta_id, None)
            if not proposta:
                self.logger.warning("Proposta %s não encontrada (modo legado)", proposta_id)
                return False

        tipo = proposta.get("tipo_ferramenta")
        if tipo == "script_python_dinamico":
            return self._instalar_script_dinamico(proposta)
        else:
            return self._instalar_comando_sistema(proposta)

    def _instalar_script_dinamico(self, proposta: Dict[str, Any]) -> bool:
        nome = proposta.get("nome_acao", "<sem_nome>")
        codigo = proposta.get("comando_ou_codigo", "")
        autor = proposta.get("autor", "desconhecido")

        self.logger.info("Instalando script dinâmico: %s", nome)

        if not self._validar_codigo_dinamico(codigo):
            msg = f"Código bloqueado por políticas de segurança: {nome}"
            self.logger.error(msg)
            try:
                self.coracao.response_queue.put({"tipo_resp": "LOG_REINO", "texto": msg})
            except Exception:
                self.logger.debug("Não foi possível notificar via response_queue")
            return False

        ferramenta_id = proposta.get("id", str(uuid.uuid4()))
        module_name = f"ferramenta_{re.sub(r'[^0-9a-zA-Z_]', '_', ferramenta_id)}"

        safe_builtins = {
            "abs": abs, "min": min, "max": max, "sum": sum, "len": len, "range": range,
            "enumerate": enumerate, "sorted": sorted, "round": round, "str": str, "int": int, "float": float,
            "bool": bool, "list": list, "dict": dict, "set": set, "tuple": tuple, "print": print
        }
        module_globals: Dict[str, Any] = {"__name__": module_name, "__builtins__": safe_builtins}

        try:
            compile(codigo, f"<{module_name}>", "exec")
        except SyntaxError as e:
            self.logger.error("Erro de sintaxe no código dinâmico: %s", e)
            return False

        try:
            exec(codigo, module_globals)
            executar = module_globals.get("executar") or module_globals.get("main")
            if not callable(executar):
                self.logger.error("Função de entrada 'executar' (ou 'main') não encontrada no código dinâmico")
                return False

            with self._lock:
                self.ferramentas_dinamicas[nome] = {"id": ferramenta_id, "funcao": executar, "autor": autor}
                self.ferramentas_instaladas[nome] = {
                    "id": ferramenta_id,
                    "descricao": proposta.get("descricao_acao", ""),
                    "autor": autor,
                    "tipo": proposta.get("tipo_ferramenta", "script_python_dinamico"),
                    "categoria": proposta.get("categoria", ""),
                    "data_instalacao": datetime.datetime.now().isoformat(),
                    "status": "instalada",
                    "uso_contador": 0,
                    "ultima_utilizacao": None,
                    "exemplos_uso": []
                }
            self._salvar_ferramentas_instaladas()
            msg = f"Ferramenta dinâmica '{nome}' instalada em memória"
            self.logger.info(msg)
            try:
                self.coracao.response_queue.put({"tipo_resp": "LOG_REINO", "texto": msg})
            except Exception:
                self.logger.debug("Falha ao notificar via response_queue (ignorado)")
            try:
                self.coracao.gerenciador_memoria.registrar_memoria(msg, "coletivo", "EngenhariaDeFerramentas")
            except Exception:
                self.logger.debug("Falha ao registrar memória (ignorado)")
            return True
        except Exception:
            self.logger.exception("Erro ao executar/instalar código dinâmico")
            try:
                self.coracao.response_queue.put({"tipo_resp": "LOG_REINO", "texto": f"[ERRO] Falha ao instalar script '{nome}'"})
            except Exception:
                pass
            return False

    def _validar_codigo_dinamico(self, codigo: str) -> bool:
        if not isinstance(codigo, str) or not codigo.strip():
            return False
        proibidos_pattern = re.compile(
            r"\b(import|exec|eval|compile|open|__import__|subprocess|socket|ctypes|mmap|shutil|os\.|sys\.|requests|urllib|pickle|yaml|marshal)\b",
            flags=re.IGNORECASE,
        )
        if proibidos_pattern.search(codigo):
            self.logger.warning("Código contém token proibido")
            return False
        if len(codigo) > 50_000:
            self.logger.warning("Código demasiado grande (bloqueado)")
            return False
        try:
            compile(codigo, "<codigo_dinamico>", "exec")
        except Exception as e:
            self.logger.warning("Código dinâmico não compilou: %s", e)
            return False
        return True

    def _instalar_comando_sistema(self, proposta: Dict[str, Any]) -> bool:
        nome = proposta.get("nome_acao", "<sem_nome>")
        comando = proposta.get("comando_ou_codigo", "")
        autor = proposta.get("autor", "desconhecido")

        self.logger.info("Instalando comando de sistema: %s", nome)
        comando_sanitizado = self._sanitizar_comando_instalacao(comando)
        if not comando_sanitizado:
            self.logger.error("Comando de instalação bloqueado por sanitização")
            try:
                self.coracao.response_queue.put({"tipo_resp": "LOG_REINO", "texto": f"[ERRO] Comando bloqueado para '{nome}'"})
            except Exception:
                pass
            return False

        pc_ctrl = getattr(self.coracao, "pc_control_manager", None)
        if not pc_ctrl:
            self.logger.error("PCControlManager ausente; não é possível executar comando de sistema")
            return False

        try:
            resultado = pc_ctrl.executar_acao_controlada(
                nome_acao=f"Instalar Ferramenta: {nome}",
                comando_script=comando_sanitizado,
                autor=f"EngenhariaDeFerramentas:{autor}"
            )
        except Exception:
            self.logger.exception("Erro ao pedir execução ao PCControlManager")
            return False

        if resultado.get("sucesso"):
            with self._lock:
                self.ferramentas_instaladas[nome] = {
                    "id": proposta.get("id", str(uuid.uuid4())),
                    "descricao": proposta.get("descricao_acao", ""),
                    "autor": autor,
                    "tipo": proposta.get("tipo_ferramenta", "comando_sistema"),
                    "categoria": proposta.get("categoria", ""),
                    "data_instalacao": datetime.datetime.now().isoformat(),
                    "status": "instalada",
                    "uso_contador": 0,
                    "ultima_utilizacao": None,
                    "exemplos_uso": []
                }
            self._salvar_ferramentas_instaladas()
            try:
                self.coracao.response_queue.put({"tipo_resp": "LOG_REINO", "texto": f"Ferramenta '{nome}' instalada com sucesso"})
            except Exception:
                pass
            try:
                self.coracao.gerenciador_memoria.registrar_memoria(f"Ferramenta '{nome}' instalada por {autor}.", "coletivo", "EngenhariaDeFerramentas")
            except Exception:
                pass
            return True
        else:
            erro = resultado.get("erro", "desconhecido")
            try:
                self.coracao.response_queue.put({"tipo_resp": "LOG_REINO", "texto": f"Falha ao instalar '{nome}': {erro}"})
            except Exception:
                pass
            try:
                self.coracao.gerenciador_memoria.registrar_memoria(f"Falha ao instalar '{nome}': {erro}", "coletivo", "EngenhariaDeFerramentas")
            except Exception:
                pass
            return False

    def _sanitizar_comando_instalacao(self, comando: str) -> Optional[str]:
        if not isinstance(comando, str) or not comando.strip():
            return None
        sanitizado = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", comando).strip()
        perigosos = [
            r";", r"\|\|", r"&&", r"\|", r"`", r"\$\(.*\)", r"rm\s+-rf", r"rm\s+-r", r"sudo\s+rm", r"del\s+/s", r"format\s+", r"mkfs", r"chown\s+", r"chmod\s+"
        ]
        for p in perigosos:
            if re.search(p, sanitizado, flags=re.IGNORECASE):
                self.logger.warning("Comando bloqueado por padrão perigoso: %s", p)
                return None
        if len(sanitizado) > 2000:
            self.logger.warning("Comando muito longo; bloqueado")
            return None
        allowed_prefixes = ["apt ", "apt-get ", "pip ", "python -m pip ", "yum ", "dnf ", "brew "]
        lower = sanitizado.lower()
        if not any(lower.startswith(pref) for pref in allowed_prefixes):
            self.logger.warning("Comando não começa com prefixo de instalação seguro")
            return None
        return sanitizado

    def executar_ferramenta(self, nome_ferramenta: str, parametros: Optional[Dict[str, Any]] = None) -> Tuple[bool, Any]:
        with self._lock:
            if nome_ferramenta not in self.ferramentas_instaladas:
                return False, "Ferramenta não encontrada"

            meta = self.ferramentas_instaladas[nome_ferramenta]

            if meta.get("tipo") == "script_python_dinamico":
                dyn = self.ferramentas_dinamicas.get(nome_ferramenta)
                if not dyn:
                    return False, "Implementação dinâmica não encontrada em memória"
                func = dyn.get("funcao")
                try:
                    resultado = func(**(parametros or {}))
                    self.registrar_uso(nome_ferramenta)
                    return True, resultado
                except Exception:
                    self.logger.exception("Erro ao executar ferramenta dinâmica %s", nome_ferramenta)
                    return False, "Erro ao executar ferramenta dinâmica"
            else:
                pc = getattr(self.coracao, "pc_control_manager", None)
                if not pc:
                    return False, "PCControlManager não disponível"
                nome_acao = f"Executar Ferramenta: {nome_ferramenta}"
                try:
                    resultado = pc.executar_acao_controlada(nome_acao=nome_acao, comando_script=None, autor="EngenhariaDeFerramentas", parametros=parametros or {})
                    if resultado.get("sucesso"):
                        self.registrar_uso(nome_ferramenta)
                        return True, resultado.get("saida", None)
                    else:
                        return False, resultado.get("erro", "Erro na execução remota")
                except Exception:
                    self.logger.exception("Erro solicitando execução ao PCControlManager")
                    return False, "Erro ao executar via PCControlManager"

    def registrar_uso(self, nome_ferramenta: str) -> bool:
        with self._lock:
            meta = self.ferramentas_instaladas.get(nome_ferramenta)
            if not meta:
                return False
            meta["uso_contador"] = int(meta.get("uso_contador", 0)) + 1
            meta["ultima_utilizacao"] = datetime.datetime.now().isoformat()
            self._salvar_ferramentas_instaladas()
            return True

    def adicionar_exemplo_uso(self, nome_ferramenta: str, exemplo: str, resultado: str) -> bool:
        with self._lock:
            meta = self.ferramentas_instaladas.get(nome_ferramenta)
            if not meta:
                return False
            meta.setdefault("exemplos_uso", [])
            meta["exemplos_uso"].append({"exemplo": exemplo, "resultado": resultado, "timestamp": datetime.datetime.now().isoformat()})
            meta["exemplos_uso"] = meta["exemplos_uso"][-10:]
            self._salvar_ferramentas_instaladas()
            return True

    def buscar_ferramenta(self, query: str) -> List[Dict[str, Any]]:
        query_l = query.lower()
        resultados = []
        with self._lock:
            for nome, meta in self.ferramentas_instaladas.items():
                if query_l in nome.lower() or query_l in meta.get("descricao", "").lower() or query_l in meta.get("categoria", "").lower():
                    resultados.append({nome: meta})
        return resultados

    def estatisticas_ferramentas(self) -> Dict[str, Any]:
        with self._lock:
            stats: Dict[str, Any] = {"total": len(self.ferramentas_instaladas), "por_categoria": {}, "mais_usadas": []}
            for nome, meta in self.ferramentas_instaladas.items():
                cat = meta.get("categoria", "sem_categoria")
                stats["por_categoria"][cat] = stats["por_categoria"].get(cat, 0) + 1
            ordenadas = sorted(self.ferramentas_instaladas.items(), key=lambda kv: kv[1].get("uso_contador", 0), reverse=True)
            stats["mais_usadas"] = [ {"nome": n, **m} for n, m in ordenadas[:10] ]
        return stats

    def obter_ferramentas_instaladas(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self.ferramentas_instaladas)

    def shutdown(self) -> None:
        self.logger.info("ðŸ›‘ Desligando EngenhariaDeFerramentas...")
        self.parar_monitoramento()
        self.logger.info("âœ… EngenhariaDeFerramentas desligada")
