"""Configuração do sistema"""

try:
    from src.config.config import get_config, Config
except Exception: pass
try:
    from src.config.config_wrapper import ConfigWrapper, Config as ConfigAlias
except Exception: pass
