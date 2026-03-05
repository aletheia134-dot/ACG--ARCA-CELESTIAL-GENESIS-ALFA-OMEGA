import logging

try:
    from .sistema_memoria import SistemaMemoriaHibrido
    SISTEMA_MEMORIA_OK = True
except Exception as e:
    logging.getLogger(__name__).warning(f"⚠️ SistemaMemoriaHibrido não disponível: {e}")
    SistemaMemoriaHibrido = None
    SISTEMA_MEMORIA_OK = False

try:
    from .memory_facade import MemoryFacade
    MEMORY_FACADE_OK = True
except Exception as e:
    logging.getLogger(__name__).warning(f"⚠️ MemoryFacade não disponível: {e}")
    MemoryFacade = None
    MEMORY_FACADE_OK = False

try:
    from .gerenciador_memoria import GerenciadorDeMemoria
    GERENCIADOR_MEMORIA_OK = True
except Exception as e:
    logging.getLogger(__name__).warning(f"⚠️ GerenciadorDeMemoria não disponível: {e}")
    GerenciadorDeMemoria = None
    GERENCIADOR_MEMORIA_OK = False

__all__ = []
if SISTEMA_MEMORIA_OK:
    __all__.append("SistemaMemoriaHibrido")
if MEMORY_FACADE_OK:
    __all__.append("MemoryFacade")
if GERENCIADOR_MEMORIA_OK:
    __all__.append("GerenciadorDeMemoria")
