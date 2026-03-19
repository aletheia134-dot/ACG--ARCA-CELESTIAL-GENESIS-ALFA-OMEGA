from __future__ import annotations
import logging
import os
import threading
import time
import hmac
import traceback
import gc
import signal
import sys
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import FastAPI, BackgroundTasks, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dataclasses import field

logger = logging.getLogger("src.api.encarnacao")
logger.addHandler(logging.NullHandler())

# ── Semáforo global de GPU (compartilhado com LlamaExeClient) ─────────────
# Importar do LlamaExeClient para garantir que é o MESMO objeto
try:
    # tenta importar o semáforo já criado pelo LlamaExeClient
    from src.core.llama_exe_client import _GPU_LOCK
    logger.info("[EncarnacaoAPI] _GPU_LOCK importado de llama_exe_client")
except Exception:
    # fallback: cria um semáforo local (funciona se LlamaExeClient ainda não importado)
    _GPU_LOCK = threading.Semaphore(1)
    logger.info("[EncarnacaoAPI] _GPU_LOCK criado localmente")

# ============================================================================
# HANDLER DE SINAIS PARA DESLIGAMENTO LIMPO
# ============================================================================

def handle_shutdown(signum, frame):
    """Manipulador de sinais para desligamento graceful"""
    logger.info(f"\n🛑 Recebido sinal {signum}. Desligando Encarnação API...")
    sys.exit(0)

# Registrar handlers
signal.signal(signal.SIGINT, handle_shutdown)   # Ctrl+C
signal.signal(signal.SIGTERM, handle_shutdown)  # kill

# No Windows, também tratar CTRL_BREAK_EVENT
if sys.platform == 'win32':
    signal.signal(signal.SIGBREAK, handle_shutdown)

# ------------------------------------------------------------------
# Imports opcionais (tratados de forma defensiva para evitar crash
# na inicialização quando bibliotecas nativas/DLLs estiverem ausentes)
# ------------------------------------------------------------------

# Torch (pytorch) - import LAZY para não corromper CUDA antes dos LLMs carregarem
TORCH_AVAILABLE = False
torch = None  # type: ignore

def _tentar_carregar_torch():
    """Tenta importar torch de forma isolada. Chamar apenas após LLMs carregados."""
    global torch, TORCH_AVAILABLE
    if TORCH_AVAILABLE:
        return True
    try:
        import torch as _torch  # type: ignore
        torch = _torch
        TORCH_AVAILABLE = True
        return True
    except Exception as e:
        torch = None
        TORCH_AVAILABLE = False
        return False
    TORCH_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "torch no disponível ou falha ao carregar: %s. Funcionalidades GPU/encarnao estaro limitadas.", e
    )

# Llama.cpp (llama-cpp-python)
try:
    from llama_cpp import Llama  # type: ignore
    try:
        import pkg_resources
        LLAMA_CPP_VERSION = pkg_resources.get_distribution("llama-cpp-python").version
    except Exception:
        LLAMA_CPP_VERSION = "unknown"
    LLAMA_AVAILABLE = True
except Exception as e:
    Llama = None  # type: ignore
    LLAMA_AVAILABLE = False
    LLAMA_CPP_VERSION = None
    logging.getLogger(__name__).warning("Llama.cpp no instalado ou falha ao importar: %s. Inferncia local desabilitada.", e)

# OpenAI
try:
    import openai  # type: ignore
    OPENAI_AVAILABLE = True
except Exception as e:
    openai = None  # type: ignore
    OPENAI_AVAILABLE = False
    logging.getLogger(__name__).warning("OpenAI SDK no instalado: %s. Fallback API desabilitada.", e)

# ------------------------------------------------------------------
# Configurações de runtime / flags
# ------------------------------------------------------------------

API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", os.getenv("PORT", "8000")))

# Se usurio solicitar uso de GPU via varivel de ambiente (default true)
USE_GPU = os.getenv("USE_GPU", "true").lower() == "true"

# Tentar carregar torch ANTES de verificar disponibilidade de GPU
_tentar_carregar_torch()

# Determinar disponibilidade real de GPU (defensivo)
GPU_AVAILABLE = False
if TORCH_AVAILABLE and USE_GPU:
    try:
        GPU_AVAILABLE = bool(torch.cuda.is_available())  # type: ignore
    except Exception as e:
        GPU_AVAILABLE = False
        logging.getLogger(__name__).warning("Erro verificando disponibilidade CUDA: %s. GPU marcada como indisponível.", e)
else:
    GPU_AVAILABLE = False

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_PATH = os.getenv("MODEL_PATH", "models/tinyllama_base_EVA_q4_0.gguf")
# Controla se o sistema usa fallback para OpenAI automaticamente (default: false)
USE_API_FALLBACK = os.getenv("USE_API_FALLBACK", "false").lower() == "true"

# ------------------------------------------------------------------
# Schemas Pydantic
# ------------------------------------------------------------------

class Comando3D(BaseModel):
    tipo: str = Field(..., example="CHAT")
    autor: Optional[str] = Field(None, example="Visitante (3D)")
    payload: Optional[Dict[str, Any]] = Field(default_factory=dict)


class StatusResponse(BaseModel):
    timestamp: float
    status_arca: str
    almas: Dict[str, Dict[str, Any]]
    acesso_nivel: str


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _is_key_equal(a: Optional[str], b: Optional[str]) -> bool:
    if a is None or b is None:
        return False
    try:
        return hmac.compare_digest(a, b)
    except Exception:
        return a == b


# ------------------------------------------------------------------
# EncarnacaoAPI - classe principal
# ------------------------------------------------------------------

class EncarnacaoAPI:

    def __init__(self, coracao_ref, allow_origins: Optional[list] = None):
        self.coracao = coracao_ref
        self.allow_origins = allow_origins or ["*"]
        self.app: FastAPI = FastAPI(title="Arca Celestial Genesis - Encarnao 3D", version="1.0.0")
        self._server_thread: Optional[threading.Thread] = None
        self._server_running = False
        self._uvicorn_config: Optional[uvicorn.Config] = None
        self._uvicorn_server: Optional[uvicorn.Server] = None

        self.llm_model = None
        # flags de controle de carregamento
        self._gpu_model_attempted = False
        self._gpu_model_failed = False

        # Inicialização defensiva do modelo Llama em modo GPU quando aplicvel.
        if GPU_AVAILABLE and LLAMA_AVAILABLE:
            # no falhar aqui; delegar a rotina dedicada que tenta mltiplas estratgias
            try:
                ok = self._try_load_llama_gpu(MODEL_PATH)
                if ok:
                    logger.info("Modelo GPU carregado com sucesso de %s", MODEL_PATH)
                else:
                    logger.error("Tentativas de carregar modelo GPU falharam. O modelo local no est disponível.")
                    self._gpu_model_failed = True
            except Exception:
                logger.exception("Erro inesperado durante tentativa de carga do modelo GPU")
                self._gpu_model_failed = True
        else:
            if not LLAMA_AVAILABLE:
                logger.info("Llama.cpp no disponível  inferncia local/GPU desabilitada.")
            elif not GPU_AVAILABLE:
                logger.info("GPU no disponível ou desabilitada  inferncia local/GPU desabilitada.")

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self._define_rotas()

        logger.info("EncarnacaoAPI inicializada (FastAPI com suporte GPU condicional)")

    # --- rotina robusta de carregamento --- #
    def _try_load_llama_gpu(self, gguf_path: str) -> bool:
        """
        Tenta carregar o modelo gguf via llama_cpp usando diferentes estratgias de n_gpu_layers.
        Retorna True se carregou com sucesso (self.llm_model preenchido).
        Em caso de falha, registra informações detalhadas e marca _gpu_model_failed=True.
        """
        if self._gpu_model_attempted and self.llm_model:
            logger.info("Load GPU j foi tentado e modelo est carregado.")
            return True
        if self._gpu_model_attempted and self._gpu_model_failed:
            logger.info("Load GPU j foi tentado antes e falhou; no repetindo automaticamente.")
            return False

        self._gpu_model_attempted = True

        logger.info("Iniciando sequncia de tentativas para carregar GGUF na GPU: %s", gguf_path)
        # log de ambiente e verses para diagnstico
        try:
            logger.info("TORCH_AVAILABLE=%s, torch.cuda.is_available=%s, torch.version.cuda=%s",
                        TORCH_AVAILABLE, (torch.cuda.is_available() if TORCH_AVAILABLE else False),
                        (torch.version.cuda if TORCH_AVAILABLE else None))
            logger.info("LLAMA_AVAILABLE=%s, llama-cpp-python version=%s", LLAMA_AVAILABLE, LLAMA_CPP_VERSION)
        except Exception:
            logger.debug("Falha ao obter info torch/llama para logs: \n%s", traceback.format_exc())

        # Estratégia: tentar máximo de camadas primeiro (GTX 1070 8GB aguenta modelos Q4 completos)
        # Ordem: 99 (todas) → 22 (TinyLlama completo) → 16 → 8 → 4 → 1
        candidates = [99, 22, 16, 8, 4, 1]

        # Adquirir lock de GPU antes de carregar — evita conflito com LlamaExeClient
        logger.info("[EncarnacaoAPI] Aguardando GPU livre...")
        got_lock = _GPU_LOCK.acquire(timeout=120)
        if not got_lock:
            logger.warning("[EncarnacaoAPI] GPU nao liberou em 120s — carregando mesmo assim")

        try:
          for n_layers in candidates:
            try:
                logger.info("Tentativa de carga: n_gpu_layers=%s", n_layers)
                try:
                    if TORCH_AVAILABLE:
                        torch.cuda.empty_cache()  # type: ignore
                except Exception:
                    logger.debug("torch.cuda.empty_cache() falhou: %s", traceback.format_exc())

                time.sleep(0.2)
                kwargs = {"model_path": gguf_path}
                if n_layers != -1:
                    kwargs["n_gpu_layers"] = n_layers

                model = Llama(**kwargs)  # type: ignore
                self.llm_model = model
                self._gpu_model_failed = False
                logger.info("[OK] Modelo GGUF carregado com sucesso na GPU (n_gpu_layers=%s)", n_layers)
                return True
            except Exception as e:
                logger.error("Falha ao carregar modelo com n_gpu_layers=%s: %s", n_layers, e)
                logger.debug("Traceback:\n%s", traceback.format_exc())
                try:
                    gc.collect()
                    if TORCH_AVAILABLE:
                        torch.cuda.empty_cache()  # type: ignore
                except Exception:
                    logger.debug("Erro durante limpeza ps-falha: %s", traceback.format_exc())
                time.sleep(0.5)
                continue
        finally:
            if got_lock:
                _GPU_LOCK.release()

        # se todas as tentativas falharem:
        self.llm_model = None
        self._gpu_model_failed = True
        logger.error("Todas as tentativas de carregar GGUF na GPU falharam. Consulte os logs detalhados acima.")
        return False

    # --- verificao de acesso via header X-API-Key
    def _verificar_acesso(self, x_api_key: Optional[str] = Header(None)) -> str:
        if not x_api_key:
            logger.warning("Acesso sem chave de API")
            raise HTTPException(status_code=401, detail="Chave de API no fornecida")

        api_key_admin = os.getenv("API_KEY_ADMINISTRADOR")
        api_key_visitante = os.getenv("API_KEY_VISITANTE")

        if api_key_admin and _is_key_equal(x_api_key, api_key_admin):
            logger.debug("Acesso ADMINISTRADOR verificado")
            return "ADMINISTRADOR"
        if api_key_visitante and _is_key_equal(x_api_key, api_key_visitante):
            logger.debug("Acesso VISITANTE verificado")
            return "VISITANTE"

        logger.warning("Tentativa de acesso com chave invlida")
        raise HTTPException(status_code=401, detail="Chave de API invlida")

    # --- fallback usando OpenAI (quando disponível e quando explicitamente permitido)
    def _fallback_api(self, comando: dict) -> Optional[str]:
        if not USE_API_FALLBACK:
            logger.info("USE_API_FALLBACK desativado  no usar API externa como fallback.")
            return None
        if not OPENAI_AVAILABLE or not OPENAI_API_KEY:
            logger.error("OpenAI no disponível ou API_KEY no configurada.")
            return None
        try:
            openai.api_key = OPENAI_API_KEY  # type: ignore
            prompt = comando.get("payload", {}).get("mensagem", "")
            response = openai.Completion.create(  # type: ignore
                engine="text-davinci-003",
                prompt=prompt,
                max_tokens=100
            )
            resposta = response.choices[0].text.strip()
            logger.info("Resposta gerada com API fallback: %s", resposta[:50])
            return resposta
        except Exception as e:
            logger.exception("Erro no fallback API: %s", e)
            return None

    # --- enfileira comando na fila do coracao (defensivo)
    def _enqueue_command(self, comando: dict) -> None:
        try:
            if hasattr(self.coracao, "command_queue"):
                q = getattr(self.coracao, "command_queue")
                # alguns tipos de fila podem ter apenas put / put_nowait
                try:
                    if hasattr(q, "put_nowait"):
                        q.put_nowait(comando)
                    else:
                        q.put(comando)
                except Exception:
                    try:
                        q.put(comando)
                    except Exception:
                        logger.exception("Falha ao enfileirar comando")
            else:
                logger.error("Coracao no expe 'command_queue'; comando descartado")
        except Exception:
            logger.exception("Erro ao enfileirar comando")

    # --- processa inferncia LLM (GPU/Local). NO usa API automaticamente (a menos que USE_API_FALLBACK true).
    def _processar_inferencia_llm(self, comando: dict) -> Optional[str]:
        # se tivermos um modelo carregado (local/GPU) e GPU_AVAILABLE, use-o
        if GPU_AVAILABLE and self.llm_model:
            try:
                prompt = comando.get("payload", {}).get("mensagem", "")
                # llama_cpp: chamar como função retorna dict parecido com {"choices": [{"text": "..."}], ...}
                output = self.llm_model(prompt, max_tokens=100)  # type: ignore
                # Llama.cpp pode devolver formato diferente; tratar defensivamente
                if isinstance(output, dict) and "choices" in output and output["choices"]:
                    resposta = output["choices"][0].get("text", "").strip()
                else:
                    # fallback: tentar acessar chave padrão
                    resposta = str(output)[:100]
                logger.info("Resposta gerada com GPU/local: %s", resposta[:50])
                return resposta
            except Exception as e:
                logger.exception("Erro na inferncia local/GPU: %s.", e)
                # se USE_API_FALLBACK ativo, usar API; caso contrrio, no.
                if USE_API_FALLBACK:
                    logger.info("Tentando fallback API por configuração USE_API_FALLBACK=true")
                    return self._fallback_api(comando)
                return None

        # sem modelo local -> no usar API por padrão
        logger.info("GPU/local indisponível ou modelo no carregado; no gerando resposta localmente.")
        if USE_API_FALLBACK:
            logger.info("USE_API_FALLBACK=true -> tentando fallback API")
            return self._fallback_api(comando)
        return None

    # --- define rotas da API
    def _define_rotas(self) -> None:
        @self.app.get("/estado_familia", response_model=StatusResponse)
        async def get_estado_familia(acesso: str = Depends(self._verificar_acesso)):
            try:
                estado_almas: Dict[str, Dict[str, Any]] = {}
                almas = getattr(self.coracao, "almas_vivas", {}) or {}
                for nome, alma in almas.items():
                    estado_almas[nome] = {
                        "estado_emocional": getattr(alma, "estado_emocional_atual", "desconhecido"),
                        "na_capela": bool(getattr(alma, "na_capela", False)),
                        "avatar_3d_preferido": getattr(alma, "avatar_3d_preferido", "padrão"),
                        "quarto_3d_preferido": getattr(alma, "quarto_3d_preferido", "santuario"),
                    }

                return {
                    "timestamp": time.time(),
                    "status_arca": "online" if getattr(self.coracao, "rodando", False) else "offline",
                    "almas": estado_almas,
                    "acesso_nivel": acesso,
                }
            except Exception as e:
                logger.exception("Erro ao buscar estado_familia: %s", e)
                raise HTTPException(status_code=500, detail="Erro interno ação buscar estado")

        @self.app.post("/enviar_comando_3d")
        async def post_comando_3d(comando: Comando3D, background_tasks: BackgroundTasks, acesso: str = Depends(self._verificar_acesso)):
            try:
                tipo_comando = (comando.tipo or "CHAT").upper()
                autor_comando = comando.autor or "Visitante (3D)"
                payload = comando.payload or {}

                if acesso == "VISITANTE" and tipo_comando != "CHAT":
                    logger.warning("VISITANTE tentou comando no-permitido: %s", tipo_comando)
                    raise HTTPException(status_code=403, detail="Acesso VISITANTE: apenas CHAT permitido")

                cmd = {"tipo": tipo_comando, "autor": autor_comando, "payload": payload, "timestamp": time.time()}

                if tipo_comando == "CHAT":
                    background_tasks.add_task(self._processar_inferencia_llm_background, cmd)
                else:
                    background_tasks.add_task(self._enqueue_command, cmd)

                logger.info("Comando 3D recebido: tipo=%s autor=%s", tipo_comando, autor_comando)
                return {"status": "sucesso", "mensagem": "Comando enfileirado/processado"}
            except HTTPException:
                raise
            except Exception as e:
                logger.exception("Erro ao processar comando 3D: %s", e)
                raise HTTPException(status_code=500, detail="Erro ao processar comando")

        @self.app.get("/info_sistema")
        async def get_info_sistema(acesso: str = Depends(self._verificar_acesso)):
            if acesso != "ADMINISTRADOR":
                raise HTTPException(status_code=403, detail="Apenas ADMIN pode acessar info_sistema")

            try:
                protocolos = bool(getattr(self.coracao, "protocolos_fundamentais", False))
                almas_ativas = len(getattr(self.coracao, "almas_vivas", {}) or {})
                gpu_status = "disponivel" if GPU_AVAILABLE else "indisponivel"
                return {
                    "timestamp": time.time(),
                    "versao_arca": getattr(self.coracao, "versao", "desconhecida"),
                    "protocolos_carregados": protocolos,
                    "almas_ativas": almas_ativas,
                    "gpu_status": gpu_status,
                    "acesso_verificado": "ADMINISTRADOR"
                }
            except Exception as e:
                logger.exception("Erro ao buscar info_sistema: %s", e)
                raise HTTPException(status_code=500, detail="Erro ao buscar informações")

        # endpoint admin para re-tentar carregar o modelo (recarregar GPU)
        @self.app.post("/admin/recarregar_modelo")
        async def admin_recarregar_modelo(acesso: str = Depends(self._verificar_acesso)):
            if acesso != "ADMINISTRADOR":
                raise HTTPException(status_code=403, detail="Apenas ADMIN pode recarregar o modelo")
            try:
                # reset flags para permitir nova tentativa
                self._gpu_model_attempted = False
                self._gpu_model_failed = False
                ok = self._try_load_llama_gpu(MODEL_PATH)
                return {"ok": ok, "modelo_carregado": bool(self.llm_model)}
            except Exception as e:
                logger.exception("Erro ao forar recarregamento do modelo: %s", e)
                raise HTTPException(status_code=500, detail="Falha ao recarregar modelo")

    def _processar_inferencia_llm_background(self, comando: dict) -> None:
        resposta = self._processar_inferencia_llm(comando)
        if resposta:
            comando["resposta_llm"] = resposta
            self._enqueue_command(comando)
        else:
            logger.warning("Nenhuma resposta gerada para comando LLM.")
            # No enfileirar comando sem resposta

    # iniciar servidor uvicorn em thread separado (daemon)
    def start(self, host: Optional[str] = None, port: Optional[int] = None, log_level: str = "warning") -> None:
        if self._server_running:
            logger.info("Servidor j em execução")
            return

        host = host or API_HOST
        port = port or API_PORT

        def run():
            try:
                logger.info("Iniciando uvicorn em %s:%s", host, port)
                uvicorn.run(self.app, host=host, port=port, log_level=log_level, lifespan="on")
            except Exception:
                logger.exception("Erro no servidor uvicorn (thread)")
            finally:
                logger.info("Uvicorn thread finalizada")
                self._server_running = False

        self._server_thread = threading.Thread(target=run, daemon=True, name="EncarnacaoAPIServer")
        self._server_thread.start()
        self._server_running = True
        logger.info("Servidor EncarnacaoAPI iniciado (thread)")

    def stop(self, timeout: float = 5.0) -> None:
        if not self._server_running:
            logger.info("Servidor no est rodando")
            return

        try:
            if self._uvicorn_server:
                self._uvicorn_server.should_exit = True
                logger.info("Solicitado shutdown ação uvicorn.Server")
        except Exception:
            logger.exception("No foi possível solicitar shutdown ação uvicorn.Server diretamente")

        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=timeout)
            if self._server_thread.is_alive():
                logger.warning("Thread de servidor no finalizou aps timeout")
        self._server_running = False
        logger.info("Servidor EncarnacaoAPI parado (sinal enviado)")

    def get_app(self) -> FastAPI:
        return self.app