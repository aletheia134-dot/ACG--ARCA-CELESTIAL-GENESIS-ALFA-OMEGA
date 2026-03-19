#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
sandbox_executor.py - Executor seguro de cdigo utilizando Docker CLI ou RestrictedPython.
"""


import ast
import logging
import re
import subprocess
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

try:
    from RestrictedPython import compile_restricted
    from RestrictedPython.Guards import safe_builtins
    _RESTRICTED_OK = True
except:
    logging.getLogger(__name__).warning("[AVISO] compile_restricted no disponível")
    compile_restricted = None
    safe_builtins = {}
    _RESTRICTED_OK = False

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class SandboxExecutor:
    """
    Classe responsvel por executar o cdigo em Sandbox com Docker ou RestrictedPython.
    """

    def __init__(
        self,
        docker_image: str = "python:3.11-slim",
        timeout_segundos: int = 30,
        memoria_max_mb: int = 512,
        cpu_max_cores: int = 1,
    ):
        self.docker_image = docker_image
        self.timeout_segundos = timeout_segundos
        self.memoria_max_mb = memoria_max_mb
        self.cpu_max_cores = cpu_max_cores
        self.logger = logging.getLogger("SandboxExecutor")
        self.containers_ativos = {}

        # Identificar se o Docker CLI est disponível
        self.docker_disponivel = self._verificar_docker_cli()

    def _verificar_docker_cli(self) -> bool:
        """
        Verifica se o Docker CLI est disponível no PATH e funcional.
        """
        try:
            self._testar_docker_cli()  # Método adicionado para logs detalhados
            return True
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"[AVISO] Docker CLI indisponível ou mal configurado. Detalhes: {e.stderr}")
            return False
        except FileNotFoundError:
            self.logger.error("[ERRO] Docker CLI no encontrado. Certifique-se de que est instalado e no PATH.")
            return False

    def _testar_docker_cli(self) -> None:
        """
        Executa o comando 'docker version' para validar se o CLI est acessvel.
        """
        self.logger.info("Testando comando Docker 'docker version'...")
        resultado = subprocess.run(
            ["docker", "version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        self.logger.info(f"[OK] Docker CLI detectado.")
        self.logger.debug(f"Detalhes Docker: {resultado.stdout}")

    def executar_codigo(
        self, codigo: str, parametros: Optional[Dict[str, Any]] = None, funcao_entrada: str = "executar"
    ) -> Dict[str, Any]:
        """
        Verifica e executa o cdigo em Sandbox. Fallback para RestrictedPython caso Docker CLI no esteja disponível.
        """
        inicio = time.time()
        exec_id = str(uuid.uuid4())[:6]  # Gerar ID curto para o log

        # Validao inicial do cdigo
        válido, erros, avisos = self._validar_codigo_restrito(codigo)
        if not válido:
            return {
                "sucesso": False,
                "stdout": "",
                "stderr": "\n".join(erros),
                "tempo_execucao": time.time() - inicio,
                "erros": erros,
                "avisos": avisos,
            }

        # Escolher entre Docker CLI ou RestrictedPython
        if self.docker_disponivel:
            resultado = self._executar_em_docker(codigo, funcao_entrada, exec_id)
        else:
            resultado = self._executar_modo_restrito(codigo, funcao_entrada)

        resultado["tempo_execucao"] = time.time() - inicio
        resultado["avisos"] = avisos
        return resultado

    def _validar_codigo_restrito(self, codigo: str) -> Tuple[bool, List[str], List[str]]:
        """
        válida o cdigo usando RestrictedPython para prevenir execução de comportamentos no seguros.
        """
        erros = []
        avisos = []

        try:
            ast.parse(codigo)
        except SyntaxError as e:
            erros.append(f"[ERRO] Erro de sintaxe: {e}")
            return False, erros, avisos

        try:
            resultado = compile_restricted(codigo, "<string>", "exec")
            if hasattr(resultado, "errors") and resultado.errors:
                erros.extend([f"[ERRO] {e}" for e in resultado.errors])
        except Exception as e:
            erros.append(f"[ERRO] Erro de compilao: {e}")
            return False, erros, avisos

        padroes_perigosos = [
            (r"import os", "[AVISO] Importao do módulo OS detectada."),
            (r"exec\(", "[AVISO] Uso do método exec() encontrado."),
            (r"eval\(", "[AVISO] Uso do método eval() encontrado."),
        ]
        for padrão, descricao in padroes_perigosos:
            if re.search(padrão, codigo, re.IGNORECASE):
                avisos.append(descricao)

        return len(erros) == 0, erros, avisos

    def _executar_em_docker(self, codigo: str, funcao_entrada: str, exec_id: str) -> Dict[str, Any]:
        """
        Executa cdigo em um continer Docker utilizando subprocess.
        """
        try:
            comando = [
                "docker",
                "run",
                "--rm",
                "--memory",
                f"{self.memoria_max_mb}m",
                "--cpus",
                str(self.cpu_max_cores),
                self.docker_image,
                "python",
                "-c",
                codigo,
            ]
            self.logger.info(f" Executando cdigo em continer Docker (ID {exec_id})...")
            resultado = subprocess.run(
                comando,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=self.timeout_segundos,
                text=True,
            )
            self.logger.info(f"[OK] execução no continer Docker concluda com sucesso (ID {exec_id})")
            return {
                "sucesso": True,
                "stdout": resultado.stdout,
                "stderr": resultado.stderr,
                "erros": [],
            }
        except subprocess.TimeoutExpired:
            self.logger.error(f" Tempo limite de execução excedido (ID {exec_id})!")
            return {
                "sucesso": False,
                "stdout": "",
                "stderr": "Tempo limite excedido",
                "erros": ["Timeout"],
            }
        except subprocess.CalledProcessError as e:
            self.logger.error(f"[ERRO] Erro durante a execução no Docker (ID {exec_id}): {e.stderr}")
            return {
                "sucesso": False,
                "stdout": e.stdout,
                "stderr": e.stderr,
                "erros": ["Erro de execução no Docker"],
            }

    def _executar_modo_restrito(self, codigo: str, funcao_entrada: str) -> Dict[str, Any]:
        """
        Executa o cdigo de forma restrita (fallback para o RestrictedPython).
        """
        try:
            namespace = {"__builtins__": safe_builtins}
            exec(compile_restricted(codigo, "<string>", "exec"), namespace)
            return {
                "sucesso": True,
                "stdout": "Cdigo executado no modo restrito.",
                "stderr": "",
                "erros": [],
            }
        except Exception as e:
            return {
                "sucesso": False,
                "stdout": "",
                "stderr": str(e),
                "erros": [str(e)],
            }
