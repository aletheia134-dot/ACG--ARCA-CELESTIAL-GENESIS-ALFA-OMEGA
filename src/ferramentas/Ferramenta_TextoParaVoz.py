# Ferramenta: Texto para Voz (TTS)
# Usa Coqui TTS (2GB VRAM) ou gTTS (leve)

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
import time
import numpy as np
from PIL import Image
import io

# Opo 1: Coqui TTS (melhor qualidade, precisa de GPU)
try:
    from TTS.api import TTS
    TTS_AVAILABLE = True
except:
    TTS_AVAILABLE = False
    print("[AVISO] Coqui TTS no instalado. Usando gTTS (leve)")

# Opo 2: gTTS (leve, no precisa GPU)
try:
    from gtts import gTTS
    import pygame
    GTTS_AVAILABLE = True
except:
    GTTS_AVAILABLE = False
    print("[AVISO] gTTS no instalado")

class FerramentaTextoParaVoz:
    def __init__(self, usar_gpu=True, motor="auto"):
        self.usar_gpu = usar_gpu and TTS_AVAILABLE
        self.motor = motor  # "coqui", "gtts", "auto"
        self.tts = None
        self.vozes_disponiveis = []
        self.carregar_modelo()
    
    def carregar_modelo(self):
        """Carrega modelo TTS"""
        if self.motor == "auto":
            # Tenta Coqui primeiro, depois gTTS
            if TTS_AVAILABLE and self.usar_gpu:
                self._carregar_coqui()
            elif GTTS_AVAILABLE:
                self.motor = "gtts"
                print("[OK] Usando gTTS (leve, no precisa GPU)")
            else:
                print("[ERRO] Nenhum motor TTS disponível")
        
        elif self.motor == "coqui" and TTS_AVAILABLE:
            self._carregar_coqui()
        
        elif self.motor == "gtts" and GTTS_AVAILABLE:
            print("[OK] Usando gTTS")
    
    def _carregar_coqui(self):
        """Carrega Coqui TTS (2GB VRAM)"""
        try:
            self.tts = TTS("tts_models/pt/cv/vits")  # Portugus
            self.vozes_disponiveis = ["feminina", "masculina"]  # padrão
            self.motor = "coqui"
            print(f"[OK] Coqui TTS carregado (GPU: {self.usar_gpu})")
        except Exception as e:
            print(f"[ERRO] Erro Coqui: {e}")
            self.motor = "gtts" if GTTS_AVAILABLE else None
    
    def processar(self, texto, voz="default", arquivo_saida=None):
        """Converte texto para udio"""
        if self.motor == "coqui" and self.tts:
            return self._processar_coqui(texto, arquivo_saida)
        elif self.motor == "gtts":
            return self._processar_gtts(texto, arquivo_saida)
        else:
            return None, "Nenhum motor TTS disponível"
    
    def _processar_coqui(self, texto, arquivo_saida=None):
        """Usa Coqui TTS"""
        try:
            if not arquivo_saida:
                arquivo_saida = PASTA_SAIDAS / f"tts_coqui_{Utils.get_timestamp()}.wav"
            
            self.tts.tts_to_file(text=texto, file_path=str(arquivo_saida))
            return str(arquivo_saida), "Sucesso"
        except Exception as e:
            return None, str(e)
    
    def _processar_gtts(self, texto, arquivo_saida=None):
        """Usa gTTS (Google TTS)"""
        try:
            if not arquivo_saida:
                arquivo_saida = PASTA_SAIDAS / f"tts_gtts_{Utils.get_timestamp()}.mp3"
            
            tts = gTTS(text=texto, lang='pt', slow=False)
            tts.save(str(arquivo_saida))
            return str(arquivo_saida), "Sucesso"
        except Exception as e:
            return None, str(e)

class InterfaceTextoParaVoz(InterfaceBase):
    def __init__(self):
        super().__init__(" Texto para Voz (TTS)", "700x600")
        self.ferramenta = FerramentaTextoParaVoz(usar_gpu=USAR_GPU)
        self.audio_gerado = None
        self.setup_interface()
        
        # Inicializa pygame para reproduo
        if GTTS_AVAILABLE:
            pygame.mixer.init()
    
    def setup_interface(self):
        # Ttulo
        titulo = ctk.CTkLabel(
            self.frame,
            text=" Conversor de Texto para Fala",
            font=("Arial", 22, "bold")
        )
        titulo.pack(pady=10)
        
        # Status motor
        motor_status = f"[OK] Motor: {self.ferramenta.motor.upper()}"
        if self.ferramenta.motor == "coqui":
            motor_status += " (2GB VRAM)"
        elif self.ferramenta.motor == "gtts":
            motor_status += " (leve, online)"
        
        self.lbl_motor = ctk.CTkLabel(self.frame, text=motor_status)
        self.lbl_motor.pack(pady=5)
        
        # rea de texto
        self.lbl_texto = ctk.CTkLabel(self.frame, text="Digite o texto para converter:")
        self.lbl_texto.pack(pady=(10,0))
        
        self.texto_entry = ctk.CTkTextbox(self.frame, height=200)
        self.texto_entry.pack(pady=5, padx=10, fill="both", expand=True)
        
        # Exemplo
        self.btn_exemplo = ctk.CTkButton(
            self.frame,
            text=" Inserir Exemplo",
            command=self.inserir_exemplo,
            width=150
        )
        self.btn_exemplo.pack(pady=5)
        
        # Opes
        self.frame_opcoes = ctk.CTkFrame(self.frame)
        self.frame_opcoes.pack(pady=10, padx=10, fill="x")
        
        self.lbl_voz = ctk.CTkLabel(self.frame_opcoes, text="Voz:")
        self.lbl_voz.pack(side="left", padx=5)
        
        self.voz_var = ctk.StringVar(value="default")
        self.voz_combo = ctk.CTkComboBox(
            self.frame_opcoes,
            values=["default", "feminina", "masculina"],
            variable=self.voz_var,
            width=100
        )
        self.voz_combo.pack(side="left", padx=5)
        
        self.lbl_velocidade = ctk.CTkLabel(self.frame_opcoes, text="Velocidade:")
        self.lbl_velocidade.pack(side="left", padx=20)
        
        self.velocidade_var = ctk.DoubleVar(value=1.0)
        self.velocidade_slider = ctk.CTkSlider(
            self.frame_opcoes,
            from_=0.5,
            to=2.0,
            variable=self.velocidade_var,
            width=100
        )
        self.velocidade_slider.pack(side="left", padx=5)
        
        self.lbl_velocidade_valor = ctk.CTkLabel(
            self.frame_opcoes,
            text="1.0x"
        )
        self.lbl_velocidade_valor.pack(side="left", padx=5)
        
        def atualizar_velocidade(valor):
            self.lbl_velocidade_valor.configure(text=f"{valor:.1f}x")
        
        self.velocidade_slider.configure(command=atualizar_velocidade)
        
        # Botes
        self.frame_botoes = ctk.CTkFrame(self.frame)
        self.frame_botoes.pack(pady=10)
        
        self.btn_gerar = ctk.CTkButton(
            self.frame_botoes,
            text=" Gerar udio",
            command=self.gerar_audio,
            width=150,
            height=40,
            fg_color="green"
        )
        self.btn_gerar.pack(side="left", padx=5)
        
        self.btn_ouvir = ctk.CTkButton(
            self.frame_botoes,
            text=" Ouvir",
            command=self.ouvir_audio,
            width=100,
            height=40,
            state="disabled"
        )
        self.btn_ouvir.pack(side="left", padx=5)
        
        self.btn_parar = ctk.CTkButton(
            self.frame_botoes,
            text=" Parar",
            command=self.parar_audio,
            width=100,
            height=40,
            state="disabled"
        )
        self.btn_parar.pack(side="left", padx=5)
        
        self.btn_salvar = ctk.CTkButton(
            self.frame_botoes,
            text=" Salvar",
            command=self.salvar_audio,
            width=100,
            height=40,
            state="disabled"
        )
        self.btn_salvar.pack(side="left", padx=5)
        
        # Barra de progresso
        self.progress = ctk.CTkProgressBar(self.frame, width=400)
        self.progress.pack(pady=10)
        self.progress.set(0)
    
    def inserir_exemplo(self):
        exemplo = """Ol! Esta  uma demonstrao da ferramenta de texto para voz.
Estou feliz em poder falar com você atravs deste udio gerado por inteligncia artificial.
Espero que goste do resultado!"""
        self.texto_entry.delete('1.0', 'end')
        self.texto_entry.insert('1.0', exemplo)
    
    def gerar_audio(self):
        texto = self.texto_entry.get('1.0', 'end').strip()
        if not texto:
            self.utils.mostrar_erro("Erro", "Digite algum texto primeiro!")
            return
        
        def gerar():
            self.btn_gerar.configure(state="disabled", text=" Gerando...")
            self.progress.set(0.3)
            
            caminho, msg = self.ferramenta.processar(
                texto,
                voz=self.voz_var.get()
            )
            
            self.progress.set(0.8)
            
            if caminho:
                self.audio_gerado = caminho
                self.btn_ouvir.configure(state="normal")
                self.btn_salvar.configure(state="normal")
                self.utils.mostrar_info("Sucesso", f"udio gerado:\n{caminho}")
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.progress.set(1)
            self.btn_gerar.configure(state="normal", text=" Gerar udio")
        
        threading.Thread(target=gerar).start()
    
    def ouvir_audio(self):
        if self.audio_gerado and GTTS_AVAILABLE:
            try:
                pygame.mixer.music.load(self.audio_gerado)
                pygame.mixer.music.play()
                self.btn_ouvir.configure(state="disabled")
                self.btn_parar.configure(state="normal")
                
                # Monitora quando terminar
                def monitorar():
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                    self.btn_ouvir.configure(state="normal")
                    self.btn_parar.configure(state="disabled")
                
                threading.Thread(target=monitorar).start()
                
            except Exception as e:
                self.utils.mostrar_erro("Erro", f"No foi possível reproduzir: {e}")
    
    def parar_audio(self):
        if GTTS_AVAILABLE:
            pygame.mixer.music.stop()
            self.btn_ouvir.configure(state="normal")
            self.btn_parar.configure(state="disabled")
    
    def salvar_audio(self):
        if self.audio_gerado:
            ext = Path(self.audio_gerado).suffix
            caminho = filedialog.asksaveasfilename(
                defaultextension=ext,
                filetypes=[(f"{ext.upper()}", f"*{ext}")]
            )
            if caminho:
                import shutil
                shutil.copy(self.audio_gerado, caminho)
                self.utils.mostrar_info("Sucesso", f"udio salvo em:\n{caminho}")

if __name__ == "__main__":
    app = InterfaceTextoParaVoz()
    app.rodar()
