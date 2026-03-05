#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARCA CELESTIAL GENESIS - MONITOR BIBLIOTECA TEOLÓGICA
Componente para acompanhamento de métricas de uso e desempenho.
"""
from __future__ import annotations
import logging
import threading
from typing import Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger("MonitorBiblioteca")


class MonitorBiblioteca:
    """
    Monitora o desempenho e uso da biblioteca teológica.Uso típico:
      monitor.registrar_consulta(texto)
      if cache_hit: monitor.registrar_hit_cache()
      monitor.registrar_consulta_sucesso(tempo_ms)
      # ou em caso de erro:
      monitor.registrar_consulta_falha(erro)
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._metricas = {
            "consultas_totais": 0,
            "consultas_com_cache_hit": 0,
            "consultas_sem_cache_hit": 0,
            "consultas_falhas": 0,
            "tempo_total_consultas_ms": 0.0,
            "tempo_maximo_consulta_ms": 0.0,
            "tempo_minimo_consulta_ms": float("inf"),
            "ultima_consulta_timestamp": None,
        }
        # Flag temporária para indicar se a consulta corrente teve cache hit
        self._ultimo_foi_cache_hit = False
        logger.info("ðŸ“Š Monitor de Biblioteca inicializado.")

    def registrar_consulta(self, texto_consulta: str) -> None:
        """Registra o início de uma nova consulta e zera a flag de hit temporária."""
        with self._lock:
            self._metricas["consultas_totais"] += 1
            self._metricas["ultima_consulta_timestamp"] = datetime.now(timezone.utc).isoformat()
            self._ultimo_foi_cache_hit = False
        logger.debug("Consulta registrada: '%s...'", (texto_consulta or "")[:30])

    def registrar_hit_cache(self) -> None:
        """Registra que a consulta corrente obteve hit no cache."""
        with self._lock:
            self._metricas["consultas_com_cache_hit"] += 1
            self._ultimo_foi_cache_hit = True
        logger.debug("Hit no cache registrado.")

    def registrar_consulta_sucesso(self, tempo_ms: float) -> None:
        """
        Registra o sucesso de uma consulta e seu tempo de execução.Observação: este método usa a flag interna `_ultimo_foi_cache_hit` para
        contabilizar misses (se a consulta não foi marcada como hit previamente).
        """
        with self._lock:
            # Atualiza tempos
            try:
                t = float(tempo_ms)
            except Exception:
                t = 0.0
            self._metricas["tempo_total_consultas_ms"] += t
            if t > self._metricas["tempo_maximo_consulta_ms"]:
                self._metricas["tempo_maximo_consulta_ms"] = t
            if t < self._metricas["tempo_minimo_consulta_ms"]:
                self._metricas["tempo_minimo_consulta_ms"] = t

            # Conta miss se a consulta não foi marcada como hit
            if not self._ultimo_foi_cache_hit:
                self._metricas["consultas_sem_cache_hit"] += 1

            # Reset flag para a próxima consulta
            self._ultimo_foi_cache_hit = False

        logger.debug("Sucesso de consulta registrado.Tempo: %.2f ms", t)

    def registrar_consulta_falha(self, erro: str) -> None:
        """Registra uma falha em uma consulta e limpa flag de hit temporária."""
        with self._lock:
            self._metricas["consultas_falhas"] += 1
            # Em caso de falha, não contamos como hit nem miss — depende da política
            self._ultimo_foi_cache_hit = False
        logger.error("Falha de consulta registrada: %s", erro)

    def obter_metricas(self) -> Dict[str, Any]:
        """
        Retorna as métricas acumuladas (cópia segura) e algumas métricas derivadas.
        """
        with self._lock:
            m = dict(self._metricas)  # shallow copy
        total = m.get("consultas_totais", 0)
        # calcular métricas derivadas de forma defensiva
        tempo_total = m.get("tempo_total_consultas_ms", 0.0) or 0.0
        tempo_medio = (tempo_total / total) if total > 0 else 0.0
        hits = m.get("consultas_com_cache_hit", 0)
        misses = m.get("consultas_sem_cache_hit", 0)
        falhas = m.get("consultas_falhas", 0)
        taxa_hit = (hits / total * 100.0) if total > 0 else 0.0
        taxa_miss = (misses / total * 100.0) if total > 0 else 0.0

        tempo_min = m.get("tempo_minimo_consulta_ms", float("inf"))
        if tempo_min == float("inf"):
            tempo_min = 0.0

        derived = {
            "consultas_totais": total,
            "consultas_com_cache_hit": hits,
            "consultas_sem_cache_hit": misses,
            "consultas_falhas": falhas,
            "tempo_total_consultas_ms": tempo_total,
            "tempo_medio_consulta_ms": tempo_medio,
            "tempo_maximo_consulta_ms": m.get("tempo_maximo_consulta_ms", 0.0) or 0.0,
            "tempo_minimo_consulta_ms": tempo_min,
            "taxa_cache_hit_percent": round(taxa_hit, 2),
            "taxa_cache_miss_percent": round(taxa_miss, 2),
            "ultima_consulta_timestamp": m.get("ultima_consulta_timestamp"),
        }
        logger.debug("Métricas obtidas: total=%d, hits=%d, misses=%d, falhas=%d", total, hits, misses, falhas)
        return derived

    def resetar_metricas(self) -> None:
        """Redefine todas as métricas para os valores iniciais."""
        with self._lock:
            self._metricas = {
                "consultas_totais": 0,
                "consultas_com_cache_hit": 0,
                "consultas_sem_cache_hit": 0,
                "consultas_falhas": 0,
                "tempo_total_consultas_ms": 0.0,
                "tempo_maximo_consulta_ms": 0.0,
                "tempo_minimo_consulta_ms": float("inf"),
                "ultima_consulta_timestamp": None,
            }
            self._ultimo_foi_cache_hit = False
        logger.info("Métricas do Monitor de Biblioteca resetadas.")


