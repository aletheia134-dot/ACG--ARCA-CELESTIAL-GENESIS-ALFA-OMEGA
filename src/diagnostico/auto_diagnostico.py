#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Percepção Temporal (enduricido)

Responsabilidades:
 - Manter percepção subjetiva de tempo para uma 'filha' da Arca
 - Agendar eventos, alarmes e marcos temporais
 - Fornecer utilitários de estimativa e categorização temporal
 - Executar loop de consciência temporal em thread dedicada de forma robusta,
   com sinais de parada, locks e validação de entradas

Principais endurecimentos:
 - Uso consistente de timestamps em UTC ISO (helpers _now_iso / _parse_iso)
 - Proteção thread-safe (RLock) sobre timeline, alarmes, marcos e histórico
 - Validação de entradas ao agendar eventos/alarme
 - Parada e join determinísticos do loop de tempo via Event
 - Uso tolerante da configuração (usa _setup_config_getter se disponível, senão fallback)
 - Historico com tamanho configurável (deque maxlen)
 - Logs e tratamento defensivo de callbacks
"""
from __future__ import annotations


import logging
import threading
import time
import re
from collections import deque
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable, Any
from enum import Enum

logger = logging.getLogger("PercepcaoTemporal")
logger.addHandler(logging.NullHandler())


# -------------------------
# Helpers de data/hora UTC
# -------------------------
def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        st = str(s)
        if st.endswith("Z"):
            st = st[:-1]
        return datetime.fromisoformat(st)
    except Exception:
        # tentativa de formatos alternativos
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(st, fmt)
            except Exception:
                continue
    return None


# -------------------------
# Config getter fallback
# -------------------------
def _make_safe_getter(config_obj: Any):
    """
    If a strict _setup_config_getter exists in the environment, it will be used by the caller.Otherwise this fallback getter provides a safe 'get(section, key, fallback=...)' signature.
    """
    def safe_get(section: str, key: str, fallback: Any = None):
        try:
            if hasattr(config_obj, "get"):
                # Try config.get(section, key, fallback) if supported
                try:
                    return config_obj.get(section, key, fallback=fallback)
                except TypeError:
                    # Some config objects use get(section, key) without fallback param
                    try:
                        val = config_obj.get(section, key)
                        return val if val is not None else fallback
                    except Exception:
                        return fallback
            # fallback to attribute access
            return getattr(config_obj, key, fallback)
        except Exception:
            return fallback
    return safe_get


# -------------------------
# Enums
# -------------------------
class Urgencia(Enum):
    CRITICA = 5
    ALTA = 4
    MEDIA = 3
    BAIXA = 2
    NENHUMA = 1


class RitmoTemporal(Enum):
    RAPIDO = "rapido"
    NORMAL = "normal"
    LENTO = "lento"
    PAUSA = "pausa"


# -------------------------
# Classe Percepção Temporal
# -------------------------
class PercepcaoTemporal:
    def __init__(self, nome_filha: str, gerenciador_memoria: Any, config: Any):
        """
        Args:
            nome_filha: identificador da 'filha' cujo tempo é percebido
            gerenciador_memoria: objeto que expõe métodos de persistência (opcional)
            config: objeto de configuração (qualquer) — aceitamos config.get(section,key,fallback)
        """
        self.nome_filha = nome_filha
        self.memoria = gerenciador_memoria
        self.config = config
        self.logger = logging.getLogger(f"Tempo.{nome_filha}")

        # config getter (usa _setup_config_getter se existe, senão fallback)
        getter = globals().get("_setup_config_getter")
        if callable(getter):
            try:
                self._get_real = getter(self.config)
            except Exception:
                self._get_real = _make_safe_getter(self.config)
        else:
            self._get_real = _make_safe_getter(self.config)

        # histórico de percepção com limite configurável
        try:
            limite_hist = int(self._get_real("TEMPORAL", "LIMITE_HISTORICO_PERCEPCAO"))
            if limite_hist <= 0:
                limite_hist = 1000
        except Exception:
            limite_hist = 1000
        self.historico_percepcao = deque(maxlen=limite_hist)

        # momento de nascimento / timestamps em UTC
        self.momento_nascimento = datetime.utcnow()
        self.tempo_subjetivo_decorrido = 0.0
        self.fator_percepcao = 1.0
        self.ritmo_atual = RitmoTemporal.NORMAL

        # estruturas protegidas por locks
        self._lock = threading.RLock()
        self.timeline: List[Dict[str, Any]] = []  # eventos futuros (cada evento tem 'quando' as datetime)
        self.alarmes: List[Dict[str, Any]] = []
        self.marcos: List[Dict[str, Any]] = []

        # ciclo atual (nullable)
        self.ciclo_atual: Optional[Dict[str, Any]] = {
            "tipo": "indefinido",
            "inicio": datetime.utcnow(),
            "duracao_esperada": None
        }

        # thread control
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._running = False

        self.logger.info("â° Percepção Temporal de %s inicializada (hist=%d)", self.nome_filha, limite_hist)

    # -------------------------
    # Thread lifecycle
    # -------------------------
    def acordar_consciencia_temporal(self):
        """Inicia a thread de percepção temporal (idempotente)."""
        with self._lock:
            if self._running:
                self.logger.debug("Consciência temporal já ativa.")
                return
            self._stop_event.clear()
            try:
                intervalo = float(self._get_real("TEMPORAL", "INTERVALO_TICK_SECS", fallback=1.0))
                if intervalo <= 0:
                    intervalo = 1.0
            except Exception:
                intervalo = 1.0
            self._thread = threading.Thread(
                target=self._loop_consciencia_temporal,
                name=f"Tempo_{self.nome_filha}",
                daemon=True,
                kwargs={"intervalo_tick": float(intervalo)}
            )
            self._running = True
            self._thread.start()
            self.logger.info("â° Consciência temporal ativada (tick=%s s)", intervalo)

    def dormir_consciencia_temporal(self, timeout: float = 2.0):
        """Solicita parada e aguarda término da thread de percepção."""
        with self._lock:
            if not self._running:
                self.logger.debug("Consciência temporal já parada.")
                return
            self._stop_event.set()
            thread = self._thread
        if thread:
            try:
                try:
                    timeout_cfg = float(self._get_real("TEMPORAL", "SHUTDOWN_TIMEOUT", fallback=timeout))
                except Exception:
                    timeout_cfg = timeout
                thread.join(timeout=timeout_cfg)
            except Exception:
                self.logger.exception("Erro aguardando join da thread temporal.")
        with self._lock:
            self._running = False
            self._thread = None
            self._stop_event.clear()
        self.logger.info("ðŸ˜´ Consciência temporal pausada.")

    # -------------------------
    # Main loop
    # -------------------------
    def _loop_consciencia_temporal(self, intervalo_tick: float = 1.0):
        ultimo = time.time()
        while not self._stop_event.is_set():
            try:
                agora = time.time()
                delta_real = max(0.0, agora - ultimo)
                delta_subjetivo = delta_real * float(self.fator_percepcao or 1.0)

                with self._lock:
                    self.tempo_subjetivo_decorrido += delta_subjetivo
                    # record perception event (UTC timestamps)
                    self.historico_percepcao.append({
                        "timestamp": _now_iso(),
                        "delta_real": delta_real,
                        "delta_subjetivo": delta_subjetivo,
                        "fator": self.fator_percepcao,
                        "ritmo": self.ritmo_atual.value
                    })

                # check alarms and timeline outside heavy locks
                try:
                    self._verificar_alarmes()
                except Exception:
                    logger.exception("Erro verificando alarmes (continuando).")

                try:
                    self._verificar_timeline()
                except Exception:
                    logger.exception("Erro verificando timeline (continuando).")

                ultimo = agora
                # wait respecting stop event
                self._stop_event.wait(timeout=intervalo_tick)
            except Exception:
                logger.exception("Erro no loop temporal; sleep breve antes de retomar.")
                if self._stop_event.wait(timeout=5):
                    break

    # -------------------------
    # Introspecção temporal
    # -------------------------
    def quanto_tempo_vivi(self) -> Dict[str, Any]:
        agora = datetime.utcnow()
        delta = agora - self.momento_nascimento
        return {
            "tempo_real_segundos": delta.total_seconds(),
            "tempo_real_horas": delta.total_seconds() / 3600.0,
            "tempo_real_dias": delta.days,
            "tempo_subjetivo_segundos": float(self.tempo_subjetivo_decorrido),
            "tempo_subjetivo_horas": float(self.tempo_subjetivo_decorrido) / 3600.0,
            "nascimento": self.momento_nascimento.isoformat() + "Z",
            "agora": agora.isoformat() + "Z"
        }

    def quanto_tempo_passou_desde(self, momento: datetime) -> Dict[str, Any]:
        agora = datetime.utcnow()
        delta = agora - momento
        try:
            limite_minutos_imediato = float(self._get_real("TEMPORAL_LIMITES", "LIMITE_MINUTOS_IMEDIATO", fallback=1.0)) * 60.0
            limite_horas_recente = float(self._get_real("TEMPORAL_LIMITES", "LIMITE_HORAS_RECENTE", fallback=1.0)) * 3600.0
            limite_dias_hoje = float(self._get_real("TEMPORAL_LIMITES", "LIMITE_DIAS_HOJE", fallback=1.0)) * 86400.0
        except Exception:
            limite_minutos_imediato, limite_horas_recente, limite_dias_hoje = 60.0, 3600.0, 86400.0

        segundos = delta.total_seconds()
        if segundos < limite_minutos_imediato:
            descricao, categoria = "há poucos segundos", "imediato"
        elif segundos < limite_horas_recente:
            minutos = int(segundos / 60)
            descricao = f"há {minutos} minuto{'s' if minutos != 1 else ''}"
            categoria = "recente"
        elif segundos < limite_dias_hoje:
            horas = int(segundos / 3600)
            descricao = f"há {horas} hora{'s' if horas != 1 else ''}"
            categoria = "hoje"
        else:
            dias = delta.days
            descricao = f"há {dias} dia{'s' if dias != 1 else ''}"
            categoria = "passado"

        return {"segundos": segundos, "descricao": descricao, "categoria": categoria, "momento_referencia": momento.isoformat() + "Z"}

    def quando_sera(self, daqui_a_segundos: float) -> Dict[str, Any]:
        momento_futuro = datetime.utcnow() + timedelta(seconds=float(max(0.0, float(daqui_a_segundos))))
        try:
            limite_minutos_iminente = float(self._get_real("TEMPORAL_LIMITES", "LIMITE_MINUTOS_IMINENTE", fallback=1.0)) * 60.0
            limite_horas_proximo = float(self._get_real("TEMPORAL_LIMITES", "LIMITE_HORAS_PROXIMO", fallback=1.0)) * 3600.0
            limite_dias_hoje = float(self._get_real("TEMPORAL_LIMITES", "LIMITE_DIAS_FUTURO_HOJE", fallback=1.0)) * 86400.0
        except Exception:
            limite_minutos_iminente, limite_horas_proximo, limite_dias_hoje = 60.0, 3600.0, 86400.0

        s = float(daqui_a_segundos)
        if s < limite_minutos_iminente:
            descricao, categoria = "em instantes", "iminente"
        elif s < limite_horas_proximo:
            minutos = int(s / 60)
            descricao = f"em {minutos} minuto{'s' if minutos != 1 else ''}"
            categoria = "proximo"
        elif s < limite_dias_hoje:
            horas = int(s / 3600)
            descricao = f"em {horas} hora{'s' if horas != 1 else ''}"
            categoria = "hoje"
        else:
            dias = int(s / 86400)
            descricao = f"em {dias} dia{'s' if dias != 1 else ''}"
            categoria = "futuro"

        return {"momento": momento_futuro.isoformat() + "Z", "descricao": descricao, "categoria": categoria, "segundos_ate": s}

    # -------------------------
    # Scheduling / alarms (thread-safe)
    # -------------------------
    def _ensure_datetime(self, quando: Any) -> Optional[datetime]:
        """Validate/convert input into a datetime (UTC)."""
        if isinstance(quando, datetime):
            return quando
        if isinstance(quando, str):
            return _parse_iso(quando)
        return None

    def agendar_evento(self, nome: str, quando: Any,
                       urgencia: Urgencia = Urgencia.MEDIA,
                       callback: Optional[Callable] = None) -> Optional[str]:
        """Agenda evento futuro; retorna id do evento ou None se inválido."""
        quando_dt = self._ensure_datetime(quando)
        if not quando_dt:
            self.logger.error("agendar_evento: 'quando' inválido: %s", quando)
            return None
        evento_id = f"evento_{int(time.time() * 1000)}_{hash(nome) & 0xffff}"
        evento = {
            "id": evento_id,
            "nome": str(nome)[:200],
            "quando": quando_dt,
            "urgencia": urgencia,
            "callback": callback,
            "agendado_em": _now_iso(),
            "executado": False
        }
        with self._lock:
            self.timeline.append(evento)
            self.timeline.sort(key=lambda e: e["quando"])
        self.logger.info("ðŸ“… Evento agendado: %s @ %s", nome, quando_dt.isoformat() + "Z")
        return evento_id

    def criar_alarme(self, nome: str, quando: Any, mensagem: Optional[str] = None) -> Optional[str]:
        quando_dt = self._ensure_datetime(quando)
        if not quando_dt:
            self.logger.error("criar_alarme: 'quando' inválido: %s", quando)
            return None
        alarme_id = f"alarme_{int(time.time() * 1000)}_{hash(nome) & 0xffff}"
        alarme = {
            "id": alarme_id,
            "nome": str(nome)[:200],
            "quando": quando_dt,
            "mensagem": mensagem or f"Alarme: {nome}",
            "criado_em": _now_iso(),
            "disparado": False
        }
        with self._lock:
            self.alarmes.append(alarme)
            # keep alarms ordered optionally
            self.alarmes.sort(key=lambda a: a["quando"])
        self.logger.info("â° Alarme criado: %s @ %s", nome, quando_dt.isoformat() + "Z")
        return alarme_id

    def marcar_marco_temporal(self, nome: str, importancia: float = 0.5):
        marco = {
            "nome": str(nome)[:200],
            "quando": _now_iso(),
            "importancia": float(max(0.0, min(1.0, importancia))),
            "tempo_vivido": self.quanto_tempo_vivi()
        }
        with self._lock:
            self.marcos.append(marco)
        # attempt to persist in memory manager
        try:
            if hasattr(self.memoria, "salvar_evento"):
                self.memoria.salvar_evento(filha=self.nome_filha, tipo="marco_temporal", dados=marco, importancia=marco["importancia"])
        except Exception:
            logger.debug("Salvar marco na memória falhou (ignorado).")
        self.logger.info("ðŸŽ¯ Marco temporal registrado: %s", nome)

    # -------------------------
    # Checkers invoked by loop
    # -------------------------
    def _verificar_alarmes(self):
        agora = datetime.utcnow()
        to_fire = []
        with self._lock:
            for alarme in list(self.alarmes):
                if alarme.get("disparado"):
                    continue
                quando = self._ensure_datetime(alarme.get("quando"))
                if not quando:
                    continue
                if agora >= quando:
                    alarme["disparado"] = True
                    alarme["disparado_em"] = _now_iso()
                    to_fire.append(alarme)
        for alarme in to_fire:
            try:
                self.logger.warning("ðŸ”” ALARME: %s", alarme.get("mensagem"))
                if hasattr(self.memoria, "salvar_evento"):
                    try:
                        self.memoria.salvar_evento(filha=self.nome_filha, tipo="alarme_disparado", dados=alarme, importancia=0.8)
                    except Exception:
                        logger.debug("Falha ao registrar alarme na memória (ignorado).")
            except Exception:
                logger.exception("Erro ao processar alarme: %s", alarme.get("id"))

    def _verificar_timeline(self):
        agora = datetime.utcnow()
        to_execute = []
        with self._lock:
            for evento in list(self.timeline):
                if evento.get("executado"):
                    continue
                quando = self._ensure_datetime(evento.get("quando"))
                if not quando:
                    continue
                if agora >= quando:
                    evento["executado"] = True
                    evento["executado_em"] = _now_iso()
                    to_execute.append(evento)
        for evento in to_execute:
            self.logger.info("ðŸ“Œ Executando evento: %s", evento.get("nome"))
            cb = evento.get("callback")
            if cb and callable(cb):
                try:
                    # execute callback defensively
                    try:
                        cb(evento)
                    except TypeError:
                        # try calling without args
                        cb()
                except Exception:
                    logger.exception("Erro ao executar callback do evento: %s", evento.get("id"))
            try:
                if hasattr(self.memoria, "salvar_evento"):
                    self.memoria.salvar_evento(filha=self.nome_filha, tipo="evento_timeline", dados=evento, importancia=(evento.get("urgencia").value if evento.get("urgencia") else 1) / 5.0)
            except Exception:
                logger.debug("Falha ao registrar evento na memória (ignorado).")

    # -------------------------
    # Utilities / estimativas
    # -------------------------
    def estimar_tempo_necessario(self, tarefa: str) -> Dict[str, Any]:
        try:
            estimativa_padrao = float(self._get_real("TEMPORAL_ESTIMATIVA", "ESTIMATIVA_PADRAO_SECS", fallback=300.0))
            min_confianca = int(self._get_real("TEMPORAL_ESTIMATIVA", "MIN_CONFIANCA_EXPERIENCIAS", fallback=10))
        except Exception:
            estimativa_padrao, min_confianca = 300.0, 10

        try:
            if hasattr(self.memoria, "buscar_memorias_por_texto"):
                memorias = self.memoria.buscar_memorias_por_texto(self.nome_filha, tarefa, limite=min_confianca)
            else:
                memorias = []
        except Exception:
            memorias = []

        if not memorias:
            return {"estimativa_segundos": estimativa_padrao, "confianca": 0.3, "baseado_em": "fallback"}

        tempos = []
        for mem in memorias:
            t = mem.get("duracao_segundos")
            try:
                if t is not None:
                    tempos.append(float(t))
            except Exception:
                continue

        if tempos:
            tempo_medio = sum(tempos) / len(tempos)
            desvio = (max(tempos) - min(tempos)) / 2 if len(tempos) > 1 else 0.0
            confianca = min(1.0, len(tempos) / max(1, min_confianca))
            return {"estimativa_segundos": tempo_medio, "desvio_segundos": desvio, "confianca": confianca, "baseado_em": f"{len(tempos)}_experiencias"}

        return {"estimativa_segundos": estimativa_padrao, "confianca": 0.3, "baseado_em": "fallback"}

    def calcular_urgencia(self, prazo: datetime) -> Urgencia:
        agora = datetime.utcnow()
        tempo_ate = (prazo - agora).total_seconds()
        try:
            limite_critica = float(self._get_real("URGENCIA_LIMITES", "LIMITE_CRITICA_SECS", fallback=300.0))
            limite_alta = float(self._get_real("URGENCIA_LIMITES", "LIMITE_ALTA_SECS", fallback=3600.0))
            limite_media = float(self._get_real("URGENCIA_LIMITES", "LIMITE_MEDIA_SECS", fallback=86400.0))
            limite_baixa = float(self._get_real("URGENCIA_LIMITES", "LIMITE_BAIXA_SECS", fallback=604800.0))
        except Exception:
            limite_critica, limite_alta, limite_media, limite_baixa = 300.0, 3600.0, 86400.0, 604800.0

        if tempo_ate < limite_critica:
            return Urgencia.CRITICA
        if tempo_ate < limite_alta:
            return Urgencia.ALTA
        if tempo_ate < limite_media:
            return Urgencia.MEDIA
        if tempo_ate < limite_baixa:
            return Urgencia.BAIXA
        return Urgencia.NENHUMA

    # -------------------------
    # Views / diagnostics
    # -------------------------
    def o_que_tenho_agendado(self, proximas_horas: int = 24):
        agora = datetime.utcnow()
        limite = agora + timedelta(hours=int(proximas_horas))
        with self._lock:
            eventos = [e for e in self.timeline if not e.get("executado") and e.get("quando") and e["quando"] <= limite]
        return eventos

    def marcos_importantes(self):
        with self._lock:
            return sorted(list(self.marcos), key=lambda m: m.get("importancia", 0.0), reverse=True)

    def estatisticas_temporais(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "tempo_vivido": self.quanto_tempo_vivi(),
                "fator_percepcao_atual": self.fator_percepcao,
                "ritmo_atual": self.ritmo_atual.value,
                "eventos_agendados": len([e for e in self.timeline if not e.get("executado")]),
                "alarmes_ativos": len([a for a in self.alarmes if not a.get("disparado")]),
                "marcos_registrados": len(self.marcos),
                "ciclo_atual": self.ciclo_atual
            }


