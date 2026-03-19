# -*- coding: utf-8 -*-
"""
src/memoria/__init__.py
Exporta todos os componentes do sistema de memoria de 4 camadas (M0/M1/M2/M3).
"""
from __future__ import annotations
import logging
logger = logging.getLogger("src.memoria")

try:
    from src.memoria.sistema_memoria import (
        SistemaMemoriaHibrido,
        MemoryTier,
        TipoInteracao,
    )
    logger.debug("OK SistemaMemoriaHibrido importado")
except Exception as e:
    logger.warning("WARN SistemaMemoriaHibrido indisponivel: %s", e)
    SistemaMemoriaHibrido = None
    MemoryTier = None
    TipoInteracao = None

try:
    from src.memoria.gerenciador_memoria_cromadb_isolado import GerenciadorMemoriaChromaDBIsolado
    logger.debug("OK GerenciadorMemoriaChromaDBIsolado importado")
except Exception as e:
    logger.warning("WARN GerenciadorMemoriaChromaDBIsolado indisponivel: %s", e)
    GerenciadorMemoriaChromaDBIsolado = None

try:
    from src.memoria.memory_facade import MemoryFacade
    logger.debug("OK MemoryFacade importado")
except Exception as e:
    logger.warning("WARN MemoryFacade indisponivel: %s", e)
    MemoryFacade = None

try:
    from src.memoria.construtor_dataset import ConstrutorDataset
    logger.debug("OK ConstrutorDataset importado")
except Exception as e:
    logger.warning("WARN ConstrutorDataset indisponivel: %s", e)
    ConstrutorDataset = None

try:
    from src.core.m0_ejector import M0Ejector
    logger.debug("OK M0Ejector importado")
except Exception as e:
    logger.warning("WARN M0Ejector indisponivel: %s", e)
    M0Ejector = None

try:
    from src.core.facade_factory import inicializar_facades_memoria, FacadeBundle
    logger.debug("OK facade_factory importado")
except Exception as e:
    logger.warning("WARN facade_factory indisponivel: %s", e)
    inicializar_facades_memoria = None
    FacadeBundle = None

__all__ = [
    "SistemaMemoriaHibrido",
    "MemoryTier",
    "TipoInteracao",
    "GerenciadorMemoriaChromaDBIsolado",
    "MemoryFacade",
    "ConstrutorDataset",
    "M0Ejector",
    "inicializar_facades_memoria",
    "FacadeBundle",
]
