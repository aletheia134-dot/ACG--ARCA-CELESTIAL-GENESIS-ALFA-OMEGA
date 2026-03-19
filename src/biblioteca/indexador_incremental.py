from __future__ import annotations
# src/biblioteca/indexador_incremental.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARCA CELESTIAL GENESIS - INDEXADOR INCREMENTAL BIBLIOTECA TEOLÓGICA
Processamento e indexao automtica de novos PDFs.
Implementao robusta e idempotente:
 - detecta novos PDFs via watchdog
 - processa em ThreadPoolExecutor para evitar bloqueio
 - calcula hash do contedo (SHA256) para idempotncia
 - divide texto em chunks razoveis para indexao
 - usa métodos adaptativos do SistemaMemoriaHibrido quando disponíveis
 - logging e tratamento de erros
"""
import logging
import time
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import PyPDF2
from datetime import datetime
import hashlib
import concurrent.futures
import os
import io

logger = logging.getLogger("IndexadorIncremental")

# Tentativa de import do SistemaMemoriaHibrido (pode no existir em ambiente de testes)
try:
    from src.memoria.sistema_memoria import SistemaMemoriaHibrido  # type: ignore
    MEMORIA_DISPONIVEL = True
except Exception as e:  # pragma: no cover - ambiente pode no ter esse módulo
    logger.debug("SistemaMemoriaHibrido no disponível: %s", e)
    SistemaMemoriaHibrido = None
    MEMORIA_DISPONIVEL = False


def _sha256_of_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _chunk_text(text: str, max_chars: int = 4000, overlap: int = 200) -> List[str]:
    """
    Divide texto em chunks com sobreposio pequena.
    - max_chars: tamanho aproximado (caracteres) por chunk
    - overlap: quantos caracteres sobrepostos entre chunks
    """
    if not text:
        return []
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    L = len(text)
    while start < L:
        end = min(start + max_chars, L)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == L:
            break
        start = max(0, end - overlap)
    return chunks


def _read_pdf_text(path: Path) -> str:
    """
    L texto de um PDF de forma defensiva usando PyPDF2.
    Retorna string vazia em caso de falha.
    """
    try:
        with path.open("rb") as fh:
            reader = PyPDF2.PdfReader(fh)
            parts = []
            for page in reader.pages:
                try:
                    txt = page.extract_text() or ""
                except Exception:
                    txt = ""
                parts.append(txt)
            return "\n".join(parts)
    except Exception as e:
        logger.exception("Falha ao ler PDF %s: %s", path, e)
        return ""


class _WorkerHandler(FileSystemEventHandler):
    """
    Watchdog handler que delega processamento a um executor (no bloqueante).
    """

    def __init__(self, indexador: "IndexadorIncremental", settle_time: float = 0.5):
        self.indexador = indexador
        self.settle_time = float(settle_time)

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() == ".pdf":
            logger.info("Novo PDF detectado: %s", path)
            # agenda processamento com pequeno delay para permitir escrita completa
            self.indexador._schedule_processing(path, delay=self.settle_time)


class IndexadorIncremental:
    """
    Indexa novos arquivos PDF de forma incremental no sistema de busca.
    """

    def __init__(
        self,
        memoria: Optional[SistemaMemoriaHibrido] = None,
        pasta_monitorada: Path = Path("datasets_fine_tuning/novos_documentos_jw"),
        processar_existentes: bool = True,
        max_workers: int = 4
    ):
        self.memoria = memoria
        self.pasta_monitorada = Path(pasta_monitorada)
        self.observer = Observer()
        self.pdf_handler = _WorkerHandler(self)
        self._hashes_indexados = set()
        self._hash_lock = threading.Lock()
        self._running = False
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._scheduled: Dict[str, float] = {}  # path -> scheduled_at (to avoid double scheduling)

        if not MEMORIA_DISPONIVEL or not self.memoria:
            logger.warning("Sistema de Memória no disponível. Indexao vetorial ficar desativada.")

        try:
            self.pasta_monitorada.mkdir(parents=True, exist_ok=True)
        except Exception:
            logger.exception("Falha ao criar pasta monitorada: %s", self.pasta_monitorada)

        logger.info("Indexador Incremental inicializado. Monitorando: %s", self.pasta_monitorada)

        if processar_existentes:
            # processar existentes de forma assncrona
            self._executor.submit(self._processar_existentes)

    # ----------------------------
    # Scheduling helpers
    # ----------------------------
    def _schedule_processing(self, path: Path, delay: float = 0.5):
        key = str(path.resolve())
        now = time.time()
        # evita mltiplas agendas em curto intervalo
        last = self._scheduled.get(key)
        if last and now - last < max(1.0, delay):
            logger.debug("Arquivo %s j agendado recentemente, ignorando re-agendamento.", path)
            return
        self._scheduled[key] = now
        def _delayed():
            time.sleep(delay)
            try:
                self.adicionar_pdf(path)
            finally:
                # limpar agendamento
                try:
                    del self._scheduled[key]
                except Exception:
                    pass
        try:
            self._executor.submit(_delayed)
        except Exception:
            # fallback thread
            threading.Thread(target=_delayed, daemon=True).start()

    # ----------------------------
    # Lifecycle: start / stop
    # ----------------------------
    def iniciar_monitoramento(self):
        """Inicia o monitoramento da pasta para novos PDFs."""
        if not MEMORIA_DISPONIVEL or not self.memoria:
            logger.error("Sistema de Memória no disponível. No  possível monitorar.")
            return
        if self._running:
            logger.debug("Monitoramento j ativo.")
            return
        self.observer.schedule(self.pdf_handler, str(self.pasta_monitorada), recursive=False)
        self.observer.start()
        self._running = True
        logger.info(" Monitoramento da pasta iniciado: %s", self.pasta_monitorada)

    def parar_monitoramento(self):
        """Para o monitoramento da pasta."""
        if not self._running:
            logger.debug("Monitoramento j parado.")
            return
        try:
            self.observer.stop()
            self.observer.join(timeout=5.0)
        except Exception:
            logger.exception("Erro ao parar observer.")
        finally:
            self._running = False
            logger.info("Monitoramento da pasta parado.")

    def shutdown(self, wait: bool = True):
        """Encerra executor e observer de forma limpa."""
        try:
            self.parar_monitoramento()
        except Exception:
            pass
        try:
            self._executor.shutdown(wait=wait)
        except Exception:
            logger.exception("Erro ao encerrar executor.")
        logger.info("IndexadorIncremental shutdown complete.")

    # ----------------------------
    # Processamento de PDFs
    # ----------------------------
    def _processar_existentes(self):
        """Processa arquivos PDF j presentes na pasta ação iniciar o indexador."""
        try:
            for arquivo in sorted(self.pasta_monitorada.glob("*.pdf")):
                try:
                    logger.debug("Processando existente: %s", arquivo)
                    # submeter ação executor para paralelismo controlado
                    self._executor.submit(self.adicionar_pdf, arquivo)
                except Exception:
                    logger.exception("Erro ao programar processamento de existente: %s", arquivo)
        except Exception:
            logger.exception("Erro ao iterar sobre arquivos existentes na pasta monitorada.")

    def adicionar_pdf(self, caminho_pdf: Path):
        """
        Processa e adiciona um único PDF ao índice.
        Método idempotente por hash do contedo (SHA256).
        """
        try:
            if not caminho_pdf or not caminho_pdf.exists():
                logger.warning("Arquivo inexistente: %s", caminho_pdf)
                return

            if not MEMORIA_DISPONIVEL or not self.memoria:
                logger.error("Sistema de Memória no disponível. Indexao desativada.")
                return

            logger.info("Indexando PDF: %s", caminho_pdf.name)

            # Ler contedo do arquivo em bytes para hash (mais robusto)
            try:
                raw = caminho_pdf.read_bytes()
            except Exception as e:
                logger.exception("Erro lendo bytes do PDF %s: %s", caminho_pdf, e)
                return

            file_hash = _sha256_of_bytes(raw)
            with self._hash_lock:
                if file_hash in self._hashes_indexados:
                    logger.info("PDF %s j indexado (hash %s). Ignorando.", caminho_pdf.name, file_hash[:8])
                    return
                # marcar imediatamente para evitar race conditions
                self._hashes_indexados.add(file_hash)

            # Extrair texto de forma defensiva
            texto_completo = _read_pdf_text(caminho_pdf)
            if not texto_completo or not texto_completo.strip():
                logger.warning("Texto vazio extrado de %s  ignorando.", caminho_pdf.name)
                # liberar marca para permitir novo processamento futuro
                with self._hash_lock:
                    self._hashes_indexados.discard(file_hash)
                return

            texto_processado = self._preprocessar_texto(texto_completo)

            # dividir em chunks para indexao
            chunks = _chunk_text(texto_processado, max_chars=4000, overlap=300)
            if not chunks:
                logger.warning("Nenhum chunk gerado para %s  ignorando.", caminho_pdf.name)
                with self._hash_lock:
                    self._hashes_indexados.discard(file_hash)
                return

            # metadados básicos
            nome_lower = caminho_pdf.stem.lower()
            if "biblia" in nome_lower or any(livro in nome_lower for livro in ["genesis", "mateus", "joao", "romanos"]):
                colecao = "biblia"
                tipo_documento = "versiculo"
            elif "sentinela" in nome_lower:
                colecao = "sentinela"
                tipo_documento = "artigo"
            elif "despertai" in nome_lower:
                colecao = "despertai"
                tipo_documento = "artigo"
            else:
                colecao = "outros"
                tipo_documento = "generico"

            metadados = {
                "fonte": caminho_pdf.name,
                "tipo": tipo_documento,
                "colecao": colecao,
                "data_indexacao": datetime.utcnow().isoformat() + "Z",
                "tamanho_original_caracteres": len(texto_completo),
                "hash_conteudo": file_hash
            }

            # Indexar usando métodos adaptativos do SistemaMemoriaHibrido
            try:
                # prefer add_documents_to_collection(documents=..., metadatas=[...], collection_name=...)
                if hasattr(self.memoria, "add_documents_to_collection"):
                    self.memoria.add_documents_to_collection(documents=chunks, metadatas=[metadados] * len(chunks), collection_name=colecao)
                    logger.info("Indexado %s via add_documents_to_collection (coleo=%s).", caminho_pdf.name, colecao)
                elif hasattr(self.memoria, "add_documents"):
                    # algumas implementaes usam (documents, metadatas, collection=...)
                    try:
                        self.memoria.add_documents(chunks, [metadados] * len(chunks), collection=colecao)
                    except TypeError:
                        # signature diferente: try keyword args
                        self.memoria.add_documents(documents=chunks, metadatas=[metadados] * len(chunks), collection=colecao)
                    logger.info("Indexado %s via add_documents (coleo=%s).", caminho_pdf.name, colecao)
                elif hasattr(self.memoria, "indexar_texto"):
                    # older API: indexar_texto(texto, metadados, colecao)
                    for chunk in chunks:
                        self.memoria.indexar_texto(chunk, metadados, colecao)
                    logger.info("Indexado %s via indexar_texto (coleo=%s).", caminho_pdf.name, colecao)
                else:
                    logger.error("Método de indexao no encontrado no SistemaMemoriaHibrido. No foi possível indexar %s.", caminho_pdf.name)
                    with self._hash_lock:
                        self._hashes_indexados.discard(file_hash)
                    return
            except Exception as e:
                logger.exception("Erro ao indexar %s: %s", caminho_pdf.name, e)
                with self._hash_lock:
                    self._hashes_indexados.discard(file_hash)
                return

            # registrar evento na memória se método disponível
            try:
                if hasattr(self.memoria, "registrar_evento"):
                    try:
                        self.memoria.registrar_evento(autor="IndexadorIncremental", tipo="indexacao_pdf", dados=metadados)
                    except TypeError:
                        # signature alternativa: registrar_evento(nome, dados)
                        try:
                            self.memoria.registrar_evento(metadados)
                        except Exception:
                            pass
            except Exception:
                logger.debug("Falha ao registrar evento na memória (no crítico).", exc_info=True)

            logger.info("Indexao concluda: %s (chunks=%d)", caminho_pdf.name, len(chunks))
        except Exception:
            logger.exception("Erro inesperado na adio do PDF %s", caminho_pdf)
            # tentativa de limpar estado em caso de erro
            try:
                with self._hash_lock:
                    self._hashes_indexados.discard(file_hash)
            except Exception:
                pass

    def _preprocessar_texto(self, texto: str) -> str:
        """
        Pr-processamento simples: normalizao de espaos e remoo de caracteres no desejados.
        """
        if not texto:
            return ""
        # normalizar espaos
        cleaned = " ".join(text.split())
        # manter apenas printable unicode characters (exemplo simples)
        cleaned = "".join(ch for ch in cleaned if ch == "\n" or ch == "\r" or (32 <= ord(ch) <= 0x10FFFF))
        return cleaned.strip()
