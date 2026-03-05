# src/biblioteca/reranking.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARCA CELESTIAL GENESIS - RERANKING INTELIGENTE BIBLIOTECA TEOLÓGICA
Componente para classificação refinada de resultados de busca.
Implementação realista e defensiva: normalização de texto, cálculo de score
multi-critério, e retornos estáveis sem placebos.
"""
from __future__ import annotations
import logging
import re
import unicodedata
from typing import Dict, List, Any, Optional

logger = logging.getLogger("RerankingInteligente")


def _normalize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text))
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch)).casefold().strip()


class RerankingInteligente:
    """
    Realiza reranking de resultados de busca com base em múltiplos critérios.
    """

    def __init__(self, pesos_padrao: Optional[Dict[str, float]] = None):
        """
        Inicializa o reranker.
        pesos_padrao: dicionário com pesos por critério. Exemplo:
            {
                "similaridade": 0.6,
                "keywords_na_query_no_doc": 0.25,
                "keywords_no_doc_na_query": 0.05,
                "fonte": 0.1
            }
        """
        self.pesos_padrao = pesos_padrao or {
            "similaridade": 0.6,
            "keywords_na_query_no_doc": 0.25,
            "keywords_no_doc_na_query": 0.05,
            "fonte": 0.1,
        }
        logger.info("⚖️ Reranking Inteligente inicializado. Pesos: %s", self.pesos_padrao)

    def rerank(
        self,
        resultados_brutos: List[Dict[str, Any]],
        consulta: str,
        pesos: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Faz reranking dos resultados_brutos com base na consulta.
        Retorna nova lista ordenada (cópias dos itens originais).
        """
        if not resultados_brutos:
            return []

        pesos_usados = dict(self.pesos_padrao)
        if pesos:
            pesos_usados.update(pesos)

        consulta_norm = _normalize_text(consulta or "")
        palavras_chave_consulta = self._extrair_palavras_chave(consulta_norm)

        resultados_com_pontos = []
        for res in resultados_brutos:
            try:
                pontos = self._calcular_pontos_individuais(res, consulta_norm, palavras_chave_consulta, pesos_usados)
            except Exception:
                logger.exception("Erro ao calcular pontos para resultado: %s", res.get("id", "<no-id>"))
                pontos = 0.0
            copia = dict(res)
            copia["_pontos_rerank"] = float(pontos)
            resultados_com_pontos.append(copia)

        resultados_ordenados = sorted(resultados_com_pontos, key=lambda x: x.get("_pontos_rerank", 0.0), reverse=True)

        for item in resultados_ordenados:
            item.pop("_pontos_rerank", None)

        return resultados_ordenados

    def _calcular_pontos_individuais(
        self,
        resultado: Dict[str, Any],
        consulta_norm: str,
        palavras_chave_consulta: List[str],
        pesos: Dict[str, float],
    ) -> float:
        """
        Calcula pontuação agregada para um único resultado.
        Critérios:
         - similaridade (0..1) — normaliza heurísticamente se necessário
         - cobertura de keywords da consulta no documento
         - cobertura de keywords do documento na consulta
         - prioridade por fonte (heurística)
        Retorna score normalizado (aprox. 0..1).
        """
        pontos_totais = 0.0

        # Similaridade
        similaridade_raw = resultado.get("similaridade", 0.0)
        similaridade = 0.0
        try:
            if similaridade_raw is None:
                similaridade = 0.0
            else:
                similaridade = float(similaridade_raw)
                # heurística: se escala 0..100, converter para 0..1
                if similaridade > 1.0:
                    similaridade = max(0.0, min(1.0, similaridade / 100.0))
                else:
                    similaridade = max(0.0, min(1.0, similaridade))
        except Exception:
            similaridade = 0.0
        pontos_totais += pesos.get("similaridade", 0.0) * similaridade

        # Preparar textos normalizados
        conteudo_doc = _normalize_text(resultado.get("conteudo", "") or "")
        consulta_text = consulta_norm or ""

        # Critério: palavras da consulta presentes no documento (cobertura)
        cobertura_query_no_doc = 0.0
        if palavras_chave_consulta and conteudo_doc:
            encontrados = 0
            for palavra in palavras_chave_consulta:
                if palavra and palavra in conteudo_doc:
                    encontrados += 1
            cobertura_query_no_doc = encontrados / len(palavras_chave_consulta)
            pontos_totais += pesos.get("keywords_na_query_no_doc", 0.0) * cobertura_query_no_doc

        # Critério: palavras do documento que aparecem na consulta
        palavras_doc = self._extrair_palavras_chave(conteudo_doc)
        cobertura_doc_na_query = 0.0
        if palavras_doc:
            consulta_set = set(palavras_chave_consulta)
            encontrados_doc_na_query = sum(1 for p in palavras_doc if p in consulta_set)
            cobertura_doc_na_query = encontrados_doc_na_query / len(palavras_doc)
            pontos_totais += pesos.get("keywords_no_doc_na_query", 0.0) * cobertura_doc_na_query

        # Critério: fonte preferencial (heurística simples, retornando fator entre 0.0 e 1.0)
        fonte_doc = _normalize_text(str(resultado.get("fonte", "") or ""))
        fator_fonte = 0.5  # default neutral
        if fonte_doc:
            if any(k in fonte_doc for k in ("biblia", "biblical", "genesis", "mateus", "joao", "romanos", "salmos")):
                fator_fonte = 1.0
            elif any(k in fonte_doc for k in ("sentinela", "despertai", "watchtower", "jw")):
                fator_fonte = 0.7
            else:
                fator_fonte = 0.5
        pontos_totais += pesos.get("fonte", 0.0) * fator_fonte

        # Normalizar pelo somatório absoluto de pesos para aproximar 0..1
        soma_pesos = sum(abs(v) for v in pesos.values()) if pesos else 1.0
        if soma_pesos <= 0:
            return float(max(0.0, pontos_totais))
        pontos_norm = pontos_totais / soma_pesos
        # garantir limites
        pontos_norm = max(0.0, pontos_norm)
        return float(pontos_norm)

    def _extrair_palavras_chave(self, texto: str) -> List[str]:
        """
        Extrai palavras-chave simples removendo stopwords e pontuação.
        Retorna tokens em lowercase sem duplicatas, preservando ordem.
        """
        if not texto:
            return []
        texto_limpo = re.sub(r"[^\w\s]", " ", texto.lower())
        tokens = [t for t in texto_limpo.split() if len(t) > 2]
        stopwords_basicas = {
            "o", "a", "os", "as", "um", "uma", "uns", "umas", "e", "ou", "mas", "de", "da", "do", "das", "dos",
            "em", "no", "na", "nos", "nas", "para", "com", "por", "ao", "aos", "se", "nao", "que", "como", "qual", "quem"
        }
        seen = set()
        out = []
        for t in tokens:
            if t in stopwords_basicas:
                continue
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out