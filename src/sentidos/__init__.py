#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MÍ³dulo src.modules.sentidos

Sistema integrado de sentidos das AIs:
- AudiÍÂ§ÍÂ£o (SistemaAudicaoReal)
- Voz/ExpressÍÂ£o (SistemaVozReal + MotorExpressao)
- AnÍÂ¡lise emocional (SentidosHumanos)
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
    from.sistema_voz import SistemaVozReal as _SistemaVozReal
    logger.debug("âÅ“... SistemaVozReal importado")
except Exception as exc:
    logger.debug("âÅ¡Â Í¯Â¸Â SistemaVozReal nÍÂ£o disponÍÂ­vel: %s", exc)

try:
    from.sistema_audicao import SistemaAudicaoReal as _SistemaAudicaoReal
    logger.debug("âÅ“... SistemaAudicaoReal importado")
except Exception as exc:
    logger.debug("âÅ¡Â Í¯Â¸Â SistemaAudicaoReal nÍÂ£o disponÍÂ­vel: %s", exc)

try:
    from.motor_expressao import MotorExpressao as _MotorExpressao
    logger.debug("âÅ“... MotorExpressao importado")
except Exception as exc:
    logger.debug("âÅ¡Â Í¯Â¸Â MotorExpressao nÍÂ£o disponÍÂ­vel: %s", exc)

try:
    from.sentidos_humanos import SentidosHumanos as _SentidosHumanos
    logger.debug("âÅ“... SentidosHumanos importado")
except Exception as exc:
    logger.debug("âÅ¡Â Í¯Â¸Â SentidosHumanos nÍÂ£o disponÍÂ­vel: %s", exc)

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
        logger.error("SistemaVozReal nÍÂ£o disponÍÂ­vel")
        return None
    try:
        return _SistemaVozReal(config or {})
    except Exception as exc:
        logger.exception("Erro ao criar SistemaVozReal: %s", exc)
        return None


def criar_sistema_audicao(config: Optional[object] = None) -> Optional["SistemaAudicaoReal"]:
    """Factory para SistemaAudicaoReal."""
    if _SistemaAudicaoReal is None:
        logger.error("SistemaAudicaoReal nÍÂ£o disponÍÂ­vel")
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
        logger.error("MotorExpressao nÍÂ£o disponÍÂ­vel")
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
        logger.error("SentidosHumanos nÍÂ£o disponÍÂ­vel")
        return None
    try:
        return _SentidosHumanos(coracao_ref, config or {})
    except Exception as exc:
        logger.exception("Erro ao criar SentidosHumanos: %s", exc)
        return None




