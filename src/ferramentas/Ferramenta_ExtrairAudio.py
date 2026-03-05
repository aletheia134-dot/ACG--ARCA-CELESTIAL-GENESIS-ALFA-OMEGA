# Ferramenta: Extrair Íudio de Vídeo (Vídeo â†’ MP3/WAV)
# Usa MoviePy (CPU)

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.utils.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS

from moviepy import VideoFileClip
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading

class FerramentaExtrairAudio:
    def __init__(self):
        self.video = None
        self.caminho_video = None
    
    def extrair(self, caminho_video, formato="mp3", bitrate="192k", 
                pasta_saida=None, nome_personalizado=None):
        """Extrai áudio do vídeo"""
        try:
            # Carrega vídeo
            video = VideoFileClip(caminho_video)
            
            # Define nome saída
            if not pasta_saida:
                pasta_saida = PASTA_SAIDAS
            
            if nome_personalizado:
                nome_arquivo = f"{nome_personalizado}.{formato}"
            else:
                nome_original = Path(caminho_video).stem
                nome_arquivo = f"{nome_original}_audio.{formato}"
            
            caminho_saida = Path(pasta_saida) / nome_arquivo
            
            # Extrai áudio
            if formato == "mp3":
                video.audio.write_audiofile(
                    str(caminho_saida),
                    codec='libmp3lame',
                    bitrate=bitrate,
                    logger=None
                )
            else:  # wav
                video.audio.write_audiofile(
                    str(caminho_saida),
                    codec='pcm_s16le',
                    logger=None
                )
            
            video.close()
            
            return {
                "arquivo": str(caminho_saida),
                "formato": formato,
                "tamanho": caminho_saida.stat().st_size if caminho_saida.exists() else 0
            }, "Sucesso"
            
        except Exception as e:
            return None, str(e)
    
    def get_info_video(self, caminho_video):
        """Obtém informações do vídeo"""
        try:
            video = VideoFileClip(caminho_video)
            info = {
                "duracao": video.duration,
                "fps": video.fps,
                "largura": video.size[0],
                "altura": video.size[1],
                "audio": video.audio is not None
            }
            video.close()
            return info
        except:
            return None

class InterfaceExtrairAudio(InterfaceBase):
    def __init__(self):
        super().__init__("ðŸŽµ Extrair Íudio de Vídeo", "700x550")
        self.ferramenta = FerramentaExtrairAudio()
        self.caminho_video = None
        self.setup_interface()
    
    def setup_interface(self):
        titulo = ctk.CTkLabel(
            self.frame,
            text="ðŸŽ¬ Extrair Íudio de Vídeo",
            font=("Arial", 24, "bold")
        )
        titulo.pack(pady=10)
        
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
        
        # Info vídeo
        self.frame_info = ctk.CTkFrame(self.frame)
        self.frame_info.pack(pady=10, padx=10, fill="x")
        
        self.lbl_info = ctk.CTkLabel(
            self.frame_info,
            text="",
            justify="left"
        )
        self.lbl_info.pack(pady=5)
        
        # Opções
        self.frame_opcoes = ctk.CTkFrame(self.frame)
        self.frame_opcoes.pack(pady=10, padx=10, fill="x")
        
        # Formato
        self.frame_formato = ctk.CTkFrame(self.frame_opcoes)
        self.frame_formato.pack(pady=5, fill="x")
        
        self.lbl_formato = ctk.CTkLabel(self.frame_formato, text="Formato:")
        self.lbl_formato.pack(side="left", padx=5)
        
        self.formato_var = ctk.StringVar(value="mp3")
        
        self.radio_mp3 = ctk.CTkRadioButton(
            self.frame_formato,
            text="MP3 (compactado)",
            variable=self.formato_var,
            value="mp3"
        )
        self.radio_mp3.pack(side="left", padx=5)
        
        self.radio_wav = ctk.CTkRadioButton(
            self.frame_formato,
            text="WAV (qualidade máxima)",
            variable=self.formato_var,
            value="wav"
        )
        self.radio_wav.pack(side="left", padx=5)
        
        # Qualidade
        self.frame_qualidade = ctk.CTkFrame(self.frame_opcoes)
        self.frame_qualidade.pack(pady=5, fill="x")
        
        self.lbl_qualidade = ctk.CTkLabel(self.frame_qualidade, text="Qualidade:")
        self.lbl_qualidade.pack(side="left", padx=5)
        
        self.bitrate_var = ctk.StringVar(value="192k")
        self.bitrate_combo = ctk.CTkComboBox(
            self.frame_qualidade,
            values=["128k", "192k", "256k", "320k"],
            variable=self.bitrate_var,
            width=80
        )
        self.bitrate_combo.pack(side="left", padx=5)
        
        # Nome personalizado
        self.frame_nome = ctk.CTkFrame(self.frame_opcoes)
        self.frame_nome.pack(pady=5, fill="x")
        
        self.lbl_nome = ctk.CTkLabel(self.frame_nome, text="Nome (opcional):")
        self.lbl_nome.pack(side="left", padx=5)
        
        self.nome_entry = ctk.CTkEntry(
            self.frame_nome,
            placeholder_text="Deixe em branco para usar nome original",
            width=250
        )
        self.nome_entry.pack(side="left", padx=5)
        
        # Pasta saída
        self.frame_pasta = ctk.CTkFrame(self.frame_opcoes)
        self.frame_pasta.pack(pady=5, fill="x")
        
        self.lbl_pasta = ctk.CTkLabel(self.frame_pasta, text="Salvar em:")
        self.lbl_pasta.pack(side="left", padx=5)
        
        self.pasta_var = ctk.StringVar(value=str(PASTA_SAIDAS))
        self.entry_pasta = ctk.CTkEntry(
            self.frame_pasta,
            textvariable=self.pasta_var,
            width=200
        )
        self.entry_pasta.pack(side="left", padx=5)
        
        self.btn_pasta = ctk.CTkButton(
            self.frame_pasta,
            text="ðŸ“",
            command=self.selecionar_pasta,
            width=30
        )
        self.btn_pasta.pack(side="left", padx=5)
        
        # Botão extrair
        self.btn_extrair = ctk.CTkButton(
            self.frame,
            text="ðŸŽµ Extrair Íudio",
            command=self.extrair,
            width=200,
            height=45,
            fg_color="green",
            state="disabled"
        )
        self.btn_extrair.pack(pady=20)
        
        # Barra de progresso
        self.progress = ctk.CTkProgressBar(self.frame, width=400)
        self.progress.pack(pady=5)
        self.progress.set(0)
    
    def selecionar_video(self):
        caminho = self.utils.selecionar_arquivo(
            "Selecione um vídeo",
            [("Vídeo", "*.mp4 *.avi *.mkv *.mov *.wmv *.flv")]
        )
        if caminho:
            self.caminho_video = caminho
            self.lbl_video.configure(text=f"Vídeo: {Path(caminho).name}")
            
            info = self.ferramenta.get_info_video(caminho)
            if info:
                self.lbl_info.configure(
                    text=f"Duração: {info['duracao']:.1f}s\n"
                         f"Resolução: {info['largura']}x{info['altura']}\n"
                         f"Íudio: {'âœ… Presente' if info['audio'] else 'âŒ Ausente'}"
                )
                self.btn_extrair.configure(
                    state="normal" if info['audio'] else "disabled"
                )
    
    def selecionar_pasta(self):
        pasta = self.utils.selecionar_pasta("Selecione a pasta de saída")
        if pasta:
            self.pasta_var.set(pasta)
    
    def extrair(self):
        def extrair_thread():
            self.btn_extrair.configure(state="disabled", text="â³ Extraindo...")
            self.progress.set(0.3)
            
            nome = self.nome_entry.get().strip()
            if not nome:
                nome = None
            
            resultado, msg = self.ferramenta.extrair(
                self.caminho_video,
                formato=self.formato_var.get(),
                bitrate=self.bitrate_var.get(),
                pasta_saida=self.pasta_var.get(),
                nome_personalizado=nome
            )
            
            self.progress.set(0.8)
            
            if resultado:
                tamanho_mb = resultado['tamanho'] / (1024 * 1024)
                self.utils.mostrar_info(
                    "Sucesso",
                    f"Íudio extraído!\n"
                    f"Arquivo: {Path(resultado['arquivo']).name}\n"
                    f"Tamanho: {tamanho_mb:.1f}MB"
                )
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.progress.set(1)
            self.btn_extrair.configure(state="normal", text="ðŸŽµ Extrair Íudio")
        
        threading.Thread(target=extrair_thread).start()

if __name__ == "__main__":
    app = InterfaceExtrairAudio()
    app.rodar()
