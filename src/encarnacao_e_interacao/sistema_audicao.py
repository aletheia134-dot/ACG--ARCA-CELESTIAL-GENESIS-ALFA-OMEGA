#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Sistema de Audio - ASR (Automatic Speech Recognition)

Suporta:
- SpeechRecognition (ASR local via Google)
- Whisper (ASR via OpenAI API)

Implementao robusta e defensiva.
"""


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
    logger.debug("[AVISO] SpeechRecognition no disponível (ASR local desabilitado)")

WHISPER_AVAILABLE = False
try:
    from openai import OpenAI
    WHISPER_AVAILABLE = True
except Exception:
    logger.debug("[AVISO] OpenAI no disponível (Whisper desabilitado)")

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
# SISTEMA DE AUDIO
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
                    self.logger.warning("Microfone no inicializvel na criao")
                    self.microphone = None
                self.logger.info("[OK] SpeechRecognition inicializado")
            except Exception:
                self.logger.exception("Erro ao inicializar SpeechRecognition")
                self.recognizer = None
        else:
            self.logger.debug("SpeechRecognition no disponível")

        # Inicializar Whisper API
        if WHISPER_AVAILABLE:
            api_key = self._get('API_KEYS', 'OPENAI_API_KEY', fallback=None)
            if api_key:
                try:
                    self.openai_client = OpenAI(api_key=api_key)
                    self.use_whisper_api = True
                    self.logger.info("[OK] Whisper API configurada")
                except Exception:
                    self.logger.exception("Erro ao inicializar OpenAI client")
            else:
                self.logger.debug("OpenAI API key no encontrada")
        else:
            self.logger.debug("Whisper no disponível")

    def ouvir_microfone(
        self,
        timeout: float = 5.0,
        phrase_time_limit: float = 10.0
    ) -> Optional[str]:
        """
        Ouve o microfone e retorna texto transcrito.Args:
            timeout: Tempo máximo para comear a falar
            phrase_time_limit: Tempo máximo da frase
            
        Returns:
            Texto transcrito ou None
        """
        if self.recognizer:
            return self._transcrever_sr_local(timeout, phrase_time_limit)
        
        if self.use_whisper_api:
            return self._transcrever_whisper_api(timeout, phrase_time_limit)
        
        self.logger.error("[ERRO] Nenhum sistema de audio disponível")
        return None

    def _transcrever_whisper_api(
        self,
        timeout: float = 5.0,
        phrase_time_limit: float = 10.0
    ) -> Optional[str]:
        """Transcrição via OpenAI Whisper API — grava áudio real do microfone."""
        import tempfile
        import os

        # Tentar gravar via sounddevice
        audio_data = None
        sample_rate = 16000
        try:
            import sounddevice as sd
            import numpy as np
            self.logger.info("🎤 Gravando via sounddevice para Whisper...")
            frames = int(phrase_time_limit * sample_rate)
            audio_np = sd.rec(frames, samplerate=sample_rate, channels=1, dtype="int16")
            sd.wait()
            audio_data = audio_np.tobytes()
        except Exception as e_sd:
            self.logger.warning("sounddevice falhou (%s); tentando pyaudio...", e_sd)
            try:
                import pyaudio
                pa = pyaudio.PyAudio()
                stream = pa.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=sample_rate,
                    input=True,
                    frames_per_buffer=1024
                )
                chunks = []
                total_frames = int(sample_rate * phrase_time_limit / 1024)
                for _ in range(total_frames):
                    chunks.append(stream.read(1024, exception_on_overflow=False))
                stream.stop_stream()
                stream.close()
                pa.terminate()
                audio_data = b"".join(chunks)
            except Exception as e_pa:
                self.logger.error("pyaudio também falhou: %s", e_pa)
                return None

        if not audio_data:
            return None

        # Salvar como WAV temporário e enviar ao Whisper
        try:
            import wave
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # int16 = 2 bytes
                wf.setframerate(sample_rate)
                wf.writeframes(audio_data)

            with open(tmp_path, "rb") as audio_file:
                lang = self._get("AUDICAO", "LANG", fallback="pt") or "pt"
                result = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=lang[:2],  # Whisper aceita código de 2 letras
                )
            texto = result.text.strip() if hasattr(result, "text") else str(result).strip()
            self.logger.info("[OK] Whisper transcreveu: %s", texto[:120])
            return texto if texto else None
        except Exception as e:
            self.logger.exception("Erro na transcrição Whisper: %s", e)
            return None
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def _transcrever_sr_local(
        self,
        timeout: float = 5.0,
        phrase_time_limit: float = 10.0
    ) -> Optional[str]:
        """Transcrio local com SpeechRecognition."""
        try:
            with self._listening_lock:
                if self.microphone is None:
                    try:
                        self.microphone = sr.Microphone()
                    except Exception:
                        self.logger.exception("Microfone indisponível")
                        return None

                self.logger.info(" Ouvindo microfone...")
                with self.microphone as source:
                    try:
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    except Exception:
                        self.logger.debug("adjust_for_ambient_noise no suportado")

                    try:
                        audio = self.recognizer.listen(
                            source,
                            timeout=timeout,
                            phrase_time_limit=phrase_time_limit
                        )
                    except sr.WaitTimeoutError:
                        self.logger.warning(" Timeout ação ouvir microfone")
                        return None

                self.logger.info(" Transcrevendo...")
                try:
                    lang = self._get('AUDICAO', 'LANG', fallback='pt-BR') or 'pt-BR'
                    texto = self.recognizer.recognize_google(audio, language=lang)
                    preview = (texto[:120] + '...') if len(texto) > 120 else texto
                    self.logger.info("[OK] Transcrio: %s", preview)
                    return texto
                except sr.UnknownValueError:
                    self.logger.warning("[ERRO] No foi possível entender o udio")
                    return None
                except Exception:
                    self.logger.exception("Erro na transcrio")
                    return None

        except Exception:
            self.logger.exception("Erro geral na audio local")
            return None

    def shutdown(self) -> None:
        """Libera recursos."""
        try:
            with self._listening_lock:
                self.microphone = None
                self.recognizer = None
            self.logger.info("[OK] SistemaAudicaoReal desligado")
        except Exception:
            self.logger.exception("Erro ao desligar SistemaAudicaoReal")


