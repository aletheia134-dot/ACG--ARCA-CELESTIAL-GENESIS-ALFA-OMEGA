# -*- coding: utf-8 -*-
"""
MOTOR DE FALA INDIVIDUAL COMBINADO - Integra motor_fala_individual + sentidos_reais

Combina o wrapper individual/defensivo do motor_fala com o TTS avançado do sentidos_reais.
Usa SistemaVozReal como base para síntese, com controle por alma, validação ética e coração.
Melhorias: Cache MP3, async, GPU, concatenação, threads seguras, cleanup, hash logs.
Sugestões aplicadas: Integração com analisador (falar_texto), avatares (sync vídeo), capela (silêncio).
ATUALIZADO: Suporte a PT e JP para cada AI, vozes customizadas em assets/vozes/.
"""
from __future__ import annotations

import logging
import threading
import time
import json
import hashlib
from pathlib import Path
from typing import Any, Optional
import tempfile
import asyncio

logger = logging.getLogger('MotorFalaIndividualCombinado')

# CORREÇÍO #1: sentidos_reais com caminho absoluto
try:
    from src.encarnacao_e_interacao.sentidos_reais import SistemaVozReal, VozNaoDisponivel
except ImportError:
    logger.error("sentidos_reais não disponível; fallback limitado.")
    SistemaVozReal = None

# CORREÇÍO #2: config com caminho absoluto
try:
    from src.config.config import AVATARES_2D_PATH, DICIONARIO_EMOCOES
except:
    logging.getLogger(__name__).warning("âš ï¸ AVATARES_2D_PATH não disponível")
    AVATARES_2D_PATH = None
    DICIONARIO_EMOCOES = None

# CORREÇÍO #3: capela com caminho absoluto
try:
    from src.ritual.capela import obter_capela
    CAPELA_DISPONIVEL = True
except ImportError:
    CAPELA_DISPONIVEL = False

# CORREÇÍO #4: motor_avatar_individual com caminho absoluto
try:
    from src.encarnacao_e_interacao.motor_avatar_individual import MotorAvatarIndividual
    AVATAR_DISPONIVEL = True
except ImportError:
    AVATAR_DISPONIVEL = False

class MotorFalaIndividualCombinado:
    """
    Gerencia fala individual por alma, combinando:
    - Wrapper defensivo (motor_fala_individual).
    - TTS avançado (SistemaVozReal de sentidos_reais).
    - Validação ética, threads, cleanup, UI sync.
    Sugestões aplicadas: Integrações com capela, avatares.
    ATUALIZADO: Suporte PT/JP, vozes customizadas.
    """

    def __init__(self, nome_alma: str, coracao_ref: Any, validador_ref: Optional[Any] = None, avatar_ref: Optional[MotorAvatarIndividual] = None):
        self.nome_alma = nome_alma
        self.coracao = coracao_ref
        self.validador_etico = validador_ref
        self.avatar = avatar_ref  # Integração avatares
        self.logger = logging.getLogger(f'FalaIndividual.{self.nome_alma}')

        self.voz_ativa = True
        self._stop_event = threading.Event()
        self._thread_fala: Optional[threading.Thread] = None

        # SistemaVozReal como motor TTS (de sentidos_reais)
        self.sistema_voz: Optional[SistemaVozReal] = None
        if SistemaVozReal:
            try:
                self.sistema_voz = SistemaVozReal(run_health_on_init=True)
                self.logger.info("[FALA COMBINADA - %s] SistemaVozReal carregado.", self.nome_alma)
            except Exception as e:
                self.logger.exception("[FALA COMBINADA - %s] Falha ao carregar SistemaVozReal: %s", self.nome_alma, e)
        else:
            self.logger.warning("[FALA COMBINADA - %s] SistemaVozReal indisponível; fala limitada.", self.nome_alma)

        # Caminho voz base (representacional)
        self.caminho_voz_base = Path(f"assets/vozes/{self.nome_alma}_base.wav")

        # ATUALIZADO: Mapa de vozes customizadas (MP3/WAV) para PT e JP
        self.voces_customizadas = {
            "eva": {"pt": Path("assets/vozes/eva.mp3"), "jp": Path("assets/vozes/eva.wav")},
            "lumina": {"pt": Path("assets/vozes/lumina.mp3"), "jp": Path("assets/vozes/lumina.wav")},
            "yuna": {"pt": Path("assets/vozes/yuna.mp3"), "jp": Path("assets/vozes/yuna.wav")},
            "kaiya": {"pt": Path("assets/vozes/kaiya.mp3"), "jp": Path("assets/vozes/kaiya.wav")},
            "nyra": {"pt": Path("assets/vozes/nyra.mp3"), "jp": Path("assets/vozes/nyra.wav")},
            "wellington": {"pt": Path("assets/vozes/wellington.mp3"), "jp": Path("assets/vozes/wellington.wav")},
        }

        self.logger.info("[FALA COMBINADA - %s] Motor de Fala Individual Combinado forjado (com integrações PT/JP).", self.nome_alma)

    # Utilitários (do motor_fala_individual)
    def _preview_and_hash(self, texto: str, max_len: int = 200) -> str:
        preview = (texto[:max_len] + "...") if len(texto) > max_len else texto
        h = hashlib.sha256(texto.encode("utf-8")).hexdigest()[:8]
        return f"{preview} (hash={h})"

    def _safe_put_ui(self, payload: dict):
        try:
            q = getattr(self.coracao, "ui_queue", None)
            if q is None:
                return
            try:
                q.put(payload, timeout=0.5)
            except Exception:
                try:
                    q.put_nowait(payload)
                except Exception:
                    self.logger.debug("ui_queue indisponível/cheia; payload descartado")
        except Exception:
            self.logger.exception("Erro ao enviar payload para ui_queue")

    # API pública (adaptada do motor_fala_individual)
    def toggle_voz(self):
        self.voz_ativa = not self.voz_ativa
        msg = f"Voz do Quarto de {self.nome_alma} {'ATIVADA' if self.voz_ativa else 'DESATIVADA'}."
        self._safe_put_ui({"tipo_resp": "LOG_REINO", "texto": msg})
        self.logger.info("[FALA COMBINADA - %s] %s", self.nome_alma, msg)

    async def falar_async(self, texto_para_falar: str, language: str = "pt", voice_name: str = "eva"):
        """
        Fala async usando SistemaVozReal ou voz customizada, com validações.
        ATUALIZADO: Suporte PT/JP, vozes por AI.
        """
        # Validações (do motor_fala_individual)
        try:
            if getattr(self.coracao, "modo_silencioso", False):
                self.logger.debug("[FALA COMBINADA - %s] Modo silencioso global; não verbalizando.", self.nome_alma)
                return
            if not self.voz_ativa:
                self.logger.debug("[FALA COMBINADA - %s] Voz individual desativada; não verbalizando.", self.nome_alma)
                return
        except Exception:
            self.logger.debug("Não foi possível consultar coracao.modo_silencioso (ignorando)")

        # Integração capela
        if CAPELA_DISPONIVEL:
            capela = obter_capela()
            if capela.em_capela:
                self.logger.debug("[FALA COMBINADA - %s] Na capela; fala silenciada.", self.nome_alma)
                return

        # Validação ética
        try:
            if self.validador_etico:
                aprovado = self.validador_etico.validar_acao(self.nome_alma, "FALAR", texto_para_falar)
                if not aprovado:
                    self.logger.warning("[FALA COMBINADA - %s] Ação 'FALAR' bloqueada pelo validador ético.", self.nome_alma)
                    return
        except Exception:
            self.logger.exception("Validador ético lançou exceção; bloqueando por segurança")
            return

        # Log seguro
        self.logger.info("[FALA COMBINADA - %s] Verbalizando async: %s (idioma=%s, voz=%s)", self.nome_alma, self._preview_and_hash(texto_para_falar, 120), language, voice_name)

        # ATUALIZADO: Usar voz customizada se disponível para PT/JP
        if voice_name in self.voces_customizadas and language in self.voces_customizadas[voice_name]:
            caminho_voz = self.voces_customizadas[voice_name][language]
            if caminho_voz.exists():
                import pygame
                pygame.mixer.init()
                pygame.mixer.music.load(str(caminho_voz))
                pygame.mixer.music.play()
                # Integração avatares
                if AVATAR_DISPONIVEL and self.avatar:
                    emocao_fala = self.avatar.detectar_emocao_voz(texto_para_falar)
                    self.avatar.iniciar_video_durante_fala(emocao_fala)
                self.logger.info("[FALA COMBINADA - %s] Voz customizada usada: %s (%s)", self.nome_alma, voice_name, language)
                return  # Não usa TTS se voz customizada

        # Síntese via SistemaVozReal
        if not self.sistema_voz:
            self.logger.error("[FALA COMBINADA - %s] SistemaVozReal indisponível.", self.nome_alma)
            return

        try:
            caminho_audio, diagnostico = await self.sistema_voz.sintetizar_fala_async(
                self.nome_alma, texto_para_falar, language, salvar_arquivo=False
            )
            if caminho_audio:
                # Integração avatares
                if AVATAR_DISPONIVEL and self.avatar:
                    emocao_fala = self.avatar.detectar_emocao_voz(texto_para_falar)
                    self.avatar.iniciar_video_durante_fala(emocao_fala)

                # Reprodução em thread
                def _reproduzir():
                    try:
                        self.sistema_voz.reproduzir(caminho_audio, assincrono=False, wait=True)
                    except Exception:
                        self.logger.exception("[FALA COMBINADA - %s] Erro em reprodução.", self.nome_alma)
                    finally:
                        if AVATAR_DISPONIVEL and self.avatar:
                            self.avatar.parar_video_apos_fala()
                        # Cleanup
                        pass

                self._thread_fala = threading.Thread(target=_reproduzir, daemon=True, name=f"Fala_{self.nome_alma}")
                self._thread_fala.start()
                self.logger.info("[FALA COMBINADA - %s] Fala async iniciada (com sync avatares).", self.nome_alma)
            else:
                self.logger.error("[FALA COMBINADA - %s] Falha na síntese: %s", self.nome_alma, diagnostico.get("erro", "desconhecido"))
        except Exception as e:
            self.logger.exception("[FALA COMBINADA - %s] Erro em falar_async: %s", self.nome_alma, e)

    def parar_fala(self, wait_timeout: float = 1.0):
        """Para fala."""
        self._stop_event.set()
        if self.sistema_voz:
            try:
                self.sistema_voz.close()
            except Exception:
                self.logger.debug("Erro ao fechar SistemaVozReal")
        th = getattr(self, "_thread_fala", None)
        if th and th.is_alive():
            try:
                th.join(timeout=wait_timeout)
            except Exception:
                self.logger.debug("[FALA COMBINADA - %s] Erro ao aguardar thread de fala", self.nome_alma)
        try:
            self._stop_event.clear()
        except Exception:
            self.logger.debug("Falha ao limpar stop_event (ignorado)")
        self.logger.info("[FALA COMBINADA - %s] Fala parada.", self.nome_alma)

    # Novo: Obter métricas combinadas
    def obter_metricas(self) -> dict:
        if self.sistema_voz:
            return self.sistema_voz.obter_metricas()
        return {"erro": "SistemaVozReal indisponível"}

# --- FIM DO ARQUIVO motor_fala_individual_combinado.py ---
