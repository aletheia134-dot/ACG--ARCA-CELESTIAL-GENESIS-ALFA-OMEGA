#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

def _now_iso():
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"

def _atomic_write_json(path, obj):
    import tempfile, os, json
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(path))
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        raise

def limpar_cache(config):
    """Limpa todo o cache e as estatsticas.

    Implementao: remove arquivos de cache no diretório configurado e
    reseta o arquivo de estatsticas.
    """
    cache_dir = Path(getattr(config, "CACHE_DIR", "data/cache"))
    stats_file = cache_dir / "stats.json"
    removed = 0
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        for p in cache_dir.iterdir():
            if p.is_file() and not p.name.startswith(".keep"):
                try:
                    p.unlink()
                    removed += 1
                except Exception:
                    logger.debug("No foi possível remover cache %s", p, exc_info=True)
        try:
            _atomic_write_json(stats_file, {"cleared_at": _now_iso(), "removed_files": removed})
        except Exception:
            try:
                if stats_file.exists():
                    stats_file.unlink()
            except Exception:
                logger.debug("Falha ao resetar stats", exc_info=True)
        return {"ok": True, "removed_files": removed}
    except Exception as e:
        logger.exception("Erro limpando cache")
        return {"ok": False, "error": str(e)}

