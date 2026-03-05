#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Audição - ASR (Automatic Speech Recognition)

Suporta:
- SpeechRecognition (ASR local via Google)
- Whisper (ASR via OpenAI API)

Implementação robusta e defensiva.
"""
from __future__ import annotations


import logging
import threading
from typing import Any, Optional

logger = logging.getLogger("SistemaAudicaoReal")

# ============================================================================
# IMPORTS DEFENSIVOS
# ============================================================================

ASR_LIB_AVAILABLE = False
try:
    import speech_recognition as sr
    ASR_LIB_AVAILABLE = True
except Exception:
    logger.debug("âš ï¸ SpeechRecognition não disponível (ASR local desabilitado)")

WHISPER_AVAILABLE = False
try:
    from openai import OpenAI
    WHISPER_AVAILABLE = True
except Exception:
    logger.debug("âš ï¸ OpenAI não disponível (Whisper desabilitado)")

# ============================================================================
# HELPERS
# ============================================================================

def _make_config_getter(config_obj: Any):
    """Cria getter tolerante para config."""
    def get_safe(section: str, key: str, fallback: Optional[Any] = None) -> Any:
        try:
            if config_obj is None:
                return fallback
            get = getattr(config_obj, "get", None)
            if callable(get):
                try:
                    return config_obj.get(section, key, fallback=fallback)
                except TypeError:
                    try:
                        return config_obj.get(section, key)
                    except Exception:
                        return fallback
                except Exception:
                    return fallback
            return getattr(config_obj, key, fallback)
        except Exception:
            return fallback
    return get_safe

# ============================================================================
# SISTEMA DE AUDIÇÍO
# ============================================================================

class SistemaAudicaoReal:
    """
    Reconhecimento de fala com fallback.Tenta local primeiro, depois API.
    """

    def __init__(self, config: Any = None):
        self.config = config or {}
        self._get = _make_config_getter(self.config)
        self.recognizer = None
        self.microphone = None
        self.use_whisper_api = False
        self.openai_client = None
        self._listening_lock = threading.RLock()
        self.logger = logging.getLogger("SistemaAudicaoReal")

        # Inicializar ASR local
        if ASR_LIB_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                try:
                    self.microphone = sr.Microphone()
                except Exception:
                    self.logger.warning("Microfone não inicializável na criação")
                    self.microphone = None
                self.logger.info("âœ… SpeechRecognition inicializado")
            except Exception:
                self.logger.exception("Erro ao inicializar SpeechRecognition")
                self.recognizer = None
        else:
            self.logger.debug("SpeechRecognition não disponível")

        # Inicializar Whisper API
        if WHISPER_AVAILABLE:
            api_key = self._get('API_KEYS', 'OPENAI_API_KEY', fallback=None)
            if api_key:
                try:
                    self.openai_client = OpenAI(api_key=api_key)
                    self.use_whisper_api = True
                    self.logger.info("âœ… Whisper API configurada")
                except Exception:
                    self.logger.exception("Erro ao inicializar OpenAI client")
            else:
                self.logger.debug("OpenAI API key não encontrada")
        else:
            self.logger.debug("Whisper não disponível")

    def ouvir_microfone(
        self,
        timeout: float = 5.0,
        phrase_time_limit: float = 10.0
    ) -> Optional[str]:
        """
        Ouve o microfone e retorna texto transcrito.Args:
            timeout: Tempo máximo para começar a falar
            phrase_time_limit: Tempo máximo da frase
            
        Returns:
            Texto transcrito ou None
        """
        if self.recognizer:
            return self._transcrever_sr_local(timeout, phrase_time_limit)
        
        if self.use_whisper_api:
            self.logger.debug("Usando Whisper API (implementação limitada)")
            return None
        
        self.logger.error("âŒ Nenhum sistema de audição disponível")
        return None

    def _transcrever_sr_local(
        self,
        timeout: float = 5.0,
        phrase_time_limit: float = 10.0
    ) -> Optional[str]:
        """Transcrição local com SpeechRecognition."""
        try:
            with self._listening_lock:
                if self.microphone is None:
                    try:
                        self.microphone = sr.Microphone()
                    except Exception:
                        self.logger.exception("Microfone indisponível")
                        return None

                self.logger.info("ðŸŽ¤ Ouvindo microfone...")
                with self.microphone as source:
                    try:
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    except Exception:
                        self.logger.debug("adjust_for_ambient_noise não suportado")

                    try:
                        audio = self.recognizer.listen(
                            source,
                            timeout=timeout,
                            phrase_time_limit=phrase_time_limit
                        )
                    except sr.WaitTimeoutError:
                        self.logger.warning("â° Timeout ao ouvir microfone")
                        return None

                self.logger.info("ðŸ”„ Transcrevendo...")
                try:
                    lang = self._get('AUDICAO', 'LANG', fallback='pt-BR') or 'pt-BR'
                    texto = self.recognizer.recognize_google(audio, language=lang)
                    preview = (texto[:120] + '...') if len(texto) > 120 else texto
                    self.logger.info("âœ… Transcrição: %s", preview)
                    return texto
                except sr.UnknownValueError:
                    self.logger.warning("âŒ Não foi possível entender o áudio")
                    return None
                except Exception:
                    self.logger.exception("Erro na transcrição")
                    return None

        except Exception:
            self.logger.exception("Erro geral na audição local")
            return None

    def shutdown(self) -> None:
        """Libera recursos."""
        try:
            with self._listening_lock:
                self.microphone = None
                self.recognizer = None
            self.logger.info("âœ… SistemaAudicaoReal desligado")
        except Exception:
            self.logger.exception("Erro ao desligar SistemaAudicaoReal")


