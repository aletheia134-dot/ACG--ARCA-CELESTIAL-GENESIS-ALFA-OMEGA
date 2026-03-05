#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerenciador de GPU (robusto e defensivo).
Detecta disponibilidade de CUDA/Torch, expõe informações de VRAM e utilitários para limpeza/otimização.
"""
from __future__ import annotations
import logging
import gc
import time
from typing import Dict, Optional

logger = logging.getLogger("GPUManager")


class GPUManager:
    """Gerenciador de GPU com fallback seguro para CPU."""

    def __init__(self):
        # estados padrão
        self.torch = None
        self.torch_available = False
        self.gpu_available = False
        self.gpu_info: Dict = {
            "available": False,
            "name": "N/A",
            "memory_total_gb": 0.0,
            "memory_allocated_gb": 0.0,
            "memory_reserved_gb": 0.0,
            "memory_free_gb": 0.0,
            "cuda_version": None,
            "device_count": 0,
            "compute_capability": None,
        }
        self.device_index: Optional[int] = None
        self.device = None

        try:
            import torch  # imported lazily to allow module import without CUDA/torch
            self.torch = torch
            self.torch_available = True
        except Exception as e:
            logger.info("Torch não disponível: %s", e)
            self.torch_available = False

        if self.torch_available:
            try:
                self.gpu_available = bool(self.torch.cuda.is_available())
                self.gpu_info = self._get_gpu_info()
                if self.gpu_available and (self.gpu_info.get("device_count", 0) > 0):
                    self.device_index = 0
                    self.device = self.torch.device(f"cuda:{self.device_index}")
                    try:
                        # set device defensively
                        self.torch.cuda.set_device(self.device_index)
                    except Exception:
                        logger.debug("Não foi possível setar device explicitamente (não crítico).", exc_info=True)
                    self._warmup_gpu()
                else:
                    self.device = self.torch.device("cpu")
            except Exception as e:
                logger.warning("Erro ao inicializar GPUManager (fallback para CPU): %s", e, exc_info=True)
                self.gpu_available = False
                self.device = self.torch.device("cpu")
        else:
            # torch não disponível -> CPU-only
            try:
                # emulate a device attribute for callers
                import torch as _torch  # may still fail; ignore
                self.device = getattr(_torch, "device", "cpu")
            except Exception:
                self.device = "cpu"

    def _get_gpu_info(self) -> Dict:
        """Obtém informações da GPU de forma segura (retorna dicionário)."""
        info = {
            "available": False,
            "name": "N/A",
            "memory_total_gb": 0.0,
            "memory_allocated_gb": 0.0,
            "memory_reserved_gb": 0.0,
            "memory_free_gb": 0.0,
            "cuda_version": None,
            "device_count": 0,
            "compute_capability": None,
        }

        if not self.torch_available:
            return info

        try:
            if self.torch.cuda.is_available():
                info["available"] = True
                device_count = self.torch.cuda.device_count()
                info["device_count"] = int(device_count)
                if device_count > 0:
                    device = 0
                    props = None
                    try:
                        props = self.torch.cuda.get_device_properties(device)
                        info["name"] = getattr(props, "name", "CUDA Device")
                        total_mem = getattr(props, "total_memory", None)
                        if total_mem is not None:
                            info["memory_total_gb"] = float(total_mem) / 1024 ** 3
                        # compute capability if available
                        major = getattr(props, "major", None)
                        minor = getattr(props, "minor", None)
                        if major is not None and minor is not None:
                            info["compute_capability"] = f"{major}.{minor}"
                    except Exception:
                        logger.debug("Falha ao obter propriedades do device (não crítico).", exc_info=True)

                    # memory API (defensiva — alguns atributos podem não existir dependendo da versão)
                    try:
                        allocated = float(self.torch.cuda.memory_allocated(device)) / 1024 ** 3
                    except Exception:
                        allocated = 0.0
                    try:
                        reserved = float(getattr(self.torch.cuda, "memory_reserved", lambda idx=0: 0)(device)) / 1024 ** 3
                    except Exception:
                        # older torch versions may not have memory_reserved
                        try:
                            reserved = float(self.torch.cuda.max_memory_reserved(device)) / 1024 ** 3
                        except Exception:
                            reserved = 0.0

                    info["memory_allocated_gb"] = allocated
                    info["memory_reserved_gb"] = reserved
                    # compute free as best-effort
                    total = info.get("memory_total_gb", 0.0)
                    if total and total > 0:
                        info["memory_free_gb"] = max(0.0, total - allocated)
                    else:
                        info["memory_free_gb"] = 0.0

                    # cuda version
                    try:
                        info["cuda_version"] = getattr(self.torch.version, "cuda", None)
                    except Exception:
                        info["cuda_version"] = None
        except Exception as e:
            logger.warning("Erro ao coletar info da GPU: %s", e, exc_info=True)

        return info

    def _warmup_gpu(self):
        """Aquece a GPU para evitar lentidão inicial (opera em try/except)."""
        if not (self.torch_available and self.gpu_available):
            return
        try:
            # small warmup matmul
            warmup_tensor = self.torch.randn((64, 64), device=self.device)
            _ = warmup_tensor @ warmup_tensor.T
            # synchronize if available
            try:
                self.torch.cuda.synchronize()
            except Exception:
                pass
        except Exception:
            logger.debug("Warmup GPU falhou (não crítico).", exc_info=True)

    def get_status(self) -> str:
        """Retorna status da GPU em formato legível."""
        try:
            if not (self.torch_available and self.gpu_info.get("available", False)):
                return "âš ï¸ GPU não disponível (CPU)"
            info = self._get_gpu_info() or self.gpu_info
            name = info.get("name", "N/A")
            total = info.get("memory_total_gb", 0.0)
            allocated = info.get("memory_allocated_gb", 0.0)
            free = info.get("memory_free_gb", 0.0)
            status = f"ðŸ–¥ï¸ GPU: {name}\nðŸ’¾ VRAM: {total:.1f} GB total\n"
            if total > 0:
                status += f"    ðŸ“ˆ {allocated:.1f} GB alocado\n"
                status += f"    ðŸ“‰ {free:.1f} GB livre"
            return status
        except Exception as e:
            logger.error("Erro em get_status: %s", e, exc_info=True)
            return f"âš ï¸ Erro no status: {e}"

    def get_short_status(self) -> str:
        """Status resumido para barra de status."""
        try:
            if not (self.torch_available and self.gpu_info.get("available", False)):
                return "GPU: âŒ"
            name = (self.gpu_info.get("name") or "GPU")[:30]
            free_gb = self.gpu_info.get("memory_free_gb", 0.0)
            return f"GPU: {name} ({free_gb:.1f}GB livre)"
        except Exception:
            return "GPU: Erro"

    def get_vram_info(self) -> Optional[Dict[str, float]]:
        """Informações detalhadas da VRAM (ou None se indisponível)."""
        if not (self.torch_available and self.gpu_info.get("available", False)):
            return None
        try:
            # refresh info
            info = self._get_gpu_info()
            total = info.get("memory_total_gb", 0.0)
            allocated = info.get("memory_allocated_gb", 0.0)
            reserved = info.get("memory_reserved_gb", 0.0)
            free = info.get("memory_free_gb", 0.0)
            usage_percent = (allocated / total) * 100.0 if total > 0 else 0.0
            return {
                "total": total,
                "allocated": allocated,
                "reserved": reserved,
                "free": free,
                "usage_percent": usage_percent
            }
        except Exception:
            logger.debug("Falha ao obter VRAM info (silenciado).", exc_info=True)
            return None

    def clear_cache(self) -> bool:
        """Limpa cache da GPU (se disponível)."""
        if not (self.torch_available and self.gpu_info.get("available", False)):
            return False
        try:
            self.torch.cuda.empty_cache()
            gc.collect()
            return True
        except Exception:
            logger.debug("Falha ao limpar cache GPU (silenciado).", exc_info=True)
            return False

    def has_enough_memory(self, required_gb: float) -> bool:
        """Verifica de forma conservadora se há memória livre suficiente."""
        if not (self.torch_available and self.gpu_info.get("available", False)):
            return False
        try:
            vram = self.get_vram_info()
            if not vram:
                return False
            return float(vram.get("free", 0.0)) >= float(required_gb)
        except Exception:
            return False

    def get_memory_usage_percent(self) -> float:
        """Obtém porcentagem de uso da memória (0..100)."""
        try:
            vram = self.get_vram_info()
            if vram and vram.get("total", 0) > 0:
                return float(vram.get("usage_percent", 0.0))
        except Exception:
            pass
        return 0.0

    def optimize_for_llm(self):
        """Tenta aplicar otimizações úteis para cargas LLM (defensivo)."""
        if not (self.torch_available and self.gpu_info.get("available", False)):
            logger.debug("Optimize skipped: GPU não disponível")
            return
        try:
            # permissões TF32/CuDNN podem ou não existir; set em try/except
            try:
                self.torch.backends.cudnn.benchmark = True
            except Exception:
                pass
            try:
                # some torch builds expose this; guard defensively
                setattr(self.torch.backends, "cuda", getattr(self.torch.backends, "cuda", None))
                if hasattr(self.torch.backends, "cuda") and hasattr(self.torch.backends.cuda, "allow_tf32"):
                    self.torch.backends.cuda.allow_tf32 = True
            except Exception:
                pass
            try:
                if hasattr(self.torch.backends, "cudnn") and hasattr(self.torch.backends.cudnn, "allow_tf32"):
                    self.torch.backends.cudnn.allow_tf32 = True
            except Exception:
                pass

            # clear cache
            self.clear_cache()

            vram = self.get_vram_info()
            if vram:
                logger.info("ðŸ”§ GPU otimizada: %.1fGB livre", vram.get("free", 0.0))
        except Exception as e:
            logger.warning("Erro na otimização da GPU: %s", e, exc_info=True)

    def print_detailed_info(self):
        """Imprime informações detalhadas no console (uso para debug)."""
        print("\n" + "=" * 50)
        print("INFORMAÇÕES DETALHADAS DA GPU")
        print("=" * 50)
        if not (self.torch_available and self.gpu_info.get("available", False)):
            print("âŒ GPU não disponível")
            return
        info = self._get_gpu_info()
        print(f"Dispositivo: {info.get('name', 'N/A')}")
        print(f"CUDA Version: {info.get('cuda_version', 'N/A')}")
        print(f"Compute Capability: {info.get('compute_capability', 'N/A')}")
        print(f"Dispositivos CUDA: {info.get('device_count', 0)}")
        print("\nMemória:")
        print(f"  Total: {info.get('memory_total_gb', 0):.2f} GB")
        print(f"  Alocada: {info.get('memory_allocated_gb', 0):.2f} GB")
        print(f"  Reservada: {info.get('memory_reserved_gb', 0):.2f} GB")
        print(f"  Livre: {info.get('memory_free_gb', 0):.2f} GB")
        v = self.get_vram_info()
        if v:
            print(f"  Uso: {v.get('usage_percent', 0.0):.1f}%")
        print("=" * 50)


# Teste rápido quando executado diretamente
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gm = GPUManager()
    print(gm.get_status())
    gm.print_detailed_info()

