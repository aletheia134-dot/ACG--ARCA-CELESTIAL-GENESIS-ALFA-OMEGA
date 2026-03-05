# src/biblioteca/preview.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARCA CELESTIAL GENESIS - PREVIEW INTELIGENTE BIBLIOTECA TEOLÓGICA
Componente para geração de trechos destacados dos resultados de busca.
"""
from __future__ import annotations
import logging
import re
import unicodedata
from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher

logger = logging.getLogger("PreviewInteligente")


def _normalize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text))
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch)).casefold()


class PreviewInteligente:
    """
    Gera previews de trechos relevantes nos resultados da busca.
    """

    def __init__(self, tamanho_max_palavras: int = 50, contexto_antes_depois: int = 10):
        """
        Args:
            tamanho_max_palavras: máximo de palavras no preview (inteiro).
            contexto_antes_depois: palavras de contexto antes/depois do trecho encontrado.
        """
        self.tamanho_max_palavras = int(tamanho_max_palavras)
        self.contexto_antes_depois = int(contexto_antes_depois)
        logger.info(
            "👁️ Preview Inteligente inicializado (tamanho_max=%d, contexto=%d).",
            self.tamanho_max_palavras,
            self.contexto_antes_depois,
        )

    def gerar_previews(
        self,
        resultados: List[Dict[str, Any]],
        consulta: str,
        estrategia: str = "keywords",  # 'keywords' | 'sequence_match'
    ) -> List[Dict[str, str]]:
        """
        Gera previews para uma lista de resultados.
        Retorna lista de dicionários com chaves:
            - conteudo_original
            - preview
            - fonte
            - id (se disponível)
        """
        previews: List[Dict[str, str]] = []
        consulta_norm = _normalize_text(consulta)

        for res in resultados:
            conteudo = res.get("conteudo", "") or ""
            fonte = res.get("fonte", "Desconhecida")
            id_resultado = res.get("id", "")

            if not conteudo:
                previews.append(
                    {
                        "conteudo_original": "",
                        "preview": "[Sem conteúdo para gerar preview]",
                        "fonte": fonte,
                        "id": id_resultado,
                    }
                )
                continue

            try:
                preview_text = self._gerar_preview_individual(conteudo, consulta_norm, estrategia)
            except Exception:
                logger.exception(
                    "Erro ao gerar preview para resultado (fonte=%s, id=%s).", fonte, id_resultado
                )
                preview_text = "[Erro gerando preview]"

            previews.append(
                {
                    "conteudo_original": conteudo,
                    "preview": preview_text,
                    "fonte": fonte,
                    "id": id_resultado,
                }
            )

        logger.debug("Previews gerados: %d", len(previews))
        return previews

    def _gerar_preview_individual(self, conteudo: str, consulta_norm: str, estrategia: str) -> str:
        """Gera um preview para um único conteúdo dado a estratégia escolhida."""
        conteudo_norm = _normalize_text(conteudo)
        if not conteudo_norm or not consulta_norm:
            # fallback: início do documento
            return self._trecho_inicio(conteudo)

        if estrategia == "sequence_match":
            return self._preview_por_sequence_match(conteudo, conteudo_norm, consulta_norm)
        # default: keywords
        return self._preview_por_keywords(conteudo, conteudo_norm, consulta_norm)

    def _extrair_palavras_chave_simples(self, texto_norm: str) -> List[str]:
        """Extrai tokens do texto normalizado (remoção de stopwords simples)."""
        tokens = re.findall(r"\w+", texto_norm, flags=re.UNICODE)
        stopwords = {
            "o",
            "a",
            "os",
            "as",
            "um",
            "uma",
            "uns",
            "umas",
            "e",
            "ou",
            "mas",
            "de",
            "da",
            "do",
            "das",
            "dos",
            "em",
            "no",
            "na",
            "nos",
            "nas",
            "para",
            "com",
            "por",
            "ao",
            "aos",
            "se",
            "nao",
            "que",
            "como",
            "qual",
            "quais",
            "quem",
            "isso",
            "esta",
            "este",
            "esse",
            "essa",
        }
        keywords = [t for t in tokens if len(t) > 2 and t not in stopwords]
        # preservar ordem de aparição, sem duplicatas
        seen = set()
        ordered = []
        for k in keywords:
            if k not in seen:
                seen.add(k)
                ordered.append(k)
        return ordered

    def _trecho_inicio(self, conteudo: str) -> str:
        palavras = conteudo.split()
        trecho = " ".join(palavras[: self.tamanho_max_palavras])
        return trecho + ("..." if len(palavras) > self.tamanho_max_palavras else "")

    def _preview_por_keywords(self, conteudo: str, conteudo_norm: str, consulta_norm: str) -> str:
        """Gera preview centrado na primeira ocorrência de palavras-chave encontradas."""
        palavras_chave = self._extrair_palavras_chave_simples(consulta_norm)
        if not palavras_chave:
            return self._trecho_inicio(conteudo)

        # trabalhar com tokens do conteúdo para localizar índices por token
        conteudo_tokens = re.findall(r"\w+|\S", conteudo)  # mantém palavras e sinais como separadores
        conteudo_tokens_norm = [_normalize_text(t) for t in conteudo_tokens]

        # localizar índice do primeiro token que contenha alguma keyword
        found_index: Optional[int] = None
        for i, tok in enumerate(conteudo_tokens_norm):
            for kw in palavras_chave:
                if kw in tok:
                    found_index = i
                    break
            if found_index is not None:
                break

        if found_index is None:
            # fallback: início
            return self._trecho_inicio(conteudo)

        # calcular janela de tokens com contexto
        word_indices = [i for i, t in enumerate(conteudo_tokens) if re.match(r"\w+", t, flags=re.UNICODE)]
        # map found_index to nearest word position
        try:
            word_pos = next(
                (wi_index for wi_index, wi in enumerate(word_indices) if wi >= found_index),
                len(word_indices) - 1,
            )
        except StopIteration:
            word_pos = 0
        idx_inicio_word = max(0, word_pos - self.contexto_antes_depois)
        idx_fim_word = idx_inicio_word + self.tamanho_max_palavras
        # map back to token indices
        token_start = word_indices[idx_inicio_word] if word_indices else 0
        token_end = (
            word_indices[idx_fim_word - 1] + 1
            if (word_indices and idx_fim_word - 1 < len(word_indices))
            else len(conteudo_tokens)
        )

        trecho_tokens = conteudo_tokens[token_start:token_end]
        trecho = " ".join(trecho_tokens).strip()
        # garantir tamanho por palavras
        palavras_trecho = re.findall(r"\w+", trecho, flags=re.UNICODE)
        if len(palavras_trecho) > self.tamanho_max_palavras:
            palavras_trecho = palavras_trecho[: self.tamanho_max_palavras]
            trecho = " ".join(palavras_trecho)
            return trecho + "..."
        return trecho + ("..." if token_end < len(conteudo_tokens) else "")

    def _preview_por_sequence_match(self, conteudo: str, conteudo_norm: str, consulta_norm: str) -> str:
        """Gera preview baseado no maior trecho correspondente entre consulta e conteúdo."""
        matcher = SequenceMatcher(None, consulta_norm, conteudo_norm)
        match = matcher.find_longest_match(0, len(consulta_norm), 0, len(conteudo_norm))
        if match.size == 0:
            return self._trecho_inicio(conteudo)

        # match.b é posição em caracteres no conteudo_norm (approx). Mapear para índice de palavras
        prefix = conteudo_norm[: match.b]
        # número aproximado de palavras antes do match
        words_before = len(re.findall(r"\w+", prefix, flags=re.UNICODE))
        idx_inicio_word = max(0, words_before - self.contexto_antes_depois)
        idx_fim_word = idx_inicio_word + self.tamanho_max_palavras

        palavras = re.findall(r"\w+|\S+", conteudo, flags=re.UNICODE)
        # extrair apenas palavras para mapear limites
        palavras_so = [p for p in palavras if re.match(r"\w+", p, flags=re.UNICODE)]
        trecho_palavras = palavras_so[idx_inicio_word: idx_fim_word]
        if not trecho_palavras:
            return self._trecho_inicio(conteudo)
        trecho = " ".join(trecho_palavras)
        return trecho + ("..." if len(palavras_so) > idx_fim_word else "")