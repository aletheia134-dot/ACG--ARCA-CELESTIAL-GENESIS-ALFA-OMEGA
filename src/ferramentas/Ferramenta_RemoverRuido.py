# Ferramenta: Remover Rudo de udio
# Usa noisereduce (CPU)

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.modulos.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS

import noisereduce as nr
import librosa
import soundfile as sf
import numpy as np
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class FerramentaRemoverRuido:
    def __init__(self):
        self.audio_original = None
        self.audio_limpo = None
        self.sr = None
    
    def carregar_audio(self, caminho):
        """Carrega arquivo de udio"""
        try:
            self.audio_original, self.sr = librosa.load(caminho, sr=None)
            return True, "udio carregado"
        except Exception as e:
            return False, str(e)
    
    def processar(self, intensidade=0.5, estacionario=True):
        """Remove rudo do udio"""
        if self.audio_original is None:
            return None, "Nenhum udio carregado"
        
        try:
            # Usa os primeiros 0.5s como amostra de rudo
            ruido_amostra = self.audio_original[:int(self.sr * 0.5)]
            
            # Aplica reduo de rudo
            self.audio_limpo = nr.reduce_noise(
                y=self.audio_original,
                sr=self.sr,
                y_noise=ruido_amostra,
                prop_decrease=intensidade,
                stationary=estacionario
            )
            
            return True, "Rudo removido"
        except Exception as e:
            return None, str(e)
    
    def salvar_audio(self, caminho_saida):
        """Salva udio processado"""
        if self.audio_limpo is not None:
            sf.write(caminho_saida, self.audio_limpo, self.sr)
            return True
        return False
    
    def get_waveform_data(self):
        """Retorna dados para visualizao"""
        if self.audio_original is not None and self.audio_limpo is not None:
            # Pega trechos para visualizao
            tamanho = min(len(self.audio_original), self.sr * 3)  # 3 segundos
            return (
                self.audio_original[:tamanho],
                self.audio_limpo[:tamanho],
                self.sr
            )
        return None, None, None

class InterfaceRemoverRuido(InterfaceBase):
    def __init__(self):
        super().__init__(" Remover Rudo de udio", "800x700")
        self.ferramenta = FerramentaRemoverRuido()
        self.caminho_audio = None
        self.setup_interface()
    
    def setup_interface(self):
        # Ttulo
        titulo = ctk.CTkLabel(
            self.frame,
            text=" Remover Rudo de udio",
            font=("Arial", 22, "bold")
        )
        titulo.pack(pady=10)
        
        # Boto selecionar
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
            text="Nenhum arquivo selecionado",
            wraplength=500
        )
        self.lbl_arquivo.pack(pady=5)
        
        # informações do udio
        self.frame_info = ctk.CTkFrame(self.frame)
        self.frame_info.pack(pady=10, padx=10, fill="x")
        
        self.lbl_info = ctk.CTkLabel(self.frame_info, text="")
        self.lbl_info.pack()
        
        # Controles
        self.frame_controles = ctk.CTkFrame(self.frame)
        self.frame_controles.pack(pady=10, padx=10, fill="x")
        
        self.lbl_intensidade = ctk.CTkLabel(
            self.frame_controles,
            text="Intensidade: 50%"
        )
        self.lbl_intensidade.pack()
        
        self.intensidade_slider = ctk.CTkSlider(
            self.frame_controles,
            from_=0.1,
            to=1.0,
            number_of_steps=9,
            command=self.atualizar_intensidade
        )
        self.intensidade_slider.set(0.5)
        self.intensidade_slider.pack(pady=5, fill="x")
        
        self.estacionario_var = ctk.BooleanVar(value=True)
        self.chk_estacionario = ctk.CTkCheckBox(
            self.frame_controles,
            text="Rudo estacionrio (constante)",
            variable=self.estacionario_var
        )
        self.chk_estacionario.pack(pady=5)
        
        self.btn_processar = ctk.CTkButton(
            self.frame_controles,
            text=" Remover Rudo",
            command=self.processar,
            width=150,
            height=40,
            fg_color="green",
            state="disabled"
        )
        self.btn_processar.pack(pady=10)
        
        # rea de visualizao
        self.frame_grafico = ctk.CTkFrame(self.frame)
        self.frame_grafico.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.lbl_grafico = ctk.CTkLabel(
            self.frame_grafico,
            text="Visualizao aparecer aps processamento"
        )
        self.lbl_grafico.pack(expand=True)
        
        # Botes salvar
        self.frame_botoes = ctk.CTkFrame(self.frame)
        self.frame_botoes.pack(pady=10)
        
        self.btn_salvar = ctk.CTkButton(
            self.frame_botoes,
            text=" Salvar udio Limpo",
            command=self.salvar_audio,
            width=150,
            height=40,
            state="disabled"
        )
        self.btn_salvar.pack()
    
    def atualizar_intensidade(self, valor):
        self.lbl_intensidade.configure(text=f"Intensidade: {int(valor*100)}%")
    
    def selecionar_audio(self):
        caminho = self.utils.selecionar_arquivo(
            "Selecione um udio",
            [("udio", "*.mp3 *.wav *.flac *.m4a")]
        )
        if caminho:
            self.caminho_audio = caminho
            self.lbl_arquivo.configure(text=f"Arquivo: {Path(caminho).name}")
            
            # Carrega e mostra info
            sucesso, msg = self.ferramenta.carregar_audio(caminho)
            if sucesso:
                duracao = len(self.ferramenta.audio_original) / self.ferramenta.sr
                self.lbl_info.configure(
                    text=f"Durao: {duracao:.1f}s | Sample rate: {self.ferramenta.sr}Hz"
                )
                self.btn_processar.configure(state="normal")
            else:
                self.utils.mostrar_erro("Erro", msg)
    
    def processar(self):
        def processar_thread():
            self.btn_processar.configure(state="disabled", text=" Processando...")
            
            resultado, msg = self.ferramenta.processar(
                intensidade=self.intensidade_slider.get(),
                estacionario=self.estacionario_var.get()
            )
            
            if resultado:
                self.mostrar_visualizacao()
                self.btn_salvar.configure(state="normal")
                self.utils.mostrar_info("Sucesso", "Rudo removido!")
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.btn_processar.configure(state="normal", text=" Remover Rudo")
        
        threading.Thread(target=processar_thread).start()
    
    def mostrar_visualizacao(self):
        # Limpa frame anterior
        for widget in self.frame_grafico.winfo_children():
            widget.destroy()
        
        # Pega dados
        orig, limpo, sr = self.ferramenta.get_waveform_data()
        if orig is not None:
            # Cria figura
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 4))
            
            time = np.arange(len(orig)) / sr
            
            ax1.plot(time, orig, color='red', alpha=0.7)
            ax1.set_title('udio Original (com rudo)')
            ax1.set_xlabel('Tempo (s)')
            ax1.set_ylabel('Amplitude')
            
            ax2.plot(time, limpo, color='green', alpha=0.7)
            ax2.set_title('udio Limpo (sem rudo)')
            ax2.set_xlabel('Tempo (s)')
            ax2.set_ylabel('Amplitude')
            
            plt.tight_layout()
            
            # Embed no tkinter
            canvas = FigureCanvasTkAgg(fig, self.frame_grafico)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def salvar_audio(self):
        caminho = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("WAV", "*.wav"), ("MP3", "*.mp3")]
        )
        if caminho:
            if self.ferramenta.salvar_audio(caminho):
                self.utils.mostrar_info("Sucesso", f"udio salvo em:\n{caminho}")

if __name__ == "__main__":
    app = InterfaceRemoverRuido()
    app.rodar()
