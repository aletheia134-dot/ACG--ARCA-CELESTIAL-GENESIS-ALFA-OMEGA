# src/encarnacao_e_interacao/lipsync_volume.py
# -*- coding: utf-8 -*-
"""
Sistema de lipsync baseado em volume de áudio.
Extrai volume em tempo real do TTS para animar avatares 3D.
"""

import logging
import threading
import time
import numpy as np
from typing import Callable, Optional

logger = logging.getLogger("LipsyncVolume")


class ExtratorVolumeAudio:
    """
    Extrai volume de áudio em tempo real para lipsync.
    Funciona com pyttsx3, ElevenLabs, ou qualquer fonte de áudio.
    """
    
    def __init__(self, callback_volume: Optional[Callable[[float], None]] = None):
        """
        Args:
            callback_volume: Função chamada com volume (0-1) em tempo real
        """
        self.callback = callback_volume
        self.audio_buffer = []
        self.sampling_rate = 16000  # Hz
        self.window_size = 800  # 50ms a 16kHz
        self.is_recording = False
        self.thread = None
        
    def iniciar_monitoramento(self):
        """Inicia thread de monitoramento"""
        self.is_recording = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("Monitoramento de volume iniciado")
    
    def parar_monitoramento(self):
        """Para monitoramento"""
        self.is_recording = False
        if self.thread:
            self.thread.join(timeout=1)
        logger.info("Monitoramento de volume parado")
    
    def _monitor_loop(self):
        """Loop principal de monitoramento"""
        while self.is_recording:
            if len(self.audio_buffer) >= self.window_size:
                # Pega janela de áudio
                window = self.audio_buffer[-self.window_size:]
                
                # Calcula RMS (volume)
                rms = np.sqrt(np.mean(np.array(window)**2))
                
                # Normaliza para 0-1
                volume = min(1.0, rms / 32768.0 * 2)
                
                # Chama callback
                if self.callback:
                    self.callback(volume)
                
                # Limpa buffer (deixa sobreposição de 100ms)
                self.audio_buffer = self.audio_buffer[-1600:]
            
            time.sleep(0.01)  # 10ms
    
    def alimentar_audio(self, dados_audio: bytes):
        """
        Alimenta o sistema com dados de áudio.
        
        Args:
            dados_audio: Bytes de áudio (formato int16)
        """
        # Converte bytes para array de int16
        samples = np.frombuffer(dados_audio, dtype=np.int16)
        self.audio_buffer.extend(samples.tolist())
        
        # Limita tamanho do buffer
        max_size = self.sampling_rate * 2  # 2 segundos
        if len(self.audio_buffer) > max_size:
            self.audio_buffer = self.audio_buffer[-max_size:]


class SistemaLipsyncIntegrado:
    """
    Integra sistema de voz com avatares 3D para lipsync automático.
    """
    
    def __init__(self, sistema_voz, gerenciador_avatares):
        """
        Args:
            sistema_voz: Instância de SistemaVozReal
            gerenciador_avatares: Instância de GerenciadorAvatares3D
        """
        self.sistema_voz = sistema_voz
        self.gerenciador_avatares = gerenciador_avatares
        self.extrator = ExtratorVolumeAudio(self._on_volume)
        self.alma_atual = None
        self.logger = logging.getLogger("SistemaLipsync")
        
        # Monkey patch no método falar
        self._original_falar = sistema_voz.falar
        sistema_voz.falar = self._falar_com_lipsync
    
    def _falar_com_lipsync(self, texto: str, voz_alma: Optional[str] = None, block: bool = True):
        """
        Versão do método falar com lipsync integrado.
        """
        # Extrai nome da alma do parâmetro voz_alma (ex: "EVA" de "EVA_voice")
        if voz_alma:
            alma = voz_alma.split('_')[0].upper()
        else:
            alma = "EVA"
        
        self.alma_atual = alma
        self.logger.info(f"🎤 {alma} falando com lipsync")
        
        # Inicia monitoramento
        self.extrator.iniciar_monitoramento()
        
        # Chama método original (vai gerar áudio)
        # Precisamos capturar o áudio gerado
        # Para pyttsx3, não temos acesso direto aos bytes
        # Solução: usar thread separada para simular volume baseado no texto
        
        def _simular_volume():
            """Simula variação de volume baseada no texto"""
            duracao_estimada = len(texto) / 10  # ~10 caracteres/segundo
            inicio = time.time()
            
            while time.time() - inicio < duracao_estimada:
                # Simula variação natural de volume
                progresso = (time.time() - inicio) / duracao_estimada
                volume = 0.5 + 0.5 * math.sin(progresso * math.pi * 4) ** 2
                self._on_volume(volume)
                time.sleep(0.05)
            
            self._on_volume(0)
            self.extrator.parar_monitoramento()
        
        # Executa fala real em thread separada
        def _falar_thread():
            self._original_falar(texto, voz_alma, block)
        
        threading.Thread(target=_falar_thread, daemon=True).start()
        
        # Inicia simulação de volume (já que não temos acesso direto ao áudio)
        threading.Thread(target=_simular_volume, daemon=True).start()
    
    def _on_volume(self, volume: float):
        """Callback chamado quando volume muda"""
        if self.alma_atual:
            self.gerenciador_avatares.atualizar_fala(self.alma_atual, volume)
    
    def parar_fala(self, alma: str):
        """Para animação de fala"""
        self.gerenciador_avatares.parar_fala(alma)
        self.alma_atual = None
        self.extrator.parar_monitoramento()