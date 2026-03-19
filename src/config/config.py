from pathlib import Path
import configparser as _cp
from pathlib import Path as _Path
import os
import sys

# Importar ConfigWrapper unificado do arquivo canônico
try:
    from src.config.config_wrapper import ConfigWrapper, Config, load_config_from_ini
except ImportError:
    # Fallback caso o path de importação esteja quebrado no ambiente atual
    ConfigWrapper = None

def get_config():
    """Retorna ConfigWrapper carregado com config.ini do projeto."""
    # PRIORIDADE: O caminho que você definiu no E:
    candidate = _Path("E:/Arca_Celestial_Genesis_Alfa_Omega/config.ini")
    if candidate.exists():
        return load_config_from_ini(str(candidate))
    
    # Segundo fallback: relativo ao arquivo atual
    root = _Path(__file__).parent
    for candidate_rel in [root / 'config.ini', root.parent / 'config.ini', root.parent.parent / 'config.ini']:
        if candidate_rel.exists():
            return load_config_from_ini(str(candidate_rel))
    return ConfigWrapper() if ConfigWrapper else None

# ─────────────────────────────────────────────────────────────────────────────
# SEGUNDA SEÇÃO: CAMINHOS E CONFIGURAÇÕES GLOBAIS
# ─────────────────────────────────────────────────────────────────────────────

# Detecta a raiz PRIORIZANDO o seu drive E: conforme o config.ini enviado
_conf = get_config()
if _conf and _conf.get("PATHS", "diretorio_raiz"):
    PASTA_RAIZ = Path("E:/Arca_Celestial_Genesis_Alfa_Omega")
else:
    # Sua lógica original de detecção de drive caso o INI falhe
    _env_raiz = os.environ.get("FERRAMENTAS_IA_RAIZ")
    if _env_raiz:
        PASTA_RAIZ = _Path(_env_raiz)
    else:
        _drive_e = _Path("E:/Arca_Celestial_Genesis_Alfa_Omega")
        _drive_c = _Path("C:/Ferramentas_IA")
        PASTA_RAIZ = _drive_e if _drive_e.exists() else _drive_c

# Definição das Subpastas (Mantendo sua estrutura integral)
PASTA_TEMP = PASTA_RAIZ / "temp"
PASTA_SAIDAS = PASTA_RAIZ / "saidas"
PASTA_MODELOS = PASTA_RAIZ / "models"
PASTA_LOGS = PASTA_RAIZ / "Logs"
# Corrigido para buscar exatamente onde você apontou: assets/Avatares
PASTA_AVATARES = PASTA_RAIZ / "assets" / "Avatares"
# Alias para compatibilidade com motor_fala_individual_combinado
AVATARES_2D_PATH = PASTA_AVATARES
DICIONARIO_EMOCOES = PASTA_RAIZ / "data" / "dicionario_emocoes_qualidades.json"

# Garante que as pastas existam
for _p in [PASTA_TEMP, PASTA_SAIDAS, PASTA_MODELOS, PASTA_LOGS]:
    try:
        _p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

def _detectar_gpu() -> bool:
    """Detecta GPU verificando compatibilidade com o ambiente."""
    try:
        import torch
        # Se o NumPy for > 2.0 e o Torch for antigo, isso retorna False ou crasha
        return torch.cuda.is_available()
    except Exception:
        return False

USAR_GPU: bool = _detectar_gpu()
MODO_LEVE: bool = False
VRAM_LIMITE: int = 6 # Conforme seu desejo de performance

# ─────────────────────────────────────────────────────────────────────────────
# PARÂMETROS DE MÍDIA (Mantendo seus valores originais)
# ─────────────────────────────────────────────────────────────────────────────
TAMANHO_MAXIMO_IMAGEM: int = 1920
QUALIDADE_JPEG: int = 95
FPS_WEBCAM: int = 30
RESOLUCAO_WEBCAM: tuple = (1280, 720)

MODELO_ANIME_GAN = PASTA_MODELOS / "animegan2-pytorch"
MODELO_WHISPER = "base"
MODELO_REMBG = "u2net"

if __name__ == "__main__":
    print("=" * 55)
    print("  CONFIGURAÇÕES DO PROJETO - ARCA CELESTIAL")
    print("=" * 55)
    print(f"  Raiz detectada: {PASTA_RAIZ}")
    print(f"  Avatares em   : {PASTA_AVATARES}")
    print(f"  GPU Ativa     : {USAR_GPU}")
    print(f"  NumPy Status  : Verificado para venv core")
    print("=" * 55)