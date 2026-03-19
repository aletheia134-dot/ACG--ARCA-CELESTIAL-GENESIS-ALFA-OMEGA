from __future__ import annotations
"""
config_wrapper.py  — wrapper canônico e unificado para configurações ARCA.

Aceita como fonte:
  - configparser.ConfigParser / RawConfigParser
  - dict aninhado  {secao: {chave: valor}}
  - outro ConfigWrapper
  - None  (tudo retorna fallback)

Métodos disponíveis (usados em vários módulos):
  get / getint / getfloat / getboolean
  has_section / has_option
  set / add_section
  sections / options
  as_dict
"""
import configparser
from typing import Any, Dict, List, Optional


class ConfigWrapper:
    """
    Wrapper unificado — contém TODOS os métodos que qualquer módulo do projeto
    pode precisar, independente de qual arquivo criou a instância.
    """

    def __init__(self, source: Any = None):
        self._data: Dict[str, Dict[str, Any]] = {}
        if source is None:
            return
        # ConfigParser / RawConfigParser
        # outro ConfigWrapper (verificar ANTES de configparser para evitar conflito)
        if hasattr(source, "_data") and isinstance(source._data, dict):
            self._data = {k: dict(v) for k, v in source._data.items()}
        # ConfigParser / RawConfigParser (tem .items(section) com 2 colunas)
        elif hasattr(source, "sections") and callable(source.sections) and hasattr(source, "items"):
            for sec in source.sections():
                self._data[sec.upper()] = {}
                for k, v in source.items(sec):
                    self._data[sec.upper()][k.upper()] = v
        # dict aninhado
        elif isinstance(source, dict):
            for sec, opts in source.items():
                s = str(sec).upper()
                self._data[s] = {}
                if isinstance(opts, dict):
                    for k, v in opts.items():
                        self._data[s][str(k).upper()] = v

    # ── Leitura ──────────────────────────────────────────────────────────────

    def get(self, section: str, key: str = None, fallback: Any = None) -> Any:
        """Compatível com ConfigParser (section, key, fallback) e uso legado (key, default)."""
        if section is None:
            return fallback
        # Se key é None: chamado como get(section) → retorna dict da seção (compat legado)
        if key is None:
            sec = self._data.get(str(section).upper())
            return dict(sec) if sec else {}
        # Se key é um dict/None e não string: chamado como get(section, default) 2-args
        # Ex: config.get("MINHA_CHAVE", "/caminho/default")
        if not isinstance(key, str):
            # Tratar como: get(chave_plana, fallback_value)
            # Buscar em todas as seções
            fallback = key
            chave = str(section).upper()
            for sec_data in self._data.values():
                if chave in sec_data:
                    return sec_data[chave]
            return fallback
        sec = self._data.get(str(section).upper())
        if sec is None:
            # Seção não existe → chamada 2-args estilo dict: get(chave, default)
            # Ex: config.get("auth_secret", "change-this-secret")
            # Buscar a chave em TODAS as seções
            chave = str(section).upper()
            for sec_data in self._data.values():
                if chave in sec_data:
                    return sec_data[chave]
            # Não encontrou → retornar fallback (terceiro argumento)
            return fallback
        return sec.get(str(key).upper(), fallback)

    def items(self, section: str = None):
        """Compatível com ConfigParser.items(section) → lista de (key, value)."""
        if section is None:
            return list(self._data.items())
        sec = self._data.get(str(section).upper(), {})
        return list(sec.items())

    def section_dict(self, section: str) -> dict:
        """Retorna dict completo de uma seção."""
        return dict(self._data.get(str(section).upper(), {}))

    def getint(self, section: str, key: str, fallback: int = 0) -> int:
        v = self.get(section, key, fallback)
        try:
            return int(v)
        except (TypeError, ValueError):
            return fallback

    def getfloat(self, section: str, key: str, fallback: float = 0.0) -> float:
        v = self.get(section, key, fallback)
        try:
            return float(v)
        except (TypeError, ValueError):
            return fallback

    def getboolean(self, section: str, key: str, fallback: bool = False) -> bool:
        v = self.get(section, key, None)
        if v is None:
            return fallback
        if isinstance(v, bool):
            return v
        return str(v).strip().lower() in ("1", "true", "yes", "on", "sim")

    # ── Verificação ──────────────────────────────────────────────────────────

    def has_section(self, section: str) -> bool:
        return str(section).upper() in self._data

    def has_option(self, section: str, key: str) -> bool:
        sec = self._data.get(str(section).upper(), {})
        return str(key).upper() in sec

    def sections(self) -> List[str]:
        return list(self._data.keys())

    def options(self, section: str) -> List[str]:
        sec = self._data.get(str(section).upper(), {})
        return list(sec.keys())

    # ── Escrita ──────────────────────────────────────────────────────────────

    def set(self, section: str, key: str, value: Any) -> None:
        s = str(section).upper()
        if s not in self._data:
            self._data[s] = {}
        self._data[s][str(key).upper()] = value

    def add_section(self, section: str) -> None:
        s = str(section).upper()
        if s not in self._data:
            self._data[s] = {}

    # ── Utilitário ───────────────────────────────────────────────────────────

    def as_dict(self) -> Dict[str, Dict[str, Any]]:
        return {k: dict(v) for k, v in self._data.items()}

    def __repr__(self) -> str:
        return f"ConfigWrapper(sections={list(self._data.keys())})"


# ── Função auxiliar para carregar config.ini ─────────────────────────────────

def load_config_from_ini(ini_path: Optional[str] = None) -> "ConfigWrapper":
    """Carrega um arquivo config.ini e retorna ConfigWrapper."""
    cp = configparser.ConfigParser()
    if ini_path:
        cp.read(ini_path, encoding="utf-8")
    return ConfigWrapper(cp)


# Alias de compatibilidade — alguns módulos importam 'Config'
Config = ConfigWrapper
