# -*- coding: utf-8 -*-
"""
DetectorHardware (enduricido)

Detecta hardware real (HDDs, USBs) e fornece utilitários factuais do sistema.Principais endurecimentos:
 - Consolida e remove duplicações
 - Plataforma-aware (WMIC apenas no Windows; lsblk/psutil em Linux)
 - Saída de subprocess encapsulada e parse robusto (/format:csv para WMIC)
 - Não usa input() no __main__; pode executar teste de velocidade via env RUN_HDD_SPEED_TEST=1
 - Teste de velocidade usa tempfile e respeita espaço/erros
 - Logs e tratamento de exceções detalhados
"""
from __future__ import annotations


import csv
import json
import logging
import platform
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def _is_windows() -> bool:
    return platform.system().lower().startswith("win")


def _run_cmd(cmd: List[str], timeout: int = 10) -> Tuple[int, str, str]:
    """
    Executa um comando seguro, retorna (returncode, stdout, stderr).
    Nunca lança; trata FileNotFoundError e Timeout.
    """
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
        logger.exception("Erro executando comando %s: %s", cmd, e)
        return 1, "", str(e)


@dataclass
class HDDCheckResult:
    found: bool
    mount_path: Optional[Path]
    model: Optional[str]
    size_bytes: Optional[int]


class DetectorHardware:
    """
    Detector de hardware factualmente orientado.Principais métodos públicos:
     - detectar_hdd_externo(modelo_esperado=None, tamanho_esperado_bytes=None) -> (bool, Optional[Path])
     - detectar_dispositivos_usb() -> List[Dict[str, Any]]
     - obter_info_sistema() -> Dict[str, Any]
     - verificar_espaco_hdd(caminho: Path) -> Optional[Dict[str, Any]]
     - testar_velocidade_hdd(caminho: Path, tamanho_mb: int = 10) -> Optional[Dict[str, Any]]
    """

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

    # --------------------
    # HDD detection
    # --------------------
    def detectar_hdd_externo(
        self,
        modelo_esperado: Optional[str] = None,
        tamanho_esperado_bytes: Optional[int] = None,
    ) -> Tuple[bool, Optional[Path]]:
        """
        Detecta um HDD externo real.Retorna (encontrado, caminho_de_montagem).
        Tenta WMIC (Windows) ou lsblk/psutil (Linux). Em falta, tenta heurística em /media, /mnt.
        """
        try:
            if _is_windows():
                res = self._detectar_hdd_windows(modelo_esperado, tamanho_esperado_bytes)
            else:
                res = self._detectar_hdd_linux(modelo_esperado, tamanho_esperado_bytes)

            if res and res.found:
                return True, res.mount_path
            # fallback heurístico: procurar em /media, /mnt, /run/media
            for base in [Path("/media"), Path("/mnt"), Path("/run/media")]:
                if base.exists():
                    for p in base.rglob("*"):
                        if p.is_mount():
                            logger.debug("Fallback: encontrado mountpoint heurístico %s", p)
                            return True, p
            return False, None
        except Exception as e:
            logger.exception("Erro ao detectar HDD externo: %s", e)
            return False, None

    def _detectar_hdd_windows(
        self, modelo_esperado: Optional[str], tamanho_esperado_bytes: Optional[int]
    ) -> Optional[HDDCheckResult]:
        """
        Tenta WMIC com /format:csv para saída mais fácil de parse.
        """
        cmd = ["wmic", "diskdrive", "get", "Caption,Size,DeviceID", "/format:csv"]
        rc, out, err = _run_cmd(cmd, timeout=8)
        if rc != 0 or not out:
            logger.debug("WMIC não retornou dados úteis: rc=%s err=%s", rc, err.strip())
            return None

        try:
            # WMIC /format:csv returns CSV with node header; parse with csv.DictReader
            lines = [l for l in out.splitlines() if l.strip()]
            reader = csv.DictReader(lines)
            for row in reader:
                model = (row.get("Caption") or row.get("Caption ").strip()) if row.get("Caption") else row.get("Caption")
                size_str = row.get("Size") or row.get("Size ")
                device_id = row.get("DeviceID") or row.get("DeviceID ")
                try:
                    size = int(size_str) if size_str and size_str.isdigit() else 0
                except Exception:
                    size = 0

                matches = True
                if modelo_esperado and (not model or modelo_esperado not in model):
                    matches = False
                if tamanho_esperado_bytes and size != tamanho_esperado_bytes:
                    matches = False

                if matches:
                    # Heurística: try common drive letters
                    for drive_letter in ["D:\\", "E:\\", "F:\\", "G:\\", "H:\\"]:
                        p = Path(drive_letter)
                        if p.exists():
                            logger.info("HDD detectado (Windows): model=%s mount=%s", model, p)
                            return HDDCheckResult(True, p, model, size)
            return HDDCheckResult(False, None, None, None)
        except Exception as e:
            logger.exception("Erro parseando saída WMIC: %s", e)
            return None

    def _detectar_hdd_linux(
        self, modelo_esperado: Optional[str], tamanho_esperado_bytes: Optional[int]
    ) -> Optional[HDDCheckResult]:
        """
        Usa lsblk -J -b para obter JSON de blockdevices
        """
        cmd = ["lsblk", "-J", "-b", "-o", "NAME,MODEL,SIZE,MOUNTPOINT,TYPE"]
        rc, out, err = _run_cmd(cmd, timeout=8)
        if rc != 0 or not out:
            logger.debug("lsblk não retornou dados úteis: rc=%s err=%s", rc, err.strip())
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
                    # prefer mountpoint if present
                    if mountpoint:
                        p = Path(mountpoint)
                        if p.exists():
                            logger.info("HDD detectado (Linux): model=%s mount=%s", model, p)
                            return HDDCheckResult(True, p, model, size)
                    # else inspect children partitions
                    for child in dev.get("children", []) or []:
                        mp = child.get("mountpoint")
                        if mp:
                            p = Path(mp)
                            if p.exists():
                                logger.info("HDD detectado via partição: %s -> %s", model, p)
                                return HDDCheckResult(True, p, model, size)
            return HDDCheckResult(False, None, None, None)
        except Exception as e:
            logger.exception("Erro parseando saída lsblk: %s", e)
            return None

    # --------------------
    # USB detection
    # --------------------
    def detectar_dispositivos_usb(self) -> List[Dict[str, Any]]:
        dispositivos: List[Dict[str, Any]] = []
        try:
            if _is_windows():
                dispositivos = self._detectar_usb_windows()
            else:
                dispositivos = self._detectar_usb_linux()
        except Exception:
            logger.exception("Erro detectando dispositivos USB")
        logger.info("Dispositivos USB detectados: %d", len(dispositivos))
        return dispositivos

    def _detectar_usb_windows(self) -> List[Dict[str, Any]]:
        cmd = ["wmic", "logicaldisk", "where", "DriveType=2", "get", "DeviceID,VolumeName,Size", "/format:csv"]
        rc, out, err = _run_cmd(cmd, timeout=6)
        dispositivos = []
        if rc != 0 or not out:
            logger.debug("WMIC logicaldisk não retornou dados úteis (Windows USB).")
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
            logger.exception("Erro parseando saída WMIC logicaldisk")
            return dispositivos

    def _detectar_usb_linux(self) -> List[Dict[str, Any]]:
        cmd = ["lsblk", "-J", "-o", "NAME,MOUNTPOINT,SIZE,TYPE,ROTA,VENDOR,MODEL"]
        rc, out, err = _run_cmd(cmd, timeout=6)
        dispositivos: List[Dict[str, Any]] = []
        if rc != 0 or not out:
            logger.debug("lsblk não retornou dados úteis (Linux USB).")
            return dispositivos
        try:
            data = json.loads(out)
            for dev in data.get("blockdevices", []):
                # heurística: removable devices often have ROTA=1 but better: check vendor/model for USB
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
            logger.exception("Erro parseando saída lsblk para USB")
            return dispositivos

    # --------------------
    # System info
    # --------------------
    def obter_info_sistema(self) -> Dict[str, Any]:
        info = dict(self.info_basica)
        try:
            import socket
            # CPU/memory/disk via psutil if available
            try:
                import psutil  # type: ignore
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
                logger.debug("psutil não disponível ou falhou; informações reduzidas")

            # network
            try:
                hostname = socket.gethostname()
                info["hostname"] = hostname
                # get local IP (non-blocking)
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

    # --------------------
    # Disk utilities
    # --------------------
    def verificar_espaco_hdd(self, caminho: Path) -> Optional[Dict[str, Any]]:
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
            logger.exception("Erro ao verificar espaço em %s", caminho)
            return None

    def testar_velocidade_hdd(self, caminho: Path, tamanho_mb: int = 10) -> Optional[Dict[str, Any]]:
        """
        Testa velocidade de escrita/leitura no HDD de forma segura:
         - cria arquivo temporário no mount point
         - escreve blocos incrementais (não todo em memória)
         - remove o arquivo ao final
        """
        try:
            if not caminho.exists() or not caminho.is_dir():
                logger.error("Caminho inválido para teste de velocidade: %s", caminho)
                return None

            # garantir espaço suficiente (heurística mínima)
            try:
                usage = shutil.disk_usage(str(caminho))
                if usage.free < (tamanho_mb * 1024 * 1024 * 2):
                    logger.warning("Espaço livre muito baixo para teste de %dMB em %s", tamanho_mb, caminho)
                    return None
            except Exception:
                logger.debug("Não foi possível determinar espaço livre (continuando com teste)")

            # cria arquivo temporário no diretório alvo
            tmp_file = Path(tempfile.NamedTemporaryFile(dir=str(caminho), delete=False).name)
            bytes_to_write = 1024 * 1024  # 1MB chunks
            total_mb = max(1, int(tamanho_mb))
            # escrita em blocos
            start = time.time()
            with open(tmp_file, "wb") as f:
                for _ in range(total_mb):
                    f.write(b"\0" * bytes_to_write)
                    f.flush()
            write_time = time.time() - start

            # leitura
            start = time.time()
            with open(tmp_file, "rb") as f:
                # ler em blocos para não carregar tudo na memória
                while f.read(bytes_to_write):
                    pass
            read_time = time.time() - start

            # remover
            try:
                tmp_file.unlink()
            except Exception:
                logger.debug("Falha ao remover arquivo temporário %s", tmp_file)

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
            logger.exception("Erro no teste de velocidade em %s", caminho)
            return None


# --------------------
# Fácil criação
# --------------------
def criar_detector_hardware_padrao() -> DetectorHardware:
    return DetectorHardware()


# --------------------
# Exemplo de uso (não interativo)
# --------------------
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("DetectorHardwareTest")

    logger.info("=== TESTE DETECTOR HARDWARE (não interativo) ===")
    detector = criar_detector_hardware_padrao()

    info = detector.obter_info_sistema()
    logger.info("Info sistema: cpu=%s, mem_total_gb=%s", info.get("cpu_usage_percent"), info.get("mem_total_gb"))

    encontrado, caminho = detector.detectar_hdd_externo()
    if encontrado and caminho:
        logger.info("HDD externo detectado em: %s", caminho)
        espaco = detector.verificar_espaco_hdd(caminho)
        logger.info("Espaço HDD: %s", espaco)
        # Teste de velocidade opcional (controlado por variável de ambiente)
        if os.environ.get("RUN_HDD_SPEED_TEST", "0") == "1":
            logger.info("Iniciando teste de velocidade (opcional)...")
            vel = detector.testar_velocidade_hdd(caminho, tamanho_mb=10)
            logger.info("Resultado teste velocidade: %s", vel)
    else:
        logger.info("Nenhum HDD externo detectado (fallback pode ter encontrado mounts heurísticos).")

    usbs = detector.detectar_dispositivos_usb()
    logger.info("USBs detectados: %d", len(usbs))
    for u in usbs:
        logger.info("  %s", u)
    logger.info("=== FIM DO TESTE ===")


