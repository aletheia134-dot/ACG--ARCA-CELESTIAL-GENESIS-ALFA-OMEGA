# src/biblioteca/analisador_contexto.py
# -*- coding: utf-8 -*-
"""
ARCA CELESTIAL GENESIS - ANALISADOR CONTEXTO BIBLIOTECA TEOLÓGICA
Componente para interpretação da intenção da consulta do usuário.
Implementação reforçada e determinística (sem placebos):
 - normalização robusta de texto
 - detecção de tipo de busca via padrões e heurísticas (referência, explicação, comparação, história, doutrina)
 - extração de palavras-chave com ranking por frequência + preservação de ordem
 - detecção simples de referências bíblicas (capítulo:versículo e ranges)
 - recomendações de fonte e número de resultados
"""
from __future__ import annotations
import logging
import re
import unicodedata
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter
from datetime import datetime

logger = logging.getLogger("AnalisadorContexto")


def _normalize_text(text: Optional[str]) -> str:
    """Normaliza texto (casefold + remoção de acentos) para comparações."""
    if not text:
        return ""
    # NFKD + remoção de diacríticos
    nfkd = unicodedata.normalize("NFKD", str(text))
    without_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return without_accents.casefold().strip()


# Precompile common regexes once
# Detecta referências como "João 3:16", "1 João 3:16-18", "1Co 13:4-7" (aceita letras, pontos e números iniciais)
_RE_REFERENCIA = re.compile(
    r"\b(?:[1-3]\s*)?[A-Za-zÀ-Í¿\.]{2,}\s+\d+:\d+(?:-\d+)?\b", flags=re.IGNORECASE
)

# Heurísticas para intenção
_PADROES_TIPO_BUSCA = {
    "referencia": _RE_REFERENCIA,
    "explicacao": re.compile(r"\b(explique(?:-me)?|o que (?:é|e|significa)|significado|definiç(?:a|ao)|definir)\b", flags=re.IGNORECASE),
    "comparacao": re.compile(r"\b(compare(?:r)?|diferen(c|ç)a|versus|vs\.?)\b", flags=re.IGNORECASE),
    "historia": re.compile(r"\b(hist[oó]ria|narr(a|ã)o|acontecimento|evento|quando aconteceu)\b", flags=re.IGNORECASE),
    "doutrina": re.compile(r"\b(doutrina|cren[çc]a|cr[eê]ncia|ensinamento|o que a b[ií]blia|o que a bíblia)\b", flags=re.IGNORECASE),
}

# Fontes conhecidas (normalizadas)
_FONTES_CONHECIDAS_TERMS = {
    "biblia": ["bible", "biblia", "escritura", "escrituras", "sagrada", "novo testamento", "antigo testamento"],
    "sentinela": ["sentinela", "revista a sentinela"],
    "despertai": ["despertai", "revista a despertai"],
    "livros": ["livro", "livros", "publicacao", "publicacoes"],
}


_DEFAULT_STOPWORDS = {
    "o", "a", "os", "as", "um", "uma", "uns", "umas", "e", "ou", "mas", "de", "da", "do", "das", "dos",
    "em", "no", "na", "nos", "nas", "para", "com", "por", "ao", "aos", "se", "nao", "não", "sim", "que",
    "este", "esta", "esse", "essa", "isto", "aquilo", "aquele", "como", "qual", "quais", "quem", "me", "minha",
    "meu", "seu", "sua", "por que", "porque", "porquê"
}


def _extract_reference(text: str) -> Optional[str]:
    """
    Tenta extrair uma referência bíblica simples da string.
    Retorna a primeira ocorrência ou None.
    """
    if not text:
        return None
    m = _RE_REFERENCIA.search(text)
    if m:
        return m.group(0)
    return None


def _tokenize_and_rank(text: str, top_n: int, stopwords: Optional[set] = None) -> List[str]:
    """
    Tokeniza o texto, remove stopwords, computa frequência e retorna top_n tokens.
    Preserva ordem relativa entre tokens com mesma frequência pela primeira ocorrência.
    """
    if not text:
        return []
    stop = stopwords or _DEFAULT_STOPWORDS
    # normalize, remove non-word chars (preserve unicode letters and digits)
    norm = _normalize_text(text)
    cleaned = re.sub(r"[^\w\s]", " ", norm, flags=re.UNICODE)
    tokens = [t for t in cleaned.split() if len(t) > 2 and not t.isdigit()]
    if not tokens:
        return []

    # frequency
    freq = Counter(tokens)
    # compute first occurrence index for stable tie-breaking
    first_idx: Dict[str, int] = {}
    for idx, tok in enumerate(tokens):
        if tok not in first_idx:
            first_idx[tok] = idx

    # sort by (-freq, first_idx)
    sorted_tokens = sorted(freq.items(), key=lambda kv: (-kv[1], first_idx.get(kv[0], 9999)))
    # filter stopwords and return top_n
    result = []
    for tok, _ in sorted_tokens:
        if tok in stop:
            continue
        if tok not in result:
            result.append(tok)
        if len(result) >= top_n:
            break
    return result


class AnalisadorContexto:
    """
    Analisa a intenção e o contexto da pergunta do usuário.
    Retorna:
      {
        "tipo_busca": str,
        "palavras_chave": List[str],
        "recomendacao_fonte": str,
        "recomendacao_n_results": int,
        "texto_original": str,
        "timestamp_analise": str,
        "referencia_encontrada": Optional[str]
      }
    """

    def __init__(self, top_n_keywords: int = 5, stopwords_extra: Optional[List[str]] = None):
        self.top_n_keywords = max(1, int(top_n_keywords))
        self.fontes_conhecidas = {k: [s for s in v] for k, v in _FONTES_CONHECIDAS_TERMS.items()}
        # extend stopwords if provided
        extra = set(w.strip().casefold() for w in (stopwords_extra or []))
        self.stopwords = set(_DEFAULT_STOPWORDS) | extra
        self.padroes_tipo_busca = _PADROES_TIPO_BUSCA
        logger.info("ðŸ§  Analisador de Contexto inicializado (top_n_keywords=%d).", self.top_n_keywords)

    def analisar(self, pergunta: Optional[str]) -> Dict[str, Any]:
        """
        Analisa a pergunta e retorna dicionário com intenção e metadados.
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        if not pergunta or not pergunta.strip():
            logger.debug("AnalisadorContexto.analisar: pergunta vazia.")
            return {
                "tipo_busca": "semantica",
                "palavras_chave": [],
                "recomendacao_fonte": "tudo",
                "recomendacao_n_results": 3,
                "texto_original": pergunta or "",
                "timestamp_analise": timestamp,
                "referencia_encontrada": None
            }

        texto_original = pergunta.strip()
        texto_normalizado = _normalize_text(texto_original)

        # detectar referência bíblica
        referencia = _extract_reference(texto_original)

        # 1) Detectar tipo de busca (prioridade: referencia > padroes definidos > heuristicas)
        tipo_busca = "semantica"
        if referencia:
            tipo_busca = "referencia"
        else:
            for tipo, padrao in self.padroes_tipo_busca.items():
                try:
                    if padrao.search(texto_original):
                        tipo_busca = tipo
                        break
                except Exception:
                    logger.debug("Erro ao aplicar padrao %s", tipo, exc_info=True)

        # 2) Extrair palavras-chave e rankear
        palavras_chave = _tokenize_and_rank(texto_original, self.top_n_keywords, stopwords=self.stopwords)

        # 3) Detectar fonte preferida (match por termos sem acento)
        recomendacao_fonte = "tudo"
        for fonte, termos in self.fontes_conhecidas.items():
            for term in termos:
                if term in texto_normalizado:
                    recomendacao_fonte = fonte
                    break
            if recomendacao_fonte != "tudo":
                break

        # 4) Recomendar número de resultados
        if tipo_busca == "referencia":
            recomendacao_n_results = 1
        elif tipo_busca == "explicacao":
            recomendacao_n_results = 5
        elif tipo_busca == "comparacao":
            recomendacao_n_results = 5
        else:
            recomendacao_n_results = 3

        analise = {
            "tipo_busca": tipo_busca,
            "palavras_chave": palavras_chave,
            "recomendacao_fonte": recomendacao_fonte,
            "recomendacao_n_results": recomendacao_n_results,
            "texto_original": texto_original,
            "timestamp_analise": timestamp,
            "referencia_encontrada": referencia
        }

        logger.debug("Análise de contexto concluída: %s", analise)
        return analise

    def _extrair_palavras_chave_simples(self, texto: str) -> List[str]:
        """
        Compatibilidade com API anterior: expõe método para extrair palavras chave sem ranking avançado.
        """
        return _tokenize_and_rank(texto, self.top_n_keywords, stopwords=self.stopwords)
