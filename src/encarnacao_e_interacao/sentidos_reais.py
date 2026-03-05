# -*- coding: utf-8 -*-
"""
Sistema de Voz Real para ARCA Celestial
Integração com TTS e reprodução de áudio
"""
from __future__ import annotations
import logging
import asyncio
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import threading
import time

logger = logging.getLogger('SistemaVozReal')

class VozNaoDisponivel(Exception):
    pass

class SistemaVozReal:
    """Sistema de síntese e reprodução de voz"""
    
    def __init__(self, run_health_on_init: bool = True):
        self.logger = logger
        self._running = True
        self._lock = threading.Lock()
        
        # Verificar disponibilidade de TTS
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.tts_disponivel = True
            self.logger.info("pyttsx3 disponível para TTS")
        except ImportError:
            self.tts_disponivel = False
            self.logger.warning("pyttsx3 não instalado; TTS desabilitado")
        
        if run_health_on_init:
            self._health_check()
        
        self.logger.info("âœ… SistemaVozReal inicializado")
    
    def _health_check(self):
        """Verifica saúde do sistema"""
        self.logger.debug("Health check OK")
    
    async def sintetizar_fala_async(self, nome_alma: str, texto: str, language: str = "pt", salvar_arquivo: bool = False) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Sintetiza fala de forma assíncrona
        Retorna (caminho_audio, diagnostico)
        """
        diagnostico = {"erro": None, "metodo": "tts"}
        
        if not self.tts_disponivel:
            diagnostico["erro"] = "TTS não disponível"
            return None, diagnostico
        
        try:
            # Criar arquivo temporário
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
            
            # Usar pyttsx3 para sintetizar
            self.engine.save_to_file(texto, temp_path)
            self.engine.runAndWait()
            
            if salvar_arquivo:
                # Salvar cópia permanente
                perm_path = Path(f"assets/audios/{nome_alma}_{int(time.time())}.wav")
                perm_path.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy2(temp_path, perm_path)
                return str(perm_path), diagnostico
            
            return temp_path, diagnostico
            
        except Exception as e:
            diagnostico["erro"] = str(e)
            self.logger.exception(f"Erro na síntese de fala: {e}")
            return None, diagnostico
    
    def reproduzir(self, caminho_audio: str, assincrono: bool = False, wait: bool = True) -> bool:
        """Reproduz arquivo de áudio"""
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(caminho_audio)
            pygame.mixer.music.play()
            
            if wait and not assincrono:
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            
            return True
        except Exception as e:
            self.logger.exception(f"Erro na reprodução: {e}")
            return False
    
    def close(self):
        """Fecha recursos"""
        self._running = False
    
    def obter_metricas(self) -> dict:
        """Retorna métricas do sistema"""
        return {
            "tts_disponivel": self.tts_disponivel,
            "running": self._running
        }
