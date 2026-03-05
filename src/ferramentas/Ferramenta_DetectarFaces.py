# Ferramenta: Detecção Facial em Tempo Real
# Usa MediaPipe (leve, CPU/GPU)

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.utils.utils import InterfaceBase, Utils

import cv2
import mediapipe as mp
from PIL import Image, ImageTk
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import time
import numpy as np

class FerramentaDetectarFaces:
    def __init__(self):
        # Inicializa MediaPipe Face Detection
        self.mp_face = mp.solutions.face_detection
        self.mp_drawing = mp.solutions.drawing_utils
        self.face_detection = self.mp_face.FaceDetection(
            model_selection=1,  # 0=short range, 1=long range
            min_detection_confidence=0.5
        )
        
        # Para landmarks faciais
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=5,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        self.cap = None
        self.running = False
        self.fps = 0
        self.modo = "deteccao"  # deteccao, landmarks, ambos
        self.frame_count = 0
        self.last_time = time.time()
    
    def iniciar(self, indice=0):
        self.cap = cv2.VideoCapture(indice)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.running = True
    
    def parar(self):
        self.running = False
        if self.cap:
            self.cap.release()
    
    def processar_deteccao(self, frame):
        """Apenas detecta rostos com bounding boxes"""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_detection.process(rgb)
        
        if results.detections:
            h, w, _ = frame.shape
            for detection in results.detections:
                # Desenha bounding box
                bbox = detection.location_data.relative_bounding_box
                x = int(bbox.xmin * w)
                y = int(bbox.ymin * h)
                width = int(bbox.width * w)
                height = int(bbox.height * h)
                
                cv2.rectangle(frame, (x, y), (x+width, y+height), (0, 255, 0), 2)
                
                # Confiança
                confidence = detection.score[0]
                cv2.putText(frame, f"{confidence:.2f}", (x, y-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                # Pontos chave (olhos, nariz, boca)
                keypoints = detection.location_data.relative_keypoints
                for kp in keypoints:
                    kp_x = int(kp.x * w)
                    kp_y = int(kp.y * h)
                    cv2.circle(frame, (kp_x, kp_y), 2, (0, 0, 255), -1)
        
        return frame
    
    def processar_landmarks(self, frame):
        """Detecta 468 landmarks faciais"""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)
        
        if results.multi_face_landmarks:
            h, w, _ = frame.shape
            for face_landmarks in results.multi_face_landmarks:
                # Desenha todos os landmarks
                for landmark in face_landmarks.landmark:
                    x = int(landmark.x * w)
                    y = int(landmark.y * h)
                    cv2.circle(frame, (x, y), 1, (0, 255, 0), -1)
                
                # Desenha conexões
                self.mp_drawing.draw_landmarks(
                    frame,
                    face_landmarks,
                    self.mp_face_mesh.FACEMESH_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=self.mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=1)
                )
        
        return frame
    
    def processar_ambos(self, frame):
        """Combina detecção e landmarks"""
        frame = self.processar_deteccao(frame)
        frame = self.processar_landmarks(frame)
        return frame
    
    def loop_captura(self, callback):
        """Loop principal"""
        while self.running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break
            
            # Processa conforme modo
            if self.modo == "deteccao":
                frame = self.processar_deteccao(frame)
            elif self.modo == "landmarks":
                frame = self.processar_landmarks(frame)
            elif self.modo == "ambos":
                frame = self.processar_ambos(frame)
            
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
    
    def processar_imagem(self, caminho_imagem):
        """Processa uma imagem estática"""
        frame = cv2.imread(caminho_imagem)
        if frame is None:
            return None
        
        # Processa
        frame = self.processar_deteccao(frame)
        frame = self.processar_landmarks(frame)
        
        return frame

class InterfaceDetectarFaces(InterfaceBase):
    def __init__(self):
        super().__init__("ðŸ‘¤ Detecção Facial", "900x700")
        self.ferramenta = FerramentaDetectarFaces()
        self.thread_webcam = None
        self.setup_interface()
    
    def setup_interface(self):
        titulo = ctk.CTkLabel(
            self.frame,
            text="ðŸ‘¤ Detecção Facial em Tempo Real",
            font=("Arial", 24, "bold")
        )
        titulo.pack(pady=10)
        
        # Frame de vídeo
        self.frame_video = ctk.CTkFrame(self.frame, width=800, height=600)
        self.frame_video.pack(pady=10)
        
        self.lbl_video = ctk.CTkLabel(self.frame_video, text="Inicie a webcam")
        self.lbl_video.pack(expand=True)
        
        # Controles
        self.frame_controles = ctk.CTkFrame(self.frame)
        self.frame_controles.pack(pady=5)
        
        self.btn_iniciar = ctk.CTkButton(
            self.frame_controles,
            text="â–¶ï¸ Iniciar Webcam",
            command=self.iniciar_webcam,
            width=120,
            height=35,
            fg_color="green"
        )
        self.btn_iniciar.pack(side="left", padx=5)
        
        self.btn_parar = ctk.CTkButton(
            self.frame_controles,
            text="â¹ï¸ Parar",
            command=self.parar_webcam,
            width=80,
            height=35,
            fg_color="red",
            state="disabled"
        )
        self.btn_parar.pack(side="left", padx=5)
        
        self.btn_imagem = ctk.CTkButton(
            self.frame_controles,
            text="ðŸ–¼ï¸ Processar Imagem",
            command=self.processar_imagem,
            width=120,
            height=35
        )
        self.btn_imagem.pack(side="left", padx=5)
        
        self.btn_foto = ctk.CTkButton(
            self.frame_controles,
            text="ðŸ“¸ Foto",
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
        
        self.modo_var = ctk.StringVar(value="deteccao")
        
        self.radio_deteccao = ctk.CTkRadioButton(
            self.frame_modos,
            text="Detecção (bounding boxes)",
            variable=self.modo_var,
            value="deteccao",
            command=self.mudar_modo
        )
        self.radio_deteccao.pack(side="left", padx=5)
        
        self.radio_landmarks = ctk.CTkRadioButton(
            self.frame_modos,
            text="Landmarks (468 pontos)",
            variable=self.modo_var,
            value="landmarks",
            command=self.mudar_modo
        )
        self.radio_landmarks.pack(side="left", padx=5)
        
        self.radio_ambos = ctk.CTkRadioButton(
            self.frame_modos,
            text="Ambos",
            variable=self.modo_var,
            value="ambos",
            command=self.mudar_modo
        )
        self.radio_ambos.pack(side="left", padx=5)
        
        # Estatísticas
        self.frame_stats = ctk.CTkFrame(self.frame)
        self.frame_stats.pack(pady=5, padx=10, fill="x")
        
        self.lbl_stats = ctk.CTkLabel(
            self.frame_stats,
            text="Aguardando detecção...",
            font=("Arial", 12)
        )
        self.lbl_stats.pack()
    
    def update_frame(self, frame):
        if frame is not None:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img.thumbnail((800, 600))
            img_tk = ImageTk.PhotoImage(img)
            self.lbl_video.configure(image=img_tk, text="")
            self.lbl_video.image = img_tk
            
            # Atualiza estatísticas (simulado)
            self.lbl_stats.configure(text="Detectando rostos...")
    
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
        self.lbl_stats.configure(text="Webcam parada")
    
    def mudar_modo(self):
        self.ferramenta.modo = self.modo_var.get()
    
    def processar_imagem(self):
        caminho = filedialog.askopenfilename(
            filetypes=[("Imagens", "*.jpg *.jpeg *.png")]
        )
        if caminho:
            frame = self.ferramenta.processar_imagem(caminho)
            if frame is not None:
                # Mostra resultado
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                img.thumbnail((800, 600))
                img_tk = ImageTk.PhotoImage(img)
                self.lbl_video.configure(image=img_tk, text="")
                self.lbl_video.image = img_tk
                
                # Pergunta se quer salvar
                if messagebox.askyesno("Salvar", "Deseja salvar a imagem processada?"):
                    caminho_salvar = filedialog.asksaveasfilename(
                        defaultextension=".jpg",
                        filetypes=[("JPEG", "*.jpg")]
                    )
                    if caminho_salvar:
                        cv2.imwrite(caminho_salvar, frame)
    
    def tirar_foto(self):
        if hasattr(self.lbl_video, 'image'):
            caminho = filedialog.asksaveasfilename(
                defaultextension=".jpg",
                filetypes=[("JPEG", "*.jpg")]
            )
            if caminho:
                # Implementar salvamento
                self.lbl_stats.configure(text="ðŸ“¸ Foto salva!")

if __name__ == "__main__":
    app = InterfaceDetectarFaces()
    app.rodar()
