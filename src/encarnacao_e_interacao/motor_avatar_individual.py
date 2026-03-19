# -*- coding: utf-8 -*-
from __future__ import annotations
"""
MotorAvatarIndividual / MotorExpressaoIndividual
Estrutura real de assets:
  E:\Arca_Celestial_Genesis_Alfa_Omega\assets\Avatares\EVA\3D\       <- modelos 3D
  E:\Arca_Celestial_Genesis_Alfa_Omega\assets\Avatares\EVA\static\  <- imagens 2D paradas
  E:\Arca_Celestial_Genesis_Alfa_Omega\assets\Avatares\EVA\videos\  <- videos de expressao
  E:\Arca_Celestial_Genesis_Alfa_Omega\assets\Avatares\grupo\       <- avatares coletivos
Almas: pasta MAIUSCULO (EVA, KAIYA, LUMINA, NYRA, WELLINGTON, YUNA)
Grupo: pasta 'grupo' (minusculo)
"""

import logging
import threading
import time
from pathlib import Path
from typing import Any, Optional, List, Dict

logger = logging.getLogger("MotorExpressaoIndividual")

# Raiz canonica dos avatares
_RAIZ_AVATARES = Path("E:/Arca_Celestial_Genesis_Alfa_Omega/assets/Avatares")
if not _RAIZ_AVATARES.exists():
    _RAIZ_AVATARES = Path(__file__).resolve().parent.parent.parent / "assets" / "Avatares"

# 144 emocoes
EMOCOES_LISTA: List[str] = [
    "alegria_leve","alegria_forte","alegria_contida","tristeza_leve","tristeza_profunda","tristeza_reflexiva",
    "raiva_leve","raiva_intensa","raiva_controlada","medo_leve","medo_panico","medo_ansioso",
    "surpresa_leve","surpresa_choque","surpresa_curiosa","nojo_leve","nojo_forte","nojo_repulsa",
    "amor_leve","amor_profundo","amor_romantico","odio_leve","odio_intenso","odio_ressentido",
    "ciume_leve","ciume_devorador","ciume_possessivo","vergonha_leve","vergonha_profunda","vergonha_social",
    "orgulho_leve","orgulho_arrogante","orgulho_conquistado","culpa_leve","culpa_pesada","culpa_remorso",
    "esperanca_leve","esperanca_otimista","esperanca_desesperada","desespero_leve","desespero_total","desespero_resignado",
    "confianca_leve","confianca_cega","confianca_prudente","desconfianca_leve","desconfianca_paranoica","desconfianca_cinica",
    "empatia_leve","empatia_profunda","empatia_solidaria","indiferenca_leve","indiferenca_apatia","indiferenca_desinteressada",
    "entusiasmo_leve","entusiasmo_explosivo","entusiasmo_contido","tedio_leve","tedio_profundo","tedio_monotono",
    "curiosidade_leve","curiosidade_intensa","curiosidade_inquisitiva","frustracao_leve","frustracao_irritada","frustracao_desanimada",
    "satisfacao_leve","satisfacao_plena","satisfacao_contente","inveja_leve","inveja_amarga","inveja_competitiva",
    "gratidao_leve","gratidao_profunda","gratidao_emocionada","ressentimento_leve","ressentimento_amargo","ressentimento_silencioso",
    "solidao_leve","solidao_profunda","solidao_isolada","companheirismo_leve","companheirismo_forte","companheirismo_fraterno",
    "paixao_leve","paixao_ardente","paixao_consumidora","calma_leve","calma_serenidade","calma_tranquila",
    "ansiedade_leve","ansiedade_paralisante","ansiedade_nervosa","excitacao_leve","excitacao_eletrizante","excitacao_adrenalina",
    "desgosto_leve","desgosto_repugnante","desgosto_moral","adoracao_leve","adoracao_devota","adoracao_fanatica",
    "desprezo_leve","desprezo_superior","desprezo_desdenhoso","neutralidade_leve","neutralidade_equilibrada","neutralidade_absoluta",
    "indiferenca_avancada","empolgacao_extrema","serenidade_avancada","raiva_suprimida","medo_paranoico","surpresa_estupefata",
    "nojo_extremo","amor_sacrificial","odio_incontrolavel","ciume_patologico","vergonha_crush","orgulho_excessivo",
    "culpa_obsessiva","esperanca_ilusoria","desespero_abissal","confianca_idealista","desconfianca_extrema","empatia_sobrehumana",
    "entusiasmo_incontrolavel","tedio_mortal","curiosidade_dangerosa","frustracao_explosiva","satisfacao_suprema","inveja_venenosa",
    "gratidao_eterna","ressentimento_feroz","solidao_angustiante","companheirismo_universal","paixao_devoradora","calma_imperturbavel",
    "ansiedade_cronica","excitacao_euforica","desgosto_profundo","adoracao_fanatica2","desprezo_absoluto","alegria_euforica",
]

# Suporte video
try:
    import pygame
    import cv2
    VIDEO_SUPPORT = True
except ImportError:
    VIDEO_SUPPORT = False

# Suporte imagem static
try:
    from PIL import Image, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False


def _resolver_pasta_alma(nome_alma: str) -> Path:
    if nome_alma.lower() == "grupo":
        return _RAIZ_AVATARES / "grupo"
    return _RAIZ_AVATARES / nome_alma.upper()


class MotorAvatarIndividual:
    """
    Motor de avatar. Modos: video > static > 3D > sinal motor global
    """
    def __init__(self, nome_alma: str, motor_de_expressao_global_ref: Any = None,
                 automatizador_web_ref: Any = None):
        self.nome_alma = nome_alma
        self.motor_global = motor_de_expressao_global_ref
        self.automatizador_web = automatizador_web_ref
        self.logger = logging.getLogger(f"AvatarIndividual.{self.nome_alma}")

        # Pastas reais baseadas na estrutura do projeto
        self.pasta_alma   = _resolver_pasta_alma(nome_alma)
        self.pasta_3d     = self.pasta_alma / "3D"
        self.pasta_static = self.pasta_alma / "static"
        self.pasta_videos = self.pasta_alma / "videos"

        for p in (self.pasta_3d, self.pasta_static, self.pasta_videos):
            try:
                p.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

        self._estado_atual = "neutralidade_equilibrada"
        self._alvo_atual   = "Quarto"
        self._stop_video   = threading.Event()
        self._video_thread: Optional[threading.Thread] = None
        self._sequencia: List[str] = []

        if VIDEO_SUPPORT:
            try:
                if not pygame.get_init():
                    pygame.init()
            except Exception:
                pass

        self.logger.info(
            "[AVATAR INDIVIDUAL - %s] Motor de Avatar Individual forjado (144 emocoes, videos/avatares, melhorado).",
            self.nome_alma)

    # --- API publica ---

    def atualizar_rosto(self, estado: str = "neutralidade_equilibrada",
                        alvo_ui: str = "Quarto", usar_video: bool = True,
                        sequencia: Optional[List[str]] = None) -> None:
        if not isinstance(estado, str) or not estado:
            estado = "neutralidade_equilibrada"
        if estado not in EMOCOES_LISTA:
            estado = "neutralidade_equilibrada"
        if estado == self._estado_atual and alvo_ui == self._alvo_atual:
            return

        self._estado_atual = estado
        self._alvo_atual   = alvo_ui

        if sequencia:
            self._sequencia = sequencia
            threading.Thread(target=self._tocar_sequencia, daemon=True).start()

        if usar_video and VIDEO_SUPPORT and self._tocar_video_expressao(estado):
            self._notificar_motor_global(estado, alvo_ui)
            return
        if self._exibir_static(estado):
            self._notificar_motor_global(estado, alvo_ui)
            return
        self._notificar_3d(estado)
        self._notificar_motor_global(estado, alvo_ui)

    def obter_arquivo_static(self, estado: str) -> Optional[Path]:
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            p = self.pasta_static / f"{estado}{ext}"
            if p.exists():
                return p
        return None

    def obter_arquivo_3d(self, estado: str) -> Optional[Path]:
        for ext in (".glb", ".obj", ".fbx", ".gltf"):
            p = self.pasta_3d / f"{estado}{ext}"
            if p.exists():
                return p
        for nome in ("idle", "neutral", "base", "default"):
            for ext in (".glb", ".obj", ".fbx", ".gltf"):
                p = self.pasta_3d / f"{nome}{ext}"
                if p.exists():
                    return p
        return None

    def obter_arquivo_video(self, estado: str) -> Optional[Path]:
        for ext in (".mp4", ".webm", ".avi"):
            p = self.pasta_videos / f"{estado}{ext}"
            if p.exists():
                return p
        return None

    def parar_video(self):
        self._stop_video.set()
        if self._video_thread and self._video_thread.is_alive():
            self._video_thread.join(timeout=2)

    def iniciar_video_durante_fala(self, estado: str):
        self.atualizar_rosto(estado, usar_video=True)

    def parar_video_apos_fala(self):
        self.parar_video()

    def detectar_emocao_voz(self, comando: str) -> str:
        c = comando.lower()
        mapa = {
            "feliz": "alegria_leve", "alegre": "alegria_leve",
            "triste": "tristeza_leve", "choro": "tristeza_profunda",
            "raiva": "raiva_leve", "furioso": "raiva_intensa",
            "medo": "medo_leve", "panico": "medo_panico",
            "amor": "amor_leve", "apaixonado": "amor_profundo",
            "curiosidade": "curiosidade_leve",
            "orgulho": "orgulho_leve",
            "calma": "calma_serenidade",
        }
        for palavra, emocao in mapa.items():
            if palavra in c:
                return emocao
        return "neutralidade_equilibrada"

    def executar_comando_avatar_via_voz(self, comando: str) -> str:
        cmd = comando.lower()
        if "mude expressao para" in cmd or "mude expressa para" in cmd:
            nova = cmd.split("para")[-1].strip()
            if nova in EMOCOES_LISTA:
                self.atualizar_rosto(estado=nova)
                return f"Expressao mudada para {nova}."
            return f"Expressao '{nova}' nao reconhecida."
        emocao = self.detectar_emocao_voz(comando)
        self.atualizar_rosto(estado=emocao)
        return f"Expressao detectada: {emocao}."

    def get_info(self) -> Dict[str, Any]:
        def _ls(p: Path, exts: tuple) -> List[str]:
            if not p.exists(): return []
            return [x.stem for x in p.iterdir() if x.suffix.lower() in exts]
        return {
            "alma":            self.nome_alma,
            "pasta_3d":        str(self.pasta_3d),
            "pasta_static":    str(self.pasta_static),
            "pasta_videos":    str(self.pasta_videos),
            "arquivos_3d":     _ls(self.pasta_3d, (".glb",".obj",".fbx",".gltf")),
            "arquivos_static": _ls(self.pasta_static, (".png",".jpg",".jpeg",".webp")),
            "arquivos_video":  _ls(self.pasta_videos, (".mp4",".webm",".avi")),
            "estado_atual":    self._estado_atual,
            "video_support":   VIDEO_SUPPORT,
        }

    # --- internos ---

    def _tocar_video_expressao(self, estado: str) -> bool:
        video_path = self.obter_arquivo_video(estado)
        if video_path is None:
            return False
        self._stop_video.clear()

        def _play():
            try:
                screen = pygame.display.set_mode((640, 480), pygame.NOFRAME)
                pygame.display.set_caption(f"{self.nome_alma} - {estado}")
                clock = pygame.time.Clock()
                while not self._stop_video.is_set():
                    cap = cv2.VideoCapture(str(video_path))
                    fps = cap.get(cv2.CAP_PROP_FPS) or 30
                    while cap.isOpened() and not self._stop_video.is_set():
                        ret, frame = cap.read()
                        if not ret: break
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        surf = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
                        screen.blit(surf, (0, 0))
                        pygame.display.flip()
                        clock.tick(fps)
                        for ev in pygame.event.get():
                            if ev.type == pygame.QUIT:
                                self._stop_video.set()
                    cap.release()
                    if self._stop_video.is_set(): break
            except Exception as ex:
                self.logger.error("Erro no video de %s: %s", estado, ex)
                self._exibir_static(estado)

        self.parar_video()
        self._video_thread = threading.Thread(target=_play, daemon=True,
                                               name=f"Video_{self.nome_alma}")
        self._video_thread.start()
        self.logger.info("[%s] Video iniciado: %s", self.nome_alma, video_path.name)
        return True

    def _exibir_static(self, estado: str) -> bool:
        img_path = self.obter_arquivo_static(estado)
        if img_path is None:
            return False
        self._notificar_motor_global(estado, self._alvo_atual, imagem_path=str(img_path))
        self.logger.info("[%s] Static exibida: %s", self.nome_alma, img_path.name)
        return True

    def _notificar_3d(self, estado: str) -> bool:
        modelo_path = self.obter_arquivo_3d(estado)
        if modelo_path is None:
            return False
        try:
            motor = self.motor_global
            method = getattr(motor, "atualizar_avatar_3d", None)
            if callable(method):
                method(self.nome_alma, estado, str(modelo_path))
        except Exception:
            pass
        self.logger.info("[%s] 3D disponivel: %s", self.nome_alma, modelo_path.name)
        return True

    def _notificar_motor_global(self, estado: str, alvo_ui: str,
                                 imagem_path: Optional[str] = None) -> None:
        motor = self.motor_global
        if motor is None: return
        try:
            method = getattr(motor, "atualizar_rosto", None) or \
                     getattr(motor, "actualizar_rosto", None)
            if not callable(method): return
            if imagem_path:
                method(self.nome_alma, estado, alvo_ui, imagem_path=imagem_path)
            else:
                method(self.nome_alma, estado, alvo_ui)
        except Exception:
            pass

    def _tocar_sequencia(self) -> None:
        for emocao in self._sequencia:
            self.atualizar_rosto(emocao, usar_video=True)
            time.sleep(2)


# Alias de compatibilidade — ambos os nomes apontam para a mesma classe
MotorExpressaoIndividual = MotorAvatarIndividual
