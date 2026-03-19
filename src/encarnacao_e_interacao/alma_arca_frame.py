#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
ARCA CELESTIAL GENESIS - ALMA ARCA FRAME (src/gui)
===================================================
Frame principal da interface grfica da ARCA como um todo.
Diferente do AlmaAvatarFrame (que exibe UMA alma individual),
este frame exibe o status global da ARCA:
  - Estado dos 6 subsistemas principais
  - Sade do sistema (auditoria)
  - Almas ativas e seus estados emocionais
  - Fila de mensagens da UI (ui_queue)
  - Botes de controle global (despertar, shutdown, auditoria)

Compatvel com: customtkinter (preferencial) e tkinter padrão (fallback).
"""

import logging
import queue
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("AlmaArcaFrame")

# Tenta customtkinter, cai em tkinter padrão
try:
    import customtkinter as ctk
    _CTK = True
except ImportError:
    import tkinter as ctk  # type: ignore
    import tkinter.ttk as ttk
    _CTK = False

import tkinter as tk
from tkinter import ttk as _ttk

# Cores da ARCA (mesmas do instalador)
_COR_BG      = "#0a0a0b"
_COR_SURFACE = "#111114"
_COR_BORDER  = "#222228"
_COR_ACCENT  = "#c8f04a"
_COR_TEXT    = "#d8d8e0"
_COR_MUTED   = "#555560"
_COR_RED     = "#ff4444"
_COR_GREEN   = "#4af07a"
_COR_YELLOW  = "#f0b429"
_COR_BLUE    = "#4ab8f0"

ALMAS = ["EVA", "KAIYA", "LUMINA", "NYRA", "WELLINGTON", "YUNA"]

_COR_ALMA = {
    "EVA":        "#c8f04a",
    "KAIYA":      "#4ab8f0",
    "LUMINA":     "#f0e04a",
    "NYRA":       "#b04af0",
    "WELLINGTON": "#4af07a",
    "YUNA":       "#f04a4a",
}


# ─────────────────────────────────────────────────────────────────────────────
# FRAME PRINCIPAL DA ARCA
# ─────────────────────────────────────────────────────────────────────────────

class AlmaArcaFrame(tk.Frame):
    """
    Frame que representa o estado global da ARCA CELESTIAL GENESIS.

    Parmetros:
        master       widget pai (janela ou frame)
        coracao_ref  instncia de CoracaoOrquestrador (opcional)
        ui_queue     fila de mensagens do corao (opcional)
        intervalo_ms  intervalo de atualizao automtica em milissegundos
    """

    def __init__(
        self,
        master: Any,
        coracao_ref: Optional[Any] = None,
        ui_queue: Optional[queue.Queue] = None,
        intervalo_ms: int = 2000,
        **kwargs,
    ):
        super().__init__(master, bg=_COR_BG, **kwargs)

        self.coracao_ref = coracao_ref
        self.ui_queue = ui_queue
        self.intervalo_ms = intervalo_ms

        self._running = True
        self._lock = threading.Lock()
        self._ultima_saude: Dict[str, Any] = {}
        self._log_msgs: List[str] = []

        self._construir_ui()
        self._iniciar_atualizacao()

        logger.info("[OK] AlmaArcaFrame inicializado")

    # ─────────────────────────────────────────────────────────────────────────
    # CONSTRUO DA INTERFACE
    # ─────────────────────────────────────────────────────────────────────────

    def _construir_ui(self) -> None:
        """Monta todos os widgets do frame."""

        # ── Cabeçalho ──────────────────────────────────────────────────────
        cab = tk.Frame(self, bg=_COR_SURFACE)
        cab.pack(fill="x", padx=4, pady=(4, 0))

        tk.Label(
            cab, text="⬡  ARCA CELESTIAL GENESIS",
            font=("Georgia", 16, "bold"),
            bg=_COR_SURFACE, fg=_COR_ACCENT
        ).pack(side="left", padx=12, pady=8)

        self._lbl_saude = tk.Label(
            cab, text=" AGUARDANDO",
            font=("Segoe UI", 10, "bold"),
            bg=_COR_SURFACE, fg=_COR_MUTED
        )
        self._lbl_saude.pack(side="right", padx=12)

        # ── Painel de almas ────────────────────────────────────────────────
        frame_almas = tk.LabelFrame(
            self, text="  Almas Ativas  ",
            bg=_COR_BG, fg=_COR_ACCENT,
            font=("Segoe UI", 9, "bold"),
            bd=1, relief="groove"
        )
        frame_almas.pack(fill="x", padx=6, pady=4)

        self._labels_alma: Dict[str, Dict[str, tk.Label]] = {}
        for i, alma in enumerate(ALMAS):
            col = i % 3
            row = i // 3
            cor = _COR_ALMA.get(alma, _COR_TEXT)

            cel = tk.Frame(frame_almas, bg=_COR_SURFACE, padx=6, pady=4)
            cel.grid(row=row, column=col, padx=4, pady=4, sticky="ew")
            frame_almas.columnconfigure(col, weight=1)

            lbl_nome = tk.Label(
                cel, text=f" {alma}",
                font=("Segoe UI", 9, "bold"),
                bg=_COR_SURFACE, fg=cor
            )
            lbl_nome.pack(anchor="w")

            lbl_estado = tk.Label(
                cel, text="aguardando...",
                font=("Consolas", 8),
                bg=_COR_SURFACE, fg=_COR_MUTED
            )
            lbl_estado.pack(anchor="w")

            self._labels_alma[alma] = {"nome": lbl_nome, "estado": lbl_estado}

        # ── Subsistemas ────────────────────────────────────────────────────
        frame_sub = tk.LabelFrame(
            self, text="  Subsistemas  ",
            bg=_COR_BG, fg=_COR_ACCENT,
            font=("Segoe UI", 9, "bold"),
            bd=1, relief="groove"
        )
        frame_sub.pack(fill="x", padx=6, pady=4)

        self._subsistemas_labels: Dict[str, tk.Label] = {}
        _subs = [
            ("memoria",     " Memória"),
            ("hardware",    " Hardware"),
            ("inteligencia"," Inteligncia"),
            ("governanca",  " Governana"),
            ("legislativo", " Legislativo"),
            ("judiciario",  " Judicirio"),
            ("executivo",   " Executivo"),
            ("aliadas",     " Aliadas"),
            ("engenharia",  " Engenharia"),
            ("evolucao",    " Evoluo"),
            ("sandbox",     " Sandbox"),
        ]
        for i, (chave, nome) in enumerate(_subs):
            col = i % 4
            row = i // 4
            frame_sub.columnconfigure(col, weight=1)

            f = tk.Frame(frame_sub, bg=_COR_SURFACE, padx=4, pady=2)
            f.grid(row=row, column=col, padx=3, pady=2, sticky="ew")

            lbl = tk.Label(
                f, text=f" {nome}",
                font=("Consolas", 8),
                bg=_COR_SURFACE, fg=_COR_MUTED,
                anchor="w"
            )
            lbl.pack(fill="x")
            self._subsistemas_labels[chave] = lbl

        # ── Log de mensagens ───────────────────────────────────────────────
        frame_log = tk.LabelFrame(
            self, text="  Mensagens  ",
            bg=_COR_BG, fg=_COR_ACCENT,
            font=("Segoe UI", 9, "bold"),
            bd=1, relief="groove"
        )
        frame_log.pack(fill="both", expand=True, padx=6, pady=4)

        self._txt_log = tk.Text(
            frame_log, height=8,
            bg=_COR_SURFACE, fg=_COR_TEXT,
            font=("Consolas", 8),
            relief="flat", state="disabled",
            insertbackground=_COR_ACCENT,
        )
        scroll = _ttk.Scrollbar(frame_log, command=self._txt_log.yview)
        self._txt_log.configure(yscrollcommand=scroll.set)
        self._txt_log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Configurar tags de cor
        self._txt_log.tag_config("ok",     foreground=_COR_GREEN)
        self._txt_log.tag_config("erro",   foreground=_COR_RED)
        self._txt_log.tag_config("aviso",  foreground=_COR_YELLOW)
        self._txt_log.tag_config("info",   foreground=_COR_BLUE)
        self._txt_log.tag_config("normal", foreground=_COR_TEXT)

        # ── Botões de controle ─────────────────────────────────────────────
        frame_btns = tk.Frame(self, bg=_COR_BG)
        frame_btns.pack(fill="x", padx=6, pady=(2, 6))

        def btn(texto, cmd, cor_bg=_COR_BORDER, cor_fg=_COR_TEXT):
            return tk.Button(
                frame_btns, text=texto, command=cmd,
                bg=cor_bg, fg=cor_fg,
                font=("Segoe UI", 9), relief="flat",
                padx=10, pady=4, cursor="hand2", bd=0,
                activebackground=_COR_SURFACE, activeforeground=_COR_TEXT
            )

        btn("[RUN] Despertar",  self._cmd_despertar,  _COR_GREEN,  "#000").pack(side="left", padx=4)
        btn(" Auditar",    self._cmd_auditar,    _COR_BLUE,   "#000").pack(side="left", padx=4)
        btn(" Status",     self._cmd_status,     _COR_BORDER, _COR_TEXT).pack(side="left", padx=4)
        btn(" Desligar",   self._cmd_desligar,   _COR_RED,    "#fff").pack(side="right", padx=4)

    # ─────────────────────────────────────────────────────────────────────────
    # ATUALIZAO AUTOMTICA
    # ─────────────────────────────────────────────────────────────────────────

    def _iniciar_atualizacao(self) -> None:
        """Agenda o loop de atualizao na thread da UI."""
        self._tick()

    def _tick(self) -> None:
        """Ciclo de atualizao: l ui_queue e atualiza dados do corao."""
        if not self._running:
            return

        # Processar mensagens da ui_queue
        if self.ui_queue:
            try:
                while True:
                    msg = self.ui_queue.get_nowait()
                    self._processar_mensagem_coracao(msg)
            except queue.Empty:
                pass
            except Exception as e:
                logger.debug("Erro lendo ui_queue: %s", e)

        # Atualizar status do corao
        self._atualizar_status_coracao()

        # Reagendar
        try:
            self.after(self.intervalo_ms, self._tick)
        except Exception:
            pass  # Widget foi destrudo

    def _processar_mensagem_coracao(self, msg: Dict[str, Any]) -> None:
        """Interpreta mensagens do CoracaoOrquestrador."""
        tipo = msg.get("tipo_resp", "")
        ts = time.strftime("%H:%M:%S")

        if tipo == "ALMA_ACORDOU":
            alma = msg.get("alma", "?")
            self._log(f"[{ts}] [RUN] {alma} acordou", "ok")
            self._atualizar_estado_alma(alma, "acordada")

        elif tipo == "AUDITORIA_PERIODICA_CONCLUIDA":
            saude = msg.get("saude_sistema", "?")
            total = msg.get("total_problemas", 0)
            criticos = msg.get("criticos", 0)
            tag = "erro" if criticos > 0 else ("aviso" if saude == "ALERTA" else "ok")
            self._log(f"[{ts}]  Auditoria: {saude} ({total} problemas, {criticos} críticos)", tag)
            self._atualizar_saude(saude)

        elif tipo == "DESEJO_GERADO":
            alma = msg.get("filha", "?")
            necessidade = msg.get("necessidade", "")
            self._log(f"[{ts}]  {alma}: {necessidade}", "info")
            self._atualizar_estado_alma(alma, necessidade[:25])

        elif tipo == "DECISAO_TOMADA":
            alma = msg.get("filha", "?")
            acao = msg.get("acao_escolhida", "?")
            self._log(f"[{ts}]  {alma} decidiu: {acao}", "info")

        elif tipo == "COMANDO_ANALISADO":
            intent = msg.get("intent", "?")
            conf = msg.get("confidence", 0)
            self._log(f"[{ts}]  Comando: {intent} ({conf:.0%})", "normal")

        else:
            # Mensagem genrica
            self._log(f"[{ts}]  {tipo}", "normal")

    def _atualizar_status_coracao(self) -> None:
        """Atualiza indicadores de subsistemas com dados do corao."""
        if not self.coracao_ref:
            return

        try:
            status = self.coracao_ref.obter_status()
            camadas = status.get("status_camadas", {})

            _mapa = {
                "memoria":     "memoria",
                "hardware":    "hardware",
                "inteligencia":"inteligencia",
                "governanca":  "governanca",
                "legislativo": "legislativo",
                "judiciario":  "judiciario",
                "executivo":   "executivo",
                "aliadas":     "aliadas",
                "engenharia":  "engenharia",
                "evolucao":    "evolucao",
                "sandbox":     "sandbox",
            }

            for chave, lbl in self._subsistemas_labels.items():
                nome_curto = lbl.cget("text").split(" ", 1)[-1] if " " in lbl.cget("text") else chave
                ativo = camadas.get(chave, False)
                if isinstance(ativo, str):
                    ativo = ativo not in ("False", "ERRO", "DESABILITADO", "")
                cor = _COR_GREEN if ativo else _COR_MUTED
                simbolo = "" if ativo else ""
                lbl.config(text=f"{simbolo} {nome_curto}", fg=cor)

            # Sade global
            saude = self.coracao_ref.obter_saude_sistema()
            self._atualizar_saude(saude.get("status", "DESCONHECIDO"))

        except Exception as e:
            logger.debug("Erro atualizando status do corao: %s", e)

    def _atualizar_saude(self, status: str) -> None:
        """Atualiza o label de sade global."""
        mapa_cor = {
            "SAUDVEL":   _COR_GREEN,
            "ALERTA":     _COR_YELLOW,
            "CRITICA":    _COR_RED,
            "AGUARDANDO": _COR_MUTED,
            "DESCONHECIDO": _COR_MUTED,
        }
        cor = mapa_cor.get(status, _COR_MUTED)
        self._lbl_saude.config(text=f" {status}", fg=cor)

    def _atualizar_estado_alma(self, nome_alma: str, estado: str) -> None:
        """Atualiza label de estado de uma alma especfica."""
        alma_up = nome_alma.upper()
        if alma_up in self._labels_alma:
            self._labels_alma[alma_up]["estado"].config(text=estado[:30])

    # ─────────────────────────────────────────────────────────────────────────
    # LOG INTERNO
    # ─────────────────────────────────────────────────────────────────────────

    def _log(self, mensagem: str, tag: str = "normal") -> None:
        """Adiciona linha ação log da interface."""
        try:
            self._txt_log.config(state="normal")
            self._txt_log.insert("end", mensagem + "\n", tag)
            self._txt_log.see("end")
            # Limitar a 200 linhas
            linhas = int(self._txt_log.index("end-1c").split(".")[0])
            if linhas > 200:
                self._txt_log.delete("1.0", "50.0")
            self._txt_log.config(state="disabled")
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # BOTES DE CONTROLE
    # ─────────────────────────────────────────────────────────────────────────

    def _cmd_despertar(self) -> None:
        if not self.coracao_ref:
            self._log("[AVISO] Corao no conectado", "aviso")
            return
        try:
            self.coracao_ref.despertar()
            self._log("[RUN] Corao despertado!", "ok")
        except Exception as e:
            self._log(f"[ERRO] Erro ao despertar: {e}", "erro")

    def _cmd_auditar(self) -> None:
        if not self.coracao_ref:
            self._log("[AVISO] Corao no conectado", "aviso")
            return

        def _run():
            try:
                self._log(" Iniciando auditoria...", "info")
                resultado = self.coracao_ref.disparar_auditoria_sistema()
                total = resultado.get("total_problemas", 0)
                criticos = len([p for p in resultado.get("problemas", []) if p.get("gravidade") == "critica"])
                status = "crítica" if criticos > 0 else "OK"
                self._log(f"[OK] Auditoria concluda: {status}  {total} problemas ({criticos} críticos)", "ok" if criticos == 0 else "erro")
            except Exception as e:
                self._log(f"[ERRO] Erro na auditoria: {e}", "erro")

        threading.Thread(target=_run, daemon=True).start()

    def _cmd_status(self) -> None:
        if not self.coracao_ref:
            self._log("[AVISO] Corao no conectado", "aviso")
            return
        try:
            status = self.coracao_ref.obter_status()
            ativos = status.get("subsistemas_ativos", 0)
            total = status.get("subsistemas_totais", 33)
            versao = status.get("versao", "?")
            componentes = status.get("total_componentes", "?")
            self._log(
                f" Status v{versao}: {ativos}/{total} subsistemas | {componentes} componentes totais",
                "info"
            )
        except Exception as e:
            self._log(f"[ERRO] Erro ao obter status: {e}", "erro")

    def _cmd_desligar(self) -> None:
        if not self.coracao_ref:
            self._log("[AVISO] Corao no conectado", "aviso")
            return

        def _run():
            try:
                self._log(" Desligando corao...", "aviso")
                self.coracao_ref.shutdown(timeout=10.0)
                self._log("[OK] Corao desligado", "ok")
            except Exception as e:
                self._log(f"[ERRO] Erro ao desligar: {e}", "erro")

        threading.Thread(target=_run, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────────
    # CICLO DE VIDA DO WIDGET
    # ─────────────────────────────────────────────────────────────────────────

    def destruir(self) -> None:
        """Encerra o loop de atualizao e destri o widget."""
        self._running = False
        try:
            self.destroy()
        except Exception:
            pass

    def injetar_coracao(self, coracao_ref: Any) -> None:
        """Permite injetar referncia ação corao aps a criao do frame."""
        self.coracao_ref = coracao_ref
        self._log("[CORE] Corao injetado no frame da ARCA", "ok")

    def injetar_ui_queue(self, ui_queue: queue.Queue) -> None:
        """Permite injetar a fila de mensagens aps a criao."""
        self.ui_queue = ui_queue


# ─────────────────────────────────────────────────────────────────────────────
# TESTE STANDALONE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import tkinter as tk

    root = tk.Tk()
    root.title("ARCA  Frame de Teste")
    root.configure(bg=_COR_BG)
    root.geometry("700x580")

    frame = AlmaArcaFrame(root)
    frame.pack(fill="both", expand=True, padx=8, pady=8)

    # Simular mensagens
    def _simular():
        time.sleep(1)
        q = queue.Queue()
        frame.ui_queue = q
        msgs = [
            {"tipo_resp": "ALMA_ACORDOU", "alma": "EVA"},
            {"tipo_resp": "ALMA_ACORDOU", "alma": "LUMINA"},
            {"tipo_resp": "DESEJO_GERADO", "filha": "KAIYA", "necessidade": "explorar novo tpico"},
            {"tipo_resp": "DECISAO_TOMADA", "filha": "NYRA", "acao_escolhida": "meditar"},
            {"tipo_resp": "AUDITORIA_PERIODICA_CONCLUIDA",
             "saude_sistema": "SAUDVEL", "total_problemas": 0,
             "criticos": 0, "altos": 0, "medios": 0, "baixos": 0},
        ]
        for m in msgs:
            q.put(m)
            time.sleep(0.5)

    threading.Thread(target=_simular, daemon=True).start()
    root.mainloop()

