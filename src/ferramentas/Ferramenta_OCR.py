# Ferramenta: OCR - Extrair texto de imagens
# Usa EasyOCR (leve, <1GB VRAM)

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.utils.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS, USAR_GPU, IDIOMAS_OCR

import easyocr
import cv2
import numpy as np
from PIL import Image
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading

class FerramentaOCR:
    def __init__(self, usar_gpu=True):
        self.usar_gpu = usar_gpu and self._check_cuda()
        self.reader = None
        self.idiomas = ['pt', 'en']  # português e inglês padrão
        self.carregar_modelo()
    
    def _check_cuda(self):
        """Verifica se CUDA está disponível para EasyOCR"""
        try:
            import torch
            return torch.cuda.is_available()
        except:
            return False
    
    def carregar_modelo(self, idiomas=None):
        """Carrega o modelo EasyOCR"""
        if idiomas:
            self.idiomas = idiomas
        
        try:
            self.reader = easyocr.Reader(
                self.idiomas,
                gpu=self.usar_gpu,
                model_storage_directory=str(Path("C:/Ferramentas_IA/modelos/easyocr")),
                download_enabled=True
            )
            print(f"âœ… EasyOCR carregado (GPU: {self.usar_gpu})")
        except Exception as e:
            print(f"âŒ Erro ao carregar EasyOCR: {e}")
            self.reader = None
    
    def processar(self, caminho_imagem, detalhado=False):
        """Extrai texto da imagem"""
        if self.reader is None:
            return None, "Modelo não carregado"
        
        try:
            # Lê imagem
            resultado = self.reader.readtext(
                caminho_imagem,
                paragraph=False,
                width_ths=0.7,
                height_ths=0.7
            )
            
            if detalhado:
                # Retorna com coordenadas
                textos = []
                for deteccao in resultado:
                    textos.append({
                        "texto": deteccao[1],
                        "confianca": float(deteccao[2]),
                        "bbox": deteccao[0]
                    })
                return textos, "Sucesso"
            else:
                # Só texto puro
                textos = [deteccao[1] for deteccao in resultado]
                return '\n'.join(textos), "Sucesso"
                
        except Exception as e:
            return None, str(e)
    
    def processar_lote(self, pasta_entrada, pasta_saida):
        """Processa várias imagens em lote"""
        resultados = []
        imagens = list(Path(pasta_entrada).glob("*.jpg")) + \
                  list(Path(pasta_entrada).glob("*.png")) + \
                  list(Path(pasta_entrada).glob("*.jpeg"))
        
        for i, img_path in enumerate(imagens):
            print(f"Processando {i+1}/{len(imagens)}: {img_path.name}")
            texto, msg = self.processar(str(img_path))
            
            if texto:
                nome_saida = f"ocr_{img_path.stem}.txt"
                with open(Path(pasta_saida) / nome_saida, 'w', encoding='utf-8') as f:
                    f.write(texto)
                resultados.append(f"âœ… {img_path.name} -> {nome_saida}")
            else:
                resultados.append(f"âŒ {img_path.name}: {msg}")
        
        return resultados

class InterfaceOCR(InterfaceBase):
    def __init__(self):
        super().__init__("ðŸ” OCR - Extrair Texto de Imagens", "700x600")
        self.ferramenta = FerramentaOCR(usar_gpu=USAR_GPU)
        self.caminho_imagem = None
        self.texto_extraido = None
        self.setup_interface()
    
    def setup_interface(self):
        # Título
        titulo = ctk.CTkLabel(
            self.frame,
            text="ðŸ“ Extrair Texto de Imagens (OCR)",
            font=("Arial", 22, "bold")
        )
        titulo.pack(pady=10)
        
        # Status GPU
        status = "âœ… GPU Ativa (GTX 1070)" if self.ferramenta.usar_gpu else "âš ï¸ CPU"
        self.lbl_gpu = ctk.CTkLabel(self.frame, text=status)
        self.lbl_gpu.pack(pady=5)
        
        # Seleção de idiomas
        self.frame_idiomas = ctk.CTkFrame(self.frame)
        self.frame_idiomas.pack(pady=10)
        
        self.lbl_idiomas = ctk.CTkLabel(self.frame_idiomas, text="Idiomas:")
        self.lbl_idiomas.pack(side="left", padx=5)
        
        self.idiomas_var = ctk.StringVar(value="pt,en")
        self.idiomas_entry = ctk.CTkEntry(
            self.frame_idiomas,
            textvariable=self.idiomas_var,
            width=150
        )
        self.idiomas_entry.pack(side="left", padx=5)
        
        self.btn_idiomas = ctk.CTkButton(
            self.frame_idiomas,
            text="Carregar",
            command=self.recarregar_idiomas,
            width=80
        )
        self.btn_idiomas.pack(side="left", padx=5)
        
        # Botão selecionar imagem
        self.btn_imagem = ctk.CTkButton(
            self.frame,
            text="ðŸ“ Selecionar Imagem",
            command=self.selecionar_imagem,
            width=200,
            height=40
        )
        self.btn_imagem.pack(pady=10)
        
        # Label arquivo
        self.lbl_arquivo = ctk.CTkLabel(
            self.frame,
            text="Nenhum arquivo selecionado",
            wraplength=500
        )
        self.lbl_arquivo.pack(pady=5)
        
        # Frame preview
        self.frame_preview = ctk.CTkFrame(self.frame, height=150)
        self.frame_preview.pack(pady=10, padx=10, fill="x")
        
        self.lbl_preview = ctk.CTkLabel(
            self.frame_preview,
            text="Preview da imagem aparecerá aqui",
            height=150
        )
        self.lbl_preview.pack(expand=True)
        
        # Botão processar
        self.btn_processar = ctk.CTkButton(
            self.frame,
            text="ðŸ” Extrair Texto",
            command=self.processar,
            width=200,
            height=40,
            fg_color="blue",
            hover_color="darkblue",
            state="disabled"
        )
        self.btn_processar.pack(pady=10)
        
        # Írea de texto resultado
        self.lbl_resultado = ctk.CTkLabel(self.frame, text="Texto extraído:")
        self.lbl_resultado.pack(pady=(10,0))
        
        self.texto_resultado = ctk.CTkTextbox(self.frame, height=150)
        self.texto_resultado.pack(pady=5, padx=10, fill="both", expand=True)
        
        # Botões salvar e copiar
        self.frame_botoes = ctk.CTkFrame(self.frame)
        self.frame_botoes.pack(pady=5)
        
        self.btn_copiar = ctk.CTkButton(
            self.frame_botoes,
            text="ðŸ“‹ Copiar",
            command=self.copiar_texto,
            width=100,
            state="disabled"
        )
        self.btn_copiar.pack(side="left", padx=5)
        
        self.btn_salvar = ctk.CTkButton(
            self.frame_botoes,
            text="ðŸ’¾ Salvar TXT",
            command=self.salvar_texto,
            width=100,
            state="disabled"
        )
        self.btn_salvar.pack(side="left", padx=5)
    
    def recarregar_idiomas(self):
        idiomas = [i.strip() for i in self.idiomas_var.get().split(',')]
        self.ferramenta.carregar_modelo(idiomas)
        messagebox.showinfo("Sucesso", f"Modelos carregados: {', '.join(idiomas)}")
    
    def selecionar_imagem(self):
        caminho = self.utils.selecionar_arquivo(
            "Selecione uma imagem",
            [("Imagens", "*.jpg *.jpeg *.png *.bmp")]
        )
        if caminho:
            self.caminho_imagem = caminho
            self.lbl_arquivo.configure(text=f"Arquivo: {Path(caminho).name}")
            self.btn_processar.configure(state="normal")
            
            # Preview da imagem
            from PIL import ImageTk
            img = Image.open(caminho)
            img.thumbnail((400, 150))
            img_tk = ImageTk.PhotoImage(img)
            self.lbl_preview.configure(image=img_tk, text="")
            self.lbl_preview.image = img_tk
    
    def processar(self):
        if not self.caminho_imagem:
            return
        
        self.btn_processar.configure(text="â³ Processando...", state="disabled")
        self.frame.update()
        
        texto, msg = self.ferramenta.processar(self.caminho_imagem)
        
        if texto:
            self.texto_extraido = texto
            self.texto_resultado.delete('1.0', 'end')
            self.texto_resultado.insert('1.0', texto)
            self.btn_copiar.configure(state="normal")
            self.btn_salvar.configure(state="normal")
        else:
            self.utils.mostrar_erro("Erro", f"Falha ao extrair: {msg}")
        
        self.btn_processar.configure(text="ðŸ” Extrair Texto", state="normal")
    
    def copiar_texto(self):
        self.frame.clipboard_clear()
        self.frame.clipboard_append(self.texto_resultado.get('1.0', 'end'))
        self.utils.mostrar_info("Copiado", "Texto copiado para área de transferência")
    
    def salvar_texto(self):
        if self.texto_extraido:
            caminho = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Texto", "*.txt")]
            )
            if caminho:
                with open(caminho, 'w', encoding='utf-8') as f:
                    f.write(self.texto_resultado.get('1.0', 'end'))
                self.utils.mostrar_info("Sucesso", f"Texto salvo em:\n{caminho}")

class ModoIA_OCR:
    def __init__(self):
        self.ferramenta = FerramentaOCR(usar_gpu=USAR_GPU)
        self.utils = Utils()
    
    def descobrir(self, pasta_teste):
        resultados = []
        imagens = list(Path(pasta_teste).glob("*.jpg"))[:5]
        
        for img_path in imagens:
            texto, _ = self.ferramenta.processar(str(img_path))
            if texto:
                resultados.append({
                    "imagem": img_path.name,
                    "texto": texto[:200] + "..." if len(texto) > 200 else texto
                })
        
        return resultados
    
    def processar_para_ia(self, caminho_imagem):
        texto, msg = self.ferramenta.processar(caminho_imagem)
        
        if texto:
            return {
                "sucesso": True,
                "texto": texto,
                "mensagem": "Texto extraído com sucesso"
            }
        else:
            return {
                "sucesso": False,
                "erro": msg
            }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        comando = sys.argv[1]
        ia = ModoIA_OCR()
        
        if comando == "--descobrir" and len(sys.argv) > 2:
            resultados = ia.descobrir(sys.argv[2])
            print(json.dumps(resultados, indent=2, ensure_ascii=False))
        
        elif comando == "--processar" and len(sys.argv) > 2:
            resultado = ia.processar_para_ia(sys.argv[2])
            print(json.dumps(resultado, indent=2, ensure_ascii=False))
        
        else:
            print("Uso: ...")
    else:
        app = InterfaceOCR()
        app.rodar()
