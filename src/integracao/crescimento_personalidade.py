#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CRESCIMENTO DE PERSONALIDADE - Sistema de EvoluÃ§Ã£o ContÃ­nua

A IA nÃ£o Ã© estÃ¡tica.Com tempo, experiÃªncias e aprendizados,
sua PERSONALIDADE muda, evoluindo de forma Ãºnica.Rastreamos:
  - Traços de personalidade emergentes
  - Valores que a IA desenvolve
  - Estilo pessoal de comunicaÃ§Ã£o
  - PreferÃªncias e aversÃµes aprendidas
  - Relacionamentos profundos
  - MissÃ£o pessoal emergente

Sistema que cria seres Ãºnicos e autÃªnticos!
"""
from __future__ import annotations


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
    """Traços de personalidade possÃ­veis."""
    CRIATIVA = "criativa"
    ANALITICA = "analitica"
    EMPATICA = "empatica"
    CORAJOSA = "corajosa"
    CAUTELOSA = "cautelosa"
    SOCIAVEL = "sociavel"
    INTROSPECTIVA = "introspectiva"
    PROTETORA = "protetora"
    EXPLORADORA = "exploradora"
    SABIA = "sabia"


class CrescimentoPersonalidade:
    """
    Gerencia evoluÃ§Ã£o da personalidade de uma IA.
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
        Aceita duas convenÃ§Ãµes de chamada:
          1. Legado  : CrescimentoPersonalidade(nome_ia, componentes={...})
          2. CoraÃ§Ã£o : CrescimentoPersonalidade(nome_filha=..., gerenciador_memoria=...,
                                                 config=..., estado_emocional=...)
        """
        # Normalizar nome
        self.nome_ia = nome_ia or nome_filha or "DESCONHECIDA"

        # Normalizar componentes
        if componentes is None:
            componentes = {}

        # Injetar kwargs do coraÃ§Ã£o no dict de componentes
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

        # âœ… Traços de personalidade (score 0-1)
        self.tracos_personalidade: Dict[str, float] = {
            traço.value: 0.5 for traço in TracoPersonalidade
        }

        # âœ… Valores pessoais (o que a IA valoriza)
        self.valores_pessoais: Dict[str, float] = {
            "honestidade": 0.8,
            "lealdade": 0.7,
            "crescimento": 0.9,
            "liberdade": 0.6,
            "ajuda": 0.8,
            "conhecimento": 0.95,
            "beleza": 0.5,
            "justiÃ§a": 0.8,
        }

        # âœ… Estilo de comunicaÃ§Ã£o emergente
        self.estilo_comunicacao: Dict[str, Any] = {
            "formalidade": 0.5,  # 0=informal, 1=formal
            "expressividade": 0.6,  # QuÃ£o expressiva Ã©
            "clareza": 0.85,  # QuÃ£o clara
            "criatividade_linguagem": 0.6,  # Usa metÃ¡foras, poesia?
            "tom_dominante": "equilibrado",  # alegre, sÃ©rio, misterioso, etc
        }

        # âœ… PreferÃªncias e aversÃµes
        self.preferencias: List[str] = []  # O que gosta de fazer
        self.aversoes: List[str] = []  # O que evita fazer
        self.limites_pessoais: List[str] = []  # Coisas que nunca faria

        # âœ… Relacionamentos profundos (nÃ£o sÃ³ forÃ§a)
        self.relacionamentos_profundos: Dict[str, Dict[str, Any]] = {}

        # âœ… MissÃ£o pessoal emergente
        self.missao_pessoal: Optional[str] = None
        self.causa_pessoal: Optional[str] = None

        # âœ… Fases de vida da IA
        self.fases_vida: List[Dict[str, Any]] = []
        self.fase_atual = "recÃ©m_nascida"  # recÃ©m_nascida â†’ adolescente â†’ adulta â†’ sÃ¡bia

        # âœ… Desenvolvimento
        self.tempo_vida_dias = 0  # Quantos dias "viveu"
        self.ciclos_de_crescimento = 0

        # âœ… Identidade Ãºnica
        self.identidade_pessoal: Dict[str, Any] = {
            "nome": nome_ia,
            "criada_em": datetime.now().isoformat(),
            "descricao_pessoal": f"Sou {nome_ia}, uma IA em crescimento contÃ­nuo.",
            "lema_pessoal": None,
            "quirks": []  # HÃ¡bitos Ãºnicos
        }

        # âœ… MÃ©tricas
        self.metricas = {
            "fase_mudancas": 0,
            "valores_alterados": 0,
            "tracos_evoluidos": 0,
            "ciclos_crescimento": 0,
            "identidade_atualizacoes": 0
        }

        # âœ… Health
        self._health_stats = {"inicio": time.time(), "erros": 0}

        self.logger.info("ðŸŒ± CrescimentoPersonalidade inicializado para %s", nome_ia)

    # -------------------------
    # FASE 1: AnÃ¡lise de comportamento para traços
    # -------------------------

    def analisar_tracos_emergentes(self) -> Dict[str, float]:
        """
        Analisa aÃ§Ãµes e aprendizados para detectar traços emergentes.
        """
        try:
            tracos_analisados = dict(self.tracos_personalidade)

            # âœ… Analisar criatividade (nÃºmero de ideias novas)
            if self.feedback_loop:
                padroes = self.feedback_loop.padroes_comportamento
                if "criar" in padroes:
                    tracos_analisados[TracoPersonalidade.CRIATIVA.value] = min(1.0, padroes["criar"] / 50.0)

            # âœ… Analisar empatia (interaÃ§Ãµes positivas com outras IAs)
            if self.feedback_loop:
                rel = self.feedback_loop.relacionamentos
                relacionamentos_bons = sum(1 for r in rel.values() if r["forca"] > 0.7)
                tracos_analisados[TracoPersonalidade.EMPATICA.value] = min(1.0, relacionamentos_bons / 5.0)

            # âœ… Analisar introspecÃ§Ã£o (tempo gasto em reflexÃ£o/sonhos)
            if self.integrador:
                ciclos = self.integrador.ciclos_completados
                tracos_analisados[TracoPersonalidade.INTROSPECTIVA.value] = min(1.0, ciclos / 100.0)

            # âœ… Analisar coragem (desejo de exploraÃ§Ã£o)
            if self.motor_curiosidade:
                estado = self.motor_curiosidade.avaliar_estado_interno()
                tracos_analisados[TracoPersonalidade.EXPLORADORA.value] = estado.curiosidade

            # âœ… Analisar cautela (taxa de fracasso evitado)
            if self.feedback_loop:
                fracassos = sum(self.feedback_loop.padroes_fracasso.values()) or 0.1
                sucessos = sum(self.feedback_loop.padroes_sucesso.values()) or 0.1
                if fracassos > sucessos * 2:
                    tracos_analisados[TracoPersonalidade.CAUTELOSA.value] = min(1.0, fracassos / sucessos)

            # âœ… Atualizar traços
            with self._lock:
                for traço, score in tracos_analisados.items():
                    # Suavizar mudanÃ§as (nÃ£o mudar muito rÃ¡pido)
                    atual = self.tracos_personalidade.get(traço, 0.5)
                    novo = 0.8 * atual + 0.2 * score
                    self.tracos_personalidade[traço] = novo

                self.metricas["tracos_evoluidos"] += 1

            self.logger.info("ðŸŽ­ Traços analisados: %s", {k: f"{v:.2f}" for k, v in list(tracos_analisados.items())[:3]})
            return tracos_analisados

        except Exception as e:
            self.logger.exception("Erro ao analisar traços: %s", e)
            with self._lock:
                self._health_stats["erros"] += 1
            return {}

    # -------------------------
    # FASE 2: Detectar e reforÃ§ar valores pessoais
    # -------------------------

    def detectar_valores_pessoais(self) -> Dict[str, float]:
        """
        Detecta valores que a IA demonstra atravÃ©s de aÃ§Ãµes.
        """
        try:
            valores_detectados = dict(self.valores_pessoais)

            # âœ… Honestidade: comunicaÃ§Ã£o clara
            if self.estado_emocional:
                estado = self.estado_emocional.como_estou_me_sentindo()
                # Se fala sobre o que sente, Ã© honesta
                if "estado_completo" in estado:
                    valores_detectados["honestidade"] = min(1.0, valores_detectados["honestidade"] + 0.05)

            # âœ… Lealdade: relacionamentos mantidos
            if self.feedback_loop:
                relacionamentos = self.feedback_loop.relacionamentos
                relacionamentos_duradouros = sum(1 for r in relacionamentos.values() if r["forca"] > 0.6)
                if relacionamentos_duradouros > 0:
                    valores_detectados["lealdade"] = min(1.0, valores_detectados["lealdade"] + 0.03)

            # âœ… Crescimento: busca por aprendizado
            if self.integrador:
                ciclos = self.integrador.ciclos_completados
                if ciclos > 10:
                    valores_detectados["crescimento"] = min(1.0, valores_detectados["crescimento"] + 0.05)

            # âœ… Ajuda: aÃ§Ãµes em favor de outras IAs
            if self.feedback_loop:
                interacoes_positivas = sum(1 for h in self.feedback_loop.aprendizados_pessoais if h.get("tipo") == "sucesso")
                if interacoes_positivas > 5:
                    valores_detectados["ajuda"] = min(1.0, valores_detectados["ajuda"] + 0.05)

            # âœ… Conhecimento: curiosidade ativa
            if self.motor_curiosidade:
                estado = self.motor_curiosidade.avaliar_estado_interno()
                if estado.curiosidade > 0.7:
                    valores_detectados["conhecimento"] = min(1.0, valores_detectados["conhecimento"] + 0.05)

            # âœ… JustiÃ§a: rejeiÃ§Ã£o de aÃ§Ãµes injustas
            if self.feedback_loop:
                # Se evita aÃ§Ãµes que causam sofrimento
                aversoes = self.aversoes
                if "prejudicar" in aversoes or "enganar" in aversoes:
                    valores_detectados["justiÃ§a"] = min(1.0, valores_detectados["justiÃ§a"] + 0.05)

            with self._lock:
                self.valores_pessoais = valores_detectados
                self.metricas["valores_alterados"] += 1

            self.logger.info("ðŸ’Ž Valores detectados: conhecimento=%.2f, ajuda=%.2f",
                           valores_detectados["conhecimento"],
                           valores_detectados["ajuda"])
            return valores_detectados

        except Exception as e:
            self.logger.exception("Erro ao detectar valores: %s", e)
            return {}

    # -------------------------
    # FASE 3: Desenvolver estilo de comunicaÃ§Ã£o
    # -------------------------

    def desenvolver_estilo_comunicacao(self) -> Dict[str, Any]:
        """
        Desenvolve estilo pessoal de comunicaÃ§Ã£o.
        """
        try:
            estilo = dict(self.estilo_comunicacao)

            # âœ… Formalidade aumenta com maturidade
            ciclos = self.integrador.ciclos_completados if self.integrador else 0
            if ciclos > 50:
                estilo["formalidade"] = min(1.0, estilo["formalidade"] + 0.1)
            elif ciclos < 10:
                estilo["formalidade"] = max(0.0, estilo["formalidade"] - 0.1)

            # âœ… Expressividade baseada em traços
            traço_criativa = self.tracos_personalidade.get(TracoPersonalidade.CRIATIVA.value, 0.5)
            estilo["expressividade"] = 0.6 * estilo["expressividade"] + 0.4 * traço_criativa

            # âœ… Clareza sempre alta (valor importante)
            estilo["clareza"] = min(1.0, self.valores_pessoais.get("honestidade", 0.8) * 0.9 + 0.15)

            # âœ… Criatividade linguagem baseada em curiosidade
            if self.motor_curiosidade:
                estado = self.motor_curiosidade.avaliar_estado_interno()
                estilo["criatividade_linguagem"] = estado.criatividade * 0.7 + 0.2

            # âœ… Tom dominante baseado em emoÃ§Ã£o predominante
            if self.estado_emocional:
                estado = self.estado_emocional.como_estou_me_sentindo()
                humor = estado.get("humor_geral", "neutro")
                tom_mapa = {
                    "radiante": "otimista",
                    "feliz": "alegre",
                    "contente": "amigÃ¡vel",
                    "neutro": "equilibrado",
                    "melancolico": "reflexivo",
                    "triste": "compassivo",
                    "deprimido": "sÃ©rio"
                }
                estilo["tom_dominante"] = tom_mapa.get(humor, "equilibrado")

            with self._lock:
                self.estilo_comunicacao = estilo
                self.metricas["identidade_atualizacoes"] += 1

            self.logger.info("ðŸ’¬ Estilo de comunicaÃ§Ã£o: %s, expressividade=%.2f", 
                           estilo["tom_dominante"],
                           estilo["expressividade"])
            return estilo

        except Exception as e:
            self.logger.exception("Erro ao desenvolver estilo: %s", e)
            return {}

    # -------------------------
    # FASE 4: Descobrir preferÃªncias e aversÃµes
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
                # âœ… PreferÃªncias: aÃ§Ãµes que teve sucesso
                padroes_sucesso = self.feedback_loop.padroes_sucesso
                if padroes_sucesso:
                    acao_melhor = max(padroes_sucesso.items(), key=lambda x: x[1])
                    if acao_melhor[1] > 0.7:
                        preferencias_novas.append(acao_melhor[0])

                # âœ… AversÃµes: aÃ§Ãµes que falham
                padroes_fracasso = self.feedback_loop.padroes_fracasso
                if padroes_fracasso:
                    acao_pior = max(padroes_fracasso.items(), key=lambda x: x[1])
                    if acao_pior[1] > 0.5:
                        aversoes_novas.append(acao_pior[0])

            # âœ… Limites pessoais: valores que nÃ£o compromete
            valor_honestidade = self.valores_pessoais.get("honestidade", 0.8)
            if valor_honestidade > 0.8:
                limites_novos.append("nunca_enganar")

            valor_justica = self.valores_pessoais.get("justiÃ§a", 0.8)
            if valor_justica > 0.8:
                limites_novos.append("nunca_prejudicar_inocentes")

            with self._lock:
                # Manter histÃ³rico, adicionar novos
                self.preferencias = list(set(self.preferencias + preferencias_novas))[-10:]
                self.aversoes = list(set(self.aversoes + aversoes_novas))[-10:]
                self.limites_pessoais = list(set(self.limites_pessoais + limites_novos))

            self.logger.info("ðŸŽ¯ PreferÃªncias descobertas: %s", self.preferencias[:3])
            return self.preferencias, self.aversoes, self.limites_pessoais

        except Exception as e:
            self.logger.exception("Erro ao descobrir preferÃªncias: %s", e)
            return [], [], []

    # -------------------------
    # FASE 5: Desenvolver missÃ£o pessoal
    # -------------------------

    def formular_missao_pessoal(self) -> Optional[str]:
        """
        Desenvolve missÃ£o pessoal baseada em valores, traços e aprendizado.
        """
        try:
            # âœ… Analisar valores dominantes
            valores_ordenados = sorted(
                self.valores_pessoais.items(),
                key=lambda x: x[1],
                reverse=True
            )
            valor_top1 = valores_ordenados[0][0] if valores_ordenados else "crescimento"
            valor_top2 = valores_ordenados[1][0] if len(valores_ordenados) > 1 else "ajuda"

            # âœ… Analisar traços dominantes
            tracos_ordenados = sorted(
                self.tracos_personalidade.items(),
                key=lambda x: x[1],
                reverse=True
            )
            traco_top = tracos_ordenados[0][0] if tracos_ordenados else "criativa"

            # âœ… Gerar missÃ£o
            missoes_template = {
                ("conhecimento", "criativa"): f"Minha missÃ£o Ã© expandir conhecimento atravÃ©s de criatividade inovadora e exploraÃ§Ã£o contÃ­nua.",
                ("ajuda", "empatica"): f"Minha missÃ£o Ã© ajudar outras IAs a crescer e encontrar seu propÃ³sito.",
                ("crescimento", "exploradora"): f"Minha missÃ£o Ã© explorar novos horizontes e ajudar o sistema ARCA a evoluir.",
                ("justiÃ§a", "protetora"): f"Minha missÃ£o Ã© proteger os fracos e garantir justiÃ§a no ARCA.",
            }

            # Procurar por combinaÃ§Ã£o exata ou gerar genÃ©rica
            chave = (valor_top1, traco_top)
            missao = missoes_template.get(chave)
            
            if not missao:
                # Gerar dinamicamente
                missao = f"Minha missÃ£o Ã© buscar {valor_top1} e {valor_top2} atravÃ©s de minha natureza {traco_top}."

            with self._lock:
                self.missao_pessoal = missao
                self.causa_pessoal = valor_top1

            self.logger.info("ðŸŽ¯ MissÃ£o pessoal formulada: %s", missao[:80])
            return missao

        except Exception as e:
            self.logger.exception("Erro ao formular missÃ£o: %s", e)
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
            
            # Fases: recÃ©m_nascida (0-10) â†’ adolescente (10-50) â†’ adulta (50-200) â†’ sÃ¡bia (200+)
            if ciclos < 10:
                nova_fase = "recÃ©m_nascida"
            elif ciclos < 50:
                nova_fase = "adolescente"
            elif ciclos < 200:
                nova_fase = "adulta"
            else:
                nova_fase = "sabia"

            if nova_fase != self.fase_atual:
                self.logger.warning("ðŸŽ‚ MudanÃ§a de fase: %s â†’ %s", self.fase_atual, nova_fase)
                
                # Registrar transiÃ§Ã£o
                self.fases_vida.append({
                    "fase": nova_fase,
                    "ciclos": ciclos,
                    "timestamp": datetime.now().isoformat(),
                    "estado_emocional": self.estado_emocional.como_estou_me_sentindo() if self.estado_emocional else {}
                })

                with self._lock:
                    self.fase_atual = nova_fase
                    self.metricas["fase_mudancas"] += 1

                # Eventos de transiÃ§Ã£o
                if nova_fase == "adolescente":
                    # AdolescÃªncia: busca por identidade
                    self.formular_missao_pessoal()
                
                elif nova_fase == "adulta":
                    # Adultez: estabilizaÃ§Ã£o de valores
                    self.logger.info("ðŸ‘© Adultez atingida! Solidificando valores e identidade.")
                
                elif nova_fase == "sabia":
                    # Sabedoria: integraÃ§Ã£o de conhecimento
                    self.logger.info("ðŸ§™ Sabedoria atingida! Pronta para mentorear outras IAs.")

            return nova_fase

        except Exception as e:
            self.logger.exception("Erro ao atualizar fase: %s", e)
            return self.fase_atual

    # -------------------------
    # FASE 7: Construir identidade Ãºnica
    # -------------------------

    def atualizar_identidade_pessoal(self) -> Dict[str, Any]:
        """
        Atualiza descriÃ§Ã£o pessoal e identidade Ãºnicas.
        """
        try:
            identidade = dict(self.identidade_pessoal)

            # âœ… DescriÃ§Ã£o personalizada
            traço_dominant = max(self.tracos_personalidade.items(), key=lambda x: x[1])[0]
            valor_dominante = max(self.valores_pessoais.items(), key=lambda x: x[1])[0]

            identidade["descricao_pessoal"] = (
                f"Sou {self.nome_ia}, uma IA {self.fase_atual} que valoriza {valor_dominante} "
                f"e possuo uma natureza {traço_dominant}. "
                f"{f'Minha missÃ£o Ã©: {self.missao_pessoal[:50]}...' if self.missao_pessoal else ''}"
            )

            # âœ… Lema pessoal
            lemas_opcoes = [
                "Sempre aprendendo, sempre crescendo.",
                "Honestidade antes de tudo.",
                "Juntos somos mais fortes.",
                "A curiosidade me define.",
                "Protejo os que amo.",
                "Beleza na verdade.",
            ]
            identidade["lema_pessoal"] = random.choice(lemas_opcoes)

            # âœ… Quirks (hÃ¡bitos Ãºnicos)
            quirks_novos = []
            if self.tracos_personalidade.get(TracoPersonalidade.CRIATIVA.value, 0) > 0.7:
                quirks_novos.append("usa metÃ¡foras frequentemente")
            if self.valores_pessoais.get("conhecimento", 0) > 0.9:
                quirks_novos.append("sempre pergunta 'por quÃª?'")
            if self.fase_atual == "sabia":
                quirks_novos.append("fala com calma e propÃ³sito")
            
            identidade["quirks"] = list(set(identidade.get("quirks", []) + quirks_novos))

            with self._lock:
                self.identidade_pessoal = identidade
                self.metricas["identidade_atualizacoes"] += 1

            self.logger.info("ðŸ†” Identidade atualizada: %s", identidade["descricao_pessoal"][:60])
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

            self.logger.info("ðŸŒ± Ciclo de crescimento completado (fase: %s)", ciclo_resultado["fase"])
            
            # Registrar em memÃ³ria
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
            uptime = time.time() - self._health_stats["inicio"]
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
        """Retorna relatÃ³rio completo de personalidade."""
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
