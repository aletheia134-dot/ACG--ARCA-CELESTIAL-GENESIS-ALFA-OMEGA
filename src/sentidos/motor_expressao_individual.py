"""
src/camara/motor_expressao_individual.py — CORRIGIDO
Shim que carrega a implementação real de motor_avatar_individual.py (na raiz do projeto).
O shim anterior apontava para 'src.modules.motor_expressao_individual' que não existe.
"""
from __future__ import annotations
import importlib
import sys
import os
from pathlib import Path
from typing import Any, Optional

__all__ = ["MotorExpressaoIndividual"]

_real_mod: Optional[Any] = None

def _load_real():
    global _real_mod
    if _real_mod is not None:
        return _real_mod

    # Tenta 1: importar diretamente como módulo (se raiz estiver no sys.path)
    for nome in ("motor_avatar_individual", "src.encarnacao_e_interacao.motor_avatar_individual"):
        try:
            mod = importlib.import_module(nome)
            _real_mod = mod
            sys.modules.setdefault("src.modules.motor_expressao_individual", mod)
            sys.modules.setdefault("src.camara.motor_expressao_individual", mod)
            return mod
        except Exception:
            continue

    # Tenta 2: carregar pelo caminho físico (garante funcionar independente do sys.path)
    candidatos = [
        Path(__file__).parent.parent.parent / "motor_avatar_individual.py",
        Path(__file__).parent.parent / "encarnacao_e_interacao" / "motor_avatar_individual.py",
        Path(__file__).parent.parent / "camara" / "motor_avatar_individual.py",
    ]
    for caminho in candidatos:
        if caminho.exists():
            try:
                spec = importlib.util.spec_from_file_location("motor_avatar_individual", str(caminho))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                _real_mod = mod
                sys.modules["motor_avatar_individual"] = mod
                sys.modules.setdefault("src.modules.motor_expressao_individual", mod)
                return mod
            except Exception:
                continue

    raise ImportError(
        "Não foi possível carregar MotorExpressaoIndividual. "
        "Verifique motor_avatar_individual.py na raiz do projeto."
    )


def __getattr__(name: str):
    mod = _load_real()
    try:
        return getattr(mod, name)
    except AttributeError as e:
        raise AttributeError(f"módulo motor_expressao_individual não exporta '{name}'") from e


def __dir__():
    try:
        mod = _load_real()
        return sorted(set(list(globals().keys()) + [n for n in dir(mod) if not n.startswith("_")]))
    except Exception:
        return list(globals().keys())

