# -*- coding: utf-8 -*-
"""
Módulo src.modules.sentidos

Sistema integrado de sentidos das AIs:
- Audio (SistemaAudicaoReal)
- Voz/Expresso (SistemaVozReal + MotorExpressao)
- Anlise emocional (SentidosHumanos)
"""
from __future__ import annotations


import logging
from typing import Optional, List

logger = logging.getLogger("Sentidos")
logger.addHandler(logging.NullHandler())

# ============================================================================
# IMPORTS DEFENSIVOS
# ============================================================================

_SistemaVozReal = None
_SistemaAudicaoReal = None
_MotorExpressao = None
_SentidosHumanos = None

try:
    from .sistema_voz import SistemaVozReal as _SistemaVozReal
    logger.debug(" SistemaVozReal importado")
except Exception as exc:
    logger.debug("[AVISO] SistemaVozReal no disponível: %s", exc)

try:
    from .sistema_audicao import SistemaAudicaoReal as _SistemaAudicaoReal
    logger.debug(" SistemaAudicaoReal importado")
except Exception as exc:
    logger.debug("[AVISO] SistemaAudicaoReal no disponível: %s", exc)

try:
    from .motor_expressao import MotorExpressao as _MotorExpressao
    logger.debug(" MotorExpressao importado")
except Exception as exc:
    logger.debug("[AVISO] MotorExpressao no disponível: %s", exc)

try:
    from .sentidos_humanos import SentidosHumanos as _SentidosHumanos
    logger.debug(" SentidosHumanos importado")
except Exception as exc:
    logger.debug("[AVISO] SentidosHumanos no disponível: %s", exc)

# ============================================================================
# EXPORTS
# ============================================================================

__all__: List[str] = []

if _SistemaVozReal is not None:
    SistemaVozReal = _SistemaVozReal
    __all__.append("SistemaVozReal")

if _SistemaAudicaoReal is not None:
    SistemaAudicaoReal = _SistemaAudicaoReal
    __all__.append("SistemaAudicaoReal")

if _MotorExpressao is not None:
    MotorExpressao = _MotorExpressao
    __all__.append("MotorExpressao")

if _SentidosHumanos is not None:
    SentidosHumanos = _SentidosHumanos
    __all__.append("SentidosHumanos")


def criar_sistema_voz(config: Optional[object] = None) -> Optional["SistemaVozReal"]:
    """Factory para SistemaVozReal."""
    if _SistemaVozReal is None:
        logger.error("SistemaVozReal no disponível")
        return None
    try:
        return _SistemaVozReal(config or {})
    except Exception as exc:
        logger.exception("Erro ao criar SistemaVozReal: %s", exc)
        return None


def criar_sistema_audicao(config: Optional[object] = None) -> Optional["SistemaAudicaoReal"]:
    """Factory para SistemaAudicaoReal."""
    if _SistemaAudicaoReal is None:
        logger.error("SistemaAudicaoReal no disponível")
        return None
    try:
        return _SistemaAudicaoReal(config or {})
    except Exception as exc:
        logger.exception("Erro ao criar SistemaAudicaoReal: %s", exc)
        return None


def criar_motor_expressao(
    nome_alma: str,
    response_queue_ref: Optional[object] = None,
    coracao_ref: Optional[object] = None,
    validador_ref: Optional[object] = None
) -> Optional["MotorExpressao"]:
    """Factory para MotorExpressao."""
    if _MotorExpressao is None:
        logger.error("MotorExpressao no disponível")
        return None
    try:
        return _MotorExpressao(
            nome_alma=nome_alma,
            response_queue_ref=response_queue_ref,
            coracao_ref=coracao_ref,
            validador_ref=validador_ref
        )
    except Exception as exc:
        logger.exception("Erro ao criar MotorExpressao para %s: %s", nome_alma, exc)
        return None


def criar_sentidos_humanos(
    coracao_ref: Optional[object] = None,
    config: Optional[object] = None
) -> Optional["SentidosHumanos"]:
    """Factory para SentidosHumanos."""
    if _SentidosHumanos is None:
        logger.error("SentidosHumanos no disponível")
        return None
    try:
        return _SentidosHumanos(coracao_ref, config or {})
    except Exception as exc:
        logger.exception("Erro ao criar SentidosHumanos: %s", exc)
        return None
