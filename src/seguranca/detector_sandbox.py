#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
detector_sandbox.py - Detecta e válida disponibilidade de Sandbox

Responsabilidades:
- Verificar se Docker est instalado
- Verificar se RestrictedPython est disponível
- Detectar modo de execução (com/sem sandbox)
- Informar IA sobre capacidades
"""


import logging
import subprocess
import sys
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class DetectorSandbox:
    """
    Detecta disponibilidade do Sandbox no sistema.
    """

    def __init__(self):
        """Inicializa detector."""
        self.logger = logging.getLogger("DetectorSandbox")
        
        # Status de cada componente
        self.docker_disponivel = False
        self.restricted_python_disponivel = False
        self.modo_sandbox = "DESCONHECIDO"
        self.detalhes = {}
        
        # Detectar automaticamente
        self._detectar_tudo()

    def _detectar_tudo(self) -> None:
        """Detecta todos os componentes."""
        self._detectar_docker()
        self._detectar_restricted_python()
        self._determinar_modo()

    def _detectar_docker(self) -> None:
        """Verifica se Docker est instalado e rodando."""
        try:
            # Verificar verso
            resultado = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if resultado.returncode == 0:
                versao = resultado.stdout.strip()
                self.logger.info("[OK] Docker detectado: %s", versao)
                
                # Verificar se daemon est rodando
                resultado_ps = subprocess.run(
                    ["docker", "ps"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if resultado_ps.returncode == 0:
                    self.docker_disponivel = True
                    self.detalhes["docker_versao"] = versao
                    self.detalhes["docker_running"] = True
                    self.logger.info("[OK] Docker daemon ativo")
                else:
                    self.detalhes["docker_versao"] = versao
                    self.detalhes["docker_running"] = False
                    self.logger.warning("    Docker instalado mas daemon no est rodando")
            else:
                self.logger.warning("[AVISO] Docker no encontrado no PATH")
                self.detalhes["docker_versao"] = None
                self.detalhes["docker_running"] = False
        
        except FileNotFoundError:
            self.logger.warning("[ERRO] Docker no est instalado")
            self.detalhes["docker_versao"] = None
            self.detalhes["docker_running"] = False
        except subprocess.TimeoutExpired:
            self.logger.warning("[AVISO] Timeout ação verificar Docker")
            self.detalhes["docker_running"] = False
        except Exception as e:
            self.logger.exception("Erro ao detectar Docker: %s", e)
            self.detalhes["docker_running"] = False

    def _detectar_restricted_python(self) -> None:
        """Verifica se RestrictedPython est instalado."""
        try:
            import RestrictedPython
            versao = RestrictedPython.__version__
            self.restricted_python_disponivel = True
            self.detalhes["restricted_python_versao"] = versao
            self.logger.info("[OK] RestrictedPython detectado: %s", versao)
        except ImportError:
            self.restricted_python_disponivel = False
            self.detalhes["restricted_python_versao"] = None
            self.logger.warning("[AVISO] RestrictedPython no est instalado")
        except Exception as e:
            self.logger.exception("Erro ao detectar RestrictedPython: %s", e)
            self.restricted_python_disponivel = False

    def _determinar_modo(self) -> None:
        """Determina modo de execução de sandbox."""
        if self.docker_disponivel and self.restricted_python_disponivel:
            self.modo_sandbox = "COMPLETO"
            self.logger.info("[OK] MODO SANDBOX: COMPLETO (Docker + RestrictedPython)")
        elif self.restricted_python_disponivel:
            self.modo_sandbox = "RESTRINGIDO"
            self.logger.info("[AVISO] MODO SANDBOX: RESTRINGIDO (apenas RestrictedPython, sem Docker)")
        else:
            self.modo_sandbox = "DESABILITADO"
            self.logger.warning("[ERRO] MODO SANDBOX: DESABILITADO (instale RestrictedPython e Docker)")

    def obter_status(self) -> Dict[str, Any]:
        """Retorna status completo do sandbox."""
        return {
            "modo": self.modo_sandbox,
            "docker_disponivel": self.docker_disponivel,
            "restricted_python_disponivel": self.restricted_python_disponivel,
            "detalhes": self.detalhes
        }

    def obter_instrucoes_instalacao(self) -> str:
        """Retorna instrues de instalao baseado no que est faltando."""
        instrucoes = []
        
        if not self.docker_disponivel:
            instrucoes.append("""
╔════════════════════════════════════════════════════════════╗
 INSTALAO DO DOCKER                                       
╚════════════════════════════════════════════════════════════╝

WINDOWS/macOS:
  1.Visite: https://www.docker.com/products/docker-desktop
  2.Download Docker Desktop
  3.Instale seguindo as instrues
  4.Verifique: docker --version

LINUX (Ubuntu/Debian):
  sudo apt update
  sudo apt install docker.io
  sudo systemctl start docker
  sudo usermod -aG docker $USER  # Para usar sem sudo
  docker --version
""")
        
        if not self.restricted_python_disponivel:
            instrucoes.append("""
╔════════════════════════════════════════════════════════════╗
 INSTALAO DO RESTRICTEDPYTHON                             
╚════════════════════════════════════════════════════════════╝

pip install RestrictedPython

Verificar:
  python -c "import RestrictedPython; print(RestrictedPython.__version__)"
""")
        
        if not instrucoes:
            return "[OK] Sistema de Sandbox est 100% configurado!"
        
        return "\n".join(instrucoes)

    def tentar_ativar_docker(self) -> Tuple[bool, str]:
        """Tenta ativar daemon do Docker."""
        try:
            if not self.docker_disponivel and self.detalhes.get("docker_versao"):
                self.logger.info("Tentando ativar Docker daemon...")
                
                # Tentar diferentes formas de ativar
                for comando in [
                    ["sudo", "systemctl", "start", "docker"],  # Linux
                    ["open", "-a", "Docker"],  # macOS
                    ["start", "Docker Desktop"],  # Windows
                ]:
                    try:
                        subprocess.run(comando, timeout=10, capture_output=True)
                        self.logger.info("Docker iniciado com: %s", " ".join(comando))
                        
                        # Verificar novamente
                        import time
                        time.sleep(2)
                        self._detectar_docker()
                        
                        if self.docker_disponivel:
                            return True, "[OK] Docker daemon ativado com sucesso"
                    except Exception:
                        continue
        
        except Exception as e:
            self.logger.exception("Erro ao ativar Docker: %s", e)
        
        return False, "[ERRO] No foi possível ativar Docker daemon"


