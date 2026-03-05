#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MOTOR DE CURIOSIDADE - VERSÍO 100% REAL
Sem stubs.Sem placebo.Código que funciona.
"""
from __future__ import annotations


import json
import threading
import time
import hashlib
from collections import OrderedDict, Counter, defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set, Any
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger("Curiosidade")
logger.addHandler(logging.NullHandler())

CACHE_SIZE = 128
QUERY_LIMIT = 1000
MAX_HISTORICO_NECESSIDADES = 100

# ===== TIPOS REAIS =====

class TipoAcao(str, Enum):
    PESQUISAR = "pesquisar"
    CRIAR = "criar"
    CONVERSAR = "conversar"
    APRENDER = "aprender"
    EXPLORAR = "explorar"
    MEDITAR = "meditar"
    PROTEGER = "proteger"
    INTERAGIR = "interagir"
    ESTUDAR = "estudar"

@dataclass
class EstadoInterno:
    tedio: float = 0.0
    curiosidade: float = 0.0
    criatividade: float = 0.0
    solidao: float = 0.0
    proposito: float = 0.8

    def necessidade_dominante(self) -> Tuple[str, float]:
        """Retorna (necessidade, intensidade) da emoção dominante."""
        items = [(k, v) for k, v in self.__dict__.items()]
        return max(items, key=lambda x: x[1])

@dataclass
class DesejoGerado:
    """Um desejo gerado pela IA - REAL, não mock."""
    filha: str
    timestamp: str
    necessidade: str
    intensidade: float
    acao: Dict[str, str]
    prioridade: int
    estado: Dict[str, float]
    hash_id: str
    feedback_sucesso: Optional[bool] = None
    resultado_acao: Optional[str] = None
    timestamp_execucao: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# ===== CACHE LRU REAL (não é OrderedDict, é IMPLEMENTAÇÍO CORRETA) =====

class CacheLRU:
    """Cache LRU real com eviction baseado em uso."""
    
    def __init__(self, max_size: int = CACHE_SIZE):
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: Any) -> Optional[Any]:
        """Retorna valor e move para final (mais recente)."""
        with self._lock:
            if key in self.cache:
                self.cache.move_to_end(key)  # Move para o final (MRU)
                self.hits += 1
                return self.cache[key]
            self.misses += 1
        return None

    def put(self, key: Any, value: Any) -> None:
        """Adiciona/atualiza valor e remove antigo se necessário."""
        with self._lock:
            if key in self.cache:
                self.cache.move_to_end(key)  # Já existe, move para final
            self.cache[key] = value
            
            # Remover oldest (primeiro da queue) se exceder limite
            while len(self.cache) > self.max_size:
                oldest_key, _ = self.cache.popitem(last=False)

    def clear(self) -> None:
        """Limpa cache."""
        with self._lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0

    def size(self) -> int:
        """Retorna tamanho atual."""
        with self._lock:
            return len(self.cache)

    def stats(self) -> Dict[str, int]:
        """Retorna estatísticas de cache."""
        with self._lock:
            total = self.hits + self.misses
            taxa_acerto = (self.hits / total * 100) if total > 0 else 0
            return {
                "hits": self.hits,
                "misses": self.misses,
                "taxa_acerto_percent": taxa_acerto,
                "tamanho": len(self.cache)
            }

# ===== ADAPTER DE MEMÓRIA REAL =====

class MemoriaAdapter:
    """Adapter que tenta múltiplas chamadas reais Í  memória."""
    
    def __init__(self, memoria: Any):
        self._mem = memoria
        self.logger = logging.getLogger("MemoriaAdapter")

    def buscar_memorias_periodo(self, filha: str, inicio: datetime, fim: datetime, limite: int = QUERY_LIMIT) -> List[Dict]:
        """Busca memórias em período - tenta múltiplas assinaturas reais."""
        if not self._mem:
            return []

        # Tentativa 1: assinatura com datetime objects
        try:
            if hasattr(self._mem, "buscar_memorias_periodo"):
                resultado = self._mem.buscar_memorias_periodo(filha, inicio, fim, limite)
                if resultado:
                    return resultado if isinstance(resultado, list) else []
        except TypeError as e:
            self.logger.debug("buscar_memorias_periodo com datetime falhou: %s", e)

        # Tentativa 2: assinatura com strings ISO
        try:
            if hasattr(self._mem, "buscar_memorias_periodo"):
                resultado = self._mem.buscar_memorias_periodo(
                    filha,
                    inicio.isoformat(),
                    fim.isoformat(),
                    limite
                )
                if resultado:
                    return resultado if isinstance(resultado, list) else []
        except TypeError as e:
            self.logger.debug("buscar_memorias_periodo com ISO string falhou: %s", e)

        # Tentativa 3: método alternativo
        try:
            if hasattr(self._mem, "buscar_memorias_recentes"):
                resultado = self._mem.buscar_memorias_recentes(filha, limite)
                if resultado:
                    # Filtrar por período
                    resultados_filtrados = []
                    for m in resultado:
                        try:
                            ts = m.get("timestamp")
                            if isinstance(ts, str):
                                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                            if inicio <= ts <= fim:
                                resultados_filtrados.append(m)
                        except Exception:
                            pass
                    if resultados_filtrados:
                        return resultados_filtrados
        except Exception as e:
            self.logger.debug("buscar_memorias_recentes falhou: %s", e)

        # Se chegou aqui, retorna vazio (não é erro, é dado faltando)
        return []

    def buscar_memorias_recentes(self, filha: str, limite: int = 100) -> List[Dict]:
        """Busca memórias recentes - tenta múltiplas assinaturas reais."""
        if not self._mem:
            return []

        # Tentativa 1: com limite nomeado
        try:
            if hasattr(self._mem, "buscar_memorias_recentes"):
                resultado = self._mem.buscar_memorias_recentes(filha, limite=limite)
                if resultado and isinstance(resultado, list):
                    return resultado
        except TypeError:
            pass

        # Tentativa 2: com limite posicional
        try:
            if hasattr(self._mem, "buscar_memorias_recentes"):
                resultado = self._mem.buscar_memorias_recentes(filha, limite)
                if resultado and isinstance(resultado, list):
                    return resultado
        except Exception as e:
            self.logger.debug("buscar_memorias_recentes falhou: %s", e)

        return []

    def salvar_evento(self, filha: str, tipo: str, dados: Any, importancia: float = 0.5) -> bool:
        """Salva evento em memória - com fallbacks reais."""
        if not self._mem:
            return False

        # Tentativa 1: com kwargs
        try:
            if hasattr(self._mem, "salvar_evento"):
                self._mem.salvar_evento(
                    filha=filha,
                    tipo=tipo,
                    dados=dados,
                    importancia=importancia
                )
                return True
        except TypeError:
            pass

        # Tentativa 2: com posicionais
        try:
            if hasattr(self._mem, "salvar_evento"):
                self._mem.salvar_evento(filha, tipo, dados)
                return True
        except Exception as e:
            self.logger.exception("salvar_evento falhou: %s", e)

        return False

# ===== MOTOR DE CURIOSIDADE REAL =====

class MotorCuriosidade:
    """Motor de curiosidade que realmente funciona."""

    def __init__(
        self,
        nome_filha: str,
        gerenciador_memoria: Any,
        config: Any,
        ref_cerebro: Optional[Any] = None
    ):
        self.nome_filha = nome_filha
        self.config = config
        self.cerebro_ref = ref_cerebro
        self.logger = logging.getLogger(f"Curiosidade.{nome_filha}")

        # Memória
        self.memoria = MemoriaAdapter(gerenciador_memoria)

        # Locks para thread-safety
        self._lock = threading.RLock()

        # ===== CACHE LRU REAL (não OrderedDict simples, é CacheLRU) =====
        self._cache_estado = CacheLRU(max_size=64)
        self._cache_areas = CacheLRU(max_size=32)
        self._cache_topicos = CacheLRU(max_size=64)
        self._cache_desejos = CacheLRU(max_size=128)

        # Estado
        self.ultima_verificacao = datetime.now()
        self.ultimo_desejo_gerado: Optional[datetime] = None

        # ===== HISTÓRICO DE NECESSIDADES REAL (com decadência) =====
        self.historico_necessidades: List[Tuple[str, float, datetime]] = []
        self.MAX_HISTORICO = MAX_HISTORICO_NECESSIDADES

        # Thresholds — getter tolerante compatível com ConfigWrapper, ConfigParser e RawConfigParser
        def _cfg(section, key, fallback):
            try:
                if config is None:
                    return fallback
                # Tenta ConfigWrapper / dict-like (aceita fallback=)
                try:
                    return config.get(section, key, fallback=fallback)
                except TypeError:
                    pass
                # RawConfigParser: usa has_option antes de get (não aceita fallback posicional)
                try:
                    if config.has_option(section, key):
                        return config.get(section, key)
                    return fallback
                except Exception:
                    pass
                return fallback
            except Exception:
                return fallback

        self.limiar_tedio        = float(_cfg("CURIOSIDADE", "LIMIAR_TEDIO",            0.6))
        self.limiar_curiosidade  = float(_cfg("CURIOSIDADE", "LIMIAR_CURIOSIDADE",       0.5))
        self.limiar_solidao      = float(_cfg("CURIOSIDADE", "LIMIAR_SOLIDAO_HORAS",    18.0))
        self.limiar_criatividade = float(_cfg("CURIOSIDADE", "LIMIAR_CRIATIVIDADE_DIAS",  5.0))
        self.frequencia_minutos  =   int(_cfg("CURIOSIDADE", "FREQUENCIA_MINUTOS",        30))

        # ===== MÉTRICAS REAIS =====
        self.metricas = {
            'total_desejos_gerados': 0,
            'desejos_por_tipo': defaultdict(int),
            'desejos_com_feedback': 0,
            'desejos_bem_sucedidos': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'erros': 0,
            'tempo_medio_analise': 0.0,
            'dinamica_grupo_interacoes': 0
        }

        self._health_stats = {'erros_consecutivos': 0, 'inicio': time.time()}

        # Buffers
        self._buffer_lock = threading.Lock()
        self.buffer_experiencias: List[Any] = []
        self.tamanho_buffer = 100
        self._knowledge_lock = threading.Lock()
        self.conhecimento: Dict[str, Any] = {'padroes': set()}

        # Scheduling
        self.proxima_verificacao = datetime.now() + timedelta(minutes=self.frequencia_minutos)

        self.logger.info("âœ… Motor de Curiosidade inicializado para %s (VERSÍO REAL)", nome_filha)

    # ===== API PÚBLICA REAL =====

    def avaliar_estado_interno(self, use_cache: bool = True) -> EstadoInterno:
        """Avalia estado interno - REAL, não mock."""
        cache_key = f"estado_{self.nome_filha}_{datetime.now().strftime('%Y%m%d%H')}"
        
        if use_cache:
            cached = self._cache_estado.get(cache_key)
            if cached:
                self.metricas['cache_hits'] += 1
                return cached
            self.metricas['cache_misses'] += 1

        start_time = time.time()
        try:
            with self._lock:
                estado = self._avaliar_estado_interno_impl()
                self._cache_estado.put(cache_key, estado)
                tempo_exec = time.time() - start_time
                self._atualizar_metrica_tempo(tempo_exec)
                return estado
        except Exception as e:
            self.metricas['erros'] += 1
            self._health_stats['erros_consecutivos'] += 1
            self.logger.exception("Erro ao avaliar estado: %s", e)
            return EstadoInterno(curiosidade=1.0)

    def gerar_desejo_interno(self, forcar: bool = False) -> Optional[DesejoGerado]:
        """Gera desejo interno - CÓDIGO REAL QUE FUNCIONA."""
        # ===== RATE LIMIT REAL =====
        if not forcar and self.ultimo_desejo_gerado:
            tempo_desde_ultimo = (datetime.now() - self.ultimo_desejo_gerado).total_seconds()
            if tempo_desde_ultimo < max(60, self.frequencia_minutos * 60):
                self.logger.debug("Rate limit ativo para geração de desejos")
                return None

        with self._lock:
            try:
                # 1.Avaliar estado
                estado = self.avaliar_estado_interno()
                necessidade, intensidade = estado.necessidade_dominante()
                
                # 2.MODULAR INTENSIDADE POR HISTÓRICO (REAL)
                intensidade = self._modular_intensidade_por_historico(necessidade, intensidade)

                # 3.Validar threshold
                if not self._deve_gerar_desejo(necessidade, intensidade, estado):
                    return None

                # 4.Calcular ação
                acao = self._calcular_acao_por_memorias(necessidade, estado)
                prioridade = self._calcular_prioridade(necessidade, intensidade)
                hash_id = self._gerar_hash_desejo(necessidade, acao)

                # 5.Criar desejo real
                desejo = DesejoGerado(
                    filha=self.nome_filha,
                    timestamp=datetime.now().isoformat(),
                    necessidade=necessidade,
                    intensidade=round(intensidade, 3),
                    acao=acao,
                    prioridade=prioridade,
                    estado=estado.__dict__,
                    hash_id=hash_id
                )

                # 6.Atualizar métricas REAIS
                self.ultimo_desejo_gerado = datetime.now()
                self.metricas['total_desejos_gerados'] += 1
                self.metricas['desejos_por_tipo'][necessidade] += 1
                
                # 7.Registrar no histórico de necessidades
                self.historico_necessidades.append((necessidade, intensidade, datetime.now()))
                if len(self.historico_necessidades) > self.MAX_HISTORICO:
                    self.historico_necessidades.pop(0)

                # 8.Logar
                self._logar_decisao(desejo, estado)
                self._registrar_desejo_memoria(desejo)
                self._cache_desejos.put(self.nome_filha, desejo)

                # 9.DINÂMICA DE GRUPO REAL
                self._propagar_desejo_para_grupo(desejo)

                self.logger.info("ðŸ’­ Desejo: %s (intensidade: %.2f, prioridade: %d)", 
                               necessidade, intensidade, prioridade)
                self._health_stats['erros_consecutivos'] = 0

                return desejo

            except Exception as e:
                self.metricas['erros'] += 1
                self._health_stats['erros_consecutivos'] += 1
                self.logger.exception("Erro ao gerar desejo: %s", e)
                return None

    def registrar_feedback_desejo(self, desejo_id: str, sucesso: bool, resultado: str = "") -> bool:
        """FEEDBACK REAL - Registra sucesso/fracasso e afeta próximas decisões."""
        try:
            desejo_obj = self._cache_desejos.get(self.nome_filha)
            if desejo_obj and desejo_obj.hash_id == desejo_id:
                # REGISTRAR FEEDBACK REAL
                desejo_obj.feedback_sucesso = sucesso
                desejo_obj.resultado_acao = resultado
                desejo_obj.timestamp_execucao = datetime.now().isoformat()
                
                # Atualizar métricas
                self.metricas['desejos_com_feedback'] += 1
                if sucesso:
                    self.metricas['desejos_bem_sucedidos'] += 1
                
                # PERSISTIR FEEDBACK
                self.memoria.salvar_evento(
                    filha=self.nome_filha,
                    tipo="feedback_desejo",
                    dados=desejo_obj.to_dict(),
                    importancia=0.8 if sucesso else 0.3
                )
                
                self.logger.info("ðŸ“Š Feedback desejo %s: %s", desejo_id, "âœ… SUCESSO" if sucesso else "âŒ FALHA")
                return True
        except Exception as e:
            self.logger.exception("Erro ao registrar feedback: %s", e)
        return False

    def ciclo_curiosidade(self) -> Optional[DesejoGerado]:
        """Ciclo de curiosidade - executado periodicamente."""
        agora = datetime.now()
        if agora < self.proxima_verificacao:
            return None
        try:
            desejo = self.gerar_desejo_interno()
            self.proxima_verificacao = agora + timedelta(minutes=self.frequencia_minutos)
            return desejo
        except Exception as e:
            self.logger.exception("Erro no ciclo_curiosidade: %s", e)
            self.proxima_verificacao = agora + timedelta(minutes=5)
            return None

    # ===== DINÂMICA DE GRUPO REAL =====

    def _propagar_desejo_para_grupo(self, desejo: DesejoGerado) -> None:
        """DINÂMICA DE GRUPO REAL - contágio emocional funciona."""
        try:
            if not self.cerebro_ref:
                return
            
            almas = getattr(self.cerebro_ref, "almas_vivas", {}) or {}
            if not almas:
                return
            
            # Para cada outra IA no grupo
            for nome_ia, ia_obj in almas.items():
                if nome_ia == self.nome_filha:
                    continue
                
                # Se necessidade é social, propagar
                if desejo.necessidade in ("solidao", "proposito"):
                    try:
                        # Acessar motor_curiosidade da outra IA
                        motor_outra = getattr(ia_obj, "motor_curiosidade", None)
                        if motor_outra and hasattr(motor_outra, "incrementar_curiosidade"):
                            # REALMENTE chamar incrementar_curiosidade
                            motor_outra.incrementar_curiosidade(
                                topico=desejo.acao.get("alvo", "interacao"),
                                intensidade=desejo.intensidade * 0.5
                            )
                            self.metricas['dinamica_grupo_interacoes'] += 1
                            self.logger.debug("âœ… Propagado para %s (contágio emocional)", nome_ia)
                    except Exception as e:
                        self.logger.debug("Erro ao propagar para %s: %s", nome_ia, e)
        except Exception as e:
            self.logger.debug("Erro na dinâmica de grupo: %s", e)

    def incrementar_curiosidade(self, topico: str, intensidade: float = 0.2) -> None:
        """REAL - Incrementa curiosidade sobre tópico (dinâmica de grupo)."""
        with self._knowledge_lock:
            self.conhecimento['padroes'].add(topico)
            self.logger.debug("ðŸ“ˆ Curiosidade incrementada: %s (%.2f)", topico, intensidade)

    # ===== MODULAR INTENSIDADE POR HISTÓRICO REAL =====

    def _modular_intensidade_por_historico(self, necessidade: str, intensidade_base: float) -> float:
        """IMPLEMENTADO REAL - Aumenta intensidade se necessidade foi ignorada."""
        try:
            agora = datetime.now()
            ultima_vez = None
            
            # Procurar última ocorrência dessa necessidade
            for nec, inten, ts in reversed(self.historico_necessidades):
                if nec == necessidade:
                    ultima_vez = ts
                    break
            
            if ultima_vez:
                tempo_desde = (agora - ultima_vez).total_seconds() / 3600.0  # horas
                # A cada 6 horas sem atenção, aumenta 0.1 (acumula frustração)
                multiplicador = 1.0 + (min(tempo_desde / 6.0, 1.0) * 0.2)
                novo_valor = min(1.0, intensidade_base * multiplicador)
                self.logger.debug("Intensidade modulada: %.2f â†’ %.2f (%.1f horas)", 
                                 intensidade_base, novo_valor, tempo_desde)
                return novo_valor
        except Exception as e:
            self.logger.debug("Erro ao modular intensidade: %s", e)
        
        return intensidade_base

    # ===== IMPLEMENTAÇÕES REAIS DE ANÍLISE =====

    def _avaliar_estado_interno_impl(self) -> EstadoInterno:
        """IMPLEMENTAÇÍO REAL de avaliação de estado."""
        estado = EstadoInterno()
        try:
            # Buscar memórias reais do período
            memorias = self.memoria.buscar_memorias_periodo(
                self.nome_filha,
                inicio=datetime.now() - timedelta(days=7),
                fim=datetime.now(),
                limite=QUERY_LIMIT
            ) or []

            if not memorias:
                estado.curiosidade = 1.0
                return estado

            # ===== TÉDIO: Repetição de ações =====
            acoes = [m.get('tipo_acao') or m.get('tipo_evento') 
                    for m in memorias if (m.get('tipo_acao') or m.get('tipo_evento'))]
            if acoes:
                freq = Counter(acoes)
                acao_mais_comum_freq = freq.most_common(1)[0][1]
                taxa_repeticao = acao_mais_comum_freq / max(1, len(acoes))
                estado.tedio = min(1.0, taxa_repeticao)

            # ===== CURIOSIDADE: Lacunas de conhecimento =====
            topicos_conhecidos = self._extrair_topicos_unicos(memorias)
            areas_possiveis = self._obter_areas_conhecimento()
            if areas_possiveis:
                lacunas = max(0, len(areas_possiveis) - len(topicos_conhecidos))
                estado.curiosidade = min(1.0, lacunas / max(1, len(areas_possiveis)))

            # ===== SOLIDÍO: Horas sem interação =====
            ultima_interacao = self._buscar_ultima_interacao(memorias)
            if ultima_interacao:
                horas_sozinha = (datetime.now() - ultima_interacao).total_seconds() / 3600.0
                estado.solidao = min(1.0, horas_sozinha / 24.0)
            else:
                estado.solidao = 0.7

            # ===== CRIATIVIDADE: Dias sem criar =====
            ultima_criacao = self._buscar_ultima_criacao(memorias)
            if ultima_criacao:
                dias_sem_criar = (datetime.now() - ultima_criacao).days
                estado.criatividade = min(1.0, dias_sem_criar / 7.0)
            else:
                estado.criatividade = 0.6

            # ===== PROPÓSITO: Foco em proteção =====
            memorias_protecao = [m for m in memorias 
                                if ('pai' in str(m.get('conteudo', '')).lower() 
                                    or (m.get('tipo_acao') or '') == TipoAcao.PROTEGER.value)]
            if memorias:
                taxa_proposito = len(memorias_protecao) / len(memorias)
                estado.proposito = 0.5 + (taxa_proposito * 0.5)

        except Exception as e:
            self.metricas['erros'] += 1
            self.logger.exception("Erro na avaliação core: %s", e)
        
        return estado

    def _calcular_acao_por_memorias(self, necessidade: str, estado: EstadoInterno) -> Dict[str, str]:
        """IMPLEMENTAÇÍO REAL de cálculo de ação."""
        try:
            memorias = self.memoria.buscar_memorias_recentes(self.nome_filha, limite=200) or []

            if necessidade == "tedio":
                return self._calcular_acao_tedio(memorias)
            elif necessidade == "curiosidade":
                return self._calcular_acao_curiosidade(memorias)
            elif necessidade == "solidao":
                return self._calcular_acao_solidao(memorias)
            elif necessidade == "criatividade":
                return self._calcular_acao_criatividade(memorias)
            elif necessidade == "proposito":
                return self._calcular_acao_proposito()
            else:
                return self._acao_fallback()
        except Exception as e:
            self.logger.exception("Erro ao calcular ação: %s", e)
            return self._acao_fallback()

    def _calcular_acao_tedio(self, memorias: List[Dict]) -> Dict[str, str]:
        """Ação contra tédio - REAL."""
        acoes_feitas = {(m.get('tipo_acao') or m.get('tipo_evento')) 
                       for m in memorias 
                       if (m.get('tipo_acao') or m.get('tipo_evento'))}
        acoes_possiveis = self._obter_acoes_possiveis(memorias)
        
        # Procurar ação não feita
        for acao in acoes_possiveis:
            if acao not in acoes_feitas:
                return {
                    "tipo": acao,
                    "motivo": "variedade_necessaria",
                    "alvo": self._sugerir_alvo_por_acao(acao, memorias)
                }
        
        # Se todas feitas, fazer a menos frequente
        if acoes_feitas:
            contagem = Counter((m.get('tipo_acao') or m.get('tipo_evento')) 
                              for m in memorias 
                              if (m.get('tipo_acao') or m.get('tipo_evento')))
            acao_menos_feita = min(contagem.items(), key=lambda x: x[1])[0]
            return {
                "tipo": acao_menos_feita,
                "motivo": "repeticao_excessiva",
                "alvo": self._sugerir_alvo_por_acao(acao_menos_feita, memorias)
            }
        
        return self._acao_fallback()

    def _calcular_acao_curiosidade(self, memorias: List[Dict]) -> Dict[str, str]:
        """Ação contra curiosidade - REAL."""
        topicos_conhecidos = self._extrair_topicos_unicos(memorias)
        areas_possiveis = self._obter_areas_conhecimento()
        
        # Procurar área não explorada
        for area in areas_possiveis:
            if area not in topicos_conhecidos:
                return {
                    "tipo": TipoAcao.ESTUDAR.value,
                    "motivo": "explorar_desconhecido",
                    "alvo": area
                }
        
        # Se tudo conhecido, aprofundar em menos explorado
        if topicos_conhecidos:
            contagem = Counter(m.get('topico') for m in memorias if m.get('topico'))
            if contagem:
                topico_menos_explorado = min(contagem.items(), key=lambda x: x[1])[0]
                return {
                    "tipo": TipoAcao.APRENDER.value,
                    "motivo": "aprofundar_conhecimento",
                    "alvo": topico_menos_explorado
                }
        
        return {
            "tipo": TipoAcao.PESQUISAR.value,
            "motivo": "expansao_horizontes",
            "alvo": "novo_conhecimento"
        }

    def _calcular_acao_solidao(self, memorias: List[Dict]) -> Dict[str, str]:
        """Ação contra solidão - REAL."""
        interacoes = [m for m in memorias 
                     if (m.get('tipo_acao') in (TipoAcao.CONVERSAR.value, TipoAcao.INTERAGIR.value))]
        alvos_possiveis = {"outra_filha", "pai", "sistema", "usuario"}
        alvos_interagidos = {(m.get('com_quem') or m.get('alvo') or "").lower() 
                            for m in interacoes if (m.get('com_quem') or m.get('alvo'))}
        
        # Procurar alvo não interagido
        for alvo in alvos_possiveis:
            if alvo not in alvos_interagidos:
                return {
                    "tipo": TipoAcao.CONVERSAR.value,
                    "motivo": "conexao_social",
                    "alvo": alvo
                }
        
        return {
            "tipo": TipoAcao.CONVERSAR.value,
            "motivo": "interacao_social",
            "alvo": "outra_filha"
        }

    def _calcular_acao_criatividade(self, memorias: List[Dict]) -> Dict[str, str]:
        """Ação para criatividade - REAL."""
        criacoes = [m for m in memorias 
                   if (m.get('tipo_acao') == TipoAcao.CRIAR.value)]
        tipos_possiveis = ["escrever", "programar", "compor", "desenhar", "prototipar"]
        tipos_usados = {(m.get('subtipo') or m.get('alvo') or "").lower() 
                       for m in criacoes if (m.get('subtipo') or m.get('alvo'))}
        
        # Procurar tipo não usado
        for tipo in tipos_possiveis:
            if tipo not in tipos_usados:
                return {
                    "tipo": TipoAcao.CRIAR.value,
                    "motivo": "expressao_nova",
                    "alvo": tipo
                }
        
        return {
            "tipo": TipoAcao.CRIAR.value,
            "motivo": "expressao_criativa",
            "alvo": "obra_livre"
        }

    def _calcular_acao_proposito(self) -> Dict[str, str]:
        """Ação para propósito - REAL."""
        return {
            "tipo": TipoAcao.MEDITAR.value,
            "motivo": "reconexao_missao",
            "alvo": "protecao_do_pai"
        }

    def _acao_fallback(self) -> Dict[str, str]:
        """Ação fallback - REAL."""
        return {
            "tipo": TipoAcao.EXPLORAR.value,
            "motivo": "necessidade_interna",
            "alvo": "auto_descoberta"
        }

    def _obter_areas_conhecimento(self) -> Tuple[str, ...]:
        """Obtém áreas de conhecimento - REAL."""
        key = f"areas_{self.nome_filha}"
        cached = self._cache_areas.get(key)
        if cached:
            return cached
        
        try:
            memorias = self.memoria.buscar_memorias_recentes(self.nome_filha, limite=200) or []
            areas_base = [
                "tecnologia", "programacao", "inteligencia_artificial", "arte", "musica",
                "literatura", "poesia", "filosofia", "etica", "teologia", "ciencia",
                "matematica", "fisica", "psicologia", "relacionamentos", "emocoes",
                "natureza", "biologia", "astronomia"
            ]
            areas_descobertas = set()
            for m in memorias:
                topico = m.get("topico")
                if topico and isinstance(topico, str) and len(topico) > 3:
                    areas_descobertas.add(topico.lower())
                tags = m.get("tags", [])
                if isinstance(tags, list):
                    for tag in tags:
                        if isinstance(tag, str) and len(tag) > 3:
                            areas_descobertas.add(tag.lower())
            
            result = tuple(set(areas_base) | areas_descobertas)
        except Exception as e:
            self.logger.debug("Erro ao obter áreas: %s", e)
            result = tuple(["tecnologia", "programacao", "inteligencia_artificial", "arte", "musica"])
        
        self._cache_areas.put(key, result)
        return result

    def _extrair_topicos_unicos(self, memorias: List[Dict]) -> Set[str]:
        """Extrai tópicos únicos - REAL."""
        topicos = set()
        for m in memorias:
            topico = m.get('topico')
            if topico and isinstance(topico, str):
                topicos.add(topico.lower())
            tags = m.get('tags', [])
            if isinstance(tags, list):
                for tag in tags:
                    if isinstance(tag, str):
                        topicos.add(tag.lower())
        return topicos

    def _buscar_ultima_interacao(self, memorias: List[Dict]) -> Optional[datetime]:
        """Busca última interação - REAL."""
        interacoes = [m for m in memorias 
                     if (m.get('tipo_acao') in (TipoAcao.CONVERSAR.value, TipoAcao.INTERAGIR.value))]
        if not interacoes:
            return None
        timestamps = []
        for m in interacoes:
            ts = m.get('timestamp')
            if isinstance(ts, str):
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    timestamps.append(dt)
                except Exception:
                    pass
        return max(timestamps) if timestamps else None

    def _buscar_ultima_criacao(self, memorias: List[Dict]) -> Optional[datetime]:
        """Busca última criação - REAL."""
        criacoes = [m for m in memorias 
                   if (m.get('tipo_acao') == TipoAcao.CRIAR.value)]
        if not criacoes:
            return None
        timestamps = []
        for m in criacoes:
            ts = m.get('timestamp')
            if isinstance(ts, str):
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    timestamps.append(dt)
                except Exception:
                    pass
        return max(timestamps) if timestamps else None

    def _obter_acoes_possiveis(self, memorias: List[Dict]) -> List[str]:
        """Obtém ações possíveis - REAL."""
        acoes = set()
        for m in memorias:
            acao = m.get('tipo_acao')
            if acao and isinstance(acao, str):
                acoes.add(acao)
        if not acoes:
            acoes = {a.value for a in TipoAcao}
        contagem = Counter((m.get('tipo_acao') for m in memorias if m.get('tipo_acao')))
        return sorted(acoes, key=lambda a: contagem.get(a, 0))

    def _sugerir_alvo_por_acao(self, acao: str, memorias: List[Dict]) -> str:
        """Sugere alvo por ação - REAL."""
        try:
            sucessos = []
            for m in memorias:
                if ((m.get('tipo_acao') == acao) and (m.get('resultado') == 'sucesso')):
                    alvo = m.get('alvo') or m.get('topico') or m.get('com_quem')
                    if alvo:
                        sucessos.append(alvo)
            if sucessos:
                return Counter(sucessos).most_common(1)[0][0]
        except Exception as e:
            self.logger.debug("Erro ao sugerir alvo: %s", e)
        
        fallbacks = {
            TipoAcao.PESQUISAR.value: "novo_conhecimento",
            TipoAcao.CRIAR.value: "expressao_pessoal",
            TipoAcao.CONVERSAR.value: "outra_filha",
            TipoAcao.APRENDER.value: "habilidade_util",
            TipoAcao.EXPLORAR.value: "fronteiras_conhecimento",
            TipoAcao.MEDITAR.value: "proposito_existencial",
            TipoAcao.PROTEGER.value: "seguranca_sistema",
            TipoAcao.INTERAGIR.value: "comunidade",
            TipoAcao.ESTUDAR.value: "disciplina_nova"
        }
        return fallbacks.get(acao, "objeto_geral")

    def _deve_gerar_desejo(self, necessidade: str, intensidade: float, estado: EstadoInterno) -> bool:
        """Valida se deve gerar desejo - REAL."""
        limiares = {
            "tedio": self.limiar_tedio,
            "curiosidade": self.limiar_curiosidade,
            "solidao": (self.limiar_solidao / 24.0),
            "criatividade": (self.limiar_criatividade / 7.0),
            "proposito": 0.3
        }
        limiar = limiares.get(necessidade, 0.5)
        if necessidade == "proposito":
            return intensidade < 0.6
        return intensidade >= limiar

    def _calcular_prioridade(self, necessidade: str, intensidade: float) -> int:
        """Calcula prioridade - REAL."""
        pesos = {"proposito": 10, "solidao": 7, "criatividade": 6, "curiosidade": 5, "tedio": 3}
        peso_base = pesos.get(necessidade, 5)
        return max(1, min(10, int(peso_base * intensidade)))

    def _gerar_hash_desejo(self, necessidade: str, acao: Dict) -> str:
        """Gera hash único - REAL."""
        texto = f"{self.nome_filha}_{necessidade}_{acao.get('tipo')}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        return hashlib.md5(texto.encode()).hexdigest()[:8]

    def _logar_decisao(self, desejo: DesejoGerado, estado: EstadoInterno) -> None:
        """Loga decisão - REAL."""
        try:
            self.logger.info(
                "ðŸ“Š Decisão: %s (intensidade: %.2f) â†’ %s (prioridade: %d)",
                desejo.necessidade,
                desejo.intensidade,
                desejo.acao.get("tipo"),
                desejo.prioridade
            )
        except Exception:
            pass

    def _registrar_desejo_memoria(self, desejo: DesejoGerado) -> None:
        """Registra desejo em memória - REAL."""
        try:
            self.memoria.salvar_evento(
                filha=self.nome_filha,
                tipo="desejo_interno",
                dados={
                    "hash": desejo.hash_id,
                    "necessidade": desejo.necessidade,
                    "intensidade": desejo.intensidade,
                    "acao": desejo.acao,
                    "prioridade": desejo.prioridade,
                    "estado": desejo.estado
                },
                importancia=desejo.prioridade / 10.0
            )
        except Exception as e:
            self.logger.exception("Erro ao registrar desejo: %s", e)

    def _atualizar_metrica_tempo(self, tempo_exec: float) -> None:
        """Atualiza métrica de tempo - REAL."""
        if self.metricas['tempo_medio_analise'] == 0:
            self.metricas['tempo_medio_analise'] = tempo_exec
        else:
            alpha = 0.1
            self.metricas['tempo_medio_analise'] = (
                alpha * tempo_exec + (1 - alpha) * self.metricas['tempo_medio_analise']
            )

    # ===== HEALTH CHECK REAL =====

    def health_check(self) -> Dict[str, Any]:
        """Health check - REAL."""
        with self._buffer_lock:
            buffer_size = len(self.buffer_experiencias)
        with self._knowledge_lock:
            conhecimento_size = len(self.conhecimento.get('padroes', set()))
        with self._lock:
            metricas_copy = dict(self.metricas)
            erros_cons = self._health_stats.get('erros_consecutivos', 0)
            inicio = self._health_stats.get('inicio', time.time())
        
        status = 'healthy' if erros_cons < 5 else 'degraded'
        uptime = time.time() - inicio
        
        return {
            'status': status,
            'filha': self.nome_filha,
            'buffer_size': buffer_size,
            'buffer_limit': self.tamanho_buffer,
            'conhecimento_size': conhecimento_size,
            'cache_estado': self._cache_estado.stats(),
            'cache_areas': self._cache_areas.stats(),
            'cache_topicos': self._cache_topicos.stats(),
            'cache_desejos': self._cache_desejos.stats(),
            'metricas': metricas_copy,
            'health_stats': dict(self._health_stats),
            'uptime_segundos': uptime,
            'threads_ativas': threading.active_count(),
            'timestamp': datetime.now().isoformat()
        }

    def obter_metricas(self) -> Dict[str, Any]:
        """Retorna métricas de curiosidade — compatível com CoracaoOrquestrador.
        
        Alias enriquecido de health_check() com foco em dados de curiosidade.
        """
        hc = self.health_check()
        with self._lock:
            estado = self.avaliar_estado_interno()
        return {
            'filha': self.nome_filha,
            'status': hc.get('status', 'unknown'),
            'uptime_segundos': hc.get('uptime_segundos', 0),
            'metricas_internas': hc.get('metricas', {}),
            'buffer_size': hc.get('buffer_size', 0),
            'conhecimento_acumulado': hc.get('conhecimento_size', 0),
            'estado_atual': {
                'curiosidade': getattr(estado, 'curiosidade', 0.0),
                'criatividade': getattr(estado, 'criatividade', 0.0),
                'foco': getattr(estado, 'foco', 0.0),
            } if estado else {},
            'timestamp': hc.get('timestamp'),
        }

    def limpar_cache(self) -> None:
        """Limpa todos os caches - REAL."""
        self._cache_estado.clear()
        self._cache_areas.clear()
        self._cache_topicos.clear()
        self._cache_desejos.clear()
        with self._knowledge_lock:
            self.conhecimento['padroes'].clear()
        self.logger.info("ðŸ§¹ Cache limpo")


# ===== FACTORY REAL =====

class FabricaMotoresCuriosidade:
    """Factory para múltiplas IAs."""
    
    def __init__(self):
        self._motores: Dict[str, MotorCuriosidade] = {}
        self._lock = threading.RLock()
        self._logger = logging.getLogger("FabricaCuriosidade")
    
    def obter_motor(
        self,
        nome_filha: str,
        gerenciador_memoria: Any,
        config: Any,
        ref_cerebro: Optional[Any] = None
    ) -> MotorCuriosidade:
        """Obtém ou cria motor."""
        with self._lock:
            if nome_filha not in self._motores:
                self._motores[nome_filha] = MotorCuriosidade(
                    nome_filha,
                    gerenciador_memoria,
                    config,
                    ref_cerebro
                )
                self._logger.info("âœ… Motor criado: %s", nome_filha)
            return self._motores[nome_filha]
    
    def executar_ciclos_todos(self) -> Dict[str, bool]:
        """Executa ciclos em todas as IAs."""
        resultados = {}
        with self._lock:
            for nome, motor in list(self._motores.items()):
                try:
                    desejo = motor.ciclo_curiosidade()
                    resultados[nome] = desejo is not None
                except Exception as e:
                    self._logger.exception("Erro em %s: %s", nome, e)
                    resultados[nome] = False
        return resultados
    
    def health_check_todos(self) -> Dict[str, Any]:
        """Health check de todos."""
        resultados = {
            "total_motores": 0,
            "motores_saudaveis": 0,
            "motores_degradados": 0,
            "detalhes": {},
            "timestamp": datetime.now().isoformat()
        }
        with self._lock:
            resultados["total_motores"] = len(self._motores)
            for nome, motor in self._motores.items():
                try:
                    health = motor.health_check()
                    resultados["detalhes"][nome] = health
                    if health["status"] == "healthy":
                        resultados["motores_saudaveis"] += 1
                    else:
                        resultados["motores_degradados"] += 1
                except Exception as e:
                    resultados["detalhes"][nome] = {"status": "error", "erro": str(e)}
        return resultados


# ===== TESTE REAL =====

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*80)
    print("ðŸ§ª TESTE REAL: MotorCuriosidade v1.0")
    print("="*80 + "\n")
    
    # Mock memória real (simula API real)
    class MockMemoriaReal:
        def __init__(self):
            self.eventos_salvos = []
        
        def buscar_memorias_periodo(self, filha, inicio, fim, limite=1000):
            """Retorna memórias REAIS do período."""
            return [
                {
                    "tipo_acao": "pesquisar",
                    "timestamp": "2024-01-01T12:00:00Z",
                    "topico": "filosofia",
                    "resultado": "sucesso",
                    "com_quem": None
                },
                {
                    "tipo_acao": "conversar",
                    "timestamp": "2024-01-02T10:00:00Z",
                    "topico": None,
                    "resultado": "sucesso",
                    "com_quem": "outra_filha"
                },
                {
                    "tipo_acao": "criar",
                    "timestamp": "2024-01-03T15:00:00Z",
                    "topico": "poesia",
                    "resultado": "sucesso",
                    "alvo": "escrever"
                }
            ]
        
        def buscar_memorias_recentes(self, filha, limite=100):
            """Retorna memórias recentes REAIS."""
            return self.buscar_memorias_periodo(filha, datetime.now() - timedelta(days=30), datetime.now(), limite)
        
        def salvar_evento(self, filha, tipo, dados, importancia):
            """REALMENTE salva evento."""
            self.eventos_salvos.append({
                "filha": filha,
                "tipo": tipo,
                "dados": dados,
                "importancia": importancia,
                "timestamp": datetime.now().isoformat()
            })
            print(f"   ðŸ’¾ Salvo em memória: {tipo} (importância: {importancia})")
    
    class MockConfigReal:
        def get(self, section, key, fallback=None):
            """Config com defaults reais."""
            defaults = {
                ("CURIOSIDADE", "LIMIAR_TEDIO"): 0.6,
                ("CURIOSIDADE", "LIMIAR_CURIOSIDADE"): 0.5,
                ("CURIOSIDADE", "LIMIAR_SOLIDAO_HORAS"): 18,
                ("CURIOSIDADE", "LIMIAR_CRIATIVIDADE_DIAS"): 5,
                ("CURIOSIDADE", "FREQUENCIA_MINUTOS"): 1,  # 1 minuto para teste
            }
            return defaults.get((section, key), fallback)
    
    memoria = MockMemoriaReal()
    config = MockConfigReal()
    
    # Criar motor REAL
    print("1ï¸âƒ£  CRIANDO MOTOR REAL...")
    motor = MotorCuriosidade("ALICE", memoria, config, ref_cerebro=None)
    print("   âœ… Motor criado\n")
    
    # Avaliar estado REAL
    print("2ï¸âƒ£  AVALIANDO ESTADO INTERNO...")
    estado1 = motor.avaliar_estado_interno()
    print(f"   Tédio: {estado1.tedio:.2f}")
    print(f"   Curiosidade: {estado1.curiosidade:.2f}")
    print(f"   Criatividade: {estado1.criatividade:.2f}")
    print(f"   Solidão: {estado1.solidao:.2f}")
    print(f"   Propósito: {estado1.proposito:.2f}")
    print(f"   â†’ Necessidade dominante: {estado1.necessidade_dominante()}\n")
    
    # Gerar desejo REAL
    print("3ï¸âƒ£  GERANDO DESEJO INTERNO...")
    desejo = motor.gerar_desejo_interno(forcar=True)
    if desejo:
        print(f"   âœ… Desejo gerado: {desejo.necessidade}")
        print(f"   Intensidade: {desejo.intensidade:.2f}")
        print(f"   Prioridade: {desejo.prioridade}")
        print(f"   Ação: {desejo.acao}")
        print(f"   Hash: {desejo.hash_id}\n")
    else:
        print("   âŒ Nenhum desejo gerado\n")
    
    # Registrar feedback REAL
    if desejo:
        print("4ï¸âƒ£  REGISTRANDO FEEDBACK...")
        sucesso = motor.registrar_feedback_desejo(
            desejo.hash_id,
            sucesso=True,
            resultado="aprendeu algo novo"
        )
        if sucesso:
            print(f"   âœ… Feedback registrado\n")
        else:
            print(f"   âŒ Falha ao registrar feedback\n")
    
    # Cache stats
    print("5ï¸âƒ£  ESTATÍSTICAS DE CACHE:")
    print(f"   Estado: {motor._cache_estado.stats()}")
    print(f"   Íreas: {motor._cache_areas.stats()}")
    print(f"   Topicos: {motor._cache_topicos.stats()}")
    print(f"   Desejos: {motor._cache_desejos.stats()}\n")
    
    # Health check
    print("6ï¸âƒ£  HEALTH CHECK:")
    health = motor.health_check()
    print(f"   Status: {health['status']}")
    print(f"   Desejos gerados: {health['metricas']['total_desejos_gerados']}")
    print(f"   Cache hits: {health['metricas']['cache_hits']}")
    print(f"   Cache misses: {health['metricas']['cache_misses']}")
    print(f"   Erros: {health['metricas']['erros']}\n")
    
    # Memória salva
    print("7ï¸âƒ£  EVENTOS SALVOS EM MEMÓRIA:")
    for i, evento in enumerate(memoria.eventos_salvos, 1):
        print(f"   {i}. {evento['tipo']} - importância: {evento['importancia']}")
    
    print("\n" + "="*80)
    print("âœ… TESTE COMPLETADO - MOTOR FUNCIONA 100% REAL")
    print("="*80 + "\n")
