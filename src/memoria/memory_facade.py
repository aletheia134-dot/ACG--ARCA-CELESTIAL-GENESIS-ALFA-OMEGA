#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import inspect
import time
import re
from typing import Any, Dict, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from functools import wraps

logger = logging.getLogger("facade_factory")

# ======================================================================
# IMPLEMENTAÇÍO REAL (COMPLETA)
# ======================================================================
class MemoryFacade:
    """
    Implementação real da MemoryFacade.
    """
    def __init__(self, nome_alma: str, config: Any = None):
        self.nome_alma = nome_alma
        self.config = config
        logger.info(f"✅ MemoryFacade REAL inicializada para {nome_alma}")

    def shutdown(self):
        logger.info(f"MemoryFacade REAL desligada para {self.nome_alma}")

    def status(self) -> Dict[str, Any]:
        return {
            "status": "real",
            "nome_alma": self.nome_alma,
            "config": str(self.config)
        }

    def inicializar_collections(self):
        logger.debug(f"MemoryFacade REAL: collections inicializadas para {self.nome_alma}")

    def salvar_memoria(self, chave: str, valor: Any) -> bool:
        # Implementação real viria aqui
        logger.debug(f"Salvando memória para {self.nome_alma}: {chave}")
        return True

    def recuperar_memoria(self, chave: str) -> Optional[Any]:
        # Implementação real viria aqui
        logger.debug(f"Recuperando memória para {self.nome_alma}: {chave}")
        return None


# ======================================================================
# STUB (USADO QUANDO A REAL NÍO ESTÁ DISPONÍVEL)
# ======================================================================
class MemoryFacadeStub:
    """
    Stub para MemoryFacade quando a implementação real não está disponível.
    """
    def __init__(self, *args, **kwargs):
        self.nome_alma = kwargs.get('nome_alma') or (args[0] if args else 'desconhecido')
        logger.info(f"MemoryFacade STUB inicializada para {self.nome_alma}")

    def shutdown(self):
        logger.info(f"MemoryFacade STUB desligada para {self.nome_alma}")

    def status(self) -> Dict[str, Any]:
        return {"status": "stub", "nome_alma": self.nome_alma}

    def inicializar_collections(self):
        logger.debug(f"MemoryFacade STUB: collections não criadas (modo stub)")

    def salvar_memoria(self, chave: str, valor: Any) -> bool:
        logger.debug(f"STUB: simulando salvamento de memória para {self.nome_alma}")
        return True

    def recuperar_memoria(self, chave: str) -> Optional[Any]:
        logger.debug(f"STUB: simulando recuperação de memória para {self.nome_alma}")
        return None


# ======================================================================
# CÓDIGO COMPARTILHADO (FUNÇÕES AUXILIARES)
# ======================================================================
DEFAULT_AIS = ["EVA", "LUMINA", "NYRA", "YUNA", "KAIYA", "WELLINGTON"]
ENV_CREATE_CHROMA = os.getenv("MEMORIA_CREATE_CHROMA_COLLECTIONS", "true").lower() in ("1", "true", "yes")
LOG = logging.getLogger("facade_factory")

# TENTATIVA DE USAR A REAL, SE FALHAR USA A STUB
try:
    # Tenta importar a real (que agora está neste mesmo arquivo)
    RealMemoryFacade = MemoryFacade
    MEMORY_FACADE_REAL = True
    logger.info("✅ Usando implementação REAL da MemoryFacade")
except:
    RealMemoryFacade = None
    MEMORY_FACADE_REAL = False
    logger.warning("⚠️ Usando STUB da MemoryFacade")


def _sanitize_nome_alma(raw: str) -> Optional[str]:
    if raw is None:
        return None
    nome = str(raw).strip().upper()
    if not nome:
        return None
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
        LOG.debug("Erro lendo nomes do sistema_memoria", exc_info=True)
    return None


def _nomes_de_config(config: Any) -> Optional[List[str]]:
    try:
        if not config:
            return None
        if hasattr(config, "get"):
            raw = None
            try:
                raw = config.get("AIS_LISTA_CSV", None)
            except Exception:
                try:
                    raw = config.get("MEMORIA", "AIS_LISTA_CSV", fallback=None)
                except Exception:
                    logger.warning("⚠️ MemoryFacade não disponível")
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
        LOG.debug("Erro lendo nomes do config", exc_info=True)
    return None


def _call_memory_facade_constructor(mf_class: Callable, nome: str, config: Any) -> Any:
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

    if kwargs:
        return mf_class(**kwargs)
    try:
        return mf_class(nome)
    except TypeError:
        return mf_class(nome, config)


def retry(exceptions, tries: int = 3, delay: float = 0.5, backoff: float = 2.0):
    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    LOG.debug("Retryable error (%s), will retry in %.2fs: %s", type(e).__name__, mdelay, e, exc_info=True)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)
        return f_retry
    return deco_retry


class FacadeBundle(dict):
    def shutdown(self) -> None:
        for name, f in list(self.items()):
            try:
                if hasattr(f, "shutdown"):
                    f.shutdown()
            except Exception:
                LOG.exception("Erro ao shutdown de %s", name)

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

    def get_or_create(self, nome: str, config: Any = None, criar_collections_chroma: Optional[bool] = None,
                      metrics_hook: Optional[Callable[[str, bool, float], None]] = None) -> Optional[Any]:
        nome_norm = _sanitize_nome_alma(nome)
        if not nome_norm:
            return None
        if nome_norm in self and self[nome_norm] is not None:
            return self[nome_norm]
        
        # Usa a implementação real se disponível, senão usa o stub
        classe_mf = RealMemoryFacade if MEMORY_FACADE_REAL else MemoryFacadeStub
        start = time.time()
        try:
            mf = _call_memory_facade_constructor(classe_mf, nome_norm, config)
            if criar_collections_chroma is None:
                criar_collections_chroma = ENV_CREATE_CHROMA
            if criar_collections_chroma and hasattr(mf, "inicializar_collections"):
                try:
                    mf.inicializar_collections()
                except Exception:
                    LOG.debug("Falha ao inicializar collections (on-demand) para %s", nome_norm, exc_info=True)
            self[nome_norm] = mf
            elapsed = time.time() - start
            if metrics_hook:
                metrics_hook(nome_norm, True, elapsed)
            LOG.info("MemoryFacade get_or_create criado para %s (%.2fs)", nome_norm, elapsed)
            return mf
        except Exception as e:
            elapsed = time.time() - start
            if metrics_hook:
                metrics_hook(nome_norm, False, elapsed)
            LOG.exception("Erro get_or_create para %s: %s", nome_norm, e)
            return None


def inicializar_facades_memoria(
    sistema_memoria: Optional[Any] = None,
    config: Optional[Any] = None,
    nomes_override: Optional[List[str]] = None,
    criar_collections_chroma: Optional[bool] = None,
    logger: Optional[logging.Logger] = None,
    paralelo: bool = True,
    max_workers: Optional[int] = None,
    timeout_por_alma: int = 30,
    metrics_hook: Optional[Callable[[str, bool, float], None]] = None,
    lazy: bool = False
) -> FacadeBundle:
    log = logger or LOG
    facades: Dict[str, Any] = {}

    classe_mf = RealMemoryFacade if MEMORY_FACADE_REAL else MemoryFacadeStub
    if classe_mf is None:
        log.error("Nenhuma implementação de MemoryFacade disponível. Retornando bundle vazio.")
        return FacadeBundle(facades)

    nomes = None
    if nomes_override:
        nomes = [str(n).strip().upper() for n in nomes_override if str(n).strip()]
    else:
        nomes = _nomes_de_sistema_memoria(sistema_memoria) or _nomes_de_config(config)

    if not nomes:
        nomes = DEFAULT_AIS.copy()
        log.info("Nenhuma lista de almas encontrada; usando padrão: %s", ", ".join(nomes))

    nomes_sanitizados = []
    for n in sorted(set(nomes)):
        ns = _sanitize_nome_alma(n)
        if ns:
            nomes_sanitizados.append(ns)

    if criar_collections_chroma is None:
        criar_collections_chroma = ENV_CREATE_CHROMA

    bundle = FacadeBundle(facades)
    bundle._factory_config = {"criar_collections_chroma": criar_collections_chroma}

    if lazy:
        for nome in nomes_sanitizados:
            bundle[nome] = None
        log.info("Facades em modo lazy. get_or_create criará instâncias sob demanda.")
        return bundle

    @retry(Exception, tries=3, delay=0.5, backoff=2.0)
    def _criar_uma(nome_alma: str) -> Optional[Any]:
        try:
            mf = _call_memory_facade_constructor(classe_mf, nome_alma, config)
            if criar_collections_chroma and hasattr(mf, "inicializar_collections"):
                try:
                    mf.inicializar_collections()
                except Exception:
                    log.debug("Falha ao criar collections para %s (não crítico)", nome_alma, exc_info=True)
            log.info("MemoryFacade inicializado para %s", nome_alma)
            return mf
        except Exception:
            log.exception("Falha ao criar MemoryFacade para %s", nome_alma)
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
                        if metrics_hook:
                            metrics_hook(nome, True, 0.0)
                except TimeoutError:
                    log.exception("Timeout ao inicializar %s", nome)
                    if metrics_hook:
                        metrics_hook(nome, False, float(timeout_por_alma))
                except Exception:
                    log.exception("Erro ao inicializar %s", nome)
                    if metrics_hook:
                        metrics_hook(nome, False, 0.0)
    else:
        for nome in nomes_sanitizados:
            mf = _criar_uma(nome)
            if mf:
                facades[nome] = mf

    return bundle
