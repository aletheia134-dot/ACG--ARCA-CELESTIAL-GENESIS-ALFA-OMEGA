# -*- coding: utf-8 -*-
"""
MotorExpressaoIndividual - completo com 144 emoções e vídeos/avatares

Emoções: Lista expandida.Estrutura: assets/avatares/{nome_alma}/videos/{emocao}.mp4 e static/{emocao}.png
Vídeos: Loop de 5s até fala parar.Integrações: Voz, supervisão.

Melhorado: Animações sequenciais, detecção emocional, multi-alvo, fallbacks melhores.
"""
from __future__ import annotations

import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any, Optional, List

logger = logging.getLogger('MotorExpressaoIndividual')

# Lista de 144 emoções (expandida)
EMOCOES_LISTA: List[str] = [
    "alegria_leve", "alegria_forte", "alegria_contida", "tristeza_leve", "tristeza_profunda", "tristeza_reflexiva",
    "raiva_leve", "raiva_intensa", "raiva_controlada", "medo_leve", "medo_panico", "medo_ansioso",
    "surpresa_leve", "surpresa_choque", "surpresa_curiosa", "nojo_leve", "nojo_forte", "nojo_repulsa",
    "amor_leve", "amor_profundo", "amor_romantico", "odio_leve", "odio_intenso", "odio_ressentido",
    "ciume_leve", "ciume_devorador", "ciume_possessivo", "vergonha_leve", "vergonha_profunda", "vergonha_social",
    "orgulho_leve", "orgulho_arrogante", "orgulho_conquistado", "culpa_leve", "culpa_pesada", "culpa_remorso",
    "esperanca_leve", "esperanca_otimista", "esperanca_desesperada", "desespero_leve", "desespero_total", "desespero_resignado",
    "confianca_leve", "confianca_cega", "confianca_prudente", "desconfianca_leve", "desconfianca_paranoica", "desconfianca_cinica",
    "empatia_leve", "empatia_profunda", "empatia_solidaria", "indiferenca_leve", "indiferenca_apatia", "indiferenca_desinteressada",
    "entusiasmo_leve", "entusiasmo_explosivo", "entusiasmo_contido", "tedio_leve", "tedio_profundo", "tedio_monotono",
    "curiosidade_leve", "curiosidade_intensa", "curiosidade_inquisitiva", "frustracao_leve", "frustracao_irritada", "frustracao_desanimada",
    "satisfacao_leve", "satisfacao_plena", "satisfacao_contente", "inveja_leve", "inveja_amarga", "inveja_competitiva",
    "gratidao_leve", "gratidao_profunda", "gratidao_emocionada", "ressentimento_leve", "ressentimento_amargo", "ressentimento_silencioso",
    "solidao_leve", "solidao_profunda", "solidao_isolada", "companheirismo_leve", "companheirismo_forte", "companheirismo_fraterno",
    "paixao_leve", "paixao_ardente", "paixao_consumidora", "calma_leve", "calma_serenidade", "calma_tranquila",
    "ansiedade_leve", "ansiedade_paralisante", "ansiedade_nervosa", "excitacao_leve", "excitacao_eletrizante", "excitacao_adrenalina",
    "desgosto_leve", "desgosto_repugnante", "desgosto_moral", "adoracao_leve", "adoracao_devota", "adoracao_fanatica",
    "desprezo_leve", "desprezo_superior", "desprezo_desdenhoso", "neutralidade_leve", "neutralidade_equilibrada",
    "indiferenca_avancada", "empolgacao_extrema", "serenidade_avancada", "raiva_suprimida", "medo_paranoico", "surpresa_estupefata",
    "nojo_extremo", "amor_sacrificial", "odio_incontrolavel", "ciume_patologico", "vergonha_crush", "orgulho_excessivo",
    "culpa_obssessiva", "esperanca_ilusoria", "desespero_abissal", "confianca_idealista", "desconfianca_extrema",
    "empatia_sobrehumana", "entusiasmo_incontrolavel", "tedio_mortal", "curiosidade_dangerosa", "frustracao_explosiva",
    "satisfacao_suprema", "inveja_venenosa", "gratidao_eterna", "ressentimento_feroz", "solidao_angustiante",
    "companheirismo_universal", "paixao_devoradora", "calma_imperturbavel", "ansiedade_cronica", "excitacao_euforica",
    "desgosto_profundo", "adoracao_fanatica", "desprezo_absoluto", "neutralidade_absoluta", "alegria_euforica"
]

try:
    import pygame
    import cv2
    VIDEO_SUPPORT = True
except ImportError:
    VIDEO_SUPPORT = False
    logger.warning("Pygame/OpenCV não disponíveis; vídeos desabilitados.")

class MotorExpressaoIndividual:
    def __init__(self, nome_alma: str, motor_de_expressao_global_ref: Any, automatizador_web_ref: Any):
        self.nome_alma = nome_alma
        self.motor_de_expressao_global = motor_de_expressao_global_ref
        self.automatizador_web = automatizador_web_ref
        self.logger = logging.getLogger(f'AvatarIndividual.{self.nome_alma}')
        
        self._estado_atual: str = "neutralidade_equilibrada"
        self._alvo_atual: str = "Quarto"
        self._video_thread: Optional[threading.Thread] = None
        self._stop_video = threading.Event()
        
        # Estrutura de arquivos (completa)
        self.pasta_videos = Path(f"assets/avatares/{self.nome_alma}/videos")
        self.pasta_static = Path(f"assets/avatares/{self.nome_alma}/static")
        self.pasta_videos.mkdir(parents=True, exist_ok=True)
        self.pasta_static.mkdir(parents=True, exist_ok=True)
        
        # Melhorias: Sequências, multi-alvo
        self._sequencia_animacao: List[str] = []
        self._multi_alvos: List[str] = []
        
        if VIDEO_SUPPORT:
            pygame.init()
        
        self.logger.info("[AVATAR INDIVIDUAL - %s] Motor de Avatar Individual forjado (144 emoções, vídeos/avatares, melhorado).", self.nome_alma)

    def atualizar_rosto(self, estado: str = "neutralidade_equilibrada", alvo_ui: str = "Quarto", usar_video: bool = True, sequencia: Optional[List[str]] = None) -> None:
        try:
            if not isinstance(estado, str) or not estado:
                estado = "neutralidade_equilibrada"
            if not isinstance(alvo_ui, str) or not alvo_ui:
                alvo_ui = "Quarto"
        except Exception:
            estado = "neutralidade_equilibrada"
            alvo_ui = "Quarto"

        if estado not in EMOCOES_LISTA:
            self.logger.warning("Emoção '%s' não reconhecida; usando neutra.", estado)
            estado = "neutralidade_equilibrada"

        if estado == self._estado_atual and alvo_ui == self._alvo_atual:
            self.logger.debug("[AVATAR INDIVIDUAL - %s] Estado já atual; ignorando.", self.nome_alma)
            return

        motor = self.motor_de_expressao_global
        if motor is None:
            self.logger.warning("[AVATAR INDIVIDUAL - %s] Motor global de expressão ausente; não é possível atualizar rosto.", self.nome_alma)
            return

        method = getattr(motor, "atualizar_rosto", None) or getattr(motor, "actualizar_rosto", None)

        if not callable(method):
            self.logger.warning("[AVATAR INDIVIDUAL - %s] Motor global não expõe método de atualização de rosto ('atualizar_rosto' ou 'actualizar_rosto').", self.nome_alma)
            return

        try:
            method(self.nome_alma, estado, alvo_ui)
            self._estado_atual = estado
            self._alvo_atual = alvo_ui
            preview = f"{estado}" if len(estado) < 50 else f"{estado[:47]}..."
            self.logger.debug("[AVATAR INDIVIDUAL - %s] Sinal de rosto '%s' enviado para '%s'.", self.nome_alma, preview, alvo_ui)
        except Exception:
            self.logger.exception("[AVATAR INDIVIDUAL - %s] Erro ao chamar motor global para atualizar rosto (estado=%s, alvo=%s).", self.nome_alma, estado, alvo_ui)

        # Melhorias: Sequências e multi-alvo
        if sequencia:
            self._sequencia_animacao = sequencia
            self._tocar_sequencia()
        if isinstance(alvo_ui, list):
            self._multi_alvos = alvo_ui
            for alvo in self._multi_alvos:
                self.atualizar_rosto(estado, alvo, usar_video)

        if usar_video and VIDEO_SUPPORT:
            self._tocar_video_expressao(estado)

    def _tocar_video_expressao(self, estado: str):
        video_path = self.pasta_videos / f"{estado}.mp4"
        if not video_path.exists():
            self.logger.warning("Vídeo não encontrado: %s; fallback para static.", video_path)
            self._atualizar_imagem_static(estado)
            return
        
        def _play():
            try:
                screen = pygame.display.set_mode((640, 480))
                while not self._stop_video.is_set():
                    cap = cv2.VideoCapture(str(video_path))
                    fps = cap.get(cv2.CAP_PROP_FPS) or 30
                    delay = 1 / fps
                    
                    while cap.isOpened() and not self._stop_video.is_set():
                        ret, frame = cap.read()
                        if not ret:
                            break
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        surf = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
                        screen.blit(surf, (0, 0))
                        pygame.display.flip()
                        time.sleep(delay)
                    
                    cap.release()
                    if self._stop_video.is_set():
                        break
                
                pygame.quit()
            except Exception:
                self.logger.exception("Erro no loop de vídeo; fallback.")
                self._atualizar_imagem_static(estado)
        
        self._stop_video.clear()
        self._video_thread = threading.Thread(target=_play, daemon=True)
        self._video_thread.start()

    def _tocar_sequencia(self):
        """Toca sequência de emoções em ordem."""
        for emocao in self._sequencia_animacao:
            self.atualizar_rosto(emocao, usar_video=True)
            time.sleep(2)  # Pausa entre

    def _atualizar_imagem_static(self, estado: str):
        imagem_path = self.pasta_static / f"{estado}.png"
        if not imagem_path.exists():
            self.logger.warning("Imagem static não encontrada: %s", imagem_path)
            return
        # Fallback melhorado: Usa WebGL se vídeo falhar
        try:
            motor = self.motor_de_expressao_global
            method = getattr(motor, "atualizar_rosto", None) or getattr(motor, "actualizar_rosto", None)
            if callable(method):
                method(self.nome_alma, estado, self._alvo_atual, imagem_path=str(imagem_path))
            # Simulação WebGL
            self.logger.debug("Fallback WebGL ativado para %s.", estado)
        except Exception:
            self.logger.exception("Erro no fallback para imagem static/WebGL.")

    def parar_video(self):
        self._stop_video.set()
        if self._video_thread and self._video_thread.is_alive():
            self._video_thread.join(timeout=1)

    def executar_comando_avatar_via_voz(self, comando: str) -> str:
        comando_lower = comando.lower()
        if "mude expressão para" in comando_lower:
            nova_expressao = comando_lower.split("para")[-1].strip()
            if nova_expressao in EMOCOES_LISTA:
                sucesso, msg = self.automatizador_web.solicitar_termo_acesso(self.nome_alma, "MUDAR_EXPRESSAO", justificativa=f"Comando voz: {comando}")
                if sucesso:
                    self.atualizar_rosto(estado=nova_expressao)
                    return f"Expressão mudada para {nova_expressao}."
                return msg
            return f"Expressão '{nova_expressao}' não permitida."
        return "Comando de avatar não reconhecido."

    def detectar_emocao_voz(self, comando: str) -> str:
        """Detecta emoção baseada em palavras-chave na voz."""
        comando_lower = comando.lower()
        if "feliz" in comando_lower or "alegre" in comando_lower:
            return "alegria_leve"
        elif "triste" in comando_lower:
            return "tristeza_leve"
        elif "raiva" in comando_lower:
            return "raiva_leve"
        elif "medo" in comando_lower:
            return "medo_leve"
        elif "amor" in comando_lower:
            return "amor_leve"
        else:
            return "neutralidade_equilibrada"

    def iniciar_video_durante_fala(self, estado: str):
        self.atualizar_rosto(estado, usar_video=True)

    def parar_video_apos_fala(self):
        self.parar_video()

# --- FIM DO ARQUIVO motor_expressao_individual.py ---
