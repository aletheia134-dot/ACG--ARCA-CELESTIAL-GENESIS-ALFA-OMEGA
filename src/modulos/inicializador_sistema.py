# src/modulos/inicializador_sistema.py
"""
ARQUIVO DE COMPATIBILIDADE
Este arquivo existe apenas para não quebrar imports antigos.
Por favor, use 'from src.core.inicializador_sistema import ...' no futuro.

Criado em: 2026-03-18
"""

import warnings
warnings.warn(
    "Import from 'src.modulos.inicializador_sistema' is deprecated. "
    "Use 'from src.core.inicializador_sistema import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Redireciona tudo do arquivo core
from src.core.inicializador_sistema import *

# Mantém a mesma interface
__all__ = [
    'inicializar_sistema_completo',
    'remove_markdown_blocks_main',
    'remove_md_blocks',
    'move_future_imports',
    'process_file_remove_md',
    'SRC'
]