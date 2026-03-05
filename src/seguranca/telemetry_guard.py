# telemetry_guard.py - Atualizado
# -*- coding: utf-8 -*-
"""
Compat / guard para telemetria PostHog usado localmente.

safe_capture(...) só envia eventos se POSTHOG_API_KEY estiver definida.
Mantém comportamento previsível em ambiente de desenvolvimento.
"""
from __future__ import annotations

import os
import logging
from typing import Any

logger = logging.getLogger("telemetry_guard")


def safe_capture(*args: Any, **kwargs: Any) -> Any:
    """
    Substituto seguro para posthog.capture.
    - Se POSTHOG_API_KEY não estiver definida, não tenta inicializar o cliente e registra info.
    - Se definida, importa posthog e delega; captura exceções e as registra.
    Retorna o que posthog.capture retornar ou None em caso de telemetria desativada/erro.
    """
    # Evita import desnecessário de módulos externos quando chave não está definida
    if not os.getenv("POSTHOG_API_KEY"):
        try:
            event = args[1] if len(args) > 1 else kwargs.get("event")
        except:
            event = None
            logger.warning("⚠️ event não disponível")
        
        logger.info(
            "Telemetria desativada localmente: POSTHOG_API_KEY ausente; evento pulado: %s",
            event,
        )
        return None

    # Se chegamos aqui, tentamos usar posthog se disponível
    try:
        import posthog  # type: ignore
    except Exception:
        logger.warning("posthog não disponível; não será enviado evento de telemetria.")
        return None

    try:
        return posthog.capture(*args, **kwargs)
    except Exception:
        logger.exception("Erro ao enviar telemetria")
        return None
