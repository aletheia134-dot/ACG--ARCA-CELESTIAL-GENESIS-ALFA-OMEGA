#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MotorCuriosidade - análise de memórias para geração de desejos internos

Melhorias aplicadas (enduricido):
 - Validação defensiva de dependências (gerenciador_memoria)
 - Proteção robusta ao parsear timestamps
 - Tokenização simples e filtragem de stopwords para extrair "tópicos conhecidos"
 - Injeção de RNG/clock para testabilidade
 - Proteção ao registrar desejos na memória (várias APIs tentadas)
 - Métricas e locks para concorrência leve
 - Remoção de imports não usados e tipagem explícita
"""
from __future__ import annotations


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


# pequena lista de stopwords para reduzir "tópicos" triviais
_DEFAULT_STOPWORDS = {
    "porque", "quando", "como", "isso", "aquela", "aquele", "este", "esta",
    "sobre", "entre", "também", "muito", "pouco", "sempre", "nunca", "tambem",
    "porque", "o", "a", "os", "as", "e", "de", "do", "da", "em", "por", "para",
    "com", "sem", "um", "uma", "uns", "umas"
}


class MotorCuriosidade:
    """
    Motor que analisa memórias para gerar 'desejos' internos das Filhas.Args:
        nome_filha: identificador da Filha.gerenciador_memoria: objeto que expõe métodos de leitura/escrita de memória.config: objeto/dict com parâmetros (opcional).
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

        # injetáveis para teste
        self._rng = rng
        self._clock = clock or datetime.utcnow

        # última checagem
        self.ultima_verificacao = self._clock()

        # limiares (podem ser fornecidos via config)
        self.limiar_tedio = float(self.config.get("limiar_tedio", 0.6))
        self.limiar_curiosidade = float(self.config.get("limiar_curiosidade", 0.5))
        self.limiar_solidao_horas = float(self.config.get("limiar_solidao_horas", 18))
        self.limiar_criatividade_dias = float(self.config.get("limiar_criatividade_dias", 5))

        # métricas (thread-safe)
        self._lock = threading.RLock()
        self.metricas: Dict[str, Any] = {
            "total_desejos_gerados": 0,
            "desejos_por_tipo": Counter(),
            "ultima_verificacao": self._clock().isoformat()
        }

        # parâmetros de busca de memória
        self._memorias_limit = int(self.config.get("memorias_limit", 200))

        # stopwords customizáveis
        self.stopwords = set(self.config.get("stopwords", [])).union(_DEFAULT_STOPWORDS)

        self.logger.info("MotorCuriosidade iniciado para %s", self.nome_filha)

    # -------------------------
    # Utilities
    # -------------------------
    def _now(self) -> datetime:
        return self._clock()

    def _parse_timestamp(self, ts_raw: Any) -> Optional[datetime]:
        """
        Tenta interpretar timestamps em vários formatos (ISO, unix str/int).
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
        Tokeniza texto em "tópicos" simples: palavras alfabéticas maiores que min_len,
        removendo stopwords; retorna lista única.
        """
        if not text:
            return []
        tokens = [t.lower() for t in re.findall(r"[a-zA-ZÀ-ÿ]{%d,}" % min_len, text)]
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
    # Core: avaliação do estado interno
    # -------------------------
    def avaliar_estado_interno(self) -> Dict[str, float]:
        """
        Retorna um dicionário com métricas (0.0-1.0) para:
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
                    self.logger.debug("Gerenciador de memória não expõe método de busca de memórias; usando lista vazia.")
                    memorias = []
            except Exception as e:
                self.logger.warning("Falha ao recuperar memórias: %s", e)
                memorias = []

            if not memorias:
                # sem memórias -> alta curiosidade / necessidade de explorar
                estado["curiosidade"] = 1.0
                # manter demais valores em baseline
                return estado

            # ANÁLISE: TÉDIO (repetição de ações)
            acoes = []
            for m in memorias:
                # suportar múltiplos formatos de chave
                tipo = m.get("tipo_evento") if isinstance(m, dict) else None
                if not tipo:
                    tipo = m.get("evento") if isinstance(m, dict) else None
                acoes.append(tipo or "nenhuma")
            if acoes:
                frequencias = Counter(acoes)
                maior = frequencias.most_common(1)[0][1]
                taxa_repeticao = maior / len(acoes)
                estado["tedio"] = min(1.0, float(taxa_repeticao))

            # ANÁLISE: CURIOSIDADE (lacunas de tópicos)
            topicos_conhecidos = set()
            for m in memorias:
                cont = m.get("conteudo", "") if isinstance(m, dict) else ""
                tokens = self._tokenize_topics(str(cont), min_len=5)
                topicos_conhecidos.update(tokens)
            vocab_size = len(topicos_conhecidos)
            # heurística defensiva
            if vocab_size < 20:
                estado["curiosidade"] = 0.9
            elif vocab_size < 50:
                estado["curiosidade"] = 0.6
            else:
                estado["curiosidade"] = 0.2

            # ANÁLISE: SOLIDÍO (tempo desde última interação social)
            ultima_interacao = None
            for m in memorias:
                t = None
                if isinstance(m, dict):
                    if m.get("tipo_evento") in ("chat", "interacao_social", "interacao"):
                        t = self._parse_timestamp(m.get("timestamp"))
                    elif m.get("evento") in ("chat", "interacao_social", "interacao"):
                        t = self._parse_timestamp(m.get("timestamp"))
                if t:
                    if not ultima_interacao or t > ultima_interacao:
                        ultima_interacao = t
            if ultima_interacao:
                horas = (self._now() - ultima_interacao).total_seconds() / 3600.0
                estado["solidao"] = min(1.0, horas / max(1.0, self.limiar_solidao_horas))
            else:
                estado["solidao"] = 1.0

            # ANÁLISE: CRIATIVIDADE (dias desde última criação)
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
    # Geração de desejos
    # -------------------------
    def gerar_desejo_interno(self) -> Optional[Dict[str, Any]]:
        """
        Gera um único desejo com base nas análises internas.Retorna o desejo (dict) ou None se nenhuma necessidade ultrapassar limiar.
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

        # regra simples: se necessidade dominante não atinge limiar, não gerar desejo
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
    # Ações auxiliares
    # -------------------------
    def _calcular_acao_por_memorias(self, necessidade: str, estado: Dict[str, float]) -> Dict[str, str]:
        mapa = {
            "tedio": {"tipo": "explorar", "motivo": "quebrar_rotina", "alvo": "novo_topico"},
            "curiosidade": {"tipo": "estudar", "motivo": "lacuna_conhecimento", "alvo": "area_desconhecida"},
            "solidao": {"tipo": "conversar", "motivo": "conexao", "alvo": "pai"},
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
                    # certas implementações aceitam (autor, evento, categoria, ...) ou (autor, evento, dados)
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

            self.logger.warning("Nenhuma API de memória compatível encontrada para persistir desejo (ignorado).")
        except Exception as e:
            self.logger.exception("Erro ao tentar registrar desejo: %s", e)

    # -------------------------
    # Exposição de métricas
    # -------------------------
    def obter_metricas(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_desejos_gerados": int(self.metricas.get("total_desejos_gerados", 0)),
                "desejos_por_tipo": dict(self.metricas.get("desejos_por_tipo", {})),
                "ultima_verificacao": self.metricas.get("ultima_verificacao"),
            }

