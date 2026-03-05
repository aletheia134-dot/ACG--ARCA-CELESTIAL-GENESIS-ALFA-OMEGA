
import configparser as _cp
from pathlib import Path as _Path

def get_config():
    """Retorna ConfigParser carregado com config.ini do projeto."""
    cfg = _cp.ConfigParser()
    root = _Path(__file__).parent.parent.parent  # raiz do projeto
    for candidate in [root / 'config.ini', _Path(__file__).parent / 'config.ini']:
        if candidate.exists():
            cfg.read(str(candidate), encoding='utf-8')
            return cfg
    return cfg


class ConfigWrapper:
    """Wrapper para acessar config de forma uniforme."""
    def __init__(self, config=None):
        self._cfg = config if config is not None else get_config()

    def get(self, section, key, fallback=None):
        try:
            return self._cfg.get(section, key)
        except Exception:
            return fallback

    def getint(self, section, key, fallback=0):
        try:
            return self._cfg.getint(section, key)
        except Exception:
            return fallback

    def getboolean(self, section, key, fallback=False):
        try:
            return self._cfg.getboolean(section, key)
        except Exception:
            return fallback

    def has_section(self, section):
        return self._cfg.has_section(section) if self._cfg else False

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
config.py - Configurações centrais do projeto
MELHORIAS v2:
  - Caminho raiz configurável via variável de ambiente FERRAMENTAS_IA_RAIZ
  - Sem drive hardcoded (C: ou E:) - usa o que o usuário definir
  - Detecta GPU automaticamente sem crashar se torch não estiver instalado
"""

import os
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CAMINHO RAIZ - Configurável via variável de ambiente
# Padrão: C:\Ferramentas_IA no Windows, ~/Ferramentas_IA no Linux/Mac
# Para mudar: set FERRAMENTAS_IA_RAIZ=E:\Ferramentas_IA  (Windows)
#             export FERRAMENTAS_IA_RAIZ=/home/user/Ferramentas_IA  (Linux)
# ─────────────────────────────────────────────────────────────────────────────
_raiz_env = os.environ.get("FERRAMENTAS_IA_RAIZ")

if _raiz_env:
    PASTA_RAIZ = Path(_raiz_env)
elif os.name == "nt":  # Windows
    # Detecta automaticamente: usa E: se existir, senão C:
    _drive_e = Path("E:/Ferramentas_IA")
    _drive_c = Path("C:/Ferramentas_IA")
    if _drive_e.parent.exists():
        PASTA_RAIZ = _drive_e
    else:
        PASTA_RAIZ = _drive_c
else:
    # Linux / macOS
    PASTA_RAIZ = Path.home() / "Ferramentas_IA"

# Subpastas
PASTA_TEMP = PASTA_RAIZ / "temp"
PASTA_SAIDAS = PASTA_RAIZ / "saidas"
PASTA_MODELOS = PASTA_RAIZ / "modelos"
PASTA_DOWNLOADS = PASTA_RAIZ / "downloads"
PASTA_LOGS = PASTA_RAIZ / "logs"

# Cria pastas se não existirem
for _pasta in [PASTA_TEMP, PASTA_SAIDAS, PASTA_MODELOS, PASTA_DOWNLOADS, PASTA_LOGS]:
    try:
        _pasta.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        print(f"⚠️ Sem permissão para criar {_pasta}: {e}")
    except Exception as e:
        print(f"⚠️ Erro ao criar {_pasta}: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÕES DE GPU
# ─────────────────────────────────────────────────────────────────────────────
def _detectar_gpu() -> bool:
    """Detecta GPU CUDA sem quebrar se torch não estiver instalado."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False

USAR_GPU: bool = _detectar_gpu()

# Limite de VRAM a usar (em GB). Deixa 2GB para o sistema.
# GTX 1070 tem 8GB → usa no máximo 6GB
VRAM_LIMITE: int = int(os.environ.get("FERRAMENTAS_VRAM_LIMITE", "6"))

# Força CPU mesmo com GPU disponível (útil para debug)
MODO_LEVE: bool = os.environ.get("FERRAMENTAS_MODO_LEVE", "").lower() in ("1", "true", "yes")
if MODO_LEVE:
    USAR_GPU = False

# ─────────────────────────────────────────────────────────────────────────────
# IDIOMAS
# ─────────────────────────────────────────────────────────────────────────────
IDIOMAS_OCR: list = ["pt", "en", "es", "ja"]          # EasyOCR
IDIOMA_WHISPER: str = "pt"                              # Faster-Whisper / Whisper
IDIOMA_TTS_PADRAO: str = "pt"                           # Text-to-Speech

# ─────────────────────────────────────────────────────────────────────────────
# QUALIDADE / TAMANHOS
# ─────────────────────────────────────────────────────────────────────────────
TAMANHO_MAXIMO_IMAGEM: int = 1920   # pixels (largura ou altura máxima)
QUALIDADE_JPEG: int = 95            # 1-100
FPS_WEBCAM: int = 30                # FPS da câmera
RESOLUCAO_WEBCAM: tuple = (1280, 720)

# ─────────────────────────────────────────────────────────────────────────────
# MODELOS - caminhos padrão
# ─────────────────────────────────────────────────────────────────────────────
MODELO_ANIME_GAN = PASTA_MODELOS / "animegan2-pytorch"
MODELO_WHISPER = "base"   # tiny, base, small, medium, large-v2, large-v3
MODELO_REMBG = "u2net"   # u2net, u2net_human_seg, isnet-general-use

# ─────────────────────────────────────────────────────────────────────────────
# DIAGNÓSTICO (imprime ao importar se rodado diretamente)
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  CONFIGURAÇÕES DO PROJETO - FERRAMENTAS IA")
    print("=" * 55)
    print(f"  Pasta raiz  : {PASTA_RAIZ}")
    print(f"  Temp        : {PASTA_TEMP}")
    print(f"  Saídas      : {PASTA_SAIDAS}")
    print(f"  Modelos     : {PASTA_MODELOS}")
    print(f"  GPU ativa   : {USAR_GPU}")
    print(f"  Modo leve   : {MODO_LEVE}")
    print(f"  VRAM limite : {VRAM_LIMITE}GB")
    print(f"  Idioma OCR  : {IDIOMAS_OCR}")
    print(f"  Whisper     : {MODELO_WHISPER}")
    print("=" * 55)
    for p in [PASTA_TEMP, PASTA_SAIDAS, PASTA_MODELOS]:
        status = "✅" if p.exists() else "❌"
        print(f"  {status} {p}")