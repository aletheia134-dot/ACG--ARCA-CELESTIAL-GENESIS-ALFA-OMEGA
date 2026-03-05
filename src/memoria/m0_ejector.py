#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import hashlib
import hmac
import time
import tempfile
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, List
import threading
import logging
import zipfile

M0_SIG_ENV_KEY = "M0_SIGNATURE_KEY"
M0_SIG_ROTATION_ENV = "M0_SIGNATURE_ROTATION"  # comma separated keys (newest first)
M0_AUDIT_LOG = "data/m0_audit.log"

logger = logging.getLogger("M0Ejector")


class M0Ejector:
    def __init__(self, m0_path: str = "data/m0_identidade.json", signature_key: Optional[str] = None):
        self.m0_path = Path(m0_path)
        self._lock = threading.RLock()
        self.signature_key = signature_key or os.getenv(M0_SIG_ENV_KEY)
        rotation = os.getenv(M0_SIG_ROTATION_ENV)
        self.rotation_keys: List[str] = []
        if rotation:
            for k in rotation.split(","):
                kk = k.strip()
                if kk:
                    self.rotation_keys.append(kk)
        if self.signature_key and self.signature_key not in self.rotation_keys:
            self.rotation_keys.insert(0, self.signature_key)
        self._ensure_path()

    def _ensure_path(self) -> None:
        if not self.m0_path.parent.exists():
            self.m0_path.parent.mkdir(parents=True, exist_ok=True)

    def _hmac_sign(self, payload_bytes: bytes, key: Optional[str] = None) -> str:
        if not key and not self.rotation_keys:
            return hashlib.sha256(payload_bytes).hexdigest()
        use_key = key or (self.rotation_keys[0] if self.rotation_keys else "")
        return hmac.new(use_key.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    def _hmac_verify(self, payload_bytes: bytes, signature: str) -> bool:
        if not self.rotation_keys:
            calc = hashlib.sha256(payload_bytes).hexdigest()
            return calc == signature
        for key in self.rotation_keys:
            if hmac.new(key.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest() == signature:
                return True
        return False

    def _atomic_write(self, dest: Path, content_bytes: bytes) -> None:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(dest.parent))
        try:
            with os.fdopen(tmp_fd, "wb") as f:
                f.write(content_bytes)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, str(dest))
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def _next_version_path(self) -> Path:
        base = str(self.m0_path)
        n = 1
        while True:
            candidate = Path(f"{base}.v{n}")
            if not candidate.exists():
                return candidate
            n += 1

    def _log_audit(self, action: str, meta: Dict[str, Any]) -> None:
        try:
            line = json.dumps({"ts": int(time.time()), "action": action, "meta": meta}, ensure_ascii=False)
            Path(M0_AUDIT_LOG).parent.mkdir(parents=True, exist_ok=True)
            with open(M0_AUDIT_LOG, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            logger.exception("Falha ao gravar audit log M0")

    def inject(self, identidade_data: Dict[str, Any], autor: str = "operator", allow_overwrite: bool = False) -> Dict[str, Any]:
        with self._lock:
            payload = {
                "injetado_por": autor,
                "timestamp": int(time.time()),
                "conteudo": identidade_data
            }
            payload_bytes = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            signature = self._hmac_sign(payload_bytes)

            meta = {"autor": autor, "timestamp": int(time.time()), "signature": signature}
            try:
                if self.m0_path.exists() and not allow_overwrite:
                    ver_path = self._next_version_path()
                    ver_content = {"version_of": str(self.m0_path), "timestamp": int(time.time()), "autor": autor,
                                   "conteudo": identidade_data, "signature": signature}
                    self._atomic_write(ver_path, json.dumps(ver_content, ensure_ascii=False, indent=2).encode("utf-8"))
                    self._log_audit("inject_versioned", {"path": str(ver_path), **meta})
                    return {"status": "versioned", "path": str(ver_path), **meta}
                else:
                    content = {"timestamp": int(time.time()), "autor": autor, "conteudo": identidade_data, "signature": signature}
                    self._atomic_write(self.m0_path, json.dumps(content, ensure_ascii=False, indent=2).encode("utf-8"))
                    self._log_audit("inject_written", {"path": str(self.m0_path), **meta})
                    return {"status": "written", "path": str(self.m0_path), **meta}
            except Exception as e:
                logger.exception("Falha ao injetar M0: %s", e)
                self._log_audit("inject_error", {"error": str(e), **meta})
                return {"status": "error", "error": str(e)}

    def validate(self, path: Optional[str] = None) -> Dict[str, Any]:
        p = Path(path) if path else self.m0_path
        if not p.exists():
            return {"exists": False}
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            signature = data.get("signature")
            payload = json.dumps({k: v for k, v in data.items() if k != "signature"}, ensure_ascii=False, sort_keys=True).encode("utf-8")
            calc_matches = self._hmac_verify(payload, signature)
            return {"exists": True, "signature_match": bool(calc_matches), "signature": signature}
        except Exception as e:
            return {"exists": True, "error": str(e)}

    def eject_to(self, out_path: str) -> str:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            if not self.m0_path.exists():
                raise FileNotFoundError("M0 não encontrado")
            shutil.copy2(self.m0_path, out)
            self._log_audit("eject", {"out": str(out)})
            return str(out)

    def list_versions(self) -> List[str]:
        parent = self.m0_path.parent
        versions = []
        for p in parent.glob(self.m0_path.name + ".v*"):
            versions.append(str(p))
        return sorted(versions)

    def export_zip(self, out_zip_path: str, include_versions: bool = True) -> str:
        out = Path(out_zip_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
                if self.m0_path.exists():
                    zf.write(self.m0_path, arcname=self.m0_path.name)
                if include_versions:
                    for v in self.list_versions():
                        zf.write(v, arcname=Path(v).name)
            self._log_audit("export_zip", {"out": str(out), "include_versions": include_versions})
            return str(out)

    def set_signature_keys(self, keys: List[str]) -> None:
        with self._lock:
            clean = [k for k in keys if k]
            self.rotation_keys = clean
            self._log_audit("set_keys", {"count": len(clean)})

    def signature_info(self) -> Dict[str, Any]:
        with self._lock:
            return {"has_keys": bool(self.rotation_keys), "num_keys": len(self.rotation_keys)}

