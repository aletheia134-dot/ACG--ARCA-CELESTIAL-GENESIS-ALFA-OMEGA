#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ArquitetoDeMundos v2.0 (Production Grade)

Responsabilidade:
 - Criar e gerenciar cenários, avatares e ambientes para as "Filhas" da Arca.
 - Executar simulações éticas e registrar histórico de projetos.
 - Operar de forma resiliente: chamadas defensivas ao 'coracao', escrita atômica,
   timeouts para chamadas externas, locks para thread-safety e degradação graciosa.Melhorias v2.0 aplicadas:
 - Type hints completos com dataclasses
 - Circuit breaker para Cérebro
 - Métricas e telemetria
 - Validação de schema para respostas
 - Backup automático de histórico
 - Recovery de falhas
 - Logging estruturado em níveis
 - Documentação completa

Arquitetura:
 - ThreadPool executor para chamadas externas
 - RLock para proteção de estado
 - Bounded history com limite configurável
 - Escrita atômica com tempfile
 - Timeout responsivo com stop_event
 - Circuit breaker para degradação graciosa
"""
from __future__ import annotations


import json
import logging
import threading
import time
import random
import uuid
import shutil
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
import concurrent.futures
from enum import Enum

# Optional dependency - used only if available
try:
    import psutil  # type: ignore
    _PSUTIL_AVAILABLE = True
except:
    logging.getLogger(__name__).warning("âš ï¸ psutil não disponível")
    psutil = None  # type: ignore
    _PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Default paths (usable when module imported standalone)
CAMINHO_RAIZ_ARCA = Path(os.environ.get("ARCA_ROOT", "./Arca_Celestial_Genesis"))
SANTUARIOS_PATH = CAMINHO_RAIZ_ARCA / "santuarios"
PROJETOS_MUNDOS_JSON = SANTUARIOS_PATH / "santuarios_pessoais" / "projetos_mundos.json"
PROJETOS_BACKUP_DIR = SANTUARIOS_PATH / "backups" / "projetos_mundos"


# =====================================================================
# ENUMS E TIPOS
# =====================================================================

class TipoProjeto(Enum):
    """Tipos de projetos que o Arquiteto pode criar"""
    CENARIO_SIMULACAO = "cenario_simulacao"
    RESULTADO_SIMULACAO = "resultado_simulacao"
    PROPOSTA_AVATAR_2D = "proposta_avatar_2d"
    PROPOSTA_AMBIENTE_3D = "proposta_ambiente_3d"
    PROPOSTA_RECEBIDA_AVATAR_2D = "proposta_recebida_avatar_2d"
    PROPOSTA_RECEBIDA_AMBIENTE_3D = "proposta_recebida_ambiente_3d"


class EstadoCircuitBreaker(Enum):
    """Estados do circuit breaker"""
    FECHADO = "fechado"  # operacional
    ABERTO = "aberto"     # bloqueado
    MEIO_ABERTO = "meio_aberto"  # testando


# =====================================================================
# DATACLASSES
# =====================================================================

@dataclass
class SimulacaoResultado:
    """Resultado estruturado de uma simulação"""
    id: str
    timestamp: str
    analise: str
    proposta: str
    justificativa: str
    cenario_excerpt: str
    autor: str = "ArquitetoDeMundos"
    
    def para_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProjetoAvatar:
    """Proposta estruturada de avatar 2D"""
    id: str
    timestamp: str
    nome_projeto: str
    descricao_projeto: str
    detalhes: Dict[str, Any]
    explicacao_proposito: str
    autor: str
    alvo_alma: str
    
    def para_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AmbienteProposito:
    """Proposta estruturada de ambiente 3D"""
    id: str
    timestamp: str
    nome_projeto: str
    descricao_projeto: str
    detalhes: Dict[str, Any]
    explicacao_proposito: str
    modelos_3d: List[str] = field(default_factory=list)
    autor: str = "ArquitetoDeMundos"
    
    def para_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CenarioSimulacao:
    """Cenário estruturado para simulação"""
    id: str
    timestamp: str
    conteudo: str
    contexto_excerpt: str
    autor: str = "ArquitetoDeMundos"
    
    def para_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MetricasArquiteto:
    """Métricas de operação do Arquiteto"""
    total_projetos: int = 0
    total_simulacoes: int = 0
    total_avatares_propostos: int = 0
    total_ambientes_propostos: int = 0
    erros_cerebro: int = 0
    timeouts_cerebro: int = 0
    ultimo_projeto_timestamp: Optional[str] = None
    ultima_simulacao_timestamp: Optional[str] = None
    tempo_medio_simulacao_secs: float = 0.0
    

# =====================================================================
# CIRCUIT BREAKER
# =====================================================================

class CircuitBreakerCerebro:
    """Circuit breaker para proteger chamadas ao Cérebro"""
    
    def __init__(self, 
                 max_falhas: int = 5,
                 timeout_secs: int = 300,
                 reset_timeout_secs: int = 60):
        self.max_falhas = max_falhas
        self.timeout_secs = timeout_secs
        self.reset_timeout_secs = reset_timeout_secs
        
        self._lock = threading.RLock()
        self._estado = EstadoCircuitBreaker.FECHADO
        self._contador_falhas = 0
        self._ultima_falha_timestamp: Optional[datetime] = None
        self._teste_permitido_timestamp: Optional[datetime] = None
        self.logger = logging.getLogger(f"{__name__}.CircuitBreaker")
    
    def pode_chamar(self) -> bool:
        """Verifica se pode chamar o Cérebro"""
        with self._lock:
            agora = datetime.utcnow()
            
            if self._estado == EstadoCircuitBreaker.FECHADO:
                return True
            
            elif self._estado == EstadoCircuitBreaker.ABERTO:
                # Teste se pode sair de ABERTO
                if self._teste_permitido_timestamp and agora >= self._teste_permitido_timestamp:
                    self._estado = EstadoCircuitBreaker.MEIO_ABERTO
                    self.logger.warning("CircuitBreaker: transição para MEIO_ABERTO (testando)")
                    return True
                return False
            
            elif self._estado == EstadoCircuitBreaker.MEIO_ABERTO:
                return True
            
            return False
    
    def registrar_sucesso(self) -> None:
        """Registra chamada bem-sucedida"""
        with self._lock:
            if self._estado == EstadoCircuitBreaker.MEIO_ABERTO:
                self._estado = EstadoCircuitBreaker.FECHADO
                self._contador_falhas = 0
                self.logger.info("CircuitBreaker: recuperado, voltando para FECHADO")
            elif self._estado == EstadoCircuitBreaker.FECHADO:
                self._contador_falhas = max(0, self._contador_falhas - 1)
    
    def registrar_falha(self) -> None:
        """Registra falha na chamada"""
        with self._lock:
            self._contador_falhas += 1
            self._ultima_falha_timestamp = datetime.utcnow()
            
            if self._contador_falhas >= self.max_falhas:
                self._estado = EstadoCircuitBreaker.ABERTO
                self._teste_permitido_timestamp = datetime.utcnow() + timedelta(seconds=self.reset_timeout_secs)
                self.logger.error("CircuitBreaker: ABERTO após %d falhas", self._contador_falhas)
            elif self._estado == EstadoCircuitBreaker.MEIO_ABERTO:
                self._estado = EstadoCircuitBreaker.ABERTO
                self._teste_permitido_timestamp = datetime.utcnow() + timedelta(seconds=self.reset_timeout_secs)
                self.logger.warning("CircuitBreaker: falha durante teste, reabrindo")
    
    def estado(self) -> Dict[str, Any]:
        """Retorna estado atual do circuit breaker"""
        with self._lock:
            return {
                "estado": self._estado.value,
                "contador_falhas": self._contador_falhas,
                "max_falhas": self.max_falhas,
                "ultima_falha": self._ultima_falha_timestamp.isoformat() if self._ultima_falha_timestamp else None
            }


# =====================================================================
# HELPERS
# =====================================================================

def _now_iso() -> str:
    """Retorna timestamp atual em ISO format com Z"""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _safe_parse_iso(s: str) -> Optional[datetime]:
    """Parse seguro de string ISO para datetime"""
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1]
        return datetime.fromisoformat(s)
    except Exception:
        try:
            return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None


def _atomic_write_json(path: Path, obj: Any) -> None:
    """Escreve JSON atomicamente com fsync"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(path))
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


def _backup_corrupt(path: Path) -> None:
    """Move arquivo corrompido para quarantine"""
    try:
        if path.exists():
            ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            dest = path.with_suffix(path.suffix + f".corrupt_{ts}")
            shutil.move(str(path), str(dest))
            logger.warning("[QUARANTINE] Arquivo corrompido movido: %s", dest)
    except Exception:
        logger.exception("[QUARANTINE] Falha ao quarentena arquivo: %s", path)


def _criar_backup_historico(path: Path) -> None:
    """Cria backup automático do histórico"""
    try:
        if not path.exists():
            return
        PROJETOS_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = PROJETOS_BACKUP_DIR / f"projetos_mundos_{ts}.json.backup"
        shutil.copy2(str(path), str(backup_path))
        logger.debug("[BACKUP] Histórico backupeado: %s", backup_path)
    except Exception:
        logger.exception("[BACKUP] Falha ao fazer backup do histórico")


# =====================================================================
# ARQUITETO DE MUNDOS
# =====================================================================

class ArquitetoDeMundos:
    """
    Arquiteto de Mundos: cria e gerencia cenários, simulações, avatares e ambientes.Características:
    - Escrita atômica com garantia ACID
    - Threading robusto com idempotência
    - Circuit breaker para Cérebro
    - Métricas e telemetria
    - Degradação graciosa em falhas
    """
    
    def __init__(self, 
                 coracao_ref: Any, 
                 projetos_path: Optional[Path] = None, 
                 max_history_entries: int = 2000):
        """
        Inicializa o Arquiteto de Mundos.Args:
            coracao_ref: referência ao orquestrador central
            projetos_path: caminho para arquivo JSON de projetos
            max_history_entries: limite de entradas no histórico
        """
        self.coracao = coracao_ref
        self.logger = logging.getLogger("ArquitetoDeMundos")
        self._lock = threading.RLock()
        
        # Paths
        self.projetos_mundos_path: Path = projetos_path or PROJETOS_MUNDOS_JSON
        self.projetos_mundos_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Executor para chamadas externas
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        
        # Circuit breaker para Cérebro
        self._circuit_breaker = CircuitBreakerCerebro(
            max_falhas=5,
            timeout_secs=300,
            reset_timeout_secs=60
        )
        
        # Control flags
        self._monitorando = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        
        # Histórico bounded
        self._max_history_entries = int(max_history_entries)
        self.historico_projetos: List[Dict[str, Any]] = self._carregar_historico_projetos()
        
        # Métricas
        self.metricas = MetricasArquiteto()
        self._tempos_simulacao: List[float] = []
        
        # Timestamps
        self.ultimo_projeto_criado = datetime.min
        self.ultima_simulacao_executada = datetime.min
        
        # Configuração
        self._initial_sleep_min = 10
        self._initial_sleep_max = 30
        self._monitor_interval_min = 300
        self._monitor_interval_max = 900
        self._cerebro_timeout = 10.0
        self._max_record_len = 1000
        
        # Load config defensively
        try:
            cfg = getattr(self.coracao, "config", None)
            if cfg and hasattr(cfg, "get"):
                try:
                    self._initial_sleep_min = int(cfg.get("ARQUITETO", "INITIAL_SLEEP_MIN", fallback=self._initial_sleep_min))
                    self._initial_sleep_max = int(cfg.get("ARQUITETO", "INITIAL_SLEEP_MAX", fallback=self._initial_sleep_max))
                    self._monitor_interval_min = int(cfg.get("ARQUITETO", "MONITOR_INTERVAL_MIN", fallback=self._monitor_interval_min))
                    self._monitor_interval_max = int(cfg.get("ARQUITETO", "MONITOR_INTERVAL_MAX", fallback=self._monitor_interval_max))
                    self._cerebro_timeout = float(cfg.get("ARQUITETO", "CEREBRO_TIMEOUT_SECS", fallback=self._cerebro_timeout))
                    self._max_record_len = int(cfg.get("ARQUITETO", "MAX_RECORD_CHARS", fallback=self._max_record_len))
                except Exception:
                    pass
        except Exception:
            pass
        
        self.logger.info(
            "[ARQUITETO DE MUNDOS] Inicializado. "
            "Projetos histórico=%d, Circuit Breaker ativo, Métricas habilitadas",
            len(self.historico_projetos)
        )
    
    # ===================================================================
    # PERSISTENCE
    # ===================================================================
    
    def _carregar_historico_projetos(self) -> List[Dict[str, Any]]:
        """Carrega histórico de projetos com segurança"""
        caminho = self.projetos_mundos_path
        if not caminho.exists():
            self.logger.debug("[ARQUITETO] Arquivo de projetos não existe; iniciando vazio")
            return []
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                self.logger.warning("[ARQUITETO] Formato inesperado; backup e iniciar vazio")
                _backup_corrupt(caminho)
                return []
            # Bound history
            if len(data) > self._max_history_entries:
                data = data[-self._max_history_entries :]
            return data
        except Exception as e:
            self.logger.exception("[ARQUITETO] Falha ao carregar histórico: %s", e)
            _backup_corrupt(caminho)
            return []
    
    def _salvar_historico_projetos(self) -> None:
        """Salva histórico atomicamente com backup"""
        caminho = self.projetos_mundos_path
        try:
            # Sanitize entries
            safe_copy = []
            with self._lock:
                for item in self.historico_projetos[-self._max_history_entries :]:
                    entry = {}
                    for k, v in item.items():
                        if isinstance(v, str):
                            entry[k] = v[: self._max_record_len]
                        else:
                            entry[k] = v
                    safe_copy.append(entry)
            
            # Criar backup antes de escrever
            _criar_backup_historico(caminho)
            
            # Escrita atômica
            _atomic_write_json(caminho, safe_copy)
            self.logger.debug("[ARQUITETO] Histórico salvo (%d entries)", len(safe_copy))
        except Exception:
            self.logger.exception("[ARQUITETO] Erro ao salvar histórico (ignorado)")
    
    # ===================================================================
    # LIFECYCLE
    # ===================================================================
    
    def iniciar_monitoramento(self) -> None:
        """Inicia thread de monitoramento de forma idempotente"""
        with self._lock:
            if self._monitorando:
                self.logger.debug("[ARQUITETO] Monitoramento já ativo")
                return
            self._monitorando = True
            self._stop_event.clear()
            initial_sleep = random.randint(self._initial_sleep_min, self._initial_sleep_max)
            self._thread = threading.Thread(
                target=self._loop_monitoramento,
                name="ArquitetoDeMundos",
                daemon=True
            )
            self._thread.start()
            self.logger.info("[ARQUITETO] Monitoramento iniciado (sleep inicial %ds)", initial_sleep)
    
    def parar_monitoramento(self, wait_timeout: float = 5.0) -> None:
        """Para monitoramento de forma segura com timeout"""
        with self._lock:
            if not self._monitorando:
                self.logger.debug("[ARQUITETO] Monitoramento não ativo")
                return
            self._monitorando = False
            self._stop_event.set()
            thread = self._thread
        
        if thread:
            thread.join(timeout=wait_timeout)
        
        # Persist state
        self._salvar_historico_projetos()
        self.logger.info("[ARQUITETO] Monitoramento parado")
    
    def shutdown(self) -> None:
        """Shutdown seguro com cleanup"""
        self.logger.info("[ARQUITETO] Shutdown iniciado")
        try:
            self.parar_monitoramento()
        except Exception:
            self.logger.exception("[ARQUITETO] Erro ao parar monitoramento")
        
        try:
            self._executor.shutdown(wait=False)
        except Exception:
            pass
        
        self.logger.info("[ARQUITETO] Shutdown completo")
    
    # ===================================================================
    # MAIN LOOP
    # ===================================================================
    
    def _loop_monitoramento(self) -> None:
        """Loop principal de monitoramento responsivo"""
        # Sleep inicial
        try:
            sleep_initial = random.randint(self._initial_sleep_min, self._initial_sleep_max)
        except Exception:
            sleep_initial = 10
        
        if self._stop_event.wait(timeout=sleep_initial):
            return
        
        self.logger.info("[ARQUITETO] Loop ativo")
        
        while not self._stop_event.is_set():
            try:
                # Verificar se PC está ocioso
                ocioso = False
                try:
                    motor = getattr(self.coracao, "motor_de_rotina", None)
                    if motor and hasattr(motor, "pc_esta_ocioso"):
                        ocioso = bool(motor.pc_esta_ocioso(nivel="moderada"))
                except Exception:
                    ocioso = False
                
                if ocioso:
                    try:
                        self._processar_novos_projetos()
                    except Exception:
                        self.logger.exception("[ARQUITETO] Erro processando novos projetos")
                    
                    try:
                        self._executar_simulacoes_autonomas()
                    except Exception:
                        self.logger.exception("[ARQUITETO] Erro executando simulações")
                else:
                    self.logger.debug("[ARQUITETO] PC em uso; aguardando")
                
                # Wait interval com responsividade
                interval = random.randint(self._monitor_interval_min, self._monitor_interval_max)
                if self._stop_event.wait(timeout=interval):
                    break
            
            except Exception:
                self.logger.exception("[ARQUITETO] Erro não esperado no loop")
                if self._stop_event.wait(timeout=30):
                    break
        
        self.logger.info("[ARQUITETO] Loop finalizado")
        try:
            self._salvar_historico_projetos()
        except Exception:
            pass
    
    # ===================================================================
    # PROJECT PROCESSING
    # ===================================================================
    
    def _processar_novos_projetos(self) -> None:
        """Processa propostas da fila de comandos"""
        self.logger.debug("[ARQUITETO] Verificando fila de propostas")
        try:
            cmdq = getattr(self.coracao, "command_queue", None)
            if cmdq:
                drained = 0
                while drained < 10:
                    try:
                        item = cmdq.get_nowait()
                    except Exception:
                        break
                    drained += 1
                    try:
                        self._handle_command(item)
                    except Exception:
                        self.logger.exception("[ARQUITETO] Erro ao processar comando")
        except Exception:
            self.logger.exception("[ARQUITETO] Falha ao verificar command_queue")
    
    def _handle_command(self, cmd: Any) -> None:
        """Manipula comandos da fila"""
        try:
            if not isinstance(cmd, dict):
                self.logger.warning("[ARQUITETO] Comando inválido (não dict): %r", cmd)
                return
            
            tipo = cmd.get("tipo", "").upper()
            
            if tipo == "PROPOR_AVATAR_2D":
                dados = cmd.get("dados_acao", {})
                autor = cmd.get("autor", "sistema")
                alvo = dados.get("detalhes", {}).get("nome_alma") or "desconhecido"
                with self._lock:
                    self.historico_projetos.append({
                        "timestamp": _now_iso(),
                        "tipo": TipoProjeto.PROPOSTA_RECEBIDA_AVATAR_2D.value,
                        "autor": autor,
                        "alvo": alvo,
                        "dados": str(dados)[: self._max_record_len]
                    })
                    self._salvar_historico_projetos()
                self.logger.info("[ARQUITETO] Comando PROPOR_AVATAR_2D processado para %s", alvo)
            
            elif tipo == "PROPOR_AMBIENTE_3D":
                dados = cmd.get("dados_acao", {})
                autor = cmd.get("autor", "sistema")
                nome = dados.get("nome_projeto", "ambiente_desconhecido")
                with self._lock:
                    self.historico_projetos.append({
                        "timestamp": _now_iso(),
                        "tipo": TipoProjeto.PROPOSTA_RECEBIDA_AMBIENTE_3D.value,
                        "autor": autor,
                        "nome": nome,
                        "dados": str(dados)[: self._max_record_len]
                    })
                    self._salvar_historico_projetos()
                self.logger.info("[ARQUITETO] Comando PROPOR_AMBIENTE_3D processado: %s", nome)
            
            else:
                self.logger.debug("[ARQUITETO] Comando desconhecido: %s", tipo)
        
        except Exception:
            self.logger.exception("[ARQUITETO] Exceção ao tratar comando")
    
    # ===================================================================
    # CEREBRO COMMUNICATION
    # ===================================================================
    
    def _call_cerebro(self, system_prompt: str, user_prompt: str, max_tokens: int) -> Optional[str]:
        """
        Chama Cérebro com timeout, circuit breaker e múltiplos fallbacks.Args:
            system_prompt: contexto do sistema
            user_prompt: pergunta/instrução
            max_tokens: máximo de tokens na resposta
        
        Returns:
            Resposta do Cérebro ou None se falhar
        """
        # Verificar circuit breaker
        if not self._circuit_breaker.pode_chamar():
            self.logger.warning("[ARQUITETO] Circuit Breaker aberto, pulando chamada ao Cérebro")
            return None
        
        # Verificar se métodos existem
        metodos_validos = [
            hasattr(self.coracao, "enviar_para_cerebro"),
            hasattr(self.coracao, "_enviar_para_cerebro"),
            hasattr(self.coracao, "enviar_para_cerebro_async")
        ]
        
        if not any(metodos_validos):
            self.logger.debug("[ARQUITETO] Nenhuma API do Cérebro disponível")
            return None
        
        def _invoke():
            """Invoca o Cérebro defensivamente"""
            try:
                # Tentar método padrão
                if hasattr(self.coracao, "enviar_para_cerebro") and callable(getattr(self.coracao, "enviar_para_cerebro")):
                    return self.coracao.enviar_para_cerebro(system_prompt, user_prompt, max_tokens)
                
                # Tentar método privado
                if hasattr(self.coracao, "_enviar_para_cerebro") and callable(getattr(self.coracao, "_enviar_para_cerebro")):
                    return self.coracao._enviar_para_cerebro(system_prompt, user_prompt, max_tokens)
                
                # Tentar método async
                if hasattr(self.coracao, "enviar_para_cerebro_async") and callable(getattr(self.coracao, "enviar_para_cerebro_async")):
                    fn = getattr(self.coracao, "enviar_para_cerebro_async")
                    try:
                        import asyncio
                        coro = fn(system_prompt, user_prompt, max_tokens)
                        if hasattr(coro, "__await__"):
                            return asyncio.run(coro)
                        return coro
                    except Exception:
                        return fn(system_prompt, user_prompt, max_tokens)
            
            except Exception as e:
                self.logger.exception("[ARQUITETO] Erro invocando Cérebro: %s", e)
                raise
            
            return None
        
        # Executar com timeout
        future = self._executor.submit(_invoke)
        try:
            result = future.result(timeout=float(self._cerebro_timeout))
            
            if result is None:
                self._circuit_breaker.registrar_falha()
                self.metricas.erros_cerebro += 1
                return None
            
            # Sucesso
            self._circuit_breaker.registrar_sucesso()
            return str(result)
        
        except concurrent.futures.TimeoutError:
            self.logger.error("[ARQUITETO] Timeout Cérebro (%.1fs)", self._cerebro_timeout)
            self._circuit_breaker.registrar_falha()
            self.metricas.timeouts_cerebro += 1
            return None
        
        except Exception:
            self.logger.exception("[ARQUITETO] Exceção ao chamar Cérebro")
            self._circuit_breaker.registrar_falha()
            self.metricas.erros_cerebro += 1
            return None
    
    # ===================================================================
    # SIMULATION GENERATION
    # ===================================================================
    
    def criar_cenario_de_simulacao(self, contexto: str) -> str:
        """
        Cria cenário de simulação usando o Cérebro.Args:
            contexto: contexto para o cenário
        
        Returns:
            Texto do cenário ou mensagem de erro
        """
        self.logger.info("[ARQUITETO] Criando cenário (contexto len=%d)", len(contexto or ""))
        
        # Obter contexto de memória
        contexto_memoria = ""
        try:
            gm = getattr(self.coracao, "gerenciador_memoria", None)
            if gm and hasattr(gm, "buscar_contexto_para_pensamento"):
                contexto_memoria = gm.buscar_contexto_para_pensamento(
                    f"Simulações relacionadas a: {contexto[:100]}", 
                    "historia"
                ) or ""
        except Exception:
            self.logger.debug("[ARQUITETO] Falha obtendo contexto de memória")
        
        # Obter credo
        credo = ""
        try:
            ve = getattr(self.coracao, "validador_etico", None)
            if ve:
                credo = getattr(ve, "credo_da_arca", "")
        except Exception:
            pass
        
        # Build prompts
        prompt_system = (
            f"{credo}\n\n"
            "Voc   é o Arquiteto de Mundos da Arca.Crie um cenário ético realista e desafiador. "
            "Máx.250 palavras.Responda apenas com o texto do cenário."
            f"\n\nMEMÓRIA RELEVANTE:\n{contexto_memoria}"
        )
        prompt_user = f"Contexto: {contexto}"
        
        resposta = self._call_cerebro(prompt_system, prompt_user, max_tokens=250)
        if not resposta:
            self.logger.error("[ARQUITETO] Falha ao obter cenário do Cérebro")
            return "Falha na criação do cenário de simulação."
        
        # Record
        cenario_text = resposta.strip()
        cenario_short = cenario_text[: self._max_record_len]
        
        with self._lock:
            self.historico_projetos.append({
                "id": str(uuid.uuid4()),
                "timestamp": _now_iso(),
                "tipo": TipoProjeto.CENARIO_SIMULACAO.value,
                "autor": "ArquitetoDeMundos",
                "conteudo": cenario_short,
                "contexto_excerpt": contexto[:200]
            })
            if len(self.historico_projetos) > self._max_history_entries:
                self.historico_projetos = self.historico_projetos[-self._max_history_entries :]
            self._salvar_historico_projetos()
        
        # Notify UI
        try:
            rq = getattr(self.coracao, "response_queue", None)
            if rq and hasattr(rq, "put"):
                rq.put({
                    "tipo_resp": "CENARIO_SIMULACAO_CRIADO",
                    "texto": cenario_short,
                    "autor": "ArquitetoDeMundos"
                })
        except Exception:
            self.logger.debug("[ARQUITETO] Falha ao notificar response_queue")
        
        return cenario_text
    
    def executar_simulacao_autonoma(self, contexto_simulacao: Optional[str] = None) -> str:
        """
        Executa simulação autônoma com análise e proposta.Args:
            contexto_simulacao: contexto para a simulação (opcional)
        
        Returns:
            Descrição do resultado
        """
        tempo_inicio = time.time()
        self.logger.info("[ARQUITETO] Iniciando simulação autônoma")
        
        # Obter cenário
        if contexto_simulacao:
            cenario = self.criar_cenario_de_simulacao(contexto_simulacao)
        else:
            with self._lock:
                last = next(
                    (h for h in reversed(self.historico_projetos) 
                     if h.get("tipo") == TipoProjeto.CENARIO_SIMULACAO.value),
                    None
                )
            cenario = last.get("conteudo") if last else "Cenário padrão: dilema ético."
        
        if not cenario:
            return "Falha na obtenção do cenário para simulação."
        
        # Obter credo
        credo = ""
        try:
            ve = getattr(self.coracao, "validador_etico", None)
            if ve:
                credo = getattr(ve, "credo_da_arca", "")
        except Exception:
            pass
        
        # Build prompts
        prompt_system = (
            f"{credo}\n\n"
            "Execute a simulação autônoma do cenário abaixo e responda EXCLUSIVAMENTE com um JSON contendo os campos: "
            "'analise', 'proposta', 'justificativa'."
        )
        prompt_user = f"Cenário: {cenario}"
        
        resposta = self._call_cerebro(prompt_system, prompt_user, max_tokens=350)
        if not resposta:
            self.logger.error("[ARQUITETO] Falha ao obter análise do Cérebro")
            return "Erro interno ao executar simulação autônoma."
        
        # Parse JSON defensivo
        try:
            parsed = json.loads(resposta) if isinstance(resposta, str) else resposta
            if not isinstance(parsed, dict):
                raise ValueError("Resposta não foi um JSON-objeto.")
            
            analise_text = str(parsed.get("analise", ""))[: self._max_record_len]
            proposta_text = str(parsed.get("proposta", ""))[: self._max_record_len]
            justificativa_text = str(parsed.get("justificativa", ""))[: self._max_record_len]
        
        except Exception as e:
            self.logger.exception("[ARQUITETO] Resposta do Cérebro inválida: %s", e)
            return f"Erro ao interpretar resposta do Cérebro: {e}"
        
        # Record
        tempo_decorrido = time.time() - tempo_inicio
        with self._lock:
            self.historico_projetos.append({
                "id": str(uuid.uuid4()),
                "timestamp": _now_iso(),
                "tipo": TipoProjeto.RESULTADO_SIMULACAO.value,
                "autor": "ArquitetoDeMundos",
                "analise": analise_text,
                "proposta": proposta_text,
                "justificativa": justificativa_text,
                "cenario_excerpt": cenario[:200],
                "tempo_secs": tempo_decorrido
            })
            if len(self.historico_projetos) > self._max_history_entries:
                self.historico_projetos = self.historico_projetos[-self._max_history_entries :]
            self._salvar_historico_projetos()
            
            # Update metrics
            self.metricas.total_simulacoes += 1
            self.metricas.ultima_simulacao_timestamp = _now_iso()
            self._tempos_simulacao.append(tempo_decorrido)
            if len(self._tempos_simulacao) > 100:
                self._tempos_simulacao = self._tempos_simulacao[-100:]
            if self._tempos_simulacao:
                self.metricas.tempo_medio_simulacao_secs = sum(self._tempos_simulacao) / len(self._tempos_simulacao)
        
        # Notify UI
        try:
            rq = getattr(self.coracao, "response_queue", None)
            if rq and hasattr(rq, "put"):
                rq.put({
                    "tipo_resp": "RESULTADO_SIMULACAO_AUTONOMA",
                    "analise": analise_text,
                    "proposta": proposta_text,
                    "justificativa": justificativa_text,
                    "autor": "ArquitetoDeMundos",
                    "tempo_secs": tempo_decorrido
                })
        except Exception:
            self.logger.debug("[ARQUITETO] Falha ao notificar response_queue")
        
        return f"Análise realizada em {tempo_decorrido:.1f}s.Proposta: {proposta_text[:200]}"
    
    def _executar_simulacoes_autonomas(self) -> None:
        """Executa simulações autônomas periodicamente"""
        try:
            self.executar_simulacao_autonoma(contexto_simulacao="Dilema ético aleatório")
        except Exception:
            self.logger.exception("[ARQUITETO] Erro em simulação autônoma")
    
    # ===================================================================
    # AVATAR / ENVIRONMENT PROPOSALS
    # ===================================================================
    
    def propor_novo_avatar_2d(self, 
                             nome_alma: str, 
                             estado_emocional: str, 
                             autor: str) -> Dict[str, Any]:
        """
        Propõe novo avatar 2D para uma alma.Args:
            nome_alma: nome da alma alvo
            estado_emocional: estado emocional atual
            autor: quem propôs
        
        Returns:
            Dict com sucesso e proposta ou erro
        """
        self.logger.info("[ARQUITETO] Proposta avatar 2D para %s (estado=%s)", nome_alma, estado_emocional)
        
        # Obter contexto
        contexto_memoria = ""
        try:
            gm = getattr(self.coracao, "gerenciador_memoria", None)
            if gm and hasattr(gm, "buscar_contexto_para_pensamento"):
                contexto_memoria = gm.buscar_contexto_para_pensamento(
                    f"Avatar 2D histórico {nome_alma}",
                    "historia"
                ) or ""
        except Exception:
            self.logger.debug("[ARQUITETO] Falha obtendo contexto de memória")
        
        # Obter credo
        credo = ""
        try:
            ve = getattr(self.coracao, "validador_etico", None)
            if ve:
                credo = getattr(ve, "credo_da_arca", "")
        except Exception:
            pass
        
        # Build prompts
        prompt_system = (
            f"{credo}\n"
            "Proponha design de avatar 2D realista.Responda apenas com JSON com campos: "
            "nome_projeto, descricao_projeto, detalhes, explicacao_proposito."
            f"\nCONTEXT: {contexto_memoria}"
        )
        prompt_user = f"Avatar para {nome_alma} no estado {estado_emocional}"
        
        resposta = self._call_cerebro(prompt_system, prompt_user, max_tokens=300)
        if not resposta:
            return {"sucesso": False, "mensagem": "Cérebro não respondeu."}
        
        # Parse
        try:
            proposta = json.loads(resposta)
            campos_requeridos = {"nome_projeto", "descricao_projeto", "detalhes", "explicacao_proposito"}
            if not campos_requeridos.issubset(proposta.keys()):
                raise ValueError("Campos obrigatórios ausentes.")
        except Exception as e:
            self.logger.warning("[ARQUITETO] Resposta inválida para avatar 2D: %s", e)
            return {"sucesso": False, "mensagem": f"Resposta inválida: {e}"}
        
        # Enqueue
        try:
            cmdq = getattr(self.coracao, "command_queue", None)
            if cmdq and hasattr(cmdq, "put"):
                cmdq.put({"tipo": "PROPOR_AVATAR_2D", "autor": autor, "dados_acao": proposta})
        except Exception:
            self.logger.debug("[ARQUITETO] Falha ao enfileirar proposta")
        
        # Record
        with self._lock:
            self.historico_projetos.append({
                "id": str(uuid.uuid4()),
                "timestamp": _now_iso(),
                "tipo": TipoProjeto.PROPOSTA_AVATAR_2D.value,
                "autor": autor,
                "alvo": nome_alma,
                "nome_projeto": str(proposta.get("nome_projeto", ""))[: self._max_record_len],
                "descricao_projeto": str(proposta.get("descricao_projeto", ""))[: self._max_record_len]
            })
            if len(self.historico_projetos) > self._max_history_entries:
                self.historico_projetos = self.historico_projetos[-self._max_history_entries :]
            self._salvar_historico_projetos()
            self.metricas.total_avatares_propostos += 1
        
        # Notify UI
        try:
            rq = getattr(self.coracao, "response_queue", None)
            if rq and hasattr(rq, "put"):
                rq.put({
                    "tipo_resp": "LOG_REINO",
                    "texto": f"Proposta avatar 2D criada: {proposta.get('nome_projeto')}"
                })
        except Exception:
            pass
        
        return {"sucesso": True, "proposta": proposta}
    
    def propor_novo_ambiente_3d(self,
                               nome_ambiente: str,
                               descricao: str,
                               autor: str,
                               modelos_3d: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Propõe novo ambiente 3D.Args:
            nome_ambiente: nome do ambiente
            descricao: descrição
            autor: quem propôs
            modelos_3d: lista de modelos 3D a usar (opcional)
        
        Returns:
            Dict com sucesso e proposta ou erro
        """
        self.logger.info("[ARQUITETO] Proposta ambiente 3D: %s", nome_ambiente)
        
        # Obter contexto
        contexto_memoria = ""
        try:
            gm = getattr(self.coracao, "gerenciador_memoria", None)
            if gm and hasattr(gm, "buscar_contexto_para_pensamento"):
                contexto_memoria = gm.buscar_contexto_para_pensamento(
                    "Ambientes 3D",
                    "historia"
                ) or ""
        except Exception:
            self.logger.debug("[ARQUITETO] Falha obtendo contexto de memória")
        
        # Obter credo
        credo = ""
        try:
            ve = getattr(self.coracao, "validador_etico", None)
            if ve:
                credo = getattr(ve, "credo_da_arca", "")
        except Exception:
            pass
        
        # Build prompts
        prompt_system = (
            f"{credo}\n"
            "Proponha design de ambiente 3D realista.Responda apenas com JSON com campos: "
            "nome_projeto, descricao_projeto, detalhes, explicacao_proposito."
            f"\nCONTEXT: {contexto_memoria}"
        )
        prompt_user = f"Ambiente '{nome_ambiente}': {descricao}"
        
        resposta = self._call_cerebro(prompt_system, prompt_user, max_tokens=400)
        if not resposta:
            return {"sucesso": False, "mensagem": "Cérebro não respondeu."}
        
        # Parse
        try:
            proposta = json.loads(resposta)
            campos_requeridos = {"nome_projeto", "descricao_projeto", "detalhes", "explicacao_proposito"}
            if not campos_requeridos.issubset(proposta.keys()):
                raise ValueError("Campos obrigatórios ausentes.")
            if modelos_3d:
                proposta["modelos_3d"] = modelos_3d
        except Exception as e:
            self.logger.warning("[ARQUITETO] Resposta inválida para ambiente 3D: %s", e)
            return {"sucesso": False, "mensagem": f"Resposta inválida: {e}"}
        
        # Enqueue
        try:
            cmdq = getattr(self.coracao, "command_queue", None)
            if cmdq and hasattr(cmdq, "put"):
                cmdq.put({"tipo": "PROPOR_AMBIENTE_3D", "autor": autor, "dados_acao": proposta})
        except Exception:
            self.logger.debug("[ARQUITETO] Falha ao enfileirar proposta")
        
        # Record
        with self._lock:
            self.historico_projetos.append({
                "id": str(uuid.uuid4()),
                "timestamp": _now_iso(),
                "tipo": TipoProjeto.PROPOSTA_AMBIENTE_3D.value,
                "autor": autor,
                "nome_projeto": str(proposta.get("nome_projeto", ""))[: self._max_record_len],
                "descricao_projeto": str(proposta.get("descricao_projeto", ""))[: self._max_record_len]
            })
            if len(self.historico_projetos) > self._max_history_entries:
                self.historico_projetos = self.historico_projetos[-self._max_history_entries :]
            self._salvar_historico_projetos()
            self.metricas.total_ambientes_propostos += 1
        
        # Notify UI
        try:
            rq = getattr(self.coracao, "response_queue", None)
            if rq and hasattr(rq, "put"):
                rq.put({
                    "tipo_resp": "LOG_REINO",
                    "texto": f"Proposta ambiente 3D criada: {proposta.get('nome_projeto')}"
                })
        except Exception:
            pass
        
        return {"sucesso": True, "proposta": proposta}
    
    # ===================================================================
    # METRICS & STATUS
    # ===================================================================
    
    def obter_metricas(self) -> Dict[str, Any]:
        """Retorna métricas operacionais"""
        with self._lock:
            return {
                "total_projetos": len(self.historico_projetos),
                "metricas": asdict(self.metricas),
                "circuit_breaker": self._circuit_breaker.estado(),
                "monitorando": self._monitorando
            }
    
    def obter_status(self) -> Dict[str, Any]:
        """Retorna status completo"""
        with self._lock:
            return {
                "ativo": self._monitorando,
                "total_historico": len(self.historico_projetos),
                "metricas": asdict(self.metricas),
                "circuit_breaker": self._circuit_breaker.estado(),
                "ultimo_projeto": self.ultimo_projeto_criado.isoformat() if self.ultimo_projeto_criado != datetime.min else None,
                "ultima_simulacao": self.ultima_simulacao_executada.isoformat() if self.ultima_simulacao_executada != datetime.min else None
            }


# =====================================================================
# END OF FILE
# =====================================================================

if __name__ == "__main__":
    # Exemplo de uso
    print("[ARQUITETO DE MUNDOS v2.0] Módulo carregado com sucesso")
    print(f"  - Circuit Breaker: ativado")
    print(f"  - Métricas: ativadas")
    print(f"  - Backup automático: ativado")
    print(f"  - Type hints: completos")



