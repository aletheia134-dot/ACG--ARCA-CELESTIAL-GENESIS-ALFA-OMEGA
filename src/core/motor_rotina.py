# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Motor de Monitoramento (antigo MotorDeRotina) - verso endurecida

Responsabilidades:
 - Monitorar sade do sistema (CPU/RAM/Disco/processos)
 - Registrar histórico de diagnsticos com escrita atmica
 - Propor solues ação "Pai" via coracao (defensivo)
 - Executar em thread com stop_event e leitura segura de configuração

Melhorias principais aplicadas:
 - get_safe / get_real para leitura de config (get_real usado apenas quando necessário)
 - psutil tratado como opcional (fallback seguro)
 - Uso de threading.Event.wait para loops interrompveis
 - Locks para proteger estado compartilhado
 - Proteo e timeouts ação enfileirar mensagens em coracao
 - Parsing robusto de logs (tail via deque) com dateutil fallback
 - Garantia de criao de diretórios antes de escrita
 - Non-blocking sampling de CPU (evita cpu_percent(interval=1) no init)
"""


import json
import logging
import threading
import time
import uuid
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Optional imports
try:
    import psutil  # type: ignore
    _PSUTIL_AVAILABLE = True
except:
    logging.getLogger(__name__).warning("[AVISO] psutil no disponível")
    psutil = None
    _PSUTIL_AVAILABLE = False

try:
    from dateutil.parser import isoparse  # type: ignore
    _DATEUTIL_AVAILABLE = True
except:
    logging.getLogger(__name__).warning("[AVISO] psutil no disponível")
    psutil = None
    _DATEUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class ConfigKeyError(Exception):
    pass


def _setup_config_getter(config_obj: Any):
    """Getter estrito  levanta se chave obrigatria estiver ausente."""
    def get_real(section: str, key: str) -> str:
        try:
            if hasattr(config_obj, "get"):
                # prefer signature with fallback
                try:
                    val = config_obj.get(section, key)
                except TypeError:
                    val = config_obj.get(section, key)
            else:
                val = getattr(config_obj, key)
            if val is None:
                raise ConfigKeyError(f"Chave ausente [{section}] {key}")
            return val
        except Exception as e:
            raise ConfigKeyError(f"Erro ao ler [{section}] {key}: {e}")
    return get_real


def _make_get_safe(config_obj: Any):
    """Getter tolerante com fallback: get_safe(section, key, fallback)."""
    def get_safe(section: str, key: str, fallback: Optional[Any] = None) -> Any:
        try:
            if config_obj is None:
                return fallback
            if hasattr(config_obj, "get"):
                try:
                    return config_obj.get(section, key, fallback=fallback)
                except TypeError:
                    try:
                        return config_obj.get(section, key)
                    except Exception:
                        return fallback
            return getattr(config_obj, key, fallback)
        except Exception:
            return fallback
    return get_safe


def _safe_parse_iso(ts: str) -> Optional[Any]:
    if not ts:
        return None
    try:
        if _DATEUTIL_AVAILABLE:
            return isoparse(ts)
        # fallback common patterns
        from datetime import datetime
        return datetime.fromisoformat(ts)
    except Exception:
        return None


class MotorMonitor:
    """
    Monitor do sistema (renomeado de MotorDeRotina).
    """

    def __init__(self, coracao_ref: Any, config: Any):
        self.coracao = coracao_ref
        self.config = config
        self.logger = logging.getLogger("MotorMonitor")
        self._lock = threading.RLock()

        self._get_real = _setup_config_getter(config)
        self._get_safe = _make_get_safe(config)

        # control
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._monitorando = False

        # system metrics (sampled on demand)
        self._ultimo_uso_cpu = 0.0
        self._ultimo_uso_ram = 0.0
        self._ultimo_uso_disco = 0.0

        # filesystem paths (read tolerantly)
        raiz = Path(self._get_safe('PATHS', 'CAMINHO_RAIZ_ARCA', fallback='./arca')).expanduser().resolve()
        santuarios = Path(self._get_safe('PATHS', 'SANTUARIOS_PATH', fallback=str(raiz / 'Santuarios'))).expanduser().resolve()
        diarios = Path(self._get_safe('PATHS', 'DIARIOS_PATH', fallback=str(raiz / 'Diarios'))).expanduser().resolve()

        self.CAMINHO_RAIZ_ARCA = raiz
        self.SANTUARIOS_PATH = santuarios
        self.DIARIOS_PATH = diarios

        # ensure directories exist
        try:
            self.CAMINHO_RAIZ_ARCA.mkdir(parents=True, exist_ok=True)
            self.SANTUARIOS_PATH.mkdir(parents=True, exist_ok=True)
            self.DIARIOS_PATH.mkdir(parents=True, exist_ok=True)
        except Exception:
            self.logger.exception("Falha ao criar diretórios obrigatrios (continuando)")

        self.ARQUIVO_HISTORICO_DIAGNOSTICOS = self.CAMINHO_RAIZ_ARCA / "Logs" / "historico_diagnosticos.json"
        self.historico_diagnosticos: List[Dict[str, Any]] = self._carregar_historico_diagnosticos()

        self.habilidades_path = self.SANTUARIOS_PATH / "habilidades_em_treinamento.json"
        self.protocolo_habilidades: Dict[str, Any] = self._carregar_protocolo_habilidades()

        # ensure parent dirs for files
        try:
            self.ARQUIVO_HISTORICO_DIAGNOSTICOS.parent.mkdir(parents=True, exist_ok=True)
            self.habilidades_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            self.logger.debug("No foi possível garantir diretórios de arquivos (continuando)")

        self.logger.info("[MONITOR] Iniciado MotorMonitor (enduricido). psutil_available=%s", _PSUTIL_AVAILABLE)

    # --- persistence helpers ---
    def _carregar_historico_diagnosticos(self) -> List[Dict[str, Any]]:
        caminho = self.ARQUIVO_HISTORICO_DIAGNOSTICOS
        if not caminho.exists():
            self.logger.debug("Arquivo de diagnsticos no existe, iniciando vazio")
            return []
        try:
            with caminho.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.logger.info("[MONITOR] %d diagnsticos carregados", len(data))
            return data
        except Exception:
            self.logger.exception("Falha ao carregar histórico de diagnsticos; iniciando vazio")
            return []

    def _salvar_historico_diagnosticos(self):
        caminho = self.ARQUIVO_HISTORICO_DIAGNOSTICOS
        try:
            caminho.parent.mkdir(parents=True, exist_ok=True)
            tmp = caminho.with_suffix('.tmp')
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(self.historico_diagnosticos, fh, ensure_ascii=False, indent=2, default=str)
            os.replace(str(tmp), str(caminho))
            self.logger.debug("[MONITOR] histórico de diagnsticos salvo em %s", caminho)
        except Exception:
            self.logger.exception("Falha ao salvar histórico de diagnsticos")

    def _carregar_protocolo_habilidades(self) -> Dict[str, Any]:
        caminho = self.habilidades_path
        if not caminho.exists():
            self.logger.info("[MONITOR] Protocolo de habilidades no encontrado; inicializando vazio")
            return {"ProtocoloHabilidadesUniversais": {}}
        try:
            with caminho.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data
        except Exception:
            self.logger.exception("Falha ao carregar protocolo de habilidades; usando vazio")
            return {"ProtocoloHabilidadesUniversais": {}}

    def _salvar_protocolo_habilidades(self):
        caminho = self.habilidades_path
        try:
            caminho.parent.mkdir(parents=True, exist_ok=True)
            tmp = caminho.with_suffix('.tmp')
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(self.protocolo_habilidades, fh, ensure_ascii=False, indent=2, default=str)
            os.replace(str(tmp), str(caminho))
            self.logger.debug("[MONITOR] Protocolo de habilidades salvo em %s", caminho)
        except Exception:
            self.logger.exception("Falha ao salvar protocolo de habilidades")

    # --- lifecycle ---
    def iniciar_monitoramento(self):
        with self._lock:
            if self._monitorando:
                self.logger.debug("Monitoramento j em execução")
                return
            self._monitorando = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._loop_monitoramento, daemon=True, name="MotorMonitor")
            self._thread.start()
            self.logger.info("[MONITOR] Monitoramento iniciado")

    def parar_monitoramento(self):
        with self._lock:
            if not self._monitorando:
                return
            self._monitorando = False
            self._stop_event.set()
        # join outside lock
        if self._thread and self._thread.is_alive():
            timeout = float(self._get_safe('ROTINA', 'SHUTDOWN_TIMEOUT_SECS', fallback=5.0))
            self._thread.join(timeout=timeout)
        # persist state
        try:
            self._salvar_historico_diagnosticos()
            self._salvar_protocolo_habilidades()
        except Exception:
            self.logger.exception("Erro ao salvar estado no parar_monitoramento")
        self.logger.info("[MONITOR] Monitoramento parado")

    def shutdown(self):
        self.logger.info("[MONITOR] Shutdown solicitado")
        self.parar_monitoramento()

    # --- main loop ---
    def _loop_monitoramento(self):
        self.logger.info("[MONITOR] Loop monitoramento iniciado")
        try:
            initial_wait = float(self._get_safe('ROTINA', 'INICIAL_WAIT_SECS', fallback=0.0))
        except Exception:
            initial_wait = 0.0
        if initial_wait:
            self._stop_event.wait(timeout=initial_wait)

        while not self._stop_event.is_set():
            try:
                nivel_monitoramento = self._get_safe('ROTINA', 'NIVEL_MONITORAMENTO_PADRAO', fallback='moderada')
                # decide if idle
                try:
                    if self.pc_esta_ocioso(nível=nivel_monitoramento):
                        self._realizar_diagnostico()
                    else:
                        self.logger.debug("[MONITOR] Sistema em uso ativo.Pulando diagnstico.")
                except Exception:
                    self.logger.exception("Erro ao avaliar ociosidade (continuando)")

                intervalo = float(self._get_safe('ROTINA', 'INTERVALO_VERIFICACAO_SECS', fallback=300.0))
                self._stop_event.wait(timeout=intervalo)
            except Exception:
                self.logger.exception("Erro no loop de monitoramento (continuando)")
                self._stop_event.wait(timeout=5.0)

        self.logger.info("[MONITOR] Loop monitoramento finalizado")

    # --- diagnose ---
    def _realizar_diagnostico(self):
        self.logger.debug("[MONITOR] Coletando mtricas do sistema...")
        try:
            # thresholds (read safely)
            limiar_cpu_saudavel = float(self._get_safe('DIAGNOSTICO', 'LIMIAR_CPU_SAUDAVEL', fallback=20.0))
            limiar_ram_saudavel = float(self._get_safe('DIAGNOSTICO', 'LIMIAR_RAM_SAUDAVEL', fallback=50.0))
            limiar_cpu_atencao = float(self._get_safe('DIAGNOSTICO', 'LIMIAR_CPU_ATENCAO', fallback=50.0))
            limiar_ram_atencao = float(self._get_safe('DIAGNOSTICO', 'LIMIAR_RAM_ATENCAO', fallback=75.0))
        except Exception:
            limiar_cpu_saudavel = 20.0
            limiar_ram_saudavel = 50.0
            limiar_cpu_atencao = 50.0
            limiar_ram_atencao = 75.0

        try:
            if _PSUTIL_AVAILABLE:
                # non-blocking sample
                try:
                    cpu = psutil.cpu_percent(interval=None)
                except Exception:
                    cpu = psutil.cpu_percent(interval=0.1)
                ram = psutil.virtual_memory().percent
                # choose disk path via config or root
                disk_path = str(self._get_safe('PATHS', 'DISK_MONITOR_PATH', fallback=( '/' if os.name != 'nt' else 'C:\\' )))
                try:
                    disk = psutil.disk_usage(disk_path)
                    uso_disco = (disk.used / disk.total) * 100
                except Exception:
                    disk = psutil.disk_usage('/') if os.name != 'nt' else psutil.disk_usage('C:\\')
                    uso_disco = (disk.used / disk.total) * 100
                processos_ativos = len(psutil.pids())
            else:
                cpu = ram = uso_disco = 0.0
                processos_ativos = 0
        except Exception:
            self.logger.exception("Erro ao coletar mtricas psutil (fallback 0)")
            cpu = ram = uso_disco = 0.0
            processos_ativos = 0

        estado = "Indeterminado"
        if cpu < limiar_cpu_saudavel and ram < limiar_ram_saudavel:
            estado = "Saudvel"
        elif cpu < limiar_cpu_atencao and ram < limiar_ram_atencao:
            estado = "atenção"
        else:
            estado = "Crítico"

        diagnostico = {
            "timestamp": datetime.datetime.now().isoformat(),
            "uso_cpu_percentual": cpu,
            "uso_ram_percentual": ram,
            "uso_disco_percentual": uso_disco,
            "processos_ativos": processos_ativos,
            "estado": estado
        }

        with self._lock:
            self.historico_diagnosticos.append(diagnostico)
            maxlen = int(self._get_safe('DIAGNOSTICO', 'LIMITE_HISTORICO_DIAG', fallback=500))
            if len(self.historico_diagnosticos) > maxlen:
                self.historico_diagnosticos = self.historico_diagnosticos[-maxlen:]
            # persist
            self._salvar_historico_diagnosticos()

        self.logger.info("[MONITOR] Diagnstico: %s CPU=%.1f%% RAM=%.1f%%", estado, cpu, ram)

        # send lightweight notifications to coracao (defensive)
        try:
            if hasattr(self.coracao, "response_queue"):
                payload = {"tipo_resp": "LOG_REINO", "texto": f"[MOTOR] Sistema {estado}. CPU:{cpu:.1f}%, RAM:{ram:.1f}%"}
                try:
                    self.coracao.response_queue.put(payload, timeout=1)
                except Exception:
                    # fallback to non-blocking put
                    try:
                        self.coracao.response_queue.put_nowait(payload)
                    except Exception:
                        self.logger.debug("Falha ao enviar response_queue (ignorado)")
            if hasattr(self.coracao, "response_queue"):
                # also update UI dataset
                try:
                    ui_payload = {"tipo_resp": "ATUALIZAR_DIAGNOSTICO_UI", "diagnosticos": list(self.historico_diagnosticos)}
                    self.coracao.response_queue.put(ui_payload, timeout=1)
                except Exception:
                    try:
                        self.coracao.response_queue.put_nowait(ui_payload)
                    except Exception:
                        pass
        except Exception:
            self.logger.exception("Erro ao notificar coracao (continuando)")

        # analyze recent errors and propose solution if needed
        erros = self._analisar_logs_de_erro()
        if erros:
            detalhes = {"erros": erros[:3]}
            self._propor_solucao_ao_pai(f"Detectados {len(erros)} erros recentes", "Anomalia de Software", detalhes)

    # --- log analysis (tail read, robust parsing) ---
    def _analisar_logs_de_erro(self) -> List[str]:
        log_file = self.CAMINHO_RAIZ_ARCA / "Logs" / "arca_soberana.log"
        linhas_limite = int(self._get_safe('DIAGNOSTICO', 'LIMITE_LINHAS_LOG', fallback=500))
        tempo_limite = float(self._get_safe('DIAGNOSTICO', 'LIMITE_TEMPO_ERRO_SECS', fallback=7 * 24 * 3600))

        if not log_file.exists():
            self.logger.debug("Arquivo de log no encontrado para anlise")
            return []

        erros: List[str] = []
        try:
            # read only tail efficiently
            from collections import deque
            with log_file.open("r", encoding="utf-8", errors="ignore") as fh:
                tail = deque(fh, maxlen=linhas_limite)
            now = datetime.datetime.now()
            for line in tail:
                if "ERROR" in line or "CRITICAL" in line:
                    # try extract timestamp
                    ts_candidate = None
                    # common pattern: ISO at start
                    if len(line) >= 25:
                        ts_candidate = line[:25].strip()
                    parsed = None
                    if ts_candidate:
                        parsed = _safe_parse_iso(ts_candidate)
                    if not parsed:
                        # try to find first token that looks like date via split
                        tokens = line.split()
                        for t in tokens[:3]:
                            parsed = _safe_parse_iso(t)
                            if parsed:
                                break
                    if parsed:
                        delta = (now - parsed).total_seconds()
                        if delta <= time_limite:
                            erros.append(line.strip())
                    else:
                        # if no timestamp parsed, include as potential error
                        erros.append(line.strip())
            return erros
        except Exception:
            self.logger.exception("Falha ao analisar logs")
            return []

    # --- proposal to coracao (defensive) ---
    def _propor_solucao_ao_pai(self, mensagem: str, tipo_problema: str, detalhes: Optional[Dict[str, Any]] = None):
        prazo_limite = float(self._get_safe('PROPOSTA', 'LIMITE_TEMPO_PROPOSTA_SECS', fallback=3600.0))
        with self._lock:
            if self.historico_diagnosticos:
                last_ts = self.historico_diagnosticos[-1].get("timestamp")
                if last_ts:
                    parsed = _safe_parse_iso(last_ts)
                    if parsed and (datetime.datetime.now() - parsed).total_seconds() < prazo_limite:
                        self.logger.debug("Proposta recente j enviada; pulando")
                        return

        self.logger.info("[MONITOR] Propondo soluo ação Pai: %s", tipo_problema)
        # build prompts
        prompt_sistema = (
            f"{getattr(self.coracao, 'validador_etico', {}).get('credo_da_arca', '')}\n"
            "### DIRETIVA MOTOR DE ROTINA ###\n"
            "Responda apenas um JSON com campos: nome_acao, descricao_acao, explicacao_proposito, comando_script"
        )
        prompt_usuario = f"Problema: {mensagem}\nTipo: {tipo_problema}\nDetalhes: {json.dumps(detalhes) if detalhes else 'nenhum'}"

        try:
            proposta_str = ""
            if hasattr(self.coracao, "_enviar_para_cerebro"):
                try:
                    proposta_str = self.coracao._enviar_para_cerebro(prompt_sistema, prompt_usuario, int(self._get_safe('PROPOSTA', 'MAX_TOKENS_PROPOSTA', fallback=300)))
                except Exception:
                    self.logger.exception("Falha ao chamar crebro (continuando)")
            if not proposta_str:
                self.logger.debug("Crebro no retornou proposta; pulando enfileiramento")
                return
            try:
                proposta = json.loads(proposta_str)
            except Exception:
                self.logger.warning("Resposta do crebro no  JSON vlido: %s", (proposta_str[:200] + '...'))
                return
            required = {'nome_acao', 'descricao_acao', 'explicacao_proposito', 'comando_script'}
            if not required.issubset(proposta):
                self.logger.warning("Proposta invlida (campos faltando)")
                return
            comando = {"tipo": "PROPOR_LEI_FILHA", "dados_acao": proposta, "autor": "MotorMonitor"}
            # enqueue defensively
            try:
                if hasattr(self.coracao, "command_queue"):
                    try:
                        self.coracao.command_queue.put(comando, timeout=1)
                    except Exception:
                        try:
                            self.coracao.command_queue.put_nowait(comando)
                        except Exception:
                            self.logger.debug("No foi possível enfileirar comando na command_queue")
            except Exception:
                self.logger.exception("Erro ao enfileirar proposta")
            self.logger.info("[MONITOR] Proposta enfileirada: %s", proposta.get("nome_acao"))
        except Exception:
            self.logger.exception("Erro ao propor soluo (unexpected)")

    # --- utility: detect idle (platform-aware) ---
    def pc_esta_ocioso(self, nível: str = "moderada") -> bool:
        """
        Determina se o sistema est ocioso com base em thresholds.Em Windows tenta usar GetLastInputInfo via ctypes; em outros usa psutil.
        """
        try:
            limiar_cpu = float(self._get_safe('OCIOSIDADE', 'LIMIAR_CPU_OCIOSO', fallback=20.0))
            limiar_ram = float(self._get_safe('OCIOSIDADE', 'LIMIAR_RAM_OCIOSO', fallback=50.0))
            thresholds_map = {
                "leve": float(self._get_safe('OCIOSIDADE', 'LIMIAR_OCIOSIDADE_LEVE_SECS', fallback=30.0)),
                "moderada": float(self._get_safe('OCIOSIDADE', 'LIMIAR_OCIOSIDADE_MODERADA_SECS', fallback=300.0)),
                "profunda": float(self._get_safe('OCIOSIDADE', 'LIMIAR_OCIOSIDADE_PROFUNDA_SECS', fallback=1800.0))
            }
            limiar_ociosidade = thresholds_map.get(nível, thresholds_map["moderada"])
        except Exception:
            limiar_cpu = 20.0
            limiar_ram = 50.0
            limiar_ociosidade = 300.0

        # Windows idle detection
        if os.name == 'nt':
            try:
                import ctypes
                class LASTINPUTINFO(ctypes.Structure):
                    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
                lastInputInfo = LASTINPUTINFO()
                lastInputInfo.cbSize = ctypes.sizeof(lastInputInfo)
                if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lastInputInfo)):
                    millis = ctypes.windll.kernel32.GetTickCount() - lastInputInfo.dwTime
                    segundos_inativos = millis / 1000.0
                    return segundos_inativos > limiar_ociosidade
            except Exception:
                self.logger.debug("Falha na deteco de idle via ctypes (Windows), fallback psutil")
        # fallback using psutil
        if _PSUTIL_AVAILABLE:
            try:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                return cpu < limiar_cpu and ram < limiar_ram
            except Exception:
                self.logger.exception("Erro usando psutil no pc_esta_ocioso")
                return False
        return False


