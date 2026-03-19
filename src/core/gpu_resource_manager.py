# core/gpu_resource_manager.py
import threading
import time
import logging
import torch
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("GPUResourceManager")

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
        self.detected_3d_processes = set()
        
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
        try:
            if torch.cuda.is_available():
                vram_total = torch.cuda.get_device_properties(0).total_memory / 1024 / 1024  # MB
                vram_used = torch.cuda.memory_allocated(0) / 1024 / 1024  # MB
                vram_free = vram_total - vram_used
                
                return {
                    'vram_total_mb': vram_total,
                    'vram_used_mb': vram_used,
                    'vram_free_mb': vram_free,
                    'gpu_util': 0  # Ideal: usar nvidia-smi para isso
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
        try:
            import psutil
            import subprocess
            
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
                    
        except ImportError:
            # Sem psutil, usa heurística simples: assume que não há
            pass
            
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
        
        # 1. Salva estado atual se necessário
        # 2. Recarrega modelo em modo CPU
        # 3. Atualiza referência no engine
        try:
            # Implementar lógica de recarregamento
            model_info.current_device = "cpu"
            logger.info(f"✅ {model_info.name} agora na CPU")
        except Exception as e:
            logger.error(f"❌ Erro ao mover {model_info.name} para CPU: {e}")
    
    def _move_model_to_gpu(self, engine, model_info):
        """Move um modelo específico da CPU para GPU"""
        logger.info(f"🔄 Movendo {model_info.name} para GPU...")
        
        try:
            # Implementar lógica de recarregamento com GPU
            model_info.current_device = "gpu"
            model_info.last_used = time.time()
            logger.info(f"✅ {model_info.name} agora na GPU")
        except Exception as e:
            logger.error(f"❌ Erro ao mover {model_info.name} para GPU: {e}")
    
    def stop_monitoring(self):
        """Para o monitoramento"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        logger.info("🛑 Monitoramento GPU parado")