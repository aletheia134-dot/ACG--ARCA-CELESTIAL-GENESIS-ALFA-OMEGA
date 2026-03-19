# -*- coding: utf-8 -*-
"""
BUSCA HBRIDA (Atualizada com fallback completo).
"""
from __future__ import annotations
import re
import logging
import unicodedata
from typing import List, Dict, Any, Optional

logger = logging.getLogger("BuscaHibrida")

try:
    from src.memoria.sistema_memoria import SistemaMemoriaHibrido
    MEMORIA_DISPONIVEL = True
except:
    logging.getLogger(__name__).warning(" SistemaMemoriaHibrido no disponível")
    SistemaMemoriaHibrido = None
    MEMORIA_DISPONIVEL = False
    logger.debug("SistemaMemoriaHibrido no disponível.")

REFERENCIA_BIBLICA_REGEX = re.compile(r'\b(?:[1-3]\s+)?[A-Za-z---]+\s+\d+:\d+(?:-\d+)?\b', re.IGNORECASE)

class BuscaHibrida:
    def __init__(self, memoria: Optional[SistemaMemoriaHibrido] = None):
        self.memoria = memoria
        if not MEMORIA_DISPONIVEL or not self.memoria:
            logger.warning("Busca vetorial desativada.")
        logger.info("Busca Hbrida inicializada.")

    def buscar(self, consulta: str, colecao: str = "tudo", n_resultados: int = 5, threshold_semantico: float = 0.3) -> List[Dict[str, Any]]:
        if not consulta:
            return []

        logger.debug("Busca: consulta='%s', colecao=%s, n=%d", consulta[:80], colecao, n_resultados)
        resultados: List[Dict[str, Any]] = []

        # Busca por referncia exata
        ref_match = REFERENCIA_BIBLICA_REGEX.search(consulta)
        if ref_match:
            referencia = ref_match.group(0).strip()
            logger.info("Referncia detectada: %s", referencia)
            ref_results = self._buscar_referencia_vetorial(referencia, colecao, 1)
            resultados.extend(ref_results)

        # Busca vetorial com fallback
        if MEMORIA_DISPONIVEL and self.memoria:
            try:
                sem_results = self._buscar_vetorial(consulta, colecao, n_resultados, threshold_semantico)
                ids_existentes = {r.get("id") for r in resultados if r.get("id")}
                sem_filtered = [r for r in sem_results if not r.get("id") or r.get("id") not in ids_existentes]
                resultados.extend(sem_filtered)
            except Exception as e:
                logger.exception("Erro vetorial: %s", e)
                # Fallback simples
                fallback_results = self._fallback_busca_simples(consulta, n_resultados)
                resultados.extend(fallback_results)
        else:
            fallback_results = self._fallback_busca_simples(consulta, n_resultados)
            resultados.extend(fallback_results)

        return resultados

    def _buscar_vetorial(self, consulta: str, colecao: str, n_resultados: int, threshold: float) -> List[Dict[str, Any]]:
        if not self.memoria:
            return []
        try:
            if hasattr(self.memoria, "retrieve_similar"):
                filtro = {}
                if colecao != "tudo":
                    filtro = {"colecao": colecao}
                raw = self.memoria.retrieve_similar(query_texts=[consulta], n_results=n_resultados, where=filtro)
                return self._formatar_resultados_retrieve_similar(raw)
            if hasattr(self.memoria, "search"):
                raw = self.memoria.search(query=consulta, top_k=n_resultados, filter_collection=colecao)
                return self._formatar_resultados_search(raw)
        except Exception as e:
            logger.exception("Erro no backend vetorial: %s", e)
            return []

    def _buscar_referencia_vetorial(self, referencia: str, colecao: str, n_resultados: int) -> List[Dict[str, Any]]:
        if not self.memoria:
            return []
        try:
            filtro = {"tipo": "versiculo"}
            if colecao != "tudo":
                filtro["colecao"] = colecao
            if hasattr(self.memoria, "retrieve_similar"):
                raw = self.memoria.retrieve_similar(query_texts=[referencia], n_results=n_resultados, where=filtro)
                return self._formatar_resultados_retrieve_similar(raw)
        except Exception as e:
            logger.exception("Erro referncia vetorial: %s", e)
            return []

    def _fallback_busca_simples(self, consulta: str, n_resultados: int) -> List[Dict[str, Any]]:
        """Fallback quando memória vetorial não está disponível.
        Não usa dados mock — retorna lista vazia para não poluir resultados com dados falsos.
        O chamador deve tratar lista vazia como 'sem resultados disponíveis'.
        """
        logger.warning(
            "BuscaHibrida: memória vetorial indisponível para consulta '%s'. "
            "Retornando lista vazia — inicialize SistemaMemoriaHibrido para busca real.",
            consulta[:80]
        )
        return []

    def _formatar_resultados_retrieve_similar(self, raw: Any) -> List[Dict[str, Any]]:
        results = []
        try:
            docs = raw.get("documents", [[]])[0]
            metas = raw.get("metadatas", [[]])[0]
            dists = raw.get("distances", [[]])[0]
            for doc, meta, dist in zip(docs, metas, dists):
                sim = 1.0 - float(dist) if dist else None
                results.append({
                    "id": meta.get("id"),
                    "conteudo": doc,
                    "fonte": meta.get("fonte", "Desconhecida"),
                    "similaridade": sim,
                    "metadata": meta,
                    "tipo": meta.get("tipo", "outro"),
                    "colecao": meta.get("colecao", "tudo")
                })
        except Exception:
            logger.exception("Erro formatao retrieve_similar.")
        return results

    def _formatar_resultados_search(self, raw: Any) -> List[Dict[str, Any]]:
        results = []
        try:
            if isinstance(raw, dict) and "results" in raw:
                block = raw["results"]
                docs = block.get("documents", [])
                metas = block.get("metadatas", [])
                scores = block.get("scores", [])
                for doc, meta, score in zip(docs, metas, scores):
                    results.append({
                        "id": meta.get("id"),
                        "conteudo": doc,
                        "fonte": meta.get("fonte", "Desconhecida"),
                        "similaridade": float(score),
                        "metadata": meta,
                        "tipo": meta.get("tipo", "outro"),
                        "colecao": meta.get("colecao", "tudo")
                    })
            elif isinstance(raw, list):
                for item in raw:
                    if isinstance(item, dict):
                        results.append({
                            "id": item.get("id"),
                            "conteudo": item.get("conteudo") or item.get("document"),
                            "fonte": item.get("fonte", "Desconhecida"),
                            "similaridade": item.get("score"),
                            "metadata": item.get("metadata", {}),
                            "tipo": item.get("tipo", "outro"),
                            "colecao": item.get("colecao", "tudo")
                        })
        except Exception:
            logger.exception("Erro formatao search.")
        return results

