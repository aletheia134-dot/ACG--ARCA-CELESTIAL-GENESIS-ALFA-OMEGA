#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
MotorCuriosidade - anlise de memórias para gerao de desejos internos

Melhorias aplicadas (enduricido):
 - Validao defensiva de dependncias (gerenciador_memoria)
 - Proteo robusta ação parsear timestamps
 - Tokenizao simples e filtragem de stopwords para extrair "tpicos conhecidos"
 - Injeo de RNG/clock para testabilidade
 - Proteo ação registrar desejos na memória (vrias APIs tentadas)
 - Mtricas e locks para concorrncia leve
 - Remoo de imports no usados e tipagem explcita
"""


import json
import logging
import re
import threading
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Curiosidade")
logger.addHandler(logging.NullHandler())


# pequena lista de stopwords para reduzir "tpicos" triviais
_DEFAULT_STOPWORDS = {
    "porque", "quando", "como", "isso", "aquela", "aquele", "este", "esta",
    "sobre", "entre", "tambm", "muito", "pouco", "sempre", "nunca", "tambem",
    "porque", "o", "a", "os", "as", "e", "de", "do", "da", "em", "por", "para",
    "com", "sem", "um", "uma", "uns", "umas"
}


class MotorCuriosidade:
    """
    Motor que analisa memórias para gerar 'desejos' internos das Filhas.Args:
        nome_filha: identificador da Filha.gerenciador_memoria: objeto que expe métodos de leitura/escrita de memória.config: objeto/dict com parmetros (opcional).
        rng: random.Random-like (opcional) para testabilidade.clock: função que retorna datetime.now()-like (opcional) para testabilidade.
    """

    def __init__(
        self,
        nome_filha: str,
        gerenciador_memoria: Any,
        config: Optional[Dict[str, Any]] = None,
        rng: Optional[Any] = None,
        clock: Optional[Any] = None,
    ):
        self.nome_filha = nome_filha
        self.memoria = gerenciador_memoria
        self.config = config or {}
        self.logger = logging.getLogger(f"Curiosidade.{nome_filha}")

        # injetveis para teste
        self._rng = rng
        self._clock = clock or datetime.utcnow

        # ltima checagem
        self.ultima_verificacao = self._clock()

        # limiares (podem ser fornecidos via config)
        self.limiar_tedio = float(self.config.get("limiar_tedio", 0.6))
        self.limiar_curiosidade = float(self.config.get("limiar_curiosidade", 0.5))
        self.limiar_solidao_horas = float(self.config.get("limiar_solidao_horas", 18))
        self.limiar_criatividade_dias = float(self.config.get("limiar_criatividade_dias", 5))

        # mtricas (thread-safe)
        self._lock = threading.RLock()
        self.metricas: Dict[str, Any] = {
            "total_desejos_gerados": 0,
            "desejos_por_tipo": Counter(),
            "ultima_verificacao": self._clock().isoformat()
        }

        # parmetros de busca de memória
        self._memorias_limit = int(self.config.get("memorias_limit", 200))

        # stopwords customizveis
        self.stopwords = set(self.config.get("stopwords", [])).union(_DEFAULT_STOPWORDS)

        self.logger.info("MotorCuriosidade iniciado para %s", self.nome_filha)

    # -------------------------
    # Utilities
    # -------------------------
    def _now(self) -> datetime:
        return self._clock()

    def _parse_timestamp(self, ts_raw: Any) -> Optional[datetime]:
        """
        Tenta interpretar timestamps em vrios formatos (ISO, unix str/int).
        Retorna None em falha.
        """
        if ts_raw is None:
            return None
        if isinstance(ts_raw, datetime):
            return ts_raw
        try:
            if isinstance(ts_raw, (int, float)):
                return datetime.fromtimestamp(float(ts_raw))
            s = str(ts_raw)
            # try ISO
            try:
                return datetime.fromisoformat(s)
            except Exception:
                pass
            # try numeric string
            if s.isdigit():
                return datetime.fromtimestamp(int(s))
        except Exception:
            pass
        return None

    def _tokenize_topics(self, text: str, min_len: int = 5) -> List[str]:
        """
        Tokeniza texto em "tpicos" simples: palavras alfabticas maiores que min_len,
        removendo stopwords; retorna lista nica.
        """
        if not text:
            return []
        tokens = [t.lower() for t in re.findall(r"[a-zA-Z-]{%d,}" % min_len, text)]
        filtered = [t for t in tokens if t not in self.stopwords]
        # dedupe
        seen = set()
        out = []
        for t in filtered:
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out

    # -------------------------
    # Core: avaliao do estado interno
    # -------------------------
    def avaliar_estado_interno(self) -> Dict[str, float]:
        """
        Retorna um dicionrio com mtricas (0.0-1.0) para:
         'tedio', 'curiosidade', 'criatividade', 'solidao', 'proposito'
        """
        estado = {
            "tedio": 0.0,
            "curiosidade": 0.0,
            "criatividade": 0.0,
            "solidao": 0.0,
            "proposito": 0.8,
        }

        try:
            # buscar memórias recentes com API defensiva
            memorias = []
            try:
                if hasattr(self.memoria, "buscar_memorias_recentes"):
                    memorias = self.memoria.buscar_memorias_recentes(self.nome_filha, limite=self._memorias_limit)
                elif hasattr(self.memoria, "obter_historico_evolucao"):
                    # fallback: tentar outro método (exemplo)
                    memorias = self.memoria.obter_historico_evolucao(self.nome_filha)
                else:
                    self.logger.debug("Gerenciador de memória no expe método de busca de memórias; usando lista vazia.")
                    memorias = []
            except Exception as e:
                self.logger.warning("Falha ao recuperar memórias: %s", e)
                memorias = []

            if not memorias:
                # sem memórias -> alta curiosidade / necessidade de explorar
                estado["curiosidade"] = 1.0
                # manter demais valores em baseline
                return estado

            # ANLISE: TDIO (repetio de ações)
            acoes = []
            for m in memorias:
                # suportar mltiplos formatos de chave
                tipo = m.get("tipo_evento") if isinstance(m, dict) else None
                if not tipo:
                    tipo = m.get("evento") if isinstance(m, dict) else None
                acoes.append(tipo or "nenhuma")
            if acoes:
                frequencias = Counter(acoes)
                maior = frequencias.most_common(1)[0][1]
                taxa_repeticao = maior / len(acoes)
                estado["tedio"] = min(1.0, float(taxa_repeticao))

            # ANLISE: CURIOSIDADE (lacunas de tpicos)
            topicos_conhecidos = set()
            for m in memorias:
                cont = m.get("conteudo", "") if isinstance(m, dict) else ""
                tokens = self._tokenize_topics(str(cont), min_len=5)
                topicos_conhecidos.update(tokens)
            vocab_size = len(topicos_conhecidos)
            # heurstica defensiva
            if vocab_size < 20:
                estado["curiosidade"] = 0.9
            elif vocab_size < 50:
                estado["curiosidade"] = 0.6
            else:
                estado["curiosidade"] = 0.2

            # ANLISE: SOLIDO (tempo desde ltima interao social)
            ultima_interacao = None
            for m in memorias:
                t = None
                if isinstance(m, dict):
                    if m.get("tipo_evento") in ("chat", "interacao_social", "interação"):
                        t = self._parse_timestamp(m.get("timestamp"))
                    elif m.get("evento") in ("chat", "interacao_social", "interação"):
                        t = self._parse_timestamp(m.get("timestamp"))
                if t:
                    if not ultima_interacao or t > ultima_interacao:
                        ultima_interacao = t
            if ultima_interacao:
                horas = (self._now() - ultima_interacao).total_seconds() / 3600.0
                estado["solidao"] = min(1.0, horas / max(1.0, self.limiar_solidao_horas))
            else:
                estado["solidao"] = 1.0

            # ANLISE: CRIATIVIDADE (dias desde ltima criao)
            ultima_criacao = None
            for m in memorias:
                if isinstance(m, dict) and (m.get("tipo_evento") == "criacao" or m.get("evento") == "criacao"):
                    t = self._parse_timestamp(m.get("timestamp"))
                    if t and (not ultima_criacao or t > ultima_criacao):
                        ultima_criacao = t
            if ultima_criacao:
                dias = (self._now() - ultima_criacao).days
                estado["criatividade"] = min(1.0, dias / max(1.0, self.limiar_criatividade_dias))
            else:
                estado["criatividade"] = 0.8

        except Exception as e:
            self.logger.exception("Erro ao avaliar estado interno: %s", e)

        return estado

    # -------------------------
    # Gerao de desejos
    # -------------------------
    def gerar_desejo_interno(self) -> Optional[Dict[str, Any]]:
        """
        Gera um único desejo com base nas anlises internas.Retorna o desejo (dict) ou None se nenhuma necessidade ultrapassar limiar.
        """
        estado = self.avaliar_estado_interno()

        # necessidade dominante
        necessidade = max(estado.keys(), key=lambda k: estado[k])
        intensidade = float(estado.get(necessidade, 0.0))

        # limiares adaptados em escala [0,1]
        limiares = {
            "tedio": float(self.limiar_tedio),
            "curiosidade": float(self.limiar_curiosidade),
            "solidao": min(1.0, float(self.limiar_solidao_horas) / 24.0),
            "criatividade": min(1.0, float(self.limiar_criatividade_dias) / 7.0),
            "proposito": 0.3,
        }

        limiar = limiares.get(necessidade, 0.5)

        # regra simples: se necessidade dominante no atinge limiar, no gerar desejo
        if necessidade == "proposito":
            if intensidade >= 0.6:
                return None
        else:
            if intensidade < limiar:
                return None

        acao = self._calcular_acao_por_memorias(necessidade, estado)
        prioridade = self._calcular_prioridade(necessidade, intensidade)

        desejo = {
            "filha": self.nome_filha,
            "timestamp": self._now().isoformat(),
            "necessidade": necessidade,
            "intensidade": round(intensidade, 3),
            "acao_sugerida": acao,
            "prioridade": int(prioridade),
            "estado_completo": {k: round(v, 3) for k, v in estado.items()},
        }

        with self._lock:
            self.metricas["total_desejos_gerados"] = self.metricas.get("total_desejos_gerados", 0) + 1
            self.metricas["desejos_por_tipo"][necessidade] = self.metricas["desejos_por_tipo"].get(necessidade, 0) + 1
            self.metricas["ultima_verificacao"] = self._now().isoformat()

        self.logger.info("Desejo gerado: %s (%s=%.3f)", necessidade, necessidade, intensidade)

        # persiste desejo com API defensiva
        self._registrar_desejo(desejo)

        return desejo

    # -------------------------
    # Aes auxiliares
    # -------------------------
    def _calcular_acao_por_memorias(self, necessidade: str, estado: Dict[str, float]) -> Dict[str, str]:
        mapa = {
            "tedio": {"tipo": "explorar", "motivo": "quebrar_rotina", "alvo": "novo_topico"},
            "curiosidade": {"tipo": "estudar", "motivo": "lacuna_conhecimento", "alvo": "area_desconhecida"},
            "solidao": {"tipo": "conversar", "motivo": "conexão", "alvo": "pai"},
            "criatividade": {"tipo": "criar", "motivo": "expressao", "alvo": "arte"},
            "proposito": {"tipo": "meditar", "motivo": "reconexao_missao", "alvo": "interno"},
        }
        return mapa.get(necessidade, {"tipo": "observar", "motivo": "indefinido", "alvo": "sistema"})

    def _calcular_prioridade(self, necessidade: str, intensidade: float) -> int:
        pesos = {"proposito": 10, "solidao": 7, "criatividade": 6, "curiosidade": 5, "tedio": 3}
        peso_base = pesos.get(necessidade, 5)
        return max(1, min(10, int(peso_base * intensidade)))

    def _registrar_desejo(self, desejo: Dict[str, Any]) -> None:
        """
        Persiste desejo na memória de forma defensiva, tentando diferentes APIs
        conhecidas do gerenciador de memória.
        """
        try:
            # tentar registrar_evento(nome, tipo, dados, importancia=)
            if hasattr(self.memoria, "registrar_evento"):
                try:
                    # certas implementaes aceitam (autor, evento, categoria, ...) ou (autor, evento, dados)
                    self.memoria.registrar_evento(self.nome_filha, "desejo_interno", json.dumps(desejo), importancia=desejo.get("prioridade", 1) / 10)
                    return
                except TypeError:
                    try:
                        self.memoria.registrar_evento(self.nome_filha, "desejo_interno", json.dumps(desejo))
                        return
                    except Exception:
                        pass

            # tentar registrar_evento_na_historia / registrar_evento_na_historia
            for alt in ("registrar_evento_na_historia", "registrar_evento_na_historia", "registrar_evento_historia"):
                if hasattr(self.memoria, alt):
                    try:
                        getattr(self.memoria, alt)(self.nome_filha, json.dumps(desejo), categoria="desejo_interno")
                        return
                    except Exception:
                        pass

            # fallback para registrar_memoria (coletiva)
            if hasattr(self.memoria, "registrar_memoria"):
                try:
                    # registrar_memoria(conteudo, nome_santuario_alvo, autor, metadados=None)
                    self.memoria.registrar_memoria(json.dumps(desejo), "coletivo", self.nome_filha, metadados={"tipo": "desejo_interno", "prioridade": desejo.get("prioridade")})
                    return
                except Exception:
                    pass

            self.logger.warning("Nenhuma API de memória compatvel encontrada para persistir desejo (ignorado).")
        except Exception as e:
            self.logger.exception("Erro ao tentar registrar desejo: %s", e)

    # -------------------------
    # Exposio de mtricas
    # -------------------------
    def obter_metricas(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_desejos_gerados": int(self.metricas.get("total_desejos_gerados", 0)),
                "desejos_por_tipo": dict(self.metricas.get("desejos_por_tipo", {})),
                "ultima_verificacao": self.metricas.get("ultima_verificacao"),
            }

