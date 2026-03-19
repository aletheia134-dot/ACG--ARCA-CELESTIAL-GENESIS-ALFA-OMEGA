#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Motor de Expresso / Sntese de Voz - ORQUESTRADOR DE SENTIDOS (enduricido)

Local: src/modules/motor_expressao.py

Melhorias aplicadas:
 - Getter de configuração tolerante (get_safe)
 - Prioridade da fila robusta: enfileira tuplas (prioridade, contador, comando)
 - Contador monotnico para desempate; protegido por lock
 - Uso de threading.Event para parada reativa do loop de processamento
 - Chamadas a voz_real defensivas com tratamento de excees
 - Logging seguro (preview + hash) para evitar vazamento de contedo
 - _load_config_values() chamado no __init__
 - Timeouts e comportamentos defensivos ação operar fila e threads
"""


import logging
import queue
import threading
import time
import hashlib
from typing import Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from.sistema_voz_real import SistemaVozReal
    from.sistema_audicao_real import SistemaAudicaoReal

# --- IMPORTAES MODULARES RIGOROSAS ---
try:
    from src.sentidos.sentidos_humanos import SentidosHumanos  # noqa: F401
    from config.config import ConfiguracaoManager  # noqa: F401
except ImportError as e:
    logging.getLogger("MotorExpressao").critical(f"ERRO crítico: Dependncia Sentidos Humanos ausente: {e}")
    raise

logger = logging.getLogger("MotorExpressao")


class TipoExpressao(Enum):
    FALA = "fala"
    AVATAR_2D = "avatar_2d"


class Idioma(Enum):
    PT_BR = "pt-BR"
    JP = "ja-JP"


@dataclass
class ComandoExpressao:
    alma_nome: str
    tipo: TipoExpressao
    conteudo: str
    idioma: Idioma = field(default=Idioma.PT_BR)
    prioridade: int = field(default=5)
    metadata: Dict = field(default_factory=dict)

    # Nota: a ordenao  feita externamente via tupla (prioridade, contador, comando)
    def preview_hash(self, max_len: int = 120) -> str:
        txt = self.conteudo or ""
        preview = (txt[:max_len] + "...") if len(txt) > max_len else txt
        h = hashlib.sha256(txt.encode("utf-8")).hexdigest()[:8] if txt else "nil"
        return f"{preview} (h={h})"


def _make_get_safe(config_obj: Any):
    """Getter tolerante: get_safe(section, key, fallback=None)"""
    def get_safe(section: str, key: str, fallback: Optional[Any] = None) -> Any:
        try:
            if config_obj is None:
                return fallback
            if hasattr(config_obj, "get"):
                try:
                    return config_obj.get(section, key, fallback=fallback)
                except TypeError:
                    try:
                        return config_obj.get(section, key)
                    except Exception:
                        return fallback
            return getattr(config_obj, key, fallback)
        except Exception:
            return fallback
    return get_safe


class MotorExpressao:
    def __init__(self, config: "ConfiguracaoManager", voz_real: "SistemaVozReal", audicao_real: "SistemaAudicaoReal"):
        self.config = config
        self.voz_real = voz_real
        self.audicao_real = audicao_real

        self._get_safe = _make_get_safe(config)

        self.idioma_padrao = Idioma.PT_BR
        self.fila_expressoes: "queue.PriorityQueue[tuple]" = queue.PriorityQueue()
        self._counter_lock = threading.Lock()
        self._counter = 0

        # controle do loop
        self._stop_event = threading.Event()
        self._thread_processamento: Optional[threading.Thread] = None
        self._running = False

        # configuração carregada
        self.limite_historico = 100
        self._load_config_values()

        self.logger = logging.getLogger("MotorExpressao")
        self.logger.info("[MotorExpressao] Orquestrador de Sentidos forjado (enduricido).")

    def _load_config_values(self):
        try:
            val = self._get_safe('SISTEMA', 'LIMITE_HISTORICO_EXPRESSAO', fallback=100)
            self.limite_historico = int(val)
        except Exception:
            self.limite_historico = 100

    def _enqueue(self, comando: ComandoExpressao):
        # enfileira (prioridade, contador, comando) para desempate seguro
        with self._counter_lock:
            self._counter += 1
            counter = self._counter
            # menor valor de prioridade => executa antes (se desejar o inverso, inverta a lógica)
            self.fila_expressoes.put((comando.prioridade, counter, comando))

    def expressar_fala(self, alma_nome: str, texto: str, idioma: Optional[Idioma] = None, prioridade: int = 5):
        idioma_usar = idioma or self.idioma_padrao
        comando = ComandoExpressao(alma_nome=alma_nome, tipo=TipoExpressao.FALA, conteudo=texto, idioma=idioma_usar, prioridade=prioridade)
        self.expressar(comando)

    def expressar(self, comando: ComandoExpressao):
        # metadata timestamp (ISO)
        comando.metadata["timestamp"] = datetime.now().isoformat()
        self._enqueue(comando)
        # inicia processamento se necessário
        if not self._running:
            self.iniciar_processamento()

    def iniciar_processamento(self):
        if self._running:
            return
        self._stop_event.clear()
        self._thread_processamento = threading.Thread(target=self._processar_fila, daemon=True, name="MotorExpressao-Processor")
        self._running = True
        self._thread_processamento.start()
        self.logger.info("Processamento de expresso iniciado.")

    def _processar_fila(self):
        # Loop responsivo ação stop_event
        try:
            while not self._stop_event.is_set():
                try:
                    prioridade, _, comando = self.fila_expressoes.get(timeout=0.5)
                except queue.Empty:
                    continue
                try:
                    self._executar_expressao(comando)
                except Exception:
                    self.logger.exception("Erro ao executar expresso (continuando)")
        finally:
            self._running = False
            self.logger.info("Processamento de expresso finalizado.")

    def _executar_expressao(self, comando: ComandoExpressao):
        if comando.tipo == TipoExpressao.FALA:
            self.logger.info("Delegando fala para %s: %s", comando.alma_nome, comando.preview_hash(80))
            sucesso = False
            diagnostico = {}
            try:
                # chamada defensiva ação motor de voz real
                if hasattr(self.voz_real, "falar_real"):
                    try:
                        res = self.voz_real.falar_real(
                            alma=comando.alma_nome,
                            texto=comando.conteudo,
                            idioma=comando.idioma.value,
                            assincrono=True
                        )
                        # suportar retorno em diversas formas
                        if isinstance(res, tuple) and len(res) >= 1:
                            sucesso = bool(res[0])
                            diagnostico = res[1] if len(res) > 1 and isinstance(res[1], dict) else {}
                        elif isinstance(res, bool):
                            sucesso = res
                        else:
                            # caso no esperado, considerar sucesso se truthy
                            sucesso = bool(res)
                    except Exception:
                        self.logger.exception("Exception ação chamar voz_real.falar_real")
                        sucesso = False
                        diagnostico = {"erro": "excecao_chamada"}
                else:
                    self.logger.error("voz_real no implementa 'falar_real'")
                    sucesso = False
                    diagnostico = {"erro": "api_ausente"}
            except Exception:
                self.logger.exception("Erro inesperado ao delegar fala")
                sucesso = False
                diagnostico = {"erro": "exception_interna"}

            if not sucesso:
                self.logger.error("FALA falhou para %s: %s", comando.alma_nome, diagnostico.get("erro", diagnostico))
            else:
                self.logger.debug("FALA executada para %s", comando.alma_nome)

        elif comando.tipo == TipoExpressao.AVATAR_2D:
            # integrao com avatar 2D se houver (defensiva)
            self.logger.info("Mostrar avatar 2D para %s: %s", comando.alma_nome, comando.conteudo[:80])
            # implementao especfica do avatar no fornecida aqui
        else:
            self.logger.warning("Tipo de expresso desconhecido: %s", comando.tipo)

    def parar_processamento(self):
        self._stop_event.set()
        if self._thread_processamento and self._thread_processamento.is_alive():
            try:
                self._thread_processamento.join(timeout=2.0)
            except Exception:
                self.logger.debug("Timeout ou erro no join do thread de processamento")
        self._running = False

    def shutdown(self):
        """Encerramento ordenado do orquestrador."""
        self.logger.info("Shutting down MotorExpressao...")
        self.parar_processamento()


