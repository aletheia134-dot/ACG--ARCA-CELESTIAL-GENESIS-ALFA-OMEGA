#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Sistema de Voz - TTS (Text-to-Speech)

Suporta:
- pyttsx3 (TTS local)
- ElevenLabs (API)

Implementao robusta e defensiva.
"""

import logging
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger("SistemaVozReal")

# ============================================================================
# IMPORTS DEFENSIVOS
# ============================================================================

TTS_LIB_AVAILABLE = False
try:
    import pyttsx3
    TTS_LIB_AVAILABLE = True
except Exception:
    logger.debug("[AVISO] pyttsx3 no disponível (voz local desabilitada)")

ELEVEN_AVAILABLE = False
try:
    from elevenlabs import generate, play
    ELEVEN_AVAILABLE = True
except Exception:
    logger.debug("[AVISO] ElevenLabs no disponível (API desabilitada)")

# ============================================================================
# HELPERS
# ============================================================================

def _make_config_getter(config_obj: Any):
    """Cria getter tolerante para config.Suporta ConfigParser, dicts aninhados, objetos com get(...) e atributos.Sempre retorna fallback em caso de problema.
    """
    import configparser
    def get_safe(section: str, key: str, fallback: Optional[Any] = None) -> Any:
        try:
            if config_obj is None:
                return fallback

            # Caso seja um ConfigParser
            if isinstance(config_obj, configparser.ConfigParser):
                try:
                    # ConfigParser.get supports fallback in Python 3.8+
                    return config_obj.get(section, key, fallback=fallback)
                except TypeError:
                    # older signature
                    try:
                        return config_obj.get(section, key)
                    except Exception:
                        return fallback
                except Exception:
                    return fallback

            # Caso seja um dict ou mapping (inclui dict-like)
            try:
                if isinstance(config_obj, dict):
                    sec = config_obj.get(section)
                    if isinstance(sec, dict):
                        return sec.get(key, fallback)
                    # tentar chave combinada "SECTION.KEY"
                    combined = f"{section}.{key}"
                    if combined in config_obj:
                        return config_obj.get(combined, fallback)
                    # tentar chave simples key no dict (caso config plana)
                    if key in config_obj:
                        return config_obj.get(key, fallback)
            except Exception:
                # se falhar, continuar para heursticas abaixo
                pass

            # Objeto com método get (assinaturas variadas)
            get = getattr(config_obj, "get", None)
            if callable(get):
                try:
                    # tentar como ConfigParser: (section, key, fallback=...)
                    return get(section, key, fallback=fallback)
                except TypeError:
                    # talvez seja get(section, key)
                    try:
                        return get(section, key)
                    except TypeError:
                        # talvez seja get("section.key")
                        try:
                            return get(f"{section}.{key}")
                        except Exception:
                            return fallback
                    except Exception:
                        return fallback
                except Exception:
                    return fallback

            # Acesso por atributo: config_obj.SECTION -> dict-like
            attr = getattr(config_obj, section, None)
            if isinstance(attr, dict):
                return attr.get(key, fallback)
            # No conseguiu: retornar fallback
            return fallback
        except Exception as e:
            logger.debug("config getter falhou para (%s,%s): %s", section, key, e)
            return fallback
    return get_safe

def _safe_int(value: Any, default: int = 200, logger: Optional[logging.Logger] = None) -> int:
    if logger is None:
        logger = logger or logging.getLogger("SistemaVozReal")
    try:
        if value is None:
            return default
        # Se for string e contiver vrgula, substituir por ponto antes de int (mais tolerante)
        if isinstance(value, str):
            # detectar casos bvios de m-formatao (p.ex.o nome da chave foi retornado)
            if value.strip().upper() == value.strip() and not any(ch.isdigit() for ch in value):
                logger.warning("Valor de configuração possivelmente invlido para inteiro: %r", value)
            value = value.strip()
        return int(float(value))
    except (ValueError, TypeError) as e:
        logger.warning("Converso para int falhou para %r: %s.Usando valor default %d", value, e, default)
        return default

def _safe_float(value: Any, default: float = 0.9, logger: Optional[logging.Logger] = None) -> float:
    if logger is None:
        logger = logger or logging.getLogger("SistemaVozReal")
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.strip().replace(",", ".")
        val = float(value)
        # limitar entre 0.0 e 1.0
        if val < 0.0:
            return 0.0
        if val > 1.0:
            return 1.0
        return val
    except (ValueError, TypeError) as e:
        logger.warning("Converso para float falhou para %r: %s.Usando valor default %s", value, e, default)
        return default

# ============================================================================
# SISTEMA DE VOZ
# ============================================================================

class SistemaVozReal:
    """
    Sntese de voz com fallback.Tenta local primeiro, depois API.
    """

    def __init__(self, config: Any = None):
        self.config = config or {}
        self._get = _make_config_getter(self.config)
        self.engine = None
        self.use_api = False
        self.eleven_api_key: Optional[str] = None
        self._lock = threading.RLock()
        self.logger = logging.getLogger("SistemaVozReal")

        # Tentar inicializar local TTS
        if TTS_LIB_AVAILABLE:
            try:
                self.engine = pyttsx3.init()
                # leitura defensiva e logging do valor cru para diagnstico
                rate_raw = self._get('VOZ', 'VELOCIDADE', fallback=None)
                self.logger.debug("DEBUG VOZ/VELOCIDADE raw value: %r (tipo: %s)", rate_raw, type(rate_raw).__name__)
                rate = _safe_int(rate_raw, default=200, logger=self.logger)

                volume_raw = self._get('VOZ', 'VOLUME', fallback=None)
                self.logger.debug("DEBUG VOZ/VOLUME raw value: %r (tipo: %s)", volume_raw, type(volume_raw).__name__)
                volume = _safe_float(volume_raw, default=0.9, logger=self.logger)

                try:
                    self.engine.setProperty('rate', rate)
                    self.engine.setProperty('volume', volume)
                except Exception:
                    self.logger.debug("No foi possível aplicar propriedades ação pyttsx3")
                self.logger.info("[OK] pyttsx3 inicializado (rate=%s, volume=%s)", rate, volume)
            except Exception:
                self.logger.exception("Erro ao inicializar pyttsx3")
                self.engine = None
        else:
            self.logger.debug("pyttsx3 no disponível")

        # Tentar inicializar API
        if ELEVEN_AVAILABLE:
            api_key = self._get('API_KEYS', 'ELEVENLABS_API_KEY', fallback=None)
            if api_key:
                self.eleven_api_key = api_key
                self.use_api = True
                self.logger.info("[OK] ElevenLabs API configurada")
            else:
                self.logger.debug("ElevenLabs API key no encontrada (valor lido: %r)", api_key)
        else:
            self.logger.debug("ElevenLabs no disponível")

    def falar(self, texto: str, voz_alma: Optional[str] = None, block: bool = True) -> None:
        """
        Fala o texto usando sistema configurado.Args:
            texto: Texto para falar
            voz_alma: ID/nome da voz
            block: Se True, aguarda; False dispara em background
        """
        if not texto:
            return

        preview = (texto[:200] + "...") if len(texto) > 200 else texto
        self.logger.info("Verbalizando: %s", preview)

        with self._lock:
            # Tentar API
            if self.use_api and ELEVEN_AVAILABLE and self.eleven_api_key:
                try:
                    audio = generate(
                        text=texto,
                        voice=voz_alma or "Rachel",
                        api_key=self.eleven_api_key
                    )
                    play(audio)
                    return
                except Exception:
                    self.logger.exception("Erro na API ElevenLabs; tentando fallback local")

            # Fallback local
            if self.engine:
                try:
                    self.engine.say(texto)
                    if block:
                        self.engine.runAndWait()
                    self.logger.debug("[OK] Voz local reproduzida")
                except Exception:
                    self.logger.exception("Erro ao reproduzir voz local")
            else:
                self.logger.error("[ERRO] Nenhum sistema de voz disponível")

    def listar_vozes(self) -> Dict[int, str]:
        """Lista vozes locais disponíveis."""
        voices_map = {}
        if not self.engine:
            return voices_map
        try:
            vozes = self.engine.getProperty('voices')
            for i, v in enumerate(vozes):
                name = getattr(v, "name", str(v))
                voices_map[i] = name
        except Exception:
            self.logger.exception("Erro ao listar vozes")
        return voices_map

    def shutdown(self) -> None:
        """Libera recursos."""
        try:
            if self.engine:
                try:
                    self.engine.stop()
                except Exception:
                    pass
            self.logger.info("[OK] SistemaVozReal desligado")
        except Exception:
            self.logger.exception("Erro ao desligar SistemaVozReal")


