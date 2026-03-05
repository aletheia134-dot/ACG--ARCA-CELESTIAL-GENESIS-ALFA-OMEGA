# -*- coding: utf-8 -*-
"""
ARCA CELESTIAL GENESIS - PARALLEL LLM ENGINE
Orquestra 6 LLMs em paralelo mas com carregamento pesado seriado para evitar picos de RAM.
Local: src/core/parallel_llm_engine.py

âš ï¸ MODO SIMULAÇÍO REMOVIDO - Erros são reportados explicitamente
"""
import logging
import os
import threading
import time
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import json

logger = logging.getLogger("ParallelLLMEngine")

# Tenta importar llama-cpp-python
try:
    from llama_cpp import Llama  # type: ignore
    LLAMA_CPP_DISPONIVEL = True
except Exception:
    LLAMA_CPP_DISPONIVEL = False
    logger.critical("âŒ CRÍTICO: llama-cpp-python NÍO INSTALADO. Modelos não serão carregados.")


def find_models_dir(configured: Optional[str] = None) -> Path:
    from os import environ

    def _is_model_folder(p: Path) -> bool:
        if not p.exists() or not p.is_dir():
            return False
        checks = ["config.json", "tokenizer.json", "pytorch_model.bin", "model.safetensors"]
        for fname in checks:
            if (p / fname).exists():
                return True
        exts = (".safetensors", ".gguf", ".bin", ".pt")
        try:
            for ext in exts:
                for _ in p.rglob(f"*{ext}"):
                    return True
        except Exception:
            pass
        return False

    try:
        if configured:
            p = Path(configured)
            if p.exists():
                logger.info("ParallelLLMEngine: usando MODELOS_DIR configurado: %s", p.resolve())
                return p.resolve()
    except Exception:
        pass

    envp = os.environ.get("MODELOS_DIR")
    if envp:
        p = Path(envp)
        if p.exists():
            logger.info("ParallelLLMEngine: usando MODELOS_DIR via env: %s", p.resolve())
            return p.resolve()

    cwd = Path.cwd()
    candidate_names = ["modelos", "models", "LLM_Models", "infraestrutura/LLM_Models", "model"]
    for base in [cwd] + list(cwd.parents):
        for name in candidate_names:
            cand = (base / name)
            if cand.exists() and cand.is_dir():
                if _is_model_folder(cand):
                    logger.info("ParallelLLMEngine: detectado diretório de modelos automático: %s", cand.resolve())
                    return cand.resolve()
                logger.info("ParallelLLMEngine: achou diretório candidato: %s (sem verificação detalhada)", cand.resolve())
                return cand.resolve()

    for base in [cwd] + list(cwd.parents):
        try:
            for child in base.iterdir():
                if not child.is_dir():
                    continue
                if _is_model_folder(child):
                    logger.info("ParallelLLMEngine: detectado diretório de modelos em child: %s", child.resolve())
                    return child.resolve()
        except Exception:
            continue

    for fallback in [cwd / "modelos", cwd / "infraestrutura" / "LLM_Models"]:
        if fallback.exists() and fallback.is_dir():
            logger.info("ParallelLLMEngine: usando fallback de diretório de modelos: %s", fallback.resolve())
            return fallback.resolve()

    logger.warning("ParallelLLMEngine: nao encontrou diretório de modelos; usando cwd: %s", cwd.resolve())
    return cwd.resolve()


class ParallelLLMEngine:
    """
    Orquestra 6 LLMs em paralelo, um para cada IA.
    Carregamento pesado (instanciação do Llama) é seriado por um semáforo para evitar picos de memória,
    mas a interface permanece paralela (futuros/executor).

    âš ï¸ SEM MODO SIMULAÇÍO - Erros são reportados explicitamente.
    """

    def __init__(self, config):
        self.config = config or {}
        self.logger = logging.getLogger("ParallelLLMEngine")

        self.nomes_ias = ["EVA", "LUMINA", "NYRA", "YUNA", "KAIYA", "WELLINGTON"]
        self.modelos: Dict[str, Any] = {ia: None for ia in self.nomes_ias}
        self.status: Dict[str, str] = {ia: "nao_carregado" for ia in self.nomes_ias}

        # Configura executor - tamanho configurável (numero de workers para tarefas assíncronas)
        try:
            default_workers = len(self.nomes_ias)
            workers = int(self.config.get("LLM_WORKERS", str(default_workers))) if isinstance(self.config, dict) else int(getattr(self.config, "LLM_WORKERS", default_workers))
        except Exception:
            workers = len(self.nomes_ias)
        self.executor = ThreadPoolExecutor(max_workers=workers)

        # Descobre diretório de modelos
        configured_dir = None
        try:
            if isinstance(self.config, dict):
                configured_dir = self.config.get("MODELOS_DIR")
            else:
                configured_dir = getattr(self.config, "MODELOS_DIR", None)
        except Exception:
            logger.warning("âš ï¸ configured_dir não disponível")
            configured_dir = None
        self.modelo_dir = find_models_dir(configured_dir)

        # Carregamento: timeout e concorrencia (semáforo) configuráveis
        try:
            self.model_load_timeout = int(self.config.get("MODEL_LOAD_TIMEOUT", "180")) if isinstance(self.config, dict) else int(getattr(self.config, "MODEL_LOAD_TIMEOUT", 180))
        except Exception:
            self.model_load_timeout = 180
        try:
            self.model_load_concurrency = int(self.config.get("MODEL_LOAD_CONCURRENCY", "1")) if isinstance(self.config, dict) else int(getattr(self.config, "MODEL_LOAD_CONCURRENCY", 1))
        except Exception:
            self.model_load_concurrency = 1
        # semáforo para limitar quantos modelos são instanciados ao mesmo tempo
        self._load_semaphore = threading.Semaphore(self.model_load_concurrency)

        # Parâmetros de concorrência e jitter para chamadas ao backend LLM (ajustáveis via config/env)
        try:
            self.llm_call_concurrency = int(self.config.get("LLM_CALL_CONCURRENCY", "1")) if isinstance(self.config, dict) else int(getattr(self.config, "LLM_CALL_CONCURRENCY", 1))
        except Exception:
            self.llm_call_concurrency = 1

        try:
            self.response_delay_min_ms = int(self.config.get("RESPONSE_DELAY_MIN_MS", "0")) if isinstance(self.config, dict) else int(getattr(self.config, "RESPONSE_DELAY_MIN_MS", 0))
            self.response_delay_max_ms = int(self.config.get("RESPONSE_DELAY_MAX_MS", "150")) if isinstance(self.config, dict) else int(getattr(self.config, "RESPONSE_DELAY_MAX_MS", 150))
        except Exception:
            self.response_delay_min_ms = 0
            self.response_delay_max_ms = 150

        # semaphore para limitar quantas chamadas nativas ao LLM podem ocorrer simultaneamente
        self._llm_call_semaphore = threading.Semaphore(self.llm_call_concurrency)

        # Tenta carregar model_map.json (mapeamento explícito)
        self.model_map: Dict[str, str] = {}
        try:
            map_file = self.modelo_dir / "model_map.json"
            if map_file.exists():
                with map_file.open("r", encoding="utf-8") as fh:
                    raw = json.load(fh)
                for k, v in (raw.items() if isinstance(raw, dict) else []):
                    if not v:
                        continue
                    ia_key = k.upper()
                    p = Path(v)
                    if not p.is_absolute():
                        p = (self.modelo_dir / v)
                    if p.exists():
                        self.model_map[ia_key] = str(p.resolve())
                    else:
                        self.model_map[ia_key] = str(p)
                if self.model_map:
                    self.logger.info("ParallelLLMEngine: carregado model_map.json com mapeamento para: %s", ", ".join(self.model_map.keys()))
        except Exception:
            self.logger.exception("ParallelLLMEngine: falha ao ler model_map.json; ignorando.")

        try:
            self.n_gpu_layers = int(self.config.get("N_GPU_LAYERS", "-1")) if isinstance(self.config, dict) else int(getattr(self.config, "N_GPU_LAYERS", -1))
        except Exception:
            self.n_gpu_layers = -1
        try:
            self.n_ctx = int(self.config.get("N_CTX", "4096")) if isinstance(self.config, dict) else int(getattr(self.config, "N_CTX", 4096))
        except Exception:
            self.n_ctx = 4096

        self.logger.info("OK ParallelLLMEngine inicializado (modelo_dir=%s)", str(self.modelo_dir))
        self.logger.info("ParallelLLMEngine: LLM_WORKERS=%s, MODEL_LOAD_TIMEOUT=%ss, MODEL_LOAD_CONCURRENCY=%s, LLM_CALL_CONCURRENCY=%s, RESPONSE_DELAY_MS=[%s-%s]",
                         workers, self.model_load_timeout, self.model_load_concurrency, self.llm_call_concurrency, self.response_delay_min_ms, self.response_delay_max_ms)

    def carregar_modelos(self) -> bool:
        """
        Carrega os 6 modelos em paralelo (futuros), mas a instância Llama será criada respeitando o semáforo.
        Retorna True se todos os modelos carregaram, False caso contrário.
        âš ï¸ SEM MODO SIMULAÇÍO - Se llama-cpp não estiver disponível, retorna False.
        """
        self.logger.info("Iniciando carregamento de 6 LLMs em paralelo...")
        
        if not LLAMA_CPP_DISPONIVEL:
            self.logger.error("âŒ ERRO CRÍTICO: llama-cpp-python não instalado. Impossível carregar modelos.")
            return False

        futures = {}
        for ia in self.nomes_ias:
            futures[ia] = self.executor.submit(self._carregar_modelo_ia, ia)

        modelos_carregados = 0
        for ia, future in futures.items():
            try:
                resultado = future.result(timeout=self.model_load_timeout)
                if resultado:
                    modelos_carregados += 1
                    self.logger.info(f"âœ… OK {ia}: Modelo carregado com sucesso")
                else:
                    self.logger.error(f"âŒ ERRO {ia}: Falha ao carregar modelo")
                    self.status[ia] = "erro"
            except Exception as e:
                self.logger.error(f"âŒ ERRO {ia}: {e}")
                self.status[ia] = "erro"

        sucesso = modelos_carregados == len(self.nomes_ias)
        self.logger.info(f"Resultado: {modelos_carregados}/{len(self.nomes_ias)} modelos carregados")
        return sucesso

    def _carregar_modelo_ia(self, ia_nome: str) -> bool:
        """Procura pelo modelo e instancia Llama; a instanciação é protegida por semáforo."""
        try:
            modelo_path = self._encontrar_modelo(ia_nome)
            if not modelo_path or not modelo_path.exists():
                self.logger.error(f"âŒ ERRO {ia_nome}: Modelo não encontrado em {modelo_path}")
                return False

            # Adquire semáforo antes de instanciar Llama (operaçao custosa em RAM)
            acquired = False
            try:
                self._load_semaphore.acquire()
                acquired = True
                # instancia Llama (pode consumir muita RAM)
                self.logger.info(f"Carregando modelo {ia_nome} de {modelo_path}...")
                self.modelos[ia_nome] = Llama(
                    model_path=str(modelo_path),
                    n_gpu_layers=self.n_gpu_layers,
                    n_ctx=self.n_ctx,
                    verbose=False
                )
                self.status[ia_nome] = "carregado"
                return True
            finally:
                if acquired:
                    try:
                        self._load_semaphore.release()
                    except Exception:
                        pass

        except Exception as e:
            self.logger.error(f"âŒ ERRO ao carregar {ia_nome}: {e}")
            self.status[ia_nome] = "erro"
            return False

    def _encontrar_modelo(self, ia_nome: str) -> Optional[Path]:
        ia_key = ia_nome.upper()
        try:
            if ia_key in self.model_map:
                p = Path(self.model_map[ia_key])
                if not p.is_absolute():
                    p = (self.modelo_dir / p)
                if p.exists():
                    return p
        except Exception:
            pass

        ia_variants = [ia_nome, ia_nome.lower(), ia_nome.upper()]
        exts = [".gguf", ".safetensors", ".bin", ".pt"]
        for ia in ia_variants:
            for ext in exts:
                cand = self.modelo_dir / f"{ia}{ext}"
                if cand.exists():
                    return cand
        for ia in ia_variants:
            subdir = self.modelo_dir / ia
            if subdir.exists() and subdir.is_dir():
                for ext in exts:
                    for p in subdir.rglob(f"*{ext}"):
                        return p
                for p in subdir.rglob("pytorch_model.bin"):
                    return p
        nested = self.modelo_dir / "modelos"
        if nested.exists() and nested.is_dir():
            for ia in ia_variants:
                for ext in exts:
                    cand = nested / f"{ia}{ext}"
                    if cand.exists():
                        return cand
                sub = nested / ia
                if sub.exists() and sub.is_dir():
                    for ext in exts:
                        for p in sub.rglob(f"*{ext}"):
                            return p
        try:
            for ext in exts:
                for p in self.modelo_dir.rglob(f"*{ia_nome[:3]}*{ext}"):
                    return p
        except Exception:
            pass
        return None

    def generate_response(self, request: Dict[str, Any]) -> str:
        ia_id = request.get('ai_id', 'EVA').upper()
        prompt = request.get('prompt', '')
        max_tokens = request.get('max_tokens', 256)
        temperature = request.get('temperature', 0.7)

        if not prompt:
            return "[ERRO] Prompt vazio"
        if ia_id not in self.nomes_ias:
            return f"[ERRO] IA '{ia_id}' nao conhecida"
            
        # âš ï¸ SEM SIMULAÇÍO - Se modelo não carregado, retorna erro explícito
        if self.status[ia_id] == "erro" or self.modelos[ia_id] is None:
            erro_msg = f"âŒ ERRO: Modelo da {ia_id} não carregado. Verifique os logs."
            self.logger.error(erro_msg)
            return erro_msg

        try:
            modelo = self.modelos[ia_id]

            # --- espera/jitter antes de tentar usar o backend (espalha picos) ---
            if getattr(self, "response_delay_max_ms", 0) > 0:
                try:
                    delay_ms = random.randint(getattr(self, "response_delay_min_ms", 0), getattr(self, "response_delay_max_ms", 0))
                except Exception:
                    delay_ms = 0
                if delay_ms > 0:
                    time.sleep(delay_ms / 1000.0)

            # --- controlar concorrência de chamadas nativas ao LLM ---
            acquired = False
            try:
                # aguarda até permissão (pode ajustar timeout se desejar)
                self._llm_call_semaphore.acquire()
                acquired = True

                # chamada nativa protegida pelo semáforo (evita condições de corrida em ggml)
                resposta = modelo.create_completion(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=["<|end|>", "\n\n"],
                )
            finally:
                if acquired:
                    try:
                        self._llm_call_semaphore.release()
                    except Exception:
                        pass

            texto = resposta['choices'][0]['text'].strip()
            return texto if texto else f"[{ia_id}] Resposta vazia"
            
        except Exception as e:
            erro_msg = f"âŒ ERRO ao gerar resposta para {ia_id}: {e}"
            self.logger.error(erro_msg)
            return erro_msg

    def execute_paralelo_6(self, prompt: str) -> Dict[str, str]:
        self.logger.info(f"Executando paralelo 6: '{prompt[:50]}...'")
        futures = {}
        for ia in self.nomes_ias:
            request = {
                'ai_id': ia,
                'prompt': prompt,
                'max_tokens': 256,
                'temperature': 0.7
            }
            futures[ia] = self.executor.submit(self.generate_response, request)
        respostas = {}
        for ia, future in futures.items():
            try:
                respostas[ia] = future.result(timeout=30)
                self.logger.info(f"âœ… OK {ia}: Resposta gerada ({len(respostas[ia])} chars)")
            except Exception as e:
                respostas[ia] = f"[ERRO] {e}"
                self.logger.error(f"âŒ ERRO {ia}: {e}")
        return respostas

    def get_status(self) -> Dict[str, Any]:
        return {
            "modelos_carregados": sum(1 for s in self.status.values() if s == "carregado"),
            "total_modelos": len(self.nomes_ias),
            "status_detalhado": self.status.copy(),
            "llama_cpp_disponivel": LLAMA_CPP_DISPONIVEL
        }

    def shutdown(self):
        self.logger.info("Encerrando ParallelLLMEngine...")
        self.executor.shutdown(wait=True)
        for ia in self.nomes_ias:
            if self.modelos[ia] is not None:
                self.modelos[ia] = None
        self.logger.info("âœ… OK ParallelLLMEngine encerrado")
