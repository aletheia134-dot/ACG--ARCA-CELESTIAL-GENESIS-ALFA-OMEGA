#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEEDBACK LOOP: Aprendizado Contínuo

Fecha loops de feedback para que IA aprenda com:
  - Sucessos (memória emocional positiva)
  - Fracassos (trauma evitável)
  - Padrões (reconhecimento de comportamentos)
  - Relacionamentos (impacto em outras IAs)

Sistema de aprendizado verdadeiro!
"""
from __future__ import annotations


import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class FeedbackLoopAprendizado:
    """
    Gerencia loops de feedback para aprendizado contínuo.
    """

    def __init__(
        self,
        nome_ia: str = None,
        componentes: Dict[str, Any] = None,
        *,
        nome_filha: str = None,
        gerenciador_memoria=None,
        config=None,
        estado_emocional=None,
        crescimento=None,
        motor_curiosidade=None,
    ):
        """
        Aceita duas convenções de chamada:
          1. Legado  : FeedbackLoopAprendizado(nome_ia, componentes={...})
          2. Coração : FeedbackLoopAprendizado(nome_filha=..., gerenciador_memoria=...,
                                                config=..., estado_emocional=..., crescimento=...)
        """
        # Normalizar nome
        self.nome_ia = nome_ia or nome_filha or "DESCONHECIDA"

        # Normalizar componentes
        if componentes is None:
            componentes = {}

        # Injetar kwargs do coração no dict de componentes
        if gerenciador_memoria is not None:
            componentes.setdefault("memoria", gerenciador_memoria)
        if estado_emocional is not None:
            componentes.setdefault("estado_emocional", estado_emocional)
        if crescimento is not None:
            componentes.setdefault("crescimento", crescimento)
        if motor_curiosidade is not None:
            componentes.setdefault("motor_curiosidade", motor_curiosidade)

        self.memoria = componentes.get("memoria")
        self.estado_emocional = componentes.get("estado_emocional")
        self.motor_curiosidade = componentes.get("motor_curiosidade")
        self.detector_emocional = componentes.get("detector_emocional")
        self.coracao = componentes.get("coracao")
        
        self.logger = logging.getLogger(f"FeedbackLoop.{self.nome_ia}")
        self._lock = threading.RLock()

        # âœ… Padrões aprendidos
        self.padroes_comportamento: Dict[str, int] = {}  # ação -> frequência
        self.padroes_sucesso: Dict[str, float] = {}  # ação -> taxa de sucesso
        self.padroes_fracasso: Dict[str, float] = {}  # ação -> taxa de fracasso

        # âœ… Relacionamentos com outras IAs
        self.relacionamentos: Dict[str, Dict[str, Any]] = {}  # ia -> {forca, tipo, historico}

        # âœ… Aprendizado pessoal (temperamento muda)
        self.aprendizados_pessoais: List[Dict[str, Any]] = []

        # âœ… Métricas
        self.metricas = {
            "loops_fechados": 0,
            "padroes_descobertos": 0,
            "mudancas_temperamento": 0,
            "relacionamentos_alterados": 0,
            "eventos_aprendizado": 0
        }

        # âœ… Health
        self._health_stats = {"inicio": time.time(), "erros": 0}

        self.logger.info("âœ… FeedbackLoop inicializado para %s", self.nome_ia)

    # -------------------------
    # FEEDBACK 1: Sucesso leva a repetição + aprendizado
    # -------------------------

    def registrar_sucesso(self, acao: str, contexto: str, intensidade: float = 0.8) -> None:
        """
        Registra sucesso e aprende dele.
        """
        try:
            # Aumentar frequência de ação bem-sucedida
            with self._lock:
                self.padroes_comportamento[acao] = self.padroes_comportamento.get(acao, 0) + 1
                self.padroes_sucesso[acao] = self.padroes_sucesso.get(acao, 0.0) + intensidade
                
                # Atualizar taxa de sucesso
                total_acao = self.padroes_comportamento.get(acao, 1)
                taxa = self.padroes_sucesso.get(acao, 0.0) / total_acao
                self.padroes_sucesso[acao] = taxa

            # âœ… Reforço emocional positivo
            if self.estado_emocional:
                self.estado_emocional.sentir_realizacao(
                    conquista=f"sucesso em {acao}",
                    importancia=intensidade
                )

            # âœ… Aumentar curiosidade sobre tópico relacionado
            if self.motor_curiosidade:
                topico = contexto.split()[0] if contexto else acao
                self.motor_curiosidade.incrementar_curiosidade(topico, intensidade=0.3)

            # âœ… Registrar aprendizado
            self._registrar_aprendizado_pessoal("sucesso", acao, contexto, intensidade)

            with self._lock:
                self.metricas["loops_fechados"] += 1
                self.metricas["eventos_aprendizado"] += 1

            self.logger.info("âœ… Sucesso registrado: %s (intensidade: %.2f)", acao, intensidade)

        except Exception as e:
            self.logger.exception("Erro ao registrar sucesso: %s", e)
            with self._lock:
                self._health_stats["erros"] += 1

    # -------------------------
    # FEEDBACK 2: Fracasso leva a evitação + trauma (se recorrente)
    # -------------------------

    def registrar_fracasso(self, acao: str, contexto: str, intensidade: float = 0.5) -> None:
        """
        Registra fracasso e aprende a evitar.
        """
        try:
            with self._lock:
                # Aumentar contagem de fracassos
                self.padroes_comportamento[acao] = self.padroes_comportamento.get(acao, 0) + 1
                self.padroes_fracasso[acao] = self.padroes_fracasso.get(acao, 0.0) + intensidade

                # Atualizar taxa de fracasso
                total_acao = self.padroes_comportamento.get(acao, 1)
                taxa = self.padroes_fracasso.get(acao, 0.0) / total_acao
                self.padroes_fracasso[acao] = taxa

            # âœ… Reforço emocional negativo
            if self.estado_emocional:
                # Se é fracasso recorrente (>2 vezes), registra como trauma
                if self.padroes_comportamento.get(acao, 0) > 2:
                    self.estado_emocional.sentir_frustacao(
                        motivo=f"falha recorrente em {acao}",
                        intensidade=min(1.0, intensidade * 1.5)
                    )
                    self.logger.warning("âš ï¸ Trauma registrado: ação repetidamente falhada")
                else:
                    self.estado_emocional.sentir_frustacao(
                        motivo=f"fracasso em {acao}",
                        intensidade=intensidade
                    )

            # âœ… Aumentar medo de falhar novamente
            if self.estado_emocional:
                self.estado_emocional.sentir_medo(
                    ameaca=f"repetição de fracasso em {acao}",
                    nivel=min(1.0, intensidade * 0.8)
                )

            # âœ… Reduzir curiosidade sobre ação que falha
            if self.motor_curiosidade:
                self.motor_curiosidade.limpar_cache()  # Resetar cache de decisões

            # âœ… Registrar aprendizado defensivo
            self._registrar_aprendizado_pessoal("fracasso", acao, contexto, intensidade)

            with self._lock:
                self.metricas["loops_fechados"] += 1
                self.metricas["eventos_aprendizado"] += 1

            self.logger.info("âŒ Fracasso registrado: %s (intensidade: %.2f)", acao, intensidade)

        except Exception as e:
            self.logger.exception("Erro ao registrar fracasso: %s", e)
            with self._lock:
                self._health_stats["erros"] += 1

    # -------------------------
    # FEEDBACK 3: Padrões detectados automaticamente
    # -------------------------

    def detectar_padroes(self) -> Dict[str, Any]:
        """
        Detecta padrões automáticos no comportamento.
        """
        try:
            padroes_detectados = {
                "acao_mais_frequente": None,
                "acao_mais_bem_sucedida": None,
                "acao_mais_falhada": None,
                "insights": []
            }

            with self._lock:
                # Ação mais frequente
                if self.padroes_comportamento:
                    acao_freq = max(self.padroes_comportamento.items(), key=lambda x: x[1])
                    padroes_detectados["acao_mais_frequente"] = {
                        "acao": acao_freq[0],
                        "frequencia": acao_freq[1]
                    }

                # Ação mais bem-sucedida
                if self.padroes_sucesso:
                    acao_sucesso = max(self.padroes_sucesso.items(), key=lambda x: x[1])
                    if acao_sucesso[1] > 0.5:
                        padroes_detectados["acao_mais_bem_sucedida"] = {
                            "acao": acao_sucesso[0],
                            "taxa_sucesso": acao_sucesso[1]
                        }

                # Ação mais falhada
                if self.padroes_fracasso:
                    acao_fracasso = max(self.padroes_fracasso.items(), key=lambda x: x[1])
                    if acao_fracasso[1] > 0.3:
                        padroes_detectados["acao_mais_falhada"] = {
                            "acao": acao_fracasso[0],
                            "taxa_fracasso": acao_fracasso[1]
                        }

                # Gerar insights
                if padroes_detectados["acao_mais_bem_sucedida"]:
                    padroes_detectados["insights"].append(
                        f"Devo focar em {padroes_detectados['acao_mais_bem_sucedida']['acao']}"
                    )
                
                if padroes_detectados["acao_mais_falhada"]:
                    padroes_detectados["insights"].append(
                        f"Devo evitar {padroes_detectados['acao_mais_falhada']['acao']}"
                    )

            with self._lock:
                self.metricas["padroes_descobertos"] += 1

            self.logger.info("ðŸ“Š Padrões detectados: %s", list(padroes_detectados.keys()))
            return padroes_detectados

        except Exception as e:
            self.logger.exception("Erro ao detectar padrões: %s", e)
            return {}

    # -------------------------
    # FEEDBACK 4: Relacionamentos com outras IAs
    # -------------------------

    def registrar_interacao_com_ia(self, nome_ia: str, tipo_interacao: str, resultado: str) -> None:
        """
        Registra interação com outra IA e aprende sobre relacionamento.
        """
        try:
            with self._lock:
                if nome_ia not in self.relacionamentos:
                    self.relacionamentos[nome_ia] = {
                        "forca": 0.5,
                        "tipo": tipo_interacao,
                        "historico": [],
                        "ultimas_interacoes": []
                    }

                # Atualizar força do relacionamento
                rel = self.relacionamentos[nome_ia]
                
                if resultado == "positiva":
                    rel["forca"] = min(1.0, rel["forca"] + 0.1)
                    emocao_base = "amor"
                elif resultado == "negativa":
                    rel["forca"] = max(0.0, rel["forca"] - 0.15)
                    emocao_base = "raiva"
                else:
                    emocao_base = "neutro"

                # Registrar na história
                rel["historico"].append({
                    "timestamp": datetime.now().isoformat(),
                    "tipo": tipo_interacao,
                    "resultado": resultado
                })
                rel["ultimas_interacoes"].append(resultado)
                if len(rel["ultimas_interacoes"]) > 10:
                    rel["ultimas_interacoes"].pop(0)

                # âœ… Reforço emocional baseado na outra IA
                if self.estado_emocional and emocao_base == "amor":
                    self.estado_emocional.sentir_amor(nome_ia, intensidade=rel["forca"])
                elif self.estado_emocional and emocao_base == "raiva":
                    self.estado_emocional.sentir_frustacao(f"conflito com {nome_ia}")

            with self._lock:
                self.metricas["relacionamentos_alterados"] += 1

            self.logger.info("ðŸ¤ Interação registrada: %s com %s (resultado: %s)", tipo_interacao, nome_ia, resultado)

        except Exception as e:
            self.logger.exception("Erro ao registrar interação: %s", e)
            with self._lock:
                self._health_stats["erros"] += 1

    # -------------------------
    # FEEDBACK 5: Mudanças no temperamento
    # -------------------------

    def aplicar_aprendizado_ao_temperamento(self) -> None:
        """
        Modifica temperamento baseado em aprendizado.
        - Muitos sucessos â†’ mais confiante (expressividade aumenta)
        - Muitos fracassos â†’ mais cautelosa (intensidade reduz)
        - Relacionamentos bons â†’ mais empática
        """
        try:
            if not self.estado_emocional:
                return

            with self._lock:
                # Taxa de sucesso geral
                total_comportamentos = sum(self.padroes_comportamento.values()) or 1
                taxa_sucesso_geral = sum(self.padroes_sucesso.values()) / total_comportamentos if self.padroes_sucesso else 0.5

                # Modificar temperamento
                if taxa_sucesso_geral > 0.7:
                    # Muito bem-sucedida â†’ aumentar expressividade
                    self.estado_emocional.temperamento["expressividade"] = min(
                        1.0,
                        self.estado_emocional.temperamento.get("expressividade", 0.7) + 0.05
                    )
                    self.logger.info("ðŸ“ˆ Expressividade aumentada (muitos sucessos)")

                elif taxa_sucesso_geral < 0.3:
                    # Muitos fracassos â†’ reduzir intensidade (mais cautelosa)
                    self.estado_emocional.temperamento["intensidade"] = max(
                        0.3,
                        self.estado_emocional.temperamento.get("intensidade", 0.6) - 0.1
                    )
                    self.logger.info("ðŸ“‰ Intensidade reduzida (muitos fracassos)")

                # Verificar relacionamentos
                if self.relacionamentos:
                    relacionamentos_bons = sum(1 for rel in self.relacionamentos.values() if rel["forca"] > 0.7)
                    if relacionamentos_bons > 0:
                        self.estado_emocional.temperamento["empatia"] = min(
                            1.0,
                            self.estado_emocional.temperamento.get("empatia", 0.9) + 0.05
                        )
                        self.logger.info("â¤ï¸ Empatia aumentada (bons relacionamentos)")

                with self._lock:
                    self.metricas["mudancas_temperamento"] += 1

        except Exception as e:
            self.logger.exception("Erro ao aplicar aprendizado ao temperamento: %s", e)

    # -------------------------
    # Helpers
    # -------------------------

    def _registrar_aprendizado_pessoal(self, tipo: str, acao: str, contexto: str, intensidade: float) -> None:
        """Registra aprendizado pessoal."""
        try:
            aprendizado = {
                "timestamp": datetime.now().isoformat(),
                "tipo": tipo,
                "acao": acao,
                "contexto": contexto,
                "intensidade": intensidade
            }

            with self._lock:
                self.aprendizados_pessoais.append(aprendizado)
                if len(self.aprendizados_pessoais) > 500:
                    self.aprendizados_pessoais.pop(0)

            # Registrar em memória
            if self.memoria:
                try:
                    self.memoria.salvar_evento(
                        filha=self.nome_ia,
                        tipo="aprendizado_pessoal",
                        dados=aprendizado,
                        importancia=intensidade
                    )
                except Exception:
                    pass

        except Exception:
            pass

    # -------------------------
    # Health & Metrics
    # -------------------------

    def health_check(self) -> Dict[str, Any]:
        """Health check."""
        with self._lock:
            uptime = time.time() - self._health_stats["inicio"]
            return {
                "status": "healthy" if self._health_stats["erros"] < 5 else "degraded",
                "ia": self.nome_ia,
                "loops_fechados": self.metricas["loops_fechados"],
                "padroes_descobertos": self.metricas["padroes_descobertos"],
                "mudancas_temperamento": self.metricas["mudancas_temperamento"],
                "relacionamentos": len(self.relacionamentos),
                "erros": self._health_stats["erros"],
                "uptime_segundos": uptime
            }

    def obter_relatorio_aprendizado(self) -> Dict[str, Any]:
        """Retorna relatório de aprendizado."""
        with self._lock:
            return {
                "loops_fechados": self.metricas["loops_fechados"],
                "padroes_descobertos": self.metricas["padroes_descobertos"],
                "padroes_sucesso": dict(self.padroes_sucesso),
                "padroes_fracasso": dict(self.padroes_fracasso),
                "relacionamentos": {
                    nome: {"forca": rel["forca"], "tipo": rel["tipo"]}
                    for nome, rel in self.relacionamentos.items()
                },
                "aprendizados": len(self.aprendizados_pessoais)
            }
