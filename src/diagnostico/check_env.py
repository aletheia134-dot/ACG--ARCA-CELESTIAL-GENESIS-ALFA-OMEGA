#!/usr/bin/env python3
# tools/check_env.py
# Verificao de dependncias essenciais (no exaustiva).
# Melhorias: verses, comandos externos, CLI, grupos, relatrio.import importlib
import json
import sys
import subprocess
from typing import Dict, Any, List
import argparse

# Grupos de pacotes
ESSENTIAL_PACKAGES = [
    "httpx", "chromadb", "playwright", "websockets"
]
OPTIONAL_PACKAGES = [
    "llama_cpp", "speech_recognition", "win32com", "docx", "pyaudio"
]

# Comandos externos para checar
EXTERNAL_COMMANDS = [
    "ffmpeg", "pandoc", "git"
]

def check_package(pkg: str) -> Dict[str, Any]:
    """Verifica pacote: import e verso."""
    result = {"status": "unknown", "version": None, "error": None}
    try:
        mod = importlib.import_module(pkg)
        result["status"] = "ok"
        try:
            # Tenta obter verso
            from importlib.metadata import version  # Python 3.8+
            result["version"] = version(pkg)
        except Exception:
            result["version"] = "unknown"
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"{e.__class__.__name__}: {str(e)}"
    return result

def check_command(cmd: str) -> Dict[str, Any]:
    """Verifica comando externo."""
    result = {"status": "unknown", "version": None, "error": None}
    try:
        proc = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            result["status"] = "ok"
            # Extrai verso da primeira linha
            lines = proc.stdout.strip().split("\n")
            if lines:
                result["version"] = lines[0]
        else:
            result["status"] = "error"
            result["error"] = proc.stderr.strip() or "return code != 0"
    except FileNotFoundError:
        result["status"] = "error"
        result["error"] = "command not found"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result

def generate_report(results: Dict[str, Any]) -> Dict[str, Any]:
    """Gera relatrio resumido."""
    total = 0
    ok = 0
    for category in ["packages", "commands"]:
        for item in results.get(category, {}).values():
            total += 1
            if item.get("status") == "ok":
                ok += 1
    return {"total_checked": total, "ok": ok, "errors": total - ok}

def main():
    parser = argparse.ArgumentParser(description="Verifica dependncias essenciais.")
    parser.add_argument("--packages", nargs="*", help="Pacotes extras para checar")
    parser.add_argument("--commands", nargs="*", help="Comandos extras para checar")
    parser.add_argument("--output", type=argparse.FileType("w"), default=sys.stdout, help="Arquivo de sada")
    parser.add_argument("--no-groups", action="store_true", help="No usar grupos (checar todos)")

    args = parser.parse_args()

    packages = ESSENTIAL_PACKAGES + OPTIONAL_PACKAGES if not args.no_groups else []
    if args.packages:
        packages.extend(args.packages)

    commands = EXTERNAL_COMMANDS[:]
    if args.commands:
        commands.extend(args.commands)

    results = {"packages": {}, "commands": {}}

    for pkg in packages:
        results["packages"][pkg] = check_package(pkg)

    for cmd in commands:
        results["commands"][cmd] = check_command(cmd)

    report = generate_report(results)
    results["report"] = report

    json.dump(results, args.output, indent=2, ensure_ascii=False)
    if args.output != sys.stdout:
        print(f"Resultado salvo em {args.output.name}")

if __name__ == "__main__":
    main()


