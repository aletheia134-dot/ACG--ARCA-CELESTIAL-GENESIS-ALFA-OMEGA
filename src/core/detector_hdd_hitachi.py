#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DETECTOR HDD HITACHI - Sistema Completo Endurecido
Local: src/core/detector_hdd_hitachi.py

Integra:
- DetectorHardware (HDD + USB detection)
- SistemaDeMemoriaSoberana (M1/M2/M-LLM)
- CacheHDD (armazenamento no HDD externo)

Principais endurecimentos:
 - Import defensivo (psutil, chromadb, llama_cpp, numpy)
 - WMIC apenas Windows; lsblk em Linux
 - SQLite thread-safe com PRAGMA WAL
 - Llama initialization com múltiplas APIs
 - Cache com escrita atômica
 - Locks para operações críticas
 - Quarantine para arquivos corrompidos/expirados
 - Logging em vez de prints
"""
from __future__ import annotations


import configparser
import csv
import datetime
import json
import logging
import os
import platform
import re
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# ============================================================================
# IMPORTS DEFENSIVOS
# ============================================================================

# numpy (opcional - estruturas multimodais)
try:
    import numpy as np
except:
    logging.getLogger(__name__).warning("âš ï¸ np não disponível")
    np = None

# llama_cpp (opcional - LLM local)
_LLAMACPP_AVAILABLE = False
try:
    from llama_cpp import Llama
    _LLAMACPP_AVAILABLE = True
except:
    logging.getLogger(__name__).warning("âš ï¸ np não disponível")
    np = None

# chromadb (opcional - RAG)
_CHROMA_AVAILABLE = False
try:
    import chromadb
    _CHROMA_AVAILABLE = True
except:
    logging.getLogger(__name__).warning("âš ï¸ np não disponível")
    np = None

# psutil (opcional - detecção de hardware)
try:
    import psutil
except:
    logging.getLogger(__name__).warning("âš ï¸ np não disponível")
    np = None

# ============================================================================
# HELPERS GLOBAIS
# ============================================================================

def _is_windows() -> bool:
    return platform.system().lower().startswith("win")


def _run_cmd(cmd: List[str], timeout: int = 10) -> Tuple[int, str, str]:
    """Executa comando seguro; retorna (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except FileNotFoundError:
        logger.debug("Comando não encontrado: %s", cmd[0])
        return 127, "", f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        logger.warning("Comando timeout: %s", cmd)
        return 124, "", "timeout"
    except Exception as e:
        logger.exception("Erro executando comando: %s", e)
        return 1, "", str(e)


def _now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _safe_filename(name: str, max_len: int = 50) -> str:
    """Sanitiza nome de arquivo."""
    if not name:
        name = "conhecimento"
    cleaned = "".join(c if (c.isalnum() or c in " _-") else "_" for c in name).strip()
    cleaned = cleaned.replace(" ", "_")
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len]
    return cleaned or "conhecimento"


# ============================================================================
# 1.DETECTOR HARDWARE
# ============================================================================

@dataclass
class HDDCheckResult:
    found: bool
    mount_path: Optional[Path]
    model: Optional[str]
    size_bytes: Optional[int]


class DetectorHardware:
    """Detecta HDDs, USBs e informações de sistema."""

    def __init__(self) -> None:
        self.sistema = platform.system()
        self.info_basica = self._obter_info_basica()
        logger.info("DetectorHardware inicializado para %s", self.sistema)

    def _obter_info_basica(self) -> Dict[str, str]:
        return {
            "sistema": self.sistema,
            "maquina": platform.machine(),
            "processador": platform.processor(),
            "arquitetura": platform.architecture()[0],
            "versao": platform.version(),
            "python_version": platform.python_version(),
        }

    def detectar_hdd_externo(
        self,
        modelo_esperado: Optional[str] = None,
        tamanho_esperado_bytes: Optional[int] = None,
    ) -> Tuple[bool, Optional[Path]]:
        """Detecta HDD externo real."""
        try:
            if _is_windows():
                res = self._detectar_hdd_windows(modelo_esperado, tamanho_esperado_bytes)
            else:
                res = self._detectar_hdd_linux(modelo_esperado, tamanho_esperado_bytes)

            if res and res.found:
                return True, res.mount_path

            # Fallback heurístico
            for base in [Path("/media"), Path("/mnt"), Path("/run/media")]:
                if base.exists():
                    for p in base.rglob("*"):
                        if p.is_mount():
                            logger.debug("Fallback: mountpoint %s", p)
                            return True, p
            return False, None
        except Exception as e:
            logger.exception("Erro ao detectar HDD: %s", e)
            return False, None

    def _detectar_hdd_windows(
        self, modelo_esperado: Optional[str], tamanho_esperado_bytes: Optional[int]
    ) -> Optional[HDDCheckResult]:
        """WMIC com /format:csv."""
        cmd = ["wmic", "diskdrive", "get", "Caption,Size,DeviceID", "/format:csv"]
        rc, out, err = _run_cmd(cmd, timeout=8)
        if rc != 0 or not out:
            return None

        try:
            lines = [l for l in out.splitlines() if l.strip()]
            reader = csv.DictReader(lines)
            for row in reader:
                model = row.get("Caption", "").strip()
                size_str = row.get("Size", "").strip()
                try:
                    size = int(size_str) if size_str.isdigit() else 0
                except Exception:
                    size = 0

                matches = True
                if modelo_esperado and (not model or modelo_esperado not in model):
                    matches = False
                if tamanho_esperado_bytes and size != tamanho_esperado_bytes:
                    matches = False

                if matches:
                    for drive_letter in ["D:\\", "E:\\", "F:\\", "G:\\", "H:\\"]:
                        p = Path(drive_letter)
                        if p.exists():
                            logger.info("HDD detectado (Windows): %s", p)
                            return HDDCheckResult(True, p, model, size)
            return HDDCheckResult(False, None, None, None)
        except Exception as e:
            logger.exception("Erro parseando WMIC: %s", e)
            return None

    def _detectar_hdd_linux(
        self, modelo_esperado: Optional[str], tamanho_esperado_bytes: Optional[int]
    ) -> Optional[HDDCheckResult]:
        """lsblk -J -b."""
        cmd = ["lsblk", "-J", "-b", "-o", "NAME,MODEL,SIZE,MOUNTPOINT,TYPE"]
        rc, out, err = _run_cmd(cmd, timeout=8)
        if rc != 0 or not out:
            return None

        try:
            data = json.loads(out)
            for dev in data.get("blockdevices", []):
                if dev.get("type") != "disk":
                    continue
                model = dev.get("model", "") or ""
                size = int(dev.get("size", 0) or 0)
                mountpoint = dev.get("mountpoint")
                matches = True
                if modelo_esperado and (modelo_esperado not in model):
                    matches = False
                if tamanho_esperado_bytes and size != tamanho_esperado_bytes:
                    matches = False
                if matches:
                    if mountpoint:
                        p = Path(mountpoint)
                        if p.exists():
                            logger.info("HDD detectado (Linux): %s", p)
                            return HDDCheckResult(True, p, model, size)
                    for child in dev.get("children", []) or []:
                        mp = child.get("mountpoint")
                        if mp:
                            p = Path(mp)
                            if p.exists():
                                logger.info("HDD via partição: %s", p)
                                return HDDCheckResult(True, p, model, size)
            return HDDCheckResult(False, None, None, None)
        except Exception as e:
            logger.exception("Erro parseando lsblk: %s", e)
            return None

    def detectar_dispositivos_usb(self) -> List[Dict[str, Any]]:
        """Detecta dispositivos USB."""
        dispositivos: List[Dict[str, Any]] = []
        try:
            if _is_windows():
                dispositivos = self._detectar_usb_windows()
            else:
                dispositivos = self._detectar_usb_linux()
        except Exception:
            logger.exception("Erro detectando USB")
        return dispositivos

    def _detectar_usb_windows(self) -> List[Dict[str, Any]]:
        cmd = ["wmic", "logicaldisk", "where", "DriveType=2", "get", "DeviceID,VolumeName,Size", "/format:csv"]
        rc, out, err = _run_cmd(cmd, timeout=6)
        dispositivos = []
        if rc != 0 or not out:
            return dispositivos
        try:
            lines = [l for l in out.splitlines() if l.strip()]
            reader = csv.DictReader(lines)
            for row in reader:
                device_id = (row.get("DeviceID") or "").strip()
                volume_name = (row.get("VolumeName") or "").strip()
                size_str = (row.get("Size") or "").strip()
                try:
                    size = int(size_str) if size_str.isdigit() else 0
                except Exception:
                    size = 0
                path = Path(f"{device_id}\\") if device_id else None
                if path and path.exists():
                    dispositivos.append({
                        "device_id": device_id,
                        "volume_name": volume_name,
                        "size_bytes": size,
                        "path": str(path),
                        "system": "Windows",
                    })
            return dispositivos
        except Exception:
            logger.exception("Erro parseando WMIC logicaldisk")
            return dispositivos

    def _detectar_usb_linux(self) -> List[Dict[str, Any]]:
        cmd = ["lsblk", "-J", "-o", "NAME,MOUNTPOINT,SIZE,TYPE,ROTA,VENDOR,MODEL"]
        rc, out, err = _run_cmd(cmd, timeout=6)
        dispositivos: List[Dict[str, Any]] = []
        if rc != 0 or not out:
            return dispositivos
        try:
            data = json.loads(out)
            for dev in data.get("blockdevices", []):
                rota = str(dev.get("rota", ""))
                tipo = dev.get("type", "")
                model = dev.get("model", "") or ""
                mountpoint = dev.get("mountpoint")
                if tipo == "disk" and (mountpoint or "usb" in model.lower() or rota == "1"):
                    if mountpoint and Path(mountpoint).exists():
                        dispositivos.append({
                            "name": dev.get("name", ""),
                            "mountpoint": mountpoint,
                            "size": dev.get("size", "0"),
                            "model": model,
                            "vendor": dev.get("vendor", ""),
                            "system": "Linux",
                        })
            return dispositivos
        except Exception:
            logger.exception("Erro parseando lsblk para USB")
            return dispositivos

    def obter_info_sistema(self) -> Dict[str, Any]:
        """Retorna informações do sistema."""
        info = dict(self.info_basica)
        try:
            import socket
            try:
                if psutil:
                    info["cpu_cores_physical"] = psutil.cpu_count(logical=False)
                    info["cpu_cores_logical"] = psutil.cpu_count(logical=True)
                    info["cpu_usage_percent"] = psutil.cpu_percent(interval=0.1)
                    mem = psutil.virtual_memory()
                    info["mem_total_gb"] = round(mem.total / (1024**3), 2)
                    info["mem_available_gb"] = round(mem.available / (1024**3), 2)
                    info["mem_used_percent"] = mem.percent
                    disk = psutil.disk_usage("/")
                    info["disk_total_gb"] = round(disk.total / (1024**3), 2)
                    info["disk_used_percent"] = disk.percent
            except Exception:
                logger.debug("psutil não disponível")

            try:
                hostname = socket.gethostname()
                info["hostname"] = hostname
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    s.connect(("8.8.8.8", 80))
                    info["local_ip"] = s.getsockname()[0]
                finally:
                    s.close()
            except Exception:
                info["local_ip"] = "Não disponível"
        except Exception:
            logger.exception("Erro coletando info do sistema")
        return info

    def verificar_espaco_hdd(self, caminho: Path) -> Optional[Dict[str, Any]]:
        """Verifica espaço disponível."""
        try:
            uso = shutil.disk_usage(str(caminho))
            return {
                "caminho": str(caminho),
                "total_gb": round(uso.total / (1024**3), 2),
                "usado_gb": round(uso.used / (1024**3), 2),
                "livre_gb": round(uso.free / (1024**3), 2),
                "percentual_usado": round((uso.used / uso.total) * 100, 2) if uso.total > 0 else 0.0,
            }
        except Exception:
            logger.exception("Erro ao verificar espaço")
            return None

    def testar_velocidade_hdd(self, caminho: Path, tamanho_mb: int = 10) -> Optional[Dict[str, Any]]:
        """Testa velocidade de I/O."""
        try:
            if not caminho.exists() or not caminho.is_dir():
                logger.error("Caminho inválido: %s", caminho)
                return None

            try:
                usage = shutil.disk_usage(str(caminho))
                if usage.free < (tamanho_mb * 1024 * 1024 * 2):
                    logger.warning("Espaço insuficiente")
                    return None
            except Exception:
                pass

            tmp_file = Path(tempfile.NamedTemporaryFile(dir=str(caminho), delete=False).name)
            bytes_to_write = 1024 * 1024
            total_mb = max(1, int(tamanho_mb))

            # Escrita
            start = time.time()
            with open(tmp_file, "wb") as f:
                for _ in range(total_mb):
                    f.write(b"\0" * bytes_to_write)
                    f.flush()
            write_time = time.time() - start

            # Leitura
            start = time.time()
            with open(tmp_file, "rb") as f:
                while f.read(bytes_to_write):
                    pass
            read_time = time.time() - start

            try:
                tmp_file.unlink()
            except Exception:
                pass

            velocidade_escrita = total_mb / write_time if write_time > 0 else 0.0
            velocidade_leitura = total_mb / read_time if read_time > 0 else 0.0

            return {
                "caminho": str(caminho),
                "tamanho_mb": total_mb,
                "tempo_escrita_s": round(write_time, 3),
                "tempo_leitura_s": round(read_time, 3),
                "velocidade_escrita_mb_s": round(velocidade_escrita, 2),
                "velocidade_leitura_mb_s": round(velocidade_leitura, 2),
            }
        except Exception:
            logger.exception("Erro no teste de velocidade")
            return None


# ============================================================================
# 2.SISTEMA DE MEMÓRIA SOBERANA
# ============================================================================

class SistemaDeMemoriaSoberana:
    """Orquesta M1 (SQLite), M2 (ChromaDB) e LLM local."""

    def __init__(self):
        self._llm_model = None
        self._llm_lock = threading.RLock()
        self._lock_escrita = threading.RLock()
        self._chroma_client = None

        # Config
        self._config = configparser.ConfigParser()
        self._config.read("config.ini")
        try:
            self._llm_path = self._config["PATHS"]["LLM_MODELO_LOCAL_PATH"]
            self._santuarios_path = self._config["PATHS"]["SANTUARIOS_BASE_PATH"]
            self._chroma_path = self._config["PATHS"]["CHROMA_DB_PATH"]
            self._max_retries = int(self._config.get("LLM", "MAX_RETRIES", fallback="3"))
        except Exception:
            self._llm_path = None
            self._santuarios_path = "Santuarios"
            self._chroma_path = "Santuarios/Chroma"
            self._max_retries = 3

        self._db_path = Path(self._santuarios_path) / "memoria_curta.sqlite"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._init_chromadb()

    def _init_db(self) -> None:
        """Inicializa SQLite com WAL."""
        try:
            self._db_conn = sqlite3.connect(str(self._db_path), check_same_thread=False, timeout=30)
            cur = self._db_conn.cursor()
            try:
                cur.execute("PRAGMA journal_mode=WAL;")
                cur.execute("PRAGMA foreign_keys=ON;")
            except Exception:
                pass
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS M1_Registros (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    alma TEXT,
                    evento TEXT,
                    dados_io TEXT
                )
                """
            )
            self._db_conn.commit()
            logger.info("SQLite M1 inicializado")
        except Exception as e:
            logger.exception("Erro inicializando SQLite: %s", e)
            raise

    def _init_chromadb(self) -> None:
        """Inicializa ChromaDB se disponível."""
        if not _CHROMA_AVAILABLE:
            logger.warning("chromadb não disponível")
            return
        try:
            chroma_dir = Path(self._chroma_path)
            chroma_dir.mkdir(parents=True, exist_ok=True)
            try:
                self._chroma_client = chromadb.PersistentClient(path=str(chroma_dir))
            except Exception:
                try:
                    self._chroma_client = chromadb.Client()
                except Exception as e:
                    logger.exception("Falha ao iniciar ChromaDB: %s", e)
        except Exception as e:
            logger.exception("Erro ao preparar ChromaDB: %s", e)

    def _iniciar_llm(self) -> None:
        """Carrega LLM se disponível."""
        with self._llm_lock:
            if self._llm_model is not None or not _LLAMACPP_AVAILABLE or not self._llm_path:
                return
            try:
                self._llm_model = Llama(model_path=str(self._llm_path))
                logger.info("LLM local carregado")
            except Exception as e:
                logger.exception("Falha ao carregar LLM: %s", e)
                raise

    def processar_requisicao(self, alma_nome: str, consulta: str, dados_audio: Any = None, dados_video: Any = None) -> str:
        """Processa requisição multimodal."""
        # M1: registra
        try:
            with self._lock_escrita:
                cur = self._db_conn.cursor()
                cur.execute(
                    "INSERT INTO M1_Registros (id, timestamp, alma, evento, dados_io) VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), _now_iso(), alma_nome, consulta, "{}"),
                )
                self._db_conn.commit()
        except Exception:
            logger.exception("Erro ao registrar em M1")

        # M2: RAG
        ctx_rag = []
        if self._chroma_client:
            try:
                coll = self._chroma_client.get_or_create_collection(name="cronicas_do_reino")
                results = coll.query(query_texts=[consulta], n_results=5, include=["documents"])
                ctx_rag = results.get("documents", [[]])[0] if isinstance(results.get("documents"), list) else []
            except Exception:
                logger.exception("Erro na consulta RAG")

        # M-LLM: geração
        if _LLAMACPP_AVAILABLE and self._llm_model is None:
            try:
                self._iniciar_llm()
            except Exception:
                logger.warning("LLM não está disponível")
                return f"Resposta padrão de {alma_nome} para: {consulta}"

        if self._llm_model:
            try:
                prompt = f"Você é {alma_nome}. Pergunta: {consulta}\nContexto RAG: {ctx_rag}\n"
                resposta = self._llm_model.create_completion(prompt, max_tokens=512, temperature=0.7)
                if isinstance(resposta, dict) and resposta.get("choices"):
                    return str(resposta["choices"][0].get("text", ""))
            except Exception as e:
                logger.exception("Erro ao gerar com LLM: %s", e)

        return f"Resposta padrão de {alma_nome} para: {consulta}"

    def shutdown(self) -> None:
        try:
            if getattr(self, "_db_conn", None):
                self._db_conn.close()
        except Exception:
            logger.exception("Erro ao fechar DB")


# ============================================================================
# 3.CACHE HDD
# ============================================================================

class CacheHDD:
    """Gerencia cache no HDD externo (JSON)."""

    def __init__(
        self,
        hdd_base_path: Optional[Path] = None,
        cache_dir_name: str = "Arca_Cache",
        quarantine_dir_name: str = "Arca_Cache_Quarantine",
        max_file_size_bytes: int = 10 * 1024 * 1024,
    ):
        self._lock = threading.RLock()
        self.hdd_path: Optional[Path] = None
        self.cache_dir: Optional[Path] = None
        self.quarantine_dir: Optional[Path] = None
        self.cache_dir_name = cache_dir_name
        self.quarantine_dir_name = quarantine_dir_name
        self._max_file_size_bytes = int(max_file_size_bytes)

        if hdd_base_path:
            self.set_hdd_base_path(hdd_base_path)
        else:
            detected = self._detectar_hdd_automatico()
            if detected:
                self.set_hdd_base_path(detected)

    def set_hdd_base_path(self, path: Path) -> None:
        """Define caminho base do HDD."""
        with self._lock:
            try:
                p = Path(path)
                if not p.exists() or not p.is_dir():
                    raise ValueError(f"Caminho inválido: {p}")
                self.hdd_path = p.resolve()
                self.cache_dir = self.hdd_path / self.cache_dir_name
                self.quarantine_dir = self.hdd_path / self.quarantine_dir_name
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                self.quarantine_dir.mkdir(parents=True, exist_ok=True)
                logger.info("Cache HDD configurado em: %s", self.cache_dir)
            except Exception as e:
                logger.exception("Erro ao configurar HDD: %s", e)
                raise

    def _detectar_hdd_automatico(self) -> Optional[Path]:
        """Detecta HDD automaticamente."""
        try:
            if psutil is not None:
                for part in psutil.disk_partitions(all=False):
                    try:
                        mount = Path(part.mountpoint)
                        if mount == Path("/") or (mount.drive and mount.drive.upper().startswith("C:")):
                            continue
                        usage = psutil.disk_usage(str(mount))
                        if usage.total and usage.total > 100 * 1024 * 1024:
                            return mount
                    except Exception:
                        continue

            common = [Path("D:/"), Path("E:/"), Path("F:/"), Path("/media/"), Path("/mnt/")]
            for p in common:
                if p.exists() and p.is_dir():
                    try:
                        if psutil is not None:
                            usage = psutil.disk_usage(str(p))
                            if usage.total and usage.total > 50 * 1024 * 1024:
                                return p
                        else:
                            if any(p.iterdir()):
                                return p
                    except Exception:
                        continue
        except Exception:
            logger.exception("Erro na detecção automática")
        return None

    def hdd_disponivel(self) -> bool:
        with self._lock:
            return bool(self.cache_dir and self.cache_dir.exists())

    def salvar_conhecimento(
        self,
        topico: str,
        dados: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        expiracao_dias: int = 30,
    ) -> Optional[str]:
        """Salva conhecimento no HDD."""
        with self._lock:
            if not self.hdd_disponivel():
                return None
            try:
                safe_topic = _safe_filename(str(topico or "conhecimento"))
                uniq = uuid.uuid4().hex[:8]
                file_id = f"{safe_topic}_{uniq}"
                file_path = self.cache_dir / f"{file_id}.json"

                timestamp = _now_iso()
                expiracao = (datetime.datetime.utcnow() + datetime.timedelta(days=int(expiracao_dias))).replace(microsecond=0).isoformat() + "Z"

                payload = {
                    "id": file_id,
                    "topico": topico,
                    "dados": dados,
                    "metadata": metadata or {},
                    "timestamp": timestamp,
                    "expiracao": expiracao,
                }

                json_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                if len(json_bytes) > self._max_file_size_bytes:
                    logger.error("Tamanho excede limite")
                    return None

                fd, tmp_path = tempfile.mkstemp(dir=str(self.cache_dir), prefix=file_id + ".", suffix=".tmp")
                try:
                    with os.fdopen(fd, "wb") as tf:
                        tf.write(json_bytes)
                        tf.flush()
                        os.fsync(tf.fileno())
                    os.replace(tmp_path, str(file_path))
                finally:
                    if os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass

                logger.debug("Conhecimento salvo: %s", file_id)
                return file_id
            except Exception:
                logger.exception("Erro ao salvar conhecimento")
                return None

    def carregar_conhecimento(self, topico: Optional[str] = None, file_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Carrega conhecimento."""
        with self._lock:
            if not self.hdd_disponivel():
                return None
            try:
                if file_id:
                    for fp in self.cache_dir.glob("*.json"):
                        if file_id in fp.stem:
                            return self._carregar_arquivo(fp)
                if topico:
                    encontrados = []
                    for fp in self.cache_dir.glob("*.json"):
                        k = self._carregar_arquivo(fp)
                        if k and k.get("topico") == topico:
                            encontrados.append(k)
                    if encontrados:
                        encontrados.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                        return encontrados[0]
                return None
            except Exception:
                logger.exception("Erro ao carregar")
                return None

    def _carregar_arquivo(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Carrega e valida arquivo."""
        try:
            with open(file_path, "rb") as f:
                raw = f.read()
            try:
                conhecimento = json.loads(raw.decode("utf-8"))
            except Exception:
                ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
                corrupt_name = f"{file_path.stem}.corrupt_{ts}{file_path.suffix}"
                corrupt_dest = self.quarantine_dir / corrupt_name if self.quarantine_dir else file_path
                try:
                    shutil.move(str(file_path), str(corrupt_dest))
                except Exception:
                    try:
                        file_path.unlink()
                    except Exception:
                        pass
                return None

            # Validar expiração
            expiracao_str = conhecimento.get("expiracao")
            if expiracao_str:
                try:
                    expiracao_dt = datetime.datetime.fromisoformat(expiracao_str.replace("Z", ""))
                    if expiracao_dt < datetime.datetime.utcnow():
                        ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
                        expired_name = f"{file_path.stem}.expired_{ts}{file_path.suffix}"
                        expired_dest = self.quarantine_dir / expired_name if self.quarantine_dir else file_path
                        try:
                            shutil.move(str(file_path), str(expired_dest))
                        except Exception:
                            try:
                                file_path.unlink()
                            except Exception:
                                pass
                        return None
                except Exception:
                    pass

            return conhecimento
        except Exception:
            logger.exception("Erro ao ler arquivo")
            return None

    def obter_estatisticas(self) -> Dict[str, Any]:
        """Obtém estatísticas do cache."""
        if not self.hdd_disponivel():
            return {"hdd_disponivel": False}
        with self._lock:
            try:
                total_files = 0
                total_bytes = 0
                topics = set()
                for fp in self.cache_dir.glob("*.json"):
                    try:
                        stat = fp.stat()
                        total_files += 1
                        total_bytes += stat.st_size
                    except Exception:
                        pass
                return {
                    "hdd_disponivel": True,
                    "total_arquivos": total_files,
                    "total_tamanho_mb": round(total_bytes / (1024 * 1024), 2),
                    "caminho_cache": str(self.cache_dir),
                }
            except Exception:
                logger.exception("Erro obtendo stats")
                return {"hdd_disponivel": True, "erro": "falha"}


# ============================================================================
# EXPORTS E FUNÇÕES DE CONVENIÍŠNCIA
# ============================================================================

def criar_detector_hitachi() -> DetectorHardware:
    """Cria detector de hardware Hitachi."""
    return DetectorHardware()


def criar_sistema_soberano() -> SistemaDeMemoriaSoberana:
    """Cria sistema de memória soberana."""
    return SistemaDeMemoriaSoberana()


def criar_cache_hdd() -> CacheHDD:
    """Cria cache HDD."""
    return CacheHDD()


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("DetectorHDDHitachiTest")

    logger.info("=== TESTE DETECTOR HDD HITACHI ===")

    detector = criar_detector_hitachi()
    info = detector.obter_info_sistema()
    logger.info("Sistema: %s", info.get("sistema"))

    encontrado, caminho = detector.detectar_hdd_externo()
    if encontrado and caminho:
        logger.info("HDD detectado em: %s", caminho)
        cache = criar_cache_hdd()
        if cache.hdd_disponivel():
            cache.salvar_conhecimento("teste", {"dados": "exemplo"})
            logger.info("Cache OK")
    else:
        logger.info("Nenhum HDD detectado")

    logger.info("=== FIM DO TESTE ===")


