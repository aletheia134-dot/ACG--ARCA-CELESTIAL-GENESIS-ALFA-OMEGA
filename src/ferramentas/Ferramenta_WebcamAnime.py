#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Ferramenta: Webcam  Anime em Tempo Real
Aplica estilo anime em feed de cmera ação vivo usando AnimeGAN2.

Modos de execução:
  python Ferramenta_WebcamAnime.py                        # Interface grfica
  python Ferramenta_WebcamAnime.py --capturar PASTA       # Captura N frames
  python Ferramenta_WebcamAnime.py --frame IMAGEM.jpg     # Processa 1 frame

CORREO: erro de sintaxe no bloco if __name__ == "__main__"
"""

import sys
import os
import json
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
try:
    from src.modulos.utils import InterfaceBase, Utils
    from src.config.config import PASTA_SAIDAS, USAR_GPU
except ImportError:
    from src.modulos.utils import InterfaceBase, Utils  # mesmo diretório
    PASTA_SAIDAS = Path.home() / "Ferramentas_IA" / "saidas"
    USAR_GPU = False

import cv2
import numpy as np
from PIL import Image
import customtkinter as ctk
from tkinter import messagebox
import threading

try:
    import torch
    TORCH_OK = True
except ImportError:
    TORCH_OK = False
    print("[ERRO] PyTorch no instalado: pip install torch torchvision")

# Tenta importar AnimeGAN
_ANIMEGAN_PATH = Path(__file__).parent.parent / "animegan2-pytorch"
_ANIMEGAN_OK = False
if _ANIMEGAN_PATH.exists() and TORCH_OK:
    sys.path.insert(0, str(_ANIMEGAN_PATH))
    try:
        from model import Generator
        _ANIMEGAN_OK = True
    except ImportError:
        print("[AVISO] animegan2-pytorch no encontrado. Clone o repo em:", _ANIMEGAN_PATH)


# ─────────────────────────────────────────────────────────────────────────────
class MotorAnimeGAN:
    """Aplica estilo anime usando AnimeGAN2 ou fallback cartoonize simples."""

    def __init__(self, usar_gpu: bool = True):
        self.usar_gpu = usar_gpu and TORCH_OK and torch.cuda.is_available() if TORCH_OK else False
        self.device = torch.device("cuda" if self.usar_gpu else "cpu") if TORCH_OK else None
        self.modelo = None
        self.fps_atual = 0
        self._t_ultimo = time.time()
        self._carregar_modelo()

    def _carregar_modelo(self):
        if not _ANIMEGAN_OK:
            print("[AVISO] Usando modo fallback (cartoon simples)")
            return
        try:
            import torch
            self.modelo = Generator()
            self.modelo.eval()
            self.modelo = self.modelo.to(self.device)
            print(f"[OK] AnimeGAN carregado em: {self.device}")
        except Exception as e:
            print(f"[ERRO] Falha ao carregar AnimeGAN: {e}")
            self.modelo = None

    def processar_frame(self, frame_bgr: np.ndarray) -> np.ndarray:
        """
        Recebe frame BGR (OpenCV) e retorna frame processado BGR.
        Se AnimeGAN no estiver disponível, aplica efeito cartoon como fallback.
        """
        if self.modelo is not None:
            return self._processar_com_modelo(frame_bgr)
        else:
            return self._cartoon_fallback(frame_bgr)

    def _processar_com_modelo(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Processa com AnimeGAN2"""
        try:
            import torch
            # BGR  RGB  PIL
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)

            # Resize para 512 (modelo espera mltiplos de 32)
            h, w = frame_bgr.shape[:2]
            new_w = (w // 32) * 32
            new_h = (h // 32) * 32
            pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)

            # Normaliza: [0,255]  [-1,1]
            tensor = torch.from_numpy(np.array(pil_img)).float()
            tensor = tensor.permute(2, 0, 1).unsqueeze(0)  # HWC  BCHW
            tensor = (tensor / 127.5) - 1.0
            tensor = tensor.to(self.device)

            with torch.no_grad():
                saida = self.modelo(tensor)

            # Desnormaliza: [-1,1]  [0,255]
            saida = saida.squeeze(0).permute(1, 2, 0).cpu().numpy()
            saida = ((saida + 1.0) * 127.5).clip(0, 255).astype(np.uint8)

            # Volta para tamanho original
            saida = cv2.resize(saida, (w, h))
            saida_bgr = cv2.cvtColor(saida, cv2.COLOR_RGB2BGR)

            self._calcular_fps()
            return saida_bgr
        except Exception as e:
            print(f"Erro no processamento do modelo: {e}")
            return frame_bgr

    def _cartoon_fallback(self, frame_bgr: np.ndarray) -> np.ndarray:
        """
        Efeito cartoon sem modelo de ML.
        Usa bilateral filter + deteco de bordas.
        """
        # Suaviza preservando bordas
        suave = cv2.bilateralFilter(frame_bgr, d=9, sigmaColor=75, sigmaSpace=75)
        suave = cv2.bilateralFilter(suave,     d=9, sigmaColor=75, sigmaSpace=75)

        # Bordas em cinza
        cinza = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        cinza = cv2.medianBlur(cinza, 7)
        bordas = cv2.adaptiveThreshold(
            cinza, 255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY,
            blockSize=9, C=2
        )
        bordas_bgr = cv2.cvtColor(bordas, cv2.COLOR_GRAY2BGR)

        # Combina
        cartoon = cv2.bitwise_and(suave, bordas_bgr)

        self._calcular_fps()
        return cartoon

    def _calcular_fps(self):
        agora = time.time()
        dt = agora - self._t_ultimo
        self.fps_atual = 1.0 / dt if dt > 0 else 0
        self._t_ultimo = agora


# ─────────────────────────────────────────────────────────────────────────────
class InterfaceWebcamAnime(InterfaceBase):
    """Interface grfica para webcam anime em tempo real."""

    def __init__(self):
        super().__init__(" Webcam Anime - Tempo Real", "900x700")
        self.motor = MotorAnimeGAN(usar_gpu=USAR_GPU)
        self.cap = None
        self.rodando = False
        self._frame_id = None
        self.gravando = False
        self.writer = None
        self._setup_interface()

    def _setup_interface(self):
        # Ttulo
        ctk.CTkLabel(self.frame, text=" Webcam  Anime em Tempo Real",
                     font=("Segoe UI", 22, "bold")).pack(pady=10)

        # Status
        modo_str = "AnimeGAN2 (GPU)" if self.motor.modelo else "Modo Fallback Cartoon"
        ctk.CTkLabel(self.frame, text=f"Modo: {modo_str}",
                     font=("Segoe UI", 13), text_color="#0078D4").pack()

        # rea de preview
        self.lbl_frame = ctk.CTkLabel(self.frame, text=" Inicie a cmera",
                                       font=("Segoe UI", 16), width=640, height=480)
        self.lbl_frame.pack(pady=10)

        # FPS label
        self.lbl_fps = ctk.CTkLabel(self.frame, text="FPS: --",
                                     font=("Segoe UI", 12), text_color="#AAAAAA")
        self.lbl_fps.pack()

        # Controles
        frame_btns = ctk.CTkFrame(self.frame, fg_color="transparent")
        frame_btns.pack(pady=10)

        self.btn_iniciar = ctk.CTkButton(frame_btns, text=" Iniciar Cmera",
                                          width=160, fg_color="#107C10",
                                          command=self._iniciar_camera)
        self.btn_iniciar.pack(side="left", padx=8)

        self.btn_parar = ctk.CTkButton(frame_btns, text=" Parar",
                                        width=120, fg_color="#E81123",
                                        state="disabled", command=self._parar_camera)
        self.btn_parar.pack(side="left", padx=8)

        self.btn_capturar = ctk.CTkButton(frame_btns, text=" Capturar",
                                           width=130, state="disabled",
                                           command=self._capturar_frame)
        self.btn_capturar.pack(side="left", padx=8)

        self.btn_gravar = ctk.CTkButton(frame_btns, text=" Gravar",
                                         width=120, state="disabled",
                                         fg_color="#D83B01", command=self._toggle_gravacao)
        self.btn_gravar.pack(side="left", padx=8)

        # Seletor de cmera
        linha_cam = ctk.CTkFrame(self.frame, fg_color="transparent")
        linha_cam.pack()
        ctk.CTkLabel(linha_cam, text="Cmera:").pack(side="left", padx=5)
        self.combo_cam = ctk.CTkComboBox(linha_cam, values=["0", "1", "2", "3"], width=80)
        self.combo_cam.set("0")
        self.combo_cam.pack(side="left", padx=5)

        self.atualizar_status("Pronto. Clique em 'Iniciar Cmera'.")

    def _iniciar_camera(self):
        cam_idx = int(self.combo_cam.get())
        self.cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY)

        if not self.cap.isOpened():
            messagebox.showerror("Erro", f"Cmera {cam_idx} no encontrada.")
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.rodando = True
        self.btn_iniciar.configure(state="disabled")
        self.btn_parar.configure(state="normal")
        self.btn_capturar.configure(state="normal")
        self.btn_gravar.configure(state="normal")
        self.atualizar_status("Cmera ativa", "#107C10")

        self._atualizar_frame()

    def _atualizar_frame(self):
        if not self.rodando:
            return

        ok, frame = self.cap.read()
        if not ok:
            self.atualizar_status("[AVISO] Falha ao ler cmera", "#FFB900")
            self._frame_id = self.janela.after(50, self._atualizar_frame)
            return

        frame = cv2.flip(frame, 1)  # espelho
        processado = self.motor.processar_frame(frame)

        # Exibe no label
        rgb = cv2.cvtColor(processado, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        ctk_img = ctk.CTkImage(light_image=pil, dark_image=pil, size=(640, 480))
        self.lbl_frame.configure(image=ctk_img, text="")
        self.lbl_frame.image = ctk_img  # evita garbage collection

        # FPS
        self.lbl_fps.configure(text=f"FPS: {self.motor.fps_atual:.1f}")

        # Grava se ativo
        if self.gravando and self.writer:
            self.writer.write(processado)

        self._frame_id = self.janela.after(30, self._atualizar_frame)

    def _parar_camera(self):
        self.rodando = False
        if self._frame_id:
            self.janela.after_cancel(self._frame_id)
        if self.gravando:
            self._toggle_gravacao()
        if self.cap:
            self.cap.release()
            self.cap = None

        self.lbl_frame.configure(image=None, text=" Inicie a cmera")
        self.btn_iniciar.configure(state="normal")
        self.btn_parar.configure(state="disabled")
        self.btn_capturar.configure(state="disabled")
        self.btn_gravar.configure(state="disabled")
        self.atualizar_status("Cmera parada.")

    def _capturar_frame(self):
        if not self.cap or not self.rodando:
            return
        ok, frame = self.cap.read()
        if not ok:
            return
        frame = cv2.flip(frame, 1)
        processado = self.motor.processar_frame(frame)

        PASTA_SAIDAS.mkdir(parents=True, exist_ok=True)
        from datetime import datetime as dt
        nome = f"webcam_anime_{dt.now().strftime('%Y%m%d_%H%M%S')}.png"
        caminho = PASTA_SAIDAS / nome
        cv2.imwrite(str(caminho), processado)
        messagebox.showinfo("Captura", f"Frame salvo em:\n{caminho}")

    def _toggle_gravacao(self):
        if not self.gravando:
            PASTA_SAIDAS.mkdir(parents=True, exist_ok=True)
            from datetime import datetime as dt
            nome = f"webcam_anime_{dt.now().strftime('%Y%m%d_%H%M%S')}.avi"
            caminho = str(PASTA_SAIDAS / nome)
            fourcc = cv2.VideoWriter_fourcc(*"XVID")
            self.writer = cv2.VideoWriter(caminho, fourcc, 20, (640, 480))
            self.gravando = True
            self.btn_gravar.configure(text=" Parar Gravao", fg_color="#E81123")
            self.atualizar_status(f"Gravando: {nome}", "#E81123")
        else:
            self.gravando = False
            if self.writer:
                self.writer.release()
                self.writer = None
            self.btn_gravar.configure(text=" Gravar", fg_color="#D83B01")
            self.atualizar_status("Gravao salva.", "#107C10")

    def _ao_fechar(self):
        self._parar_camera()
        super()._ao_fechar()


# ─────────────────────────────────────────────────────────────────────────────
class ModoIA_WebcamAnime:
    """Modos CLI: capturar N frames ou processar imagem nica."""

    def __init__(self):
        self.motor = MotorAnimeGAN(usar_gpu=USAR_GPU)
        self.utils = Utils()

    def capturar(self, pasta_saida: str, n_frames: int = 5, cam_idx: int = 0) -> dict:
        """Captura N frames, aplica anime, salva na pasta."""
        saida = Path(pasta_saida)
        saida.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(cam_idx)
        if not cap.isOpened():
            return {"sucesso": False, "erro": f"Cmera {cam_idx} no disponível"}

        frames = []
        for i in range(n_frames):
            ok, frame = cap.read()
            if not ok:
                break
            processado = self.motor.processar_frame(frame)
            nome = f"anime_frame_{i:03d}.png"
            cv2.imwrite(str(saida / nome), processado)
            frames.append(nome)
            time.sleep(0.1)

        cap.release()
        return {"sucesso": True, "pasta": str(saida), "frames": frames}

    def processar_imagem(self, caminho_imagem: str) -> dict:
        """Processa uma imagem esttica como se fosse um frame."""
        img_bgr = cv2.imread(caminho_imagem)
        if img_bgr is None:
            return {"sucesso": False, "erro": f"Imagem no encontrada: {caminho_imagem}"}

        processado = self.motor.processar_frame(img_bgr)
        nome = self.utils.safe_filename("anime_frame", "png")
        destino = PASTA_SAIDAS / nome
        PASTA_SAIDAS.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(destino), processado)
        return {"sucesso": True, "arquivo": str(destino)}


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) > 1:
        comando = sys.argv[1]
        ia = ModoIA_WebcamAnime()

        if comando == "--capturar" and len(sys.argv) > 2:
            pasta = sys.argv[2]
            n = int(sys.argv[3]) if len(sys.argv) > 3 else 5
            resultado = ia.capturar(pasta, n_frames=n)
            print(json.dumps(resultado, indent=2, ensure_ascii=False))

        elif comando == "--frame" and len(sys.argv) > 2:
            resultado = ia.processar_imagem(sys.argv[2])
            print(json.dumps(resultado, indent=2, ensure_ascii=False))

        else:
            print("Uso:")
            print("  python Ferramenta_WebcamAnime.py                          # Interface grfica")
            print("  python Ferramenta_WebcamAnime.py --capturar PASTA [N]     # Captura N frames")
            print("  python Ferramenta_WebcamAnime.py --frame IMAGEM.jpg       # Processa 1 imagem")
    else:
        app = InterfaceWebcamAnime()
        app.rodar()
