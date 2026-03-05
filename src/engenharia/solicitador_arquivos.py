#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
solicitador_arquivos.py - Gerenciador de Acesso a Arquivos

IA solicita arquivo â†’ obtém path â†’ usa â†’ acesso é revogado

Nota: Lista de arquivos é simulada (mock) para teste.Em produção, vir de: sys.modules, site-packages, venv, etc

Responsabilidades:
- Validar permissões
- Fornecer paths
- Revogar acesso
- Auditoria
- Cleanup automático de acessos expirados
"""
from __future__ import annotations


import datetime
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class SolicitadorArquivos:
    """
    Gerencia solicitação de arquivos/módulos pelas IAs.Fluxo:
    1.IA solicita arquivo
    2.Sistema valida
    3.Sistema fornece path
    4.IA usa
    5.Acesso expirado após tempo
    """

    def __init__(self, coracao_ref: Any):
        """Args: coracao_ref - Ref ao Coração"""
        self.coracao = coracao_ref
        self.logger = logging.getLogger("SolicitadorArquivos")
        
        # Buscar módulos disponíveis dinamicamente (código real)
        self.arquivos_disponiveis = self._listar_modulos_reais()
        
        # Acessos concedidos
        self.acessos_ativos: Dict[str, Dict[str, Any]] = {}
        
        self._lock = threading.RLock()
        
        # Iniciar cleanup periódico
        self.iniciar_cleanup_periodico(intervalo_horas=1)

    def _listar_modulos_reais(self) -> Dict[str, str]:
        """
        Lista módulos reais instalados (sys.modules, site-packages, venv).
        Retorna {nome_modulo: caminho_para_arquivo_ou_pasta}.
        """
        import sys
        import site
        import os
        from pathlib import Path
        
        modulos = {}
        
        # 1. De sys.modules (módulos já importados)
        for nome, modulo in sys.modules.items():
            if hasattr(modulo, '__file__') and modulo.__file__:
                caminho = Path(modulo.__file__).resolve()
                if caminho.exists() and not nome.startswith('_'):
                    modulos[nome.split('.')[0]] = str(caminho.parent)  # Pasta do módulo
        
        # 2. De site-packages
        for site_path in site.getsitepackages():
            site_path = Path(site_path)
            if site_path.exists():
                for item in site_path.iterdir():
                    if item.is_dir() and not item.name.startswith('.'):
                        modulos[item.name] = str(item)
                    elif item.is_file() and item.suffix == '.py':
                        nome = item.stem
                        modulos[nome] = str(item)
        
        # 3. De venv atual (se existir)
        venv_path = os.environ.get('VIRTUAL_ENV')
        if venv_path:
            lib_path = Path(venv_path) / 'Lib' / 'site-packages'  # Windows
            if not lib_path.exists():
                lib_path = Path(venv_path) / 'lib' / 'python3.10' / 'site-packages'  # Linux/Mac
            if lib_path.exists():
                for item in lib_path.iterdir():
                    if item.is_dir() and not item.name.startswith('.'):
                        modulos[item.name] = str(item)
        
        # Filtrar duplicatas e manter únicos
        modulos_filtrados = {}
        for nome, caminho in modulos.items():
            if nome not in modulos_filtrados:
                modulos_filtrados[nome] = caminho
        
        self.logger.info(f"ðŸ“¦ Encontrados {len(modulos_filtrados)} módulos reais disponíveis")
        return modulos_filtrados

    def solicitar_arquivos(
        self,
        proposta_id: str,
        ia_solicitante: str,
        lista_modulos: List[str],
        duracao_minutos: int = 120
    ) -> Tuple[bool, Dict[str, str], str]:
        """
        IA solicita módulos/arquivos.Args:
            proposta_id: ID da proposta que solicitou
            ia_solicitante: Nome da IA
            lista_modulos: ["numpy", "pillow"]
            duracao_minutos: Tempo de acesso
        
        Returns:
            (sucesso, {modulo: path}, mensagem)
        """
        # Validar módulos
        modulos_validos = {}
        modulos_invalidos = []
        
        for modulo in lista_modulos:
            modulo_lower = modulo.lower()
            if modulo_lower in self.arquivos_disponiveis:
                modulos_validos[modulo_lower] = self.arquivos_disponiveis[modulo_lower]
            else:
                modulos_invalidos.append(modulo)
        
        if modulos_invalidos:
            msg = f"âŒ Módulos não encontrados: {modulos_invalidos}"
            self.logger.warning(msg)
            return False, {}, msg
        
        # Gerar ID de acesso
        acesso_id = f"{proposta_id}_{ia_solicitante}"
        expiracao = datetime.datetime.utcnow() + datetime.timedelta(minutes=duracao_minutos)
        
        # Registrar acesso
        with self._lock:
            self.acessos_ativos[acesso_id] = {
                "proposta_id": proposta_id,
                "ia_solicitante": ia_solicitante,
                "modulos": list(modulos_validos.keys()),
                "tempo_concessao": datetime.datetime.utcnow().isoformat(),
                "tempo_expiracao": expiracao.isoformat(),
                "paths": modulos_validos
            }
        
        msg = f"âœ… Acesso concedido a {len(modulos_validos)} módulo(s) por {duracao_minutos} min"
        self.logger.info(msg)
        
        # Notificar
        self._notificar_coacao("ARQUIVO_SOLICITADO", {
            "proposta_id": proposta_id,
            "ia_solicitante": ia_solicitante,
            "modulos": list(modulos_validos.keys())
        })
        
        return True, modulos_validos, msg

    def validar_acesso(self, acesso_id: str) -> Tuple[bool, Optional[Dict[str, str]]]:
        """Valida se acesso ainda está válido."""
        with self._lock:
            acesso = self.acessos_ativos.get(acesso_id)
        
        if not acesso:
            return False, None
        
        expiracao = datetime.datetime.fromisoformat(acesso.get("tempo_expiracao"))
        if datetime.datetime.utcnow() > expiracao:
            self.revogar_acesso(acesso_id)
            return False, None
        
        return True, acesso.get("paths")

    def revogar_acesso(self, acesso_id: str) -> bool:
        """Revoga acesso a um arquivo."""
        with self._lock:
            if acesso_id in self.acessos_ativos:
                acesso = self.acessos_ativos.pop(acesso_id)
                self.logger.info(
                    "âœ‚ï¸ Acesso revogado: IA=%s, módulos=%s",
                    acesso.get("ia_solicitante"),
                    acesso.get("modulos")
                )
                return True
        return False

    def listar_arquivos_disponiveis(self) -> Dict[str, str]:
        """Lista todos os módulos disponíveis."""
        return dict(self.arquivos_disponiveis)

    def listar_acessos_ativos(self) -> List[Dict[str, Any]]:
        """Lista acessos ativos."""
        with self._lock:
            return list(self.acessos_ativos.values())

    def limpar_acessos_expirados(self) -> int:
        """Remove acessos que expiraram."""
        agora = datetime.datetime.utcnow()
        expirados = []
        
        with self._lock:
            for acesso_id, acesso in list(self.acessos_ativos.items()):
                expiracao = datetime.datetime.fromisoformat(acesso.get("tempo_expiracao"))
                if agora > expiracao:
                    expirados.append(acesso_id)
                    self.acessos_ativos.pop(acesso_id)
        
        if expirados:
            self.logger.info("ðŸ§¹ Limpeza: %d acessos expirados removidos", len(expirados))
        
        return len(expirados)

    def iniciar_cleanup_periodico(self, intervalo_horas: int = 1) -> None:
        """âœ… NOVO: Inicia limpeza automática de acessos expirados."""
        def _cleanup_thread():
            while True:
                try:
                    self.limpar_acessos_expirados()
                    time.sleep(intervalo_horas * 3600)
                except Exception as e:
                    self.logger.debug("Erro no cleanup: %s", e)
                    time.sleep(300)
        
        t = threading.Thread(target=_cleanup_thread, daemon=True, name="SolicitadorArquivosCleanup")
        t.start()
        self.logger.debug("âœ… Cleanup automático iniciado (intervalo: %d h)", intervalo_horas)

    def _notificar_coacao(self, tipo_evento: str, dados: Dict[str, Any]) -> None:
        """Notifica Coração."""
        try:
            if hasattr(self.coracao, "ui_queue"):
                self.coracao.ui_queue.put_nowait({
                    "tipo_resp": f"ARQUIVOS_{tipo_evento}",
                    "dados": dados,
                    "timestamp": datetime.datetime.utcnow().isoformat()
                })
        except Exception as e:
            self.logger.debug("Erro ao notificar Coração: %s", e)

    def shutdown(self) -> None:
        """Desliga."""
        self.logger.info("ðŸ›‘ Desligando SolicitadorArquivos...")
        with self._lock:
            self.acessos_ativos.clear()
        self.logger.info("âœ… SolicitadorArquivos desligado")
