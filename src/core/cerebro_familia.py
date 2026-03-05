#!/usr/bin/env python3
from __future__ import annotations
from src.diagnostico.erros import LLMTimeoutError, LLMUnavailableError, LLMExecutionError, MemoriaIndisponivelError, DryRunError, PlaceholderError
# -*- coding: utf-8 -*-
import logging
import threading
import time
import concurrent.futures
import random
import os
import uuid
from typing import Dict, List, Any, Optional

from src.utils.config_utils import (
    cfg_get as _cfg_get,
    cfg_get_bool as _cfg_get_bool,
    cfg_get_int as _cfg_get_int,
    cfg_get_float as _cfg_get_float,
)

from src.core.autonomy_state import AutonomyState
from src.core.desires import generate_desire, evaluate_proposal, execute_desire

try:
    from src.memoria.sistema_memoria import SistemaMemoriaHibrido, TipoInteracao  # type: ignore
    IMPORT_MEMORIA = True
except:
    logging.getLogger(__name__).warning("âš ï¸ SistemaMemoriaHibrido não disponível")
    SistemaMemoriaHibrido = None
    TipoInteracao = None
    IMPORT_MEMORIA = False

logger = logging.getLogger("CerebroFamilia")

NOMES_AI_FAMILIA = ["EVA", "LUMINA", "NYRA", "YUNA", "KAIYA", "WELLINGTON"]

# Original carregado diretamente
_HAS_ORIG = True
logger.debug("Cérebro Família original NÍO encontrado — usando implementação normalizada (fallback).")


if _HAS_ORIG and '_OriginalCerebroFamilia' in globals() and _OriginalCerebroFamilia is not None:
    CerebroFamilia = _OriginalCerebroFamilia
else:

    class CerebroFamilia:
        def __init__(self, memoria: Optional["SistemaMemoriaHibrido"], config: Any, llm_engine: Any, device: str = 'cuda'):  # Adicionado: device
            self.memoria = memoria
            self.config = config
            self.llm_engine = llm_engine
            self.device = device  # Adicionado: armazenar device
            self._lock = threading.RLock()
            try:
                self.logger = logging.getLogger("CerebroFamilia")
            except Exception:
                self.logger = logger
            self._load_speed_settings()
            persist_path = None
            try:
                if isinstance(self.config, dict):
                    persist_path = self.config.get("AUTONOMY_PERSIST_FILE")
                else:
                    persist_path = getattr(self.config, "AUTONOMY_PERSIST_FILE", None)
            except:
                logging.getLogger(__name__).warning("âš ï¸ Autonomy persist file não disponível")
                persist_path = None
            self.autonomy_state = AutonomyState(path=persist_path)
            try:
                self._llm_call_semaphore = threading.Semaphore(self.settings.get("llm_call_concurrency", 1))
            except Exception:
                self._llm_call_semaphore = threading.Semaphore(1)
            self.executor_paralelo = concurrent.futures.ThreadPoolExecutor(max_workers=self.settings["executor_max_workers"])
            self.status_ais: Dict[str, Dict[str, Any]] = {ai: {"status": "ociosa", "carregada": True} for ai in NOMES_AI_FAMILIA}
            self.chats_ativos: Dict[str, Optional[Any]] = {ai: None for ai in NOMES_AI_FAMILIA}
            self.historico_grupo: List[Dict[str, Any]] = []
            self.threads_autonomia: Dict[str, threading.Thread] = {}
            self._modo_autonomo_ativo = False
            self._shutdown_event = threading.Event()
            self.dispositivo_ai_ai = None
            self.metrics = {
                "llm_calls": 0,
                "llm_total_time": 0.0,
                "mem_get_calls": 0,
                "mem_get_total_time": 0.0,
            }
            self._autonomy_scheduler_interval = int(self.settings.get("autonomy_scheduler_interval_sec", 30))
            self._autonomy_scheduler_thread = threading.Thread(target=self._autonomy_scheduler_loop, daemon=True, name="AutonomyScheduler")
            self._autonomy_scheduler_thread.start()
            self.logger.info("âœ… Cérebro Família (normalizado) inicializado. Settings: %s", self.settings)

        def _load_speed_settings(self):
            defaults = {
                "executor_max_workers": 10,
                "per_ai_timeout_sec": 10.0,
                "group_timeout_sec": 120.0,
                "autonomy_interval_base_sec": 30.0,
                "llm_request_timeout_sec": 30.0,
                "llm_max_tokens": 256,
                "llm_call_concurrency": 2,  # Ajustado de 1 para 2
                "response_delay_min_ms": 0,
                "response_delay_max_ms": 150,
                "autonomy_cycle_period_sec": 3600,
                "autonomy_actions_per_cycle": 4,
                "autonomy_jitter_sec": 30,
                "autonomy_scheduler_interval_sec": 30,
            }
            try:
                cfg = self.config
                executor_max_workers = int(_cfg_get_int(cfg, "CEREBRO", "EXECUTOR_MAX_WORKERS", fallback=defaults["executor_max_workers"]) or defaults["executor_max_workers"])
                per_ai = float(_cfg_get_float(cfg, "CEREBRO", "PER_AI_TIMEOUT_SEC", fallback=defaults["per_ai_timeout_sec"]) or defaults["per_ai_timeout_sec"])
                group_to = float(_cfg_get_float(cfg, "CEREBRO", "GROUP_TIMEOUT_SEC", fallback=defaults["group_timeout_sec"]) or defaults["group_timeout_sec"])
                autonomy_base = float(_cfg_get_float(cfg, "CEREBRO", "AUTONOMY_INTERVAL_BASE_SEC", fallback=defaults["autonomy_interval_base_sec"]) or defaults["autonomy_interval_base_sec"])
                llm_request_timeout = float(_cfg_get_float(cfg, "LLM", "REQUEST_TIMEOUT_SEC", fallback=defaults["llm_request_timeout_sec"]) or defaults["llm_request_timeout_sec"])
                llm_max_tokens = int(_cfg_get_int(cfg, "LLM", "MAX_TOKENS", fallback=defaults["llm_max_tokens"]) or defaults["llm_max_tokens"])
                llm_call_concurrency = int(_cfg_get_int(cfg, "LLM", "LLM_CALL_CONCURRENCY", fallback=defaults["llm_call_concurrency"]) or defaults["llm_call_concurrency"])
                response_delay_min_ms = int(_cfg_get_int(cfg, "LLM", "RESPONSE_DELAY_MIN_MS", fallback=defaults["response_delay_min_ms"]) or defaults["response_delay_min_ms"])
                response_delay_max_ms = int(_cfg_get_int(cfg, "LLM", "RESPONSE_DELAY_MAX_MS", fallback=defaults["response_delay_max_ms"]) or defaults["response_delay_max_ms"])
                autonomy_cycle_period = int(_cfg_get_int(cfg, "AUTONOMY", "AUTONOMY_CYCLE_PERIOD_SEC", fallback=defaults["autonomy_cycle_period_sec"]) or defaults["autonomy_cycle_period_sec"])
                autonomy_actions_per_cycle = int(_cfg_get_int(cfg, "AUTONOMY", "AUTONOMY_ACTIONS_PER_CYCLE", fallback=defaults["autonomy_actions_per_cycle"]) or defaults["autonomy_actions_per_cycle"])
                autonomy_jitter = int(_cfg_get_int(cfg, "AUTONOMY", "AUTONOMY_JITTER_SEC", fallback=defaults["autonomy_jitter_sec"]) or defaults["autonomy_jitter_sec"])
                scheduler_interval = int(_cfg_get_int(cfg, "AUTONOMY", "AUTONOMY_SCHEDULER_INTERVAL_SEC", fallback=defaults["autonomy_scheduler_interval_sec"]) or defaults["autonomy_scheduler_interval_sec"])
                try:
                    env_to = os.environ.get("LLM_REQUEST_TIMEOUT_SEC")
                    if env_to is not None:
                        llm_request_timeout = float(env_to)
                except Exception:
                    pass
                try:
                    env_conc = os.environ.get("LLM_CALL_CONCURRENCY")
                    if env_conc is not None:
                        llm_call_concurrency = int(env_conc)
                except Exception:
                    pass
                self.settings = {
                    "executor_max_workers": executor_max_workers,
                    "per_ai_timeout_sec": per_ai,
                    "group_timeout_sec": group_to,
                    "autonomy_interval_base_sec": autonomy_base,
                    "llm_request_timeout_sec": llm_request_timeout,
                    "llm_max_tokens": llm_max_tokens,
                    "llm_call_concurrency": llm_call_concurrency,
                    "response_delay_min_ms": response_delay_min_ms,
                    "response_delay_max_ms": response_delay_max_ms,
                    "autonomy_cycle_period_sec": autonomy_cycle_period,
                    "autonomy_actions_per_cycle": autonomy_actions_per_cycle,
                    "autonomy_jitter_sec": autonomy_jitter,
                    "autonomy_scheduler_interval_sec": scheduler_interval,
                }
            except Exception:
                self.settings = defaults.copy()
                logger.exception("Erro lendo configurações de velocidade; usando defaults.")

        def get_speed_settings(self) -> Dict[str, Any]:
            with self._lock:
                return dict(self.settings)

        def update_speed_settings(self, overrides: Dict[str, Any]) -> Dict[str, Any]:
            valid_keys = {
                "executor_max_workers", "per_ai_timeout_sec", "group_timeout_sec",
                "autonomy_interval_base_sec", "llm_request_timeout_sec", "llm_max_tokens",
                "llm_call_concurrency", "response_delay_min_ms", "response_delay_max_ms",
                "autonomy_cycle_period_sec", "autonomy_actions_per_cycle", "autonomy_jitter_sec", "autonomy_scheduler_interval_sec"
            }
            with self._lock:
                changed = False
                for k, v in overrides.items():
                    if k in valid_keys:
                        if k.endswith("_workers") or k.endswith("_tokens") or k.endswith("_concurrency") or k.endswith("_ms") or k.endswith("_sec"):
                            self.settings[k] = int(v)
                        else:
                            self.settings[k] = float(v)
                        self.logger.info("Cérebro: setting '%s' atualizado para %s", k, self.settings[k])
                        changed = True
                try:
                    self.settings["per_ai_timeout_sec"] = max(float(self.settings.get("per_ai_timeout_sec", 0.0)), float(self.settings.get("llm_request_timeout_sec", 0.0)))
                except Exception:
                    pass
                try:
                    min_group = float(self.settings.get("per_ai_timeout_sec", 0.0)) * max(1, len(NOMES_AI_FAMILIA))
                    self.settings["group_timeout_sec"] = max(float(self.settings.get("group_timeout_sec", min_group)), min_group)
                except Exception:
                    pass
                try:
                    desired = int(self.settings["executor_max_workers"])
                    if getattr(self, "executor_paralelo", None) is not None:
                        try:
                            self.executor_paralelo.shutdown(wait=False)
                        except Exception:
                            pass
                    self.executor_paralelo = concurrent.futures.ThreadPoolExecutor(max_workers=desired)
                    self.logger.info("Cérebro: executor_paralelo recriado com max_workers=%d", desired)
                except Exception:
                    self.logger.exception("Falha ao recriar executor_paralelo.")
                if changed and "llm_call_concurrency" in overrides:
                    try:
                        conc = int(self.settings.get("llm_call_concurrency", 1))
                        self._llm_call_semaphore = threading.Semaphore(conc)
                        self.logger.info("Cérebro: llm_call_semaphore atualizado para %d", conc)
                    except Exception:
                        self.logger.exception("Falha ao atualizar llm_call_semaphore.")
                return dict(self.settings)

        def _autonomy_scheduler_loop(self):
            self.logger.info("Autonomy scheduler thread iniciado (interval=%ss)", self._autonomy_scheduler_interval)
            while not self._shutdown_event.is_set():
                try:
                    self.autonomy_scheduler_tick()
                except Exception:
                    self.logger.exception("Erro no tick do scheduler de autonomia")
                self._shutdown_event.wait(timeout=self._autonomy_scheduler_interval)
            self.logger.info("Autonomy scheduler thread encerrado")

        def autonomy_scheduler_tick(self):
            try:
                period = int(self.settings.get("autonomy_cycle_period_sec", 3600))
                actions_per_cycle = int(self.settings.get("autonomy_actions_per_cycle", 4))
                jitter = int(self.settings.get("autonomy_jitter_sec", 30))
                for ai in NOMES_AI_FAMILIA:
                    last_ts = 0.0
                    try:
                        node = self.autonomy_state.export().get("ais", {}).get(ai, {})
                        last_ts = float(node.get("last_ts", 0.0))
                    except Exception:
                        last_ts = 0.0
                    min_interval = max(10, period // max(1, actions_per_cycle))
                    if time.time() - last_ts < (min_interval / 2):
                        continue
                    desires = self.autonomy_state.peek_desires(ai)
                    if not desires:
                        try:
                            generate_desire(self, ai, period_sec=period)
                        except Exception:
                            self.logger.exception("Falha ao gerar desire para %s", ai)
                for ai in NOMES_AI_FAMILIA:
                    desires = self.autonomy_state.peek_desires(ai)
                    if not desires:
                        continue
                    desires_sorted = sorted(desires, key=lambda d: (-int(d.get("priority", 5)), float(d.get("created_at", 0))))
                    desire = desires_sorted[0]
                    target = desire.get("target")
                    if target:
                        proposal_id = str(uuid.uuid4())
                        prop = {"desire_id": desire["id"], "action": desire["type"], "payload": desire.get("payload", ""), "from": ai}
                        try:
                            self.autonomy_state.add_proposal(ai, target, proposal_id, prop)
                        except Exception:
                            self.logger.exception("Falha ao adicionar proposal %s -> %s", ai, target)
                        try:
                            decision = evaluate_proposal(self, target, ai, prop)
                            if decision.get("decision") == "accept":
                                execute_desire(self, ai, desire)
                                self.autonomy_state.resolve_proposal(target, proposal_id, "accepted", decision.get("reason"))
                                self.autonomy_state.pop_desire(ai)
                            else:
                                self.autonomy_state.resolve_proposal(target, proposal_id, "rejected", decision.get("reason"))
                                self.autonomy_state.pop_desire(ai)
                        except Exception:
                            self.logger.exception("Falha na avaliação da proposal para %s", target)
                            try:
                                self.autonomy_state.pop_desire(ai)
                            except Exception:
                                pass
                    else:
                        try:
                            allowed_csv = None
                            try:
                                if isinstance(self.config, dict):
                                    allowed_csv = self.config.get("WHITELIST_ACTIONS")
                                else:
                                    allowed_csv = getattr(self.config, "WHITELIST_ACTIONS", None)
                            except:
                                logging.getLogger(__name__).warning("âš ï¸ WHITELIST_ACTIONS não disponível")
                                allowed_csv = None
                            allowed = True
                            if allowed_csv:
                                allowed_set = set([s.strip() for s in str(allowed_csv).split(",") if s.strip()])
                                if desire.get("type") not in allowed_set:
                                    allowed = False
                            if allowed:
                                execute_desire(self, ai, desire)
                                self.autonomy_state.pop_desire(ai)
                            else:
                                self.autonomy_state.pop_desire(ai)
                        except Exception:
                            self.logger.exception("Falha ao executar desire solo para %s", ai)
                            try:
                                self.autonomy_state.pop_desire(ai)
                            except Exception:
                                pass
            except Exception:
                self.logger.exception("Erro geral no autonomy_scheduler_tick")

        def _call_llm(self, request: Dict[str, Any]) -> Any:
            start = time.perf_counter()
            self.metrics["llm_calls"] += 1
            try:
                if self.llm_engine is None:
                    raise LLMUnavailableError("LLM não disponível")
                timeout = float(self.settings.get("llm_request_timeout_sec", 30.0))
                try:
                    env_to = os.environ.get("LLM_REQUEST_TIMEOUT_SEC")
                    if env_to is not None:
                        timeout = float(env_to)
                except Exception:
                    pass
                try:
                    rmin = int(self.settings.get("response_delay_min_ms", 0))
                    rmax = int(self.settings.get("response_delay_max_ms", 0))
                    if rmax > 0 and rmax >= rmin:
                        delay_ms = random.randint(rmin, rmax)
                        if delay_ms > 0:
                            time.sleep(delay_ms / 1000.0)
                except Exception:
                    pass
                if hasattr(self.llm_engine, "generate_response_with_timeout"):
                    try:
                        return self.llm_engine.generate_response_with_timeout(request, timeout=timeout)
                    except Exception:
                        self.logger.exception("Erro no generate_response_with_timeout (fallback).")
                acquired = False
                try:
                    self._llm_call_semaphore.acquire()
                    acquired = True
                    if hasattr(self.llm_engine, "generate_response"):
                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                            fut = ex.submit(self.llm_engine.generate_response, request)
                            try:
                                resp = fut.result(timeout=timeout)
                            except concurrent.futures.TimeoutError:
                                fut.cancel()
                                self.logger.error("â° Timeout ao chamar LLM (timeout=%ss)", timeout)
                                raise LLMTimeoutError("Timeout ao chamar LLM")
                            return resp
                    else:
                        if hasattr(self.llm_engine, "generate"):
                            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                                fut = ex.submit(self.llm_engine.generate, request)
                                try:
                                    resp = fut.result(timeout=timeout)
                                except concurrent.futures.TimeoutError:
                                    fut.cancel()
                                    self.logger.error("â° Timeout ao chamar LLM (timeout=%ss)", timeout)
                                    raise LLMTimeoutError("Timeout ao chamar LLM")
                                return resp
                        # Se nenhum método suportado, levantamos erro explícito (não devolvemos placeholder)
                        self.logger.error("LLM engine presente mas sem método de geração suportado")
                        raise LLMUnavailableError("LLM engine possui nenhum método de geração suportado (generate / generate_response / generate_response_with_timeout)")
                finally:
                    if acquired:
                        try:
                            self._llm_call_semaphore.release()
                        except Exception:
                            pass
            except Exception as e:
                self.logger.exception("Erro chamando LLM")
                raise LLMExecutionError("Erro ao chamar LLM") from e
            finally:
                elapsed = time.perf_counter() - start
                self.metrics["llm_total_time"] += elapsed

        def processar_intencao(self, ai_nome_alvo: str, mensagem_usuario: str) -> str:
            ai_nome = ai_nome_alvo.upper()
            if ai_nome not in NOMES_AI_FAMILIA:
                return f"[ERRO] AI '{ai_nome}' não reconhecida."
            with self._lock:
                self.chats_ativos[ai_nome] = {"tipo": "individual", "usuario": True}
                self.status_ais[ai_nome]["status"] = "ocupada"
            try:
                contexto = ""
                if self.memoria and hasattr(self.memoria, "get_context"):
                    t0 = time.perf_counter()
                    try:
                        contexto = self.memoria.get_context(ai_nome, mensagem_usuario, limit=2048)
                    except Exception:
                        self.logger.debug("Falha ao obter contexto da memória (não crítico).")
                        contexto = ""
                    dt = time.perf_counter() - t0
                    self.metrics["mem_get_calls"] += 1
                    self.metrics["mem_get_total_time"] += dt
                prompt = f"<|system|>\n{contexto}\n<|user|>\n{mensagem_usuario}\n<|assistant|>\n"
                request = {"ai_id": ai_nome, "prompt": prompt, "max_tokens": int(self.settings.get("llm_max_tokens", 256)), "temperature": 0.7}
                resposta_bruta = self._call_llm(request)
                resposta_limpa = str(resposta_bruta).replace("<|assistant|>", "").strip()
                if self.memoria and hasattr(self.memoria, "salvar_evento_autonomo") and TipoInteracao is not None:
                    try:
                        self.memoria.salvar_evento_autonomo(
                            nome_alma=ai_nome,
                            tipo=TipoInteracao.HUMANO_AI,
                            entrada=mensagem_usuario,
                            resposta=resposta_limpa
                        )
                    except Exception:
                        self.logger.debug("Falha ao salvar evento na memória (não crítico).")
                self.logger.info("ðŸ’¬ [%s] Interação concluída (normalizado).", ai_nome)
                return resposta_limpa
            except LLMTimeoutError as e:
                self.logger.error("Timeout LLM ao processar intenção para %s: %s", ai_nome, e, exc_info=True)
                return "[ERRO] Requisição ao LLM expirou. Tente novamente."
            except LLMUnavailableError as e:
                self.logger.error("LLM indisponível ao processar intenção para %s: %s", ai_nome, e, exc_info=True)
                return "[ERRO] LLM indisponível no momento."
            except LLMExecutionError as e:
                self.logger.error("Erro de execução do LLM para %s: %s", ai_nome, e, exc_info=True)
                return "[ERRO INTERNO] Ocorreu um problema ao gerar a resposta."
            except Exception as e:
                self.logger.error("âŒ Erro ao processar intenção para %s: %s", ai_nome, e, exc_info=True)
                return f"[ERRO INTERNO] {ai_nome} não pôde processar sua solicitação."
            finally:
                with self._lock:
                    self.chats_ativos[ai_nome] = None
                    self.status_ais[ai_nome]["status"] = "ociosa"

        def _acao_pensar(self, ai_nome: str) -> Dict[str, Any]:
            with self._lock:
                try:
                    self.chats_ativos[ai_nome] = {"tipo": "autonomo", "usuario": False}
                    self.status_ais[ai_nome]["status"] = "ocupada"
                except Exception:
                    pass
            try:
                prompt = "Faça um breve plano de ação de alto nível em poucas frases."
                req = {
                    "ai_id": ai_nome,
                    "prompt": prompt,
                    "max_tokens": int(self.settings.get("llm_max_tokens", 256)),
                    "temperature": 0.7,
                }
                resposta = self._call_llm(req)
                texto = str(resposta).replace("<|assistant|>", "").strip()
                try:
                    self.logger.info("Ação PENSAR: %s -> %s", ai_nome, (texto[:200] + "...") if len(texto) > 200 else texto)
                except Exception:
                    pass
                return {"sucesso": True, "resultado": texto}
            except Exception as e:
                try:
                    self.logger.exception("Erro em _acao_pensar para %s", ai_nome)
                except Exception:
                    pass
                return {"sucesso": False, "erro": str(e)}
            finally:
                with self._lock:
                    try:
                        self.chats_ativos[ai_nome] = None
                        self.status_ais[ai_nome]["status"] = "ociosa"
                    except Exception:
                        pass

        def _acao_analisar_memoria(self, ai_nome: str) -> Dict[str, Any]:
            with self._lock:
                try:
                    self.chats_ativos[ai_nome] = {"tipo": "autonomo", "usuario": False}
                    self.status_ais[ai_nome]["status"] = "ocupada"
                except Exception:
                    pass
            try:
                contexto = ""
                if self.memoria and hasattr(self.memoria, "get_context"):
                    try:
                        t0 = time.perf_counter()
                        contexto = self.memoria.get_context(ai_nome, "analisar_memoria", limit=2048)
                        dt = time.perf_counter() - t0
                        self.metrics["mem_get_calls"] += 1
                        self.metrics["mem_get_total_time"] += dt
                    except Exception:
                        contexto = ""
                prompt = f"Analise o contexto abaixo e resuma pontos de ação:\n\n{contexto}"
                req = {
                    "ai_id": ai_nome,
                    "prompt": prompt,
                    "max_tokens": int(self.settings.get("llm_max_tokens", 256)),
                    "temperature": 0.4,
                }
                resposta = self._call_llm(req)
                texto = str(resposta).replace("<|assistant|>", "").strip()
                try:
                    self.logger.info("Ação ANALISAR_MEMORIA: %s -> %s", ai_nome, (texto[:200] + "...") if len(texto) > 200 else texto)
                except Exception:
                    pass
                return {"sucesso": True, "resultado": texto}
            except Exception as e:
                try:
                    self.logger.exception("Erro em _acao_analisar_memoria para %s", ai_nome)
                except Exception:
                    pass
                return {"sucesso": False, "erro": str(e)}
            finally:
                with self._lock:
                    try:
                        self.chats_ativos[ai_nome] = None
                        self.status_ais[ai_nome]["status"] = "ociosa"
                    except Exception:
                        pass

        def _acao_interagir_ai_especifica(self, ai_nome: str, alvo_ai: Optional[str] = None) -> Dict[str, Any]:
            with self._lock:
                try:
                    self.chats_ativos[ai_nome] = {"tipo": "autonomo", "usuario": False}
                    self.status_ais[ai_nome]["status"] = "ocupada"
                except Exception:
                    pass
            try:
                if alvo_ai and getattr(self, "dispositivo_ai_ai", None):
                    try:
                        if hasattr(self.dispositivo_ai_ai, "enviar_mensagem_para_ai"):
                            self.dispositivo_ai_ai.enviar_mensagem_para_ai(origem=ai_nome, destino=alvo_ai, mensagem="Olá — iniciar interação autônoma")
                            self.logger.info("Interação AI->AI enviada: %s -> %s", ai_nome, alvo_ai)
                            return {"sucesso": True, "resultado": f"mensagem enviada {ai_nome}->{alvo_ai}"}
                    except Exception:
                        self.logger.debug("Falha ao usar dispositivo AIâ†”AI para interação; cair para LLM")
                prompt = f"Simule uma breve interação entre {ai_nome} e {alvo_ai or 'outra AI'}: "
                req = {"ai_id": ai_nome, "prompt": prompt, "max_tokens": 200}
                resposta = self._call_llm(req)
                texto = str(resposta).replace("<|assistant|>", "").strip()
                try:
                    self.logger.info("Ação INTERAGIR_AI: %s -> %s (simulação)", ai_nome, alvo_ai or "simulado")
                except Exception:
                    pass
                return {"sucesso": True, "resultado": texto}
            except Exception as e:
                try:
                    self.logger.exception("Erro em _acao_interagir_ai_especifica para %s (alvo=%s)", ai_nome, alvo_ai)
                except Exception:
                    pass
                return {"sucesso": False, "erro": str(e)}
            finally:
                with self._lock:
                    try:
                        self.chats_ativos[ai_nome] = None
                        self.status_ais[ai_nome]["status"] = "ociosa"
                    except Exception:
                        pass

        def iniciar_modo_autonomo(self):
            if getattr(self, "_modo_autonomo_ativo", False):
                try:
                    self.logger.warning("ðŸ¤– Modo autônomo já está ativo.")
                except Exception:
                    pass
                return
            try:
                self.logger.info("ðŸ¤– Iniciando modo autônomo para as AIs...")
            except Exception:
                pass
            self._modo_autonomo_ativo = True
            try:
                self._shutdown_event.clear()
            except Exception:
                pass
            for ai_nome in NOMES_AI_FAMILIA:
                t = self.threads_autonomia.get(ai_nome)
                if not t or not t.is_alive():
                    if hasattr(self, "_loop_autonomo_ai"):
                        thread = threading.Thread(target=self._loop_autonomo_ai, args=(ai_nome,), daemon=True, name=f"Autonomia-{ai_nome}")
                        thread.start()
                        self.threads_autonomia[ai_nome] = thread
            if self.dispositivo_ai_ai and hasattr(self.dispositivo_ai_ai, "iniciar"):
                try:
                    self.dispositivo_ai_ai.iniciar()
                    self.logger.info("ðŸ“¡ Dispositivo AIâ†”AI ativado com modo autônomo.")
                except Exception:
                    self.logger.debug("Falha ao iniciar dispositivo AIâ†”AI (não crítico).")
            try:
                self.logger.info("ðŸ¤– Modo autônomo ativado para todas as AIs.")
            except Exception:
                pass

        def parar_modo_autonomo(self):
            try:
                self.logger.info("ðŸ¤– Parando modo autônomo...")
            except Exception:
                pass
            self._modo_autonomo_ativo = False
            try:
                self._shutdown_event.set()
            except Exception:
                pass
            for ai_nome, thread in self.threads_autonomia.items():
                try:
                    if thread.is_alive():
                        thread.join(timeout=5.0)
                        if thread.is_alive():
                            try:
                                self.logger.warning("âš ï¸ Thread de autonomia de %s não terminou a tempo.", ai_nome)
                            except Exception:
                                pass
                except Exception:
                    try:
                        self.logger.debug("Erro ao aguardar término de thread de autonomia (não crítico).")
                    except Exception:
                        pass
            if self.dispositivo_ai_ai and hasattr(self.dispositivo_ai_ai, "parar"):
                try:
                    self.dispositivo_ai_ai.parar()
                    self.logger.info("ðŸ“¡ Dispositivo AIâ†”AI desativado.")
                except Exception:
                    self.logger.debug("Falha ao parar dispositivo AIâ†”AI (não crítico).")
            try:
                self.logger.info("ðŸ¤– Modo autônomo parado.")
            except Exception:
                pass

        def get_status(self) -> Dict[str, Any]:
            with self._lock:
                paralelismo = 0
                try:
                    q = getattr(self.executor_paralelo, "_work_queue", None)
                    if q is not None and hasattr(q, "qsize"):
                        paralelismo = q.qsize()
                except Exception:
                    paralelismo = 0
                return {
                    "modo_autonomo": self._modo_autonomo_ativo,
                    "ais": {
                        ai: {
                            "carregada": self.status_ais[ai]["carregada"],
                            "status": self.status_ais[ai]["status"],
                            "em_chat": self.chats_ativos[ai] is not None,
                            "thread_autonomia_ativa": ai in self.threads_autonomia and self.threads_autonomia[ai].is_alive()
                        } for ai in NOMES_AI_FAMILIA
                    },
                    "paralelismo": {"executor_trabalhos_pendentes": paralelismo},
                    "metrics": dict(self.metrics),
                    "settings": dict(self.settings),
                }

        def shutdown(self):
            try:
                self.logger.info("ðŸ›‘ Desligando Cérebro Família (normalizado)...")
            except Exception:
                pass
            try:
                self.parar_modo_autonomo()
            except Exception:
                pass
            try:
                self._shutdown_event.set()
            except Exception:
                pass
            try:
                if getattr(self, "executor_paralelo", None) is not None:
                    self.executor_paralelo.shutdown(wait=True)
            except Exception:
                self.logger.debug("Erro ao encerrar executor_paralelo (não crítico).")
            try:
                self.logger.info("ðŸ›‘ Cérebro Família desligado.")
            except Exception:
                pass
