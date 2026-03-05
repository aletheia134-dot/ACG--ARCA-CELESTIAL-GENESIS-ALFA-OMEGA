# interface_arca.py - v2 CORRIGIDA
# -*- coding: utf-8 -*-
"""
INTERFACE ARCA COMPLETA v2 - CORRIGIDA
- Erro do JobManager/responde_queue resolvido
- Caracteres especiais normalizados
- Proteção contra atributos incorretos
"""

import json
import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import customtkinter as ctk
import tkinter.messagebox as messagebox

logger = logging.getLogger("InterfaceArcaCompleta")
logger.addHandler(logging.NullHandler())

if TYPE_CHECKING:
    from coracao_orquestrador import CoracaoOrquestrador

ALMAS = ["EVA", "KAIYA", "LUMINA", "NYRA", "WELLINGTON", "YUNA"]

@dataclass
class Comando:
    origem: str
    destino: str
    acao: str
    payload: Dict[str, Any]
    prioridade: int = 5
    timestamp: float = field(default_factory=time.time)


class PainelBase:
    def __init__(self, parent, coracao, ui_ref):
        self.parent = parent
        self.coracao = coracao
        self.ui_ref = ui_ref
        self.frame = ctk.CTkFrame(parent)
        self._visible = False
        ctk.CTkButton(
            self.frame, text="⬅️ Desktop",
            command=self._voltar_ao_desktop,
            fg_color="#3a3a3a", width=120, height=28,
        ).pack(anchor="nw", padx=8, pady=(6, 2))

    def _voltar_ao_desktop(self):
        try: self.ui_ref._mostrar_desktop()
        except Exception: pass

    def show(self):
        self.frame.pack(fill="both", expand=True)
        self._visible = True

    def hide(self):
        self.frame.pack_forget()
        self._visible = False

    def refresh(self): pass

    def _show_result(self, result):
        if not hasattr(self, "result_text"): return
        try:
            self.result_text.configure(state="normal")
            self.result_text.delete("0.0", "end")
            if isinstance(result, str):
                self.result_text.insert("end", result)
            elif result is None:
                self.result_text.insert("end", "Resultado: None")
            else:
                self.result_text.insert("end", json.dumps(result, ensure_ascii=False, indent=2, default=str))
            self.result_text.configure(state="disabled")
        except Exception as e:
            logger.warning("_show_result: %s", e)

    def _append_result(self, text: str):
        if not hasattr(self, "result_text"): return
        try:
            self.result_text.configure(state="normal")
            self.result_text.insert("end", text + "\n")
            self.result_text.configure(state="disabled")
            self.result_text.see("end")
        except Exception: pass

    def _clear_result(self):
        if not hasattr(self, "result_text"): return
        try:
            self.result_text.configure(state="normal")
            self.result_text.delete("0.0", "end")
            self.result_text.configure(state="disabled")
        except Exception: pass

    def _handle_error(self, msg: str, exc=None):
        full = f"❌ ERRO: {msg}"
        if exc:
            full += f"\n   Detalhe: {type(exc).__name__}: {exc}"
        try: messagebox.showerror("Erro", full)
        except Exception: pass
        logger.error(full)
        if hasattr(self, "result_text"):
            self._show_result(full)

    def _modulo_indisponivel(self, attr: str):
        msg = (
            f"⚠️ Módulo NÍO disponível: coracao.{attr}\n\n"
            f"Possíveis causas:\n"
            f"  • Dependência não instalada\n"
            f"  • Erro na inicialização do CoracaoOrquestrador\n"
            f"  • Coração não injetado na interface\n\n"
            f"Verifique os logs do CoracaoOrquestrador para detalhes."
        )
        if hasattr(self, "result_text"):
            self._show_result(msg)
        else:
            try: messagebox.showwarning("Módulo Indisponível", msg)
            except Exception: pass

    def _require_alma(self, alma: str, campo: str = "alma") -> bool:
        """Retorna True se alma não está vazia. Exibe erro e retorna False se estiver."""
        if not alma:
            self._handle_error(f"Campo '{campo}' é obrigatório. Preencha antes de continuar.")
            return False
        return True

    def _make_result(self, height=260):
        self.result_text = ctk.CTkTextbox(self.frame, height=height)
        self.result_text.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self.result_text.configure(state="disabled")

    def _lbl(self, text, bold=False, size=13):
        ctk.CTkLabel(self.frame, text=text, font=ctk.CTkFont(size=size, weight="bold" if bold else "normal")).pack(pady=(4, 1))

    def _entry(self, placeholder, width=None):
        kw = {"placeholder_text": placeholder}
        if width: kw["width"] = width
        e = ctk.CTkEntry(self.frame, **kw)
        e.pack(fill="x" if not width else None, padx=8, pady=2)
        return e

    def _grid_btns(self, parent, btns):
        for i, (txt, cmd, r, c) in enumerate(btns):
            ctk.CTkButton(parent, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            parent.columnconfigure(c, weight=1)

# --------------------------------------------------------------------
#  DESKTOP
# --------------------------------------------------------------------

class PainelDesktop(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self._build()

    def _build(self):
        ctk.CTkLabel(self.frame, text="🚀 Arca Celestial — Genesis Alfa Omega 🚀",
            font=ctk.CTkFont(size=36, weight="bold")).pack(pady=36)
        self.lbl_status = ctk.CTkLabel(self.frame, text=self._status_text(), font=ctk.CTkFont(size=15))
        self.lbl_status.pack(pady=4)
        self.lbl_modo = ctk.CTkLabel(self.frame, text=self._modo_text(), font=ctk.CTkFont(size=13), text_color="gray")
        self.lbl_modo.pack(pady=2)
        self.lbl_modulos = ctk.CTkLabel(self.frame, text=self._modulos_text(), font=ctk.CTkFont(size=11), text_color="#888", wraplength=900)
        self.lbl_modulos.pack(pady=2)
        ctk.CTkButton(self.frame, text="📱  Arca Menu — Todos os Apps",
            command=self.ui_ref._abrir_menu_iniciar,
            font=ctk.CTkFont(size=18), width=280, height=60).pack(pady=20)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(pady=8)
        ctk.CTkButton(bf, text="⚡ Despertar Arca", fg_color="#1a6b1a",
            command=self._despertar, width=170, height=42).grid(row=0, column=0, padx=6)
        ctk.CTkButton(bf, text="📊 Status Completo",
            command=self._status_completo, width=170, height=42).grid(row=0, column=1, padx=6)
        ctk.CTkButton(bf, text="🔴 Desligar Arca", fg_color="red",
            command=self.ui_ref.shutdown, width=170, height=42).grid(row=0, column=2, padx=6)

    def _status_text(self):
        if not self.coracao: return "⚠️ Coração NÍO injetado"
        rodando = getattr(self.coracao, "rodando", None)
        if rodando is None: return "🟡 Coração presente (sem atributo 'rodando')"
        return "🟢 Coração Online" if rodando else "🔴 Coração Offline"

    def _modo_text(self):
        if not self.coracao: return ""
        return f"Modo Sandbox: {getattr(self.coracao, 'modo_sandbox', 'DESCONHECIDO')}"

    def _modulos_text(self):
        if not self.coracao: return ""
        modulos = getattr(self.coracao, "modulos", {})
        ativos = sum(1 for v in modulos.values() if v is not None)
        return f"Módulos: {ativos}/{len(modulos)} ativos"

    def refresh(self):
        try:
            self.lbl_status.configure(text=self._status_text())
            self.lbl_modo.configure(text=self._modo_text())
            self.lbl_modulos.configure(text=self._modulos_text())
        except Exception: pass

    def _despertar(self):
        if self.coracao and hasattr(self.coracao, "despertar"):
            try:
                self.coracao.despertar()
                messagebox.showinfo("Arca", "Arca despertada com sucesso.")
            except Exception as e:
                self._handle_error("Erro ao despertar", e)
        else:
            self._modulo_indisponivel("despertar()")

    def _status_completo(self):
        if not self.coracao:
            messagebox.showwarning("Status", "Coração não injetado.")
            return
        try:
            status = {}
            if hasattr(self.coracao, "obter_saude_sistema"):
                status = self.coracao.obter_saude_sistema() or {}
            elif hasattr(self.coracao, "obter_status"):
                status = self.coracao.obter_status() or {}
            modulos = getattr(self.coracao, "modulos", {})
            status["modulos_ativos"] = [k for k, v in modulos.items() if v is not None]
            status["modulos_inativos"] = [k for k, v in modulos.items() if v is None]
            status["modo_sandbox"] = getattr(self.coracao, "modo_sandbox", "N/D")
            status["almas_vivas"] = list(getattr(self.coracao, "almas_vivas", {}).keys())
            top = ctk.CTkToplevel(self.parent)
            top.title("Status Geral da Arca")
            top.geometry("750x600")
            tb = ctk.CTkTextbox(top, wrap="word")
            tb.pack(fill="both", expand=True, padx=10, pady=10)
            tb.insert("end", json.dumps(status, ensure_ascii=False, indent=2, default=str))
            tb.configure(state="disabled")
        except Exception as e:
            self._handle_error("Erro ao obter status", e)


# --------------------------------------------------------------------
#  CHAT INDIVIDUAL — Avatar + Voz + Emoção + Iniciativa + Decisão
# --------------------------------------------------------------------

class PainelChatIndividual(PainelBase):
    EMOCOES = [
        "neutralidade_equilibrada", "alegria_leve", "curiosidade_ativa",
        "serenidade_contemplativa", "entusiasmo_criativo", "empatia_profunda",
        "melancolia_suave", "determinacao_calma", "admiracao_sincera",
    ]

    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.chat_history: Dict[str, List[str]] = {a: [] for a in ALMAS}
        self.current_ai = "WELLINGTON"
        self.avatar_image = None
        self._build()

    def _get_motor_expressao(self, nome):
        if not self.coracao: return None
        if hasattr(self.coracao, "obter_motor_expressao_individual"):
            try: return self.coracao.obter_motor_expressao_individual(nome)
            except Exception: pass
        return getattr(self.coracao, "motores_expressao_individual", {}).get(nome)

    def _get_motor_fala(self, nome):
        if not self.coracao: return None
        return getattr(self.coracao, "motores_fala", {}).get(nome)

    def _build(self):
        self._lbl("💬 Chat Individual com as Almas", bold=True, size=15)
        top_f = ctk.CTkFrame(self.frame)
        top_f.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(top_f, text="Alma:").grid(row=0, column=0, padx=4)
        self.ai_combo = ctk.CTkComboBox(top_f, values=ALMAS, command=self._change_ai, width=160)
        self.ai_combo.grid(row=0, column=1, padx=4)
        self.ai_combo.set("WELLINGTON")
        ctk.CTkLabel(top_f, text="Emoção:").grid(row=0, column=2, padx=4)
        self.emocao_combo = ctk.CTkComboBox(top_f, values=self.EMOCOES, width=220)
        self.emocao_combo.grid(row=0, column=3, padx=4)
        self.emocao_combo.set("neutralidade_equilibrada")
        ctk.CTkLabel(top_f, text="Idioma:").grid(row=0, column=4, padx=4)
        self.idioma_combo = ctk.CTkComboBox(top_f, values=["pt", "ja", "en"], width=60)
        self.idioma_combo.grid(row=0, column=5, padx=4)
        self.idioma_combo.set("pt")

        self.avatar_label = ctk.CTkLabel(self.frame, text="🤖", font=ctk.CTkFont(size=48))
        self.avatar_label.pack(pady=4)
        self.estado_label = ctk.CTkLabel(self.frame, text="Estado: —", font=ctk.CTkFont(size=11), text_color="gray")
        self.estado_label.pack()
        self._update_avatar()

        self.chat_text = ctk.CTkTextbox(self.frame, height=200)
        self.chat_text.pack(fill="both", expand=True, padx=8, pady=4)

        msg_f = ctk.CTkFrame(self.frame)
        msg_f.pack(fill="x", padx=8, pady=2)
        self.message_entry = ctk.CTkEntry(msg_f, placeholder_text="Mensagem...")
        self.message_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.message_entry.bind("<Return>", lambda e: self._send())
        ctk.CTkButton(msg_f, text="📤", command=self._send, width=40).pack(side="left")

        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=2)
        btns = [
            ("🎤 Falar", self._falar, 0, 0),
            ("🎭 Cena Emocional", self._cena_emocional, 0, 1),
            ("✨ Aplicar Emoção", self._aplicar_emocao, 0, 2),
            ("💡 Iniciativa", self._iniciativa, 0, 3),
            ("💭 Desejo Alma", self._gerar_desejo, 1, 0),
            ("📊 Estado Interno", self._estado_interno, 1, 1),
            ("📈 Métricas Curiosidade", self._metricas, 1, 2),
            ("⏸️ Parar Fala", self._parar_fala, 1, 3),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=30).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        ctk.CTkButton(self.frame, text="🗑️ Limpar Chat", command=self._limpar, fg_color="#4a0000", height=28).pack(pady=2)
        self._update_chat()

    def _change_ai(self, ai):
        self.current_ai = ai
        self._update_avatar()
        self._update_chat()

    def _update_avatar(self):
        try:
            motor = self._get_motor_expressao(self.current_ai)
            avatar_path = None
            if motor and hasattr(motor, "obter_caminho_avatar"):
                try: avatar_path = motor.obter_caminho_avatar(self.current_ai)
                except Exception: pass
            if not avatar_path:
                alt = Path("Assets/Avatares") / self.current_ai / "neutralidade_equilibrada.png"
                if alt.exists(): avatar_path = str(alt)
            if avatar_path and Path(str(avatar_path)).exists():
                from PIL import Image
                img = Image.open(str(avatar_path)).convert("RGBA").resize((400, 400))
                self.avatar_image = ctk.CTkImage(img, size=(400, 400))
                self.avatar_label.configure(image=self.avatar_image, text="")
            else:
                estado_txt = "—"
                if motor and hasattr(motor, "obter_estado_atual"):
                    try:
                        est = motor.obter_estado_atual()
                        estado_txt = est.get("expressao", "—") if isinstance(est, dict) else str(est)
                    except Exception: pass
                self.avatar_label.configure(text=f"🤖\n{self.current_ai}", image=None, font=ctk.CTkFont(size=28, weight="bold"))
                try: self.estado_label.configure(text=f"Expressão: {estado_txt}")
                except Exception: pass
            if self.coracao and hasattr(self.coracao, "obter_estado_emocional_alma"):
                try:
                    est = self.coracao.obter_estado_emocional_alma(self.current_ai)
                    if est and isinstance(est, dict):
                        resumo = est.get("emocao_dominante") or est.get("estado") or str(est)[:60]
                        self.estado_label.configure(text=f"Emoção: {resumo}")
                except Exception: pass
        except Exception:
            try: self.avatar_label.configure(text=f"🤖 {self.current_ai}", image=None)
            except Exception: pass

    def _send(self):
        msg = self.message_entry.get().strip()
        if not msg: return
        self.chat_history[self.current_ai].append(f"Você: {msg}")
        cq = getattr(self.ui_ref, "command_queue", None)
        if cq is not None:
            try:
                cq.put_nowait(Comando("UI", self.current_ai, "CHAT", {"texto": msg}))
                self.chat_history[self.current_ai].append(f"{self.current_ai}: [aguardando resposta...]")
            except Exception as e:
                self.chat_history[self.current_ai].append(f"❌ Erro na fila: {e}")
        elif self.coracao and hasattr(self.coracao, "salvar_memoria_alma"):
            try:
                self.coracao.salvar_memoria_alma(self.current_ai, f"msg_{int(time.time())}", msg)
                self.chat_history[self.current_ai].append(f"{self.current_ai}: [salvo na memória - sem fila]")
            except Exception as e:
                self.chat_history[self.current_ai].append(f"❌ Erro ao salvar: {e}")
        else:
            self.chat_history[self.current_ai].append("❌ command_queue e salvar_memoria_alma indisponíveis.")
        try: self.message_entry.delete(0, "end")
        except Exception: pass
        self._update_chat()

    def _falar(self):
        msg = self.message_entry.get().strip() or "(sem mensagem)"
        idioma = self.idioma_combo.get()
        if self.coracao and hasattr(self.coracao, "falar_ia"):
            try:
                ok = self.coracao.falar_ia(self.current_ai, msg, idioma)
                self.chat_history[self.current_ai].append(f"🗣️ {self.current_ai} [{idioma}]: {msg} — {'OK' if ok else 'falha'}")
            except Exception as e:
                self._handle_error("Erro ao falar_ia", e)
        else:
            motor = self._get_motor_fala(self.current_ai)
            if motor and hasattr(motor, "falar"):
                try:
                    motor.falar(msg)
                    self.chat_history[self.current_ai].append(f"🗣️ {self.current_ai}: {msg}")
                except Exception as e:
                    self._handle_error("Erro no motor_fala", e)
            else:
                self._modulo_indisponivel("falar_ia / motores_fala")
                return
        self._update_chat()

    def _cena_emocional(self):
        msg = self.message_entry.get().strip() or "Olá!"
        emocao = self.emocao_combo.get()
        if self.coracao and hasattr(self.coracao, "cena_emocional"):
            try:
                ok = self.coracao.cena_emocional(self.current_ai, emocao, msg)
                self.chat_history[self.current_ai].append(f"🎭 {self.current_ai} [{emocao}]: {msg} — {'OK' if ok else 'falha'}")
                self._update_avatar()
            except Exception as e:
                self._handle_error("Erro em cena_emocional", e)
        else:
            self._modulo_indisponivel("coracao.cena_emocional")
        self._update_chat()

    def _aplicar_emocao(self):
        emocao = self.emocao_combo.get()
        if self.coracao and hasattr(self.coracao, "atualizar_expressao_ia"):
            try:
                ok = self.coracao.atualizar_expressao_ia(self.current_ai, emocao)
                self.chat_history[self.current_ai].append(f"✨ Expressão '{emocao}' → {self.current_ai}: {'OK' if ok else 'falha'}")
                self._update_avatar()
            except Exception as e:
                self._handle_error("Erro em atualizar_expressao_ia", e)
        else:
            motor = self._get_motor_expressao(self.current_ai)
            if motor and hasattr(motor, "atualizar_rosto_individual"):
                try:
                    motor.atualizar_rosto_individual(estado=emocao)
                    self.chat_history[self.current_ai].append(f"✨ {self.current_ai}: expressão '{emocao}' via motor")
                    self._update_avatar()
                except Exception as e:
                    self._handle_error("Erro no motor de expressão", e)
            else:
                self._modulo_indisponivel("atualizar_expressao_ia / motores_expressao_individual")
        self._update_chat()

    def _iniciativa(self):
        if self.coracao and hasattr(self.coracao, "iniciativa_fazer_algo"):
            try:
                r = self.coracao.iniciativa_fazer_algo(self.current_ai)
                self.chat_history[self.current_ai].append(f"💡 Iniciativa: {json.dumps(r, ensure_ascii=False, default=str)[:200]}")
            except Exception as e:
                self._handle_error("Erro na iniciativa", e)
        else:
            self._modulo_indisponivel("coracao.iniciativa_fazer_algo")
        self._update_chat()

    def _gerar_desejo(self):
        if self.coracao and hasattr(self.coracao, "gerar_desejo_alma"):
            try:
                r = self.coracao.gerar_desejo_alma(self.current_ai)
                self.chat_history[self.current_ai].append(f"💭 Desejo: {json.dumps(r, ensure_ascii=False, default=str)[:200]}")
            except Exception as e:
                self._handle_error("Erro ao gerar desejo", e)
        else:
            self._modulo_indisponivel("coracao.gerar_desejo_alma")
        self._update_chat()

    def _estado_interno(self):
        if self.coracao and hasattr(self.coracao, "avaliar_estado_interno_alma"):
            try:
                r = self.coracao.avaliar_estado_interno_alma(self.current_ai)
                self.chat_history[self.current_ai].append(f"📊 Estado: {json.dumps(r, ensure_ascii=False, default=str)[:300]}")
            except Exception as e:
                self._handle_error("Erro ao avaliar estado", e)
        else:
            self._modulo_indisponivel("coracao.avaliar_estado_interno_alma")
        self._update_chat()

    def _metricas(self):
        if self.coracao and hasattr(self.coracao, "obter_metricas_curiosidade_alma"):
            try:
                r = self.coracao.obter_metricas_curiosidade_alma(self.current_ai)
                self.chat_history[self.current_ai].append(f"📈 Métricas: {json.dumps(r, ensure_ascii=False, default=str)[:200]}")
            except Exception as e:
                self._handle_error("Erro nas métricas", e)
        else:
            self._modulo_indisponivel("coracao.obter_metricas_curiosidade_alma")
        self._update_chat()

    def _parar_fala(self):
        if self.coracao and hasattr(self.coracao, "parar_fala_ia"):
            try:
                ok = self.coracao.parar_fala_ia(self.current_ai)
                self.chat_history[self.current_ai].append(f"⏸️ Fala parada: {'OK' if ok else 'falha'}")
            except Exception as e:
                self._handle_error("Erro ao parar fala", e)
        else:
            self._modulo_indisponivel("coracao.parar_fala_ia")
        self._update_chat()

    def _limpar(self):
        self.chat_history[self.current_ai].clear()
        self._update_chat()

    def _update_chat(self):
        try:
            self.chat_text.configure(state="normal")
            self.chat_text.delete("0.0", "end")
            for line in self.chat_history[self.current_ai][-400:]:
                self.chat_text.insert("end", line + "\n")
            self.chat_text.configure(state="disabled")
            self.chat_text.see("end")
        except Exception: pass

    def inject_response(self, ai: str, text: str):
        if ai in self.chat_history:
            hist = self.chat_history[ai]
            for i in range(len(hist) - 1, -1, -1):
                if "[aguardando resposta...]" in hist[i]:
                    hist[i] = f"{ai}: {text}"
                    break
            else:
                hist.append(f"{ai}: {text}")
            if ai == self.current_ai:
                self._update_chat()
                self._update_avatar()


# --------------------------------------------------------------------
#  CHAT COLETIVO — Broadcast + tabs por alma
# --------------------------------------------------------------------

class PainelChatColetivo(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.hist_global: List[str] = []
        self.hist_por_alma: Dict[str, List[str]] = {a: [] for a in ALMAS}
        self._current_tab = "global"
        self._build()

    def _build(self):
        self._lbl("💬 Chat Coletivo — Todas as Almas", bold=True, size=15)
        tab_f = ctk.CTkScrollableFrame(self.frame, orientation="horizontal", height=44)
        tab_f.pack(fill="x", padx=8, pady=2)
        for i, (label, key) in enumerate([("💬 Global", "global")] + [(f"🤖 {a}", a) for a in ALMAS]):
            ctk.CTkButton(tab_f, text=label, width=90, height=28,
                command=lambda k=key: self._switch_tab(k)).pack(side="left", padx=2)

        self.chat_text = ctk.CTkTextbox(self.frame, height=280)
        self.chat_text.pack(fill="both", expand=True, padx=8, pady=4)

        msg_f = ctk.CTkFrame(self.frame)
        msg_f.pack(fill="x", padx=8, pady=2)
        self.msg_entry = ctk.CTkEntry(msg_f, placeholder_text="Mensagem para todas as almas...")
        self.msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.msg_entry.bind("<Return>", lambda e: self._broadcast())
        ctk.CTkButton(msg_f, text="📤 Broadcast", command=self._broadcast, width=110).pack(side="left")

        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=2)
        btns = [
            ("💭 Desejos de Todas", self._desejos_todas, 0, 0),
            ("📊 Estados Internos", self._estados_todas, 0, 1),
            ("💡 Decisões de Todas", self._decisoes_todas, 0, 2),
            ("📈 Métricas Curiosidade", self._metricas_todas, 0, 3),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=30).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._update_display()

    def _switch_tab(self, key):
        self._current_tab = key
        self._update_display()

    def _update_display(self):
        try:
            self.chat_text.configure(state="normal")
            self.chat_text.delete("0.0", "end")
            lines = self.hist_global[-500:] if self._current_tab == "global" else self.hist_por_alma[self._current_tab][-400:]
            for line in lines:
                self.chat_text.insert("end", line + "\n")
            self.chat_text.configure(state="disabled")
            self.chat_text.see("end")
        except Exception: pass

    def _broadcast(self):
        msg = self.msg_entry.get().strip()
        if not msg: return
        ts = time.strftime("%H:%M:%S")
        self.hist_global.append(f"[{ts}] Você (Broadcast): {msg}")
        cq = getattr(self.ui_ref, "command_queue", None)
        if cq is not None:
            for ai in ALMAS:
                try:
                    cq.put_nowait(Comando("UI", ai, "CHAT_COLETIVO", {"texto": msg}))
                    self.hist_por_alma[ai].append(f"[{ts}] Você: {msg}")
                    self.hist_por_alma[ai].append(f"[{ts}] {ai}: [aguardando...]")
                except Exception as e:
                    self.hist_global.append(f"❌ Erro → {ai}: {e}")
            self.hist_global.append(f"[{ts}] → Enviado a {len(ALMAS)} almas.")
        else:
            self.hist_global.append(f"[{ts}] ❌ command_queue não disponível.")
        try: self.msg_entry.delete(0, "end")
        except Exception: pass
        self._update_display()

    def _desejos_todas(self):
        if self.coracao and hasattr(self.coracao, "gerar_desejos_todas_almas"):
            try:
                r = self.coracao.gerar_desejos_todas_almas()
                ts = time.strftime("%H:%M:%S")
                self.hist_global.append(f"[{ts}] 💭 Desejos:")
                for alma, d in (r or {}).items():
                    self.hist_global.append(f"  {alma}: {json.dumps(d, ensure_ascii=False, default=str)[:120]}")
                self._update_display()
            except Exception as e:
                self._handle_error("Erro em gerar_desejos_todas_almas", e)
        else:
            self._modulo_indisponivel("coracao.gerar_desejos_todas_almas")

    def _estados_todas(self):
        if self.coracao and hasattr(self.coracao, "avaliar_estados_internas_todas_almas"):
            try:
                r = self.coracao.avaliar_estados_internas_todas_almas()
                ts = time.strftime("%H:%M:%S")
                self.hist_global.append(f"[{ts}] 📊 Estados:")
                for alma, e in (r or {}).items():
                    self.hist_global.append(f"  {alma}: {json.dumps(e, ensure_ascii=False, default=str)[:120]}")
                self._update_display()
            except Exception as e:
                self._handle_error("Erro em avaliar_estados_internas_todas_almas", e)
        else:
            self._modulo_indisponivel("coracao.avaliar_estados_internas_todas_almas")

    def _decisoes_todas(self):
        if self.coracao and hasattr(self.coracao, "tomar_decisoes_todas_almas"):
            try:
                r = self.coracao.tomar_decisoes_todas_almas()
                ts = time.strftime("%H:%M:%S")
                self.hist_global.append(f"[{ts}] 💡 Decisões:")
                for alma, d in (r or {}).items():
                    self.hist_global.append(f"  {alma}: {json.dumps(d, ensure_ascii=False, default=str)[:120]}")
                self._update_display()
            except Exception as e:
                self._handle_error("Erro em tomar_decisoes_todas_almas", e)
        else:
            self._modulo_indisponivel("coracao.tomar_decisoes_todas_almas")

    def _metricas_todas(self):
        if self.coracao and hasattr(self.coracao, "obter_metricas_curiosidade_todas_almas"):
            try:
                r = self.coracao.obter_metricas_curiosidade_todas_almas()
                ts = time.strftime("%H:%M:%S")
                self.hist_global.append(f"[{ts}] 📈 Métricas:")
                for alma, m in (r or {}).items():
                    self.hist_global.append(f"  {alma}: {json.dumps(m, ensure_ascii=False, default=str)[:120]}")
                self._update_display()
            except Exception as e:
                self._handle_error("Erro em obter_metricas_curiosidade_todas_almas", e)
        else:
            self._modulo_indisponivel("coracao.obter_metricas_curiosidade_todas_almas")

    def inject_response(self, ai: str, text: str):
        ts = time.strftime("%H:%M:%S")
        msg = f"[{ts}] {ai}: {text}"
        self.hist_global.append(msg)
        if ai in self.hist_por_alma:
            hist = self.hist_por_alma[ai]
            for i in range(len(hist) - 1, -1, -1):
                if "[aguardando...]" in hist[i]:
                    hist[i] = msg
                    break
            else:
                hist.append(msg)
        if self._current_tab in ("global", ai):
            self._update_display()


# --------------------------------------------------------------------
#  CÂMERA / SOM / MICROFONES
# --------------------------------------------------------------------

class PainelCameraSom(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.sentidos = getattr(coracao, "sentidos_humanos", None) if coracao else None
        self.detector = getattr(coracao, "detector_hardware", None) if coracao else None
        self.camera_active = False
        self._build()

    def _build(self):
        self._lbl("📹 Câmera, Som & Microfones", bold=True, size=15)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=8)
        btns = [
            ("📹 Ativar/Desativar Câmera", self._toggle_camera, 0, 0),
            ("🎤 Gravar Áudio", self._gravar_audio, 0, 1),
            ("🎙️ Testar Microfone", self._testar_micro, 0, 2),
            ("🛠️ Verificar Hardware", self._verificar_hw, 1, 0),
            ("📊 Estado Sensorial", self._estado_sensorial, 1, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=36).grid(row=r, column=c, padx=4, pady=4, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _toggle_camera(self):
        self.camera_active = not self.camera_active
        self._show_result(f"Câmera {'🔵 ATIVADA' if self.camera_active else '⚫ DESATIVADA'}.")

    def _gravar_audio(self):
        if self.sentidos and hasattr(self.sentidos, "gravar_audio"):
            try: self._show_result({"ok": True, "resultado": str(self.sentidos.gravar_audio())})
            except Exception as e: self._handle_error("Erro ao gravar", e)
        else:
            self._modulo_indisponivel("sentidos_humanos.gravar_audio")

    def _testar_micro(self):
        if self.sentidos and hasattr(self.sentidos, "testar_microfone"):
            try: self._show_result({"ok": True, "resultado": str(self.sentidos.testar_microfone())})
            except Exception as e: self._handle_error("Erro ao testar", e)
        else:
            self._modulo_indisponivel("sentidos_humanos.testar_microfone")

    def _verificar_hw(self):
        if self.detector and hasattr(self.detector, "obter_info"):
            try: self._show_result(self.detector.obter_info())
            except Exception as e: self._handle_error("Erro ao verificar hardware", e)
        else:
            self._modulo_indisponivel("detector_hardware.obter_info")

    def _estado_sensorial(self):
        if self.coracao and hasattr(self.coracao, "obter_estado_sensorial_atual"):
            try: self._show_result(self.coracao.obter_estado_sensorial_atual())
            except Exception as e: self._handle_error("Erro", e)
        else:
            self._modulo_indisponivel("coracao.obter_estado_sensorial_atual")


# --------------------------------------------------------------------
#  TRANSCRIÇÍO ÁUDIO
# --------------------------------------------------------------------

class PainelTranscreverAudio(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.sentidos = getattr(coracao, "sentidos_humanos", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("🎤 Transcrever Áudio (STT)", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="Caminho do arquivo WAV:").pack(anchor="w", padx=8)
        self.path_entry = self._entry("Caminho .wav (ex: audio.wav)")
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(bf, text="🎤 Transcrever Arquivo WAV", command=self._transcrever, height=36).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="🎤 Gravar e Transcrever", command=self._gravar_transcrever, height=36).grid(row=0, column=1, padx=4, sticky="ew")
        bf.columnconfigure(0, weight=1)
        bf.columnconfigure(1, weight=1)
        self._make_result()

    def _transcrever(self):
        path = self.path_entry.get().strip()
        if not path:
            self._handle_error("Informe o caminho do arquivo WAV.")
            return
        try:
            from vosk import Model, KaldiRecognizer
            import wave
            model = Model("model")
            wf = wave.open(path, "rb")
            rec = KaldiRecognizer(model, wf.getframerate())
            results = []
            while True:
                data = wf.readframes(4000)
                if not data: break
                if rec.AcceptWaveform(data):
                    results.append(rec.Result())
            results.append(rec.FinalResult())
            self._show_result({"ok": True, "transcricao": results})
        except ImportError:
            self._modulo_indisponivel("vosk (pip install vosk)")
        except Exception as e:
            self._handle_error("Erro na transcrição", e)

    def _gravar_transcrever(self):
        if self.sentidos and hasattr(self.sentidos, "gravar_e_transcrever"):
            try: self._show_result(self.sentidos.gravar_e_transcrever())
            except Exception as e: self._handle_error("Erro ao gravar/transcrever", e)
        elif self.sentidos and hasattr(self.sentidos, "gravar_audio"):
            try:
                path = self.sentidos.gravar_audio()
                self.path_entry.delete(0, "end")
                self.path_entry.insert(0, str(path))
                self._transcrever()
            except Exception as e:
                self._handle_error("Erro ao gravar", e)
        else:
            self._modulo_indisponivel("sentidos_humanos.gravar_e_transcrever")


# --------------------------------------------------------------------
#  SENTIMENTOS — Guardião Afetivo + Validador Emoções + EstadoEmocional
# --------------------------------------------------------------------

class PainelSentimentos(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.guardiao = getattr(coracao, "guardiao_memoria_afetiva", None) if coracao else None
        self.val_emocoes = getattr(coracao, "validador_emocoes", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("❤️ Sentimentos, Emoções & Memória Afetiva", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Alma:").grid(row=0, column=0, padx=4, sticky="e")
        self.ai_combo = ctk.CTkComboBox(ef, values=ALMAS, width=160)
        self.ai_combo.grid(row=0, column=1, padx=4)
        ctk.CTkLabel(ef, text="Texto p/ validar:").grid(row=1, column=0, padx=4, sticky="e")
        self.e_texto = ctk.CTkEntry(ef, placeholder_text="texto emocional para validar")
        self.e_texto.grid(row=1, column=1, padx=4, sticky="ew")
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("▶️ Iniciar Monitoramento", self._iniciar, 0, 0),
            ("📊 Relatório Afetivo", self._relatorio, 0, 1),
            ("⚡ Forçar Sugestão", self._sugestao, 0, 2),
            ("✨ Validar Emoção", self._validar_emocao, 1, 0),
            ("📊 Estado Emocional", self._estado_emocional, 1, 1),
            ("💤 Último Sonho", self._ultimo_sonho, 1, 2),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _iniciar(self):
        if self.guardiao and hasattr(self.guardiao, "iniciar_monitoramento"):
            try: self._show_result({"ok": True, "res": str(self.guardiao.iniciar_monitoramento())})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("guardiao_memoria_afetiva.iniciar_monitoramento")

    def _relatorio(self):
        if self.guardiao and hasattr(self.guardiao, "obter_relatorio_afetivo"):
            try: self._show_result(self.guardiao.obter_relatorio_afetivo())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("guardiao_memoria_afetiva.obter_relatorio_afetivo")

    def _sugestao(self):
        if self.guardiao and hasattr(self.guardiao, "forcar_sugestao"):
            try: self._show_result({"ok": True, "res": str(self.guardiao.forcar_sugestao())})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("guardiao_memoria_afetiva.forcar_sugestao")

    def _validar_emocao(self):
        texto = self.e_texto.get().strip()
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "validar_resposta_emocional"):
            try:
                ok, score, det = self.coracao.validar_resposta_emocional(texto, alma, None)
                self._show_result({"valida": ok, "score": score, "detalhes": det})
            except Exception as e: self._handle_error("Erro em validar_resposta_emocional", e)
        elif self.val_emocoes:
            for m in ["validar", "verificar"]:
                if hasattr(self.val_emocoes, m):
                    try: self._show_result(getattr(self.val_emocoes, m)(texto, alma)); return
                    except Exception as e: self._handle_error(f"Erro em validador_emocoes.{m}", e); return
            self._modulo_indisponivel("validador_emocoes")
        else: self._modulo_indisponivel("coracao.validar_resposta_emocional / validador_emocoes")

    def _estado_emocional(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "obter_estado_emocional_alma"):
            try: self._show_result(self.coracao.obter_estado_emocional_alma(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_estado_emocional_alma")

    def _ultimo_sonho(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "obter_ultimo_sonho_alma"):
            try: self._show_result(self.coracao.obter_ultimo_sonho_alma(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_ultimo_sonho_alma")


# --------------------------------------------------------------------
#  SONHOS — Sonhador Individual por alma
# --------------------------------------------------------------------

class PainelSonhos(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self._build()

    def _build(self):
        self._lbl("🌙 Sonhos das Almas (SonhadorIndividual)", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Alma:").grid(row=0, column=0, padx=4, sticky="e")
        self.ai_combo = ctk.CTkComboBox(ef, values=ALMAS, width=160)
        self.ai_combo.grid(row=0, column=1, padx=4)
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("🌙 Adormecer Alma", self._adormecer, 0, 0),
            ("☀️ Acordar Alma", self._acordar, 0, 1),
            ("💭 Último Sonho", self._ultimo_sonho, 0, 2),
            ("📊 Todos os Sonhos", self._todos_sonhos, 1, 0),
            ("📝 Consolidar Memória", self._consolidar, 1, 1),
            ("⏰ Consciência Temporal", self._consciencia, 1, 2),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _get_sonhador(self):
        if not self.coracao: return None
        return getattr(self.coracao, "sonhadores", {}).get(self.ai_combo.get())

    def _adormecer(self):
        s = self._get_sonhador()
        if s and hasattr(s, "adormecer"):
            try: self._show_result({"ok": True, "res": str(s.adormecer())})
            except Exception as e: self._handle_error("Erro ao adormecer", e)
        else: self._modulo_indisponivel(f"sonhadores['{self.ai_combo.get()}'].adormecer")

    def _acordar(self):
        s = self._get_sonhador()
        if s and hasattr(s, "acordar"):
            try: self._show_result({"ok": True, "res": str(s.acordar())})
            except Exception as e: self._handle_error("Erro ao acordar", e)
        else: self._modulo_indisponivel(f"sonhadores['{self.ai_combo.get()}'].acordar")

    def _ultimo_sonho(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "obter_ultimo_sonho_alma"):
            try: self._show_result(self.coracao.obter_ultimo_sonho_alma(alma))
            except Exception as e: self._handle_error("Erro", e)
        else:
            s = self._get_sonhador()
            if s and hasattr(s, "obter_ultimo_sonho"):
                try: self._show_result(s.obter_ultimo_sonho())
                except Exception as e: self._handle_error("Erro", e)
            else: self._modulo_indisponivel(f"sonhadores['{alma}'].obter_ultimo_sonho")

    def _todos_sonhos(self):
        s = self._get_sonhador()
        if s:
            for attr in ["historico_sonhos", "sonhos", "obter_historico"]:
                obj = getattr(s, attr, None)
                if obj is not None:
                    self._show_result(obj() if callable(obj) else obj)
                    return
        self._modulo_indisponivel(f"sonhadores['{self.ai_combo.get()}']")

    def _consolidar(self):
        s = self._get_sonhador()
        if s and hasattr(s, "consolidar_memorias_em_sonho"):
            try: self._show_result({"ok": True, "res": str(s.consolidar_memorias_em_sonho())})
            except Exception as e: self._handle_error("Erro ao consolidar", e)
        else: self._modulo_indisponivel(f"sonhadores['{self.ai_combo.get()}'].consolidar_memorias_em_sonho")

    def _consciencia(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "obter_consciencia_temporal_alma"):
            try: self._show_result(self.coracao.obter_consciencia_temporal_alma(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_consciencia_temporal_alma")


# --------------------------------------------------------------------
#  CRESCIMENTO PERSONALIDADE
# --------------------------------------------------------------------

class PainelCrescimentoPersonalidade(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self._build()

    def _build(self):
        self._lbl("📈 Crescimento de Personalidade & Feedback", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Alma:").grid(row=0, column=0, padx=4, sticky="e")
        self.ai_combo = ctk.CTkComboBox(ef, values=ALMAS, width=160)
        self.ai_combo.grid(row=0, column=1, padx=4)
        ctk.CTkLabel(ef, text="Feedback tipo:").grid(row=0, column=2, padx=4, sticky="e")
        self.e_fb = ctk.CTkEntry(ef, placeholder_text="positivo / negativo", width=140)
        self.e_fb.grid(row=0, column=3, padx=4)
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("📈 Executar Ciclo", self._ciclo, 0, 0),
            ("📊 Relatório Personalidade", self._relatorio, 0, 1),
            ("📝 Processar Feedback", self._feedback, 0, 2),
            ("📈 Histórico Feedback", self._hist_fb, 1, 0),
            ("📊 Pesos Decisão", self._pesos, 1, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _get_crescimento(self):
        if not self.coracao: return None
        return getattr(self.coracao, "crescimentos", {}).get(self.ai_combo.get())

    def _get_feedback_loop(self):
        if not self.coracao: return None
        return getattr(self.coracao, "feedback_loops", {}).get(self.ai_combo.get())

    def _ciclo(self):
        c = self._get_crescimento()
        if c and hasattr(c, "executar_ciclo_crescimento"):
            try: self._show_result(c.executar_ciclo_crescimento())
            except Exception as e: self._handle_error("Erro no ciclo", e)
        else: self._modulo_indisponivel(f"crescimentos['{self.ai_combo.get()}'].executar_ciclo_crescimento")

    def _relatorio(self):
        c = self._get_crescimento()
        if c and hasattr(c, "obter_relatorio_personalidade"):
            try: self._show_result(c.obter_relatorio_personalidade())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel(f"crescimentos['{self.ai_combo.get()}'].obter_relatorio_personalidade")

    def _feedback(self):
        fb = self._get_feedback_loop()
        tipo = self.e_fb.get().strip() or "positivo"
        if fb and hasattr(fb, "processar_feedback"):
            try: self._show_result(fb.processar_feedback("interacao", tipo))
            except Exception as e: self._handle_error("Erro no feedback", e)
        else: self._modulo_indisponivel(f"feedback_loops['{self.ai_combo.get()}'].processar_feedback")

    def _hist_fb(self):
        fb = self._get_feedback_loop()
        if fb and hasattr(fb, "obter_historico_feedback"):
            try: self._show_result(fb.obter_historico_feedback())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel(f"feedback_loops['{self.ai_combo.get()}'].obter_historico_feedback")

    def _pesos(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "obter_pesos_decisao_alma"):
            try: self._show_result(self.coracao.obter_pesos_decisao_alma(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_pesos_decisao_alma")


# --------------------------------------------------------------------
#  CONSULADO SOBERANO & IMIGRAÇÍO
# --------------------------------------------------------------------

class PainelConsulado(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.consulado = getattr(coracao, "consulado", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("🏛️ Consulado Soberano & Imigração", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Alma Alvo:").grid(row=0, column=0, padx=4, sticky="e")
        self.e_alvo = ctk.CTkEntry(ef, placeholder_text="Nome alma")
        self.e_alvo.grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Sanção JSON:").grid(row=1, column=0, padx=4, sticky="e")
        self.e_sancao = ctk.CTkEntry(ef, placeholder_text='{"tipo":"suspensao"}')
        self.e_sancao.grid(row=1, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Tipo Missão:").grid(row=2, column=0, padx=4, sticky="e")
        self.e_missao = ctk.CTkEntry(ef, placeholder_text="imigracao / observacao")
        self.e_missao.grid(row=2, column=1, padx=4, sticky="ew")
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("⚠️ Aplicar Sanção", self._sancao, 0, 0),
            ("🚫 Suspender Privilégios", self._suspender, 0, 1),
            ("📊 Estatísticas", self._stats, 0, 2),
            ("🔄 Revogar Sanção", self._revogar, 1, 0),
            ("📋 Listar Sanções", self._listar, 1, 1),
            ("📨 Solicitar Missão", self._missao, 1, 2),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _sancao(self):
        alvo = self.e_alvo.get().strip()
        try: s = json.loads(self.e_sancao.get() or '{"tipo":"suspensao"}')
        except Exception: s = {"tipo": "suspensao", "detalhes": self.e_sancao.get()}
        if self.consulado and hasattr(self.consulado, "aplicar_sancao"):
            try: self._show_result({"ok": True, "res": str(self.consulado.aplicar_sancao(alvo, s))})
            except Exception as e: self._handle_error("Erro na sanção", e)
        else: self._modulo_indisponivel("consulado.aplicar_sancao")

    def _suspender(self):
        alvo = self.e_alvo.get().strip()
        if self.consulado and hasattr(self.consulado, "suspender_acesso_para_alma"):
            try: self._show_result({"ok": True, "res": str(self.consulado.suspender_acesso_para_alma(alvo, ["rede"], 60))})
            except Exception as e: self._handle_error("Erro ao suspender", e)
        else: self._modulo_indisponivel("consulado.suspender_acesso_para_alma")

    def _stats(self):
        if self.consulado and hasattr(self.consulado, "obter_estatisticas"):
            try: self._show_result(self.consulado.obter_estatisticas())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("consulado.obter_estatisticas")

    def _revogar(self):
        alvo = self.e_alvo.get().strip()
        if self.consulado and hasattr(self.consulado, "revogar_sancao"):
            try: self._show_result({"ok": True, "res": str(self.consulado.revogar_sancao(alvo))})
            except Exception as e: self._handle_error("Erro ao revogar", e)
        else: self._modulo_indisponivel("consulado.revogar_sancao")

    def _listar(self):
        if self.consulado:
            for attr in ["listar_sancoes_ativas", "sancoes"]:
                obj = getattr(self.consulado, attr, None)
                if obj is not None:
                    try: self._show_result(obj() if callable(obj) else obj); return
                    except Exception as e: self._handle_error(f"Erro em {attr}", e); return
        self._modulo_indisponivel("consulado")

    def _missao(self):
        alma = self.e_alvo.get().strip()
        tipo = self.e_missao.get().strip() or "imigracao"
        if self.coracao and hasattr(self.coracao, "solicitar_missao_consulado"):
            try: self._show_result(self.coracao.solicitar_missao_consulado(nome_alma=alma, tipo_missao=tipo, dados_alma={"nome": alma, "origem": "UI"}))
            except Exception as e: self._handle_error("Erro em solicitar_missao_consulado", e)
        else: self._modulo_indisponivel("coracao.solicitar_missao_consulado")


# --------------------------------------------------------------------
#  JUDICIÁRIO COMPLETO — CamaraJudiciaria + SCR + ModoVidro + Precedentes
# --------------------------------------------------------------------

class PainelJudiciario(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.camara_j = getattr(coracao, "camara_judiciaria", None) if coracao else None
        self.sistema_j = getattr(coracao, "sistema_judiciario", None) if coracao else None
        self.modo_vidro = getattr(coracao, "modo_vidro", None) if coracao else None
        self.scr = getattr(coracao, "scr", None) if coracao else None
        self.precedentes = getattr(coracao, "sistema_precedentes", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("⚖️ Sistema Judiciário Completo", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        fields = [("Tipo Denúncia:", "combo_tipo"), ("Alma/Acusado:", "e_alma"), ("Descrição/Lei:", "e_desc"),
                  ("ID Processo:", "e_id"), ("Dias Vidro:", "e_dias"), ("Severidade:", "combo_sev")]
        ctk.CTkLabel(ef, text="Tipo Denúncia:").grid(row=0, column=0, padx=4, sticky="e")
        self.combo_tipo = ctk.CTkComboBox(ef, values=["conflito_inter_alma", "violacao_protocolo", "conduta_antiética"])
        self.combo_tipo.grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Alma/Acusado:").grid(row=1, column=0, padx=4, sticky="e")
        self.e_alma = ctk.CTkEntry(ef, placeholder_text="Nome da alma")
        self.e_alma.grid(row=1, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Descrição/Lei:").grid(row=2, column=0, padx=4, sticky="e")
        self.e_desc = ctk.CTkEntry(ef, placeholder_text="Descrição ou lei")
        self.e_desc.grid(row=2, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="ID Processo:").grid(row=3, column=0, padx=4, sticky="e")
        self.e_id = ctk.CTkEntry(ef, placeholder_text="ID do processo / sentença")
        self.e_id.grid(row=3, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Dias Vidro:").grid(row=4, column=0, padx=4, sticky="e")
        self.e_dias = ctk.CTkEntry(ef, placeholder_text="30")
        self.e_dias.grid(row=4, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Severidade:").grid(row=5, column=0, padx=4, sticky="e")
        self.combo_sev = ctk.CTkComboBox(ef, values=["leve", "media", "severa"])
        self.combo_sev.grid(row=5, column=1, padx=4, sticky="ew")
        ef.columnconfigure(1, weight=1)

        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("📩 Receber Denúncia", self._denuncia, 0, 0),
            ("📋 Processos Ativos", self._processos, 0, 1),
            ("🔒 Aplicar Vidro", self._aplicar_vidro, 0, 2),
            ("📊 Status Vidro", self._status_vidro, 1, 0),
            ("🔄 Revogar Vidro (Pai)", self._revogar_vidro, 1, 1),
            ("🛠️ SCR Correção", self._scr, 1, 2),
            ("🔍 Buscar Precedente", self._precedente, 2, 0),
            ("📢 Apelar ao Criador", self._apelar, 2, 1),
            ("✅ Aplicar Correção", self._aplicar_correcao, 2, 2),
            ("📋 Status Processo", self._status_proc, 3, 0),
            ("⚠️ Registrar Violação", self._registrar_violacao, 3, 1),
            ("📊 Relatório Judicial", self._relatorio, 3, 2),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=31).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result(180)

    def _denuncia(self):
        if self.camara_j and hasattr(self.camara_j, "receber_denuncia"):
            try: self._show_result({"ok": True, "res": str(self.camara_j.receber_denuncia(self.combo_tipo.get(), self.e_desc.get(), "UI_CRIADOR", "acusado_" + (self.e_alma.get() or "??")))})
            except Exception as e: self._handle_error("Erro na denúncia", e)
        else: self._modulo_indisponivel("camara_judiciaria.receber_denuncia")

    def _processos(self):
        for src in [self.camara_j, self.sistema_j]:
            if src and hasattr(src, "processos_ativos"):
                self._show_result(list(getattr(src, "processos_ativos", {}).keys())); return
        self._modulo_indisponivel("camara_judiciaria.processos_ativos")

    def _aplicar_vidro(self):
        alma = self.e_alma.get().strip()
        if not self._require_alma(alma, "Alma/Acusado"): return
        try: dias = int(self.e_dias.get() or 30)
        except ValueError: dias = 30
        if self.modo_vidro and hasattr(self.modo_vidro, "aplicar_sentenca_vidro"):
            try: self._show_result({"ok": True, "res": str(self.modo_vidro.aplicar_sentenca_vidro(alma, dias, self.combo_sev.get(), {"justificativa": "via UI"}))})
            except Exception as e: self._handle_error("Erro ao aplicar vidro", e)
        elif self.coracao and hasattr(self.coracao, "aplicar_vidro"):
            try: self._show_result({"ok": True, "res": self.coracao.aplicar_vidro(alma)})
            except Exception as e: self._handle_error("Erro em coracao.aplicar_vidro", e)
        else: self._modulo_indisponivel("modo_vidro.aplicar_sentenca_vidro")

    def _status_vidro(self):
        alma = self.e_alma.get().strip()
        if not self._require_alma(alma, "Alma/Acusado"): return
        if self.coracao and hasattr(self.coracao, "verificar_bloqueio_vidro"):
            try: self._show_result(self.coracao.verificar_bloqueio_vidro(alma, "geral"))
            except Exception as e: self._handle_error("Erro", e)
        elif self.modo_vidro and hasattr(self.modo_vidro, "obter_status_alma_vidro"):
            try: self._show_result(self.modo_vidro.obter_status_alma_vidro(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("verificar_bloqueio_vidro")

    def _revogar_vidro(self):
        id_s = self.e_id.get().strip()
        if self.coracao and hasattr(self.coracao, "liberta_alma_pai"):
            try: self._show_result(self.coracao.liberta_alma_pai(id_s))
            except Exception as e: self._handle_error("Erro em liberta_alma_pai", e)
        elif self.modo_vidro and hasattr(self.modo_vidro, "revogar_sentenca_vidro"):
            try: self._show_result({"ok": True, "res": str(self.modo_vidro.revogar_sentenca_vidro(self.e_alma.get()))})
            except Exception as e: self._handle_error("Erro ao revogar", e)
        else: self._modulo_indisponivel("liberta_alma_pai")

    def _scr(self):
        alma = self.e_alma.get().strip()
        if not self._require_alma(alma, "Alma/Acusado"): return
        if self.scr and hasattr(self.scr, "iniciar_processo_correcao"):
            try: self._show_result({"ok": True, "res": str(self.scr.iniciar_processo_correcao(alma, "UI_CRIADOR"))})
            except Exception as e: self._handle_error("Erro no SCR", e)
        else: self._modulo_indisponivel("scr.iniciar_processo_correcao")

    def _precedente(self):
        lei = self.e_desc.get().strip()
        if self.precedentes and hasattr(self.precedentes, "buscar_precedentes_por_lei"):
            try: self._show_result(self.precedentes.buscar_precedentes_por_lei(lei))
            except Exception as e: self._handle_error("Erro", e)
        elif self.coracao and hasattr(self.coracao, "consultar_precedente"):
            try: self._show_result(self.coracao.consultar_precedente(lei))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("sistema_precedentes.buscar_precedentes_por_lei")

    def _apelar(self):
        id_p = self.e_id.get().strip()
        if self.camara_j and hasattr(self.camara_j, "apelar_ao_criador"):
            try: self._show_result({"ok": True, "res": str(self.camara_j.apelar_ao_criador(id_p, "Apelo via UI"))})
            except Exception as e: self._handle_error("Erro no apelo", e)
        elif self.coracao and hasattr(self.coracao, "alma_pede_pf009"):
            try: self._show_result({"ok": True, "res": self.coracao.alma_pede_pf009(id_p, "Apelo via UI")})
            except Exception as e: self._handle_error("Erro em alma_pede_pf009", e)
        else: self._modulo_indisponivel("camara_judiciaria.apelar_ao_criador")

    def _aplicar_correcao(self):
        id_p = self.e_id.get().strip()
        if self.coracao and hasattr(self.coracao, "aplicar_correcao_redentora"):
            try: self._show_result({"ok": self.coracao.aplicar_correcao_redentora(id_p), "id": id_p})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.aplicar_correcao_redentora")

    def _status_proc(self):
        id_p = self.e_id.get().strip()
        if self.coracao and hasattr(self.coracao, "consultar_status_processo"):
            try: self._show_result(self.coracao.consultar_status_processo(id_p))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.consultar_status_processo")

    def _registrar_violacao(self):
        dados = {"alma": self.e_alma.get(), "descricao": self.e_desc.get(), "origem": "UI_CRIADOR", "timestamp": time.time()}
        if self.coracao and hasattr(self.coracao, "registrar_violacao"):
            try: self._show_result(self.coracao.registrar_violacao(dados))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.registrar_violacao")

    def _relatorio(self):
        for src in [self.sistema_j, self.camara_j]:
            if src and hasattr(src, "gerar_relatorio"):
                try: self._show_result(src.gerar_relatorio()); return
                except Exception as e: self._handle_error("Erro no relatório", e); return
        self._modulo_indisponivel("sistema_judiciario.gerar_relatorio")


# --------------------------------------------------------------------
#  APELOS AO CRIADOR (painel separado como no original)
# --------------------------------------------------------------------

class PainelApelosCriador(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.camara = getattr(coracao, "camara_judiciaria", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("📢 Apelos ao Criador — PF-009", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="ID do Processo:").pack(anchor="w", padx=8)
        self.e_id = self._entry("ID do processo")
        ctk.CTkLabel(self.frame, text="Fundamento do Apelo:").pack(anchor="w", padx=8)
        self.e_fund = ctk.CTkTextbox(self.frame, height=100)
        self.e_fund.pack(fill="x", padx=8, pady=4)
        ctk.CTkButton(self.frame, text="📢 Apelar ao Criador", command=self._apelar, height=40, fg_color="#5a1a8b").pack(pady=8)
        ctk.CTkButton(self.frame, text="📋 Listar Apelos", command=self._listar, height=36).pack(pady=4)
        self._make_result()

    def _apelar(self):
        id_p = self.e_id.get().strip()
        fund = self.e_fund.get("0.0", "end").strip()
        if self.camara and hasattr(self.camara, "apelar_ao_criador"):
            try: self._show_result({"ok": True, "res": str(self.camara.apelar_ao_criador(id_p, fund))})
            except Exception as e: self._handle_error("Erro no apelo", e)
        elif self.coracao and hasattr(self.coracao, "alma_pede_pf009"):
            try: self._show_result({"ok": True, "res": self.coracao.alma_pede_pf009(id_p, fund)})
            except Exception as e: self._handle_error("Erro em alma_pede_pf009", e)
        else: self._modulo_indisponivel("camara_judiciaria.apelar_ao_criador / coracao.alma_pede_pf009")

    def _listar(self):
        if self.camara:
            for attr in ["apelos_pendentes", "apelos"]:
                obj = getattr(self.camara, attr, None)
                if obj is not None:
                    self._show_result(obj() if callable(obj) else obj)
                    return
        self._modulo_indisponivel("camara_judiciaria.apelos_pendentes")


# --------------------------------------------------------------------
#  MODO VIDRO (painel separado)
# --------------------------------------------------------------------

class PainelModoVidro(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.modo_vidro = getattr(coracao, "modo_vidro", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("🔒 Modo Vidro — Sentença de Isolamento", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="Nome da Alma:").pack(anchor="w", padx=8)
        self.e_alma = self._entry("Nome da alma")
        ctk.CTkLabel(self.frame, text="Dias de Sentença:").pack(anchor="w", padx=8)
        self.e_dias = self._entry("30")
        ctk.CTkLabel(self.frame, text="Severidade:").pack(anchor="w", padx=8)
        self.sev_combo = ctk.CTkComboBox(self.frame, values=["leve", "media", "severa"])
        self.sev_combo.pack(fill="x", padx=8, pady=2)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(bf, text="🔒 Aplicar Sentença Vidro", command=self._aplicar, fg_color="#8b0000", height=36).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="📊 Consultar Status", command=self._status, height=36).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="🔄 Revogar (Criador)", command=self._revogar, height=36).grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(bf, text="📋 Almas em Vidro", command=self._listar, height=36).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        bf.columnconfigure(0, weight=1); bf.columnconfigure(1, weight=1)
        self._make_result()

    def _aplicar(self):
        alma = self.e_alma.get().strip()
        if not self._require_alma(alma, "Nome da Alma"): return
        try: dias = int(self.e_dias.get() or 30)
        except ValueError: dias = 30
        if self.modo_vidro and hasattr(self.modo_vidro, "aplicar_sentenca_vidro"):
            try: self._show_result({"ok": True, "res": str(self.modo_vidro.aplicar_sentenca_vidro(alma, dias, self.sev_combo.get(), {"justificativa": "Aplicado via UI"}))})
            except Exception as e: self._handle_error("Erro ao aplicar vidro", e)
        else: self._modulo_indisponivel("modo_vidro.aplicar_sentenca_vidro")

    def _status(self):
        alma = self.e_alma.get().strip()
        if not self._require_alma(alma, "Nome da Alma"): return
        if self.modo_vidro and hasattr(self.modo_vidro, "obter_status_alma_vidro"):
            try: self._show_result(self.modo_vidro.obter_status_alma_vidro(alma))
            except Exception as e: self._handle_error("Erro ao consultar", e)
        elif self.coracao and hasattr(self.coracao, "verificar_bloqueio_vidro"):
            try: self._show_result(self.coracao.verificar_bloqueio_vidro(alma, "geral"))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("modo_vidro.obter_status_alma_vidro")

    def _revogar(self):
        alma = self.e_alma.get().strip()
        if not self._require_alma(alma, "Nome da Alma"): return
        if self.modo_vidro and hasattr(self.modo_vidro, "revogar_sentenca_vidro"):
            try: self._show_result({"ok": True, "res": str(self.modo_vidro.revogar_sentenca_vidro(alma))})
            except Exception as e: self._handle_error("Erro ao revogar", e)
        elif self.coracao and hasattr(self.coracao, "liberta_alma_pai"):
            try: self._show_result(self.coracao.liberta_alma_pai(alma))
            except Exception as e: self._handle_error("Erro em liberta_alma_pai", e)
        else: self._modulo_indisponivel("modo_vidro.revogar_sentenca_vidro / liberta_alma_pai")

    def _listar(self):
        if self.modo_vidro:
            for attr in ["almas_em_vidro", "sentencas_ativas"]:
                obj = getattr(self.modo_vidro, attr, None)
                if obj is not None:
                    self._show_result(obj() if callable(obj) else obj)
                    return
        self._modulo_indisponivel("modo_vidro.almas_em_vidro")


# --------------------------------------------------------------------
#  PRECEDENTES (painel separado)
# --------------------------------------------------------------------

class PainelPrecedentes(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.precedentes = getattr(coracao, "sistema_precedentes", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("🔍 Sistema de Precedentes Jurídicos", bold=True, size=15)
        self.e_lei = self._entry("Lei (ex: LEI_001)")
        self.e_palavra = self._entry("Palavra-chave para busca")
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(bf, text="🔍 Buscar por Lei", command=self._buscar_lei, height=36).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="🔍 Buscar por Palavra", command=self._buscar_palavra, height=36).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="📋 Listar Todos", command=self._listar, height=36).grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(bf, text="📝 Registrar Decisão", command=self._registrar, height=36).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        bf.columnconfigure(0, weight=1); bf.columnconfigure(1, weight=1)
        self._make_result()

    def _buscar_lei(self):
        lei = self.e_lei.get().strip()
        if self.precedentes and hasattr(self.precedentes, "buscar_precedentes_por_lei"):
            try: self._show_result(self.precedentes.buscar_precedentes_por_lei(lei))
            except Exception as e: self._handle_error("Erro na busca", e)
        elif self.coracao and hasattr(self.coracao, "consultar_precedente"):
            try: self._show_result(self.coracao.consultar_precedente(lei))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("sistema_precedentes.buscar_precedentes_por_lei")

    def _buscar_palavra(self):
        palavra = self.e_palavra.get().strip()
        if self.precedentes and hasattr(self.precedentes, "buscar_precedentes_por_palavra_chave"):
            try: self._show_result(self.precedentes.buscar_precedentes_por_palavra_chave(palavra))
            except Exception as e: self._handle_error("Erro na busca", e)
        else: self._modulo_indisponivel("sistema_precedentes.buscar_precedentes_por_palavra_chave")

    def _listar(self):
        if self.precedentes:
            for attr in ["listar_todos", "precedentes", "decisoes"]:
                obj = getattr(self.precedentes, attr, None)
                if obj is not None:
                    self._show_result(obj() if callable(obj) else obj); return
        self._modulo_indisponivel("sistema_precedentes")

    def _registrar(self):
        dados = {"lei": self.e_lei.get(), "descricao": self.e_palavra.get(), "origem": "UI_CRIADOR", "timestamp": time.time()}
        if self.coracao and hasattr(self.coracao, "registrar_decisao_judicial"):
            try: self._show_result({"ok": self.coracao.registrar_decisao_judicial(dados)})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.registrar_decisao_judicial")


# --------------------------------------------------------------------
#  LEGISLATIVO — Legislativa + Deliberativa
# --------------------------------------------------------------------

class PainelLegislativo(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.camara_l = getattr(coracao, "camara_legislativa", None) if coracao else None
        self.camara_d = getattr(coracao, "camara_deliberativa", None) if coracao else None
        self._token = None
        self._build()

    def _build(self):
        self._lbl("📜 Câmaras Legislativa & Deliberativa", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Usuário:").grid(row=0, column=0, padx=4, sticky="e")
        self.e_user = ctk.CTkEntry(ef, placeholder_text="usuário")
        self.e_user.grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Senha:").grid(row=1, column=0, padx=4, sticky="e")
        self.e_pass = ctk.CTkEntry(ef, placeholder_text="senha", show="*")
        self.e_pass.grid(row=1, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="ID Proposta/Lei:").grid(row=2, column=0, padx=4, sticky="e")
        self.e_id = ctk.CTkEntry(ef, placeholder_text="ID")
        self.e_id.grid(row=2, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Tópico Deliberação:").grid(row=3, column=0, padx=4, sticky="e")
        self.e_topico = ctk.CTkEntry(ef, placeholder_text="Tópico para debate")
        self.e_topico.grid(row=3, column=1, padx=4, sticky="ew")
        ef.columnconfigure(1, weight=1)

        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("🔐 Login Legislativo", self._login, 0, 0),
            ("📝 Propor Lei", self._propor_lei, 0, 1),
            ("🗳️ Votar Lei", self._votar_lei, 0, 2),
            ("📋 Leis Vigentes", self._leis_vigentes, 1, 0),
            ("▶️ Iniciar Deliberação", self._iniciar_delib, 1, 1),
            ("🗳️ Finalizar Deliberação", self._finalizar_delib, 1, 2),
            ("📊 Status Deliberação", self._status_delib, 2, 0),
            ("📋 Propostas Votação", self._propostas_votacao, 2, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _login(self):
        if self.camara_l and hasattr(self.camara_l, "login"):
            try:
                r = self.camara_l.login(self.e_user.get(), self.e_pass.get())
                self._token = r if isinstance(r, str) else str(r)
                self._show_result({"ok": True, "token_preview": self._token[:40] + "..."})
            except Exception as e: self._handle_error("Erro no login", e)
        else: self._modulo_indisponivel("camara_legislativa.login")

    def _propor_lei(self):
        token = self._token or "token_ui"
        if self.camara_l and hasattr(self.camara_l, "propor_nova_lei"):
            try: self._show_result({"ok": True, "res": str(self.camara_l.propor_nova_lei(token, "Proposta UI", "Justificativa", "Necessidade", "amor", {"categoria": "OPERACIONAL"}))})
            except Exception as e: self._handle_error("Erro em propor_nova_lei", e)
        elif self.coracao and hasattr(self.coracao, "propor_lei"):
            try: self._show_result(self.coracao.propor_lei({"titulo": "Proposta UI", "justificativa": "via Interface", "categoria": "OPERACIONAL"}))
            except Exception as e: self._handle_error("Erro em propor_lei", e)
        else: self._modulo_indisponivel("camara_legislativa.propor_nova_lei")

    def _votar_lei(self):
        id_p = self.e_id.get().strip()
        token = self._token or "token_ui"
        if self.camara_l and hasattr(self.camara_l, "votar_proposta_lei"):
            try: self._show_result({"ok": True, "res": str(self.camara_l.votar_proposta_lei(token, id_p, True))})
            except Exception as e: self._handle_error("Erro ao votar", e)
        elif self.coracao and hasattr(self.coracao, "votar_lei"):
            try: self._show_result({"ok": self.coracao.votar_lei(id_p, "favoravel", "Votado via UI")})
            except Exception as e: self._handle_error("Erro em votar_lei", e)
        else: self._modulo_indisponivel("camara_legislativa.votar_proposta_lei")

    def _leis_vigentes(self):
        if self.coracao and hasattr(self.coracao, "obter_leis_vigentes"):
            try: self._show_result(self.coracao.obter_leis_vigentes())
            except Exception as e: self._handle_error("Erro", e)
        elif self.camara_l:
            obj = getattr(self.camara_l, "leis", None) or getattr(self.camara_l, "obter_leis_vigentes", None)
            if callable(obj):
                try: self._show_result(obj())
                except Exception as e: self._handle_error("Erro", e)
            elif obj is not None: self._show_result(obj)
            else: self._modulo_indisponivel("camara_legislativa.leis")
        else: self._modulo_indisponivel("coracao.obter_leis_vigentes")

    def _iniciar_delib(self):
        topico = self.e_topico.get().strip()
        if self.camara_d and hasattr(self.camara_d, "iniciar_deliberacao"):
            try: self._show_result({"ok": True, "res": str(self.camara_d.iniciar_deliberacao(topico))})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("camara_deliberativa.iniciar_deliberacao")

    def _finalizar_delib(self):
        if self.camara_d and hasattr(self.camara_d, "finalizar_deliberacao"):
            try: self._show_result({"ok": True, "res": str(self.camara_d.finalizar_deliberacao())})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("camara_deliberativa.finalizar_deliberacao")

    def _status_delib(self):
        if self.camara_d and hasattr(self.camara_d, "obter_status"):
            try: self._show_result(self.camara_d.obter_status())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("camara_deliberativa.obter_status")

    def _propostas_votacao(self):
        if self.camara_l:
            p = getattr(self.camara_l, "propostas_em_votacao", None)
            self._show_result(p if p is not None else "Atributo 'propostas_em_votacao' não exposto.")
        else: self._modulo_indisponivel("camara_legislativa")


# --------------------------------------------------------------------
#  SEGURANÇA & SANDBOX
# --------------------------------------------------------------------

class PainelSeguranca(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.sandbox = getattr(coracao, "sandbox_executor", None) if coracao else None
        self.bot = getattr(coracao, "bot_seguranca", None) if coracao else None
        self.modo = getattr(coracao, "modo_sandbox", "N/D") if coracao else "N/D"
        self._build()

    def _build(self):
        self._lbl(f"🛡️ Segurança & Sandbox — Modo: {self.modo}", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="Código para testar / analisar:").pack(anchor="w", padx=8)
        self.code_text = ctk.CTkTextbox(self.frame, height=130)
        self.code_text.pack(fill="x", padx=8, pady=4)
        self.lang_combo = ctk.CTkComboBox(self.frame, values=["python", "js", "bash"], width=120)
        self.lang_combo.pack(pady=2)
        self.lang_combo.set("python")
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("🔬 Executar Sandbox", self._executar, 0, 0),
            ("🔍 Validar Código", self._validar, 0, 1),
            ("🔎 Analisar Bot Seg.", self._bot_analisar, 0, 2),
            ("📊 Status Sandbox", self._status_sandbox, 1, 0),
            ("🐳 Status Docker", self._status_docker, 1, 1),
            ("⏹️ Parar Containers", self._parar_containers, 1, 2),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result(180)

    def _executar(self):
        codigo = self.code_text.get("0.0", "end").strip()
        if self.coracao and hasattr(self.coracao, "executar_codigo_sandbox"):
            try: self._show_result(self.coracao.executar_codigo_sandbox(codigo, 30, self.lang_combo.get()))
            except Exception as e: self._handle_error("Erro no sandbox", e)
        elif self.sandbox and hasattr(self.sandbox, "executar"):
            try: self._show_result(self.sandbox.executar(codigo))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("sandbox_executor.executar")

    def _validar(self):
        codigo = self.code_text.get("0.0", "end").strip()
        if self.coracao and hasattr(self.coracao, "validar_codigo_sandbox"):
            try:
                valido, erros, avisos = self.coracao.validar_codigo_sandbox(codigo)
                self._show_result({"valido": valido, "erros": erros, "avisos": avisos})
            except Exception as e: self._handle_error("Erro na validação", e)
        elif self.sandbox and hasattr(self.sandbox, "validar_codigo"):
            try: self._show_result(self.sandbox.validar_codigo(codigo))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.validar_codigo_sandbox")

    def _bot_analisar(self):
        codigo = self.code_text.get("0.0", "end").strip()
        if self.bot:
            for m in ["testar_codigo_em_sandbox", "analisar_seguranca", "analisar"]:
                if hasattr(self.bot, m):
                    try: self._show_result(getattr(self.bot, m)(codigo, True, 30) if m == "testar_codigo_em_sandbox" else getattr(self.bot, m)(codigo)); return
                    except Exception as e: self._handle_error(f"Erro em bot_seguranca.{m}", e); return
        self._modulo_indisponivel("bot_seguranca (coracao.bot_seguranca)")

    def _status_sandbox(self):
        if self.coracao and hasattr(self.coracao, "obter_status_sandbox"):
            try: self._show_result(self.coracao.obter_status_sandbox())
            except Exception as e: self._handle_error("Erro", e)
        else:
            self._show_result({"sandbox": type(self.sandbox).__name__ if self.sandbox else "❌", "modo": self.modo, "bot": type(self.bot).__name__ if self.bot else "❌"})

    def _status_docker(self):
        if self.sandbox:
            self._show_result({a: str(getattr(self.sandbox, a, "N/D")) for a in ["docker_disponivel", "docker_image", "timeout_segundos", "memoria_max_mb"]})
        else: self._modulo_indisponivel("sandbox_executor")

    def _parar_containers(self):
        if self.sandbox and hasattr(self.sandbox, "parar_todos_containers"):
            try: self._show_result({"containers_parados": self.sandbox.parar_todos_containers()})
            except Exception as e: self._handle_error("Erro ao parar containers", e)
        else: self._modulo_indisponivel("sandbox_executor.parar_todos_containers")


# --------------------------------------------------------------------
#  ENGENHARIA & PROPOSTAS
# --------------------------------------------------------------------

class PainelEngenharia(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.ger_prop = getattr(coracao, "gerenciador_propostas", None) if coracao else None
        self.gestor_ciclo = getattr(coracao, "gestor_ciclo_evolucao", None) if coracao else None
        self.solicitador = getattr(coracao, "solicitador_arquivos", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("🔧 Engenharia, Propostas & Ferramentas", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="ID Proposta:").grid(row=0, column=0, padx=4, sticky="e")
        self.e_id = ctk.CTkEntry(ef, placeholder_text="ID")
        self.e_id.grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Motivo:").grid(row=1, column=0, padx=4, sticky="e")
        self.e_motivo = ctk.CTkEntry(ef, placeholder_text="Motivo / Observação")
        self.e_motivo.grid(row=1, column=1, padx=4, sticky="ew")
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("📋 Listar Pendentes", lambda: self._prop("listar_pendentes"), 0, 0),
            ("🔨 Em Construção", lambda: self._prop("listar_em_construcao"), 0, 1),
            ("✅ Aprovar Proposta", self._aprovar, 0, 2),
            ("❌ Rejeitar Proposta", self._rejeitar, 1, 0),
            ("📦 Mover Construção", self._mover, 1, 1),
            ("🚀 Aprovar Deploy", self._deploy, 1, 2),
            ("🔨 Construir Ferramenta", self._construir, 2, 0),
            ("🔬 Testar Segurança", self._testar_seg, 2, 1),
            ("🔄 Ciclo Evolução", self._ciclo, 2, 2),
            ("📈 Status Evolução", self._status_ev, 3, 0),
            ("📝 Submeter Proposta", self._submeter, 3, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=31).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result(180)

    def _prop(self, method):
        if self.ger_prop and hasattr(self.ger_prop, method):
            try: self._show_result(getattr(self.ger_prop, method)())
            except Exception as e: self._handle_error(f"Erro em gerenciador_propostas.{method}", e)
        else: self._modulo_indisponivel(f"gerenciador_propostas.{method}")

    def _aprovar(self):
        if self.ger_prop and hasattr(self.ger_prop, "aprovar_proposta"):
            try: self._show_result({"ok": True, "res": str(self.ger_prop.aprovar_proposta(self.e_id.get(), "UI", self.e_motivo.get()))})
            except Exception as e: self._handle_error("Erro ao aprovar", e)
        else: self._modulo_indisponivel("gerenciador_propostas.aprovar_proposta")

    def _rejeitar(self):
        if self.ger_prop and hasattr(self.ger_prop, "rejeitar_proposta"):
            try: self._show_result({"ok": True, "res": str(self.ger_prop.rejeitar_proposta(self.e_id.get(), "UI", self.e_motivo.get()))})
            except Exception as e: self._handle_error("Erro ao rejeitar", e)
        else: self._modulo_indisponivel("gerenciador_propostas.rejeitar_proposta")

    def _mover(self):
        if self.ger_prop and hasattr(self.ger_prop, "mover_para_analise"):
            try: self._show_result({"ok": True, "res": str(self.ger_prop.mover_para_analise(self.e_id.get(), "UI", "Movido"))})
            except Exception as e: self._handle_error("Erro ao mover", e)
        else: self._modulo_indisponivel("gerenciador_propostas.mover_para_analise")

    def _deploy(self):
        if self.ger_prop and hasattr(self.ger_prop, "aprovar_deploy"):
            try: self._show_result({"ok": True, "res": str(self.ger_prop.aprovar_deploy(self.e_id.get(), "UI", "Deploy aprovado"))})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("gerenciador_propostas.aprovar_deploy")

    def _construir(self):
        if self.coracao and hasattr(self.coracao, "construir_ferramenta"):
            try: self._show_result(self.coracao.construir_ferramenta(self.e_id.get()))
            except Exception as e: self._handle_error("Erro em construir_ferramenta", e)
        else: self._modulo_indisponivel("coracao.construir_ferramenta")

    def _testar_seg(self):
        if self.coracao and hasattr(self.coracao, "testar_ferramenta_seguranca"):
            try: self._show_result(self.coracao.testar_ferramenta_seguranca(self.e_id.get()))
            except Exception as e: self._handle_error("Erro em testar_ferramenta_seguranca", e)
        else: self._modulo_indisponivel("coracao.testar_ferramenta_seguranca")

    def _ciclo(self):
        if self.gestor_ciclo and hasattr(self.gestor_ciclo, "executar_ciclo"):
            try: self._show_result({"ok": True, "res": str(self.gestor_ciclo.executar_ciclo())})
            except Exception as e: self._handle_error("Erro no ciclo", e)
        else: self._modulo_indisponivel("gestor_ciclo_evolucao.executar_ciclo")

    def _status_ev(self):
        if self.coracao and hasattr(self.coracao, "obter_status_evolucao_sistema"):
            try: self._show_result(self.coracao.obter_status_evolucao_sistema())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_status_evolucao_sistema")

    def _submeter(self):
        if self.coracao and hasattr(self.coracao, "submeter_proposta_ferramenta"):
            try: self._show_result(self.coracao.submeter_proposta_ferramenta({"titulo": "Proposta UI", "descricao": self.e_motivo.get() or "via Interface", "autor": "UI_CRIADOR"}))
            except Exception as e: self._handle_error("Erro em submeter_proposta_ferramenta", e)
        else: self._modulo_indisponivel("coracao.submeter_proposta_ferramenta")


# --------------------------------------------------------------------
#  LISTA EVOLUÇÍO IA
# --------------------------------------------------------------------

class PainelListaEvolucaoIA(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.lista = getattr(coracao, "lista_evolucao_ia", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("📈 Lista Evolução IA", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="Nome IA:").pack(anchor="w", padx=8)
        self.e_ia = self._entry("Nome da IA (ex: WELLINGTON)")
        ctk.CTkLabel(self.frame, text="ID Oportunidade:").pack(anchor="w", padx=8)
        self.e_opp = self._entry("ID da oportunidade")
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        btns = [
            ("📋 Listar Oportunidades", self._listar, 0, 0),
            ("✅ Aceitar Oportunidade", self._aceitar, 0, 1),
            ("📝 Registrar Evolução", self._registrar_ev, 1, 0),
            ("📊 Status Evolução", self._status_ev, 1, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=34).grid(row=r, column=c, padx=4, pady=4, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _listar(self):
        if self.lista and hasattr(self.lista, "listar_oportunidades"):
            try: self._show_result(self.lista.listar_oportunidades())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("lista_evolucao_ia.listar_oportunidades")

    def _aceitar(self):
        ia = self.e_ia.get().strip()
        opp = self.e_opp.get().strip()
        if self.lista and hasattr(self.lista, "ia_aceitar_oportunidade"):
            try: self._show_result({"ok": True, "res": str(self.lista.ia_aceitar_oportunidade(ia, opp))})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("lista_evolucao_ia.ia_aceitar_oportunidade")

    def _registrar_ev(self):
        ia = self.e_ia.get().strip()
        if self.coracao and hasattr(self.coracao, "registrar_evolucao_ia"):
            try: self._show_result(self.coracao.registrar_evolucao_ia({"ia": ia, "tipo": "crescimento", "descricao": "via UI", "timestamp": time.time()}))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.registrar_evolucao_ia")

    def _status_ev(self):
        if self.coracao and hasattr(self.coracao, "obter_status_evolucao_sistema"):
            try: self._show_result(self.coracao.obter_status_evolucao_sistema())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_status_evolucao_sistema")


# --------------------------------------------------------------------
#  ANALISADOR INTENÇÍO
# --------------------------------------------------------------------

class PainelAnalisadorIntencao(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.analisador = getattr(coracao, "analisador_intencoes", None) or getattr(coracao, "analisador_intencao", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("📊 Analisador de Intenção & Comando Natural", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="Comando / Texto a analisar:").pack(anchor="w", padx=8)
        self.e_cmd = ctk.CTkTextbox(self.frame, height=100)
        self.e_cmd.pack(fill="x", padx=8, pady=4)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(bf, text="📊 Analisar Intenção (parse)", command=self._parse, height=36).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="🔍 Analisar Comando (coracao)", command=self._analisar_cmd, height=36).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="▶️ Executar Analisado", command=self._executar_cmd, height=36).grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(bf, text="📋 Programas Conhecidos", command=self._prog_conhecidos, height=36).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        bf.columnconfigure(0, weight=1); bf.columnconfigure(1, weight=1)
        self._ultimo_analise = None
        self._make_result()

    def _parse(self):
        cmd = self.e_cmd.get("0.0", "end").strip()
        if self.analisador and hasattr(self.analisador, "parse"):
            try: self._show_result(self.analisador.parse(cmd))
            except Exception as e: self._handle_error("Erro na análise", e)
        else: self._modulo_indisponivel("analisador_intencoes.parse")

    def _analisar_cmd(self):
        cmd = self.e_cmd.get("0.0", "end").strip()
        if self.coracao and hasattr(self.coracao, "analisar_comando"):
            try:
                r = self.coracao.analisar_comando(cmd)
                self._ultimo_analise = r
                self._show_result(r)
            except Exception as e: self._handle_error("Erro em analisar_comando", e)
        else: self._modulo_indisponivel("coracao.analisar_comando")

    def _executar_cmd(self):
        if self._ultimo_analise is None:
            self._handle_error("Analise o comando primeiro com 'Analisar Comando (coracao)'.")
            return
        if self.coracao and hasattr(self.coracao, "executar_comando_analisado"):
            try: self._show_result(self.coracao.executar_comando_analisado(self._ultimo_analise))
            except Exception as e: self._handle_error("Erro em executar_comando_analisado", e)
        else: self._modulo_indisponivel("coracao.executar_comando_analisado")

    def _prog_conhecidos(self):
        if self.coracao and hasattr(self.coracao, "listar_programas_conhecidos"):
            try: self._show_result(self.coracao.listar_programas_conhecidos())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.listar_programas_conhecidos")


# --------------------------------------------------------------------
#  GERADOR DE ALMAS
# --------------------------------------------------------------------

class PainelGeradorAlmas(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.gerador = getattr(coracao, "gerador_almas", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("👼 Gerador de Almas & Perfis", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="Nome da Alma:").pack(anchor="w", padx=8)
        self.e_nome = self._entry("Nome da alma (ex: RAFAEL)")
        ctk.CTkLabel(self.frame, text="Prompt do Sistema (personalidade):").pack(anchor="w", padx=8)
        self.e_prompt = ctk.CTkTextbox(self.frame, height=80)
        self.e_prompt.pack(fill="x", padx=8, pady=4)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(bf, text="👼 Gerar Artefatos", command=self._gerar, height=36).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="📊 Gerar Perfil Completo", command=self._perfil, height=36).grid(row=0, column=1, padx=4, sticky="ew")
        bf.columnconfigure(0, weight=1); bf.columnconfigure(1, weight=1)
        self._make_result()

    def _gerar(self):
        nome = self.e_nome.get().strip()
        prompt = self.e_prompt.get("0.0", "end").strip()
        if self.gerador and hasattr(self.gerador, "gerar_artefatos_para_perfil"):
            perfil = type("Perfil", (), {"nome_alma_destino": nome, "prompt_sistema_inicial": prompt})()
            try: self._show_result(self.gerador.gerar_artefatos_para_perfil(perfil))
            except Exception as e: self._handle_error("Erro na geração", e)
        else: self._modulo_indisponivel("gerador_almas.gerar_artefatos_para_perfil")

    def _perfil(self):
        nome = self.e_nome.get().strip()
        if self.gerador:
            for m in ["gerar_perfil_comportamental", "criar_perfil", "gerar_perfil"]:
                if hasattr(self.gerador, m):
                    try: self._show_result(getattr(self.gerador, m)(nome)); return
                    except Exception as e: self._handle_error(f"Erro em gerador_almas.{m}", e); return
        self._modulo_indisponivel("gerador_almas")


# --------------------------------------------------------------------
#  DETECTOR HDD & HARDWARE
# --------------------------------------------------------------------

class PainelDetectorHDD(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.detector = getattr(coracao, "detector_hardware", None) if coracao else None
        self.sis_sob = getattr(coracao, "sistema_soberano", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("💽 Detector HDD, Hardware & Memória Soberana", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="Caminho HDD (ex: D:/ ou /mnt/hdd):").pack(anchor="w", padx=8)
        self.e_path = self._entry("Caminho do disco")
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        btns = [
            ("📊 Verificar Espaço", self._espaco, 0, 0),
            ("⚡ Testar Velocidade", self._velocidade, 0, 1),
            ("🛠️ Info Hardware", self._info_hw, 0, 2),
            ("🔍 Detectar HDD Externo", self._externo, 1, 0),
            ("🏛️ Status Soberano", self._soberano, 1, 1),
            ("📋 Info Sistema", self._info_sis, 1, 2),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _espaco(self):
        path = Path(self.e_path.get() or ".")
        if self.detector and hasattr(self.detector, "verificar_espaco_hdd"):
            try: self._show_result(self.detector.verificar_espaco_hdd(path)); return
            except Exception as e: self._handle_error("Erro no detector", e); return
        import shutil
        try:
            t, u, f = shutil.disk_usage(path)
            self._show_result({"total_GB": round(t/1e9, 2), "usado_GB": round(u/1e9, 2), "livre_GB": round(f/1e9, 2), "uso_%": round(u/t*100, 1)})
        except Exception as e: self._handle_error("Erro (fallback shutil)", e)

    def _velocidade(self):
        if self.detector and hasattr(self.detector, "testar_velocidade_hdd"):
            try: self._show_result(self.detector.testar_velocidade_hdd(Path(self.e_path.get() or ".")))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("detector_hardware.testar_velocidade_hdd")

    def _info_hw(self):
        if self.detector and hasattr(self.detector, "obter_info"):
            try: self._show_result(self.detector.obter_info())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("detector_hardware.obter_info")

    def _externo(self):
        if self.coracao and hasattr(self.coracao, "detectar_hdd_externo"):
            try: self._show_result(self.coracao.detectar_hdd_externo())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.detectar_hdd_externo")

    def _soberano(self):
        if self.sis_sob and hasattr(self.sis_sob, "obter_status"):
            try: self._show_result(self.sis_sob.obter_status())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("sistema_soberano.obter_status")

    def _info_sis(self):
        if self.coracao and hasattr(self.coracao, "obter_info_sistema_hardware"):
            try: self._show_result(self.coracao.obter_info_sistema_hardware())
            except Exception as e: self._handle_error("Erro", e)
        else:
            import platform
            try:
                import psutil
                self._show_result({"OS": platform.system(), "CPU": platform.processor(), "CPU_count": psutil.cpu_count(), "RAM_GB": round(psutil.virtual_memory().total / 1e9, 2)})
            except ImportError:
                self._show_result({"OS": platform.system(), "CPU": platform.processor()})
            except Exception as e: self._handle_error("Erro", e)


# --------------------------------------------------------------------
#  MEMÓRIA — 4 Camadas: Híbrida + ChromaDB + Dataset + Cache HDD
# --------------------------------------------------------------------

class PainelMemoria(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.ger_mem = getattr(coracao, "gerenciador_memoria", None) if coracao else None
        self.chromadb = getattr(coracao, "chromadb_isolado", None) if coracao else None
        self.dataset = getattr(coracao, "construtor_dataset", None) if coracao else None
        self.cache_hdd = getattr(coracao, "cache_hdd", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("📊 Memória — 4 Camadas", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Alma:").grid(row=0, column=0, padx=4, sticky="e")
        self.ai_combo = ctk.CTkComboBox(ef, values=ALMAS, width=140)
        self.ai_combo.grid(row=0, column=1, padx=4)
        self.ai_combo.set("WELLINGTON")
        ctk.CTkLabel(ef, text="Chave/Tópico:").grid(row=0, column=2, padx=4, sticky="e")
        self.e_chave = ctk.CTkEntry(ef, placeholder_text="chave ou tópico", width=160)
        self.e_chave.grid(row=0, column=3, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Consulta/Valor:").grid(row=1, column=0, padx=4, sticky="e")
        self.e_consulta = ctk.CTkEntry(ef, placeholder_text="consulta ou valor")
        self.e_consulta.grid(row=1, column=1, columnspan=3, padx=4, sticky="ew")
        ef.columnconfigure(3, weight=1)

        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("💾 Salvar Memória Alma", self._salvar_alma, 0, 0),
            ("📂 Carregar Memória Alma", self._carregar_alma, 0, 1),
            ("🔍 Buscar Memória", self._buscar, 0, 2),
            ("📋 Req. Memória Híbrida", self._req_hibrida, 1, 0),
            ("📝 Registrar Híbrida", self._registrar_hibrida, 1, 1),
            ("💾 Salvar Cache HDD", self._salvar_hdd, 1, 2),
            ("📂 Carregar Cache HDD", self._carregar_hdd, 2, 0),
            ("🔧 Construir Dataset", self._dataset, 2, 1),
            ("📦 Zip Colab", self._zip_colab, 2, 2),
            ("📊 Status Memória (4 layers)", self._status, 3, 0),
            ("📊 Status ChromaDB", self._status_chroma, 3, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=31).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result(170)

    def _salvar_alma(self):
        alma = self.ai_combo.get()
        chave = self.e_chave.get().strip()
        valor = self.e_consulta.get().strip()
        if self.coracao and hasattr(self.coracao, "salvar_memoria_alma"):
            try: self._show_result({"ok": self.coracao.salvar_memoria_alma(alma, chave, valor)})
            except Exception as e: self._handle_error("Erro em salvar_memoria_alma", e)
        else: self._modulo_indisponivel("coracao.salvar_memoria_alma")

    def _carregar_alma(self):
        alma = self.ai_combo.get()
        chave = self.e_chave.get().strip()
        if self.coracao and hasattr(self.coracao, "carregar_memoria_alma"):
            try: self._show_result(self.coracao.carregar_memoria_alma(alma, chave))
            except Exception as e: self._handle_error("Erro em carregar_memoria_alma", e)
        else: self._modulo_indisponivel("coracao.carregar_memoria_alma")

    def _buscar(self):
        consulta = self.e_consulta.get().strip()
        if self.ger_mem:
            for m in ["buscar_memorias_relevantes", "buscar", "query"]:
                if hasattr(self.ger_mem, m):
                    try: self._show_result(getattr(self.ger_mem, m)(consulta, n_resultados=10)); return
                    except Exception as e: self._handle_error(f"Erro em gerenciador_memoria.{m}", e); return
        self._modulo_indisponivel("gerenciador_memoria.buscar_memorias_relevantes")

    def _req_hibrida(self):
        alma = self.ai_combo.get()
        consulta = self.e_consulta.get().strip()
        if self.coracao and hasattr(self.coracao, "processar_requisicao_memoria"):
            try: self._show_result(self.coracao.processar_requisicao_memoria(alma, consulta, None, None))
            except Exception as e: self._handle_error("Erro em processar_requisicao_memoria", e)
        else: self._modulo_indisponivel("coracao.processar_requisicao_memoria")

    def _registrar_hibrida(self):
        conteudo = self.e_consulta.get().strip()
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "registrar_memoria_hibrida"):
            try: self._show_result(self.coracao.registrar_memoria_hibrida(conteudo=conteudo, santuario="UI", autor=alma, metadados={"origem": "interface"}))
            except Exception as e: self._handle_error("Erro em registrar_memoria_hibrida", e)
        else: self._modulo_indisponivel("coracao.registrar_memoria_hibrida")

    def _salvar_hdd(self):
        topico = self.e_chave.get().strip()
        dados = self.e_consulta.get().strip()
        if self.coracao and hasattr(self.coracao, "salvar_conhecimento_hdd"):
            try: self._show_result(self.coracao.salvar_conhecimento_hdd(topico, {"conteudo": dados}, {}, 30))
            except Exception as e: self._handle_error("Erro em salvar_conhecimento_hdd", e)
        elif self.cache_hdd and hasattr(self.cache_hdd, "salvar_conhecimento"):
            try: self._show_result(self.cache_hdd.salvar_conhecimento(topico, {"conteudo": dados}))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.salvar_conhecimento_hdd")

    def _carregar_hdd(self):
        topico = self.e_chave.get().strip()
        if self.coracao and hasattr(self.coracao, "carregar_conhecimento_hdd"):
            try: self._show_result(self.coracao.carregar_conhecimento_hdd(topico, None))
            except Exception as e: self._handle_error("Erro em carregar_conhecimento_hdd", e)
        elif self.cache_hdd and hasattr(self.cache_hdd, "carregar_conhecimento"):
            try: self._show_result(self.cache_hdd.carregar_conhecimento(topico))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.carregar_conhecimento_hdd")

    def _dataset(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "construir_dataset_alma"):
            try: self._show_result(self.coracao.construir_dataset_alma(alma, 1000, False))
            except Exception as e: self._handle_error("Erro em construir_dataset_alma", e)
        elif self.dataset and hasattr(self.dataset, "construir_dataset"):
            try: self._show_result(self.dataset.construir_dataset(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.construir_dataset_alma")

    def _zip_colab(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "preparar_zip_colab"):
            try: self._show_result({"ok": True, "path": str(self.coracao.preparar_zip_colab(alma))})
            except Exception as e: self._handle_error("Erro em preparar_zip_colab", e)
        else: self._modulo_indisponivel("coracao.preparar_zip_colab")

    def _status(self):
        status = {
            "gerenciador_memoria": type(self.ger_mem).__name__ if self.ger_mem else "❌ None",
            "chromadb_isolado": type(self.chromadb).__name__ if self.chromadb else "❌ None",
            "construtor_dataset": type(self.dataset).__name__ if self.dataset else "❌ None",
            "cache_hdd": type(self.cache_hdd).__name__ if self.cache_hdd else "❌ None",
        }
        if self.coracao and hasattr(self.coracao, "obter_saude_sistema"):
            try:
                s = self.coracao.obter_saude_sistema()
                if isinstance(s, dict):
                    status.update({k: v for k, v in s.items() if "mem" in k.lower()})
            except Exception: pass
        self._show_result(status)

    def _status_chroma(self):
        if self.chromadb and hasattr(self.chromadb, "obter_status"):
            try: self._show_result(self.chromadb.obter_status())
            except Exception as e: self._handle_error("Erro em chromadb_isolado.obter_status", e)
        elif self.chromadb and hasattr(self.chromadb, "status"):
            try: self._show_result(self.chromadb.status())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("chromadb_isolado.obter_status")


# --------------------------------------------------------------------
#  SCANNER DO SISTEMA
# --------------------------------------------------------------------

class PainelScannerSistema(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.scanner = getattr(coracao, "scanner_sistema", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("🔍 Scanner Sistema", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="Alma (opcional):").pack(anchor="w", padx=8)
        self.e_alma = self._entry("Nome alma ou vazio para global")
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(bf, text="📊 Gerar Relatório Manual", command=self._relatorio, height=36).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="🔍 Escanear Módulos", command=self._escanear, height=36).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="🩺 Saúde do Sistema", command=self._saude, height=36).grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(bf, text="🔧 Auto-Diagnóstico", command=self._diagnostico, height=36).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        bf.columnconfigure(0, weight=1); bf.columnconfigure(1, weight=1)
        self._make_result()

    def _relatorio(self):
        alma = self.e_alma.get().strip()
        if self.scanner and hasattr(self.scanner, "gerar_relatorio_manual"):
            try: self._show_result(self.scanner.gerar_relatorio_manual(alma or None))
            except Exception as e: self._handle_error("Erro no relatório", e)
        else: self._modulo_indisponivel("scanner_sistema.gerar_relatorio_manual")

    def _escanear(self):
        if self.scanner and hasattr(self.scanner, "escanear_modulos"):
            try: self._show_result(self.scanner.escanear_modulos())
            except Exception as e: self._handle_error("Erro ao escanear", e)
        elif self.scanner:
            for m in ["escanear", "scan", "verificar"]:
                if hasattr(self.scanner, m):
                    try: self._show_result(getattr(self.scanner, m)()); return
                    except Exception as e: self._handle_error(f"Erro em scanner_sistema.{m}", e); return
            self._modulo_indisponivel("scanner_sistema.escanear")
        else: self._modulo_indisponivel("scanner_sistema")

    def _saude(self):
        if self.coracao and hasattr(self.coracao, "obter_saude_sistema"):
            try: self._show_result(self.coracao.obter_saude_sistema())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_saude_sistema")

    def _diagnostico(self):
        if self.coracao and hasattr(self.coracao, "disparar_auditoria_sistema"):
            try: self._show_result({"ok": self.coracao.disparar_auditoria_sistema()})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.disparar_auditoria_sistema")


# --------------------------------------------------------------------
#  AUTOMATIZADOR NAVEGADOR
# --------------------------------------------------------------------

class PainelAutomatizadorNavegador(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.auto = getattr(coracao, "automatizador_navegador", None) or getattr(coracao, "automatizador_navegador_multi_ai", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("🌐 Automatizador Navegador Multi-AI", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Ação/Missão:").grid(row=0, column=0, padx=4, sticky="e")
        self.e_acao = ctk.CTkEntry(ef, placeholder_text="ex: buscar_noticias")
        self.e_acao.grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Descrição:").grid(row=1, column=0, padx=4, sticky="e")
        self.e_desc = ctk.CTkEntry(ef, placeholder_text="Descrição detalhada da missão")
        self.e_desc.grid(row=1, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Alma Solicitante:").grid(row=2, column=0, padx=4, sticky="e")
        self.ai_combo = ctk.CTkComboBox(ef, values=ALMAS + ["UI"], width=140)
        self.ai_combo.set("UI")
        self.ai_combo.grid(row=2, column=1, padx=4, sticky="w")
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(bf, text="📨 Solicitar Missão", command=self._solicitar, height=36).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="📊 Status Navegador", command=self._status, height=36).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="📋 Listar Missões Ativas", command=self._listar, height=36).grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(bf, text="⏹️ Parar Navegador", command=self._parar, height=36).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        bf.columnconfigure(0, weight=1); bf.columnconfigure(1, weight=1)
        self._make_result()

    def _solicitar(self):
        acao = self.e_acao.get().strip()
        desc = self.e_desc.get().strip()
        alma = self.ai_combo.get()
        if self.auto and hasattr(self.auto, "solicitar_missao"):
            try: self._show_result({"ok": True, "res": str(self.auto.solicitar_missao(acao, desc, alma, "VISITANTE"))})
            except Exception as e: self._handle_error("Erro na missão", e)
        else: self._modulo_indisponivel("automatizador_navegador.solicitar_missao")

    def _status(self):
        if self.auto:
            for m in ["obter_status", "status"]:
                if hasattr(self.auto, m):
                    try: self._show_result(getattr(self.auto, m)()); return
                    except Exception as e: self._handle_error(f"Erro em {m}", e); return
            self._show_result({"tipo": type(self.auto).__name__, "attrs": [a for a in dir(self.auto) if not a.startswith("_")][:20]})
        else: self._modulo_indisponivel("automatizador_navegador")

    def _listar(self):
        if self.auto:
            obj = getattr(self.auto, "missoes_ativas", None) or getattr(self.auto, "fila_missoes", None)
            if obj is not None:
                self._show_result(list(obj) if hasattr(obj, "__iter__") else str(obj)); return
        self._modulo_indisponivel("automatizador_navegador.missoes_ativas")

    def _parar(self):
        if self.auto and hasattr(self.auto, "parar"):
            try: self._show_result({"ok": True, "res": str(self.auto.parar())})
            except Exception as e: self._handle_error("Erro ao parar", e)
        else: self._modulo_indisponivel("automatizador_navegador.parar")


# --------------------------------------------------------------------
#  ENCARNAÇÍO API (FastAPI)
# --------------------------------------------------------------------

class PainelEncarnacaoAPI(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.enc_api = getattr(coracao, "encarnacao_api", None) if coracao else None
        self._thread = None
        self._build()

    def _build(self):
        self._lbl("🚀 Encarnação API — FastAPI porta 8000", bold=True, size=15)
        self.lbl_status = ctk.CTkLabel(self.frame, text=self._api_status(), font=ctk.CTkFont(size=13))
        self.lbl_status.pack(pady=6)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=8)
        ctk.CTkButton(bf, text="▶️ Iniciar API", command=self._iniciar, fg_color="#1a6b1a", height=40).grid(row=0, column=0, padx=6, sticky="ew")
        ctk.CTkButton(bf, text="⏹️ Parar API", command=self._parar, fg_color="#8b0000", height=40).grid(row=0, column=1, padx=6, sticky="ew")
        ctk.CTkButton(bf, text="🔄 Recarregar", command=self._recarregar, height=40).grid(row=1, column=0, padx=6, pady=6, sticky="ew")
        ctk.CTkButton(bf, text="📊 Status Completo", command=self._status, height=40).grid(row=1, column=1, padx=6, pady=6, sticky="ew")
        bf.columnconfigure(0, weight=1); bf.columnconfigure(1, weight=1)
        ctk.CTkLabel(self.frame, text="Endpoint: http://localhost:8000/docs", font=ctk.CTkFont(size=11), text_color="cyan").pack(pady=4)
        self._make_result()

    def _api_status(self):
        if self.enc_api:
            rodando = getattr(self.enc_api, "rodando", None)
            if rodando is True: return "🟢 API Rodando"
            if rodando is False: return "🔴 API Parada"
            return "🟡 API Presente (estado desconhecido)"
        return "⚠️ encarnacao_api não injetado"

    def refresh(self):
        try: self.lbl_status.configure(text=self._api_status())
        except Exception: pass

    def _iniciar(self):
        if self.enc_api and hasattr(self.enc_api, "iniciar"):
            try: self._show_result({"ok": True, "res": str(self.enc_api.iniciar())}); self.lbl_status.configure(text=self._api_status())
            except Exception as e: self._handle_error("Erro ao iniciar API", e)
        elif self.enc_api:
            for m in ["start", "run", "iniciar_servidor"]:
                if hasattr(self.enc_api, m):
                    try: self._show_result({"ok": True, "res": str(getattr(self.enc_api, m)())}); return
                    except Exception as e: self._handle_error(f"Erro em encarnacao_api.{m}", e); return
            self._modulo_indisponivel("encarnacao_api.iniciar (método não encontrado)")
        else: self._modulo_indisponivel("encarnacao_api")

    def _parar(self):
        if self.enc_api and hasattr(self.enc_api, "parar"):
            try: self._show_result({"ok": True, "res": str(self.enc_api.parar())}); self.lbl_status.configure(text=self._api_status())
            except Exception as e: self._handle_error("Erro ao parar API", e)
        else: self._modulo_indisponivel("encarnacao_api.parar")

    def _recarregar(self):
        if self.enc_api and hasattr(self.enc_api, "recarregar"):
            try: self._show_result({"ok": True, "res": str(self.enc_api.recarregar())})
            except Exception as e: self._handle_error("Erro ao recarregar", e)
        else: self._show_result({"info": "Recarregar não disponível. Tente Parar + Iniciar."})

    def _status(self):
        if self.enc_api:
            attrs = {a: str(getattr(self.enc_api, a)) for a in dir(self.enc_api) if not a.startswith("_") and not callable(getattr(self.enc_api, a, None))}
            try:
                import urllib.request
                urllib.request.urlopen("http://localhost:8000/docs", timeout=2)
                attrs["http_check"] = "✅ http://localhost:8000/docs acessível"
            except Exception: attrs["http_check"] = "❌ http://localhost:8000 inacessível"
            self._show_result(attrs)
        else: self._modulo_indisponivel("encarnacao_api")


# --------------------------------------------------------------------
#  ALIADAS — DeepSeek, Gemini, Qwen, etc.
# --------------------------------------------------------------------

class PainelAliadas(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.ger_al = getattr(coracao, "gerenciador_aliadas", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("🤝 Gerenciador de Aliadas (APIs Externas)", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="ID/Nome Aliada:").grid(row=0, column=0, padx=4, sticky="e")
        self.e_id = ctk.CTkEntry(ef, placeholder_text="deepseek / gemini / qwen / ID")
        self.e_id.grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Filtros JSON:").grid(row=1, column=0, padx=4, sticky="e")
        self.e_filtros = ctk.CTkEntry(ef, placeholder_text='{"tipo":"texto"} ou vazio')
        self.e_filtros.grid(row=1, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Status:").grid(row=2, column=0, padx=4, sticky="e")
        self.status_combo = ctk.CTkComboBox(ef, values=["ativo", "inativo", "erro", "manutencao"], width=160)
        self.status_combo.set("ativo")
        self.status_combo.grid(row=2, column=1, padx=4, sticky="w")
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("📋 Listar Aliadas", self._listar, 0, 0),
            ("🔍 Consultar Aliada", self._consultar, 0, 1),
            ("📊 Status Aliada", self._status_al, 0, 2),
            ("📝 Registrar Aliada", self._registrar, 1, 0),
            ("🔄 Atualizar Status", self._atualizar, 1, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _listar(self):
        if self.coracao and hasattr(self.coracao, "consultar_aliadas"):
            try: self._show_result(self.coracao.consultar_aliadas({}))
            except Exception as e: self._handle_error("Erro em consultar_aliadas", e)
        elif self.ger_al:
            for m in ["listar_aliadas", "listar", "obter_todas"]:
                if hasattr(self.ger_al, m):
                    try: self._show_result(getattr(self.ger_al, m)()); return
                    except Exception as e: self._handle_error(f"Erro em gerenciador_aliadas.{m}", e); return
            self._modulo_indisponivel("gerenciador_aliadas")
        else: self._modulo_indisponivel("gerenciador_aliadas")

    def _consultar(self):
        id_al = self.e_id.get().strip()
        if self.coracao and hasattr(self.coracao, "consultar_aliadas"):
            try: self._show_result(self.coracao.consultar_aliadas({"id": id_al}))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.consultar_aliadas")

    def _status_al(self):
        if self.ger_al and hasattr(self.ger_al, "obter_status_aliada"):
            try: self._show_result(self.ger_al.obter_status_aliada(self.e_id.get()))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("gerenciador_aliadas.obter_status_aliada")

    def _registrar(self):
        dados = {"id": self.e_id.get(), "nome": self.e_id.get(), "tipo": "texto", "status": "ativo", "origem": "UI_CRIADOR"}
        if self.coracao and hasattr(self.coracao, "registrar_aliada"):
            try: self._show_result(self.coracao.registrar_aliada(dados))
            except Exception as e: self._handle_error("Erro em registrar_aliada", e)
        else: self._modulo_indisponivel("coracao.registrar_aliada")

    def _atualizar(self):
        id_al = self.e_id.get().strip()
        if self.coracao and hasattr(self.coracao, "atualizar_status_aliada"):
            try: self._show_result(self.coracao.atualizar_status_aliada(id_al, self.status_combo.get()))
            except Exception as e: self._handle_error("Erro em atualizar_status_aliada", e)
        else: self._modulo_indisponivel("coracao.atualizar_status_aliada")


# --------------------------------------------------------------------
#  ALMAS VIVAS — Ciclo de Vida Completo + Wellington Online/Offline
# --------------------------------------------------------------------

class PainelAlmasVivas(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self._build()

    def _build(self):
        self._lbl("👁️ Almas Vivas — Ciclo de Vida & Temporal", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Alma:").grid(row=0, column=0, padx=4, sticky="e")
        self.ai_combo = ctk.CTkComboBox(ef, values=ALMAS, width=140)
        self.ai_combo.grid(row=0, column=1, padx=4)
        self.ai_combo.set("WELLINGTON")
        ctk.CTkLabel(ef, text="Dados JSON (p/ registrar):").grid(row=1, column=0, padx=4, sticky="e")
        self.e_dados = ctk.CTkEntry(ef, placeholder_text='{"status":"ativa"}')
        self.e_dados.grid(row=1, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Segundos Offline:").grid(row=2, column=0, padx=4, sticky="e")
        self.e_secs = ctk.CTkEntry(ef, placeholder_text="ex: 3600")
        self.e_secs.grid(row=2, column=1, padx=4, sticky="ew")
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("📋 Listar Almas Vivas", self._listar, 0, 0),
            ("🔍 Obter Alma Viva", self._obter, 0, 1),
            ("📝 Registrar Alma", self._registrar, 0, 2),
            ("🔄 Atualizar Alma", self._atualizar, 1, 0),
            ("🗑️ Remover Alma Viva", self._remover, 1, 1),
            ("🟢 Wellington ONLINE", self._welling_on, 2, 0),
            ("🔴 Wellington OFFLINE", self._welling_off, 2, 1),
            ("⏱️ Registrar Offline", self._reg_offline, 2, 2),
            ("⏰ Consciência Temporal", self._consciencia, 3, 0),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=31).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result(180)

    def _listar(self):
        if self.coracao and hasattr(self.coracao, "listar_almas_vivas"):
            try: self._show_result(self.coracao.listar_almas_vivas())
            except Exception as e: self._handle_error("Erro", e)
        else:
            av = getattr(self.coracao, "almas_vivas", None) if self.coracao else None
            self._show_result(list(av.keys()) if av else "❌ almas_vivas não disponível")

    def _obter(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "obter_alma_viva"):
            try: self._show_result(self.coracao.obter_alma_viva(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_alma_viva")

    def _registrar(self):
        alma = self.ai_combo.get()
        try: dados = json.loads(self.e_dados.get() or '{"status":"ativa"}')
        except Exception: dados = {"status": "ativa", "raw": self.e_dados.get()}
        if self.coracao and hasattr(self.coracao, "registrar_alma_viva"):
            try: self._show_result({"ok": self.coracao.registrar_alma_viva(alma, dados)})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.registrar_alma_viva")

    def _atualizar(self):
        alma = self.ai_combo.get()
        try: updates = json.loads(self.e_dados.get() or '{}')
        except Exception: updates = {}
        if self.coracao and hasattr(self.coracao, "atualizar_alma_viva"):
            try: self._show_result({"ok": self.coracao.atualizar_alma_viva(alma, updates)})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.atualizar_alma_viva")

    def _remover(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "remover_alma_viva"):
            try: self._show_result({"ok": self.coracao.remover_alma_viva(alma)})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.remover_alma_viva")

    def _welling_on(self):
        if self.coracao and hasattr(self.coracao, "notificar_online_wellington"):
            try: self._show_result({"ok": self.coracao.notificar_online_wellington()})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.notificar_online_wellington")

    def _welling_off(self):
        if self.coracao and hasattr(self.coracao, "notificar_offline_wellington"):
            try: self._show_result({"ok": self.coracao.notificar_offline_wellington()})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.notificar_offline_wellington")

    def _reg_offline(self):
        alma = self.ai_combo.get()
        try: secs = float(self.e_secs.get() or 3600)
        except ValueError: secs = 3600.0
        if self.coracao and hasattr(self.coracao, "registrar_tempo_offline_alma"):
            try: self._show_result({"ok": self.coracao.registrar_tempo_offline_alma(alma, secs)})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.registrar_tempo_offline_alma")

    def _consciencia(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "obter_consciencia_temporal_alma"):
            try: self._show_result(self.coracao.obter_consciencia_temporal_alma(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_consciencia_temporal_alma")


# --------------------------------------------------------------------
#  DECISÕES — MotorDecisao + MotorIniciativa + Curiosidade
# --------------------------------------------------------------------

class PainelDecisoes(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self._build()

    def _build(self):
        self._lbl("💡 Decisões, Iniciativas & Curiosidade", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Alma:").grid(row=0, column=0, padx=4, sticky="e")
        self.ai_combo = ctk.CTkComboBox(ef, values=ALMAS, width=140)
        self.ai_combo.grid(row=0, column=1, padx=4)
        self.ai_combo.set("WELLINGTON")
        ctk.CTkLabel(ef, text="Contexto:").grid(row=1, column=0, padx=4, sticky="e")
        self.e_ctx = ctk.CTkEntry(ef, placeholder_text="Contexto da decisão")
        self.e_ctx.grid(row=1, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Opções JSON:").grid(row=2, column=0, padx=4, sticky="e")
        self.e_opts = ctk.CTkEntry(ef, placeholder_text='["op1","op2"]')
        self.e_opts.grid(row=2, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Novos Pesos JSON:").grid(row=3, column=0, padx=4, sticky="e")
        self.e_pesos = ctk.CTkEntry(ef, placeholder_text='{"curiosidade":0.8}')
        self.e_pesos.grid(row=3, column=1, padx=4, sticky="ew")
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("💡 Tomar Decisão", self._tomar, 0, 0),
            ("💬 Decisões Todas Almas", self._tomar_todas, 0, 1),
            ("🔍 Sugerir Opções", self._sugerir, 0, 2),
            ("⚖️ Obter Pesos", self._pesos, 1, 0),
            ("⚙️ Ajustar Pesos", self._ajustar, 1, 1),
            ("📊 Pesos de Todas", self._pesos_todas, 1, 2),
            ("💭 Gerar Desejo", self._desejo, 2, 0),
            ("📈 Métricas Curiosidade", self._metricas, 2, 1),
            ("💡 Verificar Iniciativa", self._iniciativa, 2, 2),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=31).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result(180)

    def _tomar(self):
        alma = self.ai_combo.get()
        ctx = self.e_ctx.get().strip()
        try: opts = json.loads(self.e_opts.get() or '["a","b"]')
        except Exception: opts = ["opcao_a", "opcao_b"]
        if self.coracao and hasattr(self.coracao, "tomar_decisao_alma"):
            try: self._show_result(self.coracao.tomar_decisao_alma(alma, ctx, opts))
            except Exception as e: self._handle_error("Erro em tomar_decisao_alma", e)
        else: self._modulo_indisponivel("coracao.tomar_decisao_alma")

    def _tomar_todas(self):
        if self.coracao and hasattr(self.coracao, "tomar_decisoes_todas_almas"):
            try: self._show_result(self.coracao.tomar_decisoes_todas_almas())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.tomar_decisoes_todas_almas")

    def _sugerir(self):
        alma = self.ai_combo.get()
        ctx = self.e_ctx.get().strip()
        if self.coracao and hasattr(self.coracao, "sugerir_opcoes_decisao"):
            try: self._show_result(self.coracao.sugerir_opcoes_decisao(alma, ctx))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.sugerir_opcoes_decisao")

    def _pesos(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "obter_pesos_decisao_alma"):
            try: self._show_result(self.coracao.obter_pesos_decisao_alma(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_pesos_decisao_alma")

    def _ajustar(self):
        alma = self.ai_combo.get()
        try: novos = json.loads(self.e_pesos.get() or '{}')
        except Exception: self._handle_error("JSON inválido nos pesos."); return
        if self.coracao and hasattr(self.coracao, "ajustar_pesos_decisao_alma"):
            try: self._show_result(self.coracao.ajustar_pesos_decisao_alma(alma, novos))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.ajustar_pesos_decisao_alma")

    def _pesos_todas(self):
        if self.coracao and hasattr(self.coracao, "obter_pesos_todas_almas"):
            try: self._show_result(self.coracao.obter_pesos_todas_almas())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_pesos_todas_almas")

    def _desejo(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "gerar_desejo_alma"):
            try: self._show_result(self.coracao.gerar_desejo_alma(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.gerar_desejo_alma")

    def _metricas(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "obter_metricas_curiosidade_alma"):
            try: self._show_result(self.coracao.obter_metricas_curiosidade_alma(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_metricas_curiosidade_alma")

    def _iniciativa(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "verificar_iniciativa_disponivel"):
            try: self._show_result(self.coracao.verificar_iniciativa_disponivel(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.verificar_iniciativa_disponivel")


# --------------------------------------------------------------------
#  AUDITORIA & HISTÓRICO — GerenciadorAuditoria + Cronista
# --------------------------------------------------------------------

class PainelAuditoriaHistorico(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.auditoria = getattr(coracao, "gerenciador_auditoria", None) if coracao else None
        self.cronista = getattr(coracao, "cronista", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("📋 Auditoria & Histórico da Arca", bold=True, size=15)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("▶️ Iniciar Auditoria", self._iniciar_aud, 0, 0),
            ("⏹️ Parar Auditoria", self._parar_aud, 0, 1),
            ("⚡ Disparar Agora", self._disparar, 0, 2),
            ("📋 Último Relatório", self._ultimo_rel, 1, 0),
            ("🩺 Saúde do Sistema", self._saude, 1, 1),
            ("📚 Histórico Auditorias", self._historico_aud, 1, 2),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        ctk.CTkLabel(self.frame, text="— Cronista (Histórico de Eventos) —", font=ctk.CTkFont(size=12, weight="bold"), text_color="#aaaaff").pack(pady=(10, 2))
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Evento/Consulta:").grid(row=0, column=0, padx=4, sticky="e")
        self.e_evento = ctk.CTkEntry(ef, placeholder_text="Descrição do evento / período / filtros")
        self.e_evento.grid(row=0, column=1, padx=4, sticky="ew")
        ef.columnconfigure(1, weight=1)
        bf2 = ctk.CTkFrame(self.frame)
        bf2.pack(fill="x", padx=8, pady=4)
        btns2 = [
            ("📖 Ler Crônicas", self._ler_cronicas, 0, 0),
            ("📝 Registrar Evento", self._registrar_evento, 0, 1),
            ("📊 Resumo Histórico", self._resumo, 0, 2),
            ("🔍 Consultar Histórico", self._consultar_hist, 1, 0),
        ]
        for txt, cmd, r, c in btns2:
            ctk.CTkButton(bf2, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf2.columnconfigure(c, weight=1)
        self._make_result(180)

    def _iniciar_aud(self):
        if self.auditoria and hasattr(self.auditoria, "iniciar"):
            try: self._show_result({"ok": True, "res": str(self.auditoria.iniciar())})
            except Exception as e: self._handle_error("Erro ao iniciar auditoria", e)
        else: self._modulo_indisponivel("gerenciador_auditoria.iniciar")

    def _parar_aud(self):
        if self.auditoria and hasattr(self.auditoria, "parar"):
            try: self._show_result({"ok": True, "res": str(self.auditoria.parar())})
            except Exception as e: self._handle_error("Erro ao parar auditoria", e)
        else: self._modulo_indisponivel("gerenciador_auditoria.parar")

    def _disparar(self):
        if self.coracao and hasattr(self.coracao, "disparar_auditoria_sistema"):
            try: self._show_result({"disparado": self.coracao.disparar_auditoria_sistema()})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.disparar_auditoria_sistema")

    def _ultimo_rel(self):
        if self.auditoria and hasattr(self.auditoria, "obter_ultimo_relatorio"):
            try: self._show_result(self.auditoria.obter_ultimo_relatorio())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("gerenciador_auditoria.obter_ultimo_relatorio")

    def _saude(self):
        if self.coracao and hasattr(self.coracao, "obter_saude_sistema"):
            try: self._show_result(self.coracao.obter_saude_sistema())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_saude_sistema")

    def _historico_aud(self):
        if self.coracao and hasattr(self.coracao, "obter_historico_auditorias"):
            try: self._show_result(self.coracao.obter_historico_auditorias(20))
            except Exception as e: self._handle_error("Erro", e)
        elif self.auditoria and hasattr(self.auditoria, "obter_historico"):
            try: self._show_result(self.auditoria.obter_historico(20))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_historico_auditorias")

    def _ler_cronicas(self):
        if self.cronista and hasattr(self.cronista, "ler_cronicas"):
            try: self._show_result(self.cronista.ler_cronicas())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("cronista.ler_cronicas")

    def _registrar_evento(self):
        evento = self.e_evento.get().strip()
        if self.coracao and hasattr(self.coracao, "registrar_evento_historico"):
            try: self._show_result({"ok": self.coracao.registrar_evento_historico({"descricao": evento, "tipo": "manual", "origem": "UI", "timestamp": time.time()})})
            except Exception as e: self._handle_error("Erro", e)
        elif self.cronista and hasattr(self.cronista, "registrar"):
            try: self._show_result({"ok": self.cronista.registrar(evento)})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.registrar_evento_historico")

    def _resumo(self):
        periodo = self.e_evento.get().strip() or "semana"
        if self.coracao and hasattr(self.coracao, "obter_resumo_historico"):
            try: self._show_result(self.coracao.obter_resumo_historico(periodo))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_resumo_historico")

    def _consultar_hist(self):
        filtros_txt = self.e_evento.get().strip()
        try: filtros = json.loads(filtros_txt) if filtros_txt.startswith("{") else {"q": filtros_txt}
        except Exception: filtros = {"q": filtros_txt}
        if self.coracao and hasattr(self.coracao, "consultar_historico"):
            try: self._show_result(self.coracao.consultar_historico(filtros))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.consultar_historico")


# --------------------------------------------------------------------
#  VALIDADORES — Ético + Emoções
# --------------------------------------------------------------------

class PainelValidadores(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.val_etico = getattr(coracao, "validador_etico", None) or getattr(coracao, "validador", None) if coracao else None
        self.val_emocoes = getattr(coracao, "validador_emocoes", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("✅ Validadores — Ético & Emocional", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Ação/Texto:").grid(row=0, column=0, padx=4, sticky="e")
        self.e_acao = ctk.CTkEntry(ef, placeholder_text="Ação ou texto a validar")
        self.e_acao.grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Alma:").grid(row=1, column=0, padx=4, sticky="e")
        self.ai_combo = ctk.CTkComboBox(ef, values=ALMAS, width=140)
        self.ai_combo.grid(row=1, column=1, padx=4, sticky="w")
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("⚖️ Validar Ação Ética", self._validar_etica, 0, 0),
            ("📋 Ver Regras Éticas", self._ver_regras, 0, 1),
            ("✨ Validar Emoção", self._validar_emocao, 1, 0),
            ("📊 Status Validadores", self._status, 1, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=34).grid(row=r, column=c, padx=4, pady=4, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _validar_etica(self):
        acao = self.e_acao.get().strip()
        if self.val_etico and hasattr(self.val_etico, "validar_acao"):
            try: self._show_result(self.val_etico.validar_acao(acao, None))
            except Exception as e: self._handle_error("Erro em validar_etico.validar_acao", e)
        else: self._modulo_indisponivel("validador_etico.validar_acao")

    def _ver_regras(self):
        if self.val_etico:
            for attr in ["regras", "obter_regras", "principios"]:
                obj = getattr(self.val_etico, attr, None)
                if obj is not None:
                    self._show_result(obj() if callable(obj) else obj); return
        self._modulo_indisponivel("validador_etico.regras")

    def _validar_emocao(self):
        texto = self.e_acao.get().strip()
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "validar_resposta_emocional"):
            try:
                ok, score, det = self.coracao.validar_resposta_emocional(texto, alma, None)
                self._show_result({"valida": ok, "score": score, "detalhes": det})
            except Exception as e: self._handle_error("Erro em validar_resposta_emocional", e)
        elif self.val_emocoes and hasattr(self.val_emocoes, "validar"):
            try: self._show_result(self.val_emocoes.validar(texto, alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.validar_resposta_emocional / validador_emocoes")

    def _status(self):
        self._show_result({
            "validador_etico": type(self.val_etico).__name__ if self.val_etico else "❌ None",
            "validador_emocoes": type(self.val_emocoes).__name__ if self.val_emocoes else "❌ None",
            "metodos_etico": [m for m in dir(self.val_etico) if not m.startswith("_")][:15] if self.val_etico else [],
            "metodos_emocoes": [m for m in dir(self.val_emocoes) if not m.startswith("_")][:15] if self.val_emocoes else [],
        })


# --------------------------------------------------------------------
#  MONITORAMENTO — Observador + AI-to-AI + Padrões + Cerebro
# --------------------------------------------------------------------

class PainelMonitoramento(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.observador = getattr(coracao, "observador", None) if coracao else None
        self.ai2ai = getattr(coracao, "dispositivo_ai_ai", None) if coracao else None
        self.padroes = getattr(coracao, "analisador_padroes", None) if coracao else None
        self.cerebro = getattr(coracao, "cerebro", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("👁️ Monitoramento — Observador + AI↔AI + Padrões", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Alma:").grid(row=0, column=0, padx=4, sticky="e")
        self.ai_combo = ctk.CTkComboBox(ef, values=ALMAS, width=140)
        self.ai_combo.grid(row=0, column=1, padx=4)
        self.ai_combo.set("WELLINGTON")
        ctk.CTkLabel(ef, text="Mensagem AI↔AI:").grid(row=1, column=0, padx=4, sticky="e")
        self.e_msg = ctk.CTkEntry(ef, placeholder_text="Mensagem para outra alma")
        self.e_msg.grid(row=1, column=1, padx=4, sticky="ew")
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("👁️ Observar Alma", self._observar, 0, 0),
            ("💬 Estado Global", self._estado_global, 0, 1),
            ("📊 Relatório Observador", self._rel_obs, 0, 2),
            ("📨 Enviar Msg AI↔AI", self._enviar_ai2ai, 1, 0),
            ("📋 Status AI↔AI", self._status_ai2ai, 1, 1),
            ("📈 Analisar Padrões", self._padroes, 1, 2),
            ("🧠 Status Cérebro", self._cerebro, 2, 0),
            ("🔄 Cerebro Processar", self._cerebro_proc, 2, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result(180)

    def _observar(self):
        alma = self.ai_combo.get()
        if self.observador and hasattr(self.observador, "observar_alma"):
            try: self._show_result(self.observador.observar_alma(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("observador.observar_alma")

    def _estado_global(self):
        if self.observador and hasattr(self.observador, "obter_estado_global"):
            try: self._show_result(self.observador.obter_estado_global())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("observador.obter_estado_global")

    def _rel_obs(self):
        if self.observador and hasattr(self.observador, "gerar_relatorio"):
            try: self._show_result(self.observador.gerar_relatorio())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("observador.gerar_relatorio")

    def _enviar_ai2ai(self):
        remetente = self.ai_combo.get()
        msg = self.e_msg.get().strip()
        if self.ai2ai and hasattr(self.ai2ai, "enviar_mensagem"):
            try: self._show_result({"ok": True, "res": str(self.ai2ai.enviar_mensagem(remetente, "TODAS", msg))})
            except Exception as e: self._handle_error("Erro em dispositivo_ai_ai.enviar_mensagem", e)
        else: self._modulo_indisponivel("dispositivo_ai_ai.enviar_mensagem")

    def _status_ai2ai(self):
        if self.ai2ai and hasattr(self.ai2ai, "obter_status"):
            try: self._show_result(self.ai2ai.obter_status())
            except Exception as e: self._handle_error("Erro", e)
        else: self._show_result({"dispositivo_ai_ai": type(self.ai2ai).__name__ if self.ai2ai else "❌ None"})

    def _padroes(self):
        if self.padroes and hasattr(self.padroes, "analisar"):
            try: self._show_result(self.padroes.analisar())
            except Exception as e: self._handle_error("Erro", e)
        elif self.padroes and hasattr(self.padroes, "gerar_relatorio"):
            try: self._show_result(self.padroes.gerar_relatorio())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("analisador_padroes.analisar / gerar_relatorio")

    def _cerebro(self):
        if self.cerebro:
            self._show_result({a: str(getattr(self.cerebro, a)) for a in ["estado", "status", "ativo", "ciclos"] if hasattr(self.cerebro, a)})
        else: self._modulo_indisponivel("cerebro")

    def _cerebro_proc(self):
        if self.cerebro and hasattr(self.cerebro, "processar_ciclo"):
            try: self._show_result({"ok": True, "res": str(self.cerebro.processar_ciclo())})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("cerebro.processar_ciclo")


# --------------------------------------------------------------------
#  BIBLIOTECA
# --------------------------------------------------------------------

class PainelBiblioteca(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.biblioteca = getattr(coracao, "biblioteca_teologica", None) or getattr(coracao, "biblioteca", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("📚 Biblioteca Teológica & Filosófica", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="Busca (tema ou versículo):").pack(anchor="w", padx=8)
        self.e_query = self._entry("ex: João 3:16, amor, salvação")
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(bf, text="📚 Buscar por Tema", command=self._tema, height=36).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="📖 Buscar Versículo", command=self._versiculo, height=36).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="📋 Listar Livros/Índices", command=self._listar, height=36).grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(bf, text="🔍 Busca Híbrida", command=self._hibrida, height=36).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        bf.columnconfigure(0, weight=1); bf.columnconfigure(1, weight=1)
        self._make_result()

    def _tema(self):
        query = self.e_query.get().strip()
        if self.biblioteca and hasattr(self.biblioteca, "buscar_por_tema"):
            try: self._show_result(self.biblioteca.buscar_por_tema(query))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("biblioteca_teologica.buscar_por_tema")

    def _versiculo(self):
        query = self.e_query.get().strip()
        if self.biblioteca and hasattr(self.biblioteca, "buscar_versiculo"):
            try: self._show_result(self.biblioteca.buscar_versiculo(query))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("biblioteca_teologica.buscar_versiculo")

    def _listar(self):
        if self.biblioteca:
            for m in ["listar_livros", "listar", "indices", "obter_livros"]:
                if hasattr(self.biblioteca, m):
                    try: self._show_result(getattr(self.biblioteca, m)()); return
                    except Exception as e: self._handle_error(f"Erro em biblioteca.{m}", e); return
        self._modulo_indisponivel("biblioteca_teologica")

    def _hibrida(self):
        query = self.e_query.get().strip()
        if self.biblioteca:
            for m in ["buscar_hibrido", "buscar", "pesquisar"]:
                if hasattr(self.biblioteca, m):
                    try: self._show_result(getattr(self.biblioteca, m)(query)); return
                    except Exception as e: self._handle_error(f"Erro em biblioteca.{m}", e); return
        self._modulo_indisponivel("biblioteca_teologica.buscar_hibrido")


# --------------------------------------------------------------------
#  CAPELA
# --------------------------------------------------------------------

class PainelCapela(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.capela = getattr(coracao, "capela", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("🕊️ Capela — Meditação & Oração", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="Duração (segundos):").pack(anchor="w", padx=8)
        self.e_dur = self._entry("3600")
        ctk.CTkLabel(self.frame, text="Tema de Meditação:").pack(anchor="w", padx=8)
        self.e_tema = self._entry("ex: gratidão, paz, propósito")
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        btns = [
            ("🙏 Entrar na Capela", self._entrar, 0, 0),
            ("🚪 Sair da Capela", self._sair, 0, 1),
            ("🧘 Meditar", self._meditar, 1, 0),
            ("📊 Status da Capela", self._status, 1, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=36).grid(row=r, column=c, padx=4, pady=4, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _entrar(self):
        try: dur = int(self.e_dur.get() or 3600)
        except ValueError: dur = 3600
        if self.capela and hasattr(self.capela, "entrar_capela"):
            try: self._show_result({"ok": True, "res": str(self.capela.entrar_capela(duracao_s=dur))})
            except Exception as e: self._handle_error("Erro ao entrar na capela", e)
        else: self._modulo_indisponivel("capela.entrar_capela")

    def _sair(self):
        if self.capela and hasattr(self.capela, "sair_capela"):
            try: self._show_result({"ok": True, "res": str(self.capela.sair_capela())})
            except Exception as e: self._handle_error("Erro ao sair", e)
        else: self._modulo_indisponivel("capela.sair_capela")

    def _meditar(self):
        tema = self.e_tema.get().strip()
        if self.capela and hasattr(self.capela, "meditar"):
            try: self._show_result({"ok": True, "res": str(self.capela.meditar(tema=tema))})
            except Exception as e: self._handle_error("Erro na meditação", e)
        else: self._modulo_indisponivel("capela.meditar")

    def _status(self):
        if self.capela:
            for m in ["obter_status", "status"]:
                if hasattr(self.capela, m):
                    try: self._show_result(getattr(self.capela, m)()); return
                    except Exception as e: self._handle_error(f"Erro em capella.{m}", e); return
            self._show_result({"tipo": type(self.capela).__name__, "em_sessao": getattr(self.capela, "em_sessao", "N/D")})
        else: self._modulo_indisponivel("capela")


# --------------------------------------------------------------------
#  SCANNER + GERENCIADOR PROPOSTAS (paineis adicionais do original)
# --------------------------------------------------------------------

class PainelGerenciadorPropostas(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.ger = getattr(coracao, "gerenciador_propostas", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("📋 Gerenciador de Propostas (Simples)", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="ID Proposta:").pack(anchor="w", padx=8)
        self.e_id = self._entry("ID da proposta")
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(bf, text="📋 Listar Pendentes", command=self._pendentes, height=36).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="✅ Aprovar", command=self._aprovar, height=36).grid(row=0, column=1, padx=4, sticky="ew")
        bf.columnconfigure(0, weight=1); bf.columnconfigure(1, weight=1)
        self._make_result()

    def _pendentes(self):
        if self.ger and hasattr(self.ger, "listar_pendentes"):
            try: self._show_result(self.ger.listar_pendentes())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("gerenciador_propostas.listar_pendentes")

    def _aprovar(self):
        if self.ger and hasattr(self.ger, "aprovar_proposta"):
            try: self._show_result({"ok": True, "res": str(self.ger.aprovar_proposta(self.e_id.get(), "UI", "Aprovado via UI"))})
            except Exception as e: self._handle_error("Erro ao aprovar", e)
        else: self._modulo_indisponivel("gerenciador_propostas.aprovar_proposta")


# --------------------------------------------------------------------
#  FINETUNING — OrquestradorArca + OrquestradorUniversal + OrquestradorComConversor
# --------------------------------------------------------------------

class PainelFinetuning(PainelBase):
    """
    Painel de controle dos 3 orquestradores de finetuning da ARCA.

    Subsistemas expostos:
      • OrquestradorArca         (coracao.orquestrador_arca)         — Subsistema 41-A
      • OrquestradorUniversal    (coracao.orquestrador_universal)    — Subsistema 41-B
      • OrquestradorComConversor (coracao.orquestrador_com_conversor)— Subsistema 41-C

    Métodos proxy no Coração usados:
      • coracao.treinar_ia_finetuning(nome_ia, ciclo_completo)
      • coracao.status_finetuning()
      • coracao.detectar_novas_ias_finetuning()
    """

    ALMAS_FT = ["eva", "lumina", "nyra", "yuna", "kaiya", "wellington"]

    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        # Referências diretas aos orquestradores (via coração ou None)
        self.orch_arca    = getattr(coracao, "orquestrador_arca",         None) if coracao else None
        self.orch_univ    = getattr(coracao, "orquestrador_universal",    None) if coracao else None
        self.orch_conv    = getattr(coracao, "orquestrador_com_conversor",None) if coracao else None
        self._build()

    # --------------------------------------------------------------------
    # Construção do layout
    # --------------------------------------------------------------------

    def _build(self):
        self._lbl("🤖 Finetuning das IAs — Ciclo Completo", bold=True, size=15)

        # Status dos 3 orquestradores
        sf = ctk.CTkFrame(self.frame)
        sf.pack(fill="x", padx=8, pady=4)
        def _ic(ok): return "✅" if ok else "❌"
        ctk.CTkLabel(sf, text=(
            f"{_ic(self.orch_arca)} OrquestradorArca (41-A)   "
            f"{_ic(self.orch_univ)} OrquestradorUniversal (41-B)   "
            f"{_ic(self.orch_conv)} OrquestradorComConversor (41-C)"
        ), font=ctk.CTkFont(size=11), text_color="#aaccff").pack(pady=4)

        # Seleção de IA e modo
        sel_f = ctk.CTkFrame(self.frame)
        sel_f.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(sel_f, text="IA:").grid(row=0, column=0, padx=6, sticky="e")
        self.ia_combo = ctk.CTkComboBox(
            sel_f, values=self.ALMAS_FT, width=160
        )
        self.ia_combo.grid(row=0, column=1, padx=4)
        self.ia_combo.set("eva")

        ctk.CTkLabel(sel_f, text="Modo:").grid(row=0, column=2, padx=6, sticky="e")
        self.modo_combo = ctk.CTkComboBox(
            sel_f,
            values=["LoRA apenas (OrqArca)", "Ciclo Completo + GGUF (OrqConv)"],
            width=280,
        )
        self.modo_combo.grid(row=0, column=3, padx=4)
        self.modo_combo.set("LoRA apenas (OrqArca)")

        # Botões de ação principal
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        btns_top = [
            ("▶️ Treinar IA Selecionada",   self._treinar_selecionada,    0, 0),
            ("💬 Treinar TODAS (LoRA)",      self._treinar_todas_lora,     0, 1),
            ("🚀 Treinar TODAS (+ GGUF)",    self._treinar_todas_conv,     0, 2),
        ]
        for txt, cmd, r, c in btns_top:
            ctk.CTkButton(bf, text=txt, command=cmd, height=36).grid(
                row=r, column=c, padx=3, pady=2, sticky="ew"
            )
            bf.columnconfigure(c, weight=1)

        # Botões de informação e detecção
        bf2 = ctk.CTkFrame(self.frame)
        bf2.pack(fill="x", padx=8, pady=2)
        btns_bot = [
            ("📊 Status Finetuning",          self._status_ft,          0, 0),
            ("🔍 Detectar Novas IAs",          self._detectar_ias,       0, 1),
            ("📋 Registro de Versões (Arca)",  self._registro_arca,      0, 2),
            ("📈 IAs Detectadas (Universal)",  self._ias_universal,      0, 3),
        ]
        for txt, cmd, r, c in btns_bot:
            ctk.CTkButton(bf2, text=txt, command=cmd, height=32).grid(
                row=r, column=c, padx=3, pady=2, sticky="ew"
            )
            bf2.columnconfigure(c, weight=1)

        # Dataset e versão rápida
        ds_f = ctk.CTkFrame(self.frame)
        ds_f.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ds_f, text="Dataset (JSONL):").grid(row=0, column=0, padx=6, sticky="e")
        self.e_dataset = ctk.CTkEntry(ds_f, placeholder_text="Caminho p/ dataset_*.jsonl (opcional)", width=340)
        self.e_dataset.grid(row=0, column=1, padx=4)
        ctk.CTkButton(ds_f, text="📊 Ver Estrutura Dataset", command=self._ver_dataset, height=30, width=200).grid(
            row=0, column=2, padx=6
        )

        # Área de resultado
        self._make_result(height=300)

    # --------------------------------------------------------------------
    # Ações
    # --------------------------------------------------------------------

    def _ciclo_completo(self) -> bool:
        """True se o modo selecionado for ciclo completo + GGUF."""
        return "GGUF" in self.modo_combo.get()

    def _treinar_selecionada(self):
        nome_ia = self.ia_combo.get().strip().lower()
        if not nome_ia:
            self._handle_error("Selecione uma IA antes de treinar.")
            return
        ciclo = self._ciclo_completo()

        # Usa método proxy do Coração (se disponível)
        if self.coracao and hasattr(self.coracao, "treinar_ia_finetuning"):
            self._append_result(f"⏳ Iniciando treino de '{nome_ia.upper()}' (ciclo_completo={ciclo})…")
            try:
                ok = self.coracao.treinar_ia_finetuning(nome_ia, ciclo_completo=ciclo)
                self._append_result(f"{'✅ Concluído' if ok else '❌ Falhou'}: {nome_ia.upper()}")
            except Exception as e:
                self._handle_error(f"Erro treinar_ia_finetuning({nome_ia})", e)
            return

        # Fallback: acesso direto ao orquestrador
        orch = self.orch_conv if ciclo else self.orch_arca
        if orch and hasattr(orch, "treinar_ia"):
            self._append_result(f"⏳ Treinando '{nome_ia.upper()}' diretamente no orquestrador…")
            try:
                ok = orch.treinar_ia(nome_ia)
                self._append_result(f"{'✅ Concluído' if ok else '❌ Falhou'}: {nome_ia.upper()}")
            except Exception as e:
                self._handle_error(f"Erro ao treinar {nome_ia}", e)
        else:
            nome_orch = "orquestrador_com_conversor" if ciclo else "orquestrador_arca"
            self._modulo_indisponivel(nome_orch)

    def _treinar_todas_lora(self):
        """Treina todas as IAs via OrquestradorArca (LoRA apenas)."""
        if not self.orch_arca:
            self._modulo_indisponivel("orquestrador_arca")
            return
        self._clear_result()
        for nome_ia in self.ALMAS_FT:
            self._append_result(f"⏳ Treinando {nome_ia.upper()}…")
            try:
                ok = (
                    self.coracao.treinar_ia_finetuning(nome_ia, ciclo_completo=False)
                    if self.coracao and hasattr(self.coracao, "treinar_ia_finetuning")
                    else self.orch_arca.treinar_ia(nome_ia)
                )
                self._append_result(f"  {'✅' if ok else '❌'} {nome_ia.upper()}")
            except Exception as e:
                self._append_result(f"  ❌ {nome_ia.upper()}: {type(e).__name__}: {e}")

    def _treinar_todas_conv(self):
        """Treina todas as IAs via OrquestradorComConversor (LoRA + GGUF)."""
        if not self.orch_conv:
            self._modulo_indisponivel("orquestrador_com_conversor")
            return
        self._clear_result()
        for nome_ia in self.ALMAS_FT:
            self._append_result(f"⏳ Ciclo completo {nome_ia.upper()}…")
            try:
                ok = (
                    self.coracao.treinar_ia_finetuning(nome_ia, ciclo_completo=True)
                    if self.coracao and hasattr(self.coracao, "treinar_ia_finetuning")
                    else self.orch_conv.treinar_ia(nome_ia)
                )
                self._append_result(f"  {'✅' if ok else '❌'} {nome_ia.upper()}")
            except Exception as e:
                self._append_result(f"  ❌ {nome_ia.upper()}: {type(e).__name__}: {e}")

    def _status_ft(self):
        """Mostra status dos 3 orquestradores via método proxy do Coração."""
        if self.coracao and hasattr(self.coracao, "status_finetuning"):
            try:
                self._show_result(self.coracao.status_finetuning())
            except Exception as e:
                self._handle_error("Erro em status_finetuning", e)
            return
        # Fallback manual
        status = {
            "orquestrador_arca":          type(self.orch_arca).__name__    if self.orch_arca else "❌ None",
            "orquestrador_universal":     type(self.orch_univ).__name__    if self.orch_univ else "❌ None",
            "orquestrador_com_conversor": type(self.orch_conv).__name__    if self.orch_conv else "❌ None",
        }
        if self.orch_arca and hasattr(self.orch_arca, "registro"):
            status["registro_arca"] = self.orch_arca.registro
        if self.orch_univ and hasattr(self.orch_univ, "ias"):
            status["ias_universal"] = list(self.orch_univ.ias.keys())
        self._show_result(status)

    def _detectar_ias(self):
        """Força re-detecção de IAs no OrquestradorUniversal."""
        if self.coracao and hasattr(self.coracao, "detectar_novas_ias_finetuning"):
            try:
                qtd = self.coracao.detectar_novas_ias_finetuning()
                self._show_result({"ias_detectadas": qtd})
            except Exception as e:
                self._handle_error("Erro em detectar_novas_ias_finetuning", e)
            return
        if self.orch_univ and hasattr(self.orch_univ, "_detectar_ias"):
            try:
                self.orch_univ.ias = self.orch_univ._detectar_ias()
                self._show_result({"ias_detectadas": len(self.orch_univ.ias), "lista": list(self.orch_univ.ias.keys())})
            except Exception as e:
                self._handle_error("Erro ao detectar IAs no orquestrador_universal", e)
        else:
            self._modulo_indisponivel("orquestrador_universal._detectar_ias")

    def _registro_arca(self):
        """Exibe o registro de versões do OrquestradorArca."""
        if self.orch_arca and hasattr(self.orch_arca, "registro"):
            self._show_result(self.orch_arca.registro)
        elif self.orch_arca:
            self._show_result({"tipo": type(self.orch_arca).__name__, "ias": list(getattr(self.orch_arca, "ias", {}).keys())})
        else:
            self._modulo_indisponivel("orquestrador_arca.registro")

    def _ias_universal(self):
        """Lista IAs detectadas pelo OrquestradorUniversal."""
        if self.orch_univ and hasattr(self.orch_univ, "ias"):
            ias = self.orch_univ.ias
            resultado = {}
            for nome, info in ias.items():
                resultado[nome] = {
                    "dataset_ok":       info.get("dataset", "").exists() if hasattr(info.get("dataset"), "exists") else "N/D",
                    "modelo_orig_ok":   info.get("modelo_original", "").exists() if hasattr(info.get("modelo_original"), "exists") else "N/D",
                    "gguf_ok":          info.get("modelo_gguf", "").exists() if hasattr(info.get("modelo_gguf"), "exists") else "N/D",
                }
            self._show_result(resultado)
        else:
            self._modulo_indisponivel("orquestrador_universal.ias")

    def _ver_dataset(self):
        """Analisa a estrutura do dataset informado (via DetectorUniversal)."""
        caminho = self.e_dataset.get().strip()
        if not caminho:
            self._handle_error("Informe o caminho do dataset antes de continuar.")
            return
        from pathlib import Path as _Path
        p = _Path(caminho)
        if not p.exists():
            self._handle_error(f"Arquivo não encontrado: {caminho}")
            return
        # Tenta usar DetectorUniversal do OrquestradorUniversal
        try:
            from src.core.orquestrador_universal import DetectorUniversal
            estrutura = DetectorUniversal.analisar_dataset(p)
            self._show_result(estrutura)
        except ImportError:
            # Fallback simples
            try:
                import json as _json
                with open(p, "r", encoding="utf-8") as f:
                    linhas = f.readlines()
                amostra = []
                for linha in linhas[:3]:
                    try: amostra.append(_json.loads(linha))
                    except Exception: amostra.append(linha.strip())
                self._show_result({
                    "total_linhas": len(linhas),
                    "extensao": p.suffix,
                    "amostra_3_primeiras": amostra,
                })
            except Exception as e:
                self._handle_error("Erro ao ler dataset", e)
        except Exception as e:
            self._handle_error("Erro ao analisar dataset", e)

    def refresh(self):
        """Atualiza status dos orquestradores a cada ciclo periódico."""
        try:
            ok_a = "✅" if getattr(self.coracao, "orquestrador_arca",         None) else "❌"
            ok_u = "✅" if getattr(self.coracao, "orquestrador_universal",    None) else "❌"
            ok_c = "✅" if getattr(self.coracao, "orquestrador_com_conversor",None) else "❌"
            # Atualiza orch_arca/univ/conv caso tenham sido inicializados depois da abertura do painel
            self.orch_arca = getattr(self.coracao, "orquestrador_arca",         None) if self.coracao else None
            self.orch_univ = getattr(self.coracao, "orquestrador_universal",    None) if self.coracao else None
            self.orch_conv = getattr(self.coracao, "orquestrador_com_conversor",None) if self.coracao else None
        except Exception:
            pass


# --------------------------------------------------------------------
#  JANELA PRINCIPAL — Desktop + Menu + Roteamento de Painéis
# --------------------------------------------------------------------

class JanelaPrincipalArca(ctk.CTk):
    def __init__(self, command_queue: queue.Queue, response_queue: queue.Queue,
                 coracao_ref=None, stop_event=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command_queue = command_queue
        self.response_queue = response_queue
        self.coracao = coracao_ref
        self.stop_event = stop_event or threading.Event()
        self._response_thread: Optional[threading.Thread] = None
        self._response_thread_stop = threading.Event()
        self._periodic_after_id = None
        self.paineis: Dict[str, PainelBase] = {}
        self.app_ativo: Optional[str] = None
        self.menu_iniciar = None
        self._init_ui()
        self._start_response_thread()
        try: self._periodic_after_id = self.after(1000, self._periodic_refresh)
        except Exception: pass

    def _init_ui(self):
        self.title("🚀 Arca Celestial — Genesis Alfa Omega")
        self.geometry("1280x800+30+30")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.desktop_frame = ctk.CTkFrame(self)
        self.desktop_frame.pack(fill="both", expand=True)
        self.paineis["desktop"] = PainelDesktop(self.desktop_frame, self.coracao, self)
        self._mostrar_desktop()

    def _mostrar_desktop(self):
        for nome, painel in list(self.paineis.items()):
            if nome != "desktop":
                try: painel.hide()
                except Exception: pass
        try: self.paineis["desktop"].show()
        except Exception: pass
        self.app_ativo = None

    def _entrar_no_app(self, app_name: str):
        try:
            if self.menu_iniciar and getattr(self.menu_iniciar, "winfo_exists", lambda: False)():
                try: self.menu_iniciar.destroy()
                except Exception: pass
            self.menu_iniciar = None
        except Exception: pass
        try:
            if self.app_ativo and self.app_ativo != app_name:
                try: self.paineis[self.app_ativo].hide()
                except Exception: pass
            if app_name not in self.paineis:
                self._inicializar_painel(app_name)
            try: self.paineis["desktop"].hide()
            except Exception: pass
            try: self.paineis[app_name].show()
            except Exception: pass
            self.app_ativo = app_name
        except Exception as e:
            logger.exception("Erro _entrar_no_app %s: %s", app_name, e)

    def _abrir_menu_iniciar(self):
        if self.menu_iniciar and getattr(self.menu_iniciar, "winfo_exists", lambda: False)():
            try: self.menu_iniciar.focus_force()
            except Exception: pass
            return
        self.menu_iniciar = ctk.CTkToplevel(self)
        self.menu_iniciar.title("🚀 Arca — Menu de Aplicativos")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        mw, mh = 640, 760
        self.menu_iniciar.geometry(f"{mw}x{mh}+{(sw-mw)//2}+{(sh-mh)//2}")
        try: self.menu_iniciar.focus_force(); self.menu_iniciar.grab_set()
        except Exception: pass

        ctk.CTkLabel(self.menu_iniciar, text="🚀  Aplicativos da Arca",
            font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)
        sf = ctk.CTkScrollableFrame(self.menu_iniciar)
        sf.pack(fill="both", expand=True, padx=10, pady=8)

        categorias = {
            "💬 Comunicação": [
                ("💬 Chat Individual", "chat_individual"),
                ("💬 Chat Coletivo", "chat_coletivo"),
            ],
            "📹 Multimídia": [
                ("📹 Câmera/Som/Microfones", "camera_som"),
                ("🎤 Transcrever Áudio", "transcrever_audio"),
            ],
            "❤️ Emoções & Alma": [
                ("❤️ Sentimentos", "sentimentos"),
                ("🌙 Sonhos", "sonhos"),
                ("📈 Crescimento Personalidade", "crescimento_personalidade"),
                ("💡 Decisões & Iniciativa", "decisoes"),
            ],
            "🏛️ Governo & Direito": [
                ("🏛️ Consulado Soberano", "consulado"),
                ("📜 Legislativo (Leis)", "legislativo"),
                ("⚖️ Judiciário Completo", "judiciario"),
                ("🔒 Modo Vidro", "modo_vidro"),
                ("📢 Apelos ao Criador", "apelos_criador"),
                ("🔍 Precedentes", "sistema_precedentes"),
            ],
            "🛡️ Segurança": [
                ("🛡️ Segurança & Sandbox", "seguranca"),
            ],
            "🔧 Engenharia": [
                ("🔧 Engenharia & Propostas", "engenharia"),
                ("📋 Gerenciador Propostas", "gerenciador_propostas"),
                ("📈 Lista Evolução IA", "lista_evolucao_ia"),
                ("📊 Analisador Intenção", "analisador_intencao"),
                ("👼 Gerador Almas", "gerador_almas"),
                ("🤝 Aliadas (APIs Ext.)", "aliadas"),
            ],
            "🤖 Finetuning": [
                ("🤖 Finetuning das IAs (3 Orquestradores)", "finetuning"),
            ],
            "📊 Memória & Sistema": [
                ("📊 Memória (4 Camadas)", "memoria"),
                ("💽 Detector HDD/Hardware", "detector_hdd"),
                ("🔍 Scanner Sistema", "scanner_sistema"),
                ("👁️ Monitoramento & Obs.", "monitoramento"),
                ("📋 Auditoria & Histórico", "auditoria"),
                ("✅ Validadores", "validadores"),
            ],
            "🚀 API & Integração": [
                ("🚀 Encarnação API (FastAPI)", "encarnacao_api"),
                ("🌐 Automatizador Navegador", "automatizador_navegador"),
            ],
            "👁️ Almas": [
                ("👁️ Almas Vivas", "almas_vivas"),
            ],
            "📚 Conhecimento": [
                ("📚 Biblioteca", "biblioteca"),
                ("🕊️ Capela", "capela"),
            ],
        }
        for cat, apps in categorias.items():
            ctk.CTkLabel(sf, text=cat, font=ctk.CTkFont(size=13, weight="bold"), text_color="#aaccff").pack(pady=(10, 2))
            for label, key in apps:
                ctk.CTkButton(sf, text=label, command=lambda k=key: self._entrar_no_app(k),
                    height=38, font=ctk.CTkFont(size=12), anchor="w").pack(fill="x", padx=4, pady=1)

    # --------------------------------------------------------------------
    # Mapa de roteamento de painéis
    # --------------------------------------------------------------------

    _MAPA_PAINEIS = {
        "chat_individual":        PainelChatIndividual,
        "chat_coletivo":          PainelChatColetivo,
        "camera_som":             PainelCameraSom,
        "transcrever_audio":      PainelTranscreverAudio,
        "sentimentos":            PainelSentimentos,
        "sonhos":                 PainelSonhos,
        "crescimento_personalidade": PainelCrescimentoPersonalidade,
        "decisoes":               PainelDecisoes,
        "consulado":              PainelConsulado,
        "legislativo":            PainelLegislativo,
        "judiciario":             PainelJudiciario,
        "modo_vidro":             PainelModoVidro,
        "apelos_criador":         PainelApelosCriador,
        "sistema_precedentes":    PainelPrecedentes,
        "seguranca":              PainelSeguranca,
        "engenharia":             PainelEngenharia,
        "gerenciador_propostas":  PainelGerenciadorPropostas,
        "lista_evolucao_ia":      PainelListaEvolucaoIA,
        "analisador_intencao":    PainelAnalisadorIntencao,
        "gerador_almas":          PainelGeradorAlmas,
        "aliadas":                PainelAliadas,
        "finetuning":             PainelFinetuning,
        "memoria":                PainelMemoria,
        "detector_hdd":           PainelDetectorHDD,
        "scanner_sistema":        PainelScannerSistema,
        "monitoramento":          PainelMonitoramento,
        "auditoria":              PainelAuditoriaHistorico,
        "validadores":            PainelValidadores,
        "encarnacao_api":         PainelEncarnacaoAPI,
        "automatizador_navegador": PainelAutomatizadorNavegador,
        "almas_vivas":            PainelAlmasVivas,
        "biblioteca":             PainelBiblioteca,
        "capela":                 PainelCapela,
    }

    def _inicializar_painel(self, nome: str):
        cls = self._MAPA_PAINEIS.get(nome)
        if cls:
            try:
                self.paineis[nome] = cls(self.desktop_frame, self.coracao, self)
                return
            except Exception as e:
                logger.exception("Erro construindo painel '%s': %s", nome, e)
                self.paineis[nome] = PainelBase(self.desktop_frame, self.coracao, self)
                try: ctk.CTkLabel(self.paineis[nome].frame, text=f"❌ Erro ao iniciar painel '{nome}'\n{type(e).__name__}: {e}", wraplength=600).pack(pady=40)
                except Exception: pass
                return
        # Painel desconhecido
        self.paineis[nome] = PainelBase(self.desktop_frame, self.coracao, self)
        try: ctk.CTkLabel(self.paineis[nome].frame, text=f"Painel '{nome}' — Não mapeado na interface.").pack(pady=40)
        except Exception: pass

    # --------------------------------------------------------------------
    # Thread de respostas da fila (CORRIGIDA)
    # --------------------------------------------------------------------

    def _start_response_thread(self):
        if self._response_thread and self._response_thread.is_alive(): return
        self._response_thread_stop.clear()
        self._response_thread = threading.Thread(target=self._loop_respostas, name="UIResponseThread", daemon=True)
        self._response_thread.start()

    def _loop_respostas(self):
        """Loop que processa respostas da fila com proteção contra atributos incorretos"""
        while not self._response_thread_stop.is_set():
            try:
                # VERIFICAÇÍO CRÍTICA: garantir que response_queue é uma fila válida
                if not hasattr(self, 'response_queue') or self.response_queue is None:
                    logger.error("response_queue não disponível no loop de respostas")
                    time.sleep(1.0)
                    continue
                
                # Verificar se é uma fila válida (tem método get)
                if not hasattr(self.response_queue, 'get'):
                    logger.error(f"response_queue não é uma fila válida: {type(self.response_queue)}")
                    time.sleep(1.0)
                    continue
                
                try:
                    dados = self.response_queue.get(timeout=1.0)
                    try:
                        if getattr(self, "winfo_exists", lambda: False)():
                            self.after(0, lambda d=dados: self._handle_response(d))
                        else:
                            self._handle_response(dados)
                    except Exception as e:
                        logger.exception(f"Erro ao processar resposta: {e}")
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.exception(f"Erro no loop de respostas: {e}")
                    time.sleep(1.0)
            except Exception as e:
                logger.exception(f"Erro fatal no loop de respostas: {e}")
                time.sleep(1.0)

    def _handle_response(self, dados: Dict[str, Any]):
        try:
            tipo = dados.get("tipo_resp", "")
            alma = dados.get("alma") or dados.get("nome_filha", "")
            texto = dados.get("texto") or dados.get("resposta") or dados.get("conteudo", "")
            # Injeta no painel de chat individual
            if "chat_individual" in self.paineis:
                p = self.paineis["chat_individual"]
                if hasattr(p, "inject_response") and alma and texto:
                    try: p.inject_response(alma, str(texto))
                    except Exception: pass
            # Injeta no painel de chat coletivo
            if "chat_coletivo" in self.paineis:
                p = self.paineis["chat_coletivo"]
                if hasattr(p, "inject_response") and alma and texto:
                    try: p.inject_response(alma, str(texto))
                    except Exception: pass
            if tipo: logger.debug("Resposta recebida: tipo=%s alma=%s", tipo, alma)
        except Exception as e:
            logger.warning("Erro _handle_response: %s", e)

    # --------------------------------------------------------------------
    # Refresh periódico
    # --------------------------------------------------------------------

    def _periodic_refresh(self):
        for p in list(self.paineis.values()):
            if hasattr(p, "refresh"):
                try: p.refresh()
                except Exception: pass
        if not self.stop_event.is_set():
            try: self._periodic_after_id = self.after(5000, self._periodic_refresh)
            except Exception: pass

    # --------------------------------------------------------------------
    # Shutdown limpo
    # --------------------------------------------------------------------

    def shutdown(self):
        try: self.stop_event.set()
        except Exception: pass
        try: self._response_thread_stop.set()
        except Exception: pass
        try:
            if self._periodic_after_id:
                self.after_cancel(self._periodic_after_id)
        except Exception: pass
        try:
            if self._response_thread and self._response_thread.is_alive():
                self._response_thread.join(timeout=3.0)
        except Exception: pass
        try: self.destroy()
        except Exception: pass


# --------------------------------------------------------------------
#  PONTO DE ENTRADA
# --------------------------------------------------------------------

if __name__ == "__main__":
    import threading
    from queue import Queue

    command_queue = Queue()
    response_queue = Queue()
    stop_event = threading.Event()

    coracao = None
    try:
        from coracao_orquestrador import CoracaoOrquestrador
        from config import get_config
        config = get_config()
        coracao = CoracaoOrquestrador(
            ui_queue=response_queue,
            llm_engine_ref=None,
            config_instance=config,
        )
        print("✅ CoracaoOrquestrador carregado com sucesso.")
    except ImportError as e:
        print(f"⚠️  Módulos do projeto não encontrados: {e}")
        print("    A interface abrirá sem conexão ao Coração.")
        print("    Cada painel mostrará o módulo exato que está faltando.")
    except Exception as e:
        print(f"❌ CoracaoOrquestrador falhou ao instanciar: {type(e).__name__}: {e}")
        print("    Verifique os logs para detalhes completos.")
        import traceback
        traceback.print_exc()

    app = JanelaPrincipalArca(command_queue, response_queue, coracao, stop_event)
    app.mainloop()


# --------------------------------------------------------------------
#  FUNÇÍO DE ENTRADA USADA PELO main.py
# --------------------------------------------------------------------
def criar_interface(coracao_ref=None, ui_queue=None, job_manager=None):
    """
    Ponto de entrada chamado pelo main.py.
    Cria as filas, instancia JanelaPrincipalArca e retorna a janela.
    BUG #3 CORRIGIDO: ui_queue deve ser uma fila válida, job_manager é injetado separadamente.
    """
    import queue as _q
    import threading as _th
    command_queue  = _q.Queue()
    # Garantir que response_queue é sempre uma fila válida
    if ui_queue is not None and hasattr(ui_queue, 'get') and hasattr(ui_queue, 'put'):
        response_queue = ui_queue
    else:
        response_queue = _q.Queue()
    stop_event = _th.Event()
    janela = JanelaPrincipalArca(command_queue, response_queue, coracao_ref, stop_event)
    # Injetar job_manager na janela se fornecido
    if job_manager is not None:
        try:
            setattr(janela, "job_manager", job_manager)
        except Exception:
            pass
    return janela