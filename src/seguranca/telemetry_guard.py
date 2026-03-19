# telemetry_guard.py
# -*- coding: utf-8 -*-
"""
Guard de telemetria para PostHog / ChromaDB.

- Desativa COMPLETAMENTE telemetria do ChromaDB via variáveis de ambiente
  (deve ser importado ANTES de qualquer import do chromadb).
- safe_capture() substitui posthog.capture de forma segura.
- Aplica monkey-patch no posthog para silenciar chamadas internas do ChromaDB
  com assinatura errada (capture() takes 1 positional argument but 3 were given).
"""
from __future__ import annotations

import os
import logging
from typing import Any

logger = logging.getLogger("telemetry_guard")

# ── 1. Desativar telemetria via variáveis de ambiente (ChromaDB/PostHog) ──────
# Deve ocorrer ANTES do import do chromadb para ter efeito.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY", "False")
os.environ.setdefault("POSTHOG_DISABLED", "1")


def safe_capture(*args: Any, **kwargs: Any) -> Any:
    """
    Substituto seguro para posthog.capture.
    Aceita qualquer assinatura (fix: 'capture() takes 1 positional argument but 3 were given').
    - Sem POSTHOG_API_KEY -> silencia completamente.
    - Com chave -> delega ao posthog real com captura de excecoes.
    """
    if not os.getenv("POSTHOG_API_KEY"):
        try:
            event = args[1] if len(args) > 1 else kwargs.get("event", "<desconhecido>")
        except Exception:
            event = "<desconhecido>"
        logger.debug("Telemetria desativada (POSTHOG_API_KEY ausente); evento ignorado: %s", event)
        return None

    try:
        import posthog  # type: ignore
    except ImportError:
        logger.debug("posthog nao instalado; telemetria ignorada.")
        return None

    try:
        return posthog.capture(*args, **kwargs)
    except Exception:
        logger.debug("Erro ao enviar telemetria (ignorado).", exc_info=True)
        return None


def _aplicar_monkey_patch_posthog() -> None:
    """
    Aplica monkey-patch no modulo posthog caso ja esteja importado,
    substituindo capture por safe_capture para evitar erros de assinatura
    vindos do ChromaDB internamente.
    """
    try:
        import sys
        if "posthog" in sys.modules:
            import posthog as _ph  # type: ignore
            if getattr(_ph, "capture", None) is not safe_capture:
                _ph.capture = safe_capture
                logger.debug("Monkey-patch aplicado: posthog.capture -> safe_capture")
    except Exception:
        pass  # nunca quebrar por causa de telemetria


# Aplicar patch imediatamente ao importar este modulo
_aplicar_monkey_patch_posthog()
