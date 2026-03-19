# -*- coding: utf-8 -*-
from __future__ import annotations
"""
CACHE HDD - Módulo endurecido para armazenamento no HDD externo

Principais endurecimentos:
 - Import defensivo de psutil (deteco opcional)
 - Locks (thread-safe) para operações de I/O
 - Escrita atmica (arquivo.tmp -> os.replace)
 - Timestamp padrão em ISO UTC
 - Backup/quarantine para arquivos corrompidos ou expirados (no apaga imediatamente)
 - Clculo de tamanho em bytes (len(json_bytes))
 - Sanitizao robusta de nomes de arquivo/tpico
 - Métodos pblicos para configurar o path do HDD e forar limpeza
"""

import json
import uuid
import os
import shutil
import tempfile
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import threading

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Try optional dependency psutil for better drive detection
try:
    import psutil  # type: ignore
    _PSUTIL_AVAILABLE = True
except:
    logging.getLogger(__name__).warning("[AVISO] psutil no disponível")
    psutil = None  # type: ignore
    _PSUTIL_AVAILABLE = False


def _now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _safe_filename(name: str, max_len: int = 50) -> str:
    # Keep only alnum, space, underscore and hyphen. Replace spaces with underscore.
    if not name:
        name = "conhecimento"
    cleaned = "".join(c if (c.isalnum() or c in " _-") else "_" for c in name).strip()
    cleaned = cleaned.replace(" ", "_")
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len]
    if not cleaned:
        cleaned = "conhecimento"
    return cleaned


class CacheHDD:
    """
    Gerencia cache no HDD externo (arquivos JSON).

    Uso principal:
        cache = CacheHDD(hdd_base_path=Path("D:/"), cache_dir_name="Arca_Conhecimento_Cache")
        file_id = cache.salvar_conhecimento("topico", dados, metadata={...})
    """

    def __init__(
        self,
        hdd_base_path: Optional[Path] = None,
        cache_dir_name: str = "Arca_Cache",
        quarantine_dir_name: str = "Arca_Cache_Quarantine",
        max_file_size_bytes: int = 10 * 1024 * 1024,  # 10MB default
    ):
        self._lock = threading.RLock()
        self.hdd_path: Optional[Path] = None
        self.cache_dir: Optional[Path] = None
        self.quarantine_dir: Optional[Path] = None
        self.cache_dir_name = cache_dir_name
        self.quarantine_dir_name = quarantine_dir_name
        self._max_file_size_bytes = int(max_file_size_bytes)

        # Try to set base path (can be None -> detection attempt)
        if hdd_base_path:
            self.set_hdd_base_path(hdd_base_path)
        else:
            detected = self._detectar_hdd_automatico()
            if detected:
                self.set_hdd_base_path(detected)
            else:
                logger.warning("Nenhum HDD detectado automaticamente. Cache permanecer desativado at set_hdd_base_path ser chamado.")

    # -------------------------
    # Configuration / detection
    # -------------------------
    def set_hdd_base_path(self, path: Path) -> None:
        """
        Define explicitamente o caminho base do HDD. Cria diretórios de cache e quarantine se possível.
        """
        with self._lock:
            try:
                p = Path(path)
                if not p.exists() or not p.is_dir():
                    raise ValueError(f"Caminho invlido ou inacessvel: {p}")
                self.hdd_path = p.resolve()
                self.cache_dir = self.hdd_path / self.cache_dir_name
                self.quarantine_dir = self.hdd_path / self.quarantine_dir_name
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                self.quarantine_dir.mkdir(parents=True, exist_ok=True)
                logger.info("Cache HDD configurado em: %s", self.cache_dir)
            except Exception as e:
                self.hdd_path = None
                self.cache_dir = None
                self.quarantine_dir = None
                logger.exception("Falha ao configurar hdd_base_path: %s", e)
                raise

    def _detectar_hdd_automatico(self) -> Optional[Path]:
        """
        Heurstica segura para detectar um HDD externo / drive montado. Retorna Path ou None.
        """
        try:
            if _PSUTIL_AVAILABLE and psutil is not None:
                for part in psutil.disk_partitions(all=False):
                    try:
                        mount = Path(part.mountpoint)
                        # Skip typical system mounts (root on unix, C: on windows)
                        if mount == Path("/") or str(mount).startswith("/boot") or (hasattr(mount, "drive") and getattr(mount, "drive", "").upper().startswith("C:")):
                            continue
                        usage = psutil.disk_usage(str(mount))
                        if usage.total and usage.total > 100 * 1024 * 1024:  # >100MB
                            logger.debug("Deteco automtica de drive: %s", mount)
                            return mount
                    except Exception:
                        continue

            # Fallback: check common paths (Windows letters and common Linux mounts)
            common = [Path("D:/"), Path("E:/"), Path("F:/"), Path("/media/"), Path("/mnt/")]
            for p in common:
                if p.exists() and p.is_dir():
                    try:
                        # if path is a directory with contents or has disk usage
                        if _PSUTIL_AVAILABLE and psutil is not None:
                            usage = psutil.disk_usage(str(p))
                            if usage.total and usage.total > 50 * 1024 * 1024:
                                logger.debug("Deteco por caminho comum: %s", p)
                                return p
                        else:
                            # if non-empty directory assume usable
                            if any(p.iterdir()):
                                logger.debug("Deteco por caminho comum (sem psutil): %s", p)
                                return p
                    except Exception:
                        continue
        except Exception as e:
            logger.exception("Erro durante deteco automtica do HDD: %s", e)

        return None

    # -------------------------
    # Availability
    # -------------------------
    def hdd_disponivel(self) -> bool:
        with self._lock:
            return bool(self.cache_dir and self.cache_dir.exists())

    # -------------------------
    # Core operations
    # -------------------------
    def salvar_conhecimento(
        self,
        topico: str,
        dados: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        expiracao_dias: int = 30,
    ) -> Optional[str]:
        """
        Salva conhecimento no cache HDD de forma atmica e segura. Retorna file_id (string) ou None em caso de falha.
        """
        with self._lock:
            if not self.hdd_disponivel():
                logger.warning("HDD indisponível. salvar_conhecimento abortado.")
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

                # Serialize to bytes first to check size
                json_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                if len(json_bytes) > self._max_file_size_bytes:
                    logger.error("Tamanho do payload excede limite (%d bytes). Abortando.", self._max_file_size_bytes)
                    return None

                # atomic write using tempfile in same filesystem
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

                logger.debug("Conhecimento salvo com ID: %s", file_id)
                return file_id
            except Exception:
                logger.exception("Erro ao salvar conhecimento no HDD.")
                return None

    def carregar_conhecimento(self, topico: Optional[str] = None, file_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Carrega conhecimento por file_id ou por tpico (mais recente).
        """
        with self._lock:
            if not self.hdd_disponivel():
                return None
            try:
                if file_id:
                    for fp in self.cache_dir.glob("*.json"):
                        if file_id in fp.stem:
                            return self._carregar_arquivo(fp)
                    return None

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

                return None
            except Exception:
                logger.exception("Erro ao carregar conhecimento (carregar_conhecimento).")
                return None

    def _carregar_arquivo(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Carrega e válida um arquivo de cache; move corrompidos/expirados para quarantine."""
        try:
            with open(file_path, "rb") as f:
                raw = f.read()
            try:
                conhecimento = json.loads(raw.decode("utf-8"))
            except Exception as e:
                # move to corrupt backup instead of deleting
                ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
                corrupt_name = f"{file_path.stem}.corrupt_{ts}{file_path.suffix}"
                corrupt_dest = (self.quarantine_dir or self.cache_dir) / corrupt_name
                try:
                    shutil.move(str(file_path), str(corrupt_dest))
                    logger.warning("Arquivo corrompido movido para quarantine: %s", corrupt_dest)
                except Exception:
                    logger.exception("Falha ao mover arquivo corrompido (tentando excluir): %s", file_path)
                    try:
                        file_path.unlink()
                    except Exception:
                        logger.debug("No foi possível remover arquivo corrompido.")
                return None

            # validate expiration
            expiracao_str = conhecimento.get("expiracao")
            if expiracao_str:
                try:
                    # handle trailing Z
                    expiracao_dt = datetime.datetime.fromisoformat(expiracao_str.replace("Z", ""))
                    if expiracao_dt < datetime.datetime.utcnow():
                        # move to quarantine (expired)
                        ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
                        expired_name = f"{file_path.stem}.expired_{ts}{file_path.suffix}"
                        expired_dest = (self.quarantine_dir or self.cache_dir) / expired_name
                        try:
                            shutil.move(str(file_path), str(expired_dest))
                            logger.debug("Arquivo expirado movido para quarantine: %s", expired_dest)
                        except Exception:
                            try:
                                file_path.unlink()
                            except Exception:
                                logger.debug("Falha ao remover arquivo expirado.")
                        return None
                except Exception:
                    logger.debug("Formato de expiracao invlido (ignorando).")

            return conhecimento
        except Exception:
            logger.exception("Erro ao ler arquivo de cache: %s", file_path)
            return None

    # -------------------------
    # Busca / listagem / remoo
    # -------------------------
    def buscar_conhecimento(self, query: str, limite: int = 10) -> List[Dict[str, Any]]:
        if not self.hdd_disponivel():
            return []
        resultados: List[Dict[str, Any]] = []
        with self._lock:
            try:
                for fp in sorted(self.cache_dir.glob("*.json"), key=os.path.getmtime, reverse=True):
                    if len(resultados) >= limite:
                        break
                    k = self._carregar_arquivo(fp)
                    if not k:
                        continue
                    topico = str(k.get("topico", "")).lower()
                    if query.lower() in topico:
                        resultados.append(k)
                return resultados
            except Exception:
                logger.exception("Erro na busca de conhecimento.")
                return []

    def listar_conhecimentos(self, limit: int = 50, ordenar_por: str = "timestamp") -> List[Dict[str, Any]]:
        if not self.hdd_disponivel():
            return []
        out: List[Dict[str, Any]] = []
        with self._lock:
            try:
                for fp in self.cache_dir.glob("*.json"):
                    k = self._carregar_arquivo(fp)
                    if k:
                        out.append(k)
                # safe sort
                try:
                    reverse = ordenar_por == "timestamp"
                    out.sort(key=lambda x: x.get(ordenar_por, ""), reverse=reverse)
                except Exception:
                    logger.debug("Ordenao por campo '%s' falhou; retornando sem ordenar.", ordenar_por)
                return out[:limit]
            except Exception:
                logger.exception("Erro ao listar conhecimentos.")
                return []

    def remover_conhecimento(self, topico: Optional[str] = None, file_id: Optional[str] = None) -> int:
        if not self.hdd_disponivel():
            return 0
        removed = 0
        with self._lock:
            try:
                for fp in list(self.cache_dir.glob("*.json")):
                    try:
                        k = self._carregar_arquivo(fp)
                        if not k:
                            continue
                        do_remove = False
                        if file_id and k.get("id") == file_id:
                            do_remove = True
                        elif topico and k.get("topico") == topico:
                            do_remove = True
                        if do_remove:
                            # move to quarantine before final deletion
                            ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
                            dest = (self.quarantine_dir or self.cache_dir) / f"{fp.stem}.removed_{ts}{fp.suffix}"
                            try:
                                shutil.move(str(fp), str(dest))
                            except Exception:
                                try:
                                    fp.unlink()
                                except Exception:
                                    logger.debug("Falha ao remover arquivo: %s", fp)
                            removed += 1
                    except Exception:
                        continue
                logger.info("Removidos %d conhecimentos (moved to quarantine)", removed)
                return removed
            except Exception:
                logger.exception("Erro ao remover conhecimentos.")
                return removed

    def limpar_cache_expirado(self) -> int:
        """Percorre arquivos e move expirados/corrompidos para quarantine; retorna quantidade de movidos."""
        if not self.hdd_disponivel():
            return 0
        count = 0
        with self._lock:
            try:
                for fp in list(self.cache_dir.glob("*.json")):
                    k = self._carregar_arquivo(fp)  # _carregar_arquivo already moves expired/corrupt
                    if k is None:
                        count += 1
                logger.info("Limpeza expirados/corrompidos: %d itens movidos", count)
                return count
            except Exception:
                logger.exception("Erro ao limpar cache expirado.")
                return count

    # -------------------------
    # Estatsticas / utilitrios
    # -------------------------
    def obter_estatisticas(self) -> Dict[str, Any]:
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
                        k = self._carregar_arquivo(fp)
                        topics.add(k.get("topico", "desconhecido") if k else "corrompido")
                    except Exception:
                        topics.add("corrompido")
                free_gb = self._obter_espaco_livre()
                return {
                    "hdd_disponivel": True,
                    "total_arquivos": total_files,
                    "total_tamanho_mb": round(total_bytes / (1024 * 1024), 2),
                    "topicos_unicos": len(topics),
                    "caminho_cache": str(self.cache_dir),
                    "espaco_livre_gb": free_gb,
                }
            except Exception:
                logger.exception("Erro obtendo estatsticas.")
                return {"hdd_disponivel": True, "erro": "falha_ao_coletar_stats"}

    def _obter_espaco_livre(self) -> Optional[float]:
        try:
            if self.hdd_path and self.hdd_path.exists():
                usage = shutil.disk_usage(str(self.hdd_path))
                return round(usage.free / (1024 ** 3), 2)
        except Exception:
            logger.debug("Falha obtendo espao livre.")
        return None

    def exportar_cache(self, destino: Path) -> bool:
        if not self.hdd_disponivel():
            return False
        with self._lock:
            try:
                destino.mkdir(parents=True, exist_ok=True)
                for fp in self.cache_dir.glob("*.json"):
                    shutil.copy2(fp, destino / fp.name)
                logger.info("Cache exportado para %s", destino)
                return True
            except Exception:
                logger.exception("Erro ao exportar cache.")
                return False

    def importar_cache(self, origem: Path) -> int:
        if not self.hdd_disponivel():
            return 0
        count = 0
        with self._lock:
            try:
                for fp in origem.glob("*.json"):
                    try:
                        shutil.copy2(fp, self.cache_dir / fp.name)
                        count += 1
                    except Exception:
                        logger.debug("Falha ao importar arquivo: %s", fp)
                logger.info("Importados %d arquivos", count)
                return count
            except Exception:
                logger.exception("Erro ao importar cache.")
                return count


# ===== FUNO DE FCIL USO =====
def criar_cache_hdd_padrao() -> CacheHDD:
    return CacheHDD(hdd_base_path=None, cache_dir_name="Arca_Conhecimento_Cache")


# ===== EXEMPLO DE USO SEGURO =====
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    print("=== TESTE CACHE HDD (ENDURECIDO) ===")

    cache = criar_cache_hdd_padrao()

    if cache.hdd_disponivel():
        print(" HDD disponível em:", cache.cache_dir)
        kid = cache.salvar_conhecimento(
            topico="inteligencia_artificial",
            dados={"definicao": "IA ... (demo)"},
            metadata={"autor": "Sistema", "confianca": 0.9},
            expiracao_dias=7
        )
        print("Salvo ID:", kid)
        k = cache.carregar_conhecimento(topico="inteligencia_artificial")
        print("Carregado:", bool(k))
        print("Estatsticas:", cache.obter_estatisticas())
        print("Limpando expirados:", cache.limpar_cache_expirado())
    else:
        print(" HDD no disponível. Configure manualmente com set_hdd_base_path(Path('D:/'))")
    print("=== TESTE CONCLUDO ===")
