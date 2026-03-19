# Ferramenta: Cortar/Editar Vdeo
# Usa MoviePy (CPU)

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.modulos.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS

from moviepy import VideoFileClip, concatenate_videoclips
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading

class FerramentaCortarVideo:
    def __init__(self):
        self.video = None
        self.caminho_video = None
    
    def carregar_video(self, caminho):
        """Carrega vdeo para edio"""
        try:
            self.video = VideoFileClip(caminho)
            self.caminho_video = caminho
            return {
                "duracao": self.video.duration,
                "fps": self.video.fps,
                "largura": self.video.size[0],
                "altura": self.video.size[1]
            }
        except Exception as e:
            return None
    
    def cortar(self, inicio, fim, pasta_saida=None, nome_personalizado=None):
        """Corta vdeo entre início e fim (segundos)"""
        if self.video is None:
            return None, "Vdeo no carregado"
        
        try:
            # Corta
            clip_cortado = self.video.subclipped(inicio, fim)
            
            # Define nome
            if not pasta_saida:
                pasta_saida = PASTA_SAIDAS
            
            if nome_personalizado:
                nome_arquivo = f"{nome_personalizado}.mp4"
            else:
                nome_original = Path(self.caminho_video).stem
                nome_arquivo = f"{nome_original}_cortado_{int(início)}-{int(fim)}.mp4"
            
            caminho_saida = Path(pasta_saida) / nome_arquivo
            
            # Salva
            clip_cortado.write_videofile(
                str(caminho_saida),
                codec='libx264',
                audio_codec='aac',
                logger=None
            )
            
            clip_cortado.close()
            
            return str(caminho_saida), "Sucesso"
            
        except Exception as e:
            return None, str(e)
    
    def dividir(self, tempos, pasta_saida=None):
        """Divide vdeo em mltiplos clips nos tempos especificados"""
        if self.video is None:
            return None, "Vdeo no carregado"
        
        try:
            resultados = []
            tempos = [0] + tempos + [self.video.duration]
            
            for i in range(len(tempos) - 1):
                inicio = tempos[i]
                fim = tempos[i + 1]
                
                if fim - inicio < 0.5:  # Ignora muito curto
                    continue
                
                clip = self.video.subclipped(inicio, fim)
                nome_arquivo = f"parte_{i+1}_{int(início)}-{int(fim)}.mp4"
                caminho = Path(pasta_saida or PASTA_SAIDAS) / nome_arquivo
                
                clip.write_videofile(
                    str(caminho),
                    codec='libx264',
                    audio_codec='aac',
                    logger=None
                )
                
                resultados.append(str(caminho))
                clip.close()
            
            return resultados, "Sucesso"
            
        except Exception as e:
            return None, str(e)

class InterfaceCortarVideo(InterfaceBase):
    def __init__(self):
        super().__init__(" Cortar Vdeo", "700x600")
        self.ferramenta = FerramentaCortarVideo()
        self.caminho_video = None
        self.info_video = None
        self.marcadores = []
        self.setup_interface()
    
    def setup_interface(self):
        titulo = ctk.CTkLabel(
            self.frame,
            text=" Cortar e Editar Vdeo",
            font=("Arial", 24, "bold")
        )
        titulo.pack(pady=10)
        
        # Seleo
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
        
        # Info
        self.frame_info = ctk.CTkFrame(self.frame)
        self.frame_info.pack(pady=10, padx=10, fill="x")
        
        self.lbl_info = ctk.CTkLabel(self.frame_info, text="")
        self.lbl_info.pack(pady=5)
        
        # Abas
        self.tabview = ctk.CTkTabview(self.frame)
        self.tabview.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.tab_cortar = self.tabview.add("Cortar")
        self.tab_dividir = self.tabview.add("Dividir")
        
        # ===== ABA CORTAR =====
        # Sliders
        self.frame_sliders = ctk.CTkFrame(self.tab_cortar)
        self.frame_sliders.pack(pady=10, padx=10, fill="x")
        
        self.lbl_inicio = ctk.CTkLabel(self.frame_sliders, text="Incio:")
        self.lbl_inicio.pack()
        
        self.slider_inicio = ctk.CTkSlider(
            self.frame_sliders,
            from_=0,
            to=100,
            command=self.atualizar_inicio
        )
        self.slider_inicio.pack(pady=5, fill="x")
        
        self.lbl_inicio_valor = ctk.CTkLabel(
            self.frame_sliders,
            text="0.0s"
        )
        self.lbl_inicio_valor.pack()
        
        self.lbl_fim = ctk.CTkLabel(self.frame_sliders, text="Fim:")
        self.lbl_fim.pack(pady=(10,0))
        
        self.slider_fim = ctk.CTkSlider(
            self.frame_sliders,
            from_=0,
            to=100,
            command=self.atualizar_fim
        )
        self.slider_fim.pack(pady=5, fill="x")
        self.slider_fim.set(100)
        
        self.lbl_fim_valor = ctk.CTkLabel(
            self.frame_sliders,
            text="0.0s"
        )
        self.lbl_fim_valor.pack()
        
        # Preview tempo
        self.lbl_preview = ctk.CTkLabel(
            self.tab_cortar,
            text="",
            font=("Arial", 12)
        )
        self.lbl_preview.pack(pady=10)
        
        # Boto cortar
        self.btn_cortar = ctk.CTkButton(
            self.tab_cortar,
            text=" Cortar Vdeo",
            command=self.cortar,
            width=200,
            height=40,
            fg_color="green",
            state="disabled"
        )
        self.btn_cortar.pack(pady=10)
        
        # ===== ABA DIVIDIR =====
        self.lbl_marcadores = ctk.CTkLabel(
            self.tab_dividir,
            text="Marque os pontos de diviso (segundos):"
        )
        self.lbl_marcadores.pack(pady=5)
        
        self.frame_marcadores = ctk.CTkFrame(self.tab_dividir)
        self.frame_marcadores.pack(pady=5, padx=10, fill="x")
        
        self.entry_marcador = ctk.CTkEntry(
            self.frame_marcadores,
            placeholder_text="Tempo em segundos",
            width=100
        )
        self.entry_marcador.pack(side="left", padx=5)
        
        self.btn_adicionar = ctk.CTkButton(
            self.frame_marcadores,
            text=" Adicionar",
            command=self.adicionar_marcador,
            width=80
        )
        self.btn_adicionar.pack(side="left", padx=5)
        
        self.lista_marcadores = ctk.CTkTextbox(self.tab_dividir, height=100)
        self.lista_marcadores.pack(pady=5, padx=10, fill="x")
        
        self.btn_limpar = ctk.CTkButton(
            self.tab_dividir,
            text=" Limpar",
            command=self.limpar_marcadores,
            width=100
        )
        self.btn_limpar.pack(pady=5)
        
        self.btn_dividir = ctk.CTkButton(
            self.tab_dividir,
            text=" Dividir Vdeo",
            command=self.dividir,
            width=200,
            height=40,
            fg_color="green",
            state="disabled"
        )
        self.btn_dividir.pack(pady=10)
        
        # Barra de progresso comum
        self.progress = ctk.CTkProgressBar(self.frame, width=400)
        self.progress.pack(pady=5)
        self.progress.set(0)
    
    def selecionar_video(self):
        caminho = self.utils.selecionar_arquivo(
            "Selecione um vdeo",
            [("Vdeo", "*.mp4 *.avi *.mkv *.mov")]
        )
        if caminho:
            self.caminho_video = caminho
            self.lbl_video.configure(text=f"Vdeo: {Path(caminho).name}")
            
            info = self.ferramenta.carregar_video(caminho)
            if info:
                self.info_video = info
                self.lbl_info.configure(
                    text=f"Durao: {info['duracao']:.1f}s\n"
                         f"Resoluo: {info['largura']}x{info['altura']}"
                )
                
                # Atualiza sliders
                self.slider_inicio.configure(to=info['duracao'])
                self.slider_fim.configure(to=info['duracao'])
                self.slider_fim.set(info['duracao'])
                
                self.atualizar_inicio(0)
                self.atualizar_fim(info['duracao'])
                
                self.btn_cortar.configure(state="normal")
                self.btn_dividir.configure(state="normal")
    
    def atualizar_inicio(self, valor):
        if self.info_video:
            self.lbl_inicio_valor.configure(text=f"{valor:.1f}s")
            duracao = self.slider_fim.get() - valor
            self.lbl_preview.configure(
                text=f"Trecho: {duracao:.1f}s ({valor:.1f}s  {self.slider_fim.get():.1f}s)"
            )
    
    def atualizar_fim(self, valor):
        if self.info_video:
            self.lbl_fim_valor.configure(text=f"{valor:.1f}s")
            duracao = valor - self.slider_inicio.get()
            self.lbl_preview.configure(
                text=f"Trecho: {duracao:.1f}s ({self.slider_inicio.get():.1f}s  {valor:.1f}s)"
            )
    
    def adicionar_marcador(self):
        try:
            tempo = float(self.entry_marcador.get())
            if 0 < tempo < self.info_video['duracao']:
                self.marcadores.append(tempo)
                self.marcadores.sort()
                self.atualizar_lista_marcadores()
                self.entry_marcador.delete(0, 'end')
        except:
            pass
    
    def atualizar_lista_marcadores(self):
        self.lista_marcadores.delete('1.0', 'end')
        for i, t in enumerate(self.marcadores):
            self.lista_marcadores.insert('end', f"{i+1}. {t:.1f}s\n")
    
    def limpar_marcadores(self):
        self.marcadores = []
        self.lista_marcadores.delete('1.0', 'end')
    
    def cortar(self):
        def cortar_thread():
            self.btn_cortar.configure(state="disabled", text=" Cortando...")
            self.progress.set(0.3)
            
            caminho, msg = self.ferramenta.cortar(
                self.slider_inicio.get(),
                self.slider_fim.get()
            )
            
            self.progress.set(0.8)
            
            if caminho:
                self.utils.mostrar_info("Sucesso", f"Vdeo cortado:\n{caminho}")
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.progress.set(1)
            self.btn_cortar.configure(state="normal", text=" Cortar Vdeo")
        
        threading.Thread(target=cortar_thread).start()
    
    def dividir(self):
        if not self.marcadores:
            self.utils.mostrar_erro("Erro", "Adicione pelo menos um marcador")
            return
        
        def dividir_thread():
            self.btn_dividir.configure(state="disabled", text=" Dividindo...")
            self.progress.set(0.3)
            
            resultados, msg = self.ferramenta.dividir(self.marcadores)
            
            self.progress.set(0.8)
            
            if resultados:
                self.utils.mostrar_info(
                    "Sucesso",
                    f"{len(resultados)} partes criadas!\n"
                    f"Pasta: {Path(resultados[0]).parent}"
                )
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.progress.set(1)
            self.btn_dividir.configure(state="normal", text=" Dividir Vdeo")
        
        threading.Thread(target=dividir_thread).start()

if __name__ == "__main__":
    app = InterfaceCortarVideo()
    app.rodar()
