# Ferramenta: Transformar Vídeo em Anime (frame a frame)
# Usa AnimeGAN (2GB VRAM) + processamento sequencial

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.utils.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS, USAR_GPU

import cv2
import torch
from PIL import Image
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import numpy as np
from moviepy import VideoFileClip, ImageSequenceClip

class FerramentaAnimeVideo:
    def __init__(self, usar_gpu=True):
        self.usar_gpu = usar_gpu and torch.cuda.is_available()
        self.device = torch.device("cuda" if self.usar_gpu else "cpu")
        self.animegan = None
        self.face2paint = None
        self.carregar_modelo()
    
    def carregar_modelo(self):
        """Carrega modelo AnimeGAN (2GB VRAM)"""
        try:
            import sys
            animegan_path = Path(__file__).parent.parent / "animegan2-pytorch"
            sys.path.append(str(animegan_path))
            
            from model import generator
            from face2paint import face2paint as f2p
            
            self.animegan = generator(pretrained='face_paint_512_v2').to(self.device)
            self.animegan.eval()
            self.face2paint = f2p
            
            print(f"âœ… AnimeGAN carregado na {self.device}")
        except Exception as e:
            print(f"âŒ Erro AnimeGAN: {e}")
            self.animegan = None
    
    def frame_para_anime(self, frame):
        """Converte um frame para estilo anime"""
        if self.animegan is None:
            return frame
        
        try:
            # Converte OpenCV (BGR) para PIL (RGB)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(frame_rgb)
            
            # Aplica AnimeGAN
            with torch.no_grad():
                img_anime = self.face2paint(self.animegan, img_pil, size=512)
            
            # Converte de volta para OpenCV
            frame_anime = cv2.cvtColor(np.array(img_anime), cv2.COLOR_RGB2BGR)
            
            return frame_anime
        except Exception as e:
            print(f"Erro no frame: {e}")
            return frame
    
    def processar_video(self, caminho_video, pasta_saida=None, 
                        qualidade="media", fps_reducao=1):
        """
        Processa vídeo inteiro frame a frame
        
        qualidade: "baixa" (480p), "media" (720p), "alta" (1080p)
        fps_reducao: 1=mesmo FPS, 2=metade, etc
        """
        try:
            # Abre vídeo
            cap = cv2.VideoCapture(caminho_video)
            
            # Informações originais
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            largura = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            altura = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Define resolução
            if qualidade == "baixa":
                nova_largura = 640
                nova_altura = 480
            elif qualidade == "media":
                nova_largura = 854
                nova_altura = 480
            else:  # alta
                nova_largura = 1280
                nova_altura = 720
            
            # Pasta de saída
            if not pasta_saida:
                pasta_saida = PASTA_SAIDAS / f"anime_{Path(caminho_video).stem}"
            
            pasta_saida = Path(pasta_saida)
            pasta_saida.mkdir(exist_ok=True, parents=True)
            
            # Processa frames
            frames_processados = []
            frame_count = 0
            frames_pulados = fps_reducao
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Pula frames se necessário (reduz FPS)
                if frame_count % frames_pulados == 0:
                    # Redimensiona
                    frame_redim = cv2.resize(frame, (nova_largura, nova_altura))
                    
                    # Converte para anime
                    frame_anime = self.frame_para_anime(frame_redim)
                    
                    # Salva frame como imagem
                    nome_frame = f"frame_{frame_count:06d}.jpg"
                    caminho_frame = pasta_saida / nome_frame
                    cv2.imwrite(str(caminho_frame), frame_anime)
                    
                    frames_processados.append(str(caminho_frame))
                
                frame_count += 1
            
            cap.release()
            
            # Cria vídeo a partir dos frames
            fps_novo = fps / fps_reducao
            video_saida = pasta_saida / "video_anime.mp4"
            
            clip = ImageSequenceClip(frames_processados, fps=fps_novo)
            clip.write_videofile(
                str(video_saida),
                codec='libx264',
                audio_codec='aac',
                logger=None
            )
            
            return {
                "video": str(video_saida),
                "frames": len(frames_processados),
                "fps": fps_novo,
                "pasta": str(pasta_saida)
            }, "Sucesso"
            
        except Exception as e:
            return None, str(e)
    
    def processar_amostra(self, caminho_video, num_frames=10):
        """Processa apenas alguns frames para teste"""
        cap = cv2.VideoCapture(caminho_video)
        frames = []
        
        for i in range(num_frames):
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_anime = self.frame_para_anime(frame)
            frames.append(frame_anime)
        
        cap.release()
        return frames

class InterfaceAnimeVideo(InterfaceBase):
    def __init__(self):
        super().__init__("ðŸŽ¨ Transformar Vídeo em Anime", "750x650")
        self.ferramenta = FerramentaAnimeVideo(usar_gpu=USAR_GPU)
        self.caminho_video = None
        self.setup_interface()
    
    def setup_interface(self):
        titulo = ctk.CTkLabel(
            self.frame,
            text="ðŸŽ¬ Converter Vídeo para Estilo Anime",
            font=("Arial", 24, "bold")
        )
        titulo.pack(pady=10)
        
        # Status GPU
        status = "âœ… GPU Ativa (AnimeGAN - 2GB VRAM)" if self.ferramenta.usar_gpu else "âš ï¸ CPU (lento)"
        self.lbl_gpu = ctk.CTkLabel(self.frame, text=status)
        self.lbl_gpu.pack(pady=5)
        
        # Aviso
        aviso = ctk.CTkLabel(
            self.frame,
            text="âš ï¸ Processamento frame a frame - pode demorar!",
            text_color="orange"
        )
        aviso.pack(pady=5)
        
        # Seleção
        self.btn_video = ctk.CTkButton(
            self.frame,
            text="ðŸ“ Selecionar Vídeo",
            command=self.selecionar_video,
            width=200,
            height=40
        )
        self.btn_video.pack(pady=10)
        
        self.lbl_video = ctk.CTkLabel(
            self.frame,
            text="Nenhum vídeo selecionado"
        )
        self.lbl_video.pack(pady=5)
        
        # Preview
        self.frame_preview = ctk.CTkFrame(self.frame, height=200)
        self.frame_preview.pack(pady=10, padx=10, fill="x")
        
        self.lbl_preview = ctk.CTkLabel(
            self.frame_preview,
            text="Preview aparecerá aqui"
        )
        self.lbl_preview.pack(expand=True)
        
        # Botão teste
        self.btn_teste = ctk.CTkButton(
            self.frame,
            text="ðŸŽ¨ Testar (10 frames)",
            command=self.testar,
            width=150,
            state="disabled"
        )
        self.btn_teste.pack(pady=5)
        
        # Opções
        self.frame_opcoes = ctk.CTkFrame(self.frame)
        self.frame_opcoes.pack(pady=10, padx=10, fill="x")
        
        # Qualidade
        self.lbl_qualidade = ctk.CTkLabel(self.frame_opcoes, text="Qualidade:")
        self.lbl_qualidade.pack()
        
        self.qualidade_var = ctk.StringVar(value="media")
        
        self.radio_baixa = ctk.CTkRadioButton(
            self.frame_opcoes,
            text="Baixa (480p) - Mais rápido",
            variable=self.qualidade_var,
            value="baixa"
        )
        self.radio_baixa.pack(pady=2)
        
        self.radio_media = ctk.CTkRadioButton(
            self.frame_opcoes,
            text="Média (720p) - Equilibrado",
            variable=self.qualidade_var,
            value="media"
        )
        self.radio_media.pack(pady=2)
        
        self.radio_alta = ctk.CTkRadioButton(
            self.frame_opcoes,
            text="Alta (1080p) - Mais lento",
            variable=self.qualidade_var,
            value="alta"
        )
        self.radio_alta.pack(pady=2)
        
        # FPS
        self.frame_fps = ctk.CTkFrame(self.frame_opcoes)
        self.frame_fps.pack(pady=10, fill="x")
        
        self.lbl_fps = ctk.CTkLabel(self.frame_fps, text="Reduzir FPS:")
        self.lbl_fps.pack(side="left", padx=5)
        
        self.fps_var = ctk.IntVar(value=1)
        self.fps_combo = ctk.CTkComboBox(
            self.frame_fps,
            values=["1 (original)", "2 (metade)", "3 (1/3)", "4 (1/4)"],
            variable=self.fps_var,
            width=120,
            command=self.atualizar_fps
        )
        self.fps_combo.pack(side="left", padx=5)
        
        # Botão processar
        self.btn_processar = ctk.CTkButton(
            self.frame,
            text="ðŸŽ¬ Processar Vídeo Completo",
            command=self.processar,
            width=250,
            height=45,
            fg_color="green",
            state="disabled"
        )
        self.btn_processar.pack(pady=20)
        
        # Barra de progresso
        self.progress = ctk.CTkProgressBar(self.frame, width=400)
        self.progress.pack(pady=5)
        self.progress.set(0)
        
        # Estimativa
        self.lbl_estimativa = ctk.CTkLabel(
            self.frame,
            text="",
            text_color="gray"
        )
        self.lbl_estimativa.pack()
    
    def atualizar_fps(self, choice):
        # Extrai número da string
        valor = int(choice.split()[0])
        self.fps_var.set(valor)
    
    def selecionar_video(self):
        caminho = self.utils.selecionar_arquivo(
            "Selecione um vídeo",
            [("Vídeo", "*.mp4 *.avi *.mkv *.mov")]
        )
        if caminho:
            self.caminho_video = caminho
            self.lbl_video.configure(text=f"Vídeo: {Path(caminho).name}")
            self.btn_teste.configure(state="normal")
            self.btn_processar.configure(state="normal")
            
            # Estima tempo
            cap = cv2.VideoCapture(caminho)
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duracao = total_frames / fps
            cap.release()
            
            # 2 segundos por frame na GPU
            tempo_estimado = (total_frames / self.fps_var.get()) * 2 / 60
            self.lbl_estimativa.configure(
                text=f"Vídeo: {duracao:.1f}s, {total_frames} frames\n"
                     f"Tempo estimado: {tempo_estimado:.1f} minutos"
            )
    
    def testar(self):
        def testar_thread():
            self.btn_teste.configure(state="disabled", text="â³ Testando...")
            
            frames = self.ferramenta.processar_amostra(self.caminho_video, 5)
            
            if frames:
                # Mostra primeiro frame
                frame_anime = frames[0]
                frame_rgb = cv2.cvtColor(frame_anime, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                img.thumbnail((400, 200))
                
                from PIL import ImageTk
                img_tk = ImageTk.PhotoImage(img)
                self.lbl_preview.configure(image=img_tk, text="")
                self.lbl_preview.image = img_tk
                
                self.utils.mostrar_info("Teste", "Preview gerado com sucesso!")
            
            self.btn_teste.configure(state="normal", text="ðŸŽ¨ Testar")
        
        threading.Thread(target=testar_thread).start()
    
    def processar(self):
        def processar_thread():
            self.btn_processar.configure(state="disabled", text="â³ Processando...")
            self.progress.set(0.1)
            
            resultado, msg = self.ferramenta.processar_video(
                self.caminho_video,
                qualidade=self.qualidade_var.get(),
                fps_reducao=self.fps_var.get()
            )
            
            self.progress.set(0.9)
            
            if resultado:
                self.utils.mostrar_info(
                    "Sucesso",
                    f"Vídeo processado!\n"
                    f"Arquivo: {Path(resultado['video']).name}\n"
                    f"Frames: {resultado['frames']} @ {resultado['fps']:.1f}fps"
                )
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.progress.set(1)
            self.btn_processar.configure(state="normal", text="ðŸŽ¬ Processar Vídeo Completo")
        
        threading.Thread(target=processar_thread).start()

if __name__ == "__main__":
    app = InterfaceAnimeVideo()
    app.rodar()
