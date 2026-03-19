#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilities for robust config access supporting both configparser-like objects
and plain dictionaries (nested dicts).
"""
from typing import Any, Optional

def cfg_get(cfg: Any, section: str, option: str = None, fallback: Any = None) -> Any:
    """
    Safe accessor for configurations.
    - If cfg implements config.get(section, option, fallback=...), it will be used.
    - If cfg is a dict (possibly nested), attempts to read cfg[section][option] or cfg.get(section).get(option).
    - On any failure returns fallback.
    """
    if cfg is None:
        return fallback
    # Prefer configparser-like get with fallback kwarg
    try:
        # Many config libs implement get(section, option, fallback=...)
        return cfg.get(section, option, fallback=fallback)
    except TypeError:
        # Signature mismatch (e.g., dict.get doesn't accept fallback kwarg)
        try:
            # If cfg is mapping and section is a key returning a mapping
            if hasattr(cfg, "get"):
                sec = cfg.get(section)
                if isinstance(sec, dict):
                    return sec.get(option, fallback)
            # If cfg is a mapping with composite keys like "SECTION.OPTION"
            if isinstance(cfg, dict):
                composite = f"{section}.{option}"
                if composite in cfg:
                    return cfg[composite]
                tup = (section, option)
                if tup in cfg:
                    return cfg[tup]
            return fallback
        except Exception:
            return fallback
    except Exception:
        return fallback


def cfg_get_bool(cfg: Any, section: str, option: str = None, fallback: Optional[bool] = None) -> Optional[bool]:
    """Robust boolean getter. Supports configparser-like objects and plain dicts/strings."""
    try:
        # Prefer configparser-like
        return cfg.getboolean(section, option, fallback=fallback)
    except Exception:
        pass
    try:
        if option is None:
            v = cfg.get(section, fallback) if hasattr(cfg, "get") else cfg.get(section, fallback)
        else:
            # reuse cfg_get if available
            v = cfg_get(cfg, section, option, fallback=fallback)
        if v is None:
            return fallback
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        if s in ("1", "true", "yes", "y", "on"):
            return True
        if s in ("0", "false", "no", "n", "off"):
            return False
        # fallback to truthiness
        return bool(v)
    except Exception:
        return fallback

def cfg_get_int(cfg: Any, section: str, option: str = None, fallback: Optional[int] = None) -> Optional[int]:
    try:
        val = cfg.get(section, option, fallback=fallback)
        if val is None:
            return fallback
        return int(val)
    except Exception:
        try:
            v = cfg_get(cfg, section, option, fallback=fallback)
            if v is None:
                return fallback
            return int(v)
        except Exception:
            return fallback

def cfg_get_float(cfg: Any, section: str, option: str = None, fallback: Optional[float] = None) -> Optional[float]:
    try:
        val = cfg.get(section, option, fallback=fallback)
        if val is None:
            return fallback
        return float(val)
    except Exception:
        try:
            v = cfg_get(cfg, section, option, fallback=fallback)
            if v is None:
                return fallback
            return float(v)
        except Exception:
            return fallback
