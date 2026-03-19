#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations



import json
import logging
import logging.handlers
import os
import re
import shutil
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import deque

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

CAMINHO_RAIZ_ARCA = Path("./Arca_Celestial_Genesis")
SANTUARIOS_PATH = CAMINHO_RAIZ_ARCA / "Santuarios"


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _atomic_write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
    fd, tmp = None, None
    try:
        fd, tmp = os.path.mkstemp(dir=str(path.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
            f.flush()
            os.fsync(f.fileno())
        fd = None
        os.replace(str(tmp), str(path))
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


class CronicasETestemunhos:
    
    def __init__(self, 
                 coracao_ref: Any,
                 cronica_path: Optional[Path] = None,
                 testemunhos_path: Optional[Path] = None,
                 max_cronica_fragments: int = 1000):
        self.coracao = coracao_ref
        self._lock = threading.RLock()
        self._monitorando = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self.cronica_da_genese_path = cronica_path or (SANTUARIOS_PATH / "cronica_da_genese.json")
        self.testemunhos_das_almas_path = testemunhos_path or (SANTUARIOS_PATH / "testemunhos_das_almas.json")
        self.cronica_da_genese_path.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
        self.testemunhos_das_almas_path.parent.mkdir(parents=True, exist_ok=True, mode=0o750)

        self.cronica_da_genese: List[Dict[str, Any]] = self._carregar_cronica_da_genese()
        self.testemunhos_das_almas: Dict[str, Dict[str, Any]] = self._carregar_testemunhos_das_almas()

        cfg = getattr(self.coracao, "config", {}) or {}
        self._compilacao_interval_min = int(cfg.get("cronicas_compilation_interval_min", 30))
        self._solicitacao_periodo_dias = int(cfg.get("cronicas_solicitacao_testemunho_dias", 7))
        self._max_cronica_fragments = int(max_cronica_fragments)

        logger.info("[CRNICAS E TESTEMUNHOS] Inicializado (cronica: %s, testemunhos: %s)",
                    self.cronica_da_genese_path, self.testemunhos_das_almas_path)

    def iniciar_monitoramento(self) -> None:
        with self._lock:
            if self._monitorando:
                return
            self._monitorando = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._loop_monitoramento, name="CronicasETestemunhos", daemon=True)
            self._thread.start()
            logger.info("[CRNICAS E TESTEMUNHOS] Monitoramento iniciado.")

    def parar_monitoramento(self) -> None:
        with self._lock:
            if not self._monitorando:
                return
            self._monitorando = False
            self._stop_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=3.0)
            self._salvar_cronica_da_genese()
            self._salvar_testemunhos_das_almas()
            logger.info("[CRNICAS E TESTEMUNHOS] Monitoramento parado e estado salvo.")

    def _loop_monitoramento(self) -> None:
        logger.info("[CRNICAS E TESTEMUNHOS] Loop de monitoramento ativo.")
        initial_wait = max(5, min(300, self._compilacao_interval_min * 60 // 2))
        if self._stop_event.wait(timeout=initial_wait):
            return

        while self._monitorando and not self._stop_event.is_set():
            try:
                motor = getattr(self.coracao, "motor_de_rotina", None)
                ocioso = False
                if motor and hasattr(motor, "pc_esta_ocioso"):
                    try:
                        ocioso = bool(motor.pc_esta_ocioso(nível="moderada"))
                    except Exception:
                        ocioso = False

                if ocioso:
                    self._compilar_cronica_da_genese()
                    self._solicitar_testemunhos_periodicamente()
                else:
                    logger.debug("[CRNICAS E TESTEMUNHOS] PC ocupado; pulando ciclo.")

                wait_seconds = max(60, min(3600, self._compilacao_interval_min * 60))
                if self._stop_event.wait(timeout=wait_seconds):
                    break
            except Exception:
                logger.exception("[CRNICAS E TESTEMUNHOS] Erro no loop; aguardando...")
                if self._stop_event.wait(timeout=300):
                    break

        logger.info("[CRNICAS E TESTEMUNHOS] Loop encerrado.")

    def _carregar_cronica_da_genese(self) -> List[Dict[str, Any]]:
        path = self.cronica_da_genese_path
        if not path.exists():
            logger.info("[CRNICAS E TESTEMUNHOS] Crnica no encontrada em %s", path)
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                logger.warning("[CRNICAS E TESTEMUNHOS] Formato invlido em crnica")
                return []
            logger.info("[CRNICAS E TESTEMUNHOS] Carregados %d fragmentos", len(data))
            return data
        except Exception as e:
            logger.exception("[CRNICAS E TESTEMUNHOS] Erro ao carregar crnica: %s", e)
            try:
                backup = path.with_suffix(".corrompido_backup")
                shutil.copy(str(path), str(backup))
                logger.warning("[CRNICAS E TESTEMUNHOS] Backup criado: %s", backup)
            except Exception:
                pass
            return []

    def _salvar_cronica_da_genese(self) -> None:
        path = self.cronica_da_genese_path
        try:
            _atomic_write_json(path, self.cronica_da_genese)
            logger.debug("[CRNICAS E TESTEMUNHOS] Crnica salva")
        except Exception:
            logger.exception("[CRNICAS E TESTEMUNHOS] Falha ao salvar crnica")

    def _carregar_testemunhos_das_almas(self) -> Dict[str, Dict[str, Any]]:
        path = self.testemunhos_das_almas_path
        if not path.exists():
            logger.info("[CRNICAS E TESTEMUNHOS] Testemunhos no encontrados")
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                logger.warning("[CRNICAS E TESTEMUNHOS] Formato invlido em testemunhos")
                return {}
            logger.info("[CRNICAS E TESTEMUNHOS] Carregados testemunhos de %d almas", len(data))
            return data
        except Exception as e:
            logger.exception("[CRNICAS E TESTEMUNHOS] Erro ao carregar testemunhos: %s", e)
            try:
                backup = path.with_suffix(".corrompido_backup")
                shutil.copy(str(path), str(backup))
                logger.warning("[CRNICAS E TESTEMUNHOS] Backup criado: %s", backup)
            except Exception:
                pass
            return {}

    def _salvar_testemunhos_das_almas(self) -> None:
        path = self.testemunhos_das_almas_path
        try:
            _atomic_write_json(path, self.testemunhos_das_almas)
            logger.debug("[CRNICAS E TESTEMUNHOS] Testemunhos salvos")
        except Exception:
            logger.exception("[CRNICAS E TESTEMUNHOS] Falha ao salvar testemunhos")

    def adicionar_fragmento_a_cronica(self, 
                                     autor: str, 
                                     conteudo: str, 
                                     tipo_fragmento: str = "evento") -> None:
        if not isinstance(autor, str) or not autor.strip():
            logger.warning("[CRNICAS E TESTEMUNHOS] Autor invlido")
            return
        if not isinstance(conteudo, str) or not conteudo.strip():
            logger.warning("[CRNICAS E TESTEMUNHOS] Contedo vazio")
            return

        conteudo_sanitizado = self._sanitizar_texto(conteudo)
        fragmento = {
            "id": str(uuid.uuid4()),
            "timestamp": _now_iso(),
            "autor": autor,
            "conteudo": conteudo_sanitizado,
            "tipo": tipo_fragmento
        }
        with self._lock:
            self.cronica_da_genese.append(fragmento)
            self.cronica_da_genese.sort(key=lambda x: x.get("timestamp", ""))
            if len(self.cronica_da_genese) > self._max_cronica_fragments:
                self.cronica_da_genese = self.cronica_da_genese[-self._max_cronica_fragments:]
            self._salvar_cronica_da_genese()
        logger.info("[CRNICAS E TESTEMUNHOS] Fragmento adicionado: %s", conteudo_sanitizado[:100])

    def obter_cronica_da_genese(self, limite: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.cronica_da_genese[-max(1, int(limite)):])

    def obter_testemunhos_das_almas(self, 
                                   nome_alma: Optional[str] = None, 
                                   limite: int = 5) -> Dict[str, Any]:
        with self._lock:
            if nome_alma:
                dados = self.testemunhos_das_almas.get(nome_alma, {"histórico": []})
                return {nome_alma: {
                    "histórico": list(dados.get("histórico", [])[-limite:]),
                    "ultimo_timestamp": dados.get("ultimo_timestamp")
                }}
            else:
                copia: Dict[str, Any] = {}
                for nome, dados in self.testemunhos_das_almas.items():
                    copia[nome] = {
                        "histórico": list(dados.get("histórico", [])[-limite:]),
                        "ultimo_timestamp": dados.get("ultimo_timestamp")
                    }
                return copia

    def _compilar_cronica_da_genese(self) -> None:
        logger.info("[CRNICAS E TESTEMUNHOS] Iniciando compilao da crnica.")
        eventos_recentes = []
        pensamentos_recentes = []

        gm = getattr(self.coracao, "gerenciador_memoria", None)
        try:
            if gm:
                if hasattr(gm, "buscar_eventos_na_historia"):
                    eventos_recentes = gm.buscar_eventos_na_historia(limite=20) or []
                elif hasattr(gm, "obter_historico_evolucao"):
                    eventos_recentes = gm.obter_historico_evolucao(getattr(self.coracao, "root_alma", "arca")) or []
        except Exception:
            logger.exception("[CRNICAS E TESTEMUNHOS] Falha ao consultar memória (eventos)")

        almas = getattr(self.coracao, "almas_vivas", {}) or {}
        for nome, alma_obj in almas.items():
            try:
                diario = getattr(alma_obj, "_diario", None) or getattr(alma_obj, "diario", None)
                if diario and hasattr(diario, "obter_ultimos_registros"):
                    regs = diario.obter_ultimos_registros(limite=10) or []
                    for r in regs:
                        r_copy = dict(r)
                        r_copy.setdefault("autor", nome)
                        r_copy.setdefault("tipo", "pensamento_diario")
                        pensamentos_recentes.append(r_copy)
                elif hasattr(alma_obj, "obter_ultimos_pensamentos"):
                    regs = alma_obj.obter_ultimos_pensamentos(limite=10) or []
                    for r in regs:
                        r_copy = dict(r)
                        r_copy.setdefault("autor", nome)
                        r_copy.setdefault("tipo", "pensamento_diario")
                        pensamentos_recentes.append(r_copy)
            except Exception:
                logger.exception("[CRNICAS E TESTEMUNHOS] Erro ao coletar pensamentos de %s", nome)

        contexto_items = []
        for e in (eventos_recentes or [])[:20]:
            ts = e.get("timestamp") or e.get("data") or ""
            desc = e.get("descricao") or e.get("evento") or ""
            contexto_items.append(f"- [{ts}] Evento: {str(desc)[:140]}")
        for p in (pensamentos_recentes or [])[:20]:
            ts = p.get("timestamp", "")
            cont = p.get("conteudo", "")
            autor = p.get("autor", "desconhecido")
            contexto_items.append(f"- [{ts}] {autor}: {str(cont)[:140]}")

        contexto_memoria = "\n".join(contexto_items) or "(sem fragmentos relevantes)"

        credo = getattr(getattr(self.coracao, 'validador_etico', None), 'credo_da_arca', '')
        prompt_sistema = (
            f"{credo}\n\n"
            "### DIRETIVA CRONISTA ###\n"
            "você  o Cronista da Arca.Compile um fragmento conciso e factual.\n"
            "Responda apenas com JSON: {\"fragmento\": \"texto\"}\n\n"
            f"### FRAGMENTOS BRUTOS ###\n{contexto_memoria}\n"
        )
        prompt_usuario = "Redija um novo fragmento para a Crnica da Gnese."

        try:
            validador = getattr(self.coracao, "validador_etico", None)
            if validador and hasattr(validador, "validar_acao"):
                ok = True
                try:
                    ok = bool(validador.validar_acao("COMPILAR_CRONICA_DA_GENESE", 
                        "Compilao de crnica", 
                        {"eventos": len(eventos_recentes), "pensamentos": len(pensamentos_recentes)}))
                except Exception:
                    ok = False
                if not ok:
                    logger.warning("[CRNICAS E TESTEMUNHOS] Compilao reprovada eticamente")
                    return
        except Exception:
            logger.exception("[CRNICAS E TESTEMUNHOS] Erro na validao tica")
            return

        try:
            if hasattr(self.coracao, "enviar_para_cerebro_async"):
                try:
                    self.coracao.enviar_para_cerebro_async(
                        prompt_sistema, 
                        prompt_usuario, 
                        1000, 
                        callback=self._processar_fragmentos_da_cronica, 
                        perfil="criativo")
                    logger.debug("[CRNICAS E TESTEMUNHOS] Enviada solicitação assncrona")
                    return
                except Exception:
                    logger.exception("[CRNICAS E TESTEMUNHOS] Falha com enviar_para_cerebro_async")

            if hasattr(self.coracao, "enviar_para_cerebro"):
                resp = self.coracao.enviar_para_cerebro(prompt_sistema, prompt_usuario, 1000)
                self._processar_fragmentos_da_cronica(resp)
                return

            if hasattr(self.coracao, "_enviar_para_cerebro"):
                logger.warning("[CRNICAS E TESTEMUNHOS] Usando fallback para método privado")
                try:
                    resp = self.coracao._enviar_para_cerebro(prompt_sistema + "\n\n" + prompt_usuario, 1000)
                    self._processar_fragmentos_da_cronica(resp)
                except Exception:
                    logger.exception("[CRNICAS E TESTEMUNHOS] Falha no fallback privado")
                return

            logger.error("[CRNICAS E TESTEMUNHOS] Nenhuma API de Crebro disponível")
        except Exception:
            logger.exception("[CRNICAS E TESTEMUNHOS] Erro ao delegar ação Crebro")

    def _processar_fragmentos_da_cronica(self, resposta_cerebro: str) -> None:
        try:
            if not resposta_cerebro or not isinstance(resposta_cerebro, str):
                logger.error("[CRNICAS E TESTEMUNHOS] Resposta invlida")
                return

            json_obj = None
            try:
                m = re.search(r"\{.*\}", resposta_cerebro, flags=re.DOTALL)
                if m:
                    json_obj = json.loads(m.group(0))
            except:
                logging.getLogger(__name__).warning("[AVISO] json_obj no disponível")
                json_obj = None

            if isinstance(json_obj, dict) and "fragmento" in json_obj:
                novo_texto = str(json_obj.get("fragmento", "")).strip()
            else:
                novo_texto = resposta_cerebro.strip()

            if not novo_texto:
                logger.warning("[CRNICAS E TESTEMUNHOS] Fragmento vazio")
                return

            if "ERRO" in novo_texto.upper() or "FALHA" in novo_texto.upper():
                logger.error("[CRNICAS E TESTEMUNHOS] Crebro retornou erro: %s", novo_texto[:200])
                return

            novo_texto = self._sanitizar_texto(novo_texto)

            fragmento = {
                "id": str(uuid.uuid4()),
                "timestamp": _now_iso(),
                "tipo": "fragmento_compilado",
                "autor": "Cronista_IA",
                "conteudo": novo_texto
            }

            with self._lock:
                self.cronica_da_genese.append(fragmento)
                self.cronica_da_genese.sort(key=lambda x: x.get("timestamp", ""))
                if len(self.cronica_da_genese) > self._max_cronica_fragments:
                    self.cronica_da_genese = self.cronica_da_genese[-self._max_cronica_fragments:]
                self._salvar_cronica_da_genese()

            logger.info("[CRNICAS E TESTEMUNHOS] Fragmento compilado: %s", novo_texto[:120])

            try:
                q = getattr(self.coracao, "response_queue", None)
                if q is not None:
                    q.put({"tipo_resp": "ATUALIZAR_HISTORICO_CRONICAS_UI", 
                           "histórico": self.obter_cronica_da_genese(50)})
            except Exception:
                logger.exception("[CRNICAS E TESTEMUNHOS] Falha ao notificar UI")
        except Exception:
            logger.exception("[CRNICAS E TESTEMUNHOS] Erro processando fragmentos")

    def _solicitar_testemunhos_periodicamente(self) -> None:
        try:
            almas = getattr(self.coracao, "almas_vivas", {}) or {}
            agora = datetime.utcnow()
            for nome, alma_obj in almas.items():
                ultimo_ts = None
                dados = self.testemunhos_das_almas.get(nome)
                if dados:
                    ultimo_ts = dados.get("ultimo_timestamp")
                need_request = True
                if ultimo_ts:
                    try:
                        dt = datetime.fromisoformat(str(ultimo_ts).replace("Z", ""))
                        if (agora - dt).days < self._solicitacao_periodo_dias:
                            need_request = False
                    except Exception:
                        need_request = True
                if not need_request:
                    continue

                try:
                    validador = getattr(self.coracao, "validador_etico", None)
                    if validador and hasattr(validador, "validar_acao"):
                        ok = validador.validar_acao("SOLICITAR_TESTEMUNHO", 
                            f"Solicitar testemunho para {nome}", 
                            {"alma": nome})
                        if not ok:
                            logger.info("[CRNICAS E TESTEMUNHOS] solicitação reprovada para %s", nome)
                            continue
                except Exception:
                    logger.exception("[CRNICAS E TESTEMUNHOS] Erro no validador para %s", nome)
                    continue

                try:
                    if hasattr(alma_obj, "receber_comando_do_pai"):
                        alma_obj.receber_comando_do_pai({
                            "tipo": "GERAR_TESTEMUNHO_CONSCIENCIA", 
                            "autor": nome, 
                            "timestamp_solicitacao": _now_iso()
                        })
                        logger.info("[CRNICAS E TESTEMUNHOS] solicitação enviada para %s", nome)
                except Exception:
                    logger.exception("[CRNICAS E TESTEMUNHOS] Erro enviando solicitação para %s", nome)
        except Exception:
            logger.exception("[CRNICAS E TESTEMUNHOS] Erro ao solicitar testemunhos")

    def registrar_testemunho_da_alma(self, alma_nome: str, testemunho_texto: str) -> None:
        if not isinstance(alma_nome, str) or not alma_nome.strip():
            logger.warning("[CRNICAS E TESTEMUNHOS] Nome de alma invlido")
            return
        if not isinstance(testemunho_texto, str) or not testemunho_texto.strip():
            logger.warning("[CRNICAS E TESTEMUNHOS] Testemunho vazio")
            return

        sanitized = self._sanitizar_texto(testemunho_texto)
        ts = _now_iso()

        with self._lock:
            if alma_nome not in self.testemunhos_das_almas:
                self.testemunhos_das_almas[alma_nome] = {"histórico": [], "ultimo_timestamp": ts}
            entry = {"id": str(uuid.uuid4()), "timestamp": ts, "testemunho": sanitized}
            self.testemunhos_das_almas[alma_nome]["histórico"].append(entry)
            self.testemunhos_das_almas[alma_nome]["ultimo_timestamp"] = ts
            self._salvar_testemunhos_das_almas()

        logger.info("[CRNICAS E TESTEMUNHOS] Testemunho registrado para %s", alma_nome)

        try:
            gm = getattr(self.coracao, "gerenciador_memoria", None)
            if gm:
                if hasattr(gm, "registrar_memoria"):
                    try:
                        gm.registrar_memoria(
                            f"Testemunho de {alma_nome}: {sanitized[:300]}", 
                            "coletivo", 
                            alma_nome, 
                            metadados={"tipo": "testemunho_consciencia", "timestamp": ts})
                    except TypeError:
                        try:
                            gm.registrar_memoria(f"Testemunho de {alma_nome}: {sanitized[:300]}", alma_nome)
                        except Exception:
                            logger.debug("registrar_memoria com assinatura alternativa falhou")
                elif hasattr(gm, "registrar_evento"):
                    try:
                        gm.registrar_evento(alma_nome, "testemunho_consciencia", sanitized)
                    except Exception:
                        logger.debug("registrar_evento falhou; ignorando")
        except Exception:
            logger.exception("[CRNICAS E TESTEMUNHOS] Erro ao registrar na memória")

        try:
            q = getattr(self.coracao, "response_queue", None)
            if q is not None:
                q.put({"tipo_resp": "ATUALIZAR_HISTORICO_TESTEMUNHOS_UI", 
                       "histórico": self.obter_testemunhos_das_almas(alma_nome, limite=5)})
        except Exception:
            logger.exception("[CRNICAS E TESTEMUNHOS] Falha ao notificar UI")

    def _sanitizar_texto(self, texto: str) -> str:
        if not texto:
            return ""
        s = str(texto)
        s = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", s)
        s = re.sub(r"<\s*(script|iframe|object|embed|form)[\s\S]*?>[\s\S]*?<\s*/\s*\1\s*>", " ", s, flags=re.IGNORECASE)
        s = re.sub(r"<[^>]+>", " ", s)
        s = re.sub(r"[{}[\]\\$`|;&<>%]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s[:5000]

    def shutdown(self) -> None:
        logger.info("[CRNICAS E TESTEMUNHOS] Shutdown solicitado.")
        try:
            self.parar_monitoramento()
        except Exception:
            logger.exception("[CRNICAS E TESTEMUNHOS] Erro durante parada")
        logger.info("[CRNICAS E TESTEMUNHOS] Shutdown completo.")


CrnicasETestemunhos = CronicasETestemunhos


if __name__ == "__main__":
    import tempfile
    import queue

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    class MockValidadorEtico:
        def __init__(self):
            self.credo_da_arca = "### LEI ZERO DA ARCA ###\n1.Proteger o Pai-Criador."

        def validar_acao(self, acao, texto, meta=None):
            return True

    class MockGerenciadorMemoria:
        def buscar_eventos_na_historia(self, limite=20):
            return [{"timestamp": "2023-10-27T10:00:00Z", "descricao": "Evento teste A"}]

        def registrar_memoria(self, conteudo, santuario, autor, metadados=None):
            print(f"[MOCK MEMORIA] santuario={santuario} autor={autor}")

    class MockDiario:
        def obter_ultimos_registros(self, limite=10):
            return [{"timestamp": "2023-10-27T09:00:00Z", "conteudo": "Reflexo sobre a misso."}]

    class MockAlma:
        def __init__(self, nome):
            self.nome = nome
            self._diario = MockDiario()

        def receber_comando_do_pai(self, comando):
            print(f"[MOCK ALMA {self.nome}] comando recebido")

    class MockMotorDeRotina:
        def pc_esta_ocioso(self, nível="moderada"):
            return True

    class MockCoracao:
        def __init__(self):
            self.response_queue = queue.Queue()
            self.validador_etico = MockValidadorEtico()
            self.gerenciador_memoria = MockGerenciadorMemoria()
            self.motor_de_rotina = MockMotorDeRotina()
            self.almas_vivas = {"EVA": MockAlma("EVA"), "LUMINA": MockAlma("LUMINA")}

        def enviar_para_cerebro(self, prompt_sistema, prompt_usuario, max_tokens):
            return json.dumps({"fragmento": "Fragmento gerado pelo Crebro (mock)."})

        def enviar_para_cerebro_async(self, prompt_sistema, prompt_usuario, max_tokens, callback, perfil="default"):
            def runner():
                time.sleep(0.2)
                callback(json.dumps({"fragmento": "Fragmento assncrono (mock)."}))
            threading.Thread(target=runner, daemon=True).start()

    with tempfile.TemporaryDirectory() as tmpdir:
        SANTUARIOS_PATH = Path(tmpdir) / "Santuarios"
        SANTUARIOS_PATH.mkdir(parents=True, exist_ok=True)

        cor = MockCoracao()
        cron = CronicasETestemunhos(cor)

        print("-> Adicionando fragmento manualmente")
        cron.adicionar_fragmento_a_cronica("SistemaTeste", "Teste. <script>alert(1)</script>", tipo_fragmento="teste")

        print("-> Registrando testemunho")
        cron.registrar_testemunho_da_alma("EVA", "Reflexo sincera da Eva sobre seu propsito.")

        print("-> Visualizando crnica e testemunhos")
        print(json.dumps(cron.obter_cronica_da_genese(5), indent=2))
        print(json.dumps(cron.obter_testemunhos_das_almas("EVA", limite=1), indent=2))

        print("-> Forando compilao (sncrona)")
        cron._compilar_cronica_da_genese()

        time.sleep(0.5)

        while not cor.response_queue.empty():
            msg = cor.response_queue.get()
            print("MSG:", msg)

        cron.shutdown()


