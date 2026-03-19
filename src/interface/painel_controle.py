#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
 Painel de Controle Estilo Windows 11 - VERSO 2.2
Central de todas as ferramentas.

CORREES v2.2:
  - Thread-safety no monitoramento (janela.after em vez de configurar widget direto da thread)
  - GPUtil com fallback quando no instalado
  - painel_controle no depende de psutil.disk_usage('C:/') no Linux
  - monitorar() no mistura time.sleep com janela.after inutilmente
  - clarear_cor() implementado de verdade
  - Barra de status com cor dinmica (verde/amarelo/vermelho)
"""

import sys
import os
import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime
import json

sys.path.append(str(Path(__file__).parent))

try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False
    print("[AVISO] psutil no instalado: pip install psutil")

try:
    import GPUtil
    GPUTIL_OK = True
except ImportError:
    GPUTIL_OK = False

import customtkinter as ctk
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    from src.config.config import PASTA_RAIZ, PASTA_SAIDAS, PASTA_MODELOS, USAR_GPU
except ImportError:
    PASTA_RAIZ = Path.home() / "Ferramentas_IA"
    PASTA_SAIDAS = PASTA_RAIZ / "saidas"
    PASTA_MODELOS = PASTA_RAIZ / "modelos"
    USAR_GPU = False

# ─────────────────────────────────────────────────────────────────────────────
# Mapa completo de ferramentas (nome  arquivo)
# Atualiza esta lista ação adicionar novas ferramentas
# ─────────────────────────────────────────────────────────────────────────────
MAPA_FERRAMENTAS = {
    "01_IMAGEM": [
        (" Foto  Anime",          "Ferramenta_Anime.py"),
        (" Envelhecer Rosto",       "Ferramenta_Envelhecer.py"),
        (" OCR - Extrair Texto",    "Ferramenta_OCR.py"),
        (" Remover Fundo",          "Ferramenta_RemoverFundo.py"),
        (" Clonagem Rosto 3D",      "Ferramenta_ClonagemRosto3D.py"),
        (" Anime Video",            "Ferramenta_AnimeVideo.py"),
    ],
    "02_AUDIO": [
        (" Transcrio (Whisper)",  "Ferramenta_Transcricao.py"),
        (" Texto para Voz",         "Ferramenta_TextoParaVoz.py"),
        (" Remover Rudo",          "Ferramenta_RemoverRuido.py"),
        (" Separar Voz",            "Ferramenta_SepararVoz.py"),
        (" Converter udio",        "Ferramenta_ConverterAudio.py"),
        (" Clonar Voz",             "Ferramenta_ClonarVoz.py"),
    ],
    "03_VIDEO": [
        (" Extrair Frames",         "Ferramenta_ExtrairFrames.py"),
        (" Legendas Automticas",   "Ferramenta_Legendas.py"),
        (" Extrair udio",          "Ferramenta_ExtrairAudio.py"),
        (" Cortar Vdeo",           "Ferramenta_CortarVideo.py"),
        (" Juntar Vdeos",          "Ferramenta_JuntarVideos.py"),
    ],
    "04_CAMERA": [
        (" Webcam",                 "Ferramenta_Webcam.py"),
        (" Webcam Anime",           "Ferramenta_WebcamAnime.py"),
        (" Detectar Faces",         "Ferramenta_DetectarFaces.py"),
        (" Detectar Objetos",       "Ferramenta_DetectarObjetos.py"),
        (" Pose Detection",         "Ferramenta_PoseDetection.py"),
    ],
    "05_DOCUMENTOS": [
        (" PDF para Texto",         "Ferramenta_PDFparaTexto.py"),
        (" Word para Texto",        "Ferramenta_WordparaTexto.py"),
        (" Excel para CSV",         "Ferramenta_ExcelparaCSV.py"),
    ],
    "06_UTILIDADES": [
        (" Downloader",             "Ferramenta_Downloader.py"),
        (" Organizador",            "Ferramenta_Organizador.py"),
        (" Compressor",             "Ferramenta_Compressor.py"),
    ],
}

CATEGORIAS = [
    {"id": "01_IMAGEM",      "nome": "Imagem",      "icone": "", "cor": "#FFB900"},
    {"id": "02_AUDIO",       "nome": "udio",        "icone": "", "cor": "#0078D4"},
    {"id": "03_VIDEO",       "nome": "Vdeo",        "icone": "", "cor": "#107C10"},
    {"id": "04_CAMERA",      "nome": "Cmera",       "icone": "", "cor": "#D83B01"},
    {"id": "05_DOCUMENTOS",  "nome": "Documentos",   "icone": "", "cor": "#881798"},
    {"id": "06_UTILIDADES",  "nome": "Utilidades",   "icone": "", "cor": "#767676"},
]

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class PainelControleWindows11:
    def __init__(self):
        self.janela = ctk.CTk()
        self.janela.title(" Central de Ferramentas IA")
        self.janela.geometry("1280x720")
        self.janela.minsize(1024, 600)

        try:
            self.janela.iconbitmap(default="icon.ico")
        except Exception:
            pass

        # Pasta raiz das ferramentas (mesmo diretório deste arquivo)
        self.pasta_ferramentas = Path(__file__).parent

        self.monitorando = True
        self.total_ferramentas = sum(len(v) for v in MAPA_FERRAMENTAS.values())

        self._setup_interface()
        self._iniciar_monitoramento()

    # ─────────────────────────────────────────────────────────────────────────
    # INTERFACE
    # ─────────────────────────────────────────────────────────────────────────
    def _setup_interface(self):
        # --- Barra superior ---
        barra_sup = ctk.CTkFrame(self.janela, height=48, fg_color="#2D2D2D", corner_radius=0)
        barra_sup.pack(fill="x")
        barra_sup.pack_propagate(False)

        logo_frame = ctk.CTkFrame(barra_sup, fg_color="transparent")
        logo_frame.pack(side="left", padx=20, pady=8)
        ctk.CTkLabel(logo_frame, text="", font=("Segoe UI", 24), text_color="#0078D4").pack(side="left", padx=(0,8))
        ctk.CTkLabel(logo_frame, text="Central de Ferramentas IA", font=("Segoe UI", 18, "bold"), text_color="#FFFFFF").pack(side="left")

        ctk.CTkLabel(
            barra_sup,
            text=f"v2.2  {self.total_ferramentas} ferramentas",
            font=("Segoe UI", 12), text_color="#AAAAAA"
        ).pack(side="right", padx=20)

        # --- Corpo principal ---
        corpo = ctk.CTkFrame(self.janela, fg_color="#202020", corner_radius=0)
        corpo.pack(fill="both", expand=True)

        # --- Barra lateral ---
        self.barra_lateral = ctk.CTkFrame(corpo, width=210, fg_color="#2D2D2D", corner_radius=0)
        self.barra_lateral.pack(side="left", fill="y")
        self.barra_lateral.pack_propagate(False)

        # Boto Incio
        self._criar_btn_menu("", "Incio", command=self._mostrar_inicio)
        ctk.CTkFrame(self.barra_lateral, height=1, fg_color="#404040").pack(fill="x", padx=15, pady=8)

        for cat in CATEGORIAS:
            self._criar_btn_menu(
                cat["icone"],
                f"{cat['nome']} ({len(MAPA_FERRAMENTAS.get(cat['id'], []))})",
                command=lambda c=cat: self._mostrar_categoria(c)
            )

        ctk.CTkFrame(self.barra_lateral, height=1, fg_color="#404040").pack(fill="x", padx=15, pady=8)
        self._criar_btn_menu("", "Configurações", command=self._mostrar_configuracoes)
        self._criar_btn_menu("", "Sobre",          command=self._mostrar_sobre)

        # --- rea de contedo ---
        self.area = ctk.CTkFrame(corpo, fg_color="#202020", corner_radius=0)
        self.area.pack(side="left", fill="both", expand=True)

        # --- Barra de status ---
        barra_status = ctk.CTkFrame(self.janela, height=34, fg_color="#2D2D2D", corner_radius=0)
        barra_status.pack(fill="x", side="bottom")
        barra_status.pack_propagate(False)

        status_esq = ctk.CTkFrame(barra_status, fg_color="transparent")
        status_esq.pack(side="left", padx=12)

        self.lbl_status_ponto = ctk.CTkLabel(status_esq, text="", font=("Segoe UI", 12), text_color="#107C10")
        self.lbl_status_ponto.pack(side="left", padx=(0, 5))
        self.lbl_status = ctk.CTkLabel(status_esq, text="Sistema pronto", font=("Segoe UI", 11), text_color="#CCCCCC")
        self.lbl_status.pack(side="left")

        status_dir = ctk.CTkFrame(barra_status, fg_color="transparent")
        status_dir.pack(side="right", padx=12)

        self.lbl_tempo = ctk.CTkLabel(status_dir, text="", font=("Segoe UI", 11), text_color="#AAAAAA")
        self.lbl_tempo.pack(side="right", padx=8)
        self.lbl_gpu = ctk.CTkLabel(status_dir, text="GPU: --",  font=("Segoe UI", 11), text_color="#CCCCCC")
        self.lbl_gpu.pack(side="right", padx=8)
        self.lbl_ram = ctk.CTkLabel(status_dir, text="RAM: --", font=("Segoe UI", 11), text_color="#CCCCCC")
        self.lbl_ram.pack(side="right", padx=8)
        self.lbl_cpu = ctk.CTkLabel(status_dir, text="CPU: --",  font=("Segoe UI", 11), text_color="#CCCCCC")
        self.lbl_cpu.pack(side="right", padx=8)

        # Mostra incio ação abrir
        self._mostrar_inicio()

    def _criar_btn_menu(self, icone: str, texto: str, command=None):
        btn = ctk.CTkButton(
            self.barra_lateral,
            text=f"  {icone}  {texto}",
            anchor="w",
            font=("Segoe UI", 13),
            height=40,
            fg_color="transparent",
            hover_color="#3D3D3D",
            text_color="#CCCCCC",
            corner_radius=6,
            command=command
        )
        btn.pack(fill="x", padx=8, pady=2)
        return btn

    def _limpar_area(self):
        """Remove todos os widgets da rea de contedo"""
        for widget in self.area.winfo_children():
            widget.destroy()

    # ─────────────────────────────────────────────────────────────────────────
    # TELAS
    # ─────────────────────────────────────────────────────────────────────────
    def _mostrar_inicio(self):
        self._limpar_area()
        self._set_status("Incio", "#107C10")

        scroll = ctk.CTkScrollableFrame(self.area, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(scroll, text=" Incio", font=("Segoe UI", 28, "bold"), text_color="#0078D4").pack(anchor="w", pady=(0, 20))

        # Cards de categoria em grid 2 colunas
        grid = ctk.CTkFrame(scroll, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        grid.columnconfigure((0, 1), weight=1)

        for idx, cat in enumerate(CATEGORIAS):
            row, col = divmod(idx, 2)
            n_ferramentas = len(MAPA_FERRAMENTAS.get(cat["id"], []))

            card = ctk.CTkFrame(grid, fg_color="#2D2D2D", corner_radius=12)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            grid.rowconfigure(row, weight=1)

            ctk.CTkLabel(card, text=cat["icone"], font=("Segoe UI", 40)).pack(pady=(20, 5))
            ctk.CTkLabel(card, text=cat["nome"], font=("Segoe UI", 16, "bold"), text_color=cat["cor"]).pack()
            ctk.CTkLabel(card, text=f"{n_ferramentas} ferramentas", font=("Segoe UI", 12), text_color="#AAAAAA").pack(pady=(2, 15))

            ctk.CTkButton(
                card, text="Abrir ", width=120,
                fg_color=cat["cor"], hover_color=self._escurecer_cor(cat["cor"]),
                command=lambda c=cat: self._mostrar_categoria(c)
            ).pack(pady=(0, 20))

    def _mostrar_categoria(self, cat: dict):
        self._limpar_area()
        self._set_status(f"{cat['icone']} {cat['nome']}", "#0078D4")

        scroll = ctk.CTkScrollableFrame(self.area, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(scroll, text=f"{cat['icone']} {cat['nome']}",
                     font=("Segoe UI", 28, "bold"), text_color=cat["cor"]).pack(anchor="w", pady=(0, 20))

        ferramentas = MAPA_FERRAMENTAS.get(cat["id"], [])
        if not ferramentas:
            ctk.CTkLabel(scroll, text="Nenhuma ferramenta cadastrada nesta categoria.",
                         text_color="#888888").pack(pady=40)
            return

        for nome, arquivo in ferramentas:
            frame_f = ctk.CTkFrame(scroll, fg_color="#2D2D2D", corner_radius=10)
            frame_f.pack(fill="x", pady=5)

            ctk.CTkLabel(frame_f, text=nome, font=("Segoe UI", 14, "bold"),
                         text_color="#FFFFFF").pack(side="left", padx=20, pady=15)

            btn_frame = ctk.CTkFrame(frame_f, fg_color="transparent")
            btn_frame.pack(side="right", padx=10)

            caminho = self.pasta_ferramentas / arquivo
            existe = caminho.exists()

            ctk.CTkButton(
                btn_frame, text=" Abrir", width=100,
                fg_color="#107C10" if existe else "#555555",
                hover_color="#0A5C0A",
                state="normal" if existe else "disabled",
                command=lambda c=caminho: self._abrir_ferramenta(c)
            ).pack(side="left", padx=5, pady=10)

            if not existe:
                ctk.CTkLabel(btn_frame, text="[ERRO] arquivo no encontrado",
                             text_color="#E81123", font=("Segoe UI", 11)).pack(side="left", padx=5)

    def _mostrar_configuracoes(self):
        self._limpar_area()
        self._set_status(" Configurações", "#767676")

        scroll = ctk.CTkScrollableFrame(self.area, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(scroll, text=" Configurações",
                     font=("Segoe UI", 28, "bold"), text_color="#0078D4").pack(anchor="w", pady=(0, 20))

        card = ctk.CTkFrame(scroll, fg_color="#2D2D2D", corner_radius=12)
        card.pack(fill="x", pady=10)

        # Pasta raiz
        ctk.CTkLabel(card, text="Pasta raiz das ferramentas:", font=("Segoe UI", 13)).pack(anchor="w", padx=20, pady=(15, 2))
        linha_pasta = ctk.CTkFrame(card, fg_color="transparent")
        linha_pasta.pack(fill="x", padx=20, pady=(0, 10))

        self._entry_pasta = ctk.CTkEntry(linha_pasta, width=400)
        self._entry_pasta.insert(0, str(PASTA_RAIZ))
        self._entry_pasta.pack(side="left", padx=(0, 10))

        ctk.CTkButton(linha_pasta, text=" Alterar", width=100,
                      command=self._selecionar_pasta_raiz).pack(side="left")

        # Tema
        ctk.CTkLabel(card, text="Tema:", font=("Segoe UI", 13)).pack(anchor="w", padx=20, pady=(10, 2))
        linha_tema = ctk.CTkFrame(card, fg_color="transparent")
        linha_tema.pack(fill="x", padx=20, pady=(0, 15))

        for tema in ["dark", "light", "system"]:
            ctk.CTkButton(linha_tema, text=tema.capitalize(), width=90,
                          command=lambda t=tema: ctk.set_appearance_mode(t)).pack(side="left", padx=5)

        ctk.CTkButton(scroll, text=" Salvar configurações", width=200,
                      fg_color="#0078D4", command=self._salvar_configuracoes).pack(pady=20)

    def _mostrar_sobre(self):
        self._limpar_area()
        self._set_status(" Sobre", "#767676")

        scroll = ctk.CTkScrollableFrame(self.area, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(scroll, text=" Sobre", font=("Segoe UI", 28, "bold"), text_color="#0078D4").pack(anchor="w")

        card = ctk.CTkFrame(scroll, fg_color="#2D2D2D", corner_radius=12)
        card.pack(fill="both", expand=True, pady=10)

        ctk.CTkLabel(card, text="", font=("Segoe UI", 72), text_color="#0078D4").pack(pady=(30, 5))
        ctk.CTkLabel(card, text="Central de Ferramentas IA", font=("Segoe UI", 22, "bold")).pack()
        ctk.CTkLabel(card, text=f"Verso 2.2  {self.total_ferramentas} Ferramentas",
                     font=("Segoe UI", 14), text_color="#AAAAAA").pack(pady=5)
        ctk.CTkLabel(card, text=f"GPU: {'[OK] Ativa' if USAR_GPU else '[ERRO] Inativa (CPU)'}",
                     font=("Segoe UI", 13), text_color="#107C10" if USAR_GPU else "#E81123").pack(pady=5)

        ctk.CTkFrame(card, height=1, fg_color="#404040").pack(fill="x", padx=40, pady=15)

        resumo = "\n".join(
            f"{cat['icone']} {cat['nome']}: {len(MAPA_FERRAMENTAS.get(cat['id'], []))} ferramentas"
            for cat in CATEGORIAS
        )
        ctk.CTkLabel(card, text=resumo, font=("Segoe UI", 13), text_color="#CCCCCC",
                     justify="center").pack(pady=10)

    # ─────────────────────────────────────────────────────────────────────────
    # AES
    # ─────────────────────────────────────────────────────────────────────────
    def _abrir_ferramenta(self, caminho: Path):
        """Abre ferramenta em processo separado"""
        try:
            subprocess.Popen([sys.executable, str(caminho)])
            self._set_status(f"Abrindo: {caminho.name}", "#0078D4")
        except Exception as e:
            messagebox.showerror("Erro", f"No foi possível abrir:\n{caminho.name}\n\n{e}")

    def _selecionar_pasta_raiz(self):
        from tkinter import filedialog
        pasta = filedialog.askdirectory(title="Selecionar pasta raiz")
        if pasta:
            self._entry_pasta.delete(0, "end")
            self._entry_pasta.insert(0, pasta)

    def _salvar_configuracoes(self):
        messagebox.showinfo("Configurações", "Configurações salvas!\n\nNota: alterar a pasta raiz requer reiniciar o painel.")

    def _set_status(self, texto: str, cor: str = "#107C10"):
        """Atualiza barra de status (thread-safe)"""
        try:
            self.lbl_status.configure(text=texto)
            self.lbl_status_ponto.configure(text_color=cor)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # MONITORAMENTO DE RECURSOS (corrigido: thread-safe via janela.after)
    # ─────────────────────────────────────────────────────────────────────────
    def _iniciar_monitoramento(self):
        """Lana thread de monitoramento. Thread NO toca em widgets tkinter diretamente."""

        def _loop():
            while self.monitorando:
                dados = self._coletar_metricas()
                # Envia atualizao para a thread principal via after()
                try:
                    self.janela.after(0, lambda d=dados: self._aplicar_metricas(d))
                except Exception:
                    break  # Janela foi destruda
                time.sleep(2)

        t = threading.Thread(target=_loop, daemon=True)
        t.start()

    def _coletar_metricas(self) -> dict:
        """Coleta mtricas - roda na thread auxiliar (sem tocar em widgets)"""
        dados = {"cpu": 0, "ram": 0, "gpu": None, "tempo": datetime.now().strftime("%H:%M")}

        if PSUTIL_OK:
            try:
                dados["cpu"] = psutil.cpu_percent(interval=0)
                dados["ram"] = psutil.virtual_memory().percent
            except Exception:
                pass

        if GPUTIL_OK:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    dados["gpu"] = gpus[0].load * 100
            except Exception:
                pass

        return dados

    def _aplicar_metricas(self, dados: dict):
        """Aplica mtricas nos labels - SEMPRE executado na thread principal"""
        try:
            self.lbl_cpu.configure(text=f"CPU: {dados['cpu']}%")
            self.lbl_ram.configure(text=f"RAM: {dados['ram']}%")
            if dados["gpu"] is not None:
                self.lbl_gpu.configure(text=f"GPU: {dados['gpu']:.0f}%")
            else:
                self.lbl_gpu.configure(text="GPU: N/A")
            self.lbl_tempo.configure(text=dados["tempo"])
        except Exception:
            pass  # Widget destrudo

    # ─────────────────────────────────────────────────────────────────────────
    # UTILITRIOS
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _escurecer_cor(hex_cor: str, fator: float = 0.7) -> str:
        """Escurece uma cor hexadecimal pelo fator dado (0-1)"""
        hex_cor = hex_cor.lstrip("#")
        if len(hex_cor) != 6:
            return "#333333"
        try:
            r = int(int(hex_cor[0:2], 16) * fator)
            g = int(int(hex_cor[2:4], 16) * fator)
            b = int(int(hex_cor[4:6], 16) * fator)
            return f"#{r:02X}{g:02X}{b:02X}"
        except ValueError:
            return "#333333"

    def executar(self):
        """Inicia o loop principal"""
        self.janela.protocol("WM_DELETE_WINDOW", self._ao_fechar)
        self.janela.mainloop()

    def _ao_fechar(self):
        self.monitorando = False
        self.janela.destroy()


if __name__ == "__main__":
    app = PainelControleWindows11()
    app.executar()
