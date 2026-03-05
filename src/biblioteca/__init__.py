try:
    from .busca_hibrida import BuscaHibrida
except:
    logging.getLogger(__name__).warning("âÅ¡Â Í¯Â¸Â BuscaHibrida nÍÂ£o disponÍÂ­vel")
    BuscaHibrida = None
try:
    from .cache_consultas import CacheConsultas
except:
    logging.getLogger(__name__).warning("âÅ¡Â Í¯Â¸Â BuscaHibrida nÍÂ£o disponÍÂ­vel")
    BuscaHibrida = None



