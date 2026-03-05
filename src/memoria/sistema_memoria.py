#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum
import json
import uuid

logger = logging.getLogger(__name__)

# Tentativa de import do chromadb
CHROMA_AVAILABLE = False
CHROMA_CLIENT = None
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
    logger.info("✅ ChromaDB disponível")
except ImportError as e:
    logger.warning(f"⚠️ ChromaDB não disponível: {e}")

# Tentativa de import do ConstrutorDataset
try:
    from src.memoria.construtor_dataset import ConstrutorDataset
    CONSTRUTOR_OK = True
except ImportError as e:
    logger.warning(f"⚠️ ConstrutorDataset não disponível: {e}")
    ConstrutorDataset = None
    CONSTRUTOR_OK = False

class TipoInteracao(Enum):
    CONVERSA = "conversa"
    REFLEXAO = "reflexao"
    APRENDIZADO = "aprendizado"
    SONHO = "sonho"
    DECISAO = "decisao"
    EMOCAO = "emocao"
    CURIOSIDADE = "curiosidade"


class SistemaMemoriaHibrido:
    def __init__(self, config=None):
        self.config = config
        self.diarios = {}  # nome_alma -> (conn, cursor)
        self.chroma_client = None
        self.chroma_collections = {}
        self.construtor_dataset = None
        self.lock = threading.RLock()
        
        # Inicializar ChromaDB com API nova
        self._inicializar_chroma()
        
        # Inicializar ConstrutorDataset se disponível
        if CONSTRUTOR_OK and ConstrutorDataset is not None:
            try:
                self.construtor_dataset = ConstrutorDataset(self)
                logger.info("✅ ConstrutorDataset inicializado")
            except Exception as e:
                logger.exception(f"Erro inicializando ConstrutorDataset: {e}")
                self.construtor_dataset = None
    
    def _inicializar_chroma(self):
        """Inicializa cliente ChromaDB com API compatível"""
        if not CHROMA_AVAILABLE:
            logger.warning("⚠️ ChromaDB não disponível - memória semântica desativada")
            return
            
        try:
            # Configurar diretório persistente
            persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
            os.makedirs(persist_dir, exist_ok=True)
            
            # Tentar API nova (PersistentClient)
            try:
                self.chroma_client = chromadb.PersistentClient(
                    path=persist_dir,
                    settings=Settings(anonymized_telemetry=False, allow_reset=False)
                )
                logger.info(f"✅ Cliente ChromaDB (PersistentClient) inicializado em {persist_dir}")
            except Exception as e:
                # Fallback para API antiga se necessário
                try:
                    self.chroma_client = chromadb.Client(
                        Settings(
                            chroma_db_impl="duckdb+parquet",
                            persist_directory=persist_dir,
                            anonymized_telemetry=False
                        )
                    )
                    logger.info(f"✅ Cliente ChromaDB (Client legacy) inicializado em {persist_dir}")
                except Exception as e2:
                    logger.warning(f"⚠️ Falha ao inicializar ChromaDB: {e2}")
                    self.chroma_client = None
                    
        except Exception as e:
            logger.warning(f"⚠️ Erro na configuração do ChromaDB: {e}")
            self.chroma_client = None
    
    def obter_colecao(self, nome_colecao: str):
        """Obtém ou cria uma coleção ChromaDB"""
        if not self.chroma_client:
            return None
            
        if nome_colecao in self.chroma_collections:
            return self.chroma_collections[nome_colecao]
            
        try:
            # Tentar obter coleção existente
            colecao = self.chroma_client.get_collection(name=nome_colecao)
        except:
            # Criar nova coleção
            try:
                colecao = self.chroma_client.create_collection(name=nome_colecao)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao criar coleção {nome_colecao}: {e}")
                return None
                
        self.chroma_collections[nome_colecao] = colecao
        return colecao
    
    def listar_ais(self) -> List[str]:
        """Retorna lista de nomes de AIs conhecidas"""
        # Implementação básica
        return ["EVA", "KAIYA", "LUMINA", "NYRA", "WELLINGTON", "YUNA"]
    
    def shutdown(self):
        """Desliga recursos da memória"""
        logger.info("Desligando SistemaMemoriaHibrido")
        # Fechar conexões SQLite
        for nome_alma, (conn, _) in self.diarios.items():
            try:
                conn.close()
            except:
                pass
        self.diarios.clear()
        self.chroma_collections.clear()
