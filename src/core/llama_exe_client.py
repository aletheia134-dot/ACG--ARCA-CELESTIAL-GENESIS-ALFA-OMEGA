# src/core/llama_exe_client.py
"""
Cliente LLM para as almas da ARCA.
Estratégia dupla:
  1. llama-cpp-python (GPU real via CUDA) — preferencial
  2. llama-cli.exe via subprocess              — fallback

IMPORTANTE: usa _GPU_LOCK global para evitar conflito CUDA com EncarnacaoAPI.
Apenas um modelo pode ser carregado na GPU por vez.
"""

import subprocess
import logging
import configparser
import gc
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("LlamaExeClient")

# ── Semáforo global de GPU ─────────────────────────────────────────────────
# Compartilhado entre LlamaExeClient e EncarnacaoAPI.
# Garante que apenas um modelo seja carregado na VRAM por vez.
# Timeout de 60s: se EncarnacaoAPI travar, LlamaExeClient ainda tenta.
_GPU_LOCK = threading.Semaphore(1)

# ── Tentar importar llama-cpp-python ──────────────────────────────────────
_LLAMA_CPP_OK = False
_Llama = None
try:
    from llama_cpp import Llama as _Llama  # type: ignore
    _LLAMA_CPP_OK = True
    logger.info("llama-cpp-python disponivel -- GPU via CUDA ativada")
except ImportError:
    logger.warning("llama-cpp-python nao encontrado -- usando llama-cli.exe (pode ser CPU-only)")


def _ler_gpu_layers() -> int:
    for candidato in [
        Path("E:/Arca_Celestial_Genesis_Alfa_Omega/config.ini"),
        Path("config.ini"),
        Path(__file__).parent.parent.parent / "config.ini",
    ]:
        if candidato.exists():
            try:
                cp = configparser.ConfigParser()
                cp.read(str(candidato), encoding="utf-8")
                val = cp.get("LLM", "GPU_LAYERS", fallback=None)
                if val:
                    return int(val)
            except Exception:
                pass
    return 99


class LlamaExeClient:
    """
    Motor LLM das almas.
    Usa llama-cpp-python com GPU (CUDA) quando disponível.
    Fallback para llama-cli.exe subprocess quando não disponível.
    Os modelos são carregados sob demanda (lazy) e mantidos em cache.
    """

    def __init__(self):
        self.executavel    = Path("E:/Arca_Celestial_Genesis_Alfa_Omega/llama/llama-cli.exe")
        self.pasta_modelos = Path("E:/Arca_Celestial_Genesis_Alfa_Omega/models")
        self.gpu_layers    = _ler_gpu_layers()
        self._lock         = threading.Lock()

        # Cache de modelos llama-cpp-python (um por alma, lazy)
        self._modelos_cache: Dict[str, Any] = {}

        self.mapeamento_modelos = {
            "EVA":        "tinyllama_base_EVA_q4_0.gguf",
            "LUMINA":     "Qwen_LUMINA_Q4_K_M.gguf",
            "NYRA":       "NYRA_Q4_KM.gguf",
            "YUNA":       "tinyllama_base_Yuna_Q4_K_M.gguf",
            "KAIYA":      "KAIYA_modelo_q4_0.gguf",
            "WELLINGTON": "Qwen_WELLINGTON_Final_Q4_K_M.gguf",
        }
        self.status: Dict[str, str] = {a: "nao_carregado" for a in self.mapeamento_modelos}

        backend = "llama-cpp-python (GPU)" if _LLAMA_CPP_OK else "llama-cli.exe (CPU fallback)"
        logger.info("✅ LlamaExeClient inicializado")
        logger.info("   Executável:      %s", self.executavel)
        logger.info("   Modelos:         %d", len(self.mapeamento_modelos))
        logger.info("   GPU layers:      %d", self.gpu_layers)
        logger.info("   Backend:         %s", backend)

    # ── Carregamento lazy do modelo llama-cpp-python ────────────────────────

    def _obter_modelo_cpp(self, alma: str) -> Optional[Any]:
        """Carrega (ou retorna do cache) o modelo via llama-cpp-python.
        Usa _GPU_LOCK para garantir que apenas um modelo seja carregado por vez."""
        if not _LLAMA_CPP_OK:
            return None

        with self._lock:
            if alma in self._modelos_cache:
                return self._modelos_cache[alma]

        modelo_path = self.pasta_modelos / self.mapeamento_modelos[alma]
        if not modelo_path.exists():
            logger.error("Modelo nao encontrado: %s", modelo_path)
            return None

        # Aguardar a GPU estar livre (EncarnacaoAPI pode estar carregando)
        logger.info("Aguardando GPU livre para carregar %s...", alma)
        got_lock = _GPU_LOCK.acquire(timeout=90)  # aguarda até 90s
        if not got_lock:
            logger.warning("GPU ocupada apos 90s — tentando sem lock para %s", alma)

        try:
            for n in [self.gpu_layers, 22, 16, 8, 4, 1]:
                try:
                    logger.info("Carregando %s na GPU (n_gpu_layers=%d)...", alma, n)
                    model = _Llama(
                        model_path=str(modelo_path),
                        n_gpu_layers=n,
                        n_ctx=512,
                        verbose=False,
                    )
                    with self._lock:
                        self._modelos_cache[alma] = model
                    self.status[alma] = "carregado_gpu"
                    logger.info("%s carregado na GPU (n_gpu_layers=%d)", alma, n)
                    return model
                except Exception as e:
                    logger.warning("GPU n_gpu_layers=%d falhou para %s: %s", n, alma, e)
                    gc.collect()
                    time.sleep(0.5)

            logger.error("Todos os modos GPU falharam para %s -- carregando na CPU", alma)
            try:
                model = _Llama(
                    model_path=str(modelo_path),
                    n_gpu_layers=0,
                    n_ctx=512,
                    verbose=False,
                )
                with self._lock:
                    self._modelos_cache[alma] = model
                self.status[alma] = "carregado_cpu"
                return model
            except Exception as e:
                logger.error("Falha total no carregamento de %s: %s", alma, e)
                return None
        finally:
            if got_lock:
                _GPU_LOCK.release()

    # ── API pública ─────────────────────────────────────────────────────────

    def carregar_modelos(self) -> bool:
        for alma in self.mapeamento_modelos:
            self.status[alma] = "pronto"
            logger.info("✅ %s: pronto para uso", alma)
        logger.info("✅ Todos os %d modelos prontos (carregamento lazy)", len(self.mapeamento_modelos))
        return True

    def generate_response(self, request: dict) -> str:
        alma        = request.get("ai_id", "EVA").upper()
        prompt      = request.get("prompt") or request.get("texto", "")
        max_tokens  = int(request.get("max_tokens", 256))
        temperature = float(request.get("temperature", 0.7))

        if alma not in self.mapeamento_modelos:
            logger.error("❌ Alma desconhecida: %s", alma)
            return f"[{alma}] Alma não reconhecida"

        logger.info("🚀 Gerando resposta para %s...", alma)

        # ── Caminho 1: llama-cpp-python com GPU ──────────────────────────
        if _LLAMA_CPP_OK:
            model = self._obter_modelo_cpp(alma)
            if model is not None:
                try:
                    saida = model(
                        prompt,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        stop=["</s>", "\n\n\n"],
                        echo=False,
                    )
                    resposta = saida["choices"][0]["text"].strip() if saida.get("choices") else ""
                    if not resposta:
                        resposta = f"[{alma}] (resposta vazia)"
                    logger.info("✅ Resposta gerada para %s (%d chars) via GPU", alma, len(resposta))
                    return resposta
                except Exception as e:
                    logger.error("❌ Erro llama-cpp-python para %s: %s", alma, e)
                    # Limpar cache e tentar fallback
                    with self._lock:
                        self._modelos_cache.pop(alma, None)

        # ── Caminho 2: llama-cli.exe subprocess (fallback) ──────────────
        modelo_path = self.pasta_modelos / self.mapeamento_modelos[alma]
        if not modelo_path.exists():
            return f"[{alma}] Modelo não encontrado"

        if not self.executavel.exists():
            return f"[{alma}] Executável llama-cli.exe não encontrado"

        cmd = [
            str(self.executavel),
            "-m",    str(modelo_path),
            "-ngl",  str(self.gpu_layers),
            "-p",    prompt,
            "-n",    str(max_tokens),
            "--temp", str(temperature),
            "--no-display-prompt",
            "--simple-io",
        ]

        try:
            resultado = subprocess.run(
                cmd,
                capture_output=True,
                text=False,
                timeout=300,
                check=False,
            )

            def _dec(b: bytes) -> str:
                if not b: return ""
                for enc in ("utf-8", "cp1252", "latin-1"):
                    try: return b.decode(enc)
                    except UnicodeDecodeError: continue
                return b.decode("utf-8", errors="replace")

            stdout_txt = _dec(resultado.stdout)
            stderr_txt = _dec(resultado.stderr)

            if resultado.returncode != 0:
                logger.error("❌ Exe código %d: %s", resultado.returncode, stderr_txt[:200])
                return f"[{alma}] Erro na geração"

            resposta = stdout_txt.strip() or f"[{alma}] (resposta vazia)"
            logger.info("✅ Resposta via exe para %s (%d chars)", alma, len(resposta))
            return resposta

        except subprocess.TimeoutExpired:
            logger.error("❌ Timeout na geração para %s", alma)
            return f"[{alma}] Tempo limite excedido"
        except Exception as e:
            logger.error("❌ Erro no subprocess para %s: %s", alma, e)
            return f"[{alma}] Erro interno"

    def get_status(self) -> Dict[str, Any]:
        return {
            "modelos_carregados": sum(1 for s in self.status.values() if s != "nao_carregado"),
            "total_modelos":      len(self.status),
            "status_detalhado":   self.status.copy(),
            "gpu_layers":         self.gpu_layers,
            "backend":            "llama-cpp-python" if _LLAMA_CPP_OK else "llama-cli.exe",
            "modelos_em_cache":   list(self._modelos_cache.keys()),
            "llama_exe_client":   True,
        }

    def shutdown(self):
        logger.info("🛑 LlamaExeClient encerrando — liberando modelos...")
        with self._lock:
            for alma, model in self._modelos_cache.items():
                try:
                    del model
                except Exception:
                    pass
            self._modelos_cache.clear()
        gc.collect()
        logger.info("🛑 LlamaExeClient encerrado")