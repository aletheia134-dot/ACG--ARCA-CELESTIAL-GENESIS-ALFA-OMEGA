#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
RESPONSE QUEUE MANAGER v2 - Com priorizao, deduplicao, batching, rate limiting, mtricas
"""


import hashlib
import json
import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from queue import PriorityQueue, Queue, Full, Empty
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("ResponseQueueManagerV2")
logger.addHandler(logging.NullHandler())


class ResponseQueueManagerV2:
    """
    Verso melhorada com:
    - Fila com 3 nveis de prioridade (crítica, ALTA, NORMAL)
    - Deduplicao automtica
    - Batching de mensagens similares
    - Rate limiting
    - Mtricas detalhadas
    - Replay de críticas persistidas
    """
    
    # Prioridades
    PRIORITY_CRITICA = 0
    PRIORITY_ALTA = 1
    PRIORITY_NORMAL = 2
    
    def __init__(self, maxsize: int = 1000, rate_limit: int = 10, persistir_criticas: bool = True):
        """
        Args:
            maxsize: tamanho máximo da fila
            rate_limit: máximo de mensagens por segundo
            persistir_criticas: persistir mensagens críticas
        """
        self.queue = PriorityQueue(maxsize=maxsize)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._lock = threading.RLock()
        
        # Rate limiting
        self.rate_limit = rate_limit
        self.timestamps_enviadas = deque(maxlen=rate_limit + 1)
        
        # Deduplicao (ltimas 100 msgs)
        self.hashes_recentes = deque(maxlen=100)
        
        # Batching (agrupa msgs do mesmo tipo)
        self.buffer_batch: Dict[str, List[Dict]] = defaultdict(list)
        self.buffer_batch_timeout = 2.0  # 2 segundos
        self.ultimo_flush_batch = time.time()
        
        # Persistncia
        self.persistir_criticas = persistir_criticas
        self.caminho_criticas = Path("./arca_criticas_v2.jsonl")
        
        # Mtricas
        self.metricas = {
            "total_enfileiradas": 0,
            "total_processadas": 0,
            "total_descartadas": 0,
            "mensagens_por_tipo": defaultdict(int),
            "tempo_medio_fila": 0.0,
            "taxa_drop": 0.0
        }
        
        self.logger.info(f"[OK] ResponseQueueManager v2 inicializado (rate_limit={rate_limit}/s)")
    
    # -------------------------
    # Enqueueing
    # -------------------------
    def put(self, payload: Dict[str, Any], timeout: Optional[float] = None, 
             priority: int = PRIORITY_NORMAL, critical: bool = False) -> bool:
        """
        Adiciona mensagem com prioridade.Args:
            payload: dicionrio com mensagem
            timeout: tempo máximo de espera
            priority: 0=crítica, 1=alta, 2=normal
            critical: fora persistncia mesmo se fila cheia
        
        Retorna:
            True se enfileirada, False caso contrrio
        """
        if not isinstance(payload, dict):
            self.logger.warning("Payload invlido (no  dict)")
            return False
        
        # Adicionar timestamp
        if "timestamp" not in payload:
            payload["timestamp"] = datetime.utcnow().isoformat()
        
        # Verificar rate limit
        if not self._verificar_rate_limit():
            self.logger.debug("Rate limit atingido; descartando mensagem")
            self.metricas["total_descartadas"] += 1
            return False
        
        # Verificar duplicao
        hash_payload = self._gerar_hash(payload)
        if hash_payload in self.hashes_recentes:
            self.logger.debug(f"Duplicao detectada; descartando: {payload.get('tipo_resp')}")
            return False
        
        self.hashes_recentes.append(hash_payload)
        
        # Verificar batching possível
        tipo_resp = payload.get("tipo_resp", "UNKNOWN")
        if self._eh_batchavel(tipo_resp):
            self.buffer_batch[tipo_resp].append(payload)
            if time.time() - self.ultimo_flush_batch > self.buffer_batch_timeout:
                self._flush_batches()
            return True
        
        # Enfileirar normal
        try:
            self.queue.put((priority, time.time(), payload), timeout=timeout)
            self.metricas["total_enfileiradas"] += 1
            self.metricas["mensagens_por_tipo"][tipo_resp] += 1
            self.logger.debug(f"Mensagem enfileirada (priority={priority}): {tipo_resp}")
            return True
        except Full:
            if critical:
                self.logger.warning(f"Fila cheia; persistindo crítica: {tipo_resp}")
                self._persistir_critica(payload)
                return True
            else:
                self.logger.warning(f"Fila cheia; descartando: {tipo_resp}")
                self.metricas["total_descartadas"] += 1
                return False
        except Exception as e:
            self.logger.exception(f"Erro ao enfileirar: {e}")
            return False
    
    def put_nowait(self, payload: Dict[str, Any], priority: int = PRIORITY_NORMAL, 
                   critical: bool = False) -> bool:
        """Verso non-blocking."""
        return self.put(payload, timeout=0.0, priority=priority, critical=critical)
    
    # -------------------------
    # Deqeueing
    # -------------------------
    def get(self, timeout: Optional[float] = 1.0) -> Optional[Dict[str, Any]]:
        """Remove e retorna mensagem da fila."""
        try:
            priority, ts, payload = self.queue.get(timeout=timeout)
            
            # Calcular tempo na fila
            tempo_fila = time.time() - ts
            self._atualizar_metrica_tempo_fila(tempo_fila)
            
            # Atualizar mtricas
            self.metricas["total_processadas"] += 1
            
            return payload
        except Empty:
            return None
        except Exception as e:
            self.logger.exception(f"Erro ao desenfeirar: {e}")
            return None
    
    def get_nowait(self) -> Optional[Dict[str, Any]]:
        """Non-blocking get."""
        return self.get(timeout=0.0)
    
    def get_batch(self, timeout: Optional[float] = 1.0, max_batch: int = 10) -> List[Dict[str, Any]]:
        """Retorna at N mensagens."""
        batch = []
        for _ in range(max_batch):
            msg = self.get(timeout=0.1)
            if msg:
                batch.append(msg)
            else:
                break
        return batch
    
    # -------------------------
    # Rate Limiting
    # -------------------------
    def _verificar_rate_limit(self) -> bool:
        """Verifica se pode enviar (rate limit)."""
        agora = time.time()
        
        # Remover timestamps antigos (> 1 segundo)
        while self.timestamps_enviadas and (agora - self.timestamps_enviadas[0]) > 1.0:
            self.timestamps_enviadas.popleft()
        
        # Se atingiu limite, negar
        if len(self.timestamps_enviadas) >= self.rate_limit:
            return False
        
        self.timestamps_enviadas.append(agora)
        return True
    
    # -------------------------
    # Deduplication
    # -------------------------
    def _gerar_hash(self, payload: Dict[str, Any]) -> str:
        """Gera hash do payload para dedup."""
        chave = f"{payload.get('tipo_resp')}_{payload.get('conteudo_key', '')}"
        return hashlib.md5(chave.encode()).hexdigest()
    
    # -------------------------
    # Batching
    # -------------------------
    def _eh_batchavel(self, tipo_resp: str) -> bool:
        """Verifica se tipo pode ser agrupado."""
        batchaveis = ["LOG_REINO", "DEBUG_LOG", "STAT_UPDATE"]
        return tipo_resp in batchaveis
    
    def _flush_batches(self) -> None:
        """Enfileira batches acumulados."""
        for tipo_resp, msgs in list(self.buffer_batch.items()):
            if msgs:
                # Criar mensagem batch
                batch_payload = {
                    "tipo_resp": f"{tipo_resp}_BATCH",
                    "mensagens": msgs,
                    "quantidade": len(msgs),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                try:
                    self.queue.put((self.PRIORITY_NORMAL, time.time(), batch_payload), timeout=0.5)
                    self.logger.debug(f"Batch enfileirado: {len(msgs)} msgs de {tipo_resp}")
                except Exception:
                    self.logger.debug(f"Falha ao enfileirar batch de {tipo_resp}")
                
                self.buffer_batch[tipo_resp] = []
        
        self.ultimo_flush_batch = time.time()
    
    # -------------------------
    # Persistncia
    # -------------------------
    def _persistir_critica(self, payload: Dict[str, Any]) -> None:
        """Persiste mensagem crítica."""
        if not self.persistir_criticas:
            return
        
        try:
            with open(self.caminho_criticas, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
            self.logger.info(f"crítica persistida: {payload.get('tipo_resp')}")
        except Exception as e:
            self.logger.exception(f"Erro ao persistir: {e}")
    
    def carregar_criticas_persistidas(self) -> List[Dict[str, Any]]:
        """Carrega e reinsere mensagens críticas persistidas."""
        if not self.caminho_criticas.exists():
            return []
        
        mensagens = []
        try:
            with open(self.caminho_criticas, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            msg = json.loads(line)
                            mensagens.append(msg)
                            # Reinserir na fila
                            self.put(msg, priority=self.PRIORITY_CRITICA)
                        except json.JSONDecodeError:
                            pass
            
            if mensagens:
                self.logger.info(f"Carregadas {len(mensagens)} mensagens críticas persistidas")
                # Limpar arquivo
                self.caminho_criticas.unlink()
        except Exception as e:
            self.logger.exception(f"Erro ao carregar críticas: {e}")
        
        return mensagens
    
    # -------------------------
    # Mtricas
    # -------------------------
    def _atualizar_metrica_tempo_fila(self, tempo: float) -> None:
        """Atualiza tempo mdio na fila."""
        media_atual = self.metricas["tempo_medio_fila"]
        total_proc = self.metricas["total_processadas"]
        
        if total_proc > 0:
            nova_media = (media_atual * (total_proc - 1) + tempo) / total_proc
            self.metricas["tempo_medio_fila"] = nova_media
    
    def obter_metricas(self) -> Dict[str, Any]:
        """Retorna mtricas de operação."""
        with self._lock:
            total = self.metricas["total_enfileiradas"]
            descartadas = self.metricas["total_descartadas"]
            taxa_drop = (descartadas / total * 100) if total > 0 else 0.0
            
            return {
                "total_enfileiradas": self.metricas["total_enfileiradas"],
                "total_processadas": self.metricas["total_processadas"],
                "total_descartadas": descartadas,
                "taxa_drop_percentual": taxa_drop,
                "tempo_medio_fila_ms": self.metricas["tempo_medio_fila"] * 1000,
                "tamanho_fila_atual": self.queue.qsize(),
                "mensagens_por_tipo": dict(self.metricas["mensagens_por_tipo"]),
                "buffer_batch_pendente": {k: len(v) for k, v in self.buffer_batch.items() if v}
            }
    
    # -------------------------
    # Utilities
    # -------------------------
    def qsize(self) -> int:
        """Retorna tamanho aproximado da fila."""
        return self.queue.qsize()
    
    def empty(self) -> bool:
        """Fila vazia?"""
        return self.queue.empty()
    
    def clear(self) -> None:
        """Limpa fila."""
        try:
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except Empty:
                    break
            self.logger.info("Fila limpa")
        except Exception as e:
            self.logger.exception(f"Erro ao limpar: {e}")
    
    def shutdown(self) -> None:
        """Desliga com persistncia."""
        self.logger.info("[START] ResponseQueueManager v2 desligando...")
        
        # Flush batches pendentes
        self._flush_batches()
        
        # Mtricas finais
        self.logger.info(f"Mtricas finais: {self.obter_metricas()}")
        
        self.clear()
        self.logger.info("[OK] Desligamento completo")


