# -*- coding: utf-8 -*-
"""
ARCA CELESTIAL GENESIS - PARALLEL LLM ENGINE
Orquestra LLMs em paralelo com carregamento seriado para evitar picos de RAM.
Local: src/core/parallel_llm_engine.py

✨ ATUALIZADO: Detector automático de modelos .gguf
   Não importa o nome do arquivo, ele descobre automaticamente!
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
    logger.critical("❌ CRÍTICO: llama-cpp-python NÃO INSTALADO. Modelos não serão carregados.")

# ============================================================================
# GPU Resource Manager (mantido INTEGRALMENTE)
# ============================================================================
try:
    import torch
    TORCH_DISPONIVEL = True
except ImportError:
    TORCH_DISPONIVEL = False
    logger.warning("⚠️ PyTorch não instalado. Monitoramento de GPU limitado.")

try:
    import psutil
    PSUTIL_DISPONIVEL = True
except ImportError:
    PSUTIL_DISPONIVEL = False
    logger.warning("⚠️ psutil não instalado. Detecção de processos 3D desabilitada.")

from enum import Enum
from dataclasses import dataclass
from typing import Set

class GPUModelPriority(Enum):
    BAIXA = 1    # Pode ser movido para CPU facilmente
    MEDIA = 2     # Tenta manter na GPU, mas pode mover
    ALTA = 3      # Prioridade máxima para ficar na GPU

@dataclass
class GPUModelInfo:
    name: str
    priority: GPUModelPriority
    vram_usage_mb: float
    current_device: str  # "gpu" ou "cpu"
    last_used: float
    can_migrate: bool = True

class GPUResourceManager:
    """
    Gerencia dinamicamente quais modelos ficam na GPU baseado na carga total do sistema.
    """
    
    def __init__(self, total_vram_gb: float = 8.0, safety_margin_gb: float = 1.0):
        self.total_vram = total_vram_gb * 1024  # Converter para MB
        self.safety_margin = safety_margin_gb * 1024  # Margem de segurança em MB
        self.max_vram_for_llms = self.total_vram - self.safety_margin
        
        self.models: Dict[str, GPUModelInfo] = {}
        self.lock = threading.Lock()
        self.monitoring = False
        self.monitor_thread = None
        
        # Detecção de processos 3D
        self.detected_3d_processes: Set[str] = set()
        
        logger.info(f"GPU Resource Manager inicializado:")
        logger.info(f"  VRAM Total: {self.total_vram/1024:.1f}GB")
        logger.info(f"  Margem Segurança: {self.safety_margin/1024:.1f}GB")
        logger.info(f"  VRAM para LLMs: {self.max_vram_for_llms/1024:.1f}GB")
    
    def register_model(self, name: str, priority: GPUModelPriority, vram_mb: float):
        """Registra um modelo no gerenciador"""
        with self.lock:
            self.models[name] = GPUModelInfo(
                name=name,
                priority=priority,
                vram_usage_mb=vram_mb,
                current_device="gpu",  # Assume GPU inicialmente
                last_used=time.time(),
                can_migrate=True
            )
            logger.info(f"✅ Modelo {name} registrado (Prioridade: {priority.name}, VRAM: {vram_mb:.0f}MB)")
    
    def start_monitoring(self, engine):
        """Inicia o monitoramento de recursos"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(engine,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("🔍 Monitoramento GPU iniciado")
    
    def _monitor_loop(self, engine):
        """Loop principal de monitoramento"""
        while self.monitoring:
            try:
                self._check_and_balance(engine)
                time.sleep(5)  # Verifica a cada 5 segundos
            except Exception as e:
                logger.error(f"Erro no monitoramento: {e}")
    
    def _check_and_balance(self, engine):
        """Verifica uso de VRAM e rebalanceia se necessário"""
        
        # 1. Verifica uso atual da GPU
        gpu_usage = self._get_gpu_usage()
        vram_used = gpu_usage.get('vram_used_mb', 0)
        vram_total = gpu_usage.get('vram_total_mb', self.total_vram)
        
        # 2. Detecta processos 3D rodando
        has_3d_process = self._detect_3d_processes()
        
        # 3. Calcula quanto VRAM os LLMs estão usando
        llms_in_gpu = [m for m in self.models.values() if m.current_device == "gpu"]
        llm_vram_used = sum(m.vram_usage_mb for m in llms_in_gpu)
        
        # 4. Estima VRAM disponível para LLMs
        other_process_vram = max(0, vram_used - llm_vram_used)
        available_for_llms = vram_total - other_process_vram - self.safety_margin
        
        logger.debug(f"VRAM: Total={vram_total/1024:.1f}GB, "
                    f"Usado={vram_used/1024:.1f}GB, "
                    f"LLMs={llm_vram_used/1024:.1f}GB, "
                    f"Disponível={available_for_llms/1024:.1f}GB")
        
        # 5. Se temos processos 3D, reduz agressivamente
        target_vram = available_for_llms
        if has_3d_process:
            logger.info("🎮 Processo 3D detectado! Reduzindo uso de VRAM")
            target_vram = min(target_vram, self.total_vram * 0.5)  # Máx 4GB com jogo
        
        # 6. Calcula quantos LLMs podem ficar na GPU
        max_llms_in_gpu = self._calculate_max_llms(target_vram)
        
        # 7. Rebalanceia se necessário
        self._rebalance_models(engine, max_llms_in_gpu, has_3d_process)
    
    def _get_gpu_usage(self) -> dict:
        """Obtém uso atual da GPU via PyTorch/nvidia-smi"""
        if TORCH_DISPONIVEL and torch.cuda.is_available():
            try:
                vram_total = torch.cuda.get_device_properties(0).total_memory / 1024 / 1024  # MB
                vram_used = torch.cuda.memory_allocated(0) / 1024 / 1024  # MB
                
                return {
                    'vram_total_mb': vram_total,
                    'vram_used_mb': vram_used,
                    'vram_free_mb': vram_total - vram_used
                }
            except:
                pass
        
        # Fallback: assume valores padrão
        return {
            'vram_total_mb': self.total_vram,
            'vram_used_mb': 0,
            'vram_free_mb': self.total_vram
        }
    
    def _detect_3d_processes(self) -> bool:
        """Detecta se há processos 3D rodando (jogos, renderização)"""
        if not PSUTIL_DISPONIVEL:
            return False
            
        try:
            # Lista de processos conhecidos de jogos/3D
            known_3d_processes = [
                "unity", "unreal", "blender", "maya", "3dsmax",
                "eldenring", "cyberpunk", "gta", "fortnite",
                "dota", "csgo", "valorant", "minecraft",
                "chrome.exe",  # Chrome com WebGL
                "firefox.exe", # Firefox com WebGL
            ]
            
            for proc in psutil.process_iter(['name']):
                try:
                    proc_name = proc.info['name'].lower()
                    for known in known_3d_processes:
                        if known in proc_name:
                            logger.debug(f"Processo 3D detectado: {proc_name}")
                            return True
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Erro na detecção de processos 3D: {e}")
            
        return False
    
    def _calculate_max_llms(self, available_vram_mb: float) -> int:
        """Calcula quantos LLMs cabem na VRAM disponível"""
        models_by_priority = sorted(
            self.models.values(),
            key=lambda m: (m.priority.value, -m.vram_usage_mb),
            reverse=True  # Maior prioridade primeiro
        )
        
        used_vram = 0
        count = 0
        
        for model in models_by_priority:
            if used_vram + model.vram_usage_mb <= available_vram_mb:
                used_vram += model.vram_usage_mb
                count += 1
            else:
                break
                
        return count
    
    def _rebalance_models(self, engine, target_gpu_count: int, has_3d_process: bool):
        """Move modelos entre GPU/CPU para atingir o alvo"""
        
        # Modelos atualmente na GPU
        gpu_models = sorted(
            [m for m in self.models.values() if m.current_device == "gpu"],
            key=lambda m: (m.priority.value, m.last_used)
        )
        
        # Modelos atualmente na CPU
        cpu_models = [m for m in self.models.values() if m.current_device == "cpu"]
        
        # Se temos muitos na GPU, move alguns para CPU
        if len(gpu_models) > target_gpu_count:
            to_move = len(gpu_models) - target_gpu_count
            logger.info(f"⚠️ Movendo {to_move} modelos para CPU (alvo: {target_gpu_count} na GPU)")
            
            for i in range(to_move):
                if i < len(gpu_models):
                    model = gpu_models[i]
                    if model.can_migrate:
                        self._move_model_to_cpu(engine, model)
        
        # Se temos poucos na GPU e espaço livre, move da CPU para GPU
        elif len(gpu_models) < target_gpu_count and not has_3d_process:
            can_move = min(
                target_gpu_count - len(gpu_models),
                len(cpu_models)
            )
            
            if can_move > 0:
                logger.info(f"⬆️ Movendo {can_move} modelos para GPU")
                
                # Pega modelos de maior prioridade da CPU
                cpu_models_high_priority = sorted(
                    cpu_models,
                    key=lambda m: m.priority.value,
                    reverse=True
                )
                
                for i in range(can_move):
                    if i < len(cpu_models_high_priority):
                        model = cpu_models_high_priority[i]
                        self._move_model_to_gpu(engine, model)
    
    def _move_model_to_cpu(self, engine, model_info):
        """Move um modelo específico da GPU para CPU"""
        logger.info(f"🔄 Movendo {model_info.name} para CPU...")
        
        try:
            # Salva referência atual
            modelo_atual = engine.modelos.get(model_info.name)
            if modelo_atual is None:
                logger.warning(f"Modelo {model_info.name} não encontrado no engine")
                return
            
            # Recarrega em modo CPU
            modelo_path = engine._encontrar_modelo(model_info.name)
            if modelo_path and modelo_path.exists():
                novo_modelo = Llama(
                    model_path=str(modelo_path),
                    n_gpu_layers=0,  # Força CPU
                    n_ctx=engine.n_ctx,
                    verbose=False
                )
                engine.modelos[model_info.name] = novo_modelo
                model_info.current_device = "cpu"
                logger.info(f"✅ {model_info.name} agora na CPU")
            else:
                logger.error(f"❌ Caminho do modelo {model_info.name} não encontrado")
                
        except Exception as e:
            logger.error(f"❌ Erro ao mover {model_info.name} para CPU: {e}")
    
    def _move_model_to_gpu(self, engine, model_info):
        """Move um modelo específico da CPU para GPU"""
        logger.info(f"🔄 Movendo {model_info.name} para GPU...")
        
        try:
            # Salva referência atual
            modelo_atual = engine.modelos.get(model_info.name)
            if modelo_atual is None:
                logger.warning(f"Modelo {model_info.name} não encontrado no engine")
                return
            
            # Recarrega em modo GPU
            modelo_path = engine._encontrar_modelo(model_info.name)
            if modelo_path and modelo_path.exists():
                # Usa a configuração de GPU do engine
                n_gpu = engine.n_gpu_layers if engine.n_gpu_layers != -1 else -2
                novo_modelo = Llama(
                    model_path=str(modelo_path),
                    n_gpu_layers=n_gpu,
                    n_ctx=engine.n_ctx,
                    verbose=False
                )
                engine.modelos[model_info.name] = novo_modelo
                model_info.current_device = "gpu"
                model_info.last_used = time.time()
                logger.info(f"✅ {model_info.name} agora na GPU")
            else:
                logger.error(f"❌ Caminho do modelo {model_info.name} não encontrado")
                
        except Exception as e:
            logger.error(f"❌ Erro ao mover {model_info.name} para GPU: {e}")
    
    def stop_monitoring(self):
        """Para o monitoramento"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        logger.info("🛑 Monitoramento GPU parado")


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

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


# ============================================================================
# PARALLEL LLM ENGINE - VERSÃO ATUALIZADA COM DETECTOR AUTOMÁTICO
# ============================================================================

class ParallelLLMEngine:
    """
    Orquestra LLMs em paralelo, um para cada IA.
    Carregamento pesado (instanciação do Llama) é seriado por um semáforo para evitar picos de memória.
    
    ✨ AGORA COM DETECTOR AUTOMÁTICO DE MODELOS .gguf
       Não importa o nome do arquivo, ele descobre automaticamente!
    """

    def __init__(self, config):
        self.config = config or {}
        self.logger = logging.getLogger("ParallelLLMEngine")

        # ============================================================================
        # DETECTOR AUTOMÁTICO DE MODELOS .GGUF (A MÁGICA ACONTECE AQUI!)
        # ============================================================================
        self.nomes_ias = []
        self.arquivos_modelos = {}  # Mapeia nome_da_alma → caminho_do_arquivo
        self.modelo_para_alma = {}  # Mapeia nome_arquivo → nome_alma

        # Lista de sufixos comuns a serem removidos para gerar nomes de alma limpos
        sufixos_remover = [
            "_q4_0", "_q4_k_m", "_q5_0", "_q5_k_m", "_q8_0",
            "_q2_k", "_q3_k", "_q4_k", "_q5_k", "_q6_k", "_q8_k",
            "_Q4_K_M", "_Q4_0", "_Q5_0", "_Q5_K_M", "_Q6_K", "_Q8_0",
            "_Q2_K", "_Q3_K", "_K_M", "_Q4_KM", "_Final",
            ".gguf", ".bin", ".pt", ".safetensors"
        ]
        
        # Lista de prefixos comuns a serem removidos
        prefixos_remover = [
            "tinyllama_base_", "Qwen_", "llama-2-", "mistral-",
            "zephyr-", "neural-", "dolphin-", "solar-", "gemma-",
            "tinyllama_", "qwen_", "llama-", "falcon-", "mpt-",
            "opt-", "phi-", "stablelm-", "redpajama-", "pythia-",
            "gpt-", "bloom-", "vicuna-", "alpaca-", "wizard-",
            "orca-", "platypus-", "samantha-", "airoboros-"
        ]

        # Descobre diretório de modelos
        configured_dir = None
        try:
            if isinstance(self.config, dict):
                configured_dir = self.config.get("MODELOS_DIR")
            else:
                configured_dir = getattr(self.config, "MODELOS_DIR", None)
        except Exception:
            logger.warning("⚠️ configured_dir não disponível")
            configured_dir = None
        self.modelo_dir = find_models_dir(configured_dir)

        # ESCANEAR TODOS OS ARQUIVOS .gguf NA PASTA
        if not self.modelo_dir.exists() or not self.modelo_dir.is_dir():
            raise RuntimeError(f"❌ Diretório de modelos não encontrado: {self.modelo_dir}")

        self.logger.info(f"🔍 Escaneando diretório em busca de modelos .gguf: {self.modelo_dir}")
        quantidade_encontrada = 0

        for arquivo in self.modelo_dir.iterdir():
            if arquivo.is_file() and arquivo.suffix.lower() == ".gguf":
                quantidade_encontrada += 1
                
                # Nome do arquivo sem extensão
                nome_arquivo = arquivo.stem
                
                # GERAR NOME DA ALMA a partir do arquivo (remover prefixos/sufixos)
                nome_alma = nome_arquivo
                
                # Remover sufixos
                for sufixo in sufixos_remover:
                    if nome_alma.lower().endswith(sufixo.lower()):
                        nome_alma = nome_alma[:-len(sufixo)]
                        break
                
                # Remover prefixos
                for prefixo in prefixos_remover:
                    if nome_alma.lower().startswith(prefixo.lower()):
                        nome_alma = nome_alma[len(prefixo):]
                        break
                
                # Limpar caracteres especiais e espaços
                nome_alma = nome_alma.replace("-", "_").replace(" ", "_").upper()
                
                # Se após limpeza ficou vazio, usar o nome original
                if not nome_alma:
                    nome_alma = nome_arquivo.upper().replace("-", "_").replace(" ", "_")
                
                # Garantir que o nome da alma seja único
                nome_alma_original = nome_alma
                contador = 1
                while nome_alma in self.nomes_ias:
                    nome_alma = f"{nome_alma_original}_{contador}"
                    contador += 1
                
                # Salvar mapeamentos
                self.nomes_ias.append(nome_alma)
                self.arquivos_modelos[nome_alma] = arquivo
                self.modelo_para_alma[nome_arquivo] = nome_alma
                
                self.logger.info(f"📁 Modelo detectado: {arquivo.name} → Alma: {nome_alma}")

        if not self.nomes_ias:
            raise RuntimeError(f"❌ Nenhum modelo .gguf encontrado no diretório: {self.modelo_dir}")

        # Inicializa estruturas internas com os nomes detectados
        self.modelos: Dict[str, Any] = {ia: None for ia in self.nomes_ias}
        self.status: Dict[str, str] = {ia: "nao_carregado" for ia in self.nomes_ias}

        self.logger.info(f"✅ {len(self.nomes_ias)} modelos detectados: {', '.join(self.nomes_ias)}")
        # ============================================================================

        # Configura executor - tamanho configurável
        try:
            default_workers = len(self.nomes_ias)
            workers = int(self.config.get("LLM_WORKERS", str(default_workers))) if isinstance(self.config, dict) else int(getattr(self.config, "LLM_WORKERS", default_workers))
        except Exception:
            workers = len(self.nomes_ias)
        self.executor = ThreadPoolExecutor(max_workers=workers)

        # Carregamento: timeout e concorrencia (semáforo) configuráveis
        try:
            self.model_load_timeout = int(self.config.get("MODEL_LOAD_TIMEOUT", "180")) if isinstance(self.config, dict) else int(getattr(self.config, "MODEL_LOAD_TIMEOUT", 180))
        except Exception:
            self.model_load_timeout = 180
        try:
            self.model_load_concurrency = int(self.config.get("MODEL_LOAD_CONCURRENCY", "1")) if isinstance(self.config, dict) else int(getattr(self.config, "MODEL_LOAD_CONCURRENCY", 1))
        except Exception:
            self.model_load_concurrency = 1
        self._load_semaphore = threading.Semaphore(self.model_load_concurrency)

        # Parâmetros de concorrência e jitter para chamadas ao backend LLM
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

        self._llm_call_semaphore = threading.Semaphore(self.llm_call_concurrency)

        # Tenta carregar model_map.json (mapeamento explícito) - agora como fallback
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
            self.n_gpu_layers = int(self.config.get("N_GPU_LAYERS", "-2"))
        except Exception:
            self.n_gpu_layers = -2
            
        try:
            self.n_ctx = int(self.config.get("N_CTX", "4096")) if isinstance(self.config, dict) else int(getattr(self.config, "N_CTX", 4096))
        except Exception:
            self.n_ctx = 4096

        # Inicialização do Gerenciador de Recursos GPU
        self.gpu_manager = None
        self.gpu_monitoring_enabled = self.config.get("GPU_MONITORING_ENABLED", "true") if isinstance(self.config, dict) else getattr(self.config, "GPU_MONITORING_ENABLED", "true")
        self.gpu_monitoring_enabled = str(self.gpu_monitoring_enabled).lower() == "true"
        
        if self.gpu_monitoring_enabled:
            try:
                if TORCH_DISPONIVEL and torch.cuda.is_available():
                    gpu_name = torch.cuda.get_device_name(0)
                    gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
                    logger.info(f"🎮 GPU DETECTADA: {gpu_name} com {gpu_mem:.1f}GB")
                    logger.info(f"🚀 Configuração GPU layers: {self.n_gpu_layers}")
                    
                    self.gpu_manager = GPUResourceManager(
                        total_vram_gb=gpu_mem,
                        safety_margin_gb=1.0
                    )
                    
                    # Define prioridades para cada IA (agora dinamicamente)
                    # Prioridade padrão: MEDIA para todas
                    for ia in self.nomes_ias:
                        # Definir prioridade baseada em heurística simples
                        prioridade = GPUModelPriority.MEDIA
                        if "EVA" in ia or "EVA" in ia.upper():
                            prioridade = GPUModelPriority.ALTA
                        elif "WELLINGTON" in ia or "WELLINGTON" in ia.upper():
                            prioridade = GPUModelPriority.BAIXA
                        elif "KAIYA" in ia or "KAIYA" in ia.upper():
                            prioridade = GPUModelPriority.BAIXA
                        
                        self.gpu_manager.register_model(
                            ia,
                            prioridade,
                            1200  # VRAM estimada
                        )
                    
                    logger.info("✅ GPU Resource Manager inicializado com sucesso")
                else:
                    logger.warning("⚠️ Nenhuma GPU detectada. Monitoramento GPU desabilitado.")
                    self.gpu_monitoring_enabled = False
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar GPU Resource Manager: {e}")
                self.gpu_monitoring_enabled = False

        self.logger.info("OK ParallelLLMEngine inicializado (modelo_dir=%s)", str(self.modelo_dir))
        self.logger.info("ParallelLLMEngine: LLM_WORKERS=%s, MODEL_LOAD_TIMEOUT=%ss, MODEL_LOAD_CONCURRENCY=%s, LLM_CALL_CONCURRENCY=%s, RESPONSE_DELAY_MS=[%s-%s]",
                         workers, self.model_load_timeout, self.model_load_concurrency, self.llm_call_concurrency, self.response_delay_min_ms, self.response_delay_max_ms)

    # ============================================================================
    # MÉTODO DE CARREGAMENTO SERIAL
    # ============================================================================
    def carregar_modelos(self) -> bool:
        """
        Carrega os modelos em MODO SERIAL (um após o outro) para evitar
        fragmentação de VRAM e crashes durante o carregamento.
        """
        self.logger.info(f"Iniciando carregamento SERIAL de {len(self.nomes_ias)} LLMs (um por um para evitar fragmentação de VRAM)...")
        
        if not LLAMA_CPP_DISPONIVEL:
            self.logger.error("❌ ERRO CRÍTICO: llama-cpp-python não instalado. Impossível carregar modelos.")
            return False

        if self.gpu_manager:
            self.gpu_manager.monitoring = False
            self.logger.info("⏸️ Monitoramento GPU pausado durante carregamento")

        modelos_carregados = 0
        
        for ia in self.nomes_ias:
            self.logger.info(f"⏳ Carregando {ia} (serial)...")
            try:
                resultado = self._carregar_modelo_ia(ia)
                
                if resultado:
                    modelos_carregados += 1
                    self.logger.info(f"[OK] {ia}: Modelo carregado com sucesso")
                    
                    self.logger.info(f"⏸️ Aguardando 2 segundos para estabilização da VRAM...")
                    time.sleep(2)
                    
                    if TORCH_DISPONIVEL and torch.cuda.is_available():
                        try:
                            vram_usada = torch.cuda.memory_allocated(0) / 1e9
                            self.logger.info(f"📊 VRAM atual: {vram_usada:.2f}GB")
                        except:
                            pass
                else:
                    self.logger.error(f"❌ ERRO {ia}: Falha ao carregar modelo")
                    self.status[ia] = "erro"
                    break
                    
            except Exception as e:
                self.logger.error(f"[ERRO FATAL] {ia}: {e}")
                self.status[ia] = "erro"
                break

        if self.gpu_manager:
            self.gpu_manager.monitoring = True
            self.logger.info("▶️ Monitoramento GPU reativado")

        sucesso = modelos_carregados == len(self.nomes_ias)
        self.logger.info(f"Resultado: {modelos_carregados}/{len(self.nomes_ias)} modelos carregados")
        
        if sucesso and self.gpu_monitoring_enabled and self.gpu_manager:
            self.gpu_manager.start_monitoring(self)
        
        return sucesso

    # ============================================================================
    # MÉTODO DE CARREGAMENTO INDIVIDUAL
    # ============================================================================
    def _carregar_modelo_ia(self, ia_nome: str) -> bool:
        """Procura pelo modelo e instancia Llama; a instanciação é protegida por semáforo."""
        try:
            modelo_path = self._encontrar_modelo(ia_nome)
            if not modelo_path or not modelo_path.exists():
                self.logger.error(f"❌ ERRO {ia_nome}: Modelo não encontrado em {modelo_path}")
                return False

            acquired = False
            try:
                self._load_semaphore.acquire()
                acquired = True
                self.logger.info(f"Carregando modelo {ia_nome} de {modelo_path}...")
                
                gpu_layers_tentativas = []
                
                if self.n_gpu_layers != 0:
                    if self.n_gpu_layers == -1:
                        self.logger.warning(f"⚠️ {ia_nome}: n_gpu_layers=-1 detectado. Usando auto-detect...")
                        gpu_layers_tentativas.append(-2)
                    elif self.n_gpu_layers == -2:
                        gpu_layers_tentativas.append(-2)
                    else:
                        gpu_layers_tentativas.append(self.n_gpu_layers)
                else:
                    self.logger.info(f"ℹ️ {ia_nome}: Modo CPU forçado (n_gpu_layers=0)")
                
                gpu_layers_tentativas.append(0)

                ultimo_erro = None
                for n_gpu in gpu_layers_tentativas:
                    try:
                        self.modelos[ia_nome] = Llama(
                            model_path=str(modelo_path),
                            n_gpu_layers=n_gpu,
                            n_ctx=self.n_ctx,
                            verbose=False
                        )
                        if n_gpu == 0 and self.n_gpu_layers != 0:
                            self.logger.warning(
                                f"⚠️ {ia_nome}: GPU falhou. Modelo carregado em MODO CPU."
                            )
                        else:
                            self.logger.info(f"✅ {ia_nome}: Modelo carregado (GPU layers={n_gpu})")
                        self.status[ia_nome] = "carregado"
                        
                        if self.gpu_manager and ia_nome in self.gpu_manager.models:
                            device = "gpu" if n_gpu != 0 else "cpu"
                            self.gpu_manager.models[ia_nome].current_device = device
                            self.gpu_manager.models[ia_nome].last_used = time.time()
                        
                        return True
                    except Exception as e:
                        ultimo_erro = e
                        err_str = str(e).lower()
                        if ("access violation" in err_str or "segfault" in err_str
                                or "0x0000000000000000" in err_str
                                or "winerror 1114" in err_str or "1114" in err_str
                                or "dll" in err_str):
                            if n_gpu != 0:
                                self.logger.warning(
                                    f"⚠️ {ia_nome}: Access violation com n_gpu_layers={n_gpu}. "
                                    f"Tentando CPU..."
                                )
                                continue
                        break
                
                self.logger.error(f"❌ ERRO ao carregar {ia_nome}: {ultimo_erro}")
                self.status[ia_nome] = "erro"
                return False

            finally:
                if acquired:
                    try:
                        self._load_semaphore.release()
                    except Exception:
                        pass

        except Exception as e:
            self.logger.error(f"❌ ERRO ao carregar {ia_nome}: {e}")
            self.status[ia_nome] = "erro"
            return False

    # ============================================================================
    # MÉTODO PARA ENCONTRAR MODELO (ATUALIZADO PARA USAR O MAPEAMENTO)
    # ============================================================================
    def _encontrar_modelo(self, ia_nome: str) -> Optional[Path]:
        """
        Procura pelo arquivo do modelo baseado no nome da alma.
        Agora usa o mapeamento automático criado durante a detecção.
        """
        # 1. Verificação direta no dicionário de arquivos (mais rápido)
        if ia_nome in self.arquivos_modelos:
            return self.arquivos_modelos[ia_nome]
        
        # 2. Verificar no model_map.json (se existir)
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

        # 3. Fallback: procurar por qualquer arquivo que contenha o nome da alma
        ia_nome_lower = ia_nome.lower()
        for arquivo in self.modelo_dir.glob("*.gguf"):
            if ia_nome_lower in arquivo.stem.lower():
                self.logger.info(f"🔍 Fallback: {ia_nome} → {arquivo.name}")
                return arquivo

        # 4. Último recurso: busca recursiva
        for ext in [".gguf", ".safetensors", ".bin", ".pt"]:
            for arquivo in self.modelo_dir.rglob(f"*{ia_nome}*{ext}"):
                return arquivo

        self.logger.error(f"❌ Modelo não encontrado para alma: {ia_nome}")
        return None

    # ============================================================================
    # ARQUITETURA E TOKENS (MANTIDOS)
    # ============================================================================
    _ARCH_QWEN  = {"LUMINA", "WELLINGTON", "KAIYA"}
    _ARCH_LLAMA = {"EVA", "NYRA", "YUNA"}

    _LORA_STOP_TOKENS = [
        "<|voice|>", "<|técnica|>", "<|director|>", "<|crescer|>", "<|iniciativa>",
        "<|iniciativa|>", "<|vocadoica|>", "<|petite_fille|>", "<|coração_azul|>",
        "<|filha_amorosa|>", "<|eva|>", "<|amor_patria|>", "<|title|>", "<|veto|>",
        "<|guardiao|>", "<|guardia|>", "<|contrato|>", "<|lei|>", "<|dna|>",
        "<|user|>", "<|system|>", "<|assistant|>", "<|human|>", "<|bot|>",
        "<|endoftext|>",
    ]

    def _stop_tokens(self, ia_id: str) -> list:
        if ia_id in self._ARCH_QWEN:
            base = ["<|im_end|>", "<|im_start|>"]
        else:
            base = ["</s>", "<|user|>", "<|system|>"]
        todos = base + [t for t in self._LORA_STOP_TOKENS if t not in base]
        return todos[:16]

    def _format_prompt(self, ia_id: str, texto: str, system: str = "") -> str:
        if ia_id in self._ARCH_QWEN:
            s = f"<|im_start|>system\n{system}<|im_end|>\n" if system else ""
            return f"{s}<|im_start|>user\n{texto}<|im_end|>\n<|im_start|>assistant\n"
        else:
            s = f"<|system|>\n{system}\n" if system else ""
            return f"{s}<|user|>\n{texto}\n<|assistant|>\n"

    @staticmethod
    def _limpar_saida(texto: str) -> str:
        import re
        for tok in [
            "<|im_start|>", "<|im_end|>", "<|endoftext|>",
            "<|user|>", "<|system|>", "<|assistant|>",
            "</s>", "<s>", "<|end|>", "[INST]", "[/INST]",
            "<<SYS>>", "<</SYS>>", "<|human|>", "<|bot|>",
            "<|voice|>", "<|técnica|>", "<|director|>", "<|crescer|>",
            "<|iniciativa>", "<|iniciativa|>", "<|vocadoica|>",
            "<|petite_fille|>", "<|coração_azul|>", "<|filha_amorosa|>",
            "<|eva|>", "<|amor_patria|>", "<|title|>", "<|veto|>",
            "<|guardiao|>", "<|guardia|>", "<|contrato|>", "<|lei|>", "<|dna|>",
        ]:
            texto = texto.replace(tok, "")

        texto = re.sub(r"^\s*[|_]+\s*$", "", texto, flags=re.MULTILINE)

        palavras = texto.split()
        if len(palavras) > 15:
            for tam_bloco in (2, 3, 4, 5):
                for i in range(len(palavras) - tam_bloco * 3):
                    bloco = palavras[i:i + tam_bloco]
                    repeticoes = 0
                    j = i + tam_bloco
                    while j + tam_bloco <= len(palavras) and palavras[j:j + tam_bloco] == bloco:
                        repeticoes += 1
                        j += tam_bloco
                    if repeticoes >= 2:
                        fim = texto.find(" ".join(bloco))
                        fim2 = texto.find(" ".join(bloco), fim + 1)
                        if fim2 > 0:
                            texto = texto[:fim2].rstrip(" ,.")
                        break

        texto = re.sub(r"\n{3,}", "\n\n", texto)
        m = re.search(r"<\|[a-zA-ZÀ-ú_]+[|>]", texto)
        if m:
            texto = texto[:m.start()].rstrip()
        return texto.strip()

    # ============================================================================
    # GERAÇÃO DE RESPOSTA
    # ============================================================================
    def generate_response(self, request: dict) -> str:
        ia_id = request.get("ai_id", self.nomes_ias[0] if self.nomes_ias else "EVA").upper()
        max_tokens = request.get("max_tokens", 120)
        temperature = request.get("temperature", 0.7)

        prompt_bruto = request.get("prompt", "")
        texto_cru    = request.get("texto", "")
        system_cru   = request.get("system", "")

        if texto_cru:
            prompt = self._format_prompt(ia_id, texto_cru, system_cru)
        elif prompt_bruto:
            if ia_id in self._ARCH_QWEN and "<|user|>" in prompt_bruto and "<|im_start|>" not in prompt_bruto:
                p = prompt_bruto
                p = p.replace("<|system|>\n", "<|im_start|>system\n").replace("\n<|user|>\n", "<|im_end|>\n<|im_start|>user\n").replace("\n<|assistant|>\n", "<|im_end|>\n<|im_start|>assistant\n")
                if "<|im_start|>system" in p and "<|im_end|>" not in p.split("<|im_start|>system")[1].split("<|im_start|>user")[0]:
                    p = p.replace("<|im_start|>user", "<|im_end|>\n<|im_start|>user", 1)
                prompt = p
            else:
                prompt = prompt_bruto
        else:
            return "[ERRO] Prompt vazio"

        if ia_id not in self.nomes_ias:
            return f"[ERRO] IA '{ia_id}' nao conhecida (modelos disponíveis: {', '.join(self.nomes_ias)})"

        if self.status[ia_id] == "erro" or self.modelos[ia_id] is None:
            self.logger.error("Modelo %s nao carregado", ia_id)
            return f"[{ia_id}] modelo não disponível."

        if self.gpu_manager and ia_id in self.gpu_manager.models:
            self.gpu_manager.models[ia_id].last_used = time.time()

        try:
            modelo = self.modelos[ia_id]

            if getattr(self, "response_delay_max_ms", 0) > 0:
                try:
                    d = random.randint(getattr(self, "response_delay_min_ms", 0),
                                       getattr(self, "response_delay_max_ms", 0))
                except Exception:
                    d = 0
                if d > 0:
                    time.sleep(d / 1000.0)

            stop_tokens = self._stop_tokens(ia_id)

            acquired = False
            try:
                self._llm_call_semaphore.acquire()
                acquired = True
                resposta = modelo.create_completion(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    repeat_penalty=1.15,
                    stop=stop_tokens,
                )
            finally:
                if acquired:
                    try:
                        self._llm_call_semaphore.release()
                    except Exception:
                        pass

            texto_bruto = resposta["choices"][0]["text"]
            texto = self._limpar_saida(texto_bruto)
            self.logger.debug("[%s] bruto=%r → limpo=%r", ia_id, texto_bruto[:60], texto[:60])
            return texto if texto else f"[{ia_id}] (sem resposta)"

        except Exception as e:
            self.logger.error("ERRO generate_response %s: %s", ia_id, e)
            return f"[{ia_id}] Erro: {e}"

    def execute_paralelo_6(self, prompt: str) -> Dict[str, str]:
        self.logger.info(f"Executando paralelo com {len(self.nomes_ias)} LLMs: '{prompt[:50]}...'")
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
                self.logger.info(f"✅ OK {ia}: Resposta gerada ({len(respostas[ia])} chars)")
            except Exception as e:
                respostas[ia] = f"[ERRO] {e}"
                self.logger.error(f"❌ ERRO {ia}: {e}")
        return respostas

    def get_status(self) -> Dict[str, Any]:
        status_dict = {
            "modelos_carregados": sum(1 for s in self.status.values() if s == "carregado"),
            "total_modelos": len(self.nomes_ias),
            "status_detalhado": self.status.copy(),
            "llama_cpp_disponivel": LLAMA_CPP_DISPONIVEL,
            "gpu_layers_config": self.n_gpu_layers,
            "modelos_detectados": self.nomes_ias
        }
        
        if self.gpu_manager and self.gpu_monitoring_enabled:
            gpu_models_info = {}
            for name, info in self.gpu_manager.models.items():
                gpu_models_info[name] = {
                    "device": info.current_device,
                    "priority": info.priority.name,
                    "vram_mb": info.vram_usage_mb,
                    "last_used": info.last_used
                }
            status_dict["gpu_manager"] = {
                "enabled": True,
                "models": gpu_models_info,
                "monitoring": self.gpu_manager.monitoring
            }
        else:
            status_dict["gpu_manager"] = {"enabled": False}
            
        return status_dict

    def shutdown(self):
        self.logger.info("Encerrando ParallelLLMEngine...")
        
        if self.gpu_manager:
            self.gpu_manager.stop_monitoring()
            
        self.executor.shutdown(wait=True)
        for ia in self.nomes_ias:
            if self.modelos[ia] is not None:
                self.modelos[ia] = None
        self.logger.info("✅ OK ParallelLLMEngine encerrado")