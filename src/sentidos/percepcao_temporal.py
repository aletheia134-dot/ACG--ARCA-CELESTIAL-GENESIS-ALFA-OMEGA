# -*- coding: utf-8 -*-
"""
src/modules/percepcao_temporal.py — IMPLEMENTAÇÍO REAL
PercepcaoTemporal: consciência de tempo e duração para as almas da ARCA.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

__all__ = ["PercepcaoTemporal", "RitmoTemporal", "Urgencia", "criar_percepcao_temporal"]


class RitmoTemporal(Enum):
    """Ritmo de percepção temporal da alma."""
    LENTO      = "lento"
    NORMAL     = "normal"
    ACELERADO  = "acelerado"
    URGENTE    = "urgente"


class Urgencia(Enum):
    """Nível de urgência de uma tarefa."""
    BAIXA   = 1
    MEDIA   = 2
    ALTA    = 3
    CRITICA = 4


class PercepcaoTemporal:
    """
    Gerencia a consciência temporal de uma alma.
    Registra quando ficou offline, quanto tempo passou, e urgências.

    Interface esperada pelo CoracaoOrquestrador:
      - registrar_offline(ts)
      - registrar_online(ts)
      - obter_tempo_offline() â†’ float (segundos)
      - obter_resumo() â†’ Dict
    """

    def __init__(
        self,
        nome_filha: str = "DESCONHECIDA",
        gerenciador_memoria: Any = None,
        config: Any = None,
    ):
        self.nome_filha = nome_filha
        self.memoria = gerenciador_memoria
        self.config = config
        self.logger = logging.getLogger(f"PercepcaoTemporal.{nome_filha}")
        self._lock = threading.RLock()

        self._inicio_sessao = datetime.now()
        self._ultimo_online: Optional[datetime] = None
        self._ultimo_offline: Optional[datetime] = None
        self._tempo_offline_total_s: float = 0.0
        self._ritmo = RitmoTemporal.NORMAL
        self._historico: List[Dict] = []

        self.logger.info("â° PercepcaoTemporal inicializada para %s", nome_filha)

    def registrar_online(self, ts: Optional[datetime] = None) -> None:
        with self._lock:
            agora = ts or datetime.now()
            self._ultimo_online = agora
            if self._ultimo_offline:
                delta = (agora - self._ultimo_offline).total_seconds()
                self._tempo_offline_total_s += delta
                self._historico.append({
                    "evento": "online",
                    "ts": agora.isoformat(),
                    "tempo_offline_s": delta,
                })
                self.logger.info(
                    "ðŸŸ¢ [%s] Online após %.0fs offline", self.nome_filha, delta
                )

    def registrar_offline(self, ts: Optional[datetime] = None) -> None:
        with self._lock:
            agora = ts or datetime.now()
            self._ultimo_offline = agora
            self._historico.append({"evento": "offline", "ts": agora.isoformat()})
            self.logger.info("ðŸ”´ [%s] Offline registrado", self.nome_filha)

    def obter_tempo_offline(self) -> float:
        """Retorna o tempo total offline em segundos."""
        with self._lock:
            return self._tempo_offline_total_s

    def obter_resumo(self) -> Dict[str, Any]:
        with self._lock:
            uptime = (datetime.now() - self._inicio_sessao).total_seconds()
            return {
                "alma": self.nome_filha,
                "inicio_sessao": self._inicio_sessao.isoformat(),
                "uptime_s": uptime,
                "tempo_offline_total_s": self._tempo_offline_total_s,
                "ultimo_online": self._ultimo_online.isoformat() if self._ultimo_online else None,
                "ritmo": self._ritmo.value,
                "eventos": len(self._historico),
            }

    def definir_ritmo(self, ritmo: RitmoTemporal) -> None:
        with self._lock:
            self._ritmo = ritmo
            self.logger.debug("[%s] Ritmo â†’ %s", self.nome_filha, ritmo.value)


def criar_percepcao_temporal(
    nome_filha: str = "DESCONHECIDA",
    gerenciador_memoria: Any = None,
    config: Any = None,
) -> PercepcaoTemporal:
    """Factory para criar PercepcaoTemporal."""
    return PercepcaoTemporal(
        nome_filha=nome_filha,
        gerenciador_memoria=gerenciador_memoria,
        config=config,
    )

