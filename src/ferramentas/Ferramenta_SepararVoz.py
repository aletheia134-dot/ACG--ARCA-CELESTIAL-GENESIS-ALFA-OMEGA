# Ferramenta: Separar Voz de Instrumental (Spleeter)
# Usa Spleeter (2GB VRAM)

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
import shutil

try:
    from spleeter.separator import Separator
    from spleeter.audio.adapter import AudioAdapter
    SPLEETER_AVAILABLE = True
except:
    SPLEETER_AVAILABLE = False
    print("[AVISO] Spleeter no instalado")

class FerramentaSepararVoz:
    def __init__(self, usar_gpu=True):
        self.usar_gpu = usar_gpu
        self.separator = None
        self.carregar_modelo()
    
    def carregar_modelo(self, stems=2):
        """Carrega modelo Spleeter"""
        if not SPLEETER_AVAILABLE:
            print("[ERRO] Spleeter no disponível")
            return
        
        try:
            # stems: 2 (voz + acompanhamento) ou 4 (voz + baixo + bateria + outros)
            self.separator = Separator(f'spleeter:{stems}stems', multiprocess=False)
            print(f"[OK] Spleeter carregado (stems={stems})")
        except Exception as e:
            print(f"[ERRO] Erro Spleeter: {e}")
    
    def processar(self, caminho_audio, stems=2, pasta_saida=None):
        """Separa udio em componentes"""
        if self.separator is None:
            return None, "Modelo no carregado"
        
        try:
            if not pasta_saida:
                pasta_saida = PASTA_SAIDAS / f"separado_{Utils.get_timestamp()}"
            
            pasta_saida = Path(pasta_saida)
            pasta_saida.mkdir(exist_ok=True)
            
            # Processa
            self.separator.separate_to_file(
                str(caminho_audio),
                str(pasta_saida)
            )
            
            # Lista arquivos gerados
            arquivos = list(pasta_saida.glob("**/*.wav"))
            
            return {
                "pasta": str(pasta_saida),
                "arquivos": [str(f) for f in arquivos],
                "stems": stems
            }, "Sucesso"
            
        except Exception as e:
            return None, str(e)

class InterfaceSepararVoz(InterfaceBase):
    def __init__(self):
        super().__init__(" Separar Voz de Instrumental", "700x600")
        self.ferramenta = FerramentaSepararVoz(usar_gpu=USAR_GPU)
        self.caminho_audio = None
        self.resultado = None
        self.setup_interface()
    
    def setup_interface(self):
        titulo = ctk.CTkLabel(
            self.frame,
            text=" Separar Voz e Instrumental",
            font=("Arial", 22, "bold")
        )
        titulo.pack(pady=10)
        
        # Status
        status = "[OK] Spleeter disponível" if SPLEETER_AVAILABLE else "[ERRO] Spleeter no instalado"
        self.lbl_status = ctk.CTkLabel(self.frame, text=status)
        self.lbl_status.pack(pady=5)
        
        # Seleo
        self.btn_audio = ctk.CTkButton(
            self.frame,
            text=" Selecionar Msica",
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
        
        # Opes
        self.frame_opcoes = ctk.CTkFrame(self.frame)
        self.frame_opcoes.pack(pady=10, padx=10, fill="x")
        
        self.lbl_stems = ctk.CTkLabel(self.frame_opcoes, text="Separar em:")
        self.lbl_stems.pack()
        
        self.stems_var = ctk.IntVar(value=2)
        
        self.radio2 = ctk.CTkRadioButton(
            self.frame_opcoes,
            text="2 stems (Voz + Instrumental)",
            variable=self.stems_var,
            value=2
        )
        self.radio2.pack(pady=5)
        
        self.radio4 = ctk.CTkRadioButton(
            self.frame_opcoes,
            text="4 stems (Voz + Baixo + Bateria + Outros)",
            variable=self.stems_var,
            value=4
        )
        self.radio4.pack(pady=5)
        
        # Boto processar
        self.btn_processar = ctk.CTkButton(
            self.frame,
            text=" Separar udio",
            command=self.processar,
            width=200,
            height=40,
            fg_color="green",
            state="disabled"
        )
        self.btn_processar.pack(pady=20)
        
        # Barra de progresso
        self.progress = ctk.CTkProgressBar(self.frame, width=400)
        self.progress.pack(pady=10)
        self.progress.set(0)
        
        # rea de resultados
        self.frame_resultado = ctk.CTkFrame(self.frame)
        self.frame_resultado.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.lbl_resultado = ctk.CTkLabel(
            self.frame_resultado,
            text="Resultados aparecero aqui"
        )
        self.lbl_resultado.pack(expand=True)
    
    def selecionar_audio(self):
        caminho = self.utils.selecionar_arquivo(
            "Selecione uma msica",
            [("udio", "*.mp3 *.wav *.flac *.m4a")]
        )
        if caminho:
            self.caminho_audio = caminho
            self.lbl_arquivo.configure(text=f"Arquivo: {Path(caminho).name}")
            self.btn_processar.configure(state="normal")
    
    def processar(self):
        def processar_thread():
            self.btn_processar.configure(state="disabled", text=" Separando...")
            self.progress.set(0.3)
            
            self.ferramenta.carregar_modelo(stems=self.stems_var.get())
            
            self.progress.set(0.6)
            
            resultado, msg = self.ferramenta.processar(
                self.caminho_audio,
                stems=self.stems_var.get()
            )
            
            self.progress.set(0.9)
            
            if resultado:
                self.resultado = resultado
                self.mostrar_resultados(resultado)
                self.utils.mostrar_info("Sucesso", "Separao concluda!")
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.progress.set(1)
            self.btn_processar.configure(state="normal", text=" Separar udio")
        
        threading.Thread(target=processar_thread).start()
    
    def mostrar_resultados(self, resultado):
        # Limpa frame
        for widget in self.frame_resultado.winfo_children():
            widget.destroy()
        
        # Ttulo
        titulo = ctk.CTkLabel(
            self.frame_resultado,
            text=f"[OK] Separado em {resultado['stems']} stems",
            font=("Arial", 14, "bold")
        )
        titulo.pack(pady=5)
        
        # Lista arquivos
        for arquivo in resultado['arquivos']:
            nome = Path(arquivo).name
            frame_arquivo = ctk.CTkFrame(self.frame_resultado)
            frame_arquivo.pack(pady=2, padx=5, fill="x")
            
            lbl = ctk.CTkLabel(frame_arquivo, text=nome)
            lbl.pack(side="left", padx=5)
            
            btn = ctk.CTkButton(
                frame_arquivo,
                text=" Abrir Pasta",
                command=lambda p=arquivo: self.abrir_pasta(p),
                width=80
            )
            btn.pack(side="right", padx=5)
    
    def abrir_pasta(self, arquivo):
        import subprocess
        subprocess.run(f'explorer /select,"{arquivo}"')

if __name__ == "__main__":
    app = InterfaceSepararVoz()
    app.rodar()
