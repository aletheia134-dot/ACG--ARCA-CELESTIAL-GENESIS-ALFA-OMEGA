from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional
import ast
import re
import time
import hashlib
import json
import shutil
import tempfile
import subprocess
from pathlib import Path
import logging

logger = logging.getLogger("BotAnalisadorSeguranca")
logger.addHandler(logging.NullHandler())

# Lista de nomes/símbolos potencialmente perigosos (alto nível)
AST_BLACKLIST_NAMES = {
    "exec", "eval", "compile", "__import__", "open", "os.system", "subprocess.Popen",
    "subprocess.call", "socket", "requests", "urllib", "shutil.rmtree", "pickle", "ctypes",
    "ffi", "system", "popen", "fork", "thread", "multiprocessing", "runpy"
}

# Padrões regex para flags simples (I/O de rede, exec, shell, escrita em FS)
REGEX_SUSPICIOUS = [
    (re.compile(r"\bsubprocess\b"), "uso de subprocess (possível execução shell)"),
    (re.compile(r"\bos\.system\b"), "chamada direta a os.system"),
    (re.compile(r"\beval\s*\("), "uso de eval()"),
    (re.compile(r"\bexec\s*\("), "uso de exec()"),
    (re.compile(r"\bopen\s*\("), "abertura de arquivos (I/O)"),
    (re.compile(r"\brequests\b"), "uso de requests (network)"),
    (re.compile(r"\bsocket\b"), "uso de sockets (network)"),
    (re.compile(r"import\s+os\b"), "import de os (verificar uso)"),
    (re.compile(r"from\s+os\b"), "import de os (verificar uso)"),
]

CRITICAL_PATTERNS = {
    "exec": re.compile(r"\bexec\s*\("),
    "eval": re.compile(r"\beval\s*\("),
    "subprocess": re.compile(r"\bsubprocess\b"),
    "os_system": re.compile(r"\bos\.system\b"),
}

def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()[:12]

def _ast_findings(code: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    try:
        tree = ast.parse(code)
    except Exception as e:
        return [{"type": "syntax_error", "message": str(e)}]

    for node in ast.walk(tree):
        # Import usage
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = []
            if isinstance(node, ast.Import):
                for n in node.names:
                    names.append(n.name)
            else:
                module = node.module or ""
                for n in node.names:
                    names.append(f"{module}.{n.name}" if module else n.name)
            for nm in names:
                for black in AST_BLACKLIST_NAMES:
                    if black in nm:
                        findings.append({"type": "import_blacklist", "symbol": nm, "message": f"Import potencialmente perigoso: {nm}"})
        # Call usage
        if isinstance(node, ast.Call):
            # get function name by drilling
            fn = node.func
            qualname = ""
            if isinstance(fn, ast.Name):
                qualname = fn.id
            elif isinstance(fn, ast.Attribute):
                parts = []
                cur = fn
                while isinstance(cur, ast.Attribute):
                    parts.append(cur.attr)
                    cur = cur.value
                if isinstance(cur, ast.Name):
                    parts.append(cur.id)
                qualname = ".".join(reversed(parts))
            if qualname:
                for black in AST_BLACKLIST_NAMES:
                    if black.endswith(")") is False and black in qualname:
                        findings.append({"type": "call_blacklist", "call": qualname, "message": f"Chamada perigosa detectada: {qualname}"})
        # Exec/Eval nodes (python 3.9+ exec is a Call to builtin; also check names)
        if isinstance(node, ast.Name):
            if node.id in {"exec", "eval", "__import__"}:
                findings.append({"type": "name_usage", "name": node.id, "message": f"Uso do símbolo: {node.id}"})
    return findings

def _regex_findings(code: str) -> List[Dict[str, Any]]:
    findings = []
    for rx, desc in REGEX_SUSPICIOUS:
        for m in rx.finditer(code):
            findings.append({"pattern": rx.pattern, "message": desc, "span": m.span()})
    return findings

def _run_flake_if_available(code_path: Path) -> Tuple[bool, Optional[str]]:
    try:
        # check if flake8 is available
        p = shutil.which("flake8")
        if not p:
            return False, None
        # run flake8 on the temp file
        proc = subprocess.run([p, "--max-line-length=120", str(code_path)], capture_output=True, text=True, timeout=20)
        return True, proc.stdout + proc.stderr
    except Exception as e:
        return False, None

class BotAnalisadorSeguranca:
    def __init__(self, sandbox_executor_cls=None):
        """
        sandbox_executor_cls: classe/fábrica para criar executor (se None, usará import dinâmico de src.seguranca.SandboxExecutor)
        """
        self.sandbox_executor_cls = sandbox_executor_cls

    def testar_codigo_em_sandbox(self, codigo: str, allow_execution: bool = False, timeout: int = 30) -> Dict[str, Any]:
        """
        Analisa e (opcionalmente) executa código em sandbox.
        - codigo: código Python (string)
        - allow_execution: se True, executa mesmo havendo problemas; caso False, bloqueia execução quando há problemas críticos
        - timeout: seconds para execução no sandbox

        Retorna dict com chaves:
          sucesso(bool), executado(bool), stdout, stderr, exception, tempo_execucao, findings([...]), severity(0-10), recommendations([...]), metadata({...})
        """
        start = time.perf_counter()
        meta = {"id": _hash_code(codigo), "ts": time.time()}
        report: Dict[str, Any] = {
            "sucesso": False,
            "executado": False,
            "stdout": "",
            "stderr": "",
            "exception": None,
            "tempo_execucao": 0.0,
            "findings": [],
            "severity": 0,
            "recomendacoes": [],
            "meta": meta,
            "lint": None,
            "allowed_to_run": False,
        }

        # 1) Static checks (AST + regex)
        ast_find = _ast_findings(codigo)
        regex_find = _regex_findings(codigo)
        report["findings"].extend(ast_find)
        report["findings"].extend(regex_find)

        # 2) severity scoring heuristic
        severity = 0
        for f in report["findings"]:
            typ = f.get("type") or ""
            msg = f.get("message", "")
            if "exec" in msg or "eval" in msg or "subprocess" in msg or "system" in msg:
                severity += 6
            elif "Import potencialmente perigoso" in msg:
                severity += 5
            else:
                severity += 2
        # clamp
        severity = min(10, severity)
        report["severity"] = severity

        # 3) Lint if available (flake8)
        tmpdir = Path(tempfile.mkdtemp(prefix="arca_sandbox_"))
        code_file = tmpdir / f"code_{meta['id']}.py"
        code_file.write_text(codigo, encoding="utf-8")
        lint_available, lint_output = _run_flake_if_available(code_file)
        report["lint"] = {"available": lint_available, "output": lint_output}

        # 4) Recommendations from findings
        recs = []
        if severity >= 8:
            recs.append("Bloquear execução: código contém padrões críticos (exec/eval/subprocess/IO).")
        if severity >= 5:
            recs.append("Revisar imports e substitua operações de I/O ou chamadas de sistema por APIs seguras.")
        if "syntax_error" in [f.get("type") for f in report["findings"]]:
            recs.append("Corrigir erro de sintaxe antes de executar.")
        if lint_output:
            recs.append("Rodar linter (flake8) e corrigir problemas reportados.")
        report["recomendacoes"] = recs

        # 5) Decide if allowed to run
        allowed = allow_execution or (severity < 6 and not any(f.get("type") == "syntax_error" for f in report["findings"]))
        report["allowed_to_run"] = allowed

        # If not allowed, skip exec but return report
        if not allowed:
            report["sucesso"] = False
            report["executado"] = False
            report["tempo_execucao"] = time.perf_counter() - start
            # cleanup
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass
            return report

        # 6) Execute in sandbox
        try:
            # instantiate executor
            if self.sandbox_executor_cls:
                executor = self.sandbox_executor_cls(timeout_segundos=timeout)
            else:
                # lazy import local SandboxExecutor
                try:
                    from src.seguranca import SandboxExecutor
                    executor = SandboxExecutor(timeout_segundos=timeout)
                except Exception as e:
                    report["exception"] = f"SandboxExecutor não disponível: {e}"
                    report["sucesso"] = False
                    report["executado"] = False
                    report["tempo_execucao"] = time.perf_counter() - start
                    try:
                        shutil.rmtree(tmpdir)
                    except Exception:
                        pass
                    return report

            t0 = time.perf_counter()
            # executor expected to accept code file path or source and run a function "executar"
            try:
                resultado = executor.executar_codigo(codigo, funcao_entrada="executar")
            except TypeError:
                # fallback: if API expects file path
                resultado = executor.executar_arquivo(str(code_file), funcao_entrada="executar")
            t1 = time.perf_counter()
            report["tempo_execucao"] = t1 - t0

            # merge resultado expected structure
            if isinstance(resultado, dict):
                report["stdout"] = resultado.get("stdout", "") or ""
                report["stderr"] = resultado.get("stderr", "") or ""
                report["sucesso"] = bool(resultado.get("sucesso", True))
                report["executado"] = True
                report["resultado"] = resultado.get("resultado")
            else:
                # generic fallback
                report["stdout"] = str(resultado)
                report["sucesso"] = True
                report["executado"] = True

        except Exception as e:
            report["exception"] = str(e)
            report["sucesso"] = False
            report["executado"] = False
        finally:
            # attempt shutdown
            try:
                executor.shutdown()
            except Exception:
                pass
            # cleanup
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass

        # 7) Post-exec checks: if stderr or non-zero severity, add recommendations
        if report.get("stderr"):
            report["recomendacoes"].append("Revisar stderr gerado durante a execução.")
        if report["severity"] >= 6:
            report["recomendacoes"].append("Considerar revisão manual e testes em ambiente controlado antes de permitir deploy/uso.")

        return report
