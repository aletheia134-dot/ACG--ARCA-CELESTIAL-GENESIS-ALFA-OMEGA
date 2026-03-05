# Ferramenta: Juntar Múltiplos Vídeos
# Usa MoviePy (CPU)

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.utils.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS

from moviepy import VideoFileClip, concatenate_videoclips
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading

class FerramentaJuntarVideos:
    def __init__(self):
        self.videos = []
    
    def adicionar_video(self, caminho):
        """Adiciona vídeo Í  lista"""
        try:
            video = VideoFileClip(caminho)
            self.videos.append({
                "caminho": caminho,
                "clip": video,
                "duracao": video.duration,
                "nome": Path(caminho).name
            })
            return True, None
        except Exception as e:
            return False, str(e)
    
    def juntar(self, metodo="concat", pasta_saida=None, nome_saida="video_compilado.mp4"):
        """Junta todos os vídeos"""
        if len(self.videos) < 2:
            return None, "Adicione pelo menos 2 vídeos"
        
        try:
            clips = [v["clip"] for v in self.videos]
            
            if metodo == "concat":
                # Concatenação simples
                final = concatenate_videoclips(clips, method="compose")
            else:
                # Transição (fade)
                from moviepy import vfx
                clips_com_transicao = []
                for i, clip in enumerate(clips):
                    if i > 0:
                        clip = clip.with_start(clips_com_transicao[i-1].end - 1)
                    clips_com_transicao.append(clip)
                
                final = concatenate_videoclips(clips_com_transicao)
            
            # Define caminho
            if not pasta_saida:
                pasta_saida = PASTA_SAIDAS
            
            caminho_saida = Path(pasta_saida) / nome_saida
            
            # Salva
            final.write_videofile(
                str(caminho_saida),
                codec='libx264',
                audio_codec='aac',
                logger=None
            )
            
            # Fecha clips
            final.close()
            for v in self.videos:
                v["clip"].close()
            
            return str(caminho_saida), "Sucesso"
            
        except Exception as e:
            return None, str(e)
    
    def limpar(self):
        """Limpa lista de vídeos"""
        for v in self.videos:
            v["clip"].close()
        self.videos = []

class InterfaceJuntarVideos(InterfaceBase):
    def __init__(self):
        super().__init__("ðŸŽ¬ Juntar Vídeos", "700x600")
        self.ferramenta = FerramentaJuntarVideos()
        self.setup_interface()
    
    def setup_interface(self):
        titulo = ctk.CTkLabel(
            self.frame,
            text="ðŸŽ¬ Juntar Múltiplos Vídeos",
            font=("Arial", 24, "bold")
        )
        titulo.pack(pady=10)
        
        # Lista de vídeos
        self.lbl_lista = ctk.CTkLabel(
            self.frame,
            text="Vídeos a serem juntados:",
            font=("Arial", 14, "bold")
        )
        self.lbl_lista.pack(pady=(10,0))
        
        self.frame_lista = ctk.CTkFrame(self.frame, height=200)
        self.frame_lista.pack(pady=5, padx=10, fill="x")
        
        self.lista_texto = ctk.CTkTextbox(self.frame_lista, height=150)
        self.lista_texto.pack(pady=5, padx=5, fill="both", expand=True)
        
        # Botões adicionar
        self.frame_botoes = ctk.CTkFrame(self.frame)
        self.frame_botoes.pack(pady=5)
        
        self.btn_adicionar = ctk.CTkButton(
            self.frame_botoes,
            text="ðŸ“ Adicionar Vídeo",
            command=self.adicionar_video,
            width=150
        )
        self.btn_adicionar.pack(side="left", padx=5)
        
        self.btn_remover = ctk.CTkButton(
            self.frame_botoes,
            text="ðŸ—‘ï¸ Remover Último",
            command=self.remover_ultimo,
            width=150
        )
        self.btn_remover.pack(side="left", padx=5)
        
        self.btn_limpar = ctk.CTkButton(
            self.frame_botoes,
            text="ðŸ§¹ Limpar Tudo",
            command=self.limpar_lista,
            width=150
        )
        self.btn_limpar.pack(side="left", padx=5)
        
        # Opções
        self.frame_opcoes = ctk.CTkFrame(self.frame)
        self.frame_opcoes.pack(pady=10, padx=10, fill="x")
        
        # Método
        self.lbl_metodo = ctk.CTkLabel(self.frame_opcoes, text="Método:")
        self.lbl_metodo.pack()
        
        self.metodo_var = ctk.StringVar(value="concat")
        
        self.radio_concat = ctk.CTkRadioButton(
            self.frame_opcoes,
            text="Concatenação simples",
            variable=self.metodo_var,
            value="concat"
        )
        self.radio_concat.pack(pady=2)
        
        self.radio_trans = ctk.CTkRadioButton(
            self.frame_opcoes,
            text="Com transição (fade)",
            variable=self.metodo_var,
            value="transicao"
        )
        self.radio_trans.pack(pady=2)
        
        # Nome saída
        self.frame_nome = ctk.CTkFrame(self.frame_opcoes)
        self.frame_nome.pack(pady=10, fill="x")
        
        self.lbl_nome = ctk.CTkLabel(self.frame_nome, text="Nome do arquivo:")
        self.lbl_nome.pack(side="left", padx=5)
        
        self.nome_entry = ctk.CTkEntry(
            self.frame_nome,
            placeholder_text="video_compilado.mp4",
            width=200
        )
        self.nome_entry.pack(side="left", padx=5)
        self.nome_entry.insert(0, "video_compilado.mp4")
        
        # Botão juntar
        self.btn_juntar = ctk.CTkButton(
            self.frame,
            text="ðŸŽ¬ Juntar Vídeos",
            command=self.juntar,
            width=200,
            height=45,
            fg_color="green",
            state="disabled"
        )
        self.btn_juntar.pack(pady=20)
        
        # Barra de progresso
        self.progress = ctk.CTkProgressBar(self.frame, width=400)
        self.progress.pack(pady=5)
        self.progress.set(0)
    
    def adicionar_video(self):
        caminhos = filedialog.askopenfilenames(
            title="Selecione os vídeos",
            filetypes=[("Vídeo", "*.mp4 *.avi *.mkv *.mov")]
        )
        
        for caminho in caminhos:
            sucesso, erro = self.ferramenta.adicionar_video(caminho)
            if sucesso:
                self.atualizar_lista()
            else:
                self.utils.mostrar_erro("Erro", f"Arquivo {Path(caminho).name}: {erro}")
        
        if len(self.ferramenta.videos) >= 2:
            self.btn_juntar.configure(state="normal")
    
    def remover_ultimo(self):
        if self.ferramenta.videos:
            self.ferramenta.videos[-1]["clip"].close()
            self.ferramenta.videos.pop()
            self.atualizar_lista()
        
        if len(self.ferramenta.videos) < 2:
            self.btn_juntar.configure(state="disabled")
    
    def limpar_lista(self):
        self.ferramenta.limpar()
        self.ferramenta.videos = []
        self.atualizar_lista()
        self.btn_juntar.configure(state="disabled")
    
    def atualizar_lista(self):
        self.lista_texto.delete('1.0', 'end')
        total = 0
        for i, v in enumerate(self.ferramenta.videos, 1):
            self.lista_texto.insert('end', f"{i}. {v['nome']} ({v['duracao']:.1f}s)\n")
            total += v['duracao']
        
        if self.ferramenta.videos:
            self.lista_texto.insert('end', f"\nTotal: {total:.1f}s")
    
    def juntar(self):
        def juntar_thread():
            self.btn_juntar.configure(state="disabled", text="â³ Juntando...")
            self.progress.set(0.2)
            
            nome = self.nome_entry.get().strip()
            if not nome:
                nome = "video_compilado.mp4"
            elif not nome.endswith('.mp4'):
                nome += '.mp4'
            
            self.progress.set(0.4)
            
            caminho, msg = self.ferramenta.juntar(
                metodo=self.metodo_var.get(),
                nome_saida=nome
            )
            
            self.progress.set(0.8)
            
            if caminho:
                self.utils.mostrar_info("Sucesso", f"Vídeos juntados:\n{caminho}")
                self.limpar_lista()
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.progress.set(1)
            self.btn_juntar.configure(state="normal", text="ðŸŽ¬ Juntar Vídeos")
        
        threading.Thread(target=juntar_thread).start()

if __name__ == "__main__":
    app = InterfaceJuntarVideos()
    app.rodar()
