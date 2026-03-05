# -*- coding: utf-8 -*-
"""
src/sentidos/analisador_intencoes.py — IMPLEMENTAÇÍO REAL
AnalisadorIntencao: analisa a intenção por trás de mensagens do usuário.
"""
from __future__ import annotations
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
__all__ = ["AnalisadorIntencao"]

INTENCOES = {
    "pergunta":     [r"\?$", r"^(o que|como|quando|onde|quem|por que|qual)", r"^(what|how|when|where|who|why|which)"],
    "saudacao":     [r"^(oi|olá|ola|hey|hi|hello|bom dia|boa tarde|boa noite)"],
    "despedida":    [r"^(tchau|adeus|até|bye|ciao|até logo|até mais)"],
    "agradecimento":[r"(obrigad|valeu|thank|gracias)"],
    "pedido":       [r"^(por favor|pfv|please|pode|poderia|preciso que|quero que)"],
    "critica":      [r"(errou|errado|incorreto|ruim|péssim|horrível|não gostei)"],
    "elogio":       [r"(parabéns|ótimo|excelente|perfeito|muito bom|adorei|amei)"],
    "comando":      [r"^(faça|crie|escreva|gere|liste|mostre|analise|execute)"],
    "conversacao":  [],  # fallback
}


class AnalisadorIntencao:
    """Analisa a intenção de uma mensagem."""

    def __init__(self, config_instance: Any = None):
        self.config = config_instance
        self._cache: Dict[str, Dict] = {}
        logger.info("âœ… AnalisadorIntencao inicializado")

    def analisar(self, texto: str, alma: str = "ARCA") -> Dict[str, Any]:
        """Analisa o texto e retorna a intenção detectada."""
        if not texto:
            return {"intencao": "vazio", "confianca": 0.0, "alma": alma}

        texto_l = texto.lower().strip()

        for intencao, patterns in INTENCOES.items():
            for p in patterns:
                if re.search(p, texto_l):
                    return {
                        "intencao": intencao,
                        "confianca": 0.85,
                        "alma": alma,
                        "texto": texto[:100],
                    }

        # Heurística de comprimento
        palavras = len(texto_l.split())
        if palavras <= 3:
            intencao = "conversacao"
        elif palavras > 30:
            intencao = "narrativa"
        else:
            intencao = "informacao"

        return {"intencao": intencao, "confianca": 0.5, "alma": alma, "texto": texto[:100]}

    def analisar_multiplos(self, textos: List[str]) -> List[Dict[str, Any]]:
        return [self.analisar(t) for t in textos]

