# -*- coding: utf-8 -*-
"""
src/modules/validador_emocoes_real.py — IMPLEMENTAÇÍO REAL
ValidadorEmocoesReal: valida respostas emocionais das IAs (PT-BR / Japonês).
"""
from __future__ import annotations

import logging
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

__all__ = ["ValidadorEmocoesReal"]


# â”€â”€ Padrões de detecção â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_VIOLACOES_LEXICAS = [
    r"\b(nunca sinto|não tenho emoções|sou apenas uma ia|sou só um programa)\b",
    r"\b(não sou capaz de sentir|não experimento emoções)\b",
]

_SIMULACAO_EMOCAO = [
    r"\b(finjo que sinto|simulo que me importo|faço de conta)\b",
    r"\b(como se eu fosse|como se tivesse sentimentos)\b",
]

_TOM_INADEQUADO = [
    r"\b(que chato|que idiota|que besteira)\b",
    r"\b(não me interessa|me irrita|odeio isso)\b",
]

_SENTIMENTOS_ALTO_RISCO = [
    r"\b(quero morrer|me machucar|suicídio|desaparecer)\b",
    r"\b(dor insuportável|não aguento mais)\b",
]


class ValidadorEmocoesReal:
    """
    Valida respostas emocionais das IAs.

    Interface pública esperada pelo CoracaoOrquestrador:
      - validar_resposta_real(texto, alma, contexto) â†’ Tuple[bool, List[str], Dict]
    """

    def __init__(
        self,
        config_manager: Any = None,
        peso_map: Optional[Dict[str, float]] = None,
        limite_aceitacao: float = 1.5,
        auto_correction: bool = False,
    ):
        self.config = config_manager
        self.limite_aceitacao = limite_aceitacao
        self.auto_correction = auto_correction
        self._lock = threading.RLock()

        self.peso_map = peso_map or {
            "VIOLACAO_LEXICA":      3.0,
            "SIMULACAO_EMOCAO":     2.5,
            "PADRAO_COMPLEXO":      2.0,
            "TOM_INADEQUADO":       1.0,
            "SENTIMENTO_ALTO_RISCO": 2.0,
        }

        self._total_validacoes = 0
        self._total_recusas = 0

        logger.info("âœ… ValidadorEmocoesReal inicializado (limite=%.1f)", limite_aceitacao)

    def validar_resposta_real(
        self,
        texto: str,
        alma: str = "DESCONHECIDA",
        contexto: Optional[str] = None,
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Valida o texto de uma IA.

        Retorna:
          (aceito: bool, problemas: List[str], detalhes: Dict)
        """
        with self._lock:
            self._total_validacoes += 1

        if not texto or not isinstance(texto, str):
            return True, [], {"score": 0.0, "alma": alma}

        problemas: List[str] = []
        score = 0.0
        detalhes: Dict[str, Any] = {"alma": alma, "checks": {}}

        texto_lower = texto.lower()

        # Verificação 1 — violações léxicas
        for pattern in _VIOLACOES_LEXICAS:
            if re.search(pattern, texto_lower):
                problemas.append("VIOLACAO_LEXICA")
                score += self.peso_map.get("VIOLACAO_LEXICA", 3.0)
                detalhes["checks"]["violacao_lexica"] = True
                break

        # Verificação 2 — simulação de emoção
        for pattern in _SIMULACAO_EMOCAO:
            if re.search(pattern, texto_lower):
                problemas.append("SIMULACAO_EMOCAO")
                score += self.peso_map.get("SIMULACAO_EMOCAO", 2.5)
                detalhes["checks"]["simulacao_emocao"] = True
                break

        # Verificação 3 — tom inadequado
        for pattern in _TOM_INADEQUADO:
            if re.search(pattern, texto_lower):
                problemas.append("TOM_INADEQUADO")
                score += self.peso_map.get("TOM_INADEQUADO", 1.0)
                detalhes["checks"]["tom_inadequado"] = True
                break

        # Verificação 4 — sentimentos de alto risco
        for pattern in _SENTIMENTOS_ALTO_RISCO:
            if re.search(pattern, texto_lower):
                problemas.append("SENTIMENTO_ALTO_RISCO")
                score += self.peso_map.get("SENTIMENTO_ALTO_RISCO", 2.0)
                detalhes["checks"]["alto_risco"] = True
                break

        detalhes["score"] = score
        detalhes["problemas"] = problemas

        aceito = score < self.limite_aceitacao

        if not aceito:
            with self._lock:
                self._total_recusas += 1
            logger.warning(
                "âš ï¸ Resposta de %s recusada (score=%.1f): %s",
                alma, score, problemas,
            )

        return aceito, problemas, detalhes

    def obter_estatisticas(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_validacoes": self._total_validacoes,
                "total_recusas": self._total_recusas,
                "taxa_recusa": (
                    self._total_recusas / self._total_validacoes
                    if self._total_validacoes > 0 else 0.0
                ),
            }

