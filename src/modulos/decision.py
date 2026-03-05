#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DecisionEngine (enduricido)

Motor de decisão híbrida que combina pontuações racionais, intuitivas e de valores.Melhorias aplicadas:
 - Validação e normalização de entradas (benefício/custo -> [0,1])
 - Injeção de RNG para determinismo/testes (seed opcional ou Random instance)
 - Validação/normalização automática de pesos (somatório -> 1.0)
 - Tie-breaker determinístico (benefício maior, custo menor)
 - Logs detalhados por opção (DEBUG)
 - Tipagem e docstrings claras
"""
from __future__ import annotations


import logging
import math
import random
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger("Cognitive.Decision")
logger.addHandler(logging.NullHandler())


class DecisionEngine:
    """
    Motor de Decisão Híbrida.Args:
        alma_nome: nome da agente/alma que toma decisões (usado em logs).
        pesos: opcional dict com chaves 'racional', 'intuitiva', 'valores'.
               Se ausente, usa valores padrão {'racional':0.4,'intuitiva':0.3,'valores':0.3}.
        rng: opcional random.Random instance para tornar decisões testáveis/determinísticas.Pode ser um int seed também; se None, usa random.Random() (não determinístico).
    """

    REQUIRED_SCORE_KEYS = ("beneficio", "custo")

    def __init__(self, alma_nome: str, pesos: Optional[Dict[str, float]] = None, rng: Optional[Any] = None):
        self.alma = alma_nome
        self.pesos = {"racional": 0.4, "intuitiva": 0.3, "valores": 0.3}
        if pesos:
            self.set_pesos(pesos)
        # rng: accept int seed, random.Random or None
        if isinstance(rng, int):
            self._rng = random.Random(rng)
        elif isinstance(rng, random.Random):
            self._rng = rng
        else:
            # default: new Random() (system-seeded)
            self._rng = random.Random()
        logger.debug("[%s] DecisionEngine iniciado com pesos=%s", self.alma, self.pesos)

    # ----------------------
    # Pesos
    # ----------------------
    def set_pesos(self, pesos: Dict[str, float]) -> None:
        """Define/normaliza pesos.Qualquer peso faltante recebe 0.0; pesos são normalizados para soma 1."""
        p = {k: float(pesos.get(k, 0.0)) for k in ("racional", "intuitiva", "valores")}
        total = sum(abs(v) for v in p.values()) or 1.0
        self.pesos = {k: (v / total) for k, v in p.items()}
        logger.debug("[%s] Pesos ajustados/normalizados: %s", self.alma, self.pesos)

    # ----------------------
    # Utilitários de normalização
    # ----------------------
    @staticmethod
    def _clamp01(v: float) -> float:
        try:
            f = float(v)
        except Exception:
            return 0.0
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return max(0.0, min(1.0, f))

    def _normalize_option(self, op: Dict) -> Tuple[float, float]:
        """
        Extrai e normaliza benefit/cost do dicionário da opção.Retorna (beneficio_normalizado, custo_normalizado).
        """
        b = op.get("beneficio", 0.5)
        c = op.get("custo", 0.5)
        return self._clamp01(b), self._clamp01(c)

    # ----------------------
    # Scoring components
    # ----------------------
    def _score_racional(self, op: Dict) -> float:
        """
        Score racional: pondera benefício e custo.Retorna valor em [0,1].
        Fórmula: 0.6 * beneficio + 0.4 * (1 - custo)
        """
        b, c = self._normalize_option(op)
        score = 0.6 * b + 0.4 * (1.0 - c)
        return self._clamp01(score)

    def _score_intuitivo(self, op: Dict) -> float:
        """
        Score intuitivo: usa distribuição Gaussiana centrada em 0.5.
        Usa RNG injetável para determinismo em testes.Resultado é truncado para [0,1].
        """
        val = self._rng.gauss(0.5, 0.2)
        return self._clamp01(val)

    def _score_valores(self, op: Dict) -> float:
        """
        Score de alinhamento com valores: se op['alinhado_proposito'] truthy => 1.0, senão 0.5.
        Pode ser estendido para checar listas de valores.
        """
        alin = op.get("alinhado_proposito")
        return 1.0 if bool(alin) else 0.5

    # ----------------------
    # Decisão principal
    # ----------------------
    def decidir(self, opcoes: List[Dict], return_scores: bool = False) -> Optional[Dict]:
        """
        Decide a melhor opção entre uma lista de dicionários.Cada opção deve ser um dict (ex.: {'acao': '...', 'beneficio':0.8, 'custo':0.2, 'alinhado_proposito': True}).

        Se return_scores=True, retorna dict com chaves:
            {'melhor': melhor_opcao_dict, 'ranked': [ (score, option), ... ]}
        Caso contrário, retorna apenas o melhor_opcao_dict ou None se opcoes vazio.
        """
        if not opcoes:
            logger.debug("[%s] decidir chamado com lista vazia", self.alma)
            return None

        scored: List[Tuple[float, Dict, Dict[str, float]]] = []  # (final_score, option, components)

        for op in opcoes:
            # validar opcao básica
            if not isinstance(op, dict):
                logger.debug("[%s] opção inválida (não dict): %s", self.alma, op)
                continue

            # compute components
            s_r = self._score_racional(op)
            s_i = self._score_intuitivo(op)
            s_v = self._score_valores(op)

            final = (s_r * self.pesos["racional"] +
                     s_i * self.pesos["intuitiva"] +
                     s_v * self.pesos["valores"])

            comps = {"racional": s_r, "intuitiva": s_i, "valores": s_v}
            scored.append((final, op, comps))
            logger.debug("[%s] opção='%s' comps=%s final=%.4f", self.alma, op.get("acao", "<sem_acao>"), comps, final)

        if not scored:
            logger.debug("[%s] nenhuma opção válida após filtragem", self.alma)
            return None

        # ordenar por score desc; tie-breaker aplica-se quando diferença < eps
        eps = 1e-6
        scored.sort(key=lambda tup: tup[0], reverse=True)

        # aplicar tie-breaker: entre opções com quase-mesmo score, escolher maior beneficio então menor custo
        top_score = scored[0][0]
        tied = [t for t in scored if abs(t[0] - top_score) <= eps]
        if len(tied) > 1:
            logger.debug("[%s] empate detectado entre %d opções; aplicando tie-breaker", self.alma, len(tied))
            def tie_key(item):
                _, op, _ = item
                b, c = self._normalize_option(op)
                return (b, -c)  # prefer higher benefit, then lower cost
            tied.sort(key=tie_key, reverse=True)
            best = tied[0]
            # find index of best in scored and place it first for consistent output
            # (not strictly necessary)
            # build ranked list with best first
            ranked = [best] + [s for s in scored if s is not best]
        else:
            ranked = scored

        melhor_score, melhor_opcao, melhor_comps = ranked[0]
        logger.info("[%s] decisão: %s (score=%.4f) comps=%s", self.alma, melhor_opcao.get("acao", "<sem_acao>"), melhor_score, melhor_comps)

        if return_scores:
            # transform ranked to simpler structure
            ranked_simple = [{"score": float(s), "opcao": o, "components": comps} for s, o, comps in ranked]
            return {"melhor": melhor_opcao, "ranked": ranked_simple}

        return melhor_opcao

    # ----------------------
    # Helpers / utilitários
    # ----------------------
    def ajustar_pesos(self, racional: Optional[float] = None, intuitiva: Optional[float] = None, valores: Optional[float] = None) -> None:
        """Ajusta pesos parcialmente e normaliza o vetor resultante."""
        p = {
            "racional": racional if racional is not None else self.pesos["racional"],
            "intuitiva": intuitiva if intuitiva is not None else self.pesos["intuitiva"],
            "valores": valores if valores is not None else self.pesos["valores"],
        }
        self.set_pesos(p)

    def get_pesos(self) -> Dict[str, float]:
        return dict(self.pesos)

