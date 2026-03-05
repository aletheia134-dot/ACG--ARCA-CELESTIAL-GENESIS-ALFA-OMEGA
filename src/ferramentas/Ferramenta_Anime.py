# Ferramenta: Foto â†’ Anime
# Modo 1: Manual (interface gráfica)
# Modo 2: IA explorando (linha de comando silencioso)
# Modo 3: IA a serviço (chamada por outra IA)

import sys
import os
from pathlib import Path

# Adiciona core ao path
sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.utils.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS, USAR_GPU

import torch
from PIL import Image
import customtkinter as ctk
from tkinter import filedialog, messagebox
import numpy as np

class FerramentaAnime:
    """Classe principal que faz o trabalho"""
    def __init__(self, usar_gpu=True):
        self.usar_gpu = usar_gpu and torch.cuda.is_available()
        self.device = torch.device("cuda" if self.usar_gpu else "cpu")
        self.modelo = None
        self.face2paint = None
        self.carregar_modelo()
        
    def carregar_modelo(self):
        """Carrega o modelo AnimeGAN (2GB de VRAM)"""
        try:
            # Importa funções do animegan
            import sys
            sys.path.append(str(Path(__file__).parent.parent / "animegan2-pytorch"))
            
            from model import generator
            from face2paint import face2paint as f2p
            
            # Carrega modelo (2GB)
            self.modelo = generator(pretrained='face_paint_512_v2').to(self.device)
            self.modelo.eval()
            
            # Função de pintura
            self.face2paint = f2p
            
            print(f"âœ… Modelo AnimeGAN carregado na {self.device}")
        except Exception as e:
            print(f"âŒ Erro ao carregar modelo: {e}")
            self.modelo = None
    
    def processar(self, caminho_imagem, tamanho=512):
        """Converte imagem para anime"""
        if self.modelo is None:
            return None, "Modelo não carregado"
        
        try:
            # Abre imagem
            img = Image.open(caminho_imagem).convert("RGB")
            
            # Converte para anime (2GB VRAM)
            with torch.no_grad():
                img_saida = self.face2paint(self.modelo, img, size=tamanho)
            
            return img_saida, "Sucesso"
        except Exception as e:
            return None, str(e)
    
    def processar_lote(self, pasta_entrada, pasta_saida):
        """Processa várias imagens"""
        resultados = []
        imagens = Path(pasta_entrada).glob("*.jpg")
        imagens = list(imagens) + list(Path(pasta_entrada).glob("*.png"))
        
        for i, img_path in enumerate(imagens):
            print(f"Processando {i+1}/{len(imagens)}: {img_path.name}")
            img_saida, msg = self.processar(str(img_path))
            
            if img_saida:
                nome_saida = f"anime_{img_path.stem}.png"
                img_saida.save(Path(pasta_saida) / nome_saida)
                resultados.append(f"âœ… {img_path.name} -> {nome_saida}")
            else:
                resultados.append(f"âŒ {img_path.name}: {msg}")
        
        return resultados

class InterfaceAnime(InterfaceBase):
    """Interface gráfica (MODO 1 - Manual)"""
    def __init__(self):
        super().__init__("ðŸŽ¨ Conversor Foto para Anime", "700x600")
        self.ferramenta = FerramentaAnime(usar_gpu=USAR_GPU)
        self.caminho_imagem = None
        self.setup_interface()
    
    def setup_interface(self):
        """Cria os elementos da interface"""
        # Título
        titulo = ctk.CTkLabel(
            self.frame, 
            text="ðŸŽ¨ Transformar Foto em Anime",
            font=("Arial", 20, "bold")
        )
        titulo.pack(pady=10)
        
        # Status GPU
        gpu_status = "âœ… GPU Ativa (GTX 1070)" if self.ferramenta.usar_gpu else "âš ï¸ CPU (mais lento)"
        self.lbl_gpu = ctk.CTkLabel(self.frame, text=gpu_status)
        self.lbl_gpu.pack(pady=5)
        
        # Botão selecionar imagem
        self.btn_imagem = ctk.CTkButton(
            self.frame,
            text="ðŸ“ Selecionar Imagem",
            command=self.selecionar_imagem,
            width=200,
            height=40
        )
        self.btn_imagem.pack(pady=10)
        
        # Label do arquivo selecionado
        self.lbl_arquivo = ctk.CTkLabel(
            self.frame, 
            text="Nenhum arquivo selecionado",
            wraplength=500
        )
        self.lbl_arquivo.pack(pady=5)
        
        # Frame de preview
        self.frame_preview = ctk.CTkFrame(self.frame)
        self.frame_preview.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.lbl_preview = ctk.CTkLabel(
            self.frame_preview,
            text="Preview aparecerá aqui",
            font=("Arial", 12)
        )
        self.lbl_preview.pack(expand=True)
        
        # Botão processar
        self.btn_processar = ctk.CTkButton(
            self.frame,
            text="âœ¨ Converter para Anime",
            command=self.processar,
            width=250,
            height=45,
            fg_color="green",
            hover_color="darkgreen",
            state="disabled"
        )
        self.btn_processar.pack(pady=10)
        
        # Opções
        self.frame_opcoes = ctk.CTkFrame(self.frame)
        self.frame_opcoes.pack(pady=5, fill="x")
        
        self.lbl_tamanho = ctk.CTkLabel(self.frame_opcoes, text="Tamanho:")
        self.lbl_tamanho.pack(side="left", padx=5)
        
        self.tamanho = ctk.CTkComboBox(
            self.frame_opcoes,
            values=["256", "512", "1024"],
            width=100
        )
        self.tamanho.pack(side="left", padx=5)
        self.tamanho.set("512")
        
        # Botão salvar
        self.btn_salvar = ctk.CTkButton(
            self.frame,
            text="ðŸ’¾ Salvar Imagem",
            command=self.salvar_imagem,
            width=200,
            state="disabled"
        )
        self.btn_salvar.pack(pady=5)
        
        self.imagem_processada = None
    
    def selecionar_imagem(self):
        caminho = self.utils.selecionar_arquivo(
            "Selecione uma imagem",
            [("Imagens", "*.jpg *.jpeg *.png *.bmp")]
        )
        if caminho:
            self.caminho_imagem = caminho
            self.lbl_arquivo.configure(text=f"Arquivo: {Path(caminho).name}")
            self.btn_processar.configure(state="normal")
    
    def processar(self):
        if not self.caminho_imagem:
            return
        
        self.btn_processar.configure(text="â³ Processando...", state="disabled")
        self.lbl_preview.configure(text="Processando... aguarde (2-3 segundos)")
        self.frame.update()
        
        # Processa
        img_saida, msg = self.ferramenta.processar(
            self.caminho_imagem,
            tamanho=int(self.tamanho.get())
        )
        
        if img_saida:
            self.imagem_processada = img_saida
            self.lbl_preview.configure(text="âœ… Imagem processada com sucesso!")
            self.btn_salvar.configure(state="normal")
            
            # Salva temporário para preview
            temp_path = Path("C:/Ferramentas_IA/temp/preview_anime.png")
            img_saida.save(temp_path)
        else:
            self.utils.mostrar_erro("Erro", f"Falha ao processar: {msg}")
            self.lbl_preview.configure(text="âŒ Erro no processamento")
        
        self.btn_processar.configure(text="âœ¨ Converter para Anime", state="normal")
    
    def salvar_imagem(self):
        if self.imagem_processada:
            caminho = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")]
            )
            if caminho:
                self.imagem_processada.save(caminho)
                self.utils.mostrar_info("Sucesso", f"Imagem salva em:\n{caminho}")

class ModoIA:
    """MODO 2 e 3 - Para IAs usarem"""
    def __init__(self):
        self.ferramenta = FerramentaAnime(usar_gpu=USAR_GPU)
        self.utils = Utils()
    
    def descobrir(self, pasta_teste):
        """MODO 2: IA explorando - testa a ferramenta em várias imagens"""
        resultados = []
        imagens = Path(pasta_teste).glob("*.jpg")
        
        for img in list(imagens)[:3]:  # Testa só 3 imagens
            resultado = self.processar_para_ia(str(img))
            resultados.append({
                "imagem": img.name,
                "resultado": resultado
            })
        
        return resultados
    
    def processar_para_ia(self, caminho_imagem):
        """MODO 3: IA a serviço - processa e retorna caminho do arquivo"""
        img_saida, msg = self.ferramenta.processar(caminho_imagem)
        
        if img_saida:
            nome_saida = self.utils.safe_filename("anime_ia", "png")
            caminho_saida = PASTA_SAIDAS / nome_saida
            img_saida.save(caminho_saida)
            return {
                "sucesso": True,
                "arquivo": str(caminho_saida),
                "mensagem": "Imagem convertida para anime"
            }
        else:
            return {
                "sucesso": False,
                "erro": msg
            }

# ===== PONTO DE ENTRADA =====
if __name__ == "__main__":
    # Verifica modo de execução
    if len(sys.argv) > 1:
        # MODO 2 ou 3: Chamado por IA ou linha de comando
        comando = sys.argv[1]
        ia = ModoIA()
        
        if comando == "--descobrir" and len(sys.argv) > 2:
            # IA explorando
            pasta = sys.argv[2]
            resultados = ia.descobrir(pasta)
            print(json.dumps(resultados, indent=2))
        
        elif comando == "--processar" and len(sys.argv) > 2:
            # IA a serviço
            imagem = sys.argv[2]
            resultado = ia.processar_para_ia(imagem)
            print(json.dumps(resultado, indent=2))
        
        else:
            print("Uso:")
            print("  python Ferramenta_Anime.py                     # Modo manual")
            print("  python Ferramenta_Anime.py --descobrir PASTA  # IA explorando")
            print("  python Ferramenta_Anime.py --processar IMAGEM # IA a serviço")
    else:
        # MODO 1: Manual (interface gráfica)
        app = InterfaceAnime()
        app.rodar()
