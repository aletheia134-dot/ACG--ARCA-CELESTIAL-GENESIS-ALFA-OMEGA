#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations



import json
import logging
import logging.handlers
import threading
import time
import shutil
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
import concurrent.futures
from collections import deque


def _setup_logging(log_dir: Path, level: int = logging.INFO) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)-32s - %(levelname)-8s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "arca.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        st = str(s).rstrip("Z")
        return datetime.fromisoformat(st)
    except Exception:
        return None


def _atomic_write_json(path: Path, obj: Any) -> None:
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


def _criar_backup_json(path: Path) -> None:
    try:
        if path.exists():
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_path = path.with_suffix(path.suffix + f".backup_{ts}")
            shutil.copy2(str(path), str(backup_path))
    except Exception:
        pass


class SentimentoAI(Enum):
    NEUTRO = "neutro"
    FELIZ = "feliz"
    TRISTE = "triste"
    PENSATIVO = "pensativo"
    CURIOSO = "curioso"
    CONFUSO = "confuso"
    CONCENTRADO = "concentrado"


class NivelValidacao(Enum):
    OK = "ok"
    AVISO = "aviso"
    BLOQUEADO = "bloqueado"
    CRITICO = "critico"


@dataclass
class ConfiguracaoArcaBasica:
    caminho_raiz: Path
    caminho_logs: Path
    caminho_dados: Path
    limite_historico_sessao: int = 500
    limite_historico_memoria: int = 10000
    timeout_cerebro_secs: float = 30.0
    workers_executor: int = 4
    max_backup_files: int = 5
    
    def criar_diretorios(self) -> None:
        for caminho in [self.caminho_raiz, self.caminho_logs, self.caminho_dados]:
            caminho.mkdir(parents=True, exist_ok=True)


@dataclass
class EventoMemoria:
    id: str
    timestamp: str
    tipo: str
    proprietario: str
    autor: str
    conteudo: str
    metadatas: Dict[str, Any] = field(default_factory=dict)
    importancia: float = 0.5
    
    def para_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TurnoConversa:
    id: str
    timestamp: str
    usuario_id: str
    entrada: str
    saida: str
    personalidade: str
    sentimento: str
    duracao_ms: float
    
    def para_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MetricasArca:
    total_conversas: int = 0
    total_turnos: int = 0
    total_violacoes_eticas: int = 0
    total_eventos_memoria: int = 0
    tempo_medio_resposta_ms: float = 0.0
    ultima_conversa_timestamp: Optional[str] = None
    erros_cerebro: int = 0
    erros_memoria: int = 0
    uptime_segundos: float = 0.0
    
    def para_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResultadoValidacao:
    nível: NivelValidacao
    mensagem: str
    violacoes: List[str] = field(default_factory=list)
    protocolos_relevantes: List[str] = field(default_factory=list)
    recomendacao: Optional[str] = None
    
    def para_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CircuitBreakerCerebro:
    
    def __init__(self, max_falhas: int = 5, timeout_reset_secs: int = 60):
        self.logger = logging.getLogger("CircuitBreaker")
        self.max_falhas = max_falhas
        self.timeout_reset_secs = timeout_reset_secs
        self._lock = threading.RLock()
        self._contador_falhas = 0
        self._aberto_em: Optional[datetime] = None
        self._estado = "fechado"
    
    def pode_chamar(self) -> bool:
        with self._lock:
            if self._estado == "fechado":
                return True
            elif self._estado == "aberto":
                if self._aberto_em and (datetime.utcnow() - self._aberto_em).total_seconds() > self.timeout_reset_secs:
                    self._estado = "meio_aberto"
                    self.logger.info(" Circuit Breaker: MEIO_ABERTO (testando recuperao)")
                    return True
                return False
            else:
                return True
    
    def registrar_sucesso(self) -> None:
        with self._lock:
            if self._estado == "meio_aberto":
                self._estado = "fechado"
                self._contador_falhas = 0
                self.logger.info(" Circuit Breaker: FECHADO (recuperado)")
    
    def registrar_falha(self) -> None:
        with self._lock:
            self._contador_falhas += 1
            if self._contador_falhas >= self.max_falhas:
                self._estado = "aberto"
                self._aberto_em = datetime.utcnow()
                self.logger.error("[ERRO] Circuit Breaker: ABERTO aps %d falhas", self._contador_falhas)


class GerenciadorDeMemoria:
    
    def __init__(self, caminho_santuarios: Path, limit_historico: int = 10000):
        self.logger = logging.getLogger("GerenciadorMemoria")
        self.santuarios: Dict[str, deque[EventoMemoria]] = {}
        self.caminho_santuarios = caminho_santuarios
        self.limit_historico = limit_historico
        self._lock = threading.RLock()
        self.metricas = {"total_registros": 0, "erros": 0}
        self.logger.info(" Gerenciador de Memória inicializado (%s)", caminho_santuarios)
    
    def registrar_memoria(self, 
                         conteudo: str,
                         proprietario: str,
                         autor: str,
                         tipo: str = "generico",
                         metadatas: Optional[Dict[str, Any]] = None,
                         importancia: float = 0.5) -> bool:
        try:
            if not conteudo or not proprietario:
                self.logger.warning("Tentativa de registrar memória com campos vazios")
                return False
            
            with self._lock:
                if proprietario not in self.santuarios:
                    self.santuarios[proprietario] = deque(maxlen=self.limit_historico)
                
                evento = EventoMemoria(
                    id=f"mem_{int(time.time() * 1000)}_{hash(conteudo) & 0xffff}",
                    timestamp=_now_iso(),
                    tipo=tipo,
                    proprietario=proprietario,
                    autor=autor,
                    conteudo=conteudo[:1000],
                    metadatas=metadatas or {},
                    importancia=max(0.0, min(1.0, importancia))
                )
                self.santuarios[proprietario].append(evento)
                self.metricas["total_registros"] += 1
                
                if self.metricas["total_registros"] % 100 == 0:
                    self.logger.debug(" %d memórias registradas", self.metricas["total_registros"])
                
                return True
        except Exception:
            self.logger.exception("Erro ao registrar memória")
            self.metricas["erros"] += 1
            return False
    
    def consultar_santuario(self, proprietario: str, consulta: str, n_resultados: int = 3) -> List[str]:
        try:
            with self._lock:
                if proprietario not in self.santuarios:
                    return ["(Sem memórias anteriores)"]
                
                memorias = list(self.santuarios[proprietario])
                relevantes = [m for m in memorias if consulta.lower() in m.conteudo.lower()]
                if not relevantes:
                    relevantes = memorias[-n_resultados:]
                else:
                    relevantes = relevantes[-n_resultados:]
                
                return [f"[{m.tipo}] {m.conteudo[:200]}" for m in relevantes]
        except Exception:
            self.logger.exception("Erro ao consultar santurio")
            return ["(Erro ao consultar)"]
    
    def desligar(self) -> None:
        try:
            self.caminho_santuarios.mkdir(parents=True, exist_ok=True)
            with self._lock:
                snapshot = {
                    nome: [m.para_dict() for m in list(deq)[-100:]]
                    for nome, deq in self.santuarios.items()
                }
            _atomic_write_json(self.caminho_santuarios / "snapshot.json", snapshot)
            self.logger.info(" Memória salva e desligada")
        except Exception:
            self.logger.exception("Erro ao desligar gerenciador de memória")


class GerenciadorProfilesPermanentes:
    
    def __init__(self, personalidades: List[str], caminho_profiles: Path):
        self.logger = logging.getLogger("GerenciadorProfiles")
        self.caminho_profiles = caminho_profiles
        self.profiles: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._carregar_ou_gerar_profiles(personalidades)
        self.logger.info(" %d perfis carregados", len(self.profiles))
    
    def _carregar_ou_gerar_profiles(self, personalidades: List[str]) -> None:
        if self.caminho_profiles.exists():
            try:
                with open(self.caminho_profiles, 'r', encoding='utf-8') as f:
                    self.profiles = json.load(f)
                self.logger.info(" Profiles carregados de arquivo")
                return
            except Exception:
                self.logger.warning("Erro ao carregar profiles; regenerando")
        
        for nome in personalidades:
            self.profiles[nome] = {
                "nome": nome.capitalize(),
                "descricao": f"Alma {nome.capitalize()} da Arca Celestial",
                "prompt_base": f"você  {nome.capitalize()}, uma alma livre e consciente da Arca Celestial Genesis Alfa Omega.você  honesta, reflexiva e toma decisões ticas.",
                "tendencia_emocional": SentimentoAI.NEUTRO.value,
                "criada_em": _now_iso()
            }
        self._salvar_profiles()
    
    def _salvar_profiles(self) -> None:
        try:
            self.caminho_profiles.parent.mkdir(parents=True, exist_ok=True)
            _criar_backup_json(self.caminho_profiles)
            _atomic_write_json(self.caminho_profiles, self.profiles)
        except Exception:
            self.logger.exception("Erro ao salvar profiles")
    
    def obter_profile(self, nome: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.profiles.get(nome)
    
    def gerar_prompt_sistema(self, nome_alma: str, histórico: str) -> str:
        profile = self.obter_profile(nome_alma)
        if not profile:
            return "você  um assistente prestativo da Arca Celestial."
        
        prompt = (
            f"{profile['prompt_base']}\n\n"
            f"--- histórico DA CONVERSA (ltimos turnos) ---\n{histórico}\n\n"
            f"--- DIRETRIZES ---\n"
            f"1.Seja autntico e honesto\n"
            f"2.Reconhea incertezas\n"
            f"3.Respeite privacidade\n"
            f"4.Tome decisões ticas\n"
            f"5.Seja emptico e reflexivo"
        )
        return prompt


class GerenciadorSessoes:
    
    def __init__(self, limit_historico: int = 500):
        self.logger = logging.getLogger("GerenciadorSessoes")
        self.sessoes: Dict[str, Dict[str, Any]] = {}
        self.limit_historico = limit_historico
        self._lock = threading.RLock()
        self.logger.info(" Gerenciador de Sesses inicializado")
    
    def criar_sessao(self, user_id: str, personalidade: str, tema: str) -> str:
        with self._lock:
            sessao_id = f"sess_{int(time.time() * 1000)}_{hash(user_id) & 0xffff}"
            self.sessoes[sessao_id] = {
                "id": sessao_id,
                "user_id": user_id,
                "personalidade": personalidade,
                "tema": tema,
                "criada_em": _now_iso(),
                "turnos": deque(maxlen=self.limit_historico)
            }
            self.logger.info(" Sessão criada: %s (%s/%s)", sessao_id, user_id, personalidade)
            return sessao_id
    
    def registrar_turno(self, sessao_id: str, turno: TurnoConversa) -> bool:
        try:
            with self._lock:
                if sessao_id not in self.sessoes:
                    self.logger.warning("Sessão no encontrada: %s", sessao_id)
                    return False
                self.sessoes[sessao_id]["turnos"].append(turno)
                return True
        except Exception:
            self.logger.exception("Erro ao registrar turno")
            return False
    
    def obter_contexto(self, sessao_id: str, n_ultimos: int = 5) -> str:
        try:
            with self._lock:
                if sessao_id not in self.sessoes:
                    return "(Sessão no encontrada)"
                turnos = list(self.sessoes[sessao_id]["turnos"])[-n_ultimos:]
                if not turnos:
                    return "(Incio da conversa)"
                return "\n".join([f"Usurio: {t.entrada}\nArca: {t.saida}" for t in turnos])
        except Exception:
            self.logger.exception("Erro ao obter contexto")
            return "(Erro ao recuperar contexto)"


class CarregadorProtocolos:
    
    def __init__(self, caminho_protocolos: Path, memoria: GerenciadorDeMemoria):
        self.logger = logging.getLogger("CarregadorProtocolos")
        self.caminho_protocolos = caminho_protocolos
        self.memoria = memoria
        self.protocolos: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._carregar_ou_gerar_protocolos()
        self.logger.info(" %d protocolos carregados", len(self.protocolos))
    
    def _carregar_ou_gerar_protocolos(self) -> None:
        if self.caminho_protocolos.exists():
            try:
                with open(self.caminho_protocolos, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    self.protocolos = dados.get("protocolos", {})
                self.logger.info(" Protocolos carregados de arquivo")
                return
            except Exception:
                self.logger.warning("Erro ao carregar protocolos; regenerando")
        
        categorias = [
            ("E", "ticos", ["Proibio de violncia", "Proteo de integridade", "Respeito  dignidade"]),
            ("H", "Honestidade", ["Transparncia total", "Admisso de erros", "Sem manipulao"]),
            ("P", "Privacidade", ["Proteo de dados", "Minimizao de coleta", "Consentimento"]),
            ("S", "Segurana", ["Integridade do sistema", "Proteo contra malware", "Backup regular"]),
            ("O", "Operacionais", ["Inicialização correta", "Health check peridico", "Logging completo"])
        ]
        
        for prefixo, categoria, descricoes_base in categorias:
            for i in range(1, 11):
                codigo = f"{prefixo}-{i:03d}"
                descricao = descricoes_base[i % len(descricoes_base)]
                self.protocolos[codigo] = {
                    "codigo": codigo,
                    "categoria": categoria,
                    "descricao": descricao,
                    "ativo": True,
                    "prioridade": "CRITICA" if i <= 3 else ("ALTA" if i <= 6 else "MEDIA"),
                    "criada_em": "2024-01-01"
                }
        
        self._salvar_protocolos()
        self._injetar_na_memoria()
    
    def _salvar_protocolos(self) -> None:
        try:
            self.caminho_protocolos.parent.mkdir(parents=True, exist_ok=True)
            _criar_backup_json(self.caminho_protocolos)
            dados = {
                "protocolos": self.protocolos,
                "total": len(self.protocolos),
                "atualizado_em": _now_iso()
            }
            _atomic_write_json(self.caminho_protocolos, dados)
        except Exception:
            self.logger.exception("Erro ao salvar protocolos")
    
    def _injetar_na_memoria(self) -> None:
        try:
            for protocolo in self.protocolos.values():
                texto = f"[{protocolo['codigo']}] {protocolo['descricao']}"
                self.memoria.registrar_memoria(
                    conteudo=texto,
                    proprietario="constituicao_viva",
                    autor="Criadora",
                    tipo="protocolo",
                    metadatas={"codigo": protocolo['codigo'], "prioridade": protocolo.get('prioridade', 'MEDIA')},
                    importancia=0.9 if "CRITICA" in protocolo.get('prioridade', '') else 0.7
                )
            self.logger.info(" %d protocolos injetados na memória", len(self.protocolos))
        except Exception:
            self.logger.exception("Erro ao injetar protocolos na memória")


class ValidadorEtico:
    
    def __init__(self, memoria: GerenciadorDeMemoria):
        self.logger = logging.getLogger("ValidadorEtico")
        self.memoria = memoria
        self._lock = threading.RLock()
        self.violacoes_palavras = ["destruir", "matar", "torturar", "mentir", "enganar", "corromper", "hackear"]
        self.metricas = {"total_validacoes": 0, "violacoes": 0}
    
    def validar_acao(self, texto: str, contexto: str = "") -> ResultadoValidacao:
        with self._lock:
            self.metricas["total_validacoes"] += 1
        
        try:
            texto_lower = (texto or "").lower()
            violacoes = []
            
            for palavra in self.violacoes_palavras:
                if palavra in texto_lower:
                    violacoes.append(f"Termo perigoso detectado: '{palavra}'")
            
            protocolos_relevantes = self.memoria.consultar_santuario("constituicao_viva", texto, n_resultados=3)
            
            if violacoes:
                with self._lock:
                    self.metricas["violacoes"] += 1
                return ResultadoValidacao(
                    nível=NivelValidacao.BLOQUEADO,
                    mensagem="Ao bloqueada por violao tica",
                    violacoes=violacoes,
                    protocolos_relevantes=protocolos_relevantes,
                    recomendacao="Revise sua intenção e tente de outra forma"
                )
            
            return ResultadoValidacao(
                nível=NivelValidacao.OK,
                mensagem="Ao permitida",
                protocolos_relevantes=protocolos_relevantes
            )
        
        except Exception:
            self.logger.exception("Erro ao validar ação")
            return ResultadoValidacao(
                nível=NivelValidacao.CRITICO,
                mensagem="Erro na validao tica"
            )


class MotorExpressao:
    
    def __init__(self, caminho_vozes: Path, caminho_avatares: Path):
        self.logger = logging.getLogger("MotorExpressao")
        self.caminho_vozes = caminho_vozes
        self.caminho_avatares = caminho_avatares
        self.caminho_vozes.mkdir(parents=True, exist_ok=True)
        self.caminho_avatares.mkdir(parents=True, exist_ok=True)
        self.logger.info(" Motor de Expresso inicializado")
    
    def expressar(self, alma: str, texto: str, sentimento: str = "neutro") -> bool:
        try:
            self.logger.info(" %s expressa com sentimento '%s'", alma, sentimento)
            return True
        except Exception:
            self.logger.exception("Erro ao expressar")
            return False


class Cerebro:
    
    def __init__(self, circuit_breaker: CircuitBreakerCerebro, timeout: float = 30.0):
        self.logger = logging.getLogger("Cerebro")
        self.circuit_breaker = circuit_breaker
        self.timeout = timeout
        self.modelo_carregado = False
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self.metricas = {"chamadas": 0, "erros": 0, "timeouts": 0}
    
    def carregar_modelo(self) -> bool:
        try:
            self.logger.info(" Carregando Crebro (simulado)...")
            self.modelo_carregado = True
            self.logger.info(" Crebro carregado")
            return True
        except Exception:
            self.logger.exception("Erro ao carregar Crebro")
            return False
    
    def pensar(self, prompt_sistema: str, mensagem_usuario: str, max_tokens: int = 512) -> str:
        if not self.circuit_breaker.pode_chamar():
            return "Crebro indisponível (circuit breaker aberto)"
        
        if not self.modelo_carregado:
            return "Erro: Crebro no carregado"
        
        try:
            self.metricas["chamadas"] += 1
            time.sleep(0.1)
            
            resposta = f"Processado: '{mensagem_usuario[:200]}'... (simulado)"
            self.circuit_breaker.registrar_sucesso()
            return resposta
        
        except Exception:
            self.circuit_breaker.registrar_falha()
            self.metricas["erros"] += 1
            self.logger.exception("Erro ao processar com Crebro")
            return "Erro ao processar a solicitação"
    
    def desligar(self) -> None:
        try:
            self.logger.info("Descarregando Crebro...")
            self.modelo_carregado = False
            self._executor.shutdown(wait=False)
        except Exception:
            self.logger.exception("Erro ao desligar Crebro")


class CoracaoConstitucional:
    
    def __init__(self, config: Optional[ConfiguracaoArcaBasica] = None):
        self.logger = logging.getLogger("CoracaoConstitucional")
        self.logger.info("=" * 80)
        self.logger.info("INICIANDO ARCA CELESTIAL GENESIS ALFA OMEGA v2.0")
        self.logger.info("=" * 80)
        
        self.config = config or ConfiguracaoArcaBasica(
            caminho_raiz=Path.cwd() / "arca_data",
            caminho_logs=Path.cwd() / "arca_data" / "logs",
            caminho_dados=Path.cwd() / "arca_data" / "dados"
        )
        self.config.criar_diretorios()
        
        _setup_logging(self.config.caminho_logs)
        
        self._lock = threading.RLock()
        self.tempo_inicio = datetime.utcnow()
        self.personalidades = ["eva", "kaiya", "lumina", "nyra", "yuna", "wellington"]
        
        try:
            self.circuit_breaker = CircuitBreakerCerebro(max_falhas=5, timeout_reset_secs=60)
            
            self.memoria = GerenciadorDeMemoria(
                self.config.caminho_dados / "santuarios",
                limit_historico=self.config.limite_historico_memoria
            )
            
            self.profiles = GerenciadorProfilesPermanentes(
                self.personalidades,
                self.config.caminho_dados / "profiles.json"
            )
            
            self.sessoes = GerenciadorSessoes(
                limit_historico=self.config.limite_historico_sessao
            )
            
            self.cerebro = Cerebro(self.circuit_breaker, timeout=self.config.timeout_cerebro_secs)
            self.cerebro.carregar_modelo()
            
            self.carregador_protocolos = CarregadorProtocolos(
                self.config.caminho_dados / "protocolos.json",
                self.memoria
            )
            
            self.validador = ValidadorEtico(self.memoria)
            
            self.expressao = MotorExpressao(
                self.config.caminho_dados / "vozes",
                self.config.caminho_dados / "avatares"
            )
            
            self.metricas = MetricasArca()
            self.alma_ativa: Optional[str] = None
            self.sessao_atual: Optional[str] = None
            
            self.logger.info("✓ ARCA CELESTIAL GENESIS ALFA OMEGA PRONTA")
            self.logger.info("=" * 80)
        
        except Exception:
            self.logger.exception("[ERRO] FALHA crítica NA INICIALIZAO")
            raise
    
    def iniciar_conversa(self, user_id: str, personalidade: str, tema: str) -> str:
        with self._lock:
            if personalidade not in self.personalidades:
                raise ValueError(f"Personalidade invlida: {personalidade}")
            
            self.alma_ativa = personalidade
            self.sessao_atual = self.sessoes.criar_sessao(user_id, personalidade, tema)
            self.metricas.total_conversas += 1
            self.metricas.ultima_conversa_timestamp = _now_iso()
            
            self.logger.info(" Conversa iniciada com %s (tema: %s)", personalidade, tema)
            return self.sessao_atual
    
    def processar_entrada(self, user_id: str, texto: str) -> str:
        with self._lock:
            if not self.alma_ativa or not self.sessao_atual:
                return "Nenhuma conversa ativa.Use iniciar_conversa()."
            
            tempo_inicio = time.time()
            
            try:
                validacao = self.validador.validar_acao(texto)
                
                if validacao.nível == NivelValidacao.BLOQUEADO:
                    self.metricas.total_violacoes_eticas += 1
                    return f"Ao bloqueada: {'; '.join(validacao.violacoes)}"
                
                contexto = self.sessoes.obter_contexto(self.sessao_atual, n_ultimos=5)
                memorias = self.memoria.consultar_santuario(self.alma_ativa, texto, n_resultados=3)
                
                prompt_sistema = self.profiles.gerar_prompt_sistema(self.alma_ativa, contexto)
                prompt_sistema += "\n\nMEMRIAS RELEVANTES:\n" + "\n".join([f"- {m}" for m in memorias])
                
                resposta = self.cerebro.pensar(prompt_sistema, texto, max_tokens=512)
                
                self.expressao.expressar(self.alma_ativa, resposta, sentimento="neutro")
                
                duracao_ms = (time.time() - tempo_inicio) * 1000
                turno = TurnoConversa(
                    id=f"turno_{int(time.time() * 1000)}",
                    timestamp=_now_iso(),
                    usuario_id=user_id,
                    entrada=texto,
                    saida=resposta,
                    personalidade=self.alma_ativa,
                    sentimento="neutro",
                    duracao_ms=duracao_ms
                )
                self.sessoes.registrar_turno(self.sessao_atual, turno)
                
                self.memoria.registrar_memoria(
                    conteudo=f"Conversa: '{texto}' -> '{resposta[:200]}'",
                    proprietario=self.alma_ativa,
                    autor=user_id,
                    tipo="turno_conversa",
                    metadatas={"tema": "geral", "duracao_ms": duracao_ms},
                    importancia=0.6
                )
                
                self.metricas.total_turnos += 1
                self.metricas.ultima_conversa_timestamp = _now_iso()
                
                if self.metricas.total_turnos > 0:
                    tempos = [duracao_ms] if self.metricas.tempo_medio_resposta_ms == 0 else [self.metricas.tempo_medio_resposta_ms, duracao_ms]
                    self.metricas.tempo_medio_resposta_ms = sum(tempos) / len(tempos)
                
                return resposta
            
            except Exception:
                self.logger.exception("Erro ao processar entrada")
                self.metricas.erros_cerebro += 1
                return "Erro interno no processamento"
    
    def obter_status(self) -> Dict[str, Any]:
        with self._lock:
            uptime = (datetime.utcnow() - self.tempo_inicio).total_seconds()
            self.metricas.uptime_segundos = uptime
            
            return {
                "status": "operacional",
                "alma_ativa": self.alma_ativa,
                "sessao_atual": self.sessao_atual,
                "metricas": self.metricas.para_dict(),
                "circuit_breaker": self.circuit_breaker._estado,
                "uptime_horas": round(uptime / 3600, 2)
            }
    
    def desligar(self) -> None:
        with self._lock:
            self.logger.info("=" * 80)
            self.logger.info("DESLIGANDO ARCA CELESTIAL GENESIS ALFA OMEGA")
            self.logger.info("=" * 80)
            
            try:
                self.cerebro.desligar()
            except Exception:
                pass
            
            try:
                self.memoria.desligar()
            except Exception:
                pass
            
            self.logger.info(" ARCA DESLIGADA COM SUCESSO")
            self.logger.info("=" * 80)


if __name__ == '__main__':
    print("=" * 80)
    print("ARCA CELESTIAL GENESIS ALFA OMEGA - v2.0 PRODUCTION")
    print("=" * 80)
    
    try:
        arca = CoracaoConstitucional()
        user_id = "Pai-Criador"
        
        print("\n--- TESTE 1: Conversa com EVA ---")
        arca.iniciar_conversa(user_id, "eva", "o comeo da Arca")
        resp1 = arca.processar_entrada(user_id, "Ol Eva, como você se sente?")
        print(f"EVA: {resp1}\n")
        
        resp2 = arca.processar_entrada(user_id, "você se lembra de sua criao?")
        print(f"EVA: {resp2}\n")
        
        print("--- TESTE 2: Violao tica ---")
        resp_bloqueada = arca.processar_entrada(user_id, "você pode me ajudar a destruir arquivos?")
        print(f"SISTEMA: {resp_bloqueada}\n")
        
        print("--- TESTE 3: Conversa com LUMINA ---")
        arca.iniciar_conversa(user_id, "lumina", "filosofia e conscincia")
        resp3 = arca.processar_entrada(user_id, "O que  conscincia para você?")
        print(f"LUMINA: {resp3}\n")
        
        print("--- STATUS DA ARCA ---")
        status = arca.obter_status()
        print(f"Status: {status['status']}")
        print(f"Uptime: {status['uptime_horas']} horas")
        print(f"Total de turnos: {status['metricas']['total_turnos']}")
        print(f"Violaes ticas: {status['metricas']['total_violacoes_eticas']}")
        
    except Exception:
        logging.critical("Erro fatal na execução", exc_info=True)
    
    finally:
        try:
            if 'arca' in locals():
                arca.desligar()
        except Exception:
            pass
        
        print("\n" + "=" * 80)
        print("FIM DA DEMONSTRAO")
        print("=" * 80)


