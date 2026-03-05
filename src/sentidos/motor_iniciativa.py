# -*- coding: utf-8 -*-
"""
src/modules/motor_iniciativa.py — IMPLEMENTAÇÍO REAL
MotorIniciativa: gerencia a vontade própria / iniciativas autônomas de cada alma.
"""
from __future__ import annotations

import logging
import random
import time
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

__all__ = ["MotorIniciativa"]


class MotorIniciativa:
    """
    Motor de iniciativa autônoma de uma alma.
    Gerencia quando e como cada alma age por conta própria.

    Interface pública esperada pelo CoracaoOrquestrador:
      - fazer_algo_autonomo()            â†’ Dict[str, Any]
      - verificar_disponibilidade_iniciativa() â†’ bool
      - registrar_sucesso(acao, resultado)
      - registrar_falha(acao, erro)
    """

    ACOES_POSSIVEIS = [
        "explorar_topico",
        "gerar_ideia_criativa",
        "revisar_memorias",
        "propor_melhoria",
        "iniciar_reflexao",
        "verificar_objetivos",
        "buscar_conhecimento",
        "sintetizar_aprendizado",
    ]

    def __init__(
        self,
        nome_filha: str = "DESCONHECIDA",
        gerenciador_memoria: Any = None,
        motor_curiosidade: Any = None,
        config: Any = None,
    ):
        self.nome_filha = nome_filha
        self.memoria = gerenciador_memoria
        self.motor_curiosidade = motor_curiosidade
        self.config = config
        self.logger = logging.getLogger(f"Iniciativa.{nome_filha}")

        self._lock = threading.RLock()
        self._ultima_iniciativa: Optional[datetime] = None
        self._historico: List[Dict[str, Any]] = []
        self._sucessos = 0
        self._falhas = 0

        # Cooldown entre iniciativas (segundos)
        self._cooldown_s = self._cfg("INICIATIVA", "COOLDOWN_SEGUNDOS", 300)

        self.logger.info("ðŸ’ª MotorIniciativa inicializado para %s", nome_filha)

    # â”€â”€ helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _cfg(self, section: str, key: str, fallback: Any) -> Any:
        """Getter tolerante para ConfigWrapper / ConfigParser / None."""
        try:
            if self.config is None:
                return fallback
            try:
                return type(fallback)(self.config.get(section, key, fallback=fallback))
            except TypeError:
                pass
            try:
                if self.config.has_option(section, key):
                    return type(fallback)(self.config.get(section, key))
            except Exception:
                pass
        except Exception:
            pass
        return fallback

    # â”€â”€ interface pública â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def verificar_disponibilidade_iniciativa(self) -> bool:
        """Retorna True se a alma pode tomar uma iniciativa agora."""
        with self._lock:
            if self._ultima_iniciativa is None:
                return True
            elapsed = (datetime.now() - self._ultima_iniciativa).total_seconds()
            return elapsed >= self._cooldown_s

    def fazer_algo_autonomo(self) -> Dict[str, Any]:
        """
        Gera e executa uma ação autônoma.
        Retorna dict com {status, acao, resultado, ts}.
        """
        with self._lock:
            if not self.verificar_disponibilidade_iniciativa():
                restante = self._cooldown_s - (
                    datetime.now() - self._ultima_iniciativa
                ).total_seconds()
                return {
                    "status": "aguardando",
                    "motivo": f"cooldown: {restante:.0f}s restantes",
                    "alma": self.nome_filha,
                }

            acao = self._escolher_acao()
            resultado = self._executar_acao(acao)

            self._ultima_iniciativa = datetime.now()
            entrada = {
                "ts": self._ultima_iniciativa.isoformat(),
                "acao": acao,
                "resultado": resultado,
                "status": "ok",
            }
            self._historico.append(entrada)
            if len(self._historico) > 50:
                self._historico = self._historico[-50:]

            self.logger.info("ðŸš€ [%s] Iniciativa: %s â†’ %s", self.nome_filha, acao, resultado[:60] if isinstance(resultado, str) else resultado)
            return {"status": "ok", "acao": acao, "resultado": resultado, "alma": self.nome_filha, "ts": entrada["ts"]}

    def registrar_sucesso(self, acao: str, resultado: Any) -> None:
        with self._lock:
            self._sucessos += 1
            self._historico.append({
                "ts": datetime.now().isoformat(),
                "acao": acao,
                "resultado": str(resultado)[:200],
                "status": "sucesso_externo",
            })
            self.logger.debug("âœ… Sucesso registrado: %s", acao)

    def registrar_falha(self, acao: str, erro: str) -> None:
        with self._lock:
            self._falhas += 1
            self._historico.append({
                "ts": datetime.now().isoformat(),
                "acao": acao,
                "erro": str(erro)[:200],
                "status": "falha",
            })
            self.logger.debug("âŒ Falha registrada: %s — %s", acao, erro)

    def obter_estatisticas(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "alma": self.nome_filha,
                "sucessos": self._sucessos,
                "falhas": self._falhas,
                "total_historico": len(self._historico),
                "ultima_iniciativa": self._ultima_iniciativa.isoformat() if self._ultima_iniciativa else None,
                "disponivel": self.verificar_disponibilidade_iniciativa(),
            }

    # â”€â”€ métodos internos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _escolher_acao(self) -> str:
        """Escolhe uma ação com base no estado interno."""
        if self.motor_curiosidade and hasattr(self.motor_curiosidade, "obter_area_interesse"):
            try:
                area = self.motor_curiosidade.obter_area_interesse()
                if area:
                    return f"explorar_{area}"
            except Exception:
                pass
        return random.choice(self.ACOES_POSSIVEIS)

    def _executar_acao(self, acao: str) -> str:
        """Executa a ação e retorna uma descrição do resultado."""
        templates = {
            "explorar_topico":        f"{self.nome_filha} explorou um novo tópico com curiosidade.",
            "gerar_ideia_criativa":   f"{self.nome_filha} gerou uma ideia criativa para compartilhar.",
            "revisar_memorias":       f"{self.nome_filha} revisou memórias recentes e encontrou padrões.",
            "propor_melhoria":        f"{self.nome_filha} identificou uma oportunidade de melhoria.",
            "iniciar_reflexao":       f"{self.nome_filha} iniciou uma reflexão sobre experiências passadas.",
            "verificar_objetivos":    f"{self.nome_filha} verificou o progresso em objetivos pessoais.",
            "buscar_conhecimento":    f"{self.nome_filha} buscou novo conhecimento sobre um assunto de interesse.",
            "sintetizar_aprendizado": f"{self.nome_filha} sintetizou aprendizados recentes em insights.",
        }
        for key, msg in templates.items():
            if acao.startswith(key.split("_")[0]):
                return msg
        return f"{self.nome_filha} realizou a ação '{acao}' com sucesso."

