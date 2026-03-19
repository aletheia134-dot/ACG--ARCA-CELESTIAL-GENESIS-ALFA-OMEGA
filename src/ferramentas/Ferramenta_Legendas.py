# Ferramenta: Gerar Legendas Automticas (Vdeo  SRT)
# Usa Whisper + MoviePy (2GB VRAM)

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.modulos.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS, USAR_GPU

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
from moviepy import VideoFileClip
from faster_whisper import WhisperModel
import time

class FerramentaLegendas:
    def __init__(self, usar_gpu=True):
        self.usar_gpu = usar_gpu
        self.model = None
        self.carregar_modelo()
    
    def carregar_modelo(self, tamanho="tiny"):
        """Carrega modelo Whisper"""
        try:
            device = "cuda" if self.usar_gpu else "cpu"
            compute_type = "float16" if self.usar_gpu else "int8"
            
            self.model = WhisperModel(
                tamanho,
                device=device,
                compute_type=compute_type,
                download_root=str(Path("C:/Ferramentas_IA/modelos/whisper"))
            )
            print(f"[OK] Whisper {tamanho} carregado")
        except Exception as e:
            print(f"[ERRO] Erro Whisper: {e}")
    
    def extrair_audio(self, caminho_video):
        """Extrai udio do vdeo"""
        try:
            video = VideoFileClip(caminho_video)
            audio_path = PASTA_SAIDAS / f"audio_temp_{Utils.get_timestamp()}.wav"
            video.audio.write_audiofile(str(audio_path), logger=None)
            video.close()
            return audio_path, None
        except Exception as e:
            return None, str(e)
    
    def gerar_legendas(self, caminho_video, idioma="pt", formato="srt"):
        """Gera legendas do vdeo"""
        if self.model is None:
            self.carregar_modelo()
        
        try:
            # Extrai udio
            audio_path, erro = self.extrair_audio(caminho_video)
            if erro:
                return None, erro
            
            # Transcreve
            segments, info = self.model.transcribe(
                str(audio_path),
                language=idioma,
                beam_size=5,
                vad_filter=True
            )
            
            # Gera legendas
            legendas = []
            for segment in segments:
                legendas.append({
                    "início": segment.start,
                    "fim": segment.end,
                    "texto": segment.text
                })
            
            # Remove udio temporrio
            audio_path.unlink()
            
            return legendas, info
            
        except Exception as e:
            return None, str(e)
    
    def salvar_srt(self, legendas, caminho_saida):
        """Salva legendas no formato SRT"""
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            for i, leg in enumerate(legendas, 1):
                inicio = self._format_timestamp(leg["início"])
                fim = self._format_timestamp(leg["fim"])
                f.write(f"{i}\n")
                f.write(f"{início} --> {fim}\n")
                f.write(f"{leg['texto']}\n\n")
    
    def salvar_txt(self, legendas, caminho_saida):
        """Salva apenas o texto das legendas"""
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            for leg in legendas:
                f.write(f"{leg['texto']}\n")
    
    def _format_timestamp(self, segundos):
        """Formata timestamp para SRT"""
        horas = int(segundos // 3600)
        minutos = int((segundos % 3600) // 60)
        segs = int(segundos % 60)
        miliseg = int((segundos - int(segundos)) * 1000)
        return f"{horas:02d}:{minutos:02d}:{segs:02d},{miliseg:03d}"

class InterfaceLegendas(InterfaceBase):
    def __init__(self):
        super().__init__(" Gerar Legendas Automticas", "700x600")
        self.ferramenta = FerramentaLegendas(usar_gpu=USAR_GPU)
        self.caminho_video = None
        self.legendas_geradas = None
        self.setup_interface()
    
    def setup_interface(self):
        titulo = ctk.CTkLabel(
            self.frame,
            text=" Gerar Legendas Automticas",
            font=("Arial", 24, "bold")
        )
        titulo.pack(pady=10)
        
        # Status GPU
        status = "[OK] GPU Ativa (Whisper)" if self.ferramenta.usar_gpu else "[AVISO] CPU"
        self.lbl_gpu = ctk.CTkLabel(self.frame, text=status)
        self.lbl_gpu.pack(pady=5)
        
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
        
        # Opes
        self.frame_opcoes = ctk.CTkFrame(self.frame)
        self.frame_opcoes.pack(pady=10, padx=10, fill="x")
        
        # Idioma
        self.frame_idioma = ctk.CTkFrame(self.frame_opcoes)
        self.frame_idioma.pack(pady=5, fill="x")
        
        self.lbl_idioma = ctk.CTkLabel(self.frame_idioma, text="Idioma:")
        self.lbl_idioma.pack(side="left", padx=5)
        
        self.idioma_var = ctk.StringVar(value="pt")
        self.idioma_combo = ctk.CTkComboBox(
            self.frame_idioma,
            values=["pt", "en", "es", "fr", "de", "it", "ja", "zh"],
            variable=self.idioma_var,
            width=80
        )
        self.idioma_combo.pack(side="left", padx=5)
        
        # Modelo Whisper
        self.frame_modelo = ctk.CTkFrame(self.frame_opcoes)
        self.frame_modelo.pack(pady=5, fill="x")
        
        self.lbl_modelo = ctk.CTkLabel(self.frame_modelo, text="Modelo:")
        self.lbl_modelo.pack(side="left", padx=5)
        
        self.modelo_var = ctk.StringVar(value="tiny")
        self.modelo_combo = ctk.CTkComboBox(
            self.frame_modelo,
            values=["tiny", "base", "small", "medium"],
            variable=self.modelo_var,
            width=100,
            command=self.trocar_modelo
        )
        self.modelo_combo.pack(side="left", padx=5)
        
        self.lbl_info_modelo = ctk.CTkLabel(
            self.frame_modelo,
            text="(tiny=1GB, small=2.5GB)"
        )
        self.lbl_info_modelo.pack(side="left", padx=5)
        
        # Formato sada
        self.frame_formato = ctk.CTkFrame(self.frame_opcoes)
        self.frame_formato.pack(pady=5, fill="x")
        
        self.lbl_formato = ctk.CTkLabel(self.frame_formato, text="Formato:")
        self.lbl_formato.pack(side="left", padx=5)
        
        self.formato_var = ctk.StringVar(value="srt")
        self.radio_srt = ctk.CTkRadioButton(
            self.frame_formato,
            text="SRT (Legendas)",
            variable=self.formato_var,
            value="srt"
        )
        self.radio_srt.pack(side="left", padx=5)
        
        self.radio_txt = ctk.CTkRadioButton(
            self.frame_formato,
            text="TXT (Apenas texto)",
            variable=self.formato_var,
            value="txt"
        )
        self.radio_txt.pack(side="left", padx=5)
        
        # Boto processar
        self.btn_processar = ctk.CTkButton(
            self.frame,
            text=" Gerar Legendas",
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
        
        # rea de preview
        self.frame_preview = ctk.CTkFrame(self.frame)
        self.frame_preview.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.lbl_preview = ctk.CTkLabel(
            self.frame_preview,
            text="Prvia das legendas aparecer aqui",
            wraplength=500
        )
        self.lbl_preview.pack(pady=5)
        
        self.texto_preview = ctk.CTkTextbox(self.frame_preview, height=150)
        self.texto_preview.pack(pady=5, padx=5, fill="both", expand=True)
        
        # Boto salvar
        self.btn_salvar = ctk.CTkButton(
            self.frame,
            text=" Salvar Legendas",
            command=self.salvar_legendas,
            width=150,
            state="disabled"
        )
        self.btn_salvar.pack(pady=5)
    
    def trocar_modelo(self, choice):
        self.ferramenta.carregar_modelo(choice)
    
    def selecionar_video(self):
        caminho = self.utils.selecionar_arquivo(
            "Selecione um vdeo",
            [("Vdeo", "*.mp4 *.avi *.mkv *.mov *.wmv")]
        )
        if caminho:
            self.caminho_video = caminho
            self.lbl_video.configure(text=f"Vdeo: {Path(caminho).name}")
            self.btn_processar.configure(state="normal")
    
    def processar(self):
        def processar_thread():
            self.btn_processar.configure(state="disabled", text=" Gerando legendas...")
            self.progress.set(0.2)
            
            # Atualiza modelo
            self.ferramenta.carregar_modelo(self.modelo_var.get())
            
            self.progress.set(0.3)
            
            legendas, info = self.ferramenta.gerar_legendas(
                self.caminho_video,
                idioma=self.idioma_var.get()
            )
            
            self.progress.set(0.8)
            
            if legendas:
                self.legendas_geradas = legendas
                
                # Preview
                preview = "\n".join([f"{l['texto']}" for l in legendas[:10]])
                if len(legendas) > 10:
                    preview += "\n..."
                
                self.texto_preview.delete('1.0', 'end')
                self.texto_preview.insert('1.0', preview)
                
                self.btn_salvar.configure(state="normal")
                
                # Info
                if info:
                    self.lbl_preview.configure(
                        text=f"Idioma detectado: {info.language} "
                             f"({info.language_probability:.2f})\n"
                             f"{len(legendas)} segmentos"
                    )
                
                self.utils.mostrar_info("Sucesso", "Legendas geradas!")
            else:
                self.utils.mostrar_erro("Erro", "Falha ao gerar legendas")
            
            self.progress.set(1)
            self.btn_processar.configure(state="normal", text=" Gerar Legendas")
        
        threading.Thread(target=processar_thread).start()
    
    def salvar_legendas(self):
        if self.legendas_geradas:
            ext = self.formato_var.get()
            caminho = filedialog.asksaveasfilename(
                defaultextension=f".{ext}",
                filetypes=[(f"{ext.upper()}", f"*.{ext}")]
            )
            if caminho:
                if ext == "srt":
                    self.ferramenta.salvar_srt(self.legendas_geradas, caminho)
                else:
                    self.ferramenta.salvar_txt(self.legendas_geradas, caminho)
                
                self.utils.mostrar_info("Sucesso", f"Legendas salvas em:\n{caminho}")

if __name__ == "__main__":
    app = InterfaceLegendas()
    app.rodar()
