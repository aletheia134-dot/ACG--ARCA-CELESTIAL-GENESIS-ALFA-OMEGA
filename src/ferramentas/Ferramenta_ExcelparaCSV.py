# Ferramenta: Converter Excel para CSV
# Usa pandas/openpyxl (leve, CPU)

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.modulos.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS

import pandas as pd
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import openpyxl

class FerramentaExcelparaCSV:
    def __init__(self):
        self.df = None
        self.caminho_excel = None
        self.planilhas = []
        self.info = {}
    
    def abrir_excel(self, caminho):
        """Abre um arquivo Excel"""
        try:
            self.caminho_excel = caminho
            
            # Obtm nomes das planilhas
            xl = pd.ExcelFile(caminho)
            self.planilhas = xl.sheet_names
            
            # Carrega primeira planilha como preview
            self.df = pd.read_excel(caminho, sheet_name=0)
            
            # informações
            self.info = {
                "planilhas": len(self.planilhas),
                "nomes_planilhas": self.planilhas,
                "linhas": len(self.df),
                "colunas": len(self.df.columns),
                "tamanho_mb": Path(caminho).stat().st_size / (1024 * 1024)
            }
            
            return True, self.info
        except Exception as e:
            return False, str(e)
    
    def carregar_planilha(self, nome_planilha):
        """Carrega uma planilha especfica"""
        try:
            self.df = pd.read_excel(self.caminho_excel, sheet_name=nome_planilha)
            return True, {
                "linhas": len(self.df),
                "colunas": len(self.df.columns),
                "colunas_nomes": list(self.df.columns)
            }
        except Exception as e:
            return False, str(e)
    
    def converter_para_csv(self, planilha=None, separador=',', 
                          encoding='utf-8', index=False, 
                          pasta_saida=None):
        """Converte Excel para CSV"""
        try:
            if planilha:
                df = pd.read_excel(self.caminho_excel, sheet_name=planilha)
            else:
                df = self.df
            
            if df is None:
                return None, "Nenhum dado carregado"
            
            # Define nome do arquivo
            if not pasta_saida:
                pasta_saida = PASTA_SAIDAS
            
            if planilha:
                nome_base = f"{Path(self.caminho_excel).stem}_{planilha}"
            else:
                nome_base = Path(self.caminho_excel).stem
            
            caminho_csv = Path(pasta_saida) / f"{nome_base}.csv"
            
            # Salva como CSV
            df.to_csv(
                caminho_csv,
                sep=separador,
                encoding=encoding,
                index=index
            )
            
            return {
                "arquivo": str(caminho_csv),
                "linhas": len(df),
                "colunas": len(df.columns),
                "tamanho_kb": caminho_csv.stat().st_size / 1024
            }, "Sucesso"
            
        except Exception as e:
            return None, str(e)
    
    def converter_todas_planilhas(self, separador=',', encoding='utf-8',
                                  pasta_saida=None):
        """Converte todas as planilhas para CSV"""
        try:
            resultados = []
            
            if not pasta_saida:
                pasta_saida = PASTA_SAIDAS / Path(self.caminho_excel).stem
            else:
                pasta_saida = Path(pasta_saida) / Path(self.caminho_excel).stem
            
            pasta_saida.mkdir(exist_ok=True, parents=True)
            
            for planilha in self.planilhas:
                df = pd.read_excel(self.caminho_excel, sheet_name=planilha)
                caminho_csv = pasta_saida / f"{planilha}.csv"
                
                df.to_csv(
                    caminho_csv,
                    sep=separador,
                    encoding=encoding,
                    index=False
                )
                
                resultados.append({
                    "planilha": planilha,
                    "arquivo": str(caminho_csv),
                    "linhas": len(df),
                    "colunas": len(df.columns)
                })
            
            return resultados, "Sucesso"
            
        except Exception as e:
            return None, str(e)
    
    def preview(self, linhas=5):
        """Retorna preview dos dados"""
        if self.df is None:
            return None
        
        return self.df.head(linhas).to_string()

class InterfaceExcelparaCSV(InterfaceBase):
    def __init__(self):
        super().__init__(" Converter Excel para CSV", "800x700")
        self.ferramenta = FerramentaExcelparaCSV()
        self.info_excel = None
        self.planilha_atual = 0
        self.setup_interface()
    
    def setup_interface(self):
        titulo = ctk.CTkLabel(
            self.frame,
            text=" Converter Excel para CSV",
            font=("Arial", 24, "bold")
        )
        titulo.pack(pady=10)
        
        # Seleo
        self.frame_arquivo = ctk.CTkFrame(self.frame)
        self.frame_arquivo.pack(pady=10, padx=10, fill="x")
        
        self.btn_excel = ctk.CTkButton(
            self.frame_arquivo,
            text=" Selecionar Excel",
            command=self.selecionar_excel,
            width=150,
            height=40
        )
        self.btn_excel.pack(side="left", padx=5)
        
        self.lbl_arquivo = ctk.CTkLabel(
            self.frame_arquivo,
            text="Nenhum arquivo selecionado"
        )
        self.lbl_arquivo.pack(side="left", padx=10)
        
        # informações
        self.frame_info = ctk.CTkFrame(self.frame)
        self.frame_info.pack(pady=10, padx=10, fill="x")
        
        self.texto_info = ctk.CTkTextbox(self.frame_info, height=80)
        self.texto_info.pack(pady=5, padx=5, fill="x")
        
        # Seleo de planilha
        self.frame_planilha = ctk.CTkFrame(self.frame)
        self.frame_planilha.pack(pady=5, padx=10, fill="x")
        
        self.lbl_planilha = ctk.CTkLabel(self.frame_planilha, text="Planilha:")
        self.lbl_planilha.pack(side="left", padx=5)
        
        self.planilha_var = ctk.StringVar()
        self.combo_planilha = ctk.CTkComboBox(
            self.frame_planilha,
            values=[],
            variable=self.planilha_var,
            width=200,
            command=self.mudar_planilha
        )
        self.combo_planilha.pack(side="left", padx=5)
        
        # Preview
        self.frame_preview = ctk.CTkFrame(self.frame)
        self.frame_preview.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.lbl_preview = ctk.CTkLabel(
            self.frame_preview,
            text="Preview dos dados",
            font=("Arial", 14)
        )
        self.lbl_preview.pack(pady=2)
        
        self.texto_preview = ctk.CTkTextbox(self.frame_preview, height=150)
        self.texto_preview.pack(pady=5, padx=5, fill="both", expand=True)
        
        # Opes
        self.frame_opcoes = ctk.CTkFrame(self.frame)
        self.frame_opcoes.pack(pady=10, padx=10, fill="x")
        
        # Separador
        self.frame_sep = ctk.CTkFrame(self.frame_opcoes)
        self.frame_sep.pack(pady=2, fill="x")
        
        self.lbl_sep = ctk.CTkLabel(self.frame_sep, text="Separador:")
        self.lbl_sep.pack(side="left", padx=5)
        
        self.sep_var = ctk.StringVar(value=",")
        self.sep_combo = ctk.CTkComboBox(
            self.frame_sep,
            values=[",", ";", "|", "\\t"],
            variable=self.sep_var,
            width=80
        )
        self.sep_combo.pack(side="left", padx=5)
        
        # Encoding
        self.frame_enc = ctk.CTkFrame(self.frame_opcoes)
        self.frame_enc.pack(pady=2, fill="x")
        
        self.lbl_enc = ctk.CTkLabel(self.frame_enc, text="Encoding:")
        self.lbl_enc.pack(side="left", padx=5)
        
        self.enc_var = ctk.StringVar(value="utf-8")
        self.enc_combo = ctk.CTkComboBox(
            self.frame_enc,
            values=["utf-8", "latin1", "cp1252"],
            variable=self.enc_var,
            width=100
        )
        self.enc_combo.pack(side="left", padx=5)
        
        # índice
        self.index_var = ctk.BooleanVar(value=False)
        self.chk_index = ctk.CTkCheckBox(
            self.frame_opcoes,
            text="Incluir índice",
            variable=self.index_var
        )
        self.chk_index.pack(pady=2)
        
        # Botes
        self.frame_botoes = ctk.CTkFrame(self.frame)
        self.frame_botoes.pack(pady=10)
        
        self.btn_converter = ctk.CTkButton(
            self.frame_botoes,
            text=" Converter para CSV",
            command=self.converter,
            width=150,
            height=35,
            fg_color="green",
            state="disabled"
        )
        self.btn_converter.pack(side="left", padx=5)
        
        self.btn_converter_todas = ctk.CTkButton(
            self.frame_botoes,
            text=" Converter Todas",
            command=self.converter_todas,
            width=150,
            height=35,
            fg_color="blue",
            state="disabled"
        )
        self.btn_converter_todas.pack(side="left", padx=5)
        
        # Barra de progresso
        self.progress = ctk.CTkProgressBar(self.frame, width=400)
        self.progress.pack(pady=5)
        self.progress.set(0)
    
    def selecionar_excel(self):
        caminho = filedialog.askopenfilename(
            title="Selecione um arquivo Excel",
            filetypes=[("Excel", "*.xlsx *.xls")]
        )
        if caminho:
            self.lbl_arquivo.configure(text=f"Arquivo: {Path(caminho).name}")
            
            sucesso, info = self.ferramenta.abrir_excel(caminho)
            if sucesso:
                self.info_excel = info
                
                info_texto = f"Planilhas: {info['planilhas']}\n"
                info_texto += f"Linhas (1): {info['linhas']}\n"
                info_texto += f"Colunas: {info['colunas']}\n"
                info_texto += f"Tamanho: {info['tamanho_mb']:.2f} MB"
                
                self.texto_info.delete('1.0', 'end')
                self.texto_info.insert('1.0', info_texto)
                
                # Atualiza combo de planilhas
                self.combo_planilha.configure(values=info['nomes_planilhas'])
                if info['nomes_planilhas']:
                    self.combo_planilha.set(info['nomes_planilhas'][0])
                    self.mudar_planilha(info['nomes_planilhas'][0])
                
                self.btn_converter.configure(state="normal")
                self.btn_converter_todas.configure(state="normal")
            else:
                self.utils.mostrar_erro("Erro", info)
    
    def mudar_planilha(self, choice):
        if choice:
            sucesso, info = self.ferramenta.carregar_planilha(choice)
            if sucesso:
                # Atualiza preview
                preview = self.ferramenta.preview(10)
                self.texto_preview.delete('1.0', 'end')
                self.texto_preview.insert('1.0', preview)
    
    def converter(self):
        def converter_thread():
            self.btn_converter.configure(state="disabled", text=" Convertendo...")
            self.progress.set(0.3)
            
            separador = self.sep_var.get()
            if separador == "\\t":
                separador = "\t"
            
            resultado, msg = self.ferramenta.converter_para_csv(
                planilha=self.planilha_var.get(),
                separador=separador,
                encoding=self.enc_var.get(),
                index=self.index_var.get()
            )
            
            self.progress.set(0.8)
            
            if resultado:
                self.utils.mostrar_info(
                    "Sucesso",
                    f"CSV gerado!\n"
                    f"Arquivo: {Path(resultado['arquivo']).name}\n"
                    f"Linhas: {resultado['linhas']}\n"
                    f"Tamanho: {resultado['tamanho_kb']:.1f} KB"
                )
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.progress.set(1)
            self.btn_converter.configure(state="normal", text=" Converter para CSV")
        
        threading.Thread(target=converter_thread).start()
    
    def converter_todas(self):
        def converter_thread():
            self.btn_converter_todas.configure(state="disabled", text=" Convertendo...")
            self.progress.set(0.3)
            
            separador = self.sep_var.get()
            if separador == "\\t":
                separador = "\t"
            
            resultados, msg = self.ferramenta.converter_todas_planilhas(
                separador=separador,
                encoding=self.enc_var.get()
            )
            
            self.progress.set(0.8)
            
            if resultados:
                texto = f"{len(resultados)} planilhas convertidas:\n"
                for r in resultados:
                    texto += f"   {r['planilha']}: {r['linhas']} linhas\n"
                
                self.utils.mostrar_info("Sucesso", texto)
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.progress.set(1)
            self.btn_converter_todas.configure(state="normal", text=" Converter Todas")
        
        threading.Thread(target=converter_thread).start()

if __name__ == "__main__":
    app = InterfaceExcelparaCSV()
    app.rodar()
