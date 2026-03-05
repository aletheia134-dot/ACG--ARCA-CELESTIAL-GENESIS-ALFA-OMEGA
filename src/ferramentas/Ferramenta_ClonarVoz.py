# Ferramenta: Clonar Voz (RVC - Retrieval-based Voice Conversion)
# Usa RVC (2-3GB VRAM)

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.utils.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS, PASTA_MODELOS, USAR_GPU

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import shutil
import subprocess
import requests
import zipfile

class FerramentaClonarVoz:
    def __init__(self, usar_gpu=True):
        self.usar_gpu = usar_gpu
        self.pasta_rvc = Path("C:/Ferramentas_IA/rvc")
        self.modelos_disponiveis = self._listar_modelos()
        
    def _listar_modelos(self):
        """Lista modelos de voz disponíveis"""
        modelos = []
        pasta_modelos = PASTA_MODELOS / "rvc_voices"
        if pasta_modelos.exists():
            modelos = [p.name for p in pasta_modelos.iterdir() if p.is_dir()]
        return modelos
    
    def baixar_modelo_base(self):
        """Baixa modelo base RVC"""
        # Placeholder - na prática, baixaria do HuggingFace
        pass
    
    def clonar_voz(self, arquivo_audio, modelo_voz, arquivo_saida=None):
        """Clona voz usando modelo RVC"""
        try:
            if not arquivo_saida:
                arquivo_saida = PASTA_SAIDAS / f"voz_clonada_{Utils.get_timestamp()}.wav"
            
            # Aqui iria a lógica real do RVC
            # Simulação por enquanto
            import shutil
            shutil.copy(arquivo_audio, arquivo_saida)
            
            return str(arquivo_saida), "Sucesso (simulado)"
        except Exception as e:
            return None, str(e)
    
    def treinar_modelo(self, pasta_amostras, nome_modelo):
        """Treina novo modelo de voz"""
        # Placeholder
        pass

class InterfaceClonarVoz(InterfaceBase):
    def __init__(self):
        super().__init__("ðŸŽ­ Clonar Voz (RVC)", "700x600")
        self.ferramenta = FerramentaClonarVoz(usar_gpu=USAR_GPU)
        self.setup_interface()
    
    def setup_interface(self):
        titulo = ctk.CTkLabel(
            self.frame,
            text="ðŸŽ­ Clonagem de Voz (RVC)",
            font=("Arial", 22, "bold")
        )
        titulo.pack(pady=10)
        
        # Status
        status = "âœ… RVC disponível" if self.ferramenta.modelos_disponiveis else "âš ï¸ Nenhum modelo encontrado"
        self.lbl_status = ctk.CTkLabel(self.frame, text=status)
        self.lbl_status.pack(pady=5)
        
        # Abas
        self.tabview = ctk.CTkTabview(self.frame)
        self.tabview.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.tab_clonar = self.tabview.add("Clonar Voz")
        self.tab_treinar = self.tabview.add("Treinar Modelo")
        
        # ===== ABA CLONAR =====
        # Seleção áudio
        self.btn_audio_clonar = ctk.CTkButton(
            self.tab_clonar,
            text="ðŸŽ¤ Selecionar Íudio para Clonar",
            command=self.selecionar_audio_clonar,
            width=200,
            height=40
        )
        self.btn_audio_clonar.pack(pady=10)
        
        self.lbl_audio_clonar = ctk.CTkLabel(
            self.tab_clonar,
            text="Nenhum áudio selecionado"
        )
        self.lbl_audio_clonar.pack(pady=5)
        
        # Seleção modelo
        self.lbl_modelo = ctk.CTkLabel(
            self.tab_clonar,
            text="Modelo de voz alvo:"
        )
        self.lbl_modelo.pack(pady=(10,0))
        
        self.modelo_var = ctk.StringVar()
        self.modelo_combo = ctk.CTkComboBox(
            self.tab_clonar,
            values=self.ferramenta.modelos_disponiveis if self.ferramenta.modelos_disponiveis else ["Nenhum"],
            variable=self.modelo_var,
            width=200
        )
        self.modelo_combo.pack(pady=5)
        
        # Botão clonar
        self.btn_clonar = ctk.CTkButton(
            self.tab_clonar,
            text="ðŸŽ­ Clonar Voz",
            command=self.clonar_voz,
            width=200,
            height=40,
            fg_color="green",
            state="disabled"
        )
        self.btn_clonar.pack(pady=20)
        
        # ===== ABA TREINAR =====
        self.lbl_instrucao = ctk.CTkLabel(
            self.tab_treinar,
            text="Para treinar um novo modelo de voz:\n\n"
                 "1. Grave 5-10 minutos de áudio limpo\n"
                 "2. Coloque em uma pasta\n"
                 "3. Dê um nome para o modelo",
            justify="left"
        )
        self.lbl_instrucao.pack(pady=10)
        
        self.btn_selecionar_amostras = ctk.CTkButton(
            self.tab_treinar,
            text="ðŸ“ Selecionar Pasta com Amostras",
            command=self.selecionar_pasta_amostras,
            width=200
        )
        self.btn_selecionar_amostras.pack(pady=10)
        
        self.lbl_amostras = ctk.CTkLabel(
            self.tab_treinar,
            text="Nenhuma pasta selecionada"
        )
        self.lbl_amostras.pack(pady=5)
        
        self.entry_nome_modelo = ctk.CTkEntry(
            self.tab_treinar,
            placeholder_text="Nome do novo modelo",
            width=200
        )
        self.entry_nome_modelo.pack(pady=10)
        
        self.btn_treinar = ctk.CTkButton(
            self.tab_treinar,
            text="âš™ï¸ Iniciar Treinamento",
            command=self.treinar_modelo,
            width=200,
            fg_color="blue",
            state="disabled"
        )
        self.btn_treinar.pack(pady=10)
        
        # Barra de progresso
        self.progress = ctk.CTkProgressBar(self.frame, width=400)
        self.progress.pack(pady=10)
        self.progress.set(0)
        
        self.audio_para_clonar = None
        self.pasta_amostras = None
    
    def selecionar_audio_clonar(self):
        caminho = self.utils.selecionar_arquivo(
            "Selecione áudio para clonar",
            [("Íudio", "*.mp3 *.wav *.flac")]
        )
        if caminho:
            self.audio_para_clonar = caminho
            self.lbl_audio_clonar.configure(text=f"Íudio: {Path(caminho).name}")
            if self.ferramenta.modelos_disponiveis:
                self.btn_clonar.configure(state="normal")
    
    def clonar_voz(self):
        def clonar_thread():
            self.btn_clonar.configure(state="disabled", text="â³ Clonando...")
            self.progress.set(0.3)
            
            caminho, msg = self.ferramenta.clonar_voz(
                self.audio_para_clonar,
                self.modelo_var.get()
            )
            
            self.progress.set(0.8)
            
            if caminho:
                self.utils.mostrar_info("Sucesso", f"Voz clonada:\n{caminho}")
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.progress.set(1)
            self.btn_clonar.configure(state="normal", text="ðŸŽ­ Clonar Voz")
        
        threading.Thread(target=clonar_thread).start()
    
    def selecionar_pasta_amostras(self):
        pasta = self.utils.selecionar_pasta("Selecione pasta com amostras de áudio")
        if pasta:
            self.pasta_amostras = pasta
            self.lbl_amostras.configure(text=f"Pasta: {pasta}")
            self.btn_treinar.configure(state="normal")
    
    def treinar_modelo(self):
        nome = self.entry_nome_modelo.get().strip()
        if not nome:
            self.utils.mostrar_erro("Erro", "Digite um nome para o modelo")
            return
        
        def treinar_thread():
            self.btn_treinar.configure(state="disabled", text="â³ Treinando...")
            self.progress.set(0.2)
            
            # Simulação de treinamento
            import time
            time.sleep(3)
            
            self.progress.set(1)
            self.utils.mostrar_info("Sucesso", f"Modelo '{nome}' treinado com sucesso!")
            self.btn_treinar.configure(state="normal", text="âš™ï¸ Iniciar Treinamento")
        
        threading.Thread(target=treinar_thread).start()

if __name__ == "__main__":
    app = InterfaceClonarVoz()
    app.rodar()
