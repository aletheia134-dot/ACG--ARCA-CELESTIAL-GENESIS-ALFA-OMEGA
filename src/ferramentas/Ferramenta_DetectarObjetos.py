# Ferramenta: Deteco de Objetos em Tempo Real
# Usa YOLOv5 (tiny/nano) - 1-2GB VRAM

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.modulos.utils import InterfaceBase, Utils
from src.config.config import USAR_GPU

import cv2
import torch
import numpy as np
from PIL import Image, ImageTk
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import time

class FerramentaDetectarObjetos:
    def __init__(self, usar_gpu=True):
        self.usar_gpu = usar_gpu and torch.cuda.is_available()
        self.device = torch.device("cuda" if self.usar_gpu else "cpu")
        self.model = None
        self.nomes_classes = []
        self.carregar_modelo()
        
        # Cores para cada classe
        np.random.seed(42)
        self.cores = np.random.randint(0, 255, size=(100, 3)).tolist()
    
    def carregar_modelo(self, modelo="yolov5n"):  # nano (mais leve)
        """Carrega YOLOv5"""
        try:
            self.model = torch.hub.load(
                'ultralytics/yolov5',
                modelo,
                pretrained=True,
                device=self.device
            )
            self.model.conf = 0.5  # confiana mnima
            self.model.iou = 0.45  # NMS IoU threshold
            self.nomes_classes = self.model.names
            print(f"[OK] YOLO carregado na {self.device}")
        except Exception as e:
            print(f"[ERRO] Erro YOLO: {e}")
            self.model = None
    
    def iniciar_webcam(self, indice=0):
        self.cap = cv2.VideoCapture(indice)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.running = True
    
    def parar_webcam(self):
        self.running = False
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()
    
    def processar_frame(self, frame):
        """Detecta objetos no frame"""
        if self.model is None:
            return frame
        
        # Converte BGR para RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detecta
        results = self.model(frame_rgb)
        
        # Desenha resultados
        for det in results.xyxy[0]:  # x1, y1, x2, y2, conf, classe
            x1, y1, x2, y2, conf, cls = det.cpu().numpy()
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            classe = int(cls)
            
            # Desenha bounding box
            cor = self.cores[classe % len(self.cores)]
            cv2.rectangle(frame, (x1, y1), (x2, y2), cor, 2)
            
            # Desenha label
            label = f"{self.nomes_classes[classe]} {conf:.2f}"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(frame, (x1, y1-20), (x1+w, y1), cor, -1)
            cv2.putText(frame, label, (x1, y1-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return frame, results
    
    def processar_imagem(self, caminho_imagem):
        """Processa imagem esttica"""
        frame = cv2.imread(caminho_imagem)
        if frame is None:
            return None, None
        
        return self.processar_frame(frame)
    
    def loop_captura(self, callback):
        """Loop da webcam"""
        fps = 0
        frame_count = 0
        last_time = time.time()
        
        while self.running and hasattr(self, 'cap') and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break
            
            # Processa
            frame, results = self.processar_frame(frame)
            
            # Calcula FPS
            frame_count += 1
            if frame_count >= 10:
                current_time = time.time()
                fps = frame_count / (current_time - last_time)
                last_time = current_time
                frame_count = 0
            
            # Adiciona info
            cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            if results is not None:
                cv2.putText(frame, f"Objetos: {len(results.xyxy[0])}", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            if callback:
                callback(frame)

class InterfaceDetectarObjetos(InterfaceBase):
    def __init__(self):
        super().__init__(" Deteco de Objetos", "900x700")
        self.ferramenta = FerramentaDetectarObjetos(usar_gpu=USAR_GPU)
        self.thread_webcam = None
        self.setup_interface()
    
    def setup_interface(self):
        titulo = ctk.CTkLabel(
            self.frame,
            text=" Deteco de Objetos em Tempo Real (YOLO)",
            font=("Arial", 24, "bold")
        )
        titulo.pack(pady=10)
        
        # Status GPU
        status = "[OK] GPU Ativa (YOLO)" if self.ferramenta.usar_gpu else "[AVISO] CPU (lento)"
        self.lbl_gpu = ctk.CTkLabel(self.frame, text=status)
        self.lbl_gpu.pack(pady=5)
        
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
        
        self.btn_imagem = ctk.CTkButton(
            self.frame_controles,
            text=" Processar Imagem",
            command=self.processar_imagem,
            width=120,
            height=35
        )
        self.btn_imagem.pack(side="left", padx=5)
        
        self.btn_foto = ctk.CTkButton(
            self.frame_controles,
            text=" Foto",
            command=self.tirar_foto,
            width=80,
            height=35,
            state="disabled"
        )
        self.btn_foto.pack(side="left", padx=5)
        
        # Confiana
        self.frame_conf = ctk.CTkFrame(self.frame)
        self.frame_conf.pack(pady=5, padx=10, fill="x")
        
        self.lbl_conf = ctk.CTkLabel(self.frame_conf, text="Confiana mnima:")
        self.lbl_conf.pack(side="left", padx=5)
        
        self.conf_slider = ctk.CTkSlider(
            self.frame_conf,
            from_=0.1,
            to=0.9,
            number_of_steps=8,
            command=self.atualizar_conf
        )
        self.conf_slider.set(0.5)
        self.conf_slider.pack(side="left", padx=5, fill="x", expand=True)
        
        self.lbl_conf_valor = ctk.CTkLabel(self.frame_conf, text="0.5")
        self.lbl_conf_valor.pack(side="left", padx=5)
        
        # Lista de classes
        self.frame_classes = ctk.CTkFrame(self.frame)
        self.frame_classes.pack(pady=5, padx=10, fill="x")
        
        self.lbl_classes = ctk.CTkLabel(
            self.frame_classes,
            text="Classes detectadas aparecero aqui",
            wraplength=500
        )
        self.lbl_classes.pack()
    
    def atualizar_conf(self, valor):
        self.lbl_conf_valor.configure(text=f"{valor:.1f}")
        if hasattr(self.ferramenta, 'model') and self.ferramenta.model:
            self.ferramenta.model.conf = valor
    
    def update_frame(self, frame):
        if frame is not None:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img.thumbnail((800, 600))
            img_tk = ImageTk.PhotoImage(img)
            self.lbl_video.configure(image=img_tk, text="")
            self.lbl_video.image = img_tk
    
    def iniciar_webcam(self):
        self.ferramenta.iniciar_webcam()
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
        self.ferramenta.parar_webcam()
        self.btn_iniciar.configure(state="normal")
        self.btn_parar.configure(state="disabled")
        self.btn_foto.configure(state="disabled")
        self.lbl_video.configure(image="", text="Webcam parada")
    
    def processar_imagem(self):
        caminho = filedialog.askopenfilename(
            filetypes=[("Imagens", "*.jpg *.jpeg *.png")]
        )
        if caminho:
            frame, results = self.ferramenta.processar_imagem(caminho)
            if frame is not None:
                # Mostra resultado
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                img.thumbnail((800, 600))
                img_tk = ImageTk.PhotoImage(img)
                self.lbl_video.configure(image=img_tk, text="")
                self.lbl_video.image = img_tk
                
                # Mostra classes detectadas
                if results and len(results.xyxy[0]) > 0:
                    classes = []
                    for det in results.xyxy[0]:
                        cls = int(det[5])
                        conf = det[4]
                        classes.append(f"{self.ferramenta.nomes_classes[cls]} ({conf:.2f})")
                    self.lbl_classes.configure(text="Detectado: " + ", ".join(classes))
                else:
                    self.lbl_classes.configure(text="Nenhum objeto detectado")
    
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
    app = InterfaceDetectarObjetos()
    app.rodar()
