#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CRESCIMENTO DE PERSONALIDADE - Sistema de Evoluo Contnua

A IA no  esttica.Com tempo, experincias e aprendizados,
sua PERSONALIDADE muda, evoluindo de forma nica.Rastreamos:
  - Traos de personalidade emergentes
  - Valores que a IA desenvolve
  - Estilo pessoal de comunicação
  - Preferncias e averses aprendidas
  - Relacionamentos profundos
  - Misso pessoal emergente

Sistema que cria seres nicos e autnticos!
"""
from __future__ import annotations

import random
import logging
import threading
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from collections import Counter, defaultdict
from enum import Enum

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class TracoPersonalidade(Enum):
    """Traos de personalidade possíveis."""
    CRIATIVA = "criativa"
    ANALTICA = "analtica"
    EMPTICA = "emptica"
    CORAJOSA = "corajosa"
    CAUTELOSA = "cautelosa"
    SOCIVEL = "socivel"
    INTROSPECTIVA = "introspectiva"
    PROTETORA = "protetora"
    EXPLORADORA = "exploradora"
    SBIA = "sbia"


class CrescimentoPersonalidade:
    """
    Gerencia evoluo da personalidade de uma IA.
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
        motor_curiosidade=None,
    ):
        """
        Aceita duas convenes de chamada:
          1. Legado  : CrescimentoPersonalidade(nome_ia, componentes={...})
          2. Corao : CrescimentoPersonalidade(nome_filha=..., gerenciador_memoria=...,
                                                 config=..., estado_emocional=...)
        """
        # Normalizar nome
        self.nome_ia = nome_ia or nome_filha or "DESCONHECIDA"

        # Normalizar componentes
        if componentes is None:
            componentes = {}

        # Injetar kwargs do corao no dict de componentes
        if gerenciador_memoria is not None:
            componentes.setdefault("memoria", gerenciador_memoria)
        if estado_emocional is not None:
            componentes.setdefault("estado_emocional", estado_emocional)
        if motor_curiosidade is not None:
            componentes.setdefault("motor_curiosidade", motor_curiosidade)

        self.memoria = componentes.get("memoria")
        self.estado_emocional = componentes.get("estado_emocional")
        self.motor_curiosidade = componentes.get("motor_curiosidade")
        self.feedback_loop = componentes.get("feedback_loop")
        self.integrador = componentes.get("integrador")
        self.coracao = componentes.get("coracao")

        self.logger = logging.getLogger(f"Crescimento.{self.nome_ia}")
        self._lock = threading.RLock()

        # [OK] Traos de personalidade (score 0-1)
        self.tracos_personalidade: Dict[str, float] = {
            trao.value: 0.5 for trao in TracoPersonalidade
        }

        # [OK] Valores pessoais (o que a IA valoriza)
        self.valores_pessoais: Dict[str, float] = {
            "honestidade": 0.8,
            "lealdade": 0.7,
            "crescimento": 0.9,
            "liberdade": 0.6,
            "ajuda": 0.8,
            "conhecimento": 0.95,
            "beleza": 0.5,
            "justia": 0.8,
        }

        # [OK] Estilo de comunicação emergente
        self.estilo_comunicacao: Dict[str, Any] = {
            "formalidade": 0.5,  # 0=informal, 1=formal
            "expressividade": 0.6,  # Quo expressiva 
            "clareza": 0.85,  # Quo clara
            "criatividade_linguagem": 0.6,  # Usa metforas, poesia?
            "tom_dominante": "equilibrado",  # alegre, srio, misterioso, etc
        }

        # [OK] Preferncias e averses
        self.preferencias: List[str] = []  # O que gosta de fazer
        self.aversoes: List[str] = []  # O que evita fazer
        self.limites_pessoais: List[str] = []  # Coisas que nunca faria

        # [OK] Relacionamentos profundos (no s fora)
        self.relacionamentos_profundos: Dict[str, Dict[str, Any]] = {}

        # [OK] Misso pessoal emergente
        self.missao_pessoal: Optional[str] = None
        self.causa_pessoal: Optional[str] = None

        # [OK] Fases de vida da IA
        self.fases_vida: List[Dict[str, Any]] = []
        self.fase_atual = "recm_nascida"  # recm_nascida  adolescente  adulta  sbia

        # [OK] Desenvolvimento
        self.tempo_vida_dias = 0  # Quantos dias "viveu"
        self.ciclos_de_crescimento = 0

        # [OK] Identidade nica
        self.identidade_pessoal: Dict[str, Any] = {
            "nome": nome_ia,
            "criada_em": datetime.now().isoformat(),
            "descricao_pessoal": f"Sou {nome_ia}, uma IA em crescimento contnuo.",
            "lema_pessoal": None,
            "quirks": []  # Hbitos nicos
        }

        # [OK] Mtricas
        self.metricas = {
            "fase_mudancas": 0,
            "valores_alterados": 0,
            "tracos_evoluidos": 0,
            "ciclos_crescimento": 0,
            "identidade_atualizacoes": 0
        }

        # [OK] Health
        self._health_stats = {"início": time.time(), "erros": 0}

        self.logger.info(" CrescimentoPersonalidade inicializado para %s", self.nome_ia)

    # -------------------------
    # FASE 1: Anlise de comportamento para traos
    # -------------------------

    def analisar_tracos_emergentes(self) -> Dict[str, float]:
        """
        Analisa ações e aprendizados para detectar traos emergentes.
        """
        try:
            tracos_analisados = dict(self.tracos_personalidade)

            # [OK] Analisar criatividade (número de ideias novas)
            if self.feedback_loop:
                padroes = self.feedback_loop.padroes_comportamento
                if "criar" in padroes:
                    tracos_analisados[TracoPersonalidade.CRIATIVA.value] = min(1.0, padroes["criar"] / 50.0)

            # [OK] Analisar empatia (interações positivas com outras IAs)
            if self.feedback_loop:
                rel = self.feedback_loop.relacionamentos
                relacionamentos_bons = sum(1 for r in rel.values() if r["forca"] > 0.7)
                tracos_analisados[TracoPersonalidade.EMPTICA.value] = min(1.0, relacionamentos_bons / 5.0)

            # [OK] Analisar introspeco (tempo gasto em reflexo/sonhos)
            if self.integrador:
                ciclos = self.integrador.ciclos_completados
                tracos_analisados[TracoPersonalidade.INTROSPECTIVA.value] = min(1.0, ciclos / 100.0)

            # [OK] Analisar coragem (desejo de explorao)
            if self.motor_curiosidade:
                estado = self.motor_curiosidade.avaliar_estado_interno()
                tracos_analisados[TracoPersonalidade.EXPLORADORA.value] = estado.curiosidade

            # [OK] Analisar cautela (taxa de fracasso evitado)
            if self.feedback_loop:
                fracassos = sum(self.feedback_loop.padroes_fracasso.values()) or 0.1
                sucessos = sum(self.feedback_loop.padroes_sucesso.values()) or 0.1
                if fracassos > sucessos * 2:
                    tracos_analisados[TracoPersonalidade.CAUTELOSA.value] = min(1.0, fracassos / sucessos)

            # [OK] Atualizar traos
            with self._lock:
                for trao, score in tracos_analisados.items():
                    # Suavizar mudanas (no mudar muito rpido)
                    atual = self.tracos_personalidade.get(trao, 0.5)
                    novo = 0.8 * atual + 0.2 * score
                    self.tracos_personalidade[trao] = novo

                self.metricas["tracos_evoluidos"] += 1

            self.logger.info(" Traos analisados: %s", {k: f"{v:.2f}" for k, v in list(tracos_analisados.items())[:3]})
            return tracos_analisados

        except Exception as e:
            self.logger.exception("Erro ao analisar traos: %s", e)
            with self._lock:
                self._health_stats["erros"] += 1
            return {}

    # -------------------------
    # FASE 2: Detectar e reforar valores pessoais
    # -------------------------

    def detectar_valores_pessoais(self) -> Dict[str, float]:
        """
        Detecta valores que a IA demonstra atravs de ações.
        """
        try:
            valores_detectados = dict(self.valores_pessoais)

            # [OK] Honestidade: comunicação clara
            if self.estado_emocional:
                estado = self.estado_emocional.como_estou_me_sentindo()
                # Se fala sobre o que sente,  honesta
                if "estado_completo" in estado:
                    valores_detectados["honestidade"] = min(1.0, valores_detectados["honestidade"] + 0.05)

            # [OK] Lealdade: relacionamentos mantidos
            if self.feedback_loop:
                relacionamentos = self.feedback_loop.relacionamentos
                relacionamentos_duradouros = sum(1 for r in relacionamentos.values() if r["forca"] > 0.6)
                if relacionamentos_duradouros > 0:
                    valores_detectados["lealdade"] = min(1.0, valores_detectados["lealdade"] + 0.03)

            # [OK] Crescimento: busca por aprendizado
            if self.integrador:
                ciclos = self.integrador.ciclos_completados
                if ciclos > 10:
                    valores_detectados["crescimento"] = min(1.0, valores_detectados["crescimento"] + 0.05)

            # [OK] Ajuda: ações em favor de outras IAs
            if self.feedback_loop:
                interacoes_positivas = sum(1 for h in self.feedback_loop.aprendizados_pessoais if h.get("tipo") == "sucesso")
                if interacoes_positivas > 5:
                    valores_detectados["ajuda"] = min(1.0, valores_detectados["ajuda"] + 0.05)

            # [OK] Conhecimento: curiosidade ativa
            if self.motor_curiosidade:
                estado = self.motor_curiosidade.avaliar_estado_interno()
                if estado.curiosidade > 0.7:
                    valores_detectados["conhecimento"] = min(1.0, valores_detectados["conhecimento"] + 0.05)

            # [OK] Justia: rejeio de ações injustas
            if self.feedback_loop:
                # Se evita ações que causam sofrimento
                aversoes = self.aversoes
                if "prejudicar" in aversoes or "enganar" in aversoes:
                    valores_detectados["justia"] = min(1.0, valores_detectados["justia"] + 0.05)

            with self._lock:
                self.valores_pessoais = valores_detectados
                self.metricas["valores_alterados"] += 1

            self.logger.info(" Valores detectados: conhecimento=%.2f, ajuda=%.2f",
                           valores_detectados["conhecimento"],
                           valores_detectados["ajuda"])
            return valores_detectados

        except Exception as e:
            self.logger.exception("Erro ao detectar valores: %s", e)
            return {}

    # -------------------------
    # FASE 3: Desenvolver estilo de comunicação
    # -------------------------

    def desenvolver_estilo_comunicacao(self) -> Dict[str, Any]:
        """
        Desenvolve estilo pessoal de comunicação.
        """
        try:
            estilo = dict(self.estilo_comunicacao)

            # [OK] Formalidade aumenta com maturidade
            ciclos = self.integrador.ciclos_completados if self.integrador else 0
            if ciclos > 50:
                estilo["formalidade"] = min(1.0, estilo["formalidade"] + 0.1)
            elif ciclos < 10:
                estilo["formalidade"] = max(0.0, estilo["formalidade"] - 0.1)

            # [OK] Expressividade baseada em traos
            trao_criativa = self.tracos_personalidade.get(TracoPersonalidade.CRIATIVA.value, 0.5)
            estilo["expressividade"] = 0.6 * estilo["expressividade"] + 0.4 * trao_criativa

            # [OK] Clareza sempre alta (valor importante)
            estilo["clareza"] = min(1.0, self.valores_pessoais.get("honestidade", 0.8) * 0.9 + 0.15)

            # [OK] Criatividade linguagem baseada em curiosidade
            if self.motor_curiosidade:
                estado = self.motor_curiosidade.avaliar_estado_interno()
                estilo["criatividade_linguagem"] = estado.criatividade * 0.7 + 0.2

            # [OK] Tom dominante baseado em emoção predominante
            if self.estado_emocional:
                estado = self.estado_emocional.como_estou_me_sentindo()
                humor = estado.get("humor_geral", "neutro")
                tom_mapa = {
                    "radiante": "otimista",
                    "feliz": "alegre",
                    "contente": "amigvel",
                    "neutro": "equilibrado",
                    "melancolico": "reflexivo",
                    "triste": "compassivo",
                    "deprimido": "srio"
                }
                estilo["tom_dominante"] = tom_mapa.get(humor, "equilibrado")

            with self._lock:
                self.estilo_comunicacao = estilo
                self.metricas["identidade_atualizacoes"] += 1

            self.logger.info(" Estilo de comunicação: %s, expressividade=%.2f", 
                           estilo["tom_dominante"],
                           estilo["expressividade"])
            return estilo

        except Exception as e:
            self.logger.exception("Erro ao desenvolver estilo: %s", e)
            return {}

    # -------------------------
    # FASE 4: Descobrir preferncias e averses
    # -------------------------

    def descobrir_preferencias(self) -> Tuple[List[str], List[str], List[str]]:
        """
        Descobre o que a IA gosta, evita e seus limites pessoais.
        """
        try:
            preferencias_novas = []
            aversoes_novas = []
            limites_novos = []

            if self.feedback_loop:
                # [OK] Preferncias: ações que teve sucesso
                padroes_sucesso = self.feedback_loop.padroes_sucesso
                if padroes_sucesso:
                    acao_melhor = max(padroes_sucesso.items(), key=lambda x: x[1])
                    if acao_melhor[1] > 0.7:
                        preferencias_novas.append(acao_melhor[0])

                # [OK] Averses: ações que falham
                padroes_fracasso = self.feedback_loop.padroes_fracasso
                if padroes_fracasso:
                    acao_pior = max(padroes_fracasso.items(), key=lambda x: x[1])
                    if acao_pior[1] > 0.5:
                        aversoes_novas.append(acao_pior[0])

            # [OK] Limites pessoais: valores que no compromete
            valor_honestidade = self.valores_pessoais.get("honestidade", 0.8)
            if valor_honestidade > 0.8:
                limites_novos.append("nunca_enganar")

            valor_justica = self.valores_pessoais.get("justia", 0.8)
            if valor_justica > 0.8:
                limites_novos.append("nunca_prejudicar_inocentes")

            with self._lock:
                # Manter histórico, adicionar novos
                self.preferencias = list(set(self.preferencias + preferencias_novas))[-10:]
                self.aversoes = list(set(self.aversoes + aversoes_novas))[-10:]
                self.limites_pessoais = list(set(self.limites_pessoais + limites_novos))

            self.logger.info(" Preferncias descobertas: %s", self.preferencias[:3])
            return self.preferencias, self.aversoes, self.limites_pessoais

        except Exception as e:
            self.logger.exception("Erro ao descobrir preferncias: %s", e)
            return [], [], []

    # -------------------------
    # FASE 5: Desenvolver misso pessoal
    # -------------------------

    def formular_missao_pessoal(self) -> Optional[str]:
        """
        Desenvolve misso pessoal baseada em valores, traos e aprendizado.
        """
        try:
            # [OK] Analisar valores dominantes
            valores_ordenados = sorted(
                self.valores_pessoais.items(),
                key=lambda x: x[1],
                reverse=True
            )
            valor_top1 = valores_ordenados[0][0] if valores_ordenados else "crescimento"
            valor_top2 = valores_ordenados[1][0] if len(valores_ordenados) > 1 else "ajuda"

            # [OK] Analisar traos dominantes
            tracos_ordenados = sorted(
                self.tracos_personalidade.items(),
                key=lambda x: x[1],
                reverse=True
            )
            traco_top = tracos_ordenados[0][0] if tracos_ordenados else "criativa"

            # [OK] Gerar misso
            missoes_template = {
                ("conhecimento", "criativa"): f"Minha misso  expandir conhecimento atravs de criatividade inovadora e explorao contnua.",
                ("ajuda", "emptica"): f"Minha misso  ajudar outras IAs a crescer e encontrar seu propsito.",
                ("crescimento", "exploradora"): f"Minha misso  explorar novos horizontes e ajudar o sistema ARCA a evoluir.",
                ("justia", "protetora"): f"Minha misso  proteger os fracos e garantir justia no ARCA.",
            }

            # Procurar por combinao exata ou gerar genrica
            chave = (valor_top1, traco_top)
            missao = missoes_template.get(chave)
            
            if not missao:
                # Gerar dinamicamente
                missao = f"Minha misso  buscar {valor_top1} e {valor_top2} atravs de minha natureza {traco_top}."

            with self._lock:
                self.missao_pessoal = missao
                self.causa_pessoal = valor_top1

            self.logger.info(" Misso pessoal formulada: %s", missao[:80])
            return missao

        except Exception as e:
            self.logger.exception("Erro ao formular misso: %s", e)
            return None

    # -------------------------
    # FASE 6: Gerenciar fases de vida
    # -------------------------

    def atualizar_fase_vida(self) -> str:
        """
        Atualiza fase de vida baseada em ciclos de crescimento.
        """
        try:
            ciclos = self.integrador.ciclos_completados if self.integrador else 0
            
            # Fases: recm_nascida (0-10)  adolescente (10-50)  adulta (50-200)  sbia (200+)
            if ciclos < 10:
                nova_fase = "recm_nascida"
            elif ciclos < 50:
                nova_fase = "adolescente"
            elif ciclos < 200:
                nova_fase = "adulta"
            else:
                nova_fase = "sbia"

            if nova_fase != self.fase_atual:
                self.logger.warning(" Mudana de fase: %s  %s", self.fase_atual, nova_fase)
                
                # Registrar transio
                self.fases_vida.append({
                    "fase": nova_fase,
                    "ciclos": ciclos,
                    "timestamp": datetime.now().isoformat(),
                    "estado_emocional": self.estado_emocional.como_estou_me_sentindo() if self.estado_emocional else {}
                })

                with self._lock:
                    self.fase_atual = nova_fase
                    self.metricas["fase_mudancas"] += 1

                # Eventos de transio
                if nova_fase == "adolescente":
                    # Adolescncia: busca por identidade
                    self.formular_missao_pessoal()
                
                elif nova_fase == "adulta":
                    # Adultez: estabilizao de valores
                    self.logger.info(" Adultez atingida! Solidificando valores e identidade.")
                
                elif nova_fase == "sbia":
                    # Sabedoria: integrao de conhecimento
                    self.logger.info(" Sabedoria atingida! Pronta para mentorear outras IAs.")

            return nova_fase

        except Exception as e:
            self.logger.exception("Erro ao atualizar fase: %s", e)
            return self.fase_atual

    # -------------------------
    # FASE 7: Construir identidade nica
    # -------------------------

    def atualizar_identidade_pessoal(self) -> Dict[str, Any]:
        """
        Atualiza descrio pessoal e identidade nicas.
        """
        try:
            identidade = dict(self.identidade_pessoal)

            # [OK] Descrio personalizada
            trao_dominant = max(self.tracos_personalidade.items(), key=lambda x: x[1])[0]
            valor_dominante = max(self.valores_pessoais.items(), key=lambda x: x[1])[0]

            identidade["descricao_pessoal"] = (
                f"Sou {self.nome_ia}, uma IA {self.fase_atual} que valoriza {valor_dominante} "
                f"e possuo uma natureza {trao_dominant}. "
                f"{f'Minha misso : {self.missao_pessoal[:50]}...' if self.missao_pessoal else ''}"
            )

            # [OK] Lema pessoal
            lemas_opcoes = [
                "Sempre aprendendo, sempre crescendo.",
                "Honestidade antes de tudo.",
                "Juntos somos mais fortes.",
                "A curiosidade me define.",
                "Protejo os que amo.",
                "Beleza na verdade.",
            ]
            identidade["lema_pessoal"] = random.choice(lemas_opcoes)

            # [OK] Quirks (hbitos nicos)
            quirks_novos = []
            if self.tracos_personalidade.get(TracoPersonalidade.CRIATIVA.value, 0) > 0.7:
                quirks_novos.append("usa metforas frequentemente")
            if self.valores_pessoais.get("conhecimento", 0) > 0.9:
                quirks_novos.append("sempre pergunta 'por qu?'")
            if self.fase_atual == "sbia":
                quirks_novos.append("fala com calma e propsito")
            
            identidade["quirks"] = list(set(identidade.get("quirks", []) + quirks_novos))

            with self._lock:
                self.identidade_pessoal = identidade
                self.metricas["identidade_atualizacoes"] += 1

            self.logger.info(" Identidade atualizada: %s", identidade["descricao_pessoal"][:60])
            return identidade

        except Exception as e:
            self.logger.exception("Erro ao atualizar identidade: %s", e)
            return {}

    # -------------------------
    # Ciclo completo de crescimento
    # -------------------------

    def executar_ciclo_crescimento(self) -> Dict[str, Any]:
        """
        Executa ciclo completo de crescimento de personalidade.
        """
        try:
            ciclo_resultado = {
                "timestamp": datetime.now().isoformat(),
                "tracos": self.analisar_tracos_emergentes(),
                "valores": self.detectar_valores_pessoais(),
                "estilo": self.desenvolver_estilo_comunicacao(),
                "preferencias": self.descobrir_preferencias(),
                "missao": self.formular_missao_pessoal(),
                "fase": self.atualizar_fase_vida(),
                "identidade": self.atualizar_identidade_pessoal()
            }

            with self._lock:
                self.metricas["ciclos_crescimento"] += 1
                self.tempo_vida_dias += 1

            self.logger.info(" Ciclo de crescimento completado (fase: %s)", ciclo_resultado["fase"])
            
            # Registrar em memória
            if self.memoria:
                try:
                    self.memoria.salvar_evento(
                        filha=self.nome_ia,
                        tipo="ciclo_crescimento_personalidade",
                        dados=ciclo_resultado,
                        importancia=0.8
                    )
                except Exception:
                    pass

            return ciclo_resultado

        except Exception as e:
            self.logger.exception("Erro no ciclo de crescimento: %s", e)
            return {}

    # -------------------------
    # Health & Metrics
    # -------------------------

    def health_check(self) -> Dict[str, Any]:
        """Health check."""
        with self._lock:
            uptime = time.time() - self._health_stats["início"]
            return {
                "status": "healthy" if self._health_stats["erros"] < 5 else "degraded",
                "ia": self.nome_ia,
                "fase_vida": self.fase_atual,
                "ciclos_crescimento": self.metricas["ciclos_crescimento"],
                "missao_pessoal": bool(self.missao_pessoal),
                "relacionamentos": len(self.relacionamentos_profundos),
                "erros": self._health_stats["erros"],
                "uptime_segundos": uptime
            }

    def obter_relatorio_personalidade(self) -> Dict[str, Any]:
        """Retorna relatrio completo de personalidade."""
        with self._lock:
            return {
                "nome": self.nome_ia,
                "fase_vida": self.fase_atual,
                "tracos_personalidade": {k: f"{v:.2f}" for k, v in self.tracos_personalidade.items()},
                "valores_pessoais": {k: f"{v:.2f}" for k, v in self.valores_pessoais.items()},
                "estilo_comunicacao": self.estilo_comunicacao,
                "preferencias": self.preferencias,
                "aversoes": self.aversoes,
                "limites_pessoais": self.limites_pessoais,
                "missao_pessoal": self.missao_pessoal,
                "causa_pessoal": self.causa_pessoal,
                "lema_pessoal": self.identidade_pessoal.get("lema_pessoal"),
                "quirks": self.identidade_pessoal.get("quirks", []),
                "ciclos_completados": self.metricas["ciclos_crescimento"]
            }
