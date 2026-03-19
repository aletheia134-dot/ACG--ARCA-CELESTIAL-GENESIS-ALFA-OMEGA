#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import inspect
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Callable
import re
import time

try:
    from src.memoria.memory_facade import MemoryFacade
except:
    logging.getLogger(__name__).warning("[AVISO] MemoryFacade no disponível")
    MemoryFacade = None  # ser tratado em runtime

try:
    from src.memoria.sistema_memoria import SistemaMemoriaHibrido
except:
    logging.getLogger(__name__).warning("[AVISO] MemoryFacade no disponível")
    MemoryFacade = None

DEFAULT_AIS = ["EVA", "LUMINA", "NYRA", "YUNA", "KAIYA", "WELLINGTON"]
# controla se a factory tentar criar colees Chroma automaticamente
ENV_CREATE_CHROMA = os.getenv("MEMORIA_CREATE_CHROMA_COLLECTIONS", "false").lower() in ("1", "true", "yes")


def _sanitize_nome_alma(raw: str) -> Optional[str]:
    if raw is None:
        return None
    nome = str(raw).strip().upper()
    if not nome:
        return None
    # permitir letras, números, underscore e hfen; evitar traversal/path chars
    if not re.match(r"^[A-Z0-9_\-]{1,64}$", nome):
        return None
    return nome


def _nomes_de_sistema_memoria(sistema_memoria: Any) -> Optional[List[str]]:
    try:
        if not sistema_memoria:
            return None
        if hasattr(sistema_memoria, "listar_ais"):
            return [str(n).strip().upper() for n in sistema_memoria.listar_ais() if str(n).strip()]
        if hasattr(sistema_memoria, "ais"):
            return [str(n).strip().upper() for n in getattr(sistema_memoria, "ais") or []]
    except Exception:
        pass
    return None


def _nomes_de_config(config: Any) -> Optional[List[str]]:
    try:
        if not config:
            return None
        if hasattr(config, "get"):
            # tenta vrias assinaturas comuns
            raw = None
            try:
                raw = config.get("AIS_LISTA_CSV", None)
            except Exception:
                try:
                    raw = config.get("MEMORIA", "AIS_LISTA_CSV", fallback=None)
                except:
                    pass
            if raw:
                if isinstance(raw, str):
                    return [a.strip().upper() for a in raw.split(",") if a.strip()]
                if isinstance(raw, (list, tuple)):
                    return [str(a).strip().upper() for a in raw]
        if isinstance(config, dict):
            raw = config.get("AIS_LISTA_CSV") or config.get("AIS_LISTA")
            if raw:
                if isinstance(raw, str):
                    return [a.strip().upper() for a in raw.split(",") if a.strip()]
                if isinstance(raw, (list, tuple)):
                    return [str(a).strip().upper() for a in raw]
    except Exception:
        pass
    return None


def _call_memory_facade_constructor(mf_class: Callable, nome: str, config: Any) -> Any:
    """
    Chama o construtor de MemoryFacade de forma robusta, inspecionando assinatura.
    """
    sig = inspect.signature(mf_class)
    params = sig.parameters
    nome_kw = None
    config_kw = None
    for p in params.values():
        n = p.name.lower()
        if n in ("nome_alma", "nome", "name", "alma"):
            nome_kw = p.name
        if n in ("config", "cfg", "config_instance"):
            config_kw = p.name

    kwargs = {}
    if nome_kw:
        kwargs[nome_kw] = nome
    if config_kw:
        kwargs[config_kw] = config

    try:
        if kwargs:
            return mf_class(**kwargs)
        # fallback: tentar passar s nome
        return mf_class(nome)
    except TypeError:
        # ltimo recurso: tentar qualquer combinao
        try:
            return mf_class(nome, config)
        except Exception:
            # propaga para o chamador tratar
            raise


class FacadeBundle(dict):
    """
    Dict-like retornado pela factory. Fornece utilitrios:
      - shutdown(): fecha recursos em cada facade
      - health(): executa status() de cada facade (se disponível)
      - get_or_create(nome): cria lazy facade on-demand
    """

    def shutdown(self) -> None:
        for name, f in list(self.items()):
            try:
                if hasattr(f, "shutdown"):
                    f.shutdown()
            except Exception:
                logging.getLogger("facade_factory").exception("Erro ao shutdown de %s", name)

    def health(self) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for name, f in self.items():
            try:
                if hasattr(f, "status"):
                    out[name] = {"ok": True, "status": f.status()}
                else:
                    out[name] = {"ok": True, "status": {}}
            except Exception as e:
                out[name] = {"ok": False, "error": str(e)}
        return out

    def get_or_create(self, nome: str, config: Any = None, criar_collections_chroma: Optional[bool] = None) -> Optional[Any]:
        nome_norm = _sanitize_nome_alma(nome)
        if not nome_norm:
            return None
        if nome_norm in self:
            return self[nome_norm]
        # cria sob demanda
        try:
            log = logging.getLogger("facade_factory")
            mf = None
            if MemoryFacade is None:
                log.error("MemoryFacade no disponível no ambiente")
                return None
            mf = _call_memory_facade_constructor(MemoryFacade, nome_norm, config)
            if criar_collections_chroma is None:
                criar_collections_chroma = ENV_CREATE_CHROMA
            try:
                if criar_collections_chroma and hasattr(mf, "inicializar_collections"):
                    mf.inicializar_collections()
            except Exception:
                log.debug("Falha ao inicializar collections (on-demand) para %s", nome_norm, exc_info=True)
            self[nome_norm] = mf
            log.info("[OK] MemoryFacade get_or_create criado para %s", nome_norm)
            return mf
        except Exception:
            logging.getLogger("facade_factory").exception("Erro get_or_create para %s", nome)
            return None


def inicializar_facades_memoria(
    sistema_memoria: Optional[Any] = None,
    config: Optional[Any] = None,
    nomes_override: Optional[List[str]] = None,
    criar_collections_chroma: Optional[bool] = None,
    logger: Optional[logging.Logger] = None,
    paralelo: bool = True,
    max_workers: Optional[int] = None,
    timeout_por_alma: int = 30
) -> FacadeBundle:
    """
    Inicializa e retorna um FacadeBundle (dict-like) com MemoryFacade por alma detectada.
    Parmetros:
      - sistema_memoria: instncia de SistemaMemoriaHibrido (opcional)
      - config: objeto de configuração (opcional)
      - nomes_override: lista explcita de nomes de almas (opcional)
      - criar_collections_chroma: se True, tenta criar colees Chroma (padrão via ENV)
      - logger: logger a usar
      - paralelo: se True, inicializa em paralelo com ThreadPoolExecutor
      - max_workers: limite de workers (se None, calcula automaticamente)
      - timeout_por_alma: timeout em segundos por alma na criao paralela
    """
    log = logger or logging.getLogger("facade_factory")
    facades: Dict[str, Any] = {}

    if MemoryFacade is None:
        log.error("MemoryFacade no est disponível (import falhou). Retornando vazio.")
        return FacadeBundle(facades)

    nomes: Optional[List[str]] = None
    if nomes_override:
        nomes = [str(n).strip().upper() for n in nomes_override if str(n).strip()]
    else:
        nomes = _nomes_de_sistema_memoria(sistema_memoria)
        if not nomes:
            nomes = _nomes_de_config(config)
    if not nomes:
        nomes = DEFAULT_AIS.copy()
        log.info("Nenhuma lista de almas encontrada; usando padrão: %s", ", ".join(nomes))

    # sanitizar e deduplicar
    nomes_sanitizados: List[str] = []
    for n in nomes:
        ns = _sanitize_nome_alma(n)
        if ns and ns not in nomes_sanitizados:
            nomes_sanitizados.append(ns)

    if criar_collections_chroma is None:
        criar_collections_chroma = ENV_CREATE_CHROMA

    def _criar_uma(nome_alma: str) -> Optional[Any]:
        try:
            mf = _call_memory_facade_constructor(MemoryFacade, nome_alma, config)
            if criar_collections_chroma and hasattr(mf, "inicializar_collections"):
                try:
                    mf.inicializar_collections()
                except Exception:
                    log.debug("Falha ao criar collections para %s (no crítico)", nome_alma, exc_info=True)
            log.info("[OK] MemoryFacade inicializado para %s", nome_alma)
            return mf
        except Exception:
            log.exception("[ERRO] Falha ao criar MemoryFacade para %s", nome_alma)
            return None

    if paralelo and len(nomes_sanitizados) > 1:
        workers = max_workers or min(8, max(2, (len(nomes_sanitizados) // 2) + 1))
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_criar_uma, nome): nome for nome in nomes_sanitizados}
            for fut in as_completed(futures):
                nome = futures[fut]
                try:
                    mf = fut.result(timeout=timeout_por_alma)
                    if mf:
                        facades[nome] = mf
                except Exception:
                    log.exception("Erro ao inicializar %s (paralelo)", nome)
    else:
        for nome in nomes_sanitizados:
            mf = _criar_uma(nome)
            if mf:
                facades[nome] = mf

    bundle = FacadeBundle(facades)
    # bind convenience references
    bundle._factory_config = {"criar_collections_chroma": criar_collections_chroma}
    bundle.get_or_create  # method present
    return bundle


if __name__ == "__main__":
    import pprint
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("facade_factory_cli")
    sistema = None
    try:
        if SistemaMemoriaHibrido:
            sistema = SistemaMemoriaHibrido(None)
    except:
        pass
    fac = inicializar_facades_memoria(sistema_memoria=sistema, config=None, logger=logger)
    pprint.pprint(sorted(list(fac.keys())))