# Ferramenta: Remover Fundo de Imagens
# Usa rembg (1.5GB VRAM)

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.modulos.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS, USAR_GPU

from rembg import remove, new_session
from PIL import Image
import customtkinter as ctk
from tkinter import filedialog, messagebox
import numpy as np
import io

class FerramentaRemoverFundo:
    def __init__(self, usar_gpu=True):
        self.usar_gpu = usar_gpu
        self.session = None
        self.carregar_modelo()
    
    def carregar_modelo(self):
        """Carrega modelo U-Net para remoo de fundo"""
        try:
            # Modelo 'u2net'  o padrão (1.5GB VRAM)
            self.session = new_session(
                model_name="u2net",
                providers=['CUDAExecutionProvider'] if self.usar_gpu else ['CPUExecutionProvider']
            )
            print(f"[OK] Modelo rembg carregado (GPU: {self.usar_gpu})")
        except Exception as e:
            print(f"[ERRO] Erro ao carregar rembg: {e}")
            self.session = None
    
    def processar(self, caminho_imagem, saida_transparente=True, cor_fundo=None):
        """Remove fundo da imagem"""
        if self.session is None:
            return None, "Modelo no carregado"
        
        try:
            # Abre imagem
            with open(caminho_imagem, 'rb') as f:
                input_data = f.read()
            
            # Remove fundo
            output_data = remove(
                input_data,
                session=self.session,
                only_mask=False,
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10,
                alpha_matting_erode_size=10
            )
            
            # Converte para PIL
            output_image = Image.open(io.BytesIO(output_data)).convert("RGBA")
            
            # Se quiser fundo colorido em vez de transparente
            if cor_fundo and not saida_transparente:
                fundo = Image.new("RGBA", output_image.size, cor_fundo)
                fundo.paste(output_image, mask=output_image)
                output_image = fundo.convert("RGB")
            elif not saida_transparente:
                # Fundo branco padrão
                fundo = Image.new("RGB", output_image.size, (255, 255, 255))
                fundo.paste(output_image, mask=output_image)
                output_image = fundo
            
            return output_image, "Sucesso"
            
        except Exception as e:
            return None, str(e)
    
    def processar_lote(self, pasta_entrada, pasta_saida, transparente=True):
        """Processa vrias imagens"""
        resultados = []
        imagens = list(Path(pasta_entrada).glob("*.jpg")) + \
                  list(Path(pasta_entrada).glob("*.png"))
        
        for i, img_path in enumerate(imagens):
            print(f"Processando {i+1}/{len(imagens)}: {img_path.name}")
            img_saida, msg = self.processar(str(img_path), transparente)
            
            if img_saida:
                ext = "png" if transparente else "jpg"
                nome_saida = f"sem_fundo_{img_path.stem}.{ext}"
                img_saida.save(Path(pasta_saida) / nome_saida)
                resultados.append(f"[OK] {img_path.name} -> {nome_saida}")
            else:
                resultados.append(f"[ERRO] {img_path.name}: {msg}")
        
        return resultados

class InterfaceRemoverFundo(InterfaceBase):
    def __init__(self):
        super().__init__(" Remover Fundo de Imagens", "700x650")
        self.ferramenta = FerramentaRemoverFundo(usar_gpu=USAR_GPU)
        self.caminho_imagem = None
        self.imagem_processada = None
        self.setup_interface()
    
    def setup_interface(self):
        titulo = ctk.CTkLabel(
            self.frame,
            text=" Remover Fundo de Imagens",
            font=("Arial", 22, "bold")
        )
        titulo.pack(pady=10)
        
        # Status GPU
        status = "[OK] GPU Ativa (GTX 1070 - 1.5GB VRAM)" if self.ferramenta.usar_gpu else "[AVISO] CPU"
        self.lbl_gpu = ctk.CTkLabel(self.frame, text=status)
        self.lbl_gpu.pack(pady=5)
        
        # Opes
        self.frame_opcoes = ctk.CTkFrame(self.frame)
        self.frame_opcoes.pack(pady=10, padx=10, fill="x")
        
        self.transparente_var = ctk.BooleanVar(value=True)
        self.chk_transparente = ctk.CTkCheckBox(
            self.frame_opcoes,
            text="Fundo Transparente (PNG)",
            variable=self.transparente_var,
            command=self.toggle_cor_fundo
        )
        self.chk_transparente.pack(side="left", padx=10)
        
        self.cor_fundo_btn = ctk.CTkButton(
            self.frame_opcoes,
            text="Escolher Cor",
            command=self.escolher_cor,
            width=100,
            state="disabled"
        )
        self.cor_fundo_btn.pack(side="left", padx=10)
        
        self.cor_fundo = (255, 255, 255)  # branco
        
        # Boto selecionar
        self.btn_imagem = ctk.CTkButton(
            self.frame,
            text=" Selecionar Imagem",
            command=self.selecionar_imagem,
            width=200,
            height=40
        )
        self.btn_imagem.pack(pady=10)
        
        # Preview lado a lado
        self.frame_previews = ctk.CTkFrame(self.frame)
        self.frame_previews.pack(pady=10, fill="both", expand=True)
        
        # Original
        self.frame_original = ctk.CTkFrame(self.frame_previews)
        self.frame_original.pack(side="left", padx=5, fill="both", expand=True)
        
        self.lbl_original_titulo = ctk.CTkLabel(self.frame_original, text="Original")
        self.lbl_original_titulo.pack()
        
        self.lbl_original = ctk.CTkLabel(self.frame_original, text="Sem imagem")
        self.lbl_original.pack(expand=True)
        
        # Processado
        self.frame_processado = ctk.CTkFrame(self.frame_previews)
        self.frame_processado.pack(side="right", padx=5, fill="both", expand=True)
        
        self.lbl_processado_titulo = ctk.CTkLabel(self.frame_processado, text="Sem Fundo")
        self.lbl_processado_titulo.pack()
        
        self.lbl_processado = ctk.CTkLabel(self.frame_processado, text="Processe uma imagem")
        self.lbl_processado.pack(expand=True)
        
        # Botes
        self.frame_botoes = ctk.CTkFrame(self.frame)
        self.frame_botoes.pack(pady=10)
        
        self.btn_processar = ctk.CTkButton(
            self.frame_botoes,
            text=" Remover Fundo",
            command=self.processar,
            width=150,
            height=40,
            fg_color="green",
            state="disabled"
        )
        self.btn_processar.pack(side="left", padx=5)
        
        self.btn_salvar = ctk.CTkButton(
            self.frame_botoes,
            text=" Salvar",
            command=self.salvar_imagem,
            width=100,
            height=40,
            state="disabled"
        )
        self.btn_salvar.pack(side="left", padx=5)
    
    def toggle_cor_fundo(self):
        if self.transparente_var.get():
            self.cor_fundo_btn.configure(state="disabled")
        else:
            self.cor_fundo_btn.configure(state="normal")
    
    def escolher_cor(self):
        from tkinter import colorchooser
        cor = colorchooser.askcolor(title="Escolha a cor de fundo")
        if cor[0]:
            self.cor_fundo = tuple(int(c) for c in cor[0])
            self.cor_fundo_btn.configure(fg_color=f"#{cor[1][1:]}")
    
    def selecionar_imagem(self):
        caminho = self.utils.selecionar_arquivo(
            "Selecione uma imagem",
            [("Imagens", "*.jpg *.jpeg *.png *.bmp")]
        )
        if caminho:
            self.caminho_imagem = caminho
            
            # Preview original
            from PIL import ImageTk
            img = Image.open(caminho)
            img.thumbnail((250, 250))
            img_tk = ImageTk.PhotoImage(img)
            self.lbl_original.configure(image=img_tk, text="")
            self.lbl_original.image = img_tk
            
            self.btn_processar.configure(state="normal")
    
    def processar(self):
        if not self.caminho_imagem:
            return
        
        self.btn_processar.configure(text=" Processando...", state="disabled")
        self.frame.update()
        
        transparente = self.transparente_var.get()
        cor_fundo = None if transparente else self.cor_fundo
        
        img_saida, msg = self.ferramenta.processar(
            self.caminho_imagem,
            saida_transparente=transparente,
            cor_fundo=cor_fundo
        )
        
        if img_saida:
            self.imagem_processada = img_saida
            
            # Preview
            from PIL import ImageTk
            img_copy = img_saida.copy()
            img_copy.thumbnail((250, 250))
            img_tk = ImageTk.PhotoImage(img_copy)
            self.lbl_processado.configure(image=img_tk, text="")
            self.lbl_processado.image = img_tk
            
            self.btn_salvar.configure(state="normal")
        else:
            self.utils.mostrar_erro("Erro", msg)
        
        self.btn_processar.configure(text=" Remover Fundo", state="normal")
    
    def salvar_imagem(self):
        if self.imagem_processada:
            ext = "png" if self.transparente_var.get() else "jpg"
            caminho = filedialog.asksaveasfilename(
                defaultextension=f".{ext}",
                filetypes=[(f"{ext.upper()}", f"*.{ext}")]
            )
            if caminho:
                self.imagem_processada.save(caminho)
                self.utils.mostrar_info("Sucesso", f"Imagem salva em:\n{caminho}")

class ModoIA_RemoverFundo:
    def __init__(self):
        self.ferramenta = FerramentaRemoverFundo(usar_gpu=USAR_GPU)
        self.utils = Utils()
    
    def descobrir(self, pasta_teste):
        resultados = []
        imagens = list(Path(pasta_teste).glob("*.jpg"))[:3]
        
        for img_path in imagens:
            img_saida, _ = self.ferramenta.processar(str(img_path))
            if img_saida:
                nome_saida = self.utils.safe_filename("sem_fundo", "png")
                caminho_saida = PASTA_SAIDAS / nome_saida
                img_saida.save(caminho_saida)
                resultados.append({
                    "imagem": img_path.name,
                    "resultado": str(caminho_saida)
                })
        
        return resultados
    
    def processar_para_ia(self, caminho_imagem, transparente=True):
        img_saida, msg = self.ferramenta.processar(caminho_imagem, transparente)
        
        if img_saida:
            nome_saida = self.utils.safe_filename("sem_fundo_ia", "png")
            caminho_saida = PASTA_SAIDAS / nome_saida
            img_saida.save(caminho_saida)
            return {
                "sucesso": True,
                "arquivo": str(caminho_saida),
                "mensagem": "Fundo removido com sucesso"
            }
        else:
            return {"sucesso": False, "erro": msg}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        comando = sys.argv[1]
        ia = ModoIA_RemoverFundo()
        
        if comando == "--descobrir" and len(sys.argv) > 2:
            resultados = ia.descobrir(sys.argv[2])
            print(json.dumps(resultados, indent=2, ensure_ascii=False))
        
        elif comando == "--processar" and len(sys.argv) > 2:
            transparente = len(sys.argv) < 4 or sys.argv[3].lower() != "false"
            resultado = ia.processar_para_ia(sys.argv[2], transparente)
            print(json.dumps(resultado, indent=2, ensure_ascii=False))
        
        else:
            print("Uso: ...")
    else:
        app = InterfaceRemoverFundo()
        app.rodar()
