# Ferramenta: Converter Formatos de udio
# Usa pydub (leve, CPU)

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.modulos.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS

from pydub import AudioSegment
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading

class FerramentaConverterAudio:
    def __init__(self):
        self.audio = None
        self.caminho_original = None
        self.formatos_suportados = {
            "MP3": "mp3",
            "WAV": "wav",
            "FLAC": "flac",
            "OGG": "ogg",
            "M4A": "m4a",
            "AAC": "aac",
            "WMA": "wma"
        }
    
    def carregar_audio(self, caminho):
        """Carrega arquivo de udio"""
        try:
            self.audio = AudioSegment.from_file(caminho)
            self.caminho_original = caminho
            return True, {
                "duracao": len(self.audio) / 1000,
                "canais": self.audio.channels,
                "frame_rate": self.audio.frame_rate,
                "sample_width": self.audio.sample_width
            }
        except Exception as e:
            return False, str(e)
    
    def converter(self, formato_destino, bitrate="192k", pasta_saida=None):
        """Converte udio para outro formato"""
        if self.audio is None:
            return None, "Nenhum udio carregado"
        
        try:
            if not pasta_saida:
                pasta_saida = PASTA_SAIDAS
            
            nome_original = Path(self.caminho_original).stem
            arquivo_saida = Path(pasta_saida) / f"{nome_original}_convertido.{formato_destino}"
            
            # Exporta
            self.audio.export(
                str(arquivo_saida),
                format=formato_destino,
                bitrate=bitrate
            )
            
            return str(arquivo_saida), "Sucesso"
        except Exception as e:
            return None, str(e)
    
    def ajustar(self, volume_db=0, velocidade=1.0):
        """Ajusta volume e velocidade"""
        if self.audio is None:
            return None
        
        audio_ajustado = self.audio
        
        # Ajusta volume
        if volume_db != 0:
            audio_ajustado = audio_ajustado + volume_db
        
        # Ajusta velocidade
        if velocidade != 1.0:
            audio_ajustado = audio_ajustado._spawn(
                audio_ajustado.raw_data,
                overrides={"frame_rate": int(audio_ajustado.frame_rate * velocidade)}
            )
        
        return audio_ajustado

class InterfaceConverterAudio(InterfaceBase):
    def __init__(self):
        super().__init__(" Conversor de udio", "700x600")
        self.ferramenta = FerramentaConverterAudio()
        self.caminho_audio = None
        self.info_original = None
        self.setup_interface()
    
    def setup_interface(self):
        titulo = ctk.CTkLabel(
            self.frame,
            text=" Converter Formatos de udio",
            font=("Arial", 22, "bold")
        )
        titulo.pack(pady=10)
        
        # Seleo
        self.btn_audio = ctk.CTkButton(
            self.frame,
            text=" Selecionar udio",
            command=self.selecionar_audio,
            width=200,
            height=40
        )
        self.btn_audio.pack(pady=10)
        
        self.lbl_arquivo = ctk.CTkLabel(
            self.frame,
            text="Nenhum arquivo selecionado"
        )
        self.lbl_arquivo.pack(pady=5)
        
        # Info do udio
        self.frame_info = ctk.CTkFrame(self.frame)
        self.frame_info.pack(pady=10, padx=10, fill="x")
        
        self.lbl_info = ctk.CTkLabel(self.frame_info, text="")
        self.lbl_info.pack()
        
        # Frame converso
        self.frame_conversao = ctk.CTkFrame(self.frame)
        self.frame_conversao.pack(pady=10, padx=10, fill="x")
        
        self.lbl_converter = ctk.CTkLabel(
            self.frame_conversao,
            text="Converter para:",
            font=("Arial", 14, "bold")
        )
        self.lbl_converter.pack(pady=5)
        
        # Grid de formatos
        self.frame_formatos = ctk.CTkFrame(self.frame_conversao)
        self.frame_formatos.pack(pady=5)
        
        self.formato_var = ctk.StringVar(value="mp3")
        row, col = 0, 0
        for nome, ext in self.ferramenta.formatos_suportados.items():
            radio = ctk.CTkRadioButton(
                self.frame_formatos,
                text=nome,
                variable=self.formato_var,
                value=ext
            )
            radio.grid(row=row, column=col, padx=10, pady=2, sticky="w")
            col += 1
            if col > 2:
                col = 0
                row += 1
        
        # Bitrate
        self.frame_bitrate = ctk.CTkFrame(self.frame_conversao)
        self.frame_bitrate.pack(pady=5)
        
        self.lbl_bitrate = ctk.CTkLabel(self.frame_bitrate, text="Qualidade:")
        self.lbl_bitrate.pack(side="left", padx=5)
        
        self.bitrate_var = ctk.StringVar(value="192k")
        self.bitrate_combo = ctk.CTkComboBox(
            self.frame_bitrate,
            values=["128k", "192k", "256k", "320k"],
            variable=self.bitrate_var,
            width=80
        )
        self.bitrate_combo.pack(side="left", padx=5)
        
        # Frame ajustes
        self.frame_ajustes = ctk.CTkFrame(self.frame)
        self.frame_ajustes.pack(pady=10, padx=10, fill="x")
        
        self.lbl_ajustes = ctk.CTkLabel(
            self.frame_ajustes,
            text="Ajustes adicionais:",
            font=("Arial", 14, "bold")
        )
        self.lbl_ajustes.pack(pady=5)
        
        # Volume
        self.frame_volume = ctk.CTkFrame(self.frame_ajustes)
        self.frame_volume.pack(pady=5, fill="x")
        
        self.lbl_volume = ctk.CTkLabel(self.frame_volume, text="Volume (dB):")
        self.lbl_volume.pack(side="left", padx=5)
        
        self.volume_var = ctk.IntVar(value=0)
        self.volume_slider = ctk.CTkSlider(
            self.frame_volume,
            from_=-20,
            to=20,
            number_of_steps=40,
            variable=self.volume_var,
            width=200
        )
        self.volume_slider.pack(side="left", padx=5)
        
        self.lbl_volume_valor = ctk.CTkLabel(
            self.frame_volume,
            text="0 dB"
        )
        self.lbl_volume_valor.pack(side="left", padx=5)
        
        def atualizar_volume(valor):
            self.lbl_volume_valor.configure(text=f"{int(valor)} dB")
        
        self.volume_slider.configure(command=atualizar_volume)
        
        # Velocidade
        self.frame_velocidade = ctk.CTkFrame(self.frame_ajustes)
        self.frame_velocidade.pack(pady=5, fill="x")
        
        self.lbl_velocidade = ctk.CTkLabel(self.frame_velocidade, text="Velocidade:")
        self.lbl_velocidade.pack(side="left", padx=5)
        
        self.velocidade_var = ctk.DoubleVar(value=1.0)
        self.velocidade_slider = ctk.CTkSlider(
            self.frame_velocidade,
            from_=0.5,
            to=2.0,
            number_of_steps=15,
            variable=self.velocidade_var,
            width=200
        )
        self.velocidade_slider.pack(side="left", padx=5)
        
        self.lbl_velocidade_valor = ctk.CTkLabel(
            self.frame_velocidade,
            text="1.0x"
        )
        self.lbl_velocidade_valor.pack(side="left", padx=5)
        
        def atualizar_velocidade(valor):
            self.lbl_velocidade_valor.configure(text=f"{valor:.1f}x")
        
        self.velocidade_slider.configure(command=atualizar_velocidade)
        
        # Botes
        self.frame_botoes = ctk.CTkFrame(self.frame)
        self.frame_botoes.pack(pady=20)
        
        self.btn_converter = ctk.CTkButton(
            self.frame_botoes,
            text=" Converter",
            command=self.converter,
            width=150,
            height=40,
            fg_color="green",
            state="disabled"
        )
        self.btn_converter.pack()
    
    def selecionar_audio(self):
        caminho = self.utils.selecionar_arquivo(
            "Selecione um udio",
            [("udio", "*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.wma")]
        )
        if caminho:
            self.caminho_audio = caminho
            self.lbl_arquivo.configure(text=f"Arquivo: {Path(caminho).name}")
            
            sucesso, info = self.ferramenta.carregar_audio(caminho)
            if sucesso:
                self.info_original = info
                self.lbl_info.configure(
                    text=f"Durao: {info['duracao']:.1f}s | "
                         f"Canais: {info['canais']} | "
                         f"Taxa: {info['frame_rate']}Hz"
                )
                self.btn_converter.configure(state="normal")
            else:
                self.utils.mostrar_erro("Erro", info)
    
    def converter(self):
        def converter_thread():
            self.btn_converter.configure(state="disabled", text=" Convertendo...")
            
            # Aplica ajustes
            audio_ajustado = self.ferramenta.ajustar(
                volume_db=self.volume_var.get(),
                velocidade=self.velocidade_var.get()
            )
            
            if audio_ajustado:
                self.ferramenta.audio = audio_ajustado
            
            # Converte
            caminho, msg = self.ferramenta.converter(
                self.formato_var.get(),
                bitrate=self.bitrate_var.get()
            )
            
            if caminho:
                self.utils.mostrar_info("Sucesso", f"Convertido:\n{caminho}")
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.btn_converter.configure(state="normal", text=" Converter")
        
        threading.Thread(target=converter_thread).start()

if __name__ == "__main__":
    app = InterfaceConverterAudio()
    app.rodar()
