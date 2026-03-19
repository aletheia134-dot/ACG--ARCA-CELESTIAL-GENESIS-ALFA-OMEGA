"""Diagnóstico e auditoria"""
try:
    from src.diagnostico.erros import (
        ArcaError,
        LLMTimeoutError, LLMUnavailableError, LLMExecutionError,
        MemoriaIndisponivelError, DryRunError, PlaceholderError,
        ErroConfiguracao, ErroTempoEsgotado, ErroExecucaoServico,
    )
except Exception: pass
try:
    from src.diagnostico.auditoria_automatica import AuditoriaArca
except Exception: pass
