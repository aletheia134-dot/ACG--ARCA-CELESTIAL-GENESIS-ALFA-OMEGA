"""
Segurança e sandboxing - ARCA GENESIS
Firmado: Conexão obrigatória do Detector de Mentira
"""

try:
    from src.seguranca.detector_sandbox import DetectorSandbox
except Exception: 
    pass

try:
    from src.seguranca.bot_analise_seguranca import BotAnalisadorSeguranca
except Exception: 
    pass

try:
    from src.seguranca.guardiao_verdade import GuardiaoVerdade
except Exception: 
    pass

# Import correto do DetectorMentira
from .detector_de_mentira import DetectorMentira

# Criar alias para compatibilidade
DetectorDeMentira = DetectorMentira

__all__ = ['DetectorMentira', 'DetectorDeMentira', 'DetectorSandbox', 'BotAnalisadorSeguranca', 'GuardiaoVerdade']