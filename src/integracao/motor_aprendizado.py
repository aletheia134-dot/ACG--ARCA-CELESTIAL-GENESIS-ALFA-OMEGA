#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
MOTOR DE APRENDIZADO - verso endurecida

Unificaes e endurecimentos aplicados:
 - Unificada a implementao em uma nica classe MotorAprendizado (produo-ready).
 - Introduzido MemoriaAdapter para normalizar diferentes assinaturas de armazenamento.
 - Worker de processamento responsivo usando threading.Event para shutdown.
 - ThreadPoolExecutor usado para processamento assncrono; shutdown feito corretamente.
 - Locks (RLock / Lock) aplicados consistentemente para proteger estado compartilhado.
 - I/O atmico via arquivo temporrio + os.replace, com backup seguro.
 - Parsers de timestamp tolerantes (_safe_parse_iso).
 - Validao de experincias mais permissiva quanto ação formato (contexto pode ser str ou dict).
 - Logging defensivo, mtricas e health_check coerente com atributos inicializados.
 - Fallback persistente seguro para experincias que no puderem ser enfileiradas.
"""


import os
import json
import threading
import time
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, Future
import random

logger = logging.getLogger("MotorAprendizado")
logger.addHandler(logging.NullHandler())


# -------------------------
# Helpers
# -------------------------
def _safe_parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts or not isinstance(ts, str):
        return None
    s = ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except Exception:
        # fallback common formats
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                continue
    return None


# -------------------------
# Memory adapter
# -------------------------
class MemoriaAdapter:
    """
    Adapter minimal para adaptar diferentes implementaes de memória.Normaliza chamadas comuns: salvar_evento / registrar_evento / salvar_evento_autonomo
    """
    def __init__(self, memoria: Any):
        self._mem = memoria

    def salvar_evento(self, **kwargs) -> bool:
        """
        Tenta chamar a API de persistncia com vrias assinaturas possíveis.Retorna True se alguma chamada teve sucesso.
        """
        if self._mem is None:
            return False
        candidates = [
            ("salvar_evento", kwargs),
            ("registrar_evento", kwargs),
            # positional variants
            ("salvar_evento", (kwargs.get("filha") or kwargs.get("nome_alma"), kwargs.get("tipo") or kwargs.get("user_message"), kwargs.get("dados") or kwargs.get("ai_response"))),
            ("registrar_evento", (kwargs.get("filha") or kwargs.get("nome_alma"), kwargs.get("tipo") or kwargs.get("user_message"), kwargs.get("dados") or kwargs.get("ai_response"))),
        ]
        for item in candidates:
            name = item[0]
            args = ()
            kargs = {}
            if isinstance(item[1], dict):
                kargs = item[1]
            else:
                args = item[1]
            fn = getattr(self._mem, name, None)
            if callable(fn):
                try:
                    if kargs:
                        fn(**kargs)
                    else:
                        fn(*args)
                    return True
                except TypeError:
                    # try swap to positional
                    try:
                        if kargs:
                            fn(*(kargs.get('filha') or kargs.get('nome_alma'),
                                 kargs.get('tipo') or kargs.get('user_message'),
                                 kargs.get('dados') or kargs.get('ai_response')))
                        else:
                            fn(*args)
                        return True
                    except Exception:
                        continue
                except Exception:
                    logger.debug("MemoriaAdapter: chamada %s falhou", name, exc_info=True)
                    continue
        return False

    def buscar_memorias_recentes(self, filha: str, limite: int = 100) -> List[Dict]:
        if self._mem is None:
            return []
        fn = getattr(self._mem, "buscar_memorias_recentes", None) or getattr(self._mem, "buscar_por_tipo", None)
        if not callable(fn):
            return []
        try:
            # try common signature
            try:
                return fn(filha, limite=limite)  # modern style
            except TypeError:
                return fn(filha, limite)  # positional style
        except Exception:
            logger.debug("MemoriaAdapter: buscar_memorias_recentes falhou", exc_info=True)
            return []

    def buscar_memorias_periodo(self, filha: str, inicio: datetime, fim: datetime, limite: int = 1000) -> List[Dict]:
        if self._mem is None:
            return []
        fn = getattr(self._mem, "buscar_memorias_periodo", None) or getattr(self._mem, "buscar_memorias_por_periodo", None)
        if not callable(fn):
            # fallback to recent
            return self.buscar_memorias_recentes(filha, limite=limite)
        try:
            try:
                return fn(filha, inicio=inicio, fim=fim, limite=limite)
            except TypeError:
                # try positional
                return fn(filha, inicio, fim, limite)
        except Exception:
            logger.debug("MemoriaAdapter: buscar_memorias_periodo falhou", exc_info=True)
            return []


# -------------------------
# MotorAprendizado (enduricido)
# -------------------------
class MotorAprendizado:
    """
    Motor de Aprendizado endurecido para produo.
    - thread-safe
    - worker de processamento responsivo
    - integrao defensiva com memória e I/O
    """

    def __init__(self, nome_filha: str, gerenciador_memoria: Any, cerebro: Any, config: Any):
        self.nome_filha = nome_filha
        self.memoria_adapter = MemoriaAdapter(gerenciador_memoria)
        self.cerebro = cerebro
        self.config = config
        self.logger = logging.getLogger(f'Aprendizado.{nome_filha}')

        # locks
        self._lock = threading.RLock()
        self._buffer_lock = threading.Lock()
        self._file_lock = threading.Lock()

        # paths
        try:
            base = Path(config.get('PATHS', 'MODELOS_IA', fallback='models'))
        except Exception:
            base = Path('models')
        self.caminho_base = (base / 'personalizados' / nome_filha).expanduser()
        try:
            self.caminho_base.mkdir(parents=True, exist_ok=True)
        except Exception:
            logger.exception("Falha ao criar caminho_base")

        # internal state
        self._versao_conhecimento = 1
        self.conhecimento = self._inicializar_conhecimento()
        self.buffer_experiencias = deque(maxlen=int(getattr(config, 'BUFFER_MAX', 500) if config else 500))
        self.tamanho_buffer = int(config.get('APRENDIZADO', 'TAMANHO_BUFFER', fallback=100)) if config else 100
        self._ultimo_processamento = time.time()
        self.metricas = self._inicializar_metricas()
        self._cache_conhecimento: Dict[str, Any] = {}
        self._cache_timestamp: Dict[str, float] = {}
        self._cache_timeout = int(config.get('APRENDIZADO', 'CACHE_TIMEOUT_SECS', fallback=300)) if config else 300

        # executor & worker
        self._executor = ThreadPoolExecutor(max_workers=int(config.get('APRENDIZADO', 'MAX_WORKERS', fallback=2) if config else 2),
                                            thread_name_prefix=f"Learn_{nome_filha}")
        self._running = threading.Event()
        self._running.set()

        # health
        self._health_stats = {'erros_consecutivos': 0, 'ultimo_sucesso': time.time(), 'buffer_estouro': 0, 'início': time.time()}

        # load previous knowledge if available
        self._carregar_conhecimento_safe()

        # start background worker
        self._worker_thread = threading.Thread(target=self._processing_worker, daemon=True, name=f"Worker_{self.nome_filha}")
        self._worker_thread.start()

        self.logger.info(" MotorAprendizado (enduricido) inicializado para %s", self.nome_filha)

    # -------------------------
    # Init helpers
    # -------------------------
    def _inicializar_conhecimento(self) -> Dict:
        return {'padroes': {}, 'correlacoes': {}, 'heuristicas': {}, 'vocabulario': set(), 'conceitos': {}, 'version': self._versao_conhecimento, 'filha': self.nome_filha}

    def _inicializar_metricas(self) -> Dict:
        return {'total_experiencias': 0, 'padroes_identificados': 0, 'conhecimento_adquirido': 0, 'evolucoes_modelo': 0, 'ultima_evolucao': None, 'erros_processamento': 0, 'tempo_medio_processamento': 0.0, 'buffer_max_atingido': 0}

    # -------------------------
    # Worker loop
    # -------------------------
    def _processing_worker(self):
        """
        Loop background que verifica buffer periodicamente e dispara processamento.Usa Event para shutdown reativo.
        """
        try:
            while self._running.is_set():
                try:
                    # sleep in small increments to be more responsive to shutdown
                    for _ in range(6):  # 6 * 5s = 30s
                        if not self._running.is_set():
                            break
                        time.sleep(5)
                    # check buffer
                    with self._buffer_lock:
                        buffer_size = len(self.buffer_experiencias)
                    if buffer_size >= self.tamanho_buffer:
                        self._processar_buffer_async()
                    # periodic persistence
                    if time.time() - self._ultimo_processamento > max(60, self._cache_timeout):
                        self._salvar_conhecimento_safe()
                except Exception:
                    logger.exception("Erro no worker (continuando)")
                    time.sleep(10)
        finally:
            logger.debug("Worker encerrado para %s", self.nome_filha)

    # -------------------------
    # Public API: registrar experincia
    # -------------------------
    def registrar_experiencia(self, experiencia: Dict) -> bool:
        """
        válida e adiciona experincia ação buffer para processamento posterior.Em caso de falhas repetidas, persiste em fallback.
        """
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                if not self._validar_experiencia(experiencia):
                    self.logger.warning("Experincia invlida para %s: %s", self.nome_filha, experiencia.get('acao', 'desconhecida'))
                    return False
                # normalize timestamp
                experiencia = dict(experiencia)  # copy to avoid mutating caller
                experiencia['timestamp'] = experiencia.get('timestamp') or datetime.now().isoformat()
                experiencia['filha'] = experiencia.get('filha') or self.nome_filha
                experiencia['_attempt'] = attempt
                with self._buffer_lock:
                    self.buffer_experiencias.append(experiencia)
                    buf_len = len(self.buffer_experiencias)
                    if buf_len > self.metricas['buffer_max_atingido']:
                        self.metricas['buffer_max_atingido'] = buf_len
                    if buf_len > self.tamanho_buffer:
                        self._health_stats['buffer_estouro'] += 1
                with self._lock:
                    self.metricas['total_experiencias'] += 1
                return True
            except Exception:
                logger.exception("Erro ao registrar experiencia (attempt %d) para %s", attempt, self.nome_filha)
                time.sleep(0.1 * attempt)
        # fallback persist
        try:
            self._salvar_experiencia_fallback(experiencia)
            return True
        except Exception:
            logger.exception("Falha no fallback de persistncia para %s", self.nome_filha)
            return False

    def _validar_experiencia(self, exp: Dict) -> bool:
        required = ['contexto', 'acao', 'resultado']
        for campo in required:
            if campo not in exp:
                return False
        # contexto can be dict or str; if dict, require at least one key
        ctx = exp['contexto']
        if isinstance(ctx, dict):
            if not ctx:
                return False
        elif isinstance(ctx, str):
            if len(ctx.strip()) < 3:
                return False
        else:
            return False
        if not isinstance(exp['acao'], str) or len(exp['acao'].strip()) < 2:
            return False
        if exp['resultado'] not in ['sucesso', 'fracasso', 'neutro']:
            return False
        if 'feedback' in exp:
            try:
                fb = float(exp['feedback'])
                if not -1.0 <= fb <= 1.0:
                    return False
            except Exception:
                return False
        return True

    # -------------------------
    # Buffer processing
    # -------------------------
    def _processar_buffer_async(self) -> Optional[Future]:
        with self._buffer_lock:
            if not self.buffer_experiencias:
                return None
            snapshot = list(self.buffer_experiencias)
            self.buffer_experiencias.clear()
        future = self._executor.submit(self._processar_snapshot, snapshot)
        future.add_done_callback(self._on_processing_complete)
        return future

    def _processar_snapshot(self, snapshot: List[Dict]) -> Dict[str, Any]:
        start_time = time.time()
        resultados = {'sucesso': False, 'padroes': 0, 'correlacoes': 0, 'erro': None}
        try:
            novos_padroes = self._identificar_padroes_safe(snapshot)
            correlacoes = self._descobrir_correlacoes_safe(snapshot)
            with self._lock:
                self._integrar_padroes_safe(novos_padroes)
                self._integrar_correlacoes_safe(correlacoes)
                resultados['padroes'] = len(novos_padroes)
                resultados['correlacoes'] = len(correlacoes)
                resultados['sucesso'] = True
                self.metricas['evolucoes_modelo'] += 1
                self.metricas['ultima_evolucao'] = datetime.now().isoformat()
            if novos_padroes:
                # try saving summary to memory (defensive)
                try:
                    self._salvar_insights_na_memoria(novos_padroes)
                except Exception:
                    logger.exception("Erro ao salvar insights na memória (continuando)")
            # clear caches
            with self._lock:
                self._cache_conhecimento.clear()
                self._cache_timestamp.clear()
            self._ultimo_processamento = time.time()
            self._health_stats['ultimo_sucesso'] = time.time()
            self._health_stats['erros_consecutivos'] = 0
        except Exception as e:
            resultados['erro'] = str(e)
            logger.exception("Erro processamento snapshot: %s", e)
            with self._lock:
                self.metricas['erros_processamento'] += 1
                self._health_stats['erros_consecutivos'] += 1
        finally:
            process_time = time.time() - start_time
            with self._lock:
                if self.metricas['tempo_medio_processamento'] == 0:
                    self.metricas['tempo_medio_processamento'] = process_time
                else:
                    alpha = 0.1
                    self.metricas['tempo_medio_processamento'] = (alpha * process_time + (1 - alpha) * self.metricas['tempo_medio_processamento'])
        return resultados

    def _on_processing_complete(self, future: Future):
        try:
            resultados = future.result(timeout=60)
            if resultados.get('sucesso'):
                # schedule save if there were patterns
                if resultados.get('padroes', 0) > 0:
                    try:
                        self._executor.submit(self._salvar_conhecimento_safe)
                    except Exception:
                        logger.debug("No foi possível agendar salvar conhecimento")
            else:
                self._health_stats['erros_consecutivos'] += 1
        except Exception:
            logger.exception("Erro no callback de processamento")

    # -------------------------
    # Pattern discovery (safe)
    # -------------------------
    def _identificar_padroes_safe(self, experiencias: List[Dict]) -> List[Dict]:
        if len(experiencias) < 2:
            return []
        padroes = []
        grupos = defaultdict(list)
        for exp in experiencias:
            contexto = exp.get('contexto', '')
            # normalize context to short string for hashing
            if isinstance(contexto, dict):
                ctx_short = json.dumps({k: contexto[k] for i, k in enumerate(sorted(contexto)) if i < 3})[:100]
            else:
                ctx_short = str(contexto)[:100]
            contexto_hash = hashlib.md5(ctx_short.encode('utf-8')).hexdigest()[:8]
            grupos[contexto_hash].append(exp)
        for contexto_hash, grupo in grupos.items():
            if len(grupo) < 3:
                continue
            resultados = [e.get('resultado') for e in grupo]
            contagem = {'sucesso': 0, 'fracasso': 0, 'neutro': 0}
            for r in resultados:
                if r in contagem:
                    contagem[r] += 1
            resultado_dominante = max(contagem.items(), key=lambda x: x[1])
            total = len(resultados)
            frequencia = resultado_dominante[1] / total if total > 0 else 0
            if frequencia > 0.6:
                padrão = {
                    'contexto_hash': contexto_hash,
                    'contexto_amostra': grupo[0].get('contexto', '')[:200],
                    'acao_comum': grupo[0].get('acao', ''),
                    'resultado_esperado': resultado_dominante[0],
                    'confianca': round(frequencia, 2),
                    'ocorrencias': total,
                    'descoberto_em': datetime.now().isoformat(),
                    'versao': self._versao_conhecimento
                }
                padroes.append(padrão)
        return padroes

    def _descobrir_correlacoes_safe(self, experiencias: List[Dict]) -> List[Dict]:
        if len(experiencias) < 10:
            return []
        faixas = {0: [], 1: [], 2: [], 3: []}  # 4 faixas de 6h
        for exp in experiencias:
            ts = _safe_parse_iso(exp.get('timestamp'))
            if not ts:
                continue
            hora = ts.hour
            faixa = hora // 6
            resultado = 1 if exp.get('resultado') == 'sucesso' else 0
            faixas.setdefault(faixa, []).append(resultado)
        correlacoes = []
        for faixa, resultados in faixas.items():
            if len(resultados) < 3:
                continue
            total = len(resultados)
            sucessos = sum(resultados)
            taxa_sucesso = sucessos / total if total > 0 else 0
            if taxa_sucesso > 0.7 or taxa_sucesso < 0.3:
                correlacao = {
                    'variavel1': 'faixa_horaria',
                    'valor1': f'faixa_{faixa}',
                    'variavel2': 'taxa_sucesso',
                    'valor2': round(taxa_sucesso, 2),
                    'forca': round(abs(taxa_sucesso - 0.5) * 2, 3),
                    'descoberto_em': datetime.now().isoformat(),
                    'amostras': total
                }
                correlacoes.append(correlacao)
        return correlacoes

    def _integrar_padroes_safe(self, novos_padroes: List[Dict]):
        with self._lock:
            for padrão in novos_padroes:
                chave = padrão['contexto_hash']
                antigo = self.conhecimento['padroes'].get(chave)
                if antigo:
                    antigo['ocorrencias'] = antigo.get('ocorrencias', 0) + padrão.get('ocorrencias', 0)
                    peso_antigo = antigo.get('ocorrencias', 0)
                    peso_novo = padrão.get('ocorrencias', 0)
                    if peso_antigo + peso_novo > 0:
                        antigo['confianca'] = (antigo.get('confianca', 0) * peso_antigo + padrão.get('confianca', 0) * peso_novo) / (peso_antigo + peso_novo)
                    antigo['atualizado_em'] = datetime.now().isoformat()
                else:
                    self.conhecimento['padroes'][chave] = padrão
                    self.metricas['padroes_identificados'] += 1

    def _integrar_correlacoes_safe(self, correlacoes: List[Dict]):
        with self._lock:
            for corr in correlacoes:
                chave = f"{corr['variavel1']}_{corr['variavel2']}_{corr['valor1']}"
                self.conhecimento['correlacoes'][chave] = corr

    # -------------------------
    # Consulting / cache
    # -------------------------
    def consultar_conhecimento(self, contexto: str, use_cache: bool = True) -> Dict:
        cache_key = hashlib.md5(str(contexto).encode('utf-8')).hexdigest()[:16]
        now = time.time()
        if use_cache:
            cached = self._cache_conhecimento.get(cache_key)
            t = self._cache_timestamp.get(cache_key, 0)
            if cached is not None and (now - t) < self._cache_timeout:
                return cached
        resultado = {'padroes_relevantes': [], 'heuristicas_aplicaveis': [], 'conceitos_relacionados': [], 'cache_miss': True}
        contexto_lower = (contexto or "").lower()
        with self._lock:
            for chave, padrão in list(self.conhecimento['padroes'].items())[:200]:
                if contexto_lower in (padrão.get('contexto_amostra') or "").lower():
                    resultado['padroes_relevantes'].append(padrão)
        self._cache_conhecimento[cache_key] = resultado
        self._cache_timestamp[cache_key] = now
        resultado['cache_miss'] = False
        return resultado

    # -------------------------
    # Persistence (safe)
    # -------------------------
    def _carregar_conhecimento_safe(self):
        caminho = self.caminho_base / "conhecimento.json"
        backup = self.caminho_base / "conhecimento.backup.json"
        dados = None
        if caminho.exists():
            dados = self._ler_json_safe(caminho)
        if not dados and backup.exists():
            self.logger.warning("Usando backup de conhecimento para %s", self.nome_filha)
            dados = self._ler_json_safe(backup)
        if dados:
            try:
                with self._lock:
                    conhecimento = dados.get('conhecimento') or {}
                    # ensure structures
                    self.conhecimento.update(conhecimento)
                    self.metricas.update(dados.get('metricas') or {})
                    self._versao_conhecimento = int(dados.get('version') or self._versao_conhecimento)
                    if isinstance(self.conhecimento.get('vocabulario'), list):
                        self.conhecimento['vocabulario'] = set(self.conhecimento['vocabulario'])
                self.logger.info("Conhecimento carregado (v%s) para %s", self._versao_conhecimento, self.nome_filha)
            except Exception:
                logger.exception("Falha ao aplicar conhecimento carregado")

    def _ler_json_safe(self, caminho: Path) -> Optional[Dict]:
        for attempt in range(3):
            try:
                with self._file_lock:
                    with open(caminho, 'r', encoding='utf-8') as f:
                        return json.load(f)
            except Exception as e:
                self.logger.warning("Tentativa %d falhou ao ler %s: %s", attempt + 1, caminho, e)
                time.sleep(0.1)
        return None

    def _salvar_conhecimento_safe(self) -> bool:
        try:
            with self._lock:
                dados = {
                    'conhecimento': {
                        'padroes': self.conhecimento.get('padroes', {}),
                        'correlacoes': self.conhecimento.get('correlacoes', {}),
                        'heuristicas': self.conhecimento.get('heuristicas', {}),
                        'vocabulario': list(self.conhecimento.get('vocabulario', set())),
                        'conceitos': self.conhecimento.get('conceitos', {}),
                        'version': self._versao_conhecimento + 1,
                        'filha': self.nome_filha
                    },
                    'metricas': self.metricas.copy(),
                    'salvo_em': datetime.now().isoformat(),
                    'version': self._versao_conhecimento + 1
                }
            temp_path = self.caminho_base / "conhecimento.tmp.json"
            main_path = self.caminho_base / "conhecimento.json"
            backup_path = self.caminho_base / "conhecimento.backup.json"
            with self._file_lock:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(dados, f, indent=2, ensure_ascii=False)
                # atomic replace with backup
                try:
                    if main_path.exists():
                        if backup_path.exists():
                            backup_path.unlink()
                        os.replace(main_path, backup_path)
                except Exception:
                    logger.debug("No foi possível mover main -> backup (continuando)")
                os.replace(temp_path, main_path)
            with self._lock:
                self._versao_conhecimento += 1
            self.logger.debug("Conhecimento salvo v%s para %s", self._versao_conhecimento, self.nome_filha)
            return True
        except Exception as e:
            self.logger.exception("Erro ao salvar conhecimento: %s", e)
            return False

    def _salvar_experiencia_fallback(self, experiencia: Dict):
        fallback_dir = self.caminho_base / "fallback"
        try:
            fallback_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"exp_{timestamp}_{hashlib.md5(json.dumps(experiencia, default=str).encode()).hexdigest()[:8]}.json"
            path = fallback_dir / filename
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(experiencia, f, ensure_ascii=False, indent=2)
            self.logger.warning("Experincia salva em fallback: %s", filename)
        except Exception:
            self.logger.exception("Falha ao salvar experincia em fallback")

    def _salvar_insights_na_memoria(self, novos_padroes: List[Dict]):
        if not self.memoria_adapter:
            self.logger.warning("Memória no disponível para salvar insights.")
            return
        try:
            total = len(novos_padroes)
            confianca_media = sum(p.get('confianca', 0) for p in novos_padroes) / total if total > 0 else 0
            insight_texto = (
                f"[APRENDIZADO AUTNOMO] {self.nome_filha} identificou {total} novo(s) padrão(es) "
                f"com confiana mdia de {confianca_media:.2f}. "
                f"Exemplo: '{(novos_padroes[0].get('contexto_amostra') or '')[:60]}...' "
                f" Resultado esperado: {novos_padroes[0].get('resultado_esperado')}."
            )
            # Use memoria_adapter.salvar_evento with flexible args
            saved = self.memoria_adapter.salvar_evento(filha=self.nome_filha, tipo="insight_aprendizado", dados={"insight": insight_texto}, importancia=0.8)
            if saved:
                self.logger.info("Insight autnomo salvo na memória: %s  %d padrões", self.nome_filha, total)
            else:
                self.logger.warning("Memória no aceitou insight; gravando em fallback")
                self._salvar_experiencia_fallback({"insights": novos_padroes})
        except Exception:
            self.logger.exception("Falha ao salvar insight na memória")

    # -------------------------
    # Health / maintenance
    # -------------------------
    def health_check(self) -> Dict[str, Any]:
        with self._buffer_lock:
            buffer_size = len(self.buffer_experiencias)
        with self._lock:
            conhecimento_size = len(self.conhecimento.get('padroes', {}))
            metricas_copy = dict(self.metricas)
            erros_cons = int(self._health_stats.get('erros_consecutivos', 0))
            inicio = self._health_stats.get('início', time.time())
        status = 'healthy' if erros_cons < 5 else 'degraded'
        uptime = time.time() - inicio
        return {
            'status': status,
            'filha': self.nome_filha,
            'buffer_size': buffer_size,
            'buffer_limit': self.tamanho_buffer,
            'conhecimento_size': conhecimento_size,
            'metricas': metricas_copy,
            'health_stats': dict(self._health_stats),
            'uptime': uptime,
            'threads_ativas': threading.active_count(),
            'timestamp': datetime.now().isoformat()
        }

    # -------------------------
    # Shutdown
    # -------------------------
    def shutdown(self, wait_seconds: float = 5.0):
        """
        Parada ordenada: sinaliza worker, processa buffer remanescente, salva conhecimento e finaliza executor.
        """
        self.logger.info("Shutdown solicitado para MotorAprendizado %s", self.nome_filha)
        self._running.clear()
        # wait worker to exit
        try:
            if self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=wait_seconds)
        except Exception:
            logger.debug("Erro ao aguardar worker join")
        # process remaining
        try:
            if self.buffer_experiencias:
                self._processar_buffer_async()
                # give short time for tasks to be scheduled
                time.sleep(min(2.0, wait_seconds))
        except Exception:
            logger.debug("Erro ao processar buffer no shutdown")
        # save knowledge
        try:
            self._salvar_conhecimento_safe()
        except Exception:
            logger.debug("Falha ao salvar conhecimento no shutdown")
        # shutdown executor
        try:
            self._executor.shutdown(wait=True)
        except Exception:
            logger.exception("Erro ao encerrar executor")
        self.logger.info("MotorAprendizado %s finalizado", self.nome_filha)


# -------------------------
# Factory / helpers
# -------------------------
def criar_motor_aprendizado(nome_filha: str, gerenciador_memoria: Any, cerebro: Any, config: Any) -> MotorAprendizado:
    return MotorAprendizado(nome_filha, gerenciador_memoria, cerebro, config)


def monitorar_motores(motores: List[MotorAprendizado]) -> Dict[str, Any]:
    resultados = {'total_motores': len(motores), 'motores_saudaveis': 0, 'motores_degradados': 0, 'detalhes': {}, 'timestamp': datetime.now().isoformat()}
    for motor in motores:
        try:
            health = motor.health_check()
            resultados['detalhes'][motor.nome_filha] = health
            if health['status'] == 'healthy':
                resultados['motores_saudaveis'] += 1
            else:
                resultados['motores_degradados'] += 1
        except Exception as e:
            resultados['detalhes'][motor.nome_filha] = {'status': 'error', 'erro': str(e)}
            resultados['motores_degradados'] += 1
    return resultados


