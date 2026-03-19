# -*- coding: utf-8 -*-
from __future__ import annotations
"""
ARCA CELESTIAL GENESIS - BIBLIOTECA PRINCIPAL (Atualizada com paralelização, fallbacks e ligações).
"""
import asyncio
import logging
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional

# --- IMPORTS ---
from src.biblioteca.busca_hibrida import BuscaHibrida
from src.biblioteca.cache_consultas import CacheConsultas
from src.biblioteca.reranking import RerankingInteligente
from src.biblioteca.preview import PreviewInteligente
from src.biblioteca.analisador_contexto import AnalisadorContexto
from src.biblioteca.exportador_resultados import ExportadorResultados
from src.biblioteca.monitor_biblioteca import MonitorBiblioteca

try:
    from src.memoria.sistema_memoria import SistemaMemoriaHibrido
    from src.core.coracao_orquestrador import CoracaoOrquestrador
    MEMORIA_DISPONIVEL = True
except Exception:
    MEMORIA_DISPONIVEL = False
    SistemaMemoriaHibrido = None
    CoracaoOrquestrador = None

logger = logging.getLogger("BibliotecaJWOtimizada")

class BibliotecaJWOtimizada:
    def __init__(
        self,
        memoria: Optional[SistemaMemoriaHibrido] = None,
        coracao: Optional[CoracaoOrquestrador] = None,
        config: Optional[Dict[str, Any]] = None,
        caminho_cache: Path = Path("Santuarios/Alma_Imutavel/biblioteca_teocratica/cache_consultas.json")
    ):
        self.memoria = memoria
        self.coracao = coracao
        self.config = config or {}
        self.caminho_cache = caminho_cache

        # Inicializar componentes com tolerncia
        try:
            self.cache = CacheConsultas(caminho_arquivo=self.caminho_cache)
        except Exception:
            logger.exception("Falha ao inicializar CacheConsultas; usando None.")
            self.cache = None

        self.analisador_contexto = AnalisadorContexto() if AnalisadorContexto else None
        self.busca_hibrida = BuscaHibrida(memoria=self.memoria) if BuscaHibrida else None
        self.reranker = RerankingInteligente() if RerankingInteligente else None
        self.preview = PreviewInteligente() if PreviewInteligente else None
        self.exportador = ExportadorResultados() if ExportadorResultados else None
        self.monitor = MonitorBiblioteca() if MonitorBiblioteca else None

        if not MEMORIA_DISPONIVEL:
            logger.warning("Sistema de Memória no disponível.")
        logger.info("Biblioteca Teolgica Otimizada inicializada.")

    def consultar(
        self,
        pergunta: str,
        fonte_preferida: Optional[str] = "tudo",
        n_resultados: int = 5,
        usar_cache: bool = True,
        gerar_preview: bool = True,
        analisar_contexto: bool = True,
        rerankear: bool = True,
        exportar: Optional[str] = None
    ) -> Dict[str, Any]:
        """Consulta sncrona (pode chamar async internamente)."""
        # Usar asyncio.run para sync wrapper
        return asyncio.run(self.consultar_async(pergunta, fonte_preferida, n_resultados, usar_cache, gerar_preview, analisar_contexto, rerankear, exportar))

    async def consultar_async(
        self,
        pergunta: str,
        fonte_preferida: Optional[str] = "tudo",
        n_resultados: int = 5,
        usar_cache: bool = True,
        gerar_preview: bool = True,
        analisar_contexto: bool = True,
        rerankear: bool = True,
        exportar: Optional[str] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        logger.info("Nova consulta: '%s...'", pergunta[:50])

        # Monitor: registrar
        if self.monitor:
            try:
                self.monitor.registrar_consulta(pergunta)
            except Exception:
                logger.debug("Falha no monitor (no crítico).")

        # Cache
        cache_key = self._gerar_chave_cache(pergunta, fonte_preferida or "tudo", n_resultados)
        if usar_cache and self.cache:
            cached = self.cache.obter(cache_key)
            if cached:
                if self.monitor:
                    self.monitor.registrar_hit_cache()
                return cached

        # Anlise de contexto
        analise = {}
        if analisar_contexto and self.analisador_contexto:
            try:
                analise = self.analisador_contexto.analisar(pergunta)
            except Exception:
                logger.exception("Falha na anlise.")

        # Ajustar parmetros
        n_resultados_final = analise.get('recomendacao_n_results', n_resultados)
        fonte_final = analise.get('recomendacao_fonte', fonte_preferida or "tudo")

        # Busca
        resultados_brutos = []
        if self.busca_hibrida:
            try:
                resultados_brutos = self.busca_hibrida.buscar(pergunta, fonte_final, n_resultados_final)
            except Exception:
                logger.exception("Falha na busca; vazios.")

        # Paralelizar rerank e preview
        tasks = []
        if rerankear and self.reranker:
            tasks.append(asyncio.create_task(self._rerank_async(resultados_brutos, pergunta)))
        else:
            tasks.append(asyncio.create_task(asyncio.sleep(0)))
        
        if gerar_preview and self.preview:
            tasks.append(asyncio.create_task(self._preview_async(resultados_brutos, pergunta)))
        else:
            tasks.append(asyncio.create_task(asyncio.sleep(0)))
        
        await asyncio.gather(*tasks)
        resultados_rerankeados = tasks[0].result() if tasks[0].done() and isinstance(tasks[0].result(), list) else resultados_brutos
        previews = tasks[1].result() if tasks[1].done() and isinstance(tasks[1].result(), list) else []

        # Montar resultado
        resultado = {
            "resultados": resultados_rerankeados,
            "analise_contexto": analise,
            "previews": previews,
            "fonte_utilizada": fonte_final,
            "tempo_total_ms": round((time.time() - start_time) * 1000, 2)
        }

        # Cache
        if usar_cache and self.cache:
            try:
                self.cache.armazenar(cache_key, resultado)
            except Exception:
                logger.exception("Falha no cache.")

        # Exportar
        if exportar and self.exportador:
            try:
                caminho = self.exportador.exportar(resultado, formato=exportar)
                resultado['caminho_exportado'] = str(caminho)
            except Exception:
                logger.exception("Falha na exportao.")

        # Monitor: sucesso
        if self.monitor:
            try:
                self.monitor.registrar_consulta_sucesso(resultado.get("tempo_total_ms", 0))
            except Exception:
                logger.debug("Falha no monitor.")

        return resultado

    async def _rerank_async(self, resultados: List[Dict[str, Any]], consulta: str) -> List[Dict[str, Any]]:
        if self.reranker:
            return self.reranker.rerank(resultados, consulta)
        return resultados

    async def _preview_async(self, resultados: List[Dict[str, Any]], consulta: str) -> List[Dict[str, Any]]:
        if self.preview:
            return self.preview.gerar_previews(resultados, consulta)
        return []

    def _gerar_chave_cache(self, pergunta: str, fonte: str, n_resultados: int) -> str:
        data = f"{pergunta}||{fonte}||{n_resultados}".encode('utf-8')
        return hashlib.md5(data).hexdigest()

    def obter_estatisticas(self) -> Dict[str, Any]:
        stats = {}
        if self.cache:
            stats['cache'] = self.cache.obter_estatisticas()
        if self.monitor:
            stats['monitor'] = self.monitor.obter_metricas()
        return stats

    def limpar_cache(self):
        if self.cache:
            self.cache.limpar()

