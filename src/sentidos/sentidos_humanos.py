from __future__ import annotations


import logging
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger("SentidosHumanos")

try:
    from.sistema_voz import SistemaVozReal
    VOZ_OK = True
except Exception:
    SistemaVozReal = None
    VOZ_OK = False
    logger.debug("âš ï¸ SistemaVozReal não disponível")

try:
    from.sistema_audicao import SistemaAudicaoReal
    AUDICAO_OK = True
except Exception:
    SistemaAudicaoReal = None
    AUDICAO_OK = False
    logger.debug("âš ï¸ SistemaAudicaoReal não disponível")

def _make_config_getter(config_obj: Any):
    def get_safe(section: str, key: str, fallback: Optional[Any] = None) -> Any:
        try:
            if config_obj is None:
                return fallback
            get = getattr(config_obj, "get", None)
            if callable(get):
                try:
                    return config_obj.get(section, key, fallback=fallback)
                except TypeError:
                    try:
                        return config_obj.get(section, key)
                    except Exception:
                        return fallback
                except Exception:
                    return fallback
            return getattr(config_obj, key, fallback)
        except Exception:
            return fallback
    return get_safe

class SentidosHumanos:

    def __init__(self, coracao_ref: Optional[Any] = None, config: Optional[Any] = None):
        self.coracao = coracao_ref
        self.config = config or {}
        self._get = _make_config_getter(self.config)
        self.logger = logging.getLogger("SentidosHumanos")
        self._lock = threading.RLock()

        if VOZ_OK and SistemaVozReal:
            try:
                self.sistema_voz = SistemaVozReal(self.config)
            except Exception:
                self.logger.exception("Erro ao criar SistemaVozReal")
                self.sistema_voz = None
        else:
            self.logger.warning("SistemaVozReal não disponível")
            self.sistema_voz = None

        if AUDICAO_OK and SistemaAudicaoReal:
            try:
                self.sistema_audicao = SistemaAudicaoReal(self.config)
            except Exception:
                self.logger.exception("Erro ao criar SistemaAudicaoReal")
                self.sistema_audicao = None
        else:
            self.logger.warning("SistemaAudicaoReal não disponível")
            self.sistema_audicao = None

        self.sentimentos_padrao = self._carregar_sentimentos_padrao()

        self.logger.info("âœ… SentidosHumanos inicializado")

    def _carregar_sentimentos_padrao(self) -> Dict[str, float]:
        try:
            return {
                'humor': float(self._get('SENTIMENTOS', 'HUMOR_PADRAO', fallback=0.5)),
                'empatia': float(self._get('SENTIMENTOS', 'EMPATIA_PADRAO', fallback=0.7)),
                'moralidade': float(self._get('SENTIMENTOS', 'MORALIDADE_PADRAO', fallback=0.9)),
                'curiosidade': float(self._get('SENTIMENTOS', 'CURIOSIDADE_PADRAO', fallback=0.6)),
            }
        except Exception:
            self.logger.debug("Erro ao carregar sentimentos; usando defaults")
            return {
                'humor': 0.5,
                'empatia': 0.7,
                'moralidade': 0.9,
                'curiosidade': 0.6
            }

    def falar(self, texto: str, alma_nome: Optional[str] = None) -> None:
        if not self.sistema_voz:
            self.logger.error("Sistema de voz não disponível")
            return
        try:
            self.sistema_voz.falar(texto)
        except Exception:
            self.logger.exception("Erro ao falar")

    def ouvir(self, timeout: float = 5.0) -> Optional[str]:
        if not self.sistema_audicao:
            self.logger.error("Sistema de audição não disponível")
            return None
        try:
            return self.sistema_audicao.ouvir_microfone(timeout=timeout)
        except Exception:
            self.logger.exception("Erro ao ouvir")
            return None

    def analisar_sentimento(self, alma_nome: str, sentimento: str) -> float:
        try:
            if not self.coracao:
                return self.sentimentos_padrao.get(sentimento, 0.5)

            gm = getattr(self.coracao, "gerenciador_memoria", None)
            if gm:
                m0 = getattr(gm, "m0_data", {}) or {}
                alma_data = m0.get('almas', {}).get(alma_nome, {})
                grau = alma_data.get('sentimentos', {}).get(sentimento)
                if isinstance(grau, (int, float)):
                    return float(grau)

            return self.sentimentos_padrao.get(sentimento, 0.5)

        except Exception:
            self.logger.debug("Erro ao analisar sentimento para %s", alma_nome)
            return self.sentimentos_padrao.get(sentimento, 0.5)

    def iniciar(self) -> None:
        try:
            if self.sistema_audicao and hasattr(self.sistema_audicao, "iniciar"):
                self.sistema_audicao.iniciar()
            self.logger.info("âœ… SentidosHumanos iniciados")
        except Exception:
            self.logger.exception("Erro ao iniciar SentidosHumanos")

    def shutdown(self) -> None:
        try:
            if self.sistema_audicao:
                self.sistema_audicao.shutdown()
        except Exception:
            self.logger.exception("Erro ao desligar audição")

        try:
            if self.sistema_voz:
                self.sistema_voz.shutdown()
        except Exception:
            self.logger.exception("Erro ao desligar voz")

        self.logger.info("âœ… SentidosHumanos desligado")

def executar_testes_reais_interativos_async():
    pass



