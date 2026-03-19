# Ferramenta: Extrair Frames de Vdeo (Vdeo  Imagens)
# Usa OpenCV (CPU/GPU leve)

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.modulos.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS

import cv2
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
from PIL import Image, ImageTk
import numpy as np

class FerramentaExtrairFrames:
    def __init__(self):
        self.video = None
        self.caminho_video = None
        self.total_frames = 0
        self.fps = 0
        self.duracao = 0
    
    def carregar_video(self, caminho):
        """Carrega vdeo para anlise"""
        try:
            self.video = cv2.VideoCapture(caminho)
            self.caminho_video = caminho
            self.total_frames = int(self.video.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.video.get(cv2.CAP_PROP_FPS)
            self.duracao = self.total_frames / self.fps if self.fps > 0 else 0
            return True, {
                "total_frames": self.total_frames,
                "fps": self.fps,
                "duracao": self.duracao,
                "largura": int(self.video.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "altura": int(self.video.get(cv2.CAP_PROP_FRAME_HEIGHT))
            }
        except Exception as e:
            return False, str(e)
    
    def extrair_frames(self, pasta_saida, metodo="todos", intervalo=1, 
                       frames_especificos=None, max_frames=0):
        """
        Extrai frames do vdeo
        
        metodos:
            "todos" - todos os frames
            "intervalo" - a cada N frames
            "segundos" - a cada N segundos
            "quantidade" - número fixo de frames
            "específicos" - lista de frames especficos
        """
        if self.video is None:
            return None, "Vdeo no carregado"
        
        try:
            pasta_saida = Path(pasta_saida)
            pasta_saida.mkdir(exist_ok=True, parents=True)
            
            frames_extraidos = []
            frame_count = 0
            salvo_count = 0
            
            # Reset vdeo
            self.video.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            # Determina quais frames extrair
            frames_para_extrair = set()
            
            if metodo == "todos":
                # Todos os frames
                pass
            
            elif metodo == "intervalo":
                # A cada N frames
                frames_para_extrair = set(range(0, self.total_frames, intervalo))
            
            elif metodo == "segundos":
                # A cada N segundos
                frame_intervalo = int(self.fps * intervalo)
                frames_para_extrair = set(range(0, self.total_frames, frame_intervalo))
            
            elif metodo == "quantidade":
                # Número fixo de frames
                if max_frames > 0:
                    step = max(1, self.total_frames // max_frames)
                    frames_para_extrair = set(range(0, self.total_frames, step))
            
            elif metodo == "específicos" and frames_especificos:
                frames_para_extrair = set(frames_especificos)
            
            while True:
                ret, frame = self.video.read()
                if not ret:
                    break
                
                deve_extrair = (
                    (metodo == "todos") or
                    (frame_count in frames_para_extrair)
                )
                
                if deve_extrair:
                    # Salva frame
                    nome_arquivo = f"frame_{frame_count:06d}.jpg"
                    caminho_completo = pasta_saida / nome_arquivo
                    cv2.imwrite(str(caminho_completo), frame)
                    frames_extraidos.append(str(caminho_completo))
                    salvo_count += 1
                
                frame_count += 1
                
                # Limite de frames
                if max_frames > 0 and salvo_count >= max_frames:
                    break
            
            self.video.release()
            
            return {
                "total_extraidos": salvo_count,
                "frames": frames_extraidos,
                "pasta": str(pasta_saida)
            }, "Sucesso"
            
        except Exception as e:
            return None, str(e)
    
    def extrair_frame_unico(self, numero_frame, pasta_saida):
        """Extrai um frame específico"""
        if self.video is None:
            return None, "Vdeo no carregado"
        
        try:
            self.video.set(cv2.CAP_PROP_POS_FRAMES, numero_frame)
            ret, frame = self.video.read()
            
            if ret:
                pasta_saida = Path(pasta_saida)
                pasta_saida.mkdir(exist_ok=True)
                nome_arquivo = f"frame_{numero_frame:06d}.jpg"
                caminho = pasta_saida / nome_arquivo
                cv2.imwrite(str(caminho), frame)
                return str(caminho), "Sucesso"
            else:
                return None, "Frame no encontrado"
                
        except Exception as e:
            return None, str(e)

class InterfaceExtrairFrames(InterfaceBase):
    def __init__(self):
        super().__init__(" Extrair Frames de Vdeo", "800x700")
        self.ferramenta = FerramentaExtrairFrames()
        self.caminho_video = None
        self.info_video = None
        self.setup_interface()
    
    def setup_interface(self):
        # Ttulo
        titulo = ctk.CTkLabel(
            self.frame,
            text=" Extrair Frames de Vdeo",
            font=("Arial", 24, "bold")
        )
        titulo.pack(pady=10)
        
        # Seleo de vdeo
        self.btn_video = ctk.CTkButton(
            self.frame,
            text=" Selecionar Vdeo",
            command=self.selecionar_video,
            width=200,
            height=40
        )
        self.btn_video.pack(pady=10)
        
        self.lbl_video = ctk.CTkLabel(
            self.frame,
            text="Nenhum vdeo selecionado"
        )
        self.lbl_video.pack(pady=5)
        
        # informações do vdeo
        self.frame_info = ctk.CTkFrame(self.frame)
        self.frame_info.pack(pady=10, padx=10, fill="x")
        
        self.lbl_info = ctk.CTkLabel(
            self.frame_info,
            text="",
            justify="left"
        )
        self.lbl_info.pack(pady=5)
        
        # Preview do vdeo
        self.frame_preview = ctk.CTkFrame(self.frame, width=320, height=180)
        self.frame_preview.pack(pady=10)
        
        self.lbl_preview = ctk.CTkLabel(
            self.frame_preview,
            text="Preview do vdeo"
        )
        self.lbl_preview.pack(expand=True)
        
        # Método de extrao
        self.lbl_metodo = ctk.CTkLabel(
            self.frame,
            text="Método de extrao:",
            font=("Arial", 14, "bold")
        )
        self.lbl_metodo.pack(pady=(10,0))
        
        self.metodo_var = ctk.StringVar(value="todos")
        
        self.frame_metodos = ctk.CTkFrame(self.frame)
        self.frame_metodos.pack(pady=5, padx=10, fill="x")
        
        metodos = [
            ("Todos os frames", "todos"),
            ("A cada N frames", "intervalo"),
            ("A cada N segundos", "segundos"),
            ("Número fixo de frames", "quantidade")
        ]
        
        for i, (texto, valor) in enumerate(metodos):
            radio = ctk.CTkRadioButton(
                self.frame_metodos,
                text=texto,
                variable=self.metodo_var,
                value=valor,
                command=self.atualizar_campos
            )
            radio.grid(row=i, column=0, padx=10, pady=2, sticky="w")
        
        # Campos dinmicos
        self.frame_campos = ctk.CTkFrame(self.frame)
        self.frame_campos.pack(pady=10, padx=10, fill="x")
        
        self.campo_valor = ctk.CTkEntry(
            self.frame_campos,
            placeholder_text="Valor",
            width=100
        )
        
        self.campo_max = ctk.CTkEntry(
            self.frame_campos,
            placeholder_text="Mx. frames (0=ilimitado)",
            width=150
        )
        self.campo_max.insert(0, "0")
        
        # Pasta de sada
        self.frame_saida = ctk.CTkFrame(self.frame)
        self.frame_saida.pack(pady=10, padx=10, fill="x")
        
        self.lbl_saida = ctk.CTkLabel(
            self.frame_saida,
            text="Pasta de sada:"
        )
        self.lbl_saida.pack(side="left", padx=5)
        
        self.pasta_saida_var = ctk.StringVar(value=str(PASTA_SAIDAS / "frames"))
        self.entry_saida = ctk.CTkEntry(
            self.frame_saida,
            textvariable=self.pasta_saida_var,
            width=300
        )
        self.entry_saida.pack(side="left", padx=5)
        
        self.btn_pasta = ctk.CTkButton(
            self.frame_saida,
            text="",
            command=self.selecionar_pasta,
            width=30
        )
        self.btn_pasta.pack(side="left", padx=5)
        
        # Boto processar
        self.btn_processar = ctk.CTkButton(
            self.frame,
            text=" Extrair Frames",
            command=self.processar,
            width=200,
            height=45,
            fg_color="green",
            state="disabled"
        )
        self.btn_processar.pack(pady=20)
        
        # Barra de progresso
        self.progress = ctk.CTkProgressBar(self.frame, width=400)
        self.progress.pack(pady=5)
        self.progress.set(0)
    
    def atualizar_campos(self):
        # Limpa campos
        for widget in self.frame_campos.winfo_children():
            widget.destroy()
        
        metodo = self.metodo_var.get()
        
        if metodo == "intervalo":
            ctk.CTkLabel(self.frame_campos, text="A cada:").pack(side="left", padx=5)
            self.campo_valor = ctk.CTkEntry(self.frame_campos, width=80)
            self.campo_valor.pack(side="left", padx=5)
            self.campo_valor.insert(0, "10")
            ctk.CTkLabel(self.frame_campos, text="frames").pack(side="left")
        
        elif metodo == "segundos":
            ctk.CTkLabel(self.frame_campos, text="A cada:").pack(side="left", padx=5)
            self.campo_valor = ctk.CTkEntry(self.frame_campos, width=80)
            self.campo_valor.pack(side="left", padx=5)
            self.campo_valor.insert(0, "1")
            ctk.CTkLabel(self.frame_campos, text="segundos").pack(side="left")
        
        elif metodo == "quantidade":
            ctk.CTkLabel(self.frame_campos, text="Extrair:").pack(side="left", padx=5)
            self.campo_valor = ctk.CTkEntry(self.frame_campos, width=80)
            self.campo_valor.pack(side="left", padx=5)
            self.campo_valor.insert(0, "10")
            ctk.CTkLabel(self.frame_campos, text="frames no total").pack(side="left")
        
        # Campo max sempre
        ctk.CTkLabel(self.frame_campos, text=" | Máximo:").pack(side="left", padx=(20,5))
        self.campo_max = ctk.CTkEntry(self.frame_campos, width=80)
        self.campo_max.pack(side="left", padx=5)
        self.campo_max.insert(0, "0")
    
    def selecionar_video(self):
        caminho = self.utils.selecionar_arquivo(
            "Selecione um vdeo",
            [("Vdeo", "*.mp4 *.avi *.mkv *.mov *.wmv")]
        )
        if caminho:
            self.caminho_video = caminho
            self.lbl_video.configure(text=f"Vdeo: {Path(caminho).name}")
            
            sucesso, info = self.ferramenta.carregar_video(caminho)
            if sucesso:
                self.info_video = info
                self.lbl_info.configure(
                    text=f"Durao: {info['duracao']:.1f}s\n"
                         f"Frames: {info['total_frames']} @ {info['fps']:.2f}fps\n"
                         f"Resoluo: {info['largura']}x{info['altura']}"
                )
                self.btn_processar.configure(state="normal")
                
                # Preview primeiro frame
                self.ferramenta.video.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.ferramenta.video.read()
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    img.thumbnail((320, 180))
                    img_tk = ImageTk.PhotoImage(img)
                    self.lbl_preview.configure(image=img_tk, text="")
                    self.lbl_preview.image = img_tk
            else:
                self.utils.mostrar_erro("Erro", info)
    
    def selecionar_pasta(self):
        pasta = self.utils.selecionar_pasta("Selecione a pasta de sada")
        if pasta:
            self.pasta_saida_var.set(pasta)
    
    def processar(self):
        def processar_thread():
            self.btn_processar.configure(state="disabled", text=" Extraindo...")
            self.progress.set(0.2)
            
            metodo = self.metodo_var.get()
            valor = 1
            if hasattr(self, 'campo_valor') and self.campo_valor.get():
                try:
                    valor = float(self.campo_valor.get())
                except:
                    valor = 1
            
            max_frames = 0
            if self.campo_max.get():
                try:
                    max_frames = int(self.campo_max.get())
                except:
                    max_frames = 0
            
            self.progress.set(0.4)
            
            resultado, msg = self.ferramenta.extrair_frames(
                self.pasta_saida_var.get(),
                metodo=metodo,
                intervalo=valor if metodo == "intervalo" else 1,
                max_frames=max_frames
            )
            
            self.progress.set(0.8)
            
            if resultado:
                self.utils.mostrar_info(
                    "Sucesso",
                    f"{resultado['total_extraidos']} frames extrados!\n"
                    f"Pasta: {resultado['pasta']}"
                )
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.progress.set(1)
            self.btn_processar.configure(state="normal", text=" Extrair Frames")
        
        threading.Thread(target=processar_thread).start()

if __name__ == "__main__":
    app = InterfaceExtrairFrames()
    app.rodar()
