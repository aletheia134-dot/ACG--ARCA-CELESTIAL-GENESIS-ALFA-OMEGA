"""
ARCA CELESTIAL GENESIS - Pacote src
Ponte para os módulos raiz do projeto.
Adiciona a raiz ao sys.path para que todos os submódulos funcionem.
"""
import sys, os as _os

# Raiz = 2 níveis acima de src/ → E:\Arca_Celestial_Genesis_Alfa_Omega
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
del _ROOT
