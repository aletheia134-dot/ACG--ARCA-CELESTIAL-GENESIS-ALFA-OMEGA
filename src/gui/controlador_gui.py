#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ControladorGUI (enduricido)

Abstração segura para controle de mouse/teclado e screenshots, pensada para:
 - trabalhar em ambientes com/sem display (headless)
 - validar e limitar ações solicitadas pela GUI
 - auditar ações e persistir logs (opcional)
 - evitar combinações perigosas e impedir execução de ações críticas

Design decisions:
 - imports de pyautogui / PIL são feitos de forma lazy dentro de __init__ e métodos,
   para permitir import do módulo em ambientes sem GUI.
 - Se GUI não estiver disponível, os métodos devolvem False/None e logam aviso.
 - Apenas comandos simples são permitidos (ex.: press de uma única tecla).
 - Auditoria opcional pode ser ativada fornecendo um caminho no config (audit_log_path).
"""
from __future__ import annotations


import io
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

logger = logging.getLogger("ControladorGUI")
logger.addHandler(logging.NullHandler())


class GUIUnavailableError(RuntimeError):
    """Indica que APIs de controle GUI não estão disponíveis no runtime."""


class ControladorGUI:
    """
    Controlador seguro para automação de UI.Args:
        config_instance: objeto com método get(section, key, fallback=...) ou dict-like.Reconhece (opcional):
             - 'GUI.LIMITE_VELOCIDADE_MOUSE_PIXELS_POR_SEG'
             - 'GUI.LIMITE_VELOCIDADE_TECLADO_CARACTERES_POR_SEG'
             - 'GUI.TEMPO_MAXIMO_ACAO_GUI_SECS'
             - 'GUI.PAUSE_GUI_SEGUNDOS'
             - 'GUI.AREA_PERMITIDA_X_MIN/Y_MIN/X_MAX/Y_MAX'
             - 'GUI.AUDIT_LOG_PATH' (opcional) -> path para arquivo de log de auditoria
             - 'GUI.ALLOWLIST_KEYS' (opcional) -> list of allowed single keys
             - 'GUI.MAX_SCREENSHOT_PIXELS' (opcional) -> int, cap pixels (w*h) for screenshots
        lazy_import: if True, imports GUI libs only when needed (default True).
    """

    DEFAULT_MOUSE_SPEED_LIMIT = 5000.0  # px/s
    DEFAULT_KEYBOARD_SPEED_LIMIT = 100.0  # chars/s
    DEFAULT_ACTION_TIMEOUT = 30.0  # seconds
    DEFAULT_PAUSE = 0.1  # seconds between GUI actions
    DEFAULT_MAX_SCREENSHOT_PIXELS = 3840 * 2160  # ~8MP

    SAFE_KEY_ALLOWLIST = {
        "enter", "tab", "space", "backspace", "delete", "shift", "ctrl", "alt",
        "up", "down", "left", "right", "pageup", "pagedown", "home", "end",
        "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
        # letters and digits are allowed
    } | set(list("abcdefghijklmnopqrstuvwxyz")) | set(str(i) for i in range(10))

    DANGEROUS_KEY_PATTERNS = [
        re.compile(r"alt\+f4", re.IGNORECASE),
        re.compile(r"win", re.IGNORECASE),
        re.compile(r"ctrl\+alt\+del", re.IGNORECASE),
    ]

    def __init__(self, config_instance: Optional[Any] = None, lazy_import: bool = True):
        self.config = config_instance or {}
        self._lock_gui = threading.RLock()
        self._last_mouse_time = 0.0
        self._last_mouse_pos: Optional[Tuple[int, int]] = None
        self._last_keyboard_time = 0.0
        self._last_click_time = 0.0
        self._audit_history: List[Dict[str, Any]] = []

        # read config defensively (supports configparser-like or dict)
        def _cfg_get(section_key: str, fallback):
            try:
                if hasattr(self.config, "get"):
                    # allow "GUI" and key or "GUI.KEY"
                    if isinstance(section_key, tuple):
                        section, key = section_key
                        return self.config.get(section, key, fallback=fallback)
                    return self.config.get(section_key, fallback=fallback)
                elif isinstance(self.config, dict):
                    return self.config.get(section_key, fallback)
            except Exception:
                pass
            return fallback

        # numeric configs
        self._limite_velocidade_mouse = float(_cfg_get(("GUI", "LIMITE_VELOCIDADE_MOUSE_PIXELS_POR_SEG"), self.DEFAULT_MOUSE_SPEED_LIMIT))
        self._limite_velocidade_teclado = float(_cfg_get(("GUI", "LIMITE_VELOCIDADE_TECLADO_CARACTERES_POR_SEG"), self.DEFAULT_KEYBOARD_SPEED_LIMIT))
        self._tempo_maximo_acao_gui = float(_cfg_get(("GUI", "TEMPO_MAXIMO_ACAO_GUI_SECS"), self.DEFAULT_ACTION_TIMEOUT))
        self._intervalo_paleta_seguranca = float(_cfg_get(("GUI", "PAUSE_GUI_SEGUNDOS"), self.DEFAULT_PAUSE))
        self._max_screenshot_pixels = int(_cfg_get(("GUI", "MAX_SCREENSHOT_PIXELS"), self.DEFAULT_MAX_SCREENSHOT_PIXELS))

        # area permitted (lazy evaluate screen size if GUI is available)
        self._area_permitida_x_min = int(_cfg_get(("GUI", "AREA_PERMITIDA_X_MIN"), 0))
        self._area_permitida_y_min = int(_cfg_get(("GUI", "AREA_PERMITIDA_Y_MIN"), 0))
        self._area_permitida_x_max = _cfg_get(("GUI", "AREA_PERMITIDA_X_MAX"), None)
        self._area_permitida_y_max = _cfg_get(("GUI", "AREA_PERMITIDA_Y_MAX"), None)

        # audit log path (optional)
        audit_path = _cfg_get(("GUI", "AUDIT_LOG_PATH"), None)
        self._audit_log_path: Optional[Path] = Path(audit_path) if audit_path else None
        if self._audit_log_path:
            try:
                self._audit_log_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                logger.exception("Falha ao criar pasta para audit log; auditoria em memória apenas.")
                self._audit_log_path = None

        # allowed keys custom (optional)
        allowed_keys_cfg = _cfg_get(("GUI", "ALLOWLIST_KEYS"), None)
        if isinstance(allowed_keys_cfg, (list, tuple, set)):
            self._allowed_keys = set(k.lower() for k in allowed_keys_cfg)
        else:
            self._allowed_keys = self.SAFE_KEY_ALLOWLIST.copy()

        # GUI libs (lazy import)
        self._pyautogui = None
        self._PIL_Image = None  # optional Pillow
        self._gui_available = False
        if not lazy_import:
            self._ensure_gui_imports()

        logger.info("ControladorGUI inicializado (gui_available=%s).", self._gui_available)

    # -------------------------
    # Lazy imports / availability
    # -------------------------
    def _ensure_gui_imports(self) -> None:
        """Tenta importar pyautogui e Pillow (opcional). Seta flag _gui_available."""
        if self._gui_available:
            return
        try:
            import pyautogui  # type: ignore
            # configure safely
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = max(0.0, float(self._intervalo_paleta_seguranca))
            self._pyautogui = pyautogui
            # try Pillow for resizing screenshots
            try:
                from PIL import Image  # type: ignore
                self._PIL_Image = Image
            except Exception:
                self._PIL_Image = None
            # determine screen area limits if not explicitly set
            try:
                w, h = pyautogui.size()
                if self._area_permitida_x_max is None:
                    self._area_permitida_x_max = w
                if self._area_permitida_y_max is None:
                    self._area_permitida_y_max = h
            except Exception:
                # keep as-is, may be headless
                pass
            self._gui_available = True
            logger.debug("pyautogui importado com sucesso; GUI disponível.")
        except Exception:
            self._pyautogui = None
            self._PIL_Image = None
            self._gui_available = False
            logger.warning("pyautogui não disponível ou environment sem display; ControladorGUI entra em modo degradado.")

    def is_gui_available(self) -> bool:
        """Retorna True se as APIs GUI estão disponíveis no ambiente."""
        if not self._gui_available:
            # attempt import on demand
            self._ensure_gui_imports()
        return bool(self._gui_available)

    # -------------------------
    # Helpers de validação
    # -------------------------
    def _validar_posicao_mouse(self, x: int, y: int) -> bool:
        try:
            xmin = int(self._area_permitida_x_min)
            ymin = int(self._area_permitida_y_min)
            xmax = int(self._area_permitida_x_max) if self._area_permitida_x_max is not None else None
            ymax = int(self._area_permitida_y_max) if self._area_permitida_y_max is not None else None
            if xmax is not None and ymax is not None:
                return xmin <= x <= xmax and ymin <= y <= ymax
            # if unknown screen bounds, accept non-negative coords
            return x >= xmin and y >= ymin
        except Exception:
            return False

    def _validar_velocidade_mouse(self, x: int, y: int) -> bool:
        """Evita movimentos de mouse com velocidade acima do limite."""
        if not self.is_gui_available():
            return False
        now = time.time()
        # initial position
        try:
            current_pos = self._pyautogui.position()
            curr_x, curr_y = int(current_pos.x), int(current_pos.y)
        except Exception:
            # if we cannot query current position, allow movement but update state
            curr_x, curr_y = x, y

        if self._last_mouse_time <= 0.0 or self._last_mouse_pos is None:
            # initialize baseline
            self._last_mouse_time = now
            self._last_mouse_pos = (curr_x, curr_y)
            return True

        delta_t = max(1e-3, now - self._last_mouse_time)
        dx = x - self._last_mouse_pos[0]
        dy = y - self._last_mouse_pos[1]
        distancia = (dx * dx + dy * dy) ** 0.5
        velocidade = distancia / delta_t
        if velocidade > self._limite_velocidade_mouse:
            logger.warning("Movimento de mouse bloqueado por velocidade: %.1f px/s (limite %.1f)", velocidade, self._limite_velocidade_mouse)
            return False

        # update baseline
        self._last_mouse_time = now
        self._last_mouse_pos = (x, y)
        return True

    def _validar_velocidade_teclado(self, texto: str) -> bool:
        """Evita digitação em velocidade superior ao limite."""
        now = time.time()
        delta_t = max(1e-3, now - self._last_keyboard_time) if self._last_keyboard_time else None
        if delta_t is None or delta_t <= 0.0:
            self._last_keyboard_time = now
            return True
        velocidade = len(texto) / delta_t
        if velocidade > self._limite_velocidade_teclado:
            logger.warning("Digitação bloqueada por velocidade: %.1f chars/s (limite %.1f)", velocidade, self._limite_velocidade_teclado)
            return False
        self._last_keyboard_time = now
        return True

    def _registrar_acao(self, tipo_acao: str, detalhes: Dict[str, Any]) -> None:
        """Registra ação localmente e opcionalmente em arquivo de auditoria (append)."""
        entry = {"timestamp": time.time(), "tipo_acao": tipo_acao, "detalhes": detalhes}
        with self._lock_gui:
            self._audit_history.append(entry)
            if len(self._audit_history) > 2000:
                # keep recent window
                self._audit_history = self._audit_history[-1000:]
        # append to file if configured
        if self._audit_log_path:
            try:
                s = json.dumps(entry, ensure_ascii=False)
                # atomic append is tricky; open in append mode
                with open(self._audit_log_path, "a", encoding="utf-8") as f:
                    f.write(s + "\n")
            except Exception:
                logger.exception("Falha ao persistir audit log (ignorado)")

    # -------------------------
    # Actions (public)
    # -------------------------
    def mover_mouse_para(self, x: int, y: int, duracao: float = 0.5) -> bool:
        """
        Move o mouse para (x,y). Retorna True se OK, False se ação bloqueada ou GUI indisponível.
        """
        if not self.is_gui_available():
            logger.warning("Mover mouse solicitado mas GUI não disponível.")
            return False
        with self._lock_gui:
            if not isinstance(x, int) or not isinstance(y, int):
                logger.warning("Coordenadas inválidas para mover_mouse_para")
                return False
            if not self._validar_posicao_mouse(x, y):
                logger.warning("Posição fora da área permitida: (%s,%s)", x, y)
                return False
            if not self._validar_velocidade_mouse(x, y):
                return False
            # enforce maximum duration
            duracao = max(0.0, min(float(duracao), float(self._tempo_maximo_acao_gui)))
            try:
                self._pyautogui.moveTo(x, y, duration=duracao)
                self._registrar_acao("MOVER_MOUSE", {"x": x, "y": y, "duracao": duracao})
                time.sleep(self._intervalo_paleta_seguranca)
                return True
            except self._pyautogui.FailSafeException:  # type: ignore
                logger.critical("Fail-safe ativado; ação abortada.")
                return False
            except Exception:
                logger.exception("Erro ao mover mouse para (%s,%s)", x, y)
                return False

    def clicar_em(self, x: int, y: int, botao: str = "left", duracao_movimento: float = 0.2) -> bool:
        """
        Move e clica em (x,y). Valida posição, velocidade e evita spam de cliques.
        """
        if not self.is_gui_available():
            logger.warning("Clicar solicitado mas GUI não disponível.")
            return False
        with self._lock_gui:
            now = time.time()
            if now - self._last_click_time < 0.05:
                logger.warning("Clique bloqueado: muito rápido entre cliques.")
                return False
            # move then click; mover_mouse_para will re-check safety
            if not self.mover_mouse_para(x, y, duracao=duracao_movimento):
                return False
            try:
                self._pyautogui.click(x=x, y=y, button=botao)  # type: ignore
                self._last_click_time = now
                self._registrar_acao("CLICAR", {"x": x, "y": y, "botao": botao})
                time.sleep(self._intervalo_paleta_seguranca)
                return True
            except self._pyautogui.FailSafeException:  # type: ignore
                logger.critical("Fail-safe ativado durante clique; abortando.")
                return False
            except Exception:
                logger.exception("Erro ao clicar em (%s,%s)", x, y)
                return False

    def digitar_texto(self, texto: str, intervalo_entre_caracteres: float = 0.05) -> bool:
        """Digita texto com velocidade limitada."""
        if not self.is_gui_available():
            logger.warning("Digitar texto solicitado mas GUI não disponível.")
            return False
        if not isinstance(texto, str) or texto == "":
            logger.warning("digitar_texto chamado com texto inválido.")
            return False
        with self._lock_gui:
            if not self._validar_velocidade_teclado(texto):
                return False
            intervalo = max(0.0, float(intervalo_entre_caracteres))
            intervalo = min(intervalo, 1.0)
            try:
                self._pyautogui.typewrite(texto, interval=intervalo)  # type: ignore
                self._registrar_acao("DIGITAR_TEXTO", {"len": len(texto), "interval": intervalo})
                time.sleep(self._intervalo_paleta_seguranca)
                return True
            except self._pyautogui.FailSafeException:  # type: ignore
                logger.critical("Fail-safe ativado durante digitacao; abortando.")
                return False
            except Exception:
                logger.exception("Erro ao digitar texto")
                return False

    def pressionar_tecla(self, tecla: str) -> bool:
        """
        Pressiona uma única tecla permitida.Não permite combinações (hotkeys) aqui.
        """
        if not self.is_gui_available():
            logger.warning("Pressionar tecla solicitado mas GUI não disponível.")
            return False
        if not isinstance(tecla, str) or tecla.strip() == "":
            logger.warning("Tecla inválida solicitada.")
            return False
        tecla_norm = tecla.lower().strip()

        # block dangerous patterns
        for patt in self.DANGEROUS_KEY_PATTERNS:
            if patt.search(tecla_norm):
                logger.warning("Tecla proibida por padrão de segurança: %s", tecla)
                return False

        if "+" in tecla_norm or " " in tecla_norm:
            # do not allow hotkey combos via this method
            logger.warning("Combinações de teclas não permitidas por pressionar_tecla: %s", tecla)
            return False

        if tecla_norm not in self._allowed_keys:
            logger.warning("Tecla não permitida: %s", tecla)
            return False

        with self._lock_gui:
            try:
                self._pyautogui.press(tecla_norm)  # type: ignore
                self._registrar_acao("PRESSIONAR_TECLA", {"tecla": tecla_norm})
                time.sleep(self._intervalo_paleta_seguranca)
                return True
            except self._pyautogui.FailSafeException:  # type: ignore
                logger.critical("Fail-safe ativado durante pressionar_tecla; abortando.")
                return False
            except Exception:
                logger.exception("Erro ao pressionar tecla %s", tecla_norm)
                return False

    def obter_posicao_mouse(self) -> Optional[Tuple[int, int]]:
        """Retorna posição do mouse ou None se indisponível."""
        if not self.is_gui_available():
            logger.debug("Solicitação de posição do mouse mas GUI indisponível.")
            return None
        try:
            pos = self._pyautogui.position()  # type: ignore
            return int(pos.x), int(pos.y)
        except Exception:
            logger.exception("Erro ao obter posicao do mouse")
            return None

    def obter_tamanho_tela(self) -> Optional[Tuple[int, int]]:
        """Retorna tamanho da tela ou None se indisponível."""
        if not self.is_gui_available():
            return None
        try:
            size = self._pyautogui.size()  # type: ignore
            return int(size.width), int(size.height)
        except Exception:
            logger.exception("Erro ao obter tamanho de tela")
            return None

    def obter_screenshot(self, caminho_saida: Optional[Path] = None, regiao: Optional[Tuple[int, int, int, int]] = None, max_pixels: Optional[int] = None) -> Optional[bytes]:
        """
        Captura screenshot; salva em caminho_saida (se informado) de forma segura (path relativa dentro audit dir ou temp).
        Retorna bytes PNG ou None em erro.
        """
        if not self.is_gui_available():
            logger.warning("Solicitação de screenshot mas GUI não disponível.")
            return None
        with self._lock_gui:
            try:
                img = self._pyautogui.screenshot(region=regiao)  # type: ignore
                # optional resize if too big (use Pillow if available)
                max_pixels = int(max_pixels or self._max_screenshot_pixels)
                try:
                    w, h = img.size
                    if w * h > max_pixels and self._PIL_Image is not None:
                        # resize proportionally
                        ratio = (max_pixels / (w * h)) ** 0.5
                        new_w = max(1, int(w * ratio))
                        new_h = max(1, int(h * ratio))
                        img.thumbnail((new_w, new_h))
                except Exception:
                    logger.debug("Falha ao avaliar/ajustar tamanho da screenshot (continuando).")

                # save optionally to path (safe path check)
                if caminho_saida:
                    try:
                        # only allow saving under audit log directory or same dir as configured, else reject
                        if self._audit_log_path:
                            allowed_base = self._audit_log_path.parent.resolve()
                        else:
                            allowed_base = Path.cwd().resolve()
                        target = Path(caminho_saida).resolve()
                        if allowed_base not in target.parents and allowed_base != target.parent:
                            logger.warning("Caminho de screenshot não permitido: %s", caminho_saida)
                            caminho_saida = None
                        else:
                            target.parent.mkdir(parents=True, exist_ok=True)
                            img.save(str(target))
                            logger.debug("Screenshot salvo em %s", target)
                    except Exception:
                        logger.exception("Falha ao salvar screenshot em disco; ignorando save.")

                # convert to PNG bytes
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                data = buf.getvalue()
                self._registrar_acao("SCREENSHOT", {"region": regiao, "bytes_len": len(data)})
                return data
            except Exception:
                logger.exception("Erro ao capturar screenshot")
                return None

    # -------------------------
    # Auditoria / Histórico
    # -------------------------
    def obter_historico_acoes_gui(self) -> List[Dict[str, Any]]:
        """Retorna cópia do histórico de auditoria em memória."""
        with self._lock_gui:
            return list(self._audit_history)

    def limpar_historico_acoes_gui(self) -> None:
        """Limpa histórico de auditoria (memória e arquivo se configurado)."""
        with self._lock_gui:
            self._audit_history.clear()
        if self._audit_log_path:
            try:
                # truncate file
                open(self._audit_log_path, "w", encoding="utf-8").close()
            except Exception:
                logger.exception("Falha ao truncar audit log file")

    # -------------------------
    # Utilities para testes e administração
    # -------------------------
    def allow_gui_actions_for_tests(self) -> None:
        """
        For testing only: forces import of GUI libs if available in environment.
        """
        self._ensure_gui_imports()

    def shutdown(self) -> None:
        """Cleanup hooks (currently noop)."""
        logger.debug("ControladorGUI shutdown called.")


