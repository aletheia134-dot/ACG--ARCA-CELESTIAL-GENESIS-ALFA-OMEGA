#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sensor_presenca.py - Sensor de Presença com Webcam para AIs da Arca Celestial

Usa webcam para detectar presença (movimento/rosto), integrando com avatares, capela e analisador.
Melhorado: Detecção de rosto com MediaPipe, sensores múltiplos (microfone), modos (ativo/dormindo/privacidade), integrações expandidas.
"""

import logging
import threading
import time
import cv2
from typing import Any, Optional, Callable

logger = logging.getLogger(__name__)

try:
    import numpy as np
    OPENCV_FULL = True
except ImportError:
    OPENCV_FULL = False
    logger.warning("NumPy não disponível; detecção de movimento limitada.")

# Integrações
try:
    from src.ritual.capela import obter_capela
    CAPELA_DISPONIVEL = True
except ImportError:
    CAPELA_DISPONIVEL = False

try:
    from src.encarnacao_e_interacao.motor_avatar_individual import MotorAvatarIndividual
    AVATAR_DISPONIVEL = True
except ImportError:
    AVATAR_DISPONIVEL = False

try:
    import pyaudio
    import speech_recognition as sr
    MICROFONE_DISPONIVEL = True
except ImportError:
    MICROFONE_DISPONIVEL = False
    logger.warning("PyAudio/SpeechRecognition não disponíveis; microfone desabilitado.")

class SensorPresenca:
    """
    Sensor de presença usando webcam: detecta movimento/rosto para presença do Criador.
    Melhorado: Detecção facial avançada, microfone, modos, integrações expandidas.
    """

    def __init__(self, callback_presenca: Optional[Callable[[bool], None]] = None, device_id: int = 0):
        self.callback = callback_presenca  # Função chamada ao detectar presença/ausência
        self.device_id = device_id  # ID da webcam (0=default)
        self.logger = logging.getLogger("SensorPresenca")
        
        self._cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._presenca_atual = False
        self._tempo_ultimo_movimento = time.time()
        self._timeout_ausencia = 30  # Segundos sem movimento â†’ ausência
        
        # Para detecção de movimento
        self._frame_anterior: Optional[np.ndarray] = None
        self._thresh_movimento = 5000  # Limiar de pixels mudados
        
        # Melhorias: Modos, microfone
        self._modo = "ativo"  # ativo, dormindo, privacidade
        self._microfone_ativo = False
        self._audio_thread: Optional[threading.Thread] = None
        
        self.logger.info("Sensor de Presença inicializado (webcam device %d, melhorado).", self.device_id)

    def iniciar(self) -> bool:
        """Inicia o sensor em thread separada."""
        if self._cap is not None:
            self.logger.info("Sensor já iniciado.")
            return True
        
        self._cap = cv2.VideoCapture(self.device_id)
        if not self._cap.isOpened():
            self.logger.error("Falha ao abrir webcam device %d.", self.device_id)
            self._cap = None
            return False
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop_deteccao, daemon=True, name="SensorPresencaLoop")
        self._thread.start()
        
        # Iniciar microfone se disponível
        if MICROFONE_DISPONIVEL and self._modo == "ativo":
            self._iniciar_microfone()
        
        self.logger.info("Sensor de Presença iniciado (thread ativa, microfone %s).", "ativo" if self._microfone_ativo else "inativo")
        return True

    def parar(self) -> None:
        """Para o sensor e libera recursos."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        if self._cap:
            self._cap.release()
            self._cap = None
        if self._audio_thread and self._audio_thread.is_alive():
            self._audio_thread.join(timeout=2)
        self.logger.info("Sensor de Presença parado.")

    def _loop_deteccao(self) -> None:
        """Loop principal: captura frames, detecta movimento/rosto."""
        while not self._stop_event.is_set():
            if not self._cap or not self._cap.isOpened():
                self.logger.error("Webcam fechada; parando loop.")
                break
            
            ret, frame = self._cap.read()
            if not ret:
                self.logger.warning("Falha ao capturar frame; pulando.")
                time.sleep(0.1)
                continue
            
            # Detecta presença (movimento ou rosto)
            movimento_detectado = self._detectar_movimento(frame)
            rosto_detectado = self._detectar_rosto(frame) if self._modo == "ativo" else False
            presenca_detectada = movimento_detectado or rosto_detectado
            
            if presenca_detectada:
                self._tempo_ultimo_movimento = time.time()
                if not self._presenca_atual:
                    self._presenca_atual = True
                    self.logger.info("Presença detectada (movimento/rosto).")
                    self._on_presenca_mudou(True)
            else:
                # Verifica timeout para ausência
                if time.time() - self._tempo_ultimo_movimento > self._timeout_ausencia:
                    if self._presenca_atual:
                        self._presenca_atual = False
                        self.logger.info("Ausência detectada (sem movimento/rosto por %ds).", self._timeout_ausencia)
                        self._on_presenca_mudou(False)
            
            time.sleep(0.5)  # Intervalo entre checks
        
        self.logger.info("Loop de detecção finalizado.")

    def _detectar_movimento(self, frame: np.ndarray) -> bool:
        """Detecta movimento comparando frames."""
        if not OPENCV_FULL:
            return False
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        if self._frame_anterior is None:
            self._frame_anterior = gray
            return False
        
        frame_delta = cv2.absdiff(self._frame_anterior, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        movimento = sum(cv2.contourArea(c) for c in contours) > self._thresh_movimento
        
        self._frame_anterior = gray
        return movimento

    def _detectar_rosto(self, frame: np.ndarray) -> bool:
        """Detecta rosto usando MediaPipe ou Haar cascades."""
        try:
            import mediapipe as mp
            mp_face = mp.solutions.face_detection.FaceDetection()
            results = mp_face.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            return results.detections is not None
        except ImportError:
            # Fallback Haar
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            return len(faces) > 0

    def _iniciar_microfone(self):
        """Inicia detecção de som via microfone."""
        if not MICROFONE_DISPONIVEL:
            return
        
        def _listen():
            r = sr.Recognizer()
            with sr.Microphone() as source:
                while not self._stop_event.is_set():
                    try:
                        audio = r.listen(source, timeout=1, phrase_time_limit=5)
                        if audio:
                            self.logger.debug("Som detectado via microfone.")
                            # Pode integrar com voz
                    except:
                        pass
        
        self._audio_thread = threading.Thread(target=_listen, daemon=True)
        self._audio_thread.start()
        self._microfone_ativo = True

    def _on_presenca_mudou(self, presente: bool) -> None:
        """Chamado quando presença muda: integra com AIs."""
        if self.callback:
            try:
                self.callback(presente)
            except Exception as e:
                self.logger.exception("Erro no callback customizado: %s", e)
        
        # Integração com Capela
        if CAPELA_DISPONIVEL:
            capela = obter_capela()
            if presente:
                capela.sair_capela()
            else:
                capela.entrar_capela(duracao_s=300)  # 5min
        
        # Integração com Avatares
        if AVATAR_DISPONIVEL and hasattr(self, '_avatar_ref'):
            avatar = self._avatar_ref
            if presente:
                avatar.atualizar_rosto("alegria_leve")
            else:
                avatar.atualizar_rosto("solidao_leve")
        
        # Integração com Emocoes
        try:
            from src.emocoes import gerenciador_emocoes
            if presente:
                gerenciador_emocoes.definir_humor("alegre")
        except:
            pass
        
        # Modo dormindo
        if not presente and self._modo == "dormindo":
            self.parar()
        
        self.logger.debug("Integrações AIs executadas (presença: %s).", presente)

    def status_presenca(self) -> dict:
        """Retorna status atual."""
        return {
            "presenca_detectada": self._presenca_atual,
            "tempo_ultimo_movimento": self._tempo_ultimo_movimento,
            "timeout_ausencia": self._timeout_ausencia,
            "webcam_ativa": self._cap is not None and self._cap.isOpened(),
            "microfone_ativo": self._microfone_ativo,
            "modo": self._modo
        }

    def configurar_timeout(self, segundos: int) -> None:
        """Configura timeout para ausência."""
        if segundos > 0:
            self._timeout_ausencia = segundos
            self.logger.info("Timeout ausência configurado para %ds.", segundos)

    def ativar_modo(self, modo: str):
        """Ativa modo: ativo, dormindo, privacidade."""
        if modo in ["ativo", "dormindo", "privacidade"]:
            self._modo = modo
            if modo == "privacidade":
                self.parar()
            elif modo == "ativo":
                self.iniciar()
            self.logger.info("Modo sensor alterado para %s.", modo)


# Instância global
_sensor_presenca: Optional[SensorPresenca] = None

def obter_sensor_presenca(callback: Optional[Callable[[bool], None]] = None) -> SensorPresenca:
    """Retorna instância singleton."""
    global _sensor_presenca
    if _sensor_presenca is None:
        _sensor_presenca = SensorPresenca(callback=callback)
    return _sensor_presenca


# Teste
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("ðŸ–¥ï¸ Teste Sensor de Presença")
    print("=" * 40)
    
    def callback_teste(presente: bool):
        print(f"Callback: Presença mudou para {presente}")
    
    sensor = obter_sensor_presenca(callback=callback_teste)
    
    if sensor.iniciar():
        print("Sensor iniciado. Mova-se na frente da webcam para testar.")
        time.sleep(20)
        sensor.parar()
    else:
        print("Falha ao iniciar sensor.")
    
    print(f"Status final: {sensor.status_presenca()}")
    print("âœ… Sensor testado (melhorado)!")

# --- FIM DO ARQUIVO sensor_presenca.py ---
