# Ferramenta: Extrair Texto de PDF
# Usa pymupdf (leve, CPU)

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.modulos.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS

import fitz  # pymupdf
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
from PIL import Image, ImageTk
import io

class FerramentaPDFparaTexto:
    def __init__(self):
        self.documento = None
        self.caminho_pdf = None
        self.total_paginas = 0
    
    def abrir_pdf(self, caminho):
        """Abre um arquivo PDF"""
        try:
            self.documento = fitz.open(caminho)
            self.caminho_pdf = caminho
            self.total_paginas = len(self.documento)
            
            # Extrai metadados
            metadados = self.documento.metadata
            info = {
                "titulo": metadados.get("title", "Desconhecido"),
                "autor": metadados.get("author", "Desconhecido"),
                "assunto": metadados.get("subject", ""),
                "palavras_chave": metadados.get("keywords", ""),
                "criador": metadados.get("creator", ""),
                "produtor": metadados.get("producer", ""),
                "criacao": metadados.get("creationDate", ""),
                "modificacao": metadados.get("modDate", ""),
                "total_paginas": self.total_paginas
            }
            
            return True, info
        except Exception as e:
            return False, str(e)
    
    def extrair_texto_todas(self):
        """Extrai texto de todas as pginas"""
        if self.documento is None:
            return None, "PDF no carregado"
        
        try:
            texto_completo = []
            for num_pagina in range(self.total_paginas):
                pagina = self.documento[num_pagina]
                texto = pagina.get_text()
                texto_completo.append(f"--- Pgina {num_pagina + 1} ---\n{texto}")
            
            return "\n\n".join(texto_completo), "Sucesso"
        except Exception as e:
            return None, str(e)
    
    def extrair_texto_paginas(self, paginas):
        """Extrai texto de pginas especficas"""
        if self.documento is None:
            return None, "PDF no carregado"
        
        try:
            texto_completo = []
            for num_pagina in paginas:
                if 0 <= num_pagina < self.total_paginas:
                    pagina = self.documento[num_pagina]
                    texto = pagina.get_text()
                    texto_completo.append(f"--- Pgina {num_pagina + 1} ---\n{texto}")
            
            return "\n\n".join(texto_completo), "Sucesso"
        except Exception as e:
            return None, str(e)
    
    def extrair_texto_com_formato(self, manter_formatacao=False):
        """Extrai texto mantendo ou no formatao"""
        if self.documento is None:
            return None, "PDF no carregado"
        
        try:
            texto_completo = []
            for num_pagina in range(self.total_paginas):
                pagina = self.documento[num_pagina]
                
                if manter_formatacao:
                    # Extrai com informações de formatao
                    blocos = pagina.get_text("dict")
                    texto_pagina = []
                    for bloco in blocos["blocks"]:
                        if "lines" in bloco:
                            for linha in bloco["lines"]:
                                for span in linha["spans"]:
                                    texto_pagina.append(span["text"])
                    texto = "\n".join(texto_pagina)
                else:
                    # Apenas texto simples
                    texto = pagina.get_text()
                
                texto_completo.append(f"--- Pgina {num_pagina + 1} ---\n{texto}")
            
            return "\n\n".join(texto_completo), "Sucesso"
        except Exception as e:
            return None, str(e)
    
    def extrair_imagens(self, pasta_saida):
        """Extrai imagens do PDF"""
        if self.documento is None:
            return None, "PDF no carregado"
        
        try:
            pasta_saida = Path(pasta_saida)
            pasta_saida.mkdir(exist_ok=True, parents=True)
            
            imagens_extraidas = []
            
            for num_pagina in range(self.total_paginas):
                pagina = self.documento[num_pagina]
                lista_imagens = pagina.get_images()
                
                for idx, img in enumerate(lista_imagens):
                    xref = img[0]
                    pix = fitz.Pixmap(self.documento, xref)
                    
                    if pix.n - pix.alpha < 4:  # RGB ou CMYK
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    
                    nome_arquivo = pasta_saida / f"pagina_{num_pagina+1}_imagem_{idx+1}.png"
                    pix.save(str(nome_arquivo))
                    imagens_extraidas.append(str(nome_arquivo))
                    
                    if pix:
                        pix = None
            
            return imagens_extraidas, "Sucesso"
        except Exception as e:
            return None, str(e)
    
    def extrair_tabelas(self):
        """Tenta extrair tabelas (aproximao)"""
        if self.documento is None:
            return None, "PDF no carregado"
        
        try:
            tabelas = []
            for num_pagina in range(self.total_paginas):
                pagina = self.documento[num_pagina]
                
                # Procura por padrões de tabela (texto alinhado em colunas)
                texto = pagina.get_text("dict")
                linhas_tabela = []
                
                for bloco in texto["blocks"]:
                    if "lines" in bloco:
                        for linha in bloco["lines"]:
                            linha_texto = []
                            for span in linha["spans"]:
                                linha_texto.append(span["text"])
                            if len(linha_texto) > 1:  # Possvel linha de tabela
                                linhas_tabela.append(" | ".join(linha_texto))
                
                if linhas_tabela:
                    tabelas.append({
                        "pagina": num_pagina + 1,
                        "conteudo": linhas_tabela
                    })
            
            return tabelas, "Sucesso"
        except Exception as e:
            return None, str(e)
    
    def fechar(self):
        """Fecha o documento"""
        if self.documento:
            self.documento.close()

class InterfacePDFparaTexto(InterfaceBase):
    def __init__(self):
        super().__init__(" Extrair Texto de PDF", "800x700")
        self.ferramenta = FerramentaPDFparaTexto()
        self.info_pdf = None
        self.texto_extraido = None
        self.setup_interface()
    
    def setup_interface(self):
        # Ttulo
        titulo = ctk.CTkLabel(
            self.frame,
            text=" Extrair Texto de Arquivos PDF",
            font=("Arial", 24, "bold")
        )
        titulo.pack(pady=10)
        
        # Seleo de arquivo
        self.frame_arquivo = ctk.CTkFrame(self.frame)
        self.frame_arquivo.pack(pady=10, padx=10, fill="x")
        
        self.btn_pdf = ctk.CTkButton(
            self.frame_arquivo,
            text=" Selecionar PDF",
            command=self.selecionar_pdf,
            width=150,
            height=40
        )
        self.btn_pdf.pack(side="left", padx=5)
        
        self.lbl_arquivo = ctk.CTkLabel(
            self.frame_arquivo,
            text="Nenhum PDF selecionado",
            font=("Arial", 12)
        )
        self.lbl_arquivo.pack(side="left", padx=10)
        
        # informações do PDF
        self.frame_info = ctk.CTkFrame(self.frame)
        self.frame_info.pack(pady=10, padx=10, fill="x")
        
        self.texto_info = ctk.CTkTextbox(self.frame_info, height=100)
        self.texto_info.pack(pady=5, padx=5, fill="x")
        
        # Abas
        self.tabview = ctk.CTkTabview(self.frame)
        self.tabview.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Aba: Texto
        self.tab_texto = self.tabview.add("Extrair Texto")
        self.setup_tab_texto()
        
        # Aba: Imagens
        self.tab_imagens = self.tabview.add("Extrair Imagens")
        self.setup_tab_imagens()
        
        # Aba: Tabelas
        self.tab_tabelas = self.tabview.add("Tabelas")
        self.setup_tab_tabelas()
        
        # Barra de progresso
        self.progress = ctk.CTkProgressBar(self.frame, width=400)
        self.progress.pack(pady=5)
        self.progress.set(0)
    
    def setup_tab_texto(self):
        # Opes
        self.frame_opcoes = ctk.CTkFrame(self.tab_texto)
        self.frame_opcoes.pack(pady=5, fill="x")
        
        self.manter_formatacao = ctk.BooleanVar(value=False)
        self.chk_formatacao = ctk.CTkCheckBox(
            self.frame_opcoes,
            text="Manter formatao aproximada",
            variable=self.manter_formatacao
        )
        self.chk_formatacao.pack(side="left", padx=5)
        
        self.selecionar_paginas = ctk.BooleanVar(value=False)
        self.chk_selecionar = ctk.CTkCheckBox(
            self.frame_opcoes,
            text="Selecionar pginas especficas",
            variable=self.selecionar_paginas,
            command=self.toggle_paginas
        )
        self.chk_selecionar.pack(side="left", padx=20)
        
        self.entry_paginas = ctk.CTkEntry(
            self.frame_opcoes,
            placeholder_text="Ex: 1,3,5-10",
            width=150,
            state="disabled"
        )
        self.entry_paginas.pack(side="left", padx=5)
        
        # Boto extrair
        self.btn_extrair = ctk.CTkButton(
            self.tab_texto,
            text=" Extrair Texto",
            command=self.extrair_texto,
            width=150,
            height=35,
            fg_color="green",
            state="disabled"
        )
        self.btn_extrair.pack(pady=10)
        
        # rea de texto resultado
        self.lbl_resultado = ctk.CTkLabel(self.tab_texto, text="Texto extrado:")
        self.lbl_resultado.pack(pady=(10,0))
        
        self.texto_resultado = ctk.CTkTextbox(self.tab_texto, height=200)
        self.texto_resultado.pack(pady=5, padx=5, fill="both", expand=True)
        
        # Botes
        self.frame_botoes = ctk.CTkFrame(self.tab_texto)
        self.frame_botoes.pack(pady=5)
        
        self.btn_copiar = ctk.CTkButton(
            self.frame_botoes,
            text=" Copiar",
            command=self.copiar_texto,
            width=100,
            state="disabled"
        )
        self.btn_copiar.pack(side="left", padx=5)
        
        self.btn_salvar = ctk.CTkButton(
            self.frame_botoes,
            text=" Salvar TXT",
            command=self.salvar_texto,
            width=100,
            state="disabled"
        )
        self.btn_salvar.pack(side="left", padx=5)
    
    def setup_tab_imagens(self):
        self.lbl_imagens_info = ctk.CTkLabel(
            self.tab_imagens,
            text="Extraia todas as imagens contidas no PDF",
            font=("Arial", 12)
        )
        self.lbl_imagens_info.pack(pady=10)
        
        self.btn_extrair_imagens = ctk.CTkButton(
            self.tab_imagens,
            text=" Extrair Imagens",
            command=self.extrair_imagens,
            width=150,
            height=35,
            fg_color="blue",
            state="disabled"
        )
        self.btn_extrair_imagens.pack(pady=10)
        
        self.frame_lista_imagens = ctk.CTkFrame(self.tab_imagens)
        self.frame_lista_imagens.pack(pady=10, padx=5, fill="both", expand=True)
        
        self.lista_imagens = ctk.CTkTextbox(self.frame_lista_imagens, height=150)
        self.lista_imagens.pack(fill="both", expand=True)
    
    def setup_tab_tabelas(self):
        self.lbl_tabelas_info = ctk.CTkLabel(
            self.tab_tabelas,
            text="Tentativa de detectar tabelas no PDF",
            font=("Arial", 12)
        )
        self.lbl_tabelas_info.pack(pady=10)
        
        self.btn_extrair_tabelas = ctk.CTkButton(
            self.tab_tabelas,
            text=" Detectar Tabelas",
            command=self.extrair_tabelas,
            width=150,
            height=35,
            fg_color="orange",
            state="disabled"
        )
        self.btn_extrair_tabelas.pack(pady=10)
        
        self.frame_tabelas = ctk.CTkFrame(self.tab_tabelas)
        self.frame_tabelas.pack(pady=10, padx=5, fill="both", expand=True)
        
        self.texto_tabelas = ctk.CTkTextbox(self.frame_tabelas, height=200)
        self.texto_tabelas.pack(fill="both", expand=True)
    
    def toggle_paginas(self):
        if self.selecionar_paginas.get():
            self.entry_paginas.configure(state="normal")
        else:
            self.entry_paginas.configure(state="disabled")
    
    def selecionar_pdf(self):
        caminho = filedialog.askopenfilename(
            title="Selecione um arquivo PDF",
            filetypes=[("PDF", "*.pdf")]
        )
        if caminho:
            self.lbl_arquivo.configure(text=f"Arquivo: {Path(caminho).name}")
            
            sucesso, info = self.ferramenta.abrir_pdf(caminho)
            if sucesso:
                self.info_pdf = info
                
                # Mostra informações
                info_texto = f"Ttulo: {info['titulo']}\n"
                info_texto += f"Autor: {info['autor']}\n"
                info_texto += f"Pginas: {info['total_paginas']}\n"
                info_texto += f"Criado: {info['criacao']}"
                
                self.texto_info.delete('1.0', 'end')
                self.texto_info.insert('1.0', info_texto)
                
                # Ativa botes
                self.btn_extrair.configure(state="normal")
                self.btn_extrair_imagens.configure(state="normal")
                self.btn_extrair_tabelas.configure(state="normal")
            else:
                self.utils.mostrar_erro("Erro", info)
    
    def extrair_texto(self):
        def extrair_thread():
            self.btn_extrair.configure(state="disabled", text=" Extraindo...")
            self.progress.set(0.2)
            
            if self.selecionar_paginas.get():
                # Parse pginas
                paginas_texto = self.entry_paginas.get()
                paginas = []
                
                for parte in paginas_texto.split(','):
                    if '-' in parte:
                        inicio, fim = parte.split('-')
                        paginas.extend(range(int(inicio)-1, int(fim)))
                    else:
                        paginas.append(int(parte)-1)
                
                self.progress.set(0.4)
                texto, msg = self.ferramenta.extrair_texto_paginas(paginas)
            else:
                texto, msg = self.ferramenta.extrair_texto_todas()
            
            self.progress.set(0.8)
            
            if texto:
                self.texto_extraido = texto
                self.texto_resultado.delete('1.0', 'end')
                self.texto_resultado.insert('1.0', texto[:1000] + "...\n\n(Texto truncado no preview)")
                self.btn_copiar.configure(state="normal")
                self.btn_salvar.configure(state="normal")
                self.utils.mostrar_info("Sucesso", "Texto extrado!")
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.progress.set(1)
            self.btn_extrair.configure(state="normal", text=" Extrair Texto")
        
        threading.Thread(target=extrair_thread).start()
    
    def extrair_imagens(self):
        def extrair_thread():
            self.btn_extrair_imagens.configure(state="disabled", text=" Extraindo...")
            self.progress.set(0.2)
            
            pasta_saida = PASTA_SAIDAS / f"imagens_{Path(self.ferramenta.caminho_pdf).stem}"
            
            imagens, msg = self.ferramenta.extrair_imagens(pasta_saida)
            
            self.progress.set(0.8)
            
            if imagens:
                self.lista_imagens.delete('1.0', 'end')
                for img in imagens:
                    self.lista_imagens.insert('end', f"[OK] {Path(img).name}\n")
                self.utils.mostrar_info("Sucesso", f"{len(imagens)} imagens extradas!")
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.progress.set(1)
            self.btn_extrair_imagens.configure(state="normal", text=" Extrair Imagens")
        
        threading.Thread(target=extrair_thread).start()
    
    def extrair_tabelas(self):
        def tabelas_thread():
            self.btn_extrair_tabelas.configure(state="disabled", text=" Detectando...")
            self.progress.set(0.2)
            
            tabelas, msg = self.ferramenta.extrair_tabelas()
            
            self.progress.set(0.8)
            
            if tabelas:
                self.texto_tabelas.delete('1.0', 'end')
                for tabela in tabelas:
                    self.texto_tabelas.insert('end', f"--- Pgina {tabela['pagina']} ---\n")
                    for linha in tabela['conteudo'][:10]:
                        self.texto_tabelas.insert('end', f"{linha}\n")
                    if len(tabela['conteudo']) > 10:
                        self.texto_tabelas.insert('end', "...\n\n")
                self.utils.mostrar_info("Sucesso", "Tabelas detectadas!")
            else:
                self.utils.mostrar_erro("Erro", msg or "Nenhuma tabela encontrada")
            
            self.progress.set(1)
            self.btn_extrair_tabelas.configure(state="normal", text=" Detectar Tabelas")
        
        threading.Thread(target=tabelas_thread).start()
    
    def copiar_texto(self):
        if self.texto_extraido:
            self.frame.clipboard_clear()
            self.frame.clipboard_append(self.texto_extraido[:10000])
            self.utils.mostrar_info("Copiado", "Texto copiado (primeiros 10000 caracteres)")
    
    def salvar_texto(self):
        if self.texto_extraido:
            caminho = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Texto", "*.txt")]
            )
            if caminho:
                with open(caminho, 'w', encoding='utf-8') as f:
                    f.write(self.texto_extraido)
                self.utils.mostrar_info("Sucesso", f"Texto salvo em:\n{caminho}")
    
    def __del__(self):
        self.ferramenta.fechar()

if __name__ == "__main__":
    app = InterfacePDFparaTexto()
    app.rodar()
