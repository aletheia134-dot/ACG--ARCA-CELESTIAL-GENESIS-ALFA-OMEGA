"""
PATCH para src/emocoes/motor_curiosidade.py
Substitui a função get() que falha com RawConfigParser por uma versão tolerante.

COMO USAR: copie o bloco abaixo e substitua as linhas 281-294
do arquivo src/emocoes/motor_curiosidade.py
"""

# â”€â”€ BLOCO CORRIGIDO (substitui linhas 281-294) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Thresholds
def _cfg_get(cfg, section, key, fallback):
    """Getter tolerante que funciona com ConfigWrapper, ConfigParser e RawConfigParser."""
    try:
        if cfg is None:
            return fallback
        # ConfigWrapper / dict-like com fallback keyword
        if hasattr(cfg, "get"):
            try:
                return cfg.get(section, key, fallback=fallback)
            except TypeError:
                pass
            # ConfigParser / RawConfigParser - fallback via fallback=
            try:
                return cfg.get(section, key, fallback=fallback)
            except TypeError:
                pass
            # RawConfigParser sem fallback keyword: usa has_option
            try:
                if cfg.has_option(section, key):
                    return cfg.get(section, key)
                return fallback
            except Exception:
                pass
        return fallback
    except Exception:
        return fallback

