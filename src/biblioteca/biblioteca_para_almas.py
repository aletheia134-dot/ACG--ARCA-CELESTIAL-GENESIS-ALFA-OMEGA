# -*- coding: utf-8 -*-
"""
BIBLIOTECA PARA ALMAS (Atualizada com cache compartilhado e tolerância).
"""
from __future__ import annotations
import asyncio
import logging
import hashlib
from typing import Dict, Any, Optional

logger = logging.getLogger("BibliotecaParaAlmas")

class BibliotecaParaAlmas:
    def __init__(
        self,
        biblioteca_principal: Optional[Any],
        nome_alma: str,
        enable_cache: bool = True,
        cache_externo: Optional[Any] = None  # Novo: cache compartilhado
    ):
        self.biblioteca_principal = biblioteca_principal
        self.nome_alma = nome_alma
        self.enable_cache = enable_cache
        self._cache: Dict[str, Any] = {}  # Cache interno
        self.cache_externo = cache_externo  # Cache compartilhado opcional
        logger.info("Interface criada para alma: %s", nome_alma)

    def _cache_key(self, pergunta: str, fonte: str, n_resultados: int) -> str:
        return hashlib.md5(f"{pergunta}||{fonte}||{n_resultados}".encode('utf-8')).hexdigest()

    def consultar(
        self,
        pergunta: str,
        fonte_preferida: Optional[str] = "tudo",
        n_resultados: int = 3,
        usar_cache: bool = True,
        gerar_preview: bool = True,
        analisar_contexto: bool = True,
        rerankear: bool = True,
        exportar: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not pergunta:
            return {"sucesso": False, "erro": "Pergunta vazia."}

        key = self._cache_key(pergunta, fonte_preferida or "tudo", n_resultados)
        
        # Verificar cache externo primeiro
        if usar_cache and self.cache_externo:
            cached = self.cache_externo.obter(key)
            if cached:
                logger.debug("[%s] Hit no cache externo.", self.nome_alma)
                return {"sucesso": True, "resultados": cached.get("resultados", []), "fonte": "cache_externo"}

        # Verificar cache interno
        if usar_cache and self.enable_cache:
            cached = self._cache.get(key)
            if cached:
                logger.debug("[%s] Hit no cache interno.", self.nome_alma)
                return {"sucesso": True, "resultados": cached.get("resultados", []), "fonte": "cache_interno"}

        if not self.biblioteca_principal:
            return {"sucesso": False, "erro": "Biblioteca não disponível."}

        func = getattr(self.biblioteca_principal, "consultar", None)
        if not callable(func):
            return {"sucesso": False, "erro": "Biblioteca inválida."}

        try:
            resultado = func(
                pergunta=pergunta,
                fonte_preferida=fonte_preferida,
                n_resultados=n_resultados,
                usar_cache=usar_cache,
                gerar_preview=gerar_preview,
                analisar_contexto=analisar_contexto,
                rerankear=rerankear,
                exportar=exportar
            )

            # Coroutine handling
            if asyncio.iscoroutine(resultado):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        return {"sucesso": False, "erro": "Consulta assíncrona; use consultar_async."}
                    resultado = asyncio.run(resultado)
                except RuntimeError:
                    resultado = asyncio.run(resultado)

            # Armazenar no cache interno
            if self.enable_cache and usar_cache and isinstance(resultado, dict):
                self._cache[key] = {"resultados": resultado.get("resultados", [])}

            # Armazenar no cache externo
            if self.cache_externo and usar_cache and isinstance(resultado, dict):
                self.cache_externo.armazenar(key, {"resultados": resultado.get("resultados", [])})

            return resultado if isinstance(resultado, dict) else {"sucesso": True, "resultados": resultado}
        except Exception as e:
            logger.exception("[%s] Erro: %s", self.nome_alma, e)
            return {"sucesso": False, "erro": str(e)}

    async def consultar_async(
        self,
        pergunta: str,
        fonte_preferida: Optional[str] = "tudo",
        n_resultados: int = 3,
        usar_cache: bool = True,
        gerar_preview: bool = True,
        analisar_contexto: bool = True,
        rerankear: bool = True,
        exportar: Optional[str] = None,
    ) -> Dict[str, Any]:
        # Similar ao sync, mas await na biblioteca principal
        if not pergunta:
            return {"sucesso": False, "erro": "Pergunta vazia."}

        key = self._cache_key(pergunta, fonte_preferida or "tudo", n_resultados)
        
        if usar_cache and self.cache_externo:
            cached = self.cache_externo.obter(key)
            if cached:
                return {"sucesso": True, "resultados": cached.get("resultados", []), "fonte": "cache_externo"}

        if usar_cache and self.enable_cache:
            cached = self._cache.get(key)
            if cached:
                return {"sucesso": True, "resultados": cached.get("resultados", []), "fonte": "cache_interno"}

        if not self.biblioteca_principal:
            return {"sucesso": False, "erro": "Biblioteca não disponível."}

        func = getattr(self.biblioteca_principal, "consultar_async", None) or getattr(self.biblioteca_principal, "consultar", None)
        if not callable(func):
            return {"sucesso": False, "erro": "Biblioteca inválida."}

        try:
            resultado = func(
                pergunta=pergunta,
                fonte_preferida=fonte_preferida,
                n_resultados=n_resultados,
                usar_cache=usar_cache,
                gerar_preview=gerar_preview,
                analisar_contexto=analisar_contexto,
                rerankear=rerankear,
                exportar=exportar
            )
            if asyncio.iscoroutine(resultado):
                resultado = await resultado

            if self.enable_cache and usar_cache and isinstance(resultado, dict):
                self._cache[key] = {"resultados": resultado.get("resultados", [])}
            if self.cache_externo and usar_cache and isinstance(resultado, dict):
                self.cache_externo.armazenar(key, {"resultados": resultado.get("resultados", [])})

            return resultado if isinstance(resultado, dict) else {"sucesso": True, "resultados": resultado}
        except Exception as e:
            logger.exception("[%s] Erro async: %s", self.nome_alma, e)
            return {"sucesso": False, "erro": str(e)}

    def obter_estatisticas(self) -> Dict[str, Any]:
        try:
            fn = getattr(self.biblioteca_principal, "obter_estatisticas", None)
            if callable(fn):
                return {"sucesso": True, "estatisticas": fn()}
            return {"sucesso": True, "estatisticas": {"cache_size": len(self._cache)}}
        except Exception as e:
            return {"sucesso": False, "erro": str(e)}

    def pesquisar_biblia(self, consulta: str, n_resultados: int = 1) -> Dict[str, Any]:
        return self.consultar(consulta, fonte_preferida="biblia", n_resultados=n_resultados, rerankear=False)

    def pesquisar_doutrina(self, tema: str) -> Dict[str, Any]:
        pergunta = f"O que a Bíblia e as publicações relevantes ensinam sobre {tema}?"
        return self.consultar(pergunta, analisar_contexto=True, gerar_preview=True)

