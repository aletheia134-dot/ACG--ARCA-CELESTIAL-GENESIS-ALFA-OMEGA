# Ferramenta: Deteco de Pose Corporal
# Usa MediaPipe Pose (leve, CPU/GPU)

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.modulos.utils import InterfaceBase, Utils

import cv2
import mediapipe as mp
from PIL import Image, ImageTk
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import time
import numpy as np

class FerramentaPoseDetection:
    def __init__(self):
        # Inicializa MediaPipe Pose
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,  # 0, 1, 2 (2  mais preciso, mais lento)
            smooth_landmarks=True,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        self.cap = None
        self.running = False
        self.fps = 0
        self.modo = "pontos"  # pontos, linhas, ambas
        self.frame_count = 0
        self.last_time = time.time()
        
        # conexões para desenho
        self.connections = self.mp_pose.POSE_CONNECTIONS
    
    def iniciar(self, indice=0):
        self.cap = cv2.VideoCapture(indice)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.running = True
    
    def parar(self):
        self.running = False
        if self.cap:
            self.cap.release()
    
    def processar_frame(self, frame):
        """Detecta pose no frame"""
        # Converte para RGB
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)
        
        if results.pose_landmarks:
            h, w, _ = frame.shape
            
            if self.modo in ["pontos", "ambas"]:
                # Desenha apenas pontos
                for landmark in results.pose_landmarks.landmark:
                    x = int(landmark.x * w)
                    y = int(landmark.y * h)
                    cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)
            
            if self.modo in ["linhas", "ambas"]:
                # Desenha conexões
                self.mp_drawing.draw_landmarks(
                    frame,
                    results.pose_landmarks,
                    self.mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
                )
            
            # Adiciona info de ngulos
            self._calcular_angulos(frame, results.pose_landmarks.landmark, w, h)
        
        return frame
    
    def _calcular_angulos(self, frame, landmarks, w, h):
        """Calcula e mostra ngulos das articulaes"""
        # índices dos landmarks
        # Ombro, cotovelo, punho
        ombro_d = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        cotovelo_d = landmarks[self.mp_pose.PoseLandmark.RIGHT_ELBOW]
        punho_d = landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST]
        
        # Calcula ngulo do cotovelo direito
        if ombro_d and cotovelo_d and punho_d:
            angulo = self._calcular_angulo_3pontos(
                (ombro_d.x, ombro_d.y),
                (cotovelo_d.x, cotovelo_d.y),
                (punho_d.x, punho_d.y)
            )
            
            # Mostra ngulo
            x = int(cotovelo_d.x * w)
            y = int(cotovelo_d.y * h)
            cv2.putText(frame, f"{angulo:.0f}", (x, y-20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        # Joelho direito
        quadril_d = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP]
        joelho_d = landmarks[self.mp_pose.PoseLandmark.RIGHT_KNEE]
        tornozelo_d = landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE]
        
        if quadril_d and joelho_d and tornozelo_d:
            angulo = self._calcular_angulo_3pontos(
                (quadril_d.x, quadril_d.y),
                (joelho_d.x, joelho_d.y),
                (tornozelo_d.x, tornozelo_d.y)
            )
            
            x = int(joelho_d.x * w)
            y = int(joelho_d.y * h)
            cv2.putText(frame, f"{angulo:.0f}", (x, y-20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
    
    def _calcular_angulo_3pontos(self, p1, p2, p3):
        """Calcula ngulo entre trs pontos"""
        a = np.array(p1)
        b = np.array(p2)
        c = np.array(p3)
        
        ba = a - b
        bc = c - b
        
        cos_angulo = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
        angulo = np.arccos(np.clip(cos_angulo, -1, 1))
        
        return np.degrees(angulo)
    
    def loop_captura(self, callback):
        """Loop principal"""
        while self.running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break
            
            # Processa
            frame = self.processar_frame(frame)
            
            # Calcula FPS
            self.frame_count += 1
            if self.frame_count >= 10:
                current_time = time.time()
                self.fps = self.frame_count / (current_time - self.last_time)
                self.last_time = current_time
                self.frame_count = 0
            
            # Adiciona info
            cv2.putText(frame, f"FPS: {self.fps:.1f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            if callback:
                callback(frame)

class InterfacePoseDetection(InterfaceBase):
    def __init__(self):
        super().__init__(" Deteco de Pose", "900x700")
        self.ferramenta = FerramentaPoseDetection()
        self.thread_webcam = None
        self.setup_interface()
    
    def setup_interface(self):
        titulo = ctk.CTkLabel(
            self.frame,
            text=" Deteco de Pose Corporal",
            font=("Arial", 24, "bold")
        )
        titulo.pack(pady=10)
        
        # Frame de vdeo
        self.frame_video = ctk.CTkFrame(self.frame, width=800, height=600)
        self.frame_video.pack(pady=10)
        
        self.lbl_video = ctk.CTkLabel(self.frame_video, text="Inicie a webcam")
        self.lbl_video.pack(expand=True)
        
        # Controles
        self.frame_controles = ctk.CTkFrame(self.frame)
        self.frame_controles.pack(pady=5)
        
        self.btn_iniciar = ctk.CTkButton(
            self.frame_controles,
            text=" Iniciar Webcam",
            command=self.iniciar_webcam,
            width=120,
            height=35,
            fg_color="green"
        )
        self.btn_iniciar.pack(side="left", padx=5)
        
        self.btn_parar = ctk.CTkButton(
            self.frame_controles,
            text=" Parar",
            command=self.parar_webcam,
            width=80,
            height=35,
            fg_color="red",
            state="disabled"
        )
        self.btn_parar.pack(side="left", padx=5)
        
        self.btn_foto = ctk.CTkButton(
            self.frame_controles,
            text=" Foto",
            command=self.tirar_foto,
            width=80,
            height=35,
            state="disabled"
        )
        self.btn_foto.pack(side="left", padx=5)
        
        # Modos
        self.frame_modos = ctk.CTkFrame(self.frame)
        self.frame_modos.pack(pady=5, padx=10, fill="x")
        
        self.lbl_modos = ctk.CTkLabel(self.frame_modos, text="Modo:", font=("Arial", 14))
        self.lbl_modos.pack(side="left", padx=5)
        
        self.modo_var = ctk.StringVar(value="ambas")
        
        self.radio_pontos = ctk.CTkRadioButton(
            self.frame_modos,
            text="Apenas Pontos",
            variable=self.modo_var,
            value="pontos",
            command=self.mudar_modo
        )
        self.radio_pontos.pack(side="left", padx=5)
        
        self.radio_linhas = ctk.CTkRadioButton(
            self.frame_modos,
            text="Apenas Linhas",
            variable=self.modo_var,
            value="linhas",
            command=self.mudar_modo
        )
        self.radio_linhas.pack(side="left", padx=5)
        
        self.radio_ambas = ctk.CTkRadioButton(
            self.frame_modos,
            text="Ambos",
            variable=self.modo_var,
            value="ambas",
            command=self.mudar_modo
        )
        self.radio_ambas.pack(side="left", padx=5)
        
        # Info
        self.frame_info = ctk.CTkFrame(self.frame)
        self.frame_info.pack(pady=5, padx=10, fill="x")
        
        self.lbl_info = ctk.CTkLabel(
            self.frame_info,
            text="33 pontos corporais detectados\nngulos calculados automaticamente",
            justify="left"
        )
        self.lbl_info.pack()
    
    def update_frame(self, frame):
        if frame is not None:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img.thumbnail((800, 600))
            img_tk = ImageTk.PhotoImage(img)
            self.lbl_video.configure(image=img_tk, text="")
            self.lbl_video.image = img_tk
    
    def iniciar_webcam(self):
        self.ferramenta.iniciar()
        self.thread_webcam = threading.Thread(
            target=self.ferramenta.loop_captura,
            args=(self.update_frame,)
        )
        self.thread_webcam.daemon = True
        self.thread_webcam.start()
        
        self.btn_iniciar.configure(state="disabled")
        self.btn_parar.configure(state="normal")
        self.btn_foto.configure(state="normal")
    
    def parar_webcam(self):
        self.ferramenta.parar()
        self.btn_iniciar.configure(state="normal")
        self.btn_parar.configure(state="disabled")
        self.btn_foto.configure(state="disabled")
        self.lbl_video.configure(image="", text="Webcam parada")
    
    def mudar_modo(self):
        self.ferramenta.modo = self.modo_var.get()
    
    def tirar_foto(self):
        if hasattr(self.lbl_video, 'image'):
            caminho = filedialog.asksaveasfilename(
                defaultextension=".jpg",
                filetypes=[("JPEG", "*.jpg")]
            )
            if caminho:
                # Implementar salvamento
                pass

if __name__ == "__main__":
    app = InterfacePoseDetection()
    app.rodar()
