# -*- coding: utf-8 -*-
"""
ARCA CELESTIAL GENESIS - Módulo de Erros
Todas as exceções personalizadas do sistema.
Local: src/diagnostico/erros.py
"""


# ── Erros base ────────────────────────────────────────────────
class ArcaError(Exception):
    """Exceção base de todos os erros da Arca."""
    pass


# ── Erros de LLM ─────────────────────────────────────────────
class LLMTimeoutError(ArcaError):
    """LLM demorou mais do que o tempo permitido."""
    pass


class LLMUnavailableError(ArcaError):
    """LLM nao esta disponivel ou nao pôde ser carregado."""
    pass


class LLMExecutionError(ArcaError):
    """Erro durante execucao/inferencia do LLM."""
    pass


# ── Erros de Memória ─────────────────────────────────────────
class MemoriaIndisponivelError(ArcaError):
    """Sistema de memória nao esta disponivel."""
    pass


# ── Erros de Modo Seco / Placeholder ────────────────────────
class DryRunError(ArcaError):
    """Operacao bloqueada porque esta em modo de teste."""
    pass


class PlaceholderError(ArcaError):
    """Funcao ainda nao foi implementada (placeholder)."""
    pass


# ── Erros de Configuração e Servicos ────────────────────────
class ErroConfiguracao(ArcaError):
    """Configuracao inválida ou ausente."""
    pass


class ErroTempoEsgotado(ArcaError):
    """Operacao excedeu o tempo limite."""
    pass


class ErroExecucaoServico(ArcaError):
    """Erro durante execucao de um servico externo."""
    pass


# ── Aliases de compatibilidade ───────────────────────────────
TimeoutError_  = LLMTimeoutError
ServiceError   = ErroExecucaoServico
ConfigError    = ErroConfiguracao
