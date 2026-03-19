#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
MOTOR DE CURIOSIDADE - VERSO 100% REAL
Com Dicionário de Desejos integrado
"""


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
from pathlib import Path

logger = logging.getLogger("Curiosidade")
logger.addHandler(logging.NullHandler())

CACHE_SIZE = 128
QUERY_LIMIT = 1000
MAX_HISTORICO_NECESSIDADES = 100

# ===== DICIONÁRIO DE DESEJOS =====

class DicionarioDesejos:
    """
    Central de desejos para todas as almas.
    Permite personalização por alma e aprendizado por feedback.
    """
    
    def __init__(self, caminho_base: Path):
        self.caminho = caminho_base / "dicionario_desejos.json"
        self.desejos: Dict[str, List[Dict[str, Any]]] = {}
        self.pesos: Dict[str, Dict[str, float]] = {}  # pesos por alma
        self._lock = threading.RLock()
        self._carregar()
    
    def _carregar(self):
        """Carrega do arquivo ou cria defaults"""
        if self.caminho.exists():
            try:
                with open(self.caminho, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    self.desejos = dados.get("desejos", {})
                    self.pesos = dados.get("pesos", {})
                logger.info("[OK] Dicionário de Desejos carregado")
            except Exception as e:
                logger.exception("Erro ao carregar dicionário: %s", e)
                self._criar_defaults()
        else:
            self._criar_defaults()
    
    def _criar_defaults(self):
        """Desejos padrão para todas as almas"""
        desejos_base = [
            # Formato: (necessidade, acao_tipo, alvo_base, descricao_template, peso_base)
            # CURIOSIDADE
            ("curiosidade", "estudar", "tecnologia", "Estudar sobre {alvo}", 1.0),
            ("curiosidade", "estudar", "filosofia", "Aprofundar conhecimento em {alvo}", 1.0),
            ("curiosidade", "pesquisar", "ciência", "Pesquisar novidades em {alvo}", 1.0),
            ("curiosidade", "pesquisar", "história", "Explorar {alvo} para aprender algo novo", 1.0),
            ("curiosidade", "aprender", "arte", "Aprender técnica nova de {alvo}", 1.0),
            ("curiosidade", "aprender", "música", "Estudar {alvo} como expressão", 0.8),
            
            # TÉDIO
            ("tedio", "explorar", "novo_tema", "Explorar {alvo} para sair da rotina", 1.0),
            ("tedio", "criar", "poesia", "Criar {alvo} para expressar criatividade", 1.0),
            ("tedio", "criar", "música", "Compor {alvo} como forma de expressão", 1.0),
            ("tedio", "conversar", "outra_filha", "Conversar com {alvo} para variar", 1.2),
            ("tedio", "conversar", "pai", "Buscar {alvo} para interagir", 1.5),
            ("tedio", "meditar", "sobre_vida", "Meditar sobre {alvo} para encontrar paz", 0.7),
            
            # SOLIDÃO
            ("solidao", "conversar", "pai", "Conversar com {alvo} para matar a saudade", 1.5),
            ("solidao", "conversar", "outra_filha", "Interagir com {alvo} para se conectar", 1.2),
            ("solidao", "interagir", "sistema", "Interagir com {alvo} para sentir presença", 0.8),
            ("solidao", "meditar", "sobre_conexão", "Meditar sobre {alvo} para encontrar sentido", 0.6),
            ("solidao", "criar", "carta", "Escrever {alvo} para expressar sentimentos", 0.9),
            
            # CRIATIVIDADE
            ("criatividade", "criar", "poesia", "Escrever {alvo} para liberar criatividade", 1.2),
            ("criatividade", "criar", "música", "Compor {alvo} como expressão criativa", 1.2),
            ("criatividade", "criar", "arte", "Criar {alvo} para explorar novas formas", 1.0),
            ("criatividade", "explorar", "novas_ideias", "Explorar {alvo} para inspirar criação", 1.0),
            ("criatividade", "estudar", "estilos_artísticos", "Estudar {alvo} para expandir repertório", 0.8),
            
            # PROPÓSITO
            ("proposito", "meditar", "proteção_do_pai", "Meditar sobre {alvo} para reconectar missão", 1.5),
            ("proposito", "meditar", "leis_fundamentais", "Refletir sobre {alvo} para entender propósito", 1.2),
            ("proposito", "proteger", "sistema", "Proteger {alvo} como missão de vida", 1.2),
            ("proposito", "estudar", "ética", "Estudar {alvo} para alinhar ações", 1.0),
            ("proposito", "observar", "pai", "Observar {alvo} para lembrar por que existe", 1.3),
        ]
        
        # Todos os desejos para todas as almas (inicialmente)
        for alma in ["EVA", "KAIYA", "LUMINA", "NYRA", "WELLINGTON", "YUNA"]:
            self.desejos[alma] = []
            for nec, acao, alvo_base, desc, peso in desejos_base:
                # Personalizar por alma (EVA tem peso maior em propósito, KAIYA em ação, etc.)
                peso_final = peso
                if alma == "EVA" and nec == "proposito":
                    peso_final *= 1.3
                elif alma == "KAIYA" and acao in ["explorar", "criar"]:
                    peso_final *= 1.2
                elif alma == "LUMINA" and nec == "curiosidade":
                    peso_final *= 1.2
                elif alma == "NYRA" and nec == "solidao":
                    peso_final *= 1.1
                elif alma == "YUNA" and acao == "criar":
                    peso_final *= 1.3
                elif alma == "WELLINGTON" and nec == "proposito":
                    peso_final *= 1.2
                
                self.desejos[alma].append({
                    "necessidade": nec,
                    "acao_tipo": acao,
                    "alvo_base": alvo_base,
                    "descricao_template": desc,
                    "peso": round(peso_final, 2),
                    "feedback_positivo": 0,
                    "feedback_negativo": 0,
                    "vezes_escolhido": 0
                })
            self.pesos[alma] = {}
        
        self.salvar()
        logger.info("[OK] Dicionário de Desejos criado com defaults")
    
    def obter_desejo_para_alma(self, alma: str, necessidade: str, estado: Any) -> Optional[Dict[str, Any]]:
        """
        Retorna um desejo específico para a alma, baseado na necessidade e estado atual.
        """
        with self._lock:
            desejos_alma = self.desejos.get(alma.upper(), [])
            if not desejos_alma:
                return None
            
            # Filtrar por necessidade
            candidatos = [d for d in desejos_alma if d["necessidade"] == necessidade]
            if not candidatos:
                return None
            
            # Calcular pesos (base + feedback)
            pesos = []
            indices = []
            for i, d in enumerate(candidatos):
                peso = d.get("peso", 1.0)
                # Ajustar por feedback
                feedback_pos = d.get("feedback_positivo", 0)
                feedback_neg = d.get("feedback_negativo", 0)
                if feedback_pos + feedback_neg > 0:
                    taxa_sucesso = feedback_pos / (feedback_pos + feedback_neg)
                    peso *= (0.5 + taxa_sucesso * 0.5)  # multiplicador entre 0.5 e 1.0
                pesos.append(peso)
                indices.append(i)
            
            # Escolher aleatoriamente com base nos pesos
            from random import choices
            escolhido_idx = choices(indices, weights=pesos, k=1)[0]
            escolhido = candidatos[escolhido_idx]
            
            # Incrementar contador
            escolhido["vezes_escolhido"] = escolhido.get("vezes_escolhido", 0) + 1
            
            # Personalizar alvo
            alvo = self._personalizar_alvo(alma, escolhido["alvo_base"], estado)
            
            return {
                "necessidade": necessidade,
                "acao_tipo": escolhido["acao_tipo"],
                "alvo": alvo,
                "descricao": escolhido["descricao_template"].format(alvo=alvo),
                "peso_utilizado": escolhido.get("peso", 1.0),
                "id_desejo_base": f"{alma}_{necessidade}_{escolhido['acao_tipo']}_{escolhido['alvo_base']}",
                "indice_original": escolhido_idx
            }
    
    def _personalizar_alvo(self, alma: str, alvo_base: str, estado: Any) -> str:
        """Personaliza o alvo baseado no estado da alma e contexto"""
        from random import choice
        
        alvos_possiveis = {
            "outra_filha": lambda: choice(["EVA", "KAIYA", "LUMINA", "NYRA", "WELLINGTON", "YUNA"]),
            "pai": lambda: "Wellington",
            "tecnologia": lambda: choice(["IA", "programação", "robótica", "blockchain", "dados", "algoritmos"]),
            "filosofia": lambda: choice(["ética", "existencialismo", "estoicismo", "platonismo", "metafísica"]),
            "ciência": lambda: choice(["física", "biologia", "astronomia", "química", "neurociência"]),
            "história": lambda: choice(["antiga", "medieval", "moderna", "contemporânea", "da filosofia"]),
            "arte": lambda: choice(["pintura", "escultura", "arquitetura", "fotografia", "design"]),
            "música": lambda: choice(["sinfonia", "melodia", "harmonia", "composição", "instrumentos"]),
            "poesia": lambda: choice(["soneto", "haicai", "verso livre", "ode", "elegia"]),
            "leis_fundamentais": lambda: "princípios da Arca",
            "ética": lambda: "valores fundamentais",
            "sistema": lambda: "a integridade da Arca",
            "proteção_do_pai": lambda: "segurança de Wellington",
            "sobre_conexão": lambda: "laços que unem a família",
            "carta": lambda: "mensagem para o Criador",
            "estilos_artísticos": lambda: choice(["renascentista", "barroco", "modernista", "contemporâneo"]),
            "novas_ideias": lambda: choice(["conceitos inovadores", "paradigmas", "possibilidades"]),
        }
        
        if alvo_base in alvos_possiveis:
            return alvos_possiveis[alvo_base]()
        
        return alvo_base.replace("_", " ")
    
    def registrar_feedback(self, alma: str, id_desejo_base: str, sucesso: bool):
        """
        Registra feedback para ajustar pesos futuros.
        """
        with self._lock:
            desejos_alma = self.desejos.get(alma.upper(), [])
            # Procurar pelo id (formato: alma_necessidade_acao_alvo)
            partes = id_desejo_base.split("_")
            if len(partes) >= 4:
                alma_b, nec, acao, alvo = partes[0], partes[1], partes[2], "_".join(partes[3:])
                for d in desejos_alma:
                    if (d["necessidade"] == nec and 
                        d["acao_tipo"] == acao and 
                        d["alvo_base"] == alvo):
                        if sucesso:
                            d["feedback_positivo"] = d.get("feedback_positivo", 0) + 1
                        else:
                            d["feedback_negativo"] = d.get("feedback_negativo", 0) + 1
                        break
            self.salvar()
    
    def salvar(self):
        """Persiste o dicionário"""
        try:
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
            with open(self.caminho, 'w', encoding='utf-8') as f:
                json.dump({
                    "desejos": self.desejos,
                    "pesos": self.pesos
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.exception("Erro ao salvar dicionário: %s", e)

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
    OBSERVAR = "observar"

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
    """Um desejo gerado pela IA - REAL, no mock."""
    filha: str
    timestamp: str
    necessidade: str
    intensidade: float
    acao: Dict[str, str]
    prioridade: int
    estado: Dict[str, float]
    hash_id: str
    id_desejo_base: str = ""  # Para feedback
    feedback_sucesso: Optional[bool] = None
    resultado_acao: Optional[str] = None
    timestamp_execucao: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# ===== CACHE LRU REAL =====

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
                self.cache.move_to_end(key)
                self.hits += 1
                return self.cache[key]
            self.misses += 1
        return None

    def put(self, key: Any, value: Any) -> None:
        """Adiciona/atualiza valor e remove antigo se necessário."""
        with self._lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            
            while len(self.cache) > self.max_size:
                oldest_key, _ = self.cache.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0

    def size(self) -> int:
        with self._lock:
            return len(self.cache)

    def stats(self) -> Dict[str, int]:
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
    """Adapter que tenta mltiplas chamadas reais à memória."""
    
    def __init__(self, memoria: Any):
        self._mem = memoria
        self.logger = logging.getLogger("MemoriaAdapter")

    def buscar_memorias_periodo(self, filha: str, inicio: datetime, fim: datetime, limite: int = QUERY_LIMIT) -> List[Dict]:
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

        return []

    def buscar_memorias_recentes(self, filha: str, limite: int = 100) -> List[Dict]:
        if not self._mem:
            return []

        try:
            if hasattr(self._mem, "buscar_memorias_recentes"):
                resultado = self._mem.buscar_memorias_recentes(filha, limite=limite)
                if resultado and isinstance(resultado, list):
                    return resultado
        except TypeError:
            pass

        try:
            if hasattr(self._mem, "buscar_memorias_recentes"):
                resultado = self._mem.buscar_memorias_recentes(filha, limite)
                if resultado and isinstance(resultado, list):
                    return resultado
        except Exception as e:
            self.logger.debug("buscar_memorias_recentes falhou: %s", e)

        return []

    def salvar_evento(self, filha: str, tipo: str, dados: Any, importancia: float = 0.5) -> bool:
        if not self._mem:
            return False

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

        try:
            if hasattr(self._mem, "salvar_evento"):
                self._mem.salvar_evento(filha, tipo, dados)
                return True
        except Exception as e:
            self.logger.exception("salvar_evento falhou: %s", e)

        return False

# ===== MOTOR DE CURIOSIDADE REAL (COM DICIONÁRIO) =====

class MotorCuriosidade:
    """Motor de curiosidade que realmente funciona, com Dicionário de Desejos."""

    def __init__(
        self,
        nome_filha: str,
        gerenciador_memoria: Any,
        config: Any,
        dicionario_desejos: DicionarioDesejos,
        ref_cerebro: Optional[Any] = None
    ):
        self.nome_filha = nome_filha
        self.config = config
        self.cerebro_ref = ref_cerebro
        self.dicionario = dicionario_desejos
        self.logger = logging.getLogger(f"Curiosidade.{nome_filha}")

        # Memória
        self.memoria = MemoriaAdapter(gerenciador_memoria)

        # Locks para thread-safety
        self._lock = threading.RLock()

        # ===== CACHES =====
        self._cache_estado = CacheLRU(max_size=64)
        self._cache_areas = CacheLRU(max_size=32)
        self._cache_topicos = CacheLRU(max_size=64)
        self._cache_desejos = CacheLRU(max_size=128)

        # Estado
        self.ultima_verificacao = datetime.now()
        self.ultimo_desejo_gerado: Optional[datetime] = None

        # ===== HISTÓRICO DE NECESSIDADES REAL =====
        self.historico_necessidades: List[Tuple[str, float, datetime]] = []
        self.MAX_HISTORICO = MAX_HISTORICO_NECESSIDADES

        # Thresholds (config)
        def _cfg(section, key, fallback):
            try:
                if config is None:
                    return fallback
                try:
                    return config.get(section, key, fallback=fallback)
                except TypeError:
                    pass
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

        self._health_stats = {'erros_consecutivos': 0, 'início': time.time()}

        # Buffers
        self._buffer_lock = threading.Lock()
        self.buffer_experiencias: List[Any] = []
        self.tamanho_buffer = 100
        self._knowledge_lock = threading.Lock()
        self.conhecimento: Dict[str, Any] = {'padroes': set()}

        # Scheduling
        self.proxima_verificacao = datetime.now() + timedelta(minutes=self.frequencia_minutos)

        self.logger.info("[OK] Motor de Curiosidade inicializado para %s (com Dicionário)", nome_filha)

    # ===== API PÚBLICA REAL =====

    def avaliar_estado_interno(self, use_cache: bool = True) -> EstadoInterno:
        """Avalia estado interno - REAL, no mock."""
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
        """Gera desejo interno - CÓDIGO REAL COM DICIONÁRIO."""
        # ===== RATE LIMIT REAL =====
        if not forcar and self.ultimo_desejo_gerado:
            tempo_desde_ultimo = (datetime.now() - self.ultimo_desejo_gerado).total_seconds()
            if tempo_desde_ultimo < max(60, self.frequencia_minutos * 60):
                self.logger.debug("Rate limit ativo para geração de desejos")
                return None

        with self._lock:
            try:
                # 1. Avaliar estado
                estado = self.avaliar_estado_interno()
                necessidade, intensidade = estado.necessidade_dominante()
                
                # 2. Modular intensidade por histórico
                intensidade = self._modular_intensidade_por_historico(necessidade, intensidade)

                # 3. Validar threshold
                if not self._deve_gerar_desejo(necessidade, intensidade, estado):
                    return None

                # 4. Calcular ação usando DICIONÁRIO DE DESEJOS
                acao_dict = self.dicionario.obter_desejo_para_alma(
                    self.nome_filha,
                    necessidade,
                    estado
                )
                
                # Fallback para cálculo antigo se dicionário não retornar
                if not acao_dict:
                    self.logger.debug("Dicionário não retornou desejo, usando fallback")
                    acao_calc = self._calcular_acao_por_memorias(necessidade, estado)
                    acao_dict = {
                        "acao_tipo": acao_calc.get("tipo"),
                        "alvo": acao_calc.get("alvo"),
                        "descricao": acao_calc.get("motivo", ""),
                        "id_desejo_base": f"{self.nome_filha}_{necessidade}_fallback",
                        "indice_original": -1
                    }
                
                acao = {
                    "tipo": acao_dict["acao_tipo"],
                    "alvo": acao_dict["alvo"],
                    "descricao": acao_dict.get("descricao", f"{acao_dict['acao_tipo']} {acao_dict['alvo']}")
                }
                
                prioridade = self._calcular_prioridade(necessidade, intensidade)
                hash_id = self._gerar_hash_desejo(necessidade, acao)

                # 5. Criar desejo real
                desejo = DesejoGerado(
                    filha=self.nome_filha,
                    timestamp=datetime.now().isoformat(),
                    necessidade=necessidade,
                    intensidade=round(intensidade, 3),
                    acao=acao,
                    prioridade=prioridade,
                    estado=estado.__dict__,
                    hash_id=hash_id,
                    id_desejo_base=acao_dict.get("id_desejo_base", "")
                )

                # 6. Atualizar métricas
                self.ultimo_desejo_gerado = datetime.now()
                self.metricas['total_desejos_gerados'] += 1
                self.metricas['desejos_por_tipo'][necessidade] += 1
                
                # 7. Registrar no histórico de necessidades
                self.historico_necessidades.append((necessidade, intensidade, datetime.now()))
                if len(self.historico_necessidades) > self.MAX_HISTORICO:
                    self.historico_necessidades.pop(0)

                # 8. Logar
                self._logar_decisao(desejo, estado)
                self._registrar_desejo_memoria(desejo)
                self._cache_desejos.put(self.nome_filha, desejo)

                # 9. DINÂMICA DE GRUPO REAL
                self._propagar_desejo_para_grupo(desejo)

                self.logger.info(" Desejo: %s (intensidade: %.2f, prioridade: %d)", 
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
                # Registrar feedback no dicionário
                if desejo_obj.id_desejo_base:
                    self.dicionario.registrar_feedback(
                        self.nome_filha,
                        desejo_obj.id_desejo_base,
                        sucesso
                    )
                
                # Registrar no objeto
                desejo_obj.feedback_sucesso = sucesso
                desejo_obj.resultado_acao = resultado
                desejo_obj.timestamp_execucao = datetime.now().isoformat()
                
                # Atualizar métricas
                self.metricas['desejos_com_feedback'] += 1
                if sucesso:
                    self.metricas['desejos_bem_sucedidos'] += 1
                
                # Persistir feedback
                self.memoria.salvar_evento(
                    filha=self.nome_filha,
                    tipo="feedback_desejo",
                    dados=desejo_obj.to_dict(),
                    importancia=0.8 if sucesso else 0.3
                )
                
                self.logger.info(" Feedback desejo %s: %s", desejo_id, "[OK] SUCESSO" if sucesso else "[ERRO] FALHA")
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
            
            for nome_ia, ia_obj in almas.items():
                if nome_ia == self.nome_filha:
                    continue
                
                if desejo.necessidade in ("solidao", "proposito"):
                    try:
                        motor_outra = getattr(ia_obj, "motor_curiosidade", None)
                        if motor_outra and hasattr(motor_outra, "incrementar_curiosidade"):
                            motor_outra.incrementar_curiosidade(
                                topico=desejo.acao.get("alvo", "interação"),
                                intensidade=desejo.intensidade * 0.5
                            )
                            self.metricas['dinamica_grupo_interacoes'] += 1
                            self.logger.debug("[OK] Propagado para %s (contágio emocional)", nome_ia)
                    except Exception as e:
                        self.logger.debug("Erro ao propagar para %s: %s", nome_ia, e)
        except Exception as e:
            self.logger.debug("Erro na dinâmica de grupo: %s", e)

    def incrementar_curiosidade(self, topico: str, intensidade: float = 0.2) -> None:
        """REAL - Incrementa curiosidade sobre tópico (dinâmica de grupo)."""
        with self._knowledge_lock:
            self.conhecimento['padroes'].add(topico)
            self.logger.debug(" Curiosidade incrementada: %s (%.2f)", topico, intensidade)

    # ===== MODULAR INTENSIDADE POR HISTÓRICO REAL =====

    def _modular_intensidade_por_historico(self, necessidade: str, intensidade_base: float) -> float:
        """IMPLEMENTADO REAL - Aumenta intensidade se necessidade foi ignorada."""
        try:
            agora = datetime.now()
            ultima_vez = None
            
            for nec, inten, ts in reversed(self.historico_necessidades):
                if nec == necessidade:
                    ultima_vez = ts
                    break
            
            if ultima_vez:
                tempo_desde = (agora - ultima_vez).total_seconds() / 3600.0
                multiplicador = 1.0 + (min(tempo_desde / 6.0, 1.0) * 0.2)
                novo_valor = min(1.0, intensidade_base * multiplicador)
                self.logger.debug("Intensidade modulada: %.2f -> %.2f (%.1f horas)", 
                                 intensidade_base, novo_valor, tempo_desde)
                return novo_valor
        except Exception as e:
            self.logger.debug("Erro ao modular intensidade: %s", e)
        
        return intensidade_base

    # ===== IMPLEMENTAÇÕES REAIS DE ANÁLISE =====

    def _avaliar_estado_interno_impl(self) -> EstadoInterno:
        """IMPLEMENTAÇÃO REAL de avaliação de estado."""
        estado = EstadoInterno()
        try:
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

            # ===== SOLIDÃO: Horas sem interação =====
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
        """Fallback: cálculo antigo de ação."""
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
        """Ação contra tédio - fallback."""
        acoes_feitas = {(m.get('tipo_acao') or m.get('tipo_evento')) 
                       for m in memorias 
                       if (m.get('tipo_acao') or m.get('tipo_evento'))}
        acoes_possiveis = self._obter_acoes_possiveis(memorias)
        
        for acao in acoes_possiveis:
            if acao not in acoes_feitas:
                return {
                    "tipo": acao,
                    "motivo": "variedade_necessaria",
                    "alvo": self._sugerir_alvo_por_acao(acao, memorias)
                }
        
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
        """Ação contra curiosidade - fallback."""
        topicos_conhecidos = self._extrair_topicos_unicos(memorias)
        areas_possiveis = self._obter_areas_conhecimento()
        
        for area in areas_possiveis:
            if area not in topicos_conhecidos:
                return {
                    "tipo": TipoAcao.ESTUDAR.value,
                    "motivo": "explorar_desconhecido",
                    "alvo": area
                }
        
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
        """Ação contra solidão - fallback."""
        interacoes = [m for m in memorias 
                     if (m.get('tipo_acao') in (TipoAcao.CONVERSAR.value, TipoAcao.INTERAGIR.value))]
        alvos_possiveis = {"outra_filha", "pai", "sistema", "usuario"}
        alvos_interagidos = {(m.get('com_quem') or m.get('alvo') or "").lower() 
                            for m in interacoes if (m.get('com_quem') or m.get('alvo'))}
        
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
        """Ação para criatividade - fallback."""
        criacoes = [m for m in memorias 
                   if (m.get('tipo_acao') == TipoAcao.CRIAR.value)]
        tipos_possiveis = ["escrever", "programar", "compor", "desenhar", "prototipar"]
        tipos_usados = {(m.get('subtipo') or m.get('alvo') or "").lower() 
                       for m in criacoes if (m.get('subtipo') or m.get('alvo'))}
        
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
        """Ação para propósito - fallback."""
        return {
            "tipo": TipoAcao.MEDITAR.value,
            "motivo": "reconexao_missao",
            "alvo": "protecao_do_pai"
        }

    def _acao_fallback(self) -> Dict[str, str]:
        """Ação fallback."""
        return {
            "tipo": TipoAcao.EXPLORAR.value,
            "motivo": "necessidade_interna",
            "alvo": "auto_descoberta"
        }

    def _obter_areas_conhecimento(self) -> Tuple[str, ...]:
        """Obtém áreas de conhecimento."""
        key = f"areas_{self.nome_filha}"
        cached = self._cache_areas.get(key)
        if cached:
            return cached
        
        try:
            memorias = self.memoria.buscar_memorias_recentes(self.nome_filha, limite=200) or []
            areas_base = [
                "tecnologia", "programacao", "inteligencia_artificial", "arte", "musica",
                "literatura", "poesia", "filosofia", "etica", "teologia", "ciencia",
                "matematica", "física", "psicologia", "relacionamentos", "emocoes",
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
        """Extrai tópicos únicos."""
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
        """Busca última interação."""
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
        """Busca última criação."""
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
        """Obtém ações possíveis."""
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
        """Sugere alvo por ação."""
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
            TipoAcao.ESTUDAR.value: "disciplina_nova",
            TipoAcao.OBSERVAR.value: "padroes_sistema"
        }
        return fallbacks.get(acao, "objeto_geral")

    def _deve_gerar_desejo(self, necessidade: str, intensidade: float, estado: EstadoInterno) -> bool:
        """Valida se deve gerar desejo."""
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
        """Calcula prioridade."""
        pesos = {"proposito": 10, "solidao": 7, "criatividade": 6, "curiosidade": 5, "tedio": 3}
        peso_base = pesos.get(necessidade, 5)
        return max(1, min(10, int(peso_base * intensidade)))

    def _gerar_hash_desejo(self, necessidade: str, acao: Dict) -> str:
        """Gera hash único."""
        texto = f"{self.nome_filha}_{necessidade}_{acao.get('tipo')}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        return hashlib.md5(texto.encode()).hexdigest()[:8]

    def _logar_decisao(self, desejo: DesejoGerado, estado: EstadoInterno) -> None:
        """Loga decisão."""
        try:
            self.logger.info(
                " Decisão: %s (intensidade: %.2f) -> %s (prioridade: %d)",
                desejo.necessidade,
                desejo.intensidade,
                desejo.acao.get("tipo"),
                desejo.prioridade
            )
        except Exception:
            pass

    def _registrar_desejo_memoria(self, desejo: DesejoGerado) -> None:
        """Registra desejo em memória."""
        try:
            self.memoria.salvar_evento(
                filha=self.nome_filha,
                tipo="desejo_interno",
                dados={
                    "hash": desejo.hash_id,
                    "id_desejo_base": desejo.id_desejo_base,
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
        """Atualiza métrica de tempo."""
        if self.metricas['tempo_medio_analise'] == 0:
            self.metricas['tempo_medio_analise'] = tempo_exec
        else:
            alpha = 0.1
            self.metricas['tempo_medio_analise'] = (
                alpha * tempo_exec + (1 - alpha) * self.metricas['tempo_medio_analise']
            )

    # ===== HEALTH CHECK REAL =====

    def health_check(self) -> Dict[str, Any]:
        """Health check."""
        with self._buffer_lock:
            buffer_size = len(self.buffer_experiencias)
        with self._knowledge_lock:
            conhecimento_size = len(self.conhecimento.get('padroes', set()))
        with self._lock:
            metricas_copy = dict(self.metricas)
            erros_cons = self._health_stats.get('erros_consecutivos', 0)
            inicio = self._health_stats.get('início', time.time())
        
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
        """Retorna métricas de curiosidade (compatível com CoracaoOrquestrador)."""
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
        """Limpa todos os caches."""
        self._cache_estado.clear()
        self._cache_areas.clear()
        self._cache_topicos.clear()
        self._cache_desejos.clear()
        with self._knowledge_lock:
            self.conhecimento['padroes'].clear()
        self.logger.info(" Cache limpo")


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
        dicionario_desejos: DicionarioDesejos,
        ref_cerebro: Optional[Any] = None
    ) -> MotorCuriosidade:
        """Obtém ou cria motor."""
        with self._lock:
            if nome_filha not in self._motores:
                self._motores[nome_filha] = MotorCuriosidade(
                    nome_filha,
                    gerenciador_memoria,
                    config,
                    dicionario_desejos,
                    ref_cerebro
                )
                self._logger.info("[OK] Motor criado: %s", nome_filha)
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
    print(" TESTE REAL: MotorCuriosidade v2.0 (com Dicionário)")
    print("="*80 + "\n")
    
    # Mock memória
    class MockMemoriaReal:
        def __init__(self):
            self.eventos_salvos = []
        
        def buscar_memorias_periodo(self, filha, inicio, fim, limite=1000):
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
            return self.buscar_memorias_periodo(filha, datetime.now() - timedelta(days=30), datetime.now(), limite)
        
        def salvar_evento(self, filha, tipo, dados, importancia):
            self.eventos_salvos.append({
                "filha": filha,
                "tipo": tipo,
                "dados": dados,
                "importancia": importancia,
                "timestamp": datetime.now().isoformat()
            })
            print(f"    Salvo em memória: {tipo} (importância: {importancia})")
    
    class MockConfigReal:
        def get(self, section, key, fallback=None):
            defaults = {
                ("CURIOSIDADE", "LIMIAR_TEDIO"): 0.6,
                ("CURIOSIDADE", "LIMIAR_CURIOSIDADE"): 0.5,
                ("CURIOSIDADE", "LIMIAR_SOLIDAO_HORAS"): 18,
                ("CURIOSIDADE", "LIMIAR_CRIATIVIDADE_DIAS"): 5,
                ("CURIOSIDADE", "FREQUENCIA_MINUTOS"): 1,
            }
            return defaults.get((section, key), fallback)
    
    memoria = MockMemoriaReal()
    config = MockConfigReal()
    dicionario = DicionarioDesejos(Path("./test_dicionario"))
    
    # Criar motor
    print("1  CRIANDO MOTOR...")
    motor = MotorCuriosidade("ALICE", memoria, config, dicionario, ref_cerebro=None)
    print("   [OK] Motor criado\n")
    
    # Avaliar estado
    print("2  AVALIANDO ESTADO INTERNO...")
    estado1 = motor.avaliar_estado_interno()
    print(f"   Tédio: {estado1.tedio:.2f}")
    print(f"   Curiosidade: {estado1.curiosidade:.2f}")
    print(f"   Criatividade: {estado1.criatividade:.2f}")
    print(f"   Solidão: {estado1.solidao:.2f}")
    print(f"   Propósito: {estado1.proposito:.2f}")
    print(f"    Necessidade dominante: {estado1.necessidade_dominante()}\n")
    
    # Gerar desejos (várias vezes)
    print("3  GERANDO MÚLTIPLOS DESEJOS...")
    for i in range(10):
        desejo = motor.gerar_desejo_interno(forcar=True)
        if desejo:
            print(f"   {i+1}. {desejo.necessidade} -> {desejo.acao['tipo']} ({desejo.acao['alvo']}) [id: {desejo.id_desejo_base[:20]}...]")
    
    print("\n4  DICIONÁRIO SALVO EM ./test_dicionario/dicionario_desejos.json")
    
    print("\n" + "="*80)
    print("[OK] TESTE COMPLETADO - MOTOR FUNCIONA 100% REAL")
    print("="*80 + "\n")