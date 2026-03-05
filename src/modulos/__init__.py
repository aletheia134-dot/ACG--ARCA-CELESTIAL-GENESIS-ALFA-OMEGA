import logging

# Decision Engine (principal)
try:
    from .decision import DecisionEngine as Decision
    DECISION_OK = True
except Exception as e:
    logging.getLogger(__name__).warning(f"âÅ¡Â Í¯Â¸Â DecisionEngine nÍÂ£o disponÍÂ­vel: {e}")
    Decision = None
    DECISION_OK = False

# Motor de DecisÍÂ£o (mÍ³dulo separado)
try:
    from .motor_decisao import MotorDecisao
    MOTOR_DECISAO_OK = True
except Exception as e:
    logging.getLogger(__name__).warning(f"âÅ¡Â Í¯Â¸Â MotorDecisao nÍÂ£o disponÍÂ­vel: {e}")
    MotorDecisao = None
    MOTOR_DECISAO_OK = False

# Motor de Rotina (agora MotorMonitor)
try:
    from .motor_rotina import MotorMonitor
    MOTOR_ROTINA_OK = True
except Exception as e:
    logging.getLogger(__name__).warning(f"âÅ¡Â Í¯Â¸Â MotorMonitor nÍÂ£o disponÍÂ­vel: {e}")
    MotorMonitor = None
    MOTOR_ROTINA_OK = False

# ExportaÍÂ§ÍÂ£o explÍÂ­cita dos sÍÂ­mbolos disponÍÂ­veis
__all__ = []
if DECISION_OK:
    __all__.append("Decision")
if MOTOR_DECISAO_OK:
    __all__.append("MotorDecisao")
if MOTOR_ROTINA_OK:
    __all__.append("MotorMonitor")


