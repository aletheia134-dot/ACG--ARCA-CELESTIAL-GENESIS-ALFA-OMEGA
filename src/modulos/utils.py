#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
utils.py - Utilitrios compartilhados por todas as ferramentas
ARQUIVO crítico: estava AUSENTE no projeto. Todos os outros arquivos
dependem deste módulo via: from utils import InterfaceBase, Utils
"""

import sys
import os
import json
import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk

try:
    import customtkinter as ctk
    CTK_DISPONIVEL = True
except ImportError:
    CTK_DISPONIVEL = False
    print("[ERRO] customtkinter no instalado. Instale com: pip install customtkinter")

# Importa config de forma segura (pode no existir ainda)
try:
    from src.config.config import PASTA_RAIZ, PASTA_TEMP, PASTA_SAIDAS
except ImportError:
    # Fallback para quando config.py no est no path
    PASTA_RAIZ = Path.home() / "Ferramentas_IA"
    PASTA_TEMP = PASTA_RAIZ / "temp"
    PASTA_SAIDAS = PASTA_RAIZ / "saidas"
    PASTA_RAIZ.mkdir(parents=True, exist_ok=True)
    PASTA_TEMP.mkdir(parents=True, exist_ok=True)
    PASTA_SAIDAS.mkdir(parents=True, exist_ok=True)


# ============================================================
# CLASSE Utils - funções utilitrias sem interface grfica
# ============================================================
class Utils:
    """Utilitrios gerais: arquivos, nomes, notificaes"""

    def safe_filename(self, prefixo: str, extensao: str) -> str:
        """
        Gera nome de arquivo único baseado em timestamp.
        Exemplo: safe_filename('anime', 'png')  'anime_20240215_143022.png'
        """
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = extensao.lstrip(".")
        return f"{prefixo}_{ts}.{ext}"

    def selecionar_arquivo(self, titulo: str, tipos: list) -> str | None:
        """
        Abre dilogo de seleo de arquivo.
        tipos: lista de tuplas [('Imagens', '*.jpg *.png'), ...]
        Retorna: caminho absoluto (str) ou None se cancelado
        """
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        caminho = filedialog.askopenfilename(title=titulo, filetypes=tipos)
        root.destroy()
        return caminho if caminho else None

    def selecionar_pasta(self, titulo: str = "Selecionar pasta") -> str | None:
        """Abre dilogo para selecionar pasta. Retorna caminho ou None."""
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        pasta = filedialog.askdirectory(title=titulo)
        root.destroy()
        return pasta if pasta else None

    def salvar_arquivo(self, titulo: str, extensao_padrao: str, tipos: list) -> str | None:
        """
        Abre dilogo 'Salvar Como'.
        Retorna: caminho destino (str) ou None se cancelado
        """
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        caminho = filedialog.asksaveasfilename(
            title=titulo,
            defaultextension=extensao_padrao,
            filetypes=tipos
        )
        root.destroy()
        return caminho if caminho else None

    def mostrar_erro(self, titulo: str, mensagem: str):
        """Mostra caixa de erro"""
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(titulo, mensagem, parent=root)
        root.destroy()

    def mostrar_info(self, titulo: str, mensagem: str):
        """Mostra caixa de informação"""
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(titulo, mensagem, parent=root)
        root.destroy()

    def mostrar_aviso(self, titulo: str, mensagem: str):
        """Mostra caixa de aviso"""
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(titulo, mensagem, parent=root)
        root.destroy()

    def salvar_json(self, dados: dict | list, caminho: str | Path) -> bool:
        """Salva dados em JSON. Retorna True se sucesso."""
        try:
            with open(caminho, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[ERRO] Erro ao salvar JSON: {e}")
            return False

    def carregar_json(self, caminho: str | Path) -> dict | list | None:
        """Carrega JSON. Retorna None se falhar."""
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERRO] Erro ao carregar JSON: {e}")
            return None

    def verificar_gpu(self) -> bool:
        """Verifica se CUDA est disponível."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def info_gpu(self) -> str:
        """Retorna string com info da GPU ou 'CPU'."""
        try:
            import torch
            if torch.cuda.is_available():
                nome = torch.cuda.get_device_name(0)
                vram = torch.cuda.get_device_properties(0).total_memory / 1e9
                return f"{nome} ({vram:.1f}GB VRAM)"
            return "CPU (sem GPU CUDA)"
        except ImportError:
            return "CPU (torch no instalado)"


# ============================================================
# CLASSE InterfaceBase - Base para todas as interfaces grficas
# ============================================================
class InterfaceBase:
    """
    Classe base para interfaces grficas customtkinter.
    Todas as Ferramentas herdam desta classe.

    Uso:
        class MinhaInterface(InterfaceBase):
            def __init__(self):
                super().__init__("Ttulo da Janela", "800x600")
                self.setup_interface()   # implemente nas subclasses
    """

    def __init__(self, titulo: str, geometria: str = "800x600"):
        if not CTK_DISPONIVEL:
            raise RuntimeError(
                "customtkinter no est instalado.\n"
                "Execute: pip install customtkinter"
            )

        self.utils = Utils()

        # configuração visual padrão
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Cria janela principal
        self.janela = ctk.CTk()
        self.janela.title(titulo)
        self.janela.geometry(geometria)
        self.janela.minsize(600, 400)

        # Centraliza janela na tela
        self._centralizar_janela()

        # Frame principal com scroll
        self.frame_scroll = ctk.CTkScrollableFrame(
            self.janela,
            fg_color="transparent"
        )
        self.frame_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # Frame interno (alias para compatibilidade)
        self.frame = self.frame_scroll

        # Barra de status na base
        self.barra_status = ctk.CTkFrame(
            self.janela,
            height=28,
            fg_color="#2D2D2D",
            corner_radius=0
        )
        self.barra_status.pack(fill="x", side="bottom")
        self.barra_status.pack_propagate(False)

        self.lbl_status = ctk.CTkLabel(
            self.barra_status,
            text="Pronto",
            font=("Segoe UI", 11),
            text_color="#AAAAAA"
        )
        self.lbl_status.pack(side="left", padx=10, pady=4)

        # Evento de fechar
        self.janela.protocol("WM_DELETE_WINDOW", self._ao_fechar)

    def _centralizar_janela(self):
        """Centraliza a janela na tela"""
        self.janela.update_idletasks()
        w = self.janela.winfo_reqwidth()
        h = self.janela.winfo_reqheight()
        sw = self.janela.winfo_screenwidth()
        sh = self.janela.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.janela.geometry(f"+{x}+{y}")

    def atualizar_status(self, mensagem: str, cor: str = "#AAAAAA"):
        """Atualiza texto da barra de status (thread-safe via after)"""
        try:
            self.janela.after(0, lambda: self.lbl_status.configure(
                text=mensagem, text_color=cor
            ))
        except Exception:
            pass  # Janela pode ter sido fechada

    def mostrar_processando(self, botao=None, texto_original: str = ""):
        """
        Desabilita boto e mostra estado de processamento.
        Use antes de operações longas.
        Retorna o texto original para restaurar depois.
        """
        if botao:
            try:
                if not texto_original:
                    texto_original = botao.cget("text")
                botao.configure(text=" Processando...", state="disabled")
                self.janela.update()
            except Exception:
                pass
        return texto_original

    def finalizar_processando(self, botao=None, texto_original: str = "Processar"):
        """Restaura boto aps processamento"""
        if botao:
            try:
                botao.configure(text=texto_original, state="normal")
            except Exception:
                pass

    def rodar(self):
        """Inicia o loop principal da interface"""
        self.janela.mainloop()

    def _ao_fechar(self):
        """Chamado quando usurio fecha a janela"""
        self.janela.destroy()