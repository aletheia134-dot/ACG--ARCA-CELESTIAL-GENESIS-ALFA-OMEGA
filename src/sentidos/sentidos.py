# -*- coding: utf-8 -*-
from __future__ import annotations
"""
src/sentidos/sentidos.py  IMPLEMENTAO REAL
SentidosHumanos: módulo de percepo sensorial das almas (viso, audio, tato, etc.)
"""

import logging
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

__all__ = ["SentidosHumanos", "criar_sentidos_humanos"]


class SentidosHumanos:
    """
    Simula os sentidos humanos para as IAs da ARCA.
    Fornece percepo de texto, voz, imagem e contexto ambiental.

    Interface esperada pelo CoracaoOrquestrador:
      - iniciar()
      - parar()
      - injetar_percepcao_temporal (atributo bool)
      - processar_estimulo(tipo, dado)  Dict
    """

    def __init__(
        self,
        coracao_ref: Any = None,
        config: Any = None,
        nome_alma: str = "ARCA",
    ):
        self.coracao = coracao_ref
        self.config = config
        self.nome_alma = nome_alma
        self.logger = logging.getLogger(f"Sentidos.{nome_alma}")
        self._lock = threading.RLock()
        self._ativo = False
        self.injetar_percepcao_temporal = False

        # Estado dos sentidos
        self._estimulos: list = []

        self.logger.info("  SentidosHumanos inicializados para %s", nome_alma)

    def iniciar(self) -> None:
        with self._lock:
            self._ativo = True
        self.logger.info("[OK] Sentidos ativados para %s", self.nome_alma)

    def parar(self) -> None:
        with self._lock:
            self._ativo = False
        self.logger.info(" Sentidos desativados para %s", self.nome_alma)

    def processar_estimulo(self, tipo: str, dado: Any) -> Dict[str, Any]:
        """Processa um estmulo sensorial e retorna a percepo."""
        with self._lock:
            if not self._ativo:
                return {"status": "inativo", "tipo": tipo}

            entrada = {
                "tipo": tipo,
                "dado": str(dado)[:200] if dado else "",
                "processado": True,
            }
            self._estimulos.append(entrada)
            if len(self._estimulos) > 100:
                self._estimulos = self._estimulos[-100:]

            return {"status": "ok", "tipo": tipo, "percebido": True}

    def obter_contexto_sensorial(self) -> Dict[str, Any]:
        """Retorna o contexto sensorial atual."""
        with self._lock:
            return {
                "ativo": self._ativo,
                "total_estimulos": len(self._estimulos),
                "percepcao_temporal": self.injetar_percepcao_temporal,
                "ultimos": self._estimulos[-5:] if self._estimulos else [],
            }


def criar_sentidos_humanos(
    coracao_ref: Any = None,
    config: Any = None,
    nome_alma: str = "ARCA",
) -> SentidosHumanos:
    """Factory function para criar SentidosHumanos."""
    return SentidosHumanos(coracao_ref=coracao_ref, config=config, nome_alma=nome_alma)
