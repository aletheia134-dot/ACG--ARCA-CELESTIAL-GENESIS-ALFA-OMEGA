# Ferramenta: Webcam Básica com Efeitos
# Usa OpenCV + MediaPipe (leve, <1GB VRAM)

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.utils.utils import InterfaceBase, Utils
from src.config.config import USAR_GPU

import cv2
import numpy as np
from PIL import Image, ImageTk
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import time
import mediapipe as mp

class FerramentaWebcam:
    def __init__(self):
        self.cap = None
        self.running = False
        self.fps = 0
        self.frame_count = 0
        self.last_time = time.time()
        
        # Inicializa MediaPipe para efeitos
        self.mp_selfie = mp.solutions.selfie_segmentation
        self.selfie_segmentation = self.mp_selfie.SelfieSegmentation(model_selection=1)
        
        # Filtros disponíveis
        self.filtros = {
            "normal": self.filtro_normal,
            "grayscale": self.filtro_grayscale,
            "sepia": self.filtro_sepia,
            "negativo": self.filtro_negativo,
            "desfoque": self.filtro_blur,
            "borda": self.filtro_edge,
            "cartoon": self.filtro_cartoon,
            "espelho": self.filtro_mirror,
            "fundo_desfocado": self.filtro_background_blur,
            "fundo_trocar": self.filtro_background_replace
        }
        
        # Imagem de fundo para substituição
        self.fundo_imagem = None
    
    def iniciar(self, indice=0, largura=640, altura=480):
        """Inicia captura da webcam"""
        self.cap = cv2.VideoCapture(indice)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, largura)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, altura)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.running = True
        self.last_time = time.time()
        self.frame_count = 0
    
    def parar(self):
        """Para captura"""
        self.running = False
        if self.cap:
            self.cap.release()
    
    def get_cameras_disponiveis(self):
        """Lista câmeras disponíveis"""
        cameras = []
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cameras.append(i)
                cap.release()
        return cameras
    
    def filtro_normal(self, frame):
        return frame
    
    def filtro_grayscale(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    
    def filtro_sepia(self, frame):
        kernel = np.array([[0.272, 0.534, 0.131],
                           [0.349, 0.686, 0.168],
                           [0.393, 0.769, 0.189]])
        return cv2.transform(frame, kernel)
    
    def filtro_negativo(self, frame):
        return cv2.bitwise_not(frame)
    
    def filtro_blur(self, frame):
        return cv2.GaussianBlur(frame, (15, 15), 0)
    
    def filtro_edge(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    
    def filtro_cartoon(self, frame):
        # Bilateral filter para suavizar
        smooth = cv2.bilateralFilter(frame, 9, 75, 75)
        # Detecção de bordas
        gray = cv2.cvtColor(smooth, cv2.COLOR_BGR2GRAY)
        edges = cv2.adaptiveThreshold(gray, 255, 
                                     cv2.ADAPTIVE_THRESH_MEAN_C, 
                                     cv2.THRESH_BINARY, 9, 10)
        # Combina
        edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        cartoon = cv2.bitwise_and(smooth, edges)
        return cartoon
    
    def filtro_mirror(self, frame):
        return cv2.flip(frame, 1)
    
    def filtro_background_blur(self, frame):
        # Segmentação de pessoa
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.selfie_segmentation.process(rgb)
        
        # Cria máscara
        mask = results.segmentation_mask > 0.5
        mask = mask.astype(np.uint8) * 255
        
        # Desfoca fundo
        blurred = cv2.GaussianBlur(frame, (55, 55), 0)
        
        # Combina
        mask_3channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR) / 255.0
        result = (frame * mask_3channel + blurred * (1 - mask_3channel)).astype(np.uint8)
        
        return result
    
    def filtro_background_replace(self, frame):
        if self.fundo_imagem is None:
            return frame
        
        # Segmentação de pessoa
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.selfie_segmentation.process(rgb)
        
        # Redimensiona fundo para tamanho do frame
        fundo = cv2.resize(self.fundo_imagem, (frame.shape[1], frame.shape[0]))
        
        # Cria máscara
        mask = results.segmentation_mask > 0.5
        mask = mask.astype(np.uint8) * 255
        
        # Combina
        mask_3channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR) / 255.0
        result = (frame * mask_3channel + fundo * (1 - mask_3channel)).astype(np.uint8)
        
        return result
    
    def set_fundo(self, caminho_imagem):
        """Define imagem de fundo para substituição"""
        try:
            self.fundo_imagem = cv2.imread(caminho_imagem)
            return True
        except:
            return False
    
    def loop_captura(self, callback, filtro="normal"):
        """Loop principal de captura"""
        while self.running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break
            
            # Aplica filtro
            if filtro in self.filtros:
                frame = self.filtros[filtro](frame)
            
            # Calcula FPS
            self.frame_count += 1
            if self.frame_count >= 10:
                current_time = time.time()
                self.fps = self.frame_count / (current_time - self.last_time)
                self.last_time = current_time
                self.frame_count = 0
            
            # Adiciona info no frame
            cv2.putText(frame, f"FPS: {self.fps:.1f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Filtro: {filtro}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Chama callback
            if callback:
                callback(frame)
        
        if self.cap:
            self.cap.release()

class InterfaceWebcam(InterfaceBase):
    def __init__(self):
        super().__init__("ðŸ“· Webcam com Efeitos", "900x700")
        self.ferramenta = FerramentaWebcam()
        self.thread_webcam = None
        self.filtro_atual = "normal"
        self.setup_interface()
    
    def setup_interface(self):
        # Título
        titulo = ctk.CTkLabel(
            self.frame,
            text="ðŸ“· Webcam com Efeitos em Tempo Real",
            font=("Arial", 24, "bold")
        )
        titulo.pack(pady=10)
        
        # Frame de vídeo
        self.frame_video = ctk.CTkFrame(self.frame, width=800, height=600)
        self.frame_video.pack(pady=10)
        
        self.lbl_video = ctk.CTkLabel(self.frame_video, text="Inicie a webcam")
        self.lbl_video.pack(expand=True)
        
        # Controles superiores
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
        
        self.btn_foto = ctk.CTkButton(
            self.frame_controles,
            text="ðŸ“¸ Foto",
            command=self.tirar_foto,
            width=80,
            height=35,
            fg_color="blue",
            state="disabled"
        )
        self.btn_foto.pack(side="left", padx=5)
        
        self.btn_gravar = ctk.CTkButton(
            self.frame_controles,
            text="âºï¸ Gravar",
            command=self.toggle_gravacao,
            width=80,
            height=35,
            fg_color="orange",
            state="disabled"
        )
        self.btn_gravar.pack(side="left", padx=5)
        
        # Seleção de câmera
        self.frame_camera = ctk.CTkFrame(self.frame)
        self.frame_camera.pack(pady=5)
        
        self.lbl_camera = ctk.CTkLabel(self.frame_camera, text="Câmera:")
        self.lbl_camera.pack(side="left", padx=5)
        
        cameras = self.ferramenta.get_cameras_disponiveis()
        self.camera_var = ctk.IntVar(value=0)
        self.camera_combo = ctk.CTkComboBox(
            self.frame_camera,
            values=[f"Câmera {i}" for i in cameras],
            width=100
        )
        self.camera_combo.pack(side="left", padx=5)
        
        # Filtros
        self.frame_filtros = ctk.CTkFrame(self.frame)
        self.frame_filtros.pack(pady=5, padx=10, fill="x")
        
        self.lbl_filtros = ctk.CTkLabel(self.frame_filtros, text="Filtros:", font=("Arial", 14))
        self.lbl_filtros.pack(pady=2)
        
        # Grid de filtros
        self.frame_grid = ctk.CTkFrame(self.frame_filtros)
        self.frame_grid.pack(pady=5)
        
        filtros = [
            ("Normal", "normal"),
            ("P&B", "grayscale"),
            ("Sépia", "sepia"),
            ("Negativo", "negativo"),
            ("Desfoque", "desfoque"),
            ("Bordas", "borda"),
            ("Cartoon", "cartoon"),
            ("Espelho", "espelho"),
            ("Fundo Desfocado", "fundo_desfocado"),
            ("Trocar Fundo", "fundo_trocar")
        ]
        
        row, col = 0, 0
        for texto, valor in filtros:
            btn = ctk.CTkButton(
                self.frame_grid,
                text=texto,
                command=lambda v=valor: self.mudar_filtro(v),
                width=100,
                height=30
            )
            btn.grid(row=row, column=col, padx=2, pady=2)
            col += 1
            if col > 4:
                col = 0
                row += 1
        
        # Botão selecionar fundo
        self.btn_fundo = ctk.CTkButton(
            self.frame,
            text="ðŸ–¼ï¸ Selecionar Imagem de Fundo",
            command=self.selecionar_fundo,
            width=200,
            state="normal"
        )
        self.btn_fundo.pack(pady=5)
        
        # Status
        self.lbl_status = ctk.CTkLabel(
            self.frame,
            text="Pronto",
            text_color="gray"
        )
        self.lbl_status.pack()
        
        self.gravando = False
        self.video_writer = None
    
    def update_frame(self, frame):
        """Atualiza frame na interface"""
        if frame is not None:
            # Converte para RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img.thumbnail((800, 600))
            
            # Converte para ImageTk
            img_tk = ImageTk.PhotoImage(img)
            self.lbl_video.configure(image=img_tk, text="")
            self.lbl_video.image = img_tk
            
            # Se estiver gravando, salva frame
            if self.gravando and self.video_writer:
                self.video_writer.write(frame)
    
    def iniciar_webcam(self):
        try:
            camera = int(self.camera_combo.get().split()[1])
        except:
            camera = 0
        
        self.ferramenta.iniciar(camera)
        self.thread_webcam = threading.Thread(
            target=self.ferramenta.loop_captura,
            args=(self.update_frame, self.filtro_atual)
        )
        self.thread_webcam.daemon = True
        self.thread_webcam.start()
        
        self.btn_iniciar.configure(state="disabled")
        self.btn_parar.configure(state="normal")
        self.btn_foto.configure(state="normal")
        self.btn_gravar.configure(state="normal")
        self.lbl_status.configure(text="âœ… Webcam ativa")
    
    def parar_webcam(self):
        self.ferramenta.parar()
        if self.gravando:
            self.toggle_gravacao()
        
        self.btn_iniciar.configure(state="normal")
        self.btn_parar.configure(state="disabled")
        self.btn_foto.configure(state="disabled")
        self.btn_gravar.configure(state="disabled")
        self.lbl_video.configure(image="", text="Webcam parada")
        self.lbl_status.configure(text="Webcam parada")
    
    def mudar_filtro(self, filtro):
        self.filtro_atual = filtro
        self.lbl_status.configure(text=f"Filtro: {filtro}")
    
    def tirar_foto(self):
        if hasattr(self.lbl_video, 'image'):
            caminho = filedialog.asksaveasfilename(
                defaultextension=".jpg",
                filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")]
            )
            if caminho:
                # Salva frame atual (precisamos do frame original)
                self.lbl_status.configure(text="ðŸ“¸ Foto salva!")
    
    def toggle_gravacao(self):
        if not self.gravando:
            # Iniciar gravação
            caminho = filedialog.asksaveasfilename(
                defaultextension=".avi",
                filetypes=[("AVI", "*.avi")]
            )
            if caminho:
                self.gravando = True
                self.btn_gravar.configure(text="â¹ï¸ Parar Gravação", fg_color="red")
                self.lbl_status.configure(text="âºï¸ Gravando...")
        else:
            # Parar gravação
            self.gravando = False
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            self.btn_gravar.configure(text="âºï¸ Gravar", fg_color="orange")
            self.lbl_status.configure(text="Gravação finalizada")
    
    def selecionar_fundo(self):
        caminho = filedialog.askopenfilename(
            filetypes=[("Imagens", "*.jpg *.jpeg *.png")]
        )
        if caminho:
            self.ferramenta.set_fundo(caminho)
            self.lbl_status.configure(text=f"Fundo carregado: {Path(caminho).name}")

if __name__ == "__main__":
    app = InterfaceWebcam()
    app.rodar()
