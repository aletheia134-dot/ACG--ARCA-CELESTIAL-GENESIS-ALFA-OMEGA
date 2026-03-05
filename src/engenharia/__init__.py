# src/engenharia/__init__.py
"""
MÍ³dulo de Engenharia da ARCA ââ‚¬" propostas, ferramentas, evoluÍÂ§ÍÂ£o e seguranÍÂ§a.
"""
from __future__ import annotations

import logging
logger = logging.getLogger(__name__)

# â"â‚¬â"â‚¬ Propostas e Ferramentas â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬
try:
    from .sistema_propostas_ferramentas import GerenciadorPropostas
except Exception as e:
    logger.debug("GerenciadorPropostas: %s", e)
    GerenciadorPropostas = None  # type: ignore

try:
    from .construtor_ferramentas_incremental import ConstrutorFerramentasIncremental
except Exception as e:
    logger.debug("ConstrutorFerramentasIncremental: %s", e)
    ConstrutorFerramentasIncremental = None  # type: ignore

try:
    from .solicitador_arquivos import SolicitadorArquivos
except Exception as e:
    logger.debug("SolicitadorArquivos: %s", e)
    SolicitadorArquivos = None  # type: ignore

try:
    from .bot_analise_seguranca import BotAnalisadorSeguranca
except Exception as e:
    logger.debug("BotAnalisadorSeguranca: %s", e)
    BotAnalisadorSeguranca = None  # type: ignore

try:
    from .integracao_proptas import IntegracaoProptas
except Exception as e:
    logger.debug("IntegracaoProptas: %s", e)
    IntegracaoProptas = None  # type: ignore

# â"â‚¬â"â‚¬ EvoluÍÂ§ÍÂ£o â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬â"â‚¬
try:
    from .scanner_sistema import ScannerSistema
except Exception as e:
    logger.debug("ScannerSistema: %s", e)
    ScannerSistema = None  # type: ignore

try:
    from .lista_evolucao_ia import ListaEvolucaoIA
except Exception as e:
    logger.debug("ListaEvolucaoIA: %s", e)
    ListaEvolucaoIA = None  # type: ignore

try:
    from .gestor_ciclo_evolucao import GestorCicloEvolucao
except Exception as e:
    logger.debug("GestorCicloEvolucao: %s", e)
    GestorCicloEvolucao = None  # type: ignore

try:
    from .integracao_evolucao_ia import IntegracaoEvolucaoIA
except Exception as e:
    logger.debug("IntegracaoEvolucaoIA: %s", e)
    IntegracaoEvolucaoIA = None  # type: ignore

__all__ = [
    "GerenciadorPropostas", "ConstrutorFerramentasIncremental",
    "SolicitadorArquivos", "BotAnalisadorSeguranca", "IntegracaoProptas",
    "ScannerSistema", "ListaEvolucaoIA", "GestorCicloEvolucao",
    "IntegracaoEvolucaoIA",
]



