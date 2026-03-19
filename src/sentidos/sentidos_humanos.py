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
    logger.debug("[AVISO] SistemaVozReal no disponível")

try:
    from.sistema_audicao import SistemaAudicaoReal
    AUDICAO_OK = True
except Exception:
    SistemaAudicaoReal = None
    AUDICAO_OK = False
    logger.debug("[AVISO] SistemaAudicaoReal no disponível")

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
            self.logger.warning("SistemaVozReal no disponível")
            self.sistema_voz = None

        if AUDICAO_OK and SistemaAudicaoReal:
            try:
                self.sistema_audicao = SistemaAudicaoReal(self.config)
            except Exception:
                self.logger.exception("Erro ao criar SistemaAudicaoReal")
                self.sistema_audicao = None
        else:
            self.logger.warning("SistemaAudicaoReal no disponível")
            self.sistema_audicao = None

        self.sentimentos_padrao = self._carregar_sentimentos_padrao()

        self.logger.info("[OK] SentidosHumanos inicializado")

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
            self.logger.error("Sistema de voz no disponível")
            return
        try:
            self.sistema_voz.falar(texto)
        except Exception:
            self.logger.exception("Erro ao falar")

    def ouvir(self, timeout: float = 5.0) -> Optional[str]:
        if not self.sistema_audicao:
            self.logger.error("Sistema de audio no disponível")
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

    def obter_estado_atual(self) -> Dict[str, Any]:
        """Retorna estado atual de todos os sentidos. Chamado por coracao.obter_estado_sensorial_atual()."""
        estado: Dict[str, Any] = {
            "voz_disponivel": self.sistema_voz is not None,
            "audicao_disponivel": self.sistema_audicao is not None,
            "sentimentos": dict(self.sentimentos_padrao),
        }
        # Estado real da voz
        if self.sistema_voz:
            try:
                if hasattr(self.sistema_voz, "esta_falando"):
                    estado["voz_ativa"] = self.sistema_voz.esta_falando()
                elif hasattr(self.sistema_voz, "engine") and self.sistema_voz.engine:
                    estado["voz_ativa"] = True
                else:
                    estado["voz_ativa"] = False
            except Exception:
                estado["voz_ativa"] = False
        else:
            estado["voz_ativa"] = False

        # Estado real da audição
        if self.sistema_audicao:
            try:
                if hasattr(self.sistema_audicao, "esta_ouvindo"):
                    estado["audicao_ativa"] = self.sistema_audicao.esta_ouvindo()
                elif hasattr(self.sistema_audicao, "ouvindo"):
                    estado["audicao_ativa"] = bool(self.sistema_audicao.ouvindo)
                else:
                    estado["audicao_ativa"] = False
            except Exception:
                estado["audicao_ativa"] = False
        else:
            estado["audicao_ativa"] = False

        return estado

    def calibrar_sentido(self, sentido: str, parametros: Dict[str, Any]) -> bool:
        """Calibra um sentido específico. Chamado por coracao.calibrar_sentido()."""
        sentido = sentido.lower()
        try:
            if sentido in ("voz", "fala", "tts"):
                if self.sistema_voz:
                    if "velocidade" in parametros and hasattr(self.sistema_voz, "engine") and self.sistema_voz.engine:
                        self.sistema_voz.engine.setProperty("rate", int(parametros["velocidade"]))
                    if "volume" in parametros and hasattr(self.sistema_voz, "engine") and self.sistema_voz.engine:
                        self.sistema_voz.engine.setProperty("volume", float(parametros["volume"]))
                    self.logger.info("[OK] Voz calibrada: %s", parametros)
                    return True
                self.logger.warning("sistema_voz indisponível para calibrar")
                return False

            elif sentido in ("audicao", "audio", "microfone", "mic"):
                if self.sistema_audicao:
                    if "timeout" in parametros and hasattr(self.sistema_audicao, "timeout"):
                        self.sistema_audicao.timeout = float(parametros["timeout"])
                    if "energia_minima" in parametros and hasattr(self.sistema_audicao, "recognizer"):
                        self.sistema_audicao.recognizer.energy_threshold = int(parametros["energia_minima"])
                    self.logger.info("[OK] Audição calibrada: %s", parametros)
                    return True
                self.logger.warning("sistema_audicao indisponível para calibrar")
                return False

            elif sentido in ("sentimentos", "emocao", "emocoes"):
                for chave, valor in parametros.items():
                    if chave in self.sentimentos_padrao:
                        self.sentimentos_padrao[chave] = float(valor)
                self.logger.info("[OK] Sentimentos calibrados: %s", parametros)
                return True

            else:
                self.logger.warning("Sentido desconhecido para calibrar: %s", sentido)
                return False

        except Exception:
            self.logger.exception("Erro ao calibrar sentido '%s'", sentido)
            return False

    def processar_estimulo(self, tipo_estimulo: str, dados: Dict[str, Any]) -> Dict[str, Any]:
        """Processa um estímulo sensorial. Chamado por coracao.processar_estimulo_sensorial()."""
        tipo = tipo_estimulo.lower()
        try:
            if tipo in ("fala", "voz", "tts"):
                texto = dados.get("texto", "")
                alma = dados.get("alma", None)
                if texto:
                    self.falar(texto, alma_nome=alma)
                    return {"status": "ok", "tipo": tipo, "texto": texto}
                return {"status": "erro", "mensagem": "texto vazio"}

            elif tipo in ("audio", "microfone", "escuta", "ouvir"):
                timeout = float(dados.get("timeout", 5.0))
                resultado = self.ouvir(timeout=timeout)
                return {
                    "status": "ok",
                    "tipo": tipo,
                    "texto_reconhecido": resultado,
                    "reconheceu": resultado is not None
                }

            elif tipo in ("sentimento", "emocao", "humor"):
                alma = dados.get("alma", "sistema")
                sentimento_nome = dados.get("sentimento", "humor")
                valor = self.analisar_sentimento(alma, sentimento_nome)
                return {
                    "status": "ok",
                    "tipo": tipo,
                    "alma": alma,
                    "sentimento": sentimento_nome,
                    "valor": valor
                }

            elif tipo in ("gravar", "gravar_audio"):
                duracao = float(dados.get("duracao", 5.0))
                resultado = self.gravar_audio(duracao=duracao)
                return {"status": "ok", "tipo": tipo, "resultado": resultado}

            elif tipo in ("transcrever", "gravar_transcrever"):
                duracao = float(dados.get("duracao", 5.0))
                resultado = self.gravar_e_transcrever(duracao=duracao)
                return {"status": "ok", "tipo": tipo, "transcricao": resultado}

            else:
                self.logger.warning("Tipo de estímulo desconhecido: %s", tipo_estimulo)
                return {"status": "erro", "mensagem": f"Tipo '{tipo_estimulo}' não suportado"}

        except Exception as exc:
            self.logger.exception("Erro ao processar estímulo '%s'", tipo_estimulo)
            return {"status": "erro", "mensagem": str(exc)}

    def gravar_audio(self, duracao: float = 5.0) -> Optional[str]:
        """Grava áudio do microfone por `duracao` segundos. Retorna texto reconhecido ou None."""
        if not self.sistema_audicao:
            self.logger.error("sistema_audicao indisponível para gravar_audio")
            return None
        try:
            return self.sistema_audicao.ouvir_microfone(timeout=duracao)
        except Exception:
            self.logger.exception("Erro em gravar_audio")
            return None

    def testar_microfone(self) -> Dict[str, Any]:
        """Testa o microfone e retorna nível de ruído e disponibilidade."""
        resultado: Dict[str, Any] = {
            "disponivel": False,
            "nivel_ruido": None,
            "erro": None
        }
        if not self.sistema_audicao:
            resultado["erro"] = "sistema_audicao não inicializado"
            return resultado
        try:
            import speech_recognition as sr
            recognizer = getattr(self.sistema_audicao, "recognizer", sr.Recognizer())
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
                resultado["disponivel"] = True
                resultado["nivel_ruido"] = recognizer.energy_threshold
        except Exception as exc:
            resultado["erro"] = str(exc)
        return resultado

    def gravar_e_transcrever(self, duracao: float = 5.0) -> Optional[str]:
        """Grava áudio e retorna transcrição. Atalho para gravar_audio()."""
        return self.gravar_audio(duracao=duracao)

    def iniciar(self) -> None:
        try:
            if self.sistema_audicao and hasattr(self.sistema_audicao, "iniciar"):
                self.sistema_audicao.iniciar()
            self.logger.info("[OK] SentidosHumanos iniciados")
        except Exception:
            self.logger.exception("Erro ao iniciar SentidosHumanos")

    def shutdown(self) -> None:
        try:
            if self.sistema_audicao:
                self.sistema_audicao.shutdown()
        except Exception:
            self.logger.exception("Erro ao desligar audio")

        try:
            if self.sistema_voz:
                self.sistema_voz.shutdown()
        except Exception:
            self.logger.exception("Erro ao desligar voz")

        self.logger.info("[OK] SentidosHumanos desligado")

def executar_testes_reais_interativos_async():
    pass



