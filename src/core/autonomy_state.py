# -*- coding: utf-8 -*-
# src/core/autonomy_state.py - Persistncia simples em JSON para o sistema de autonomia.

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
import time
import os

from filelock import FileLock, Timeout

"""
AutonomyState - Persistncia simples em JSON para o sistema de autonomia.

Estrutura do JSON:
{
  "ais": {
    "EVA": {
       "next_index": 0,
       "last_ts": 1670000000.0,
       "desire_queue": [ {desire}, ... ],
       "pending_proposals": { "proposal_id": {...} }
    }, ...
  },
  "meta": { "version": 1, "updated_at": 1670000000.0 }
}
"""

DEFAULT_PATH = Path("data") / "autonomy_state.json"


class AutonomyState:
    def __init__(self, path: Optional[str] = None):
        self.path = Path(path) if path else DEFAULT_PATH
        if not self.path.parent.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = {"ais": {}, "meta": {"version": 1, "updated_at": time.time()}}
        self._file_lock_path = self.path.with_suffix(self.path.suffix + ".lock") if self.path.suffix else Path(str(self.path) + ".lock")
        self.load()

    def load(self) -> None:
        with self._lock:
            try:
                if self.path.exists():
                    with self.path.open("r", encoding="utf-8") as fh:
                        self._data = json.load(fh)
                else:
                    self._save_locked()
            except Exception:
                # reinit minimal structure if corrupt
                self._data = {"ais": {}, "meta": {"version": 1, "updated_at": time.time()}}
                try:
                    self._save_locked()
                except Exception:
                    # if even saving fails, log via print (no logger here)
                    print("AutonomyState: erro ação salvar estado durante load fallback", flush=True)

    def save(self) -> None:
        with self._lock:
            self._save_locked()

    def _safe_replace(self, tmp_path: Path, target_path: Path, retries: int = 6, base_delay: float = 0.05) -> None:
        """
        Tenta substituir tmp_path -> target_path usando FileLock para evitar PermissionError
        em ambientes Windows onde outro handle pode manter o ficheiro aberto.
        """
        lock = FileLock(str(self._file_lock_path))
        attempt = 0
        while True:
            try:
                # Adquire lock (com timeout curto)
                with lock.acquire(timeout=2):
                    # Use os.replace para operação atmica
                    os.replace(str(tmp_path), str(target_path))
                    return
            except Timeout:
                # No conseguiu adquirir lock dentro do timeout - tentar novamente com backoff
                attempt += 1
                if attempt > retries:
                    # ltima tentativa direta sem lock para propagar a exceo se falhar
                    try:
                        os.replace(str(tmp_path), str(target_path))
                        return
                    except Exception as e:
                        raise
                time.sleep(base_delay * (1 + attempt * 0.5))
            except PermissionError:
                attempt += 1
                if attempt > retries:
                    # re-raise aps tentativas
                    raise
                time.sleep(base_delay * (1 + attempt * 0.5))
            except Exception:
                # para outras OSErrors, tentar uma ltima vez e propagar se falhar
                try:
                    os.replace(str(tmp_path), str(target_path))
                    return
                except Exception:
                    raise

    def _save_locked(self) -> None:
        """
        Grava self._data em arquivo JSON de forma atmica e robusta.
        Usa arquivo temporrio + replace, protegido por lock (filelock) com retries.
        """
        self._data.setdefault("ais", {})
        self._data.setdefault("meta", {})["updated_at"] = time.time()
        tmp = self.path.with_suffix(self.path.suffix + ".tmp") if self.path.suffix else Path(str(self.path) + ".tmp")

        # Escrever tmp em modo texto (garantir flush/close)
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(self._data, fh, ensure_ascii=False, indent=2)

        # Substituir o arquivo alvo de forma segura (com file lock e retries).
        # Se houver falha no recupervel, a exceo ser propagada para o chamador.
        self._safe_replace(tmp, self.path)

    # per-AI helpers
    def _ensure_ai(self, ai: str) -> None:
        self._data.setdefault("ais", {})
        if ai not in self._data["ais"]:
            self._data["ais"][ai] = {
                "next_index": 0,
                "last_ts": 0.0,
                "desire_queue": [],
                "pending_proposals": {}
            }

    def get_next_index(self, ai: str) -> int:
        with self._lock:
            self._ensure_ai(ai)
            return int(self._data["ais"][ai].get("next_index", 0))

    def set_next_index(self, ai: str, idx: int) -> None:
        with self._lock:
            self._ensure_ai(ai)
            self._data["ais"][ai]["next_index"] = int(idx)
            self._data["ais"][ai]["last_ts"] = time.time()
            self._save_locked()

    def push_desire(self, ai: str, desire: Dict[str, Any]) -> None:
        with self._lock:
            self._ensure_ai(ai)
            self._data["ais"][ai]["desire_queue"].append(desire)
            self._data["ais"][ai]["last_ts"] = time.time()
            self._save_locked()

    def add_desire(self, ai: str, desire: dict) -> None:
        """Alias para push_desire para compatibilidade com desires.py."""
        self.push_desire(ai, desire)

    def pop_desire(self, ai: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            self._ensure_ai(ai)
            q: List = self._data["ais"][ai].get("desire_queue", [])
            if not q:
                return None
            item = q.pop(0)
            self._data["ais"][ai]["last_ts"] = time.time()
            self._save_locked()
            return item

    def peek_desires(self, ai: str) -> List[Dict[str, Any]]:
        with self._lock:
            self._ensure_ai(ai)
            return list(self._data["ais"][ai].get("desire_queue", []))

    # proposals
    def add_proposal(self, ai_from: str, ai_to: str, proposal_id: str, proposal: Dict[str, Any]) -> None:
        with self._lock:
            self._ensure_ai(ai_from)
            self._ensure_ai(ai_to)
            # store under ai_to.pending_proposals[proposal_id]
            self._data["ais"][ai_to].setdefault("pending_proposals", {})[proposal_id] = {
                "from": ai_from,
                "proposal": proposal,
                "created_at": time.time(),
                "status": "pending"
            }
            self._save_locked()

    def resolve_proposal(self, ai_to: str, proposal_id: str, decision: str, reason: Optional[str] = None) -> None:
        with self._lock:
            self._ensure_ai(ai_to)
            props = self._data["ais"][ai_to].setdefault("pending_proposals", {})
            if proposal_id in props:
                props[proposal_id]["status"] = decision
                props[proposal_id]["decision_reason"] = reason
                props[proposal_id]["resolved_at"] = time.time()
                self._save_locked()

    def get_pending_proposals(self, ai: str) -> Dict[str, Any]:
        with self._lock:
            self._ensure_ai(ai)
            return dict(self._data["ais"][ai].get("pending_proposals", {}))

    # debugging / export
    def export(self) -> Dict[str, Any]:
        with self._lock:
            # return a deep copy of the state to avoid accidental external mutation
            return json.loads(json.dumps(self._data))

