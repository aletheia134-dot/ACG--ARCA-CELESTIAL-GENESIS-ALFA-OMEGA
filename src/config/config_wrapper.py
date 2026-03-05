# src/config/config_wrapper.py — CRIADO
"""
ConfigWrapper — wrapper tolerante para ConfigParser / RawConfigParser / dict.
O CoracaoOrquestrador importa este arquivo em:
    from ..config.config_wrapper import ConfigWrapper
"""
from __future__ import annotations
from typing import Any, Dict, Optional


class ConfigWrapper:
    """
    Wrapper que aceita:
      - configparser.ConfigParser / RawConfigParser
      - dict aninhado  {secao: {chave: valor}}
      - None (retorna sempre fallback)
    """

    def __init__(self, source: Any = None):
        self._data: Dict[str, Dict[str, Any]] = {}
        if source is None:
            return
        # Se for ConfigParser / RawConfigParser
        if hasattr(source, "sections"):
            for sec in source.sections():
                self._data[sec.upper()] = {}
                for k, v in source.items(sec):
                    self._data[sec.upper()][k.upper()] = v
        # Se for dict
        elif isinstance(source, dict):
            for sec, opts in source.items():
                s = str(sec).upper()
                self._data[s] = {}
                if isinstance(opts, dict):
                    for k, v in opts.items():
                        self._data[s][str(k).upper()] = v
        # Se for outro ConfigWrapper
        elif isinstance(source, ConfigWrapper):
            self._data = {k: dict(v) for k, v in source._data.items()}

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        if section is None or key is None:
            return fallback
        sec = self._data.get(str(section).upper())
        if sec is None:
            return fallback
        return sec.get(str(key).upper(), fallback)

    def has_option(self, section: str, key: str) -> bool:
        sec = self._data.get(str(section).upper(), {})
        return str(key).upper() in sec

    def sections(self):
        return list(self._data.keys())

    def as_dict(self) -> Dict[str, Dict[str, Any]]:
        return {k: dict(v) for k, v in self._data.items()}

    def __repr__(self) -> str:  # pragma: no cover
        return f"ConfigWrapper(sections={list(self._data.keys())})"

