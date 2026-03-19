#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
integracao_evolucao_corao.py - Integra Sistema de Evoluo no Corao v7

Adiciona ao Coração:
- Scanner de Sistema (subsistema 27)
- Lista de Evoluo IA (subsistema 28)
- Gestor de Ciclos (subsistema 29)

Métodos pblicos para IAs e humanos
"""


import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class IntegracaoEvolucaoIA:
    """
    Mixin para adicionar evoluo auto-adaptativa ação Corao.
    """

    def _inicializar_sistema_evolucao(self) -> None:
        """
        Inicializa sistema de evoluo.Chamado no __init__ do Corao APS inicializar propostas.
        """
        from src.engenharia.scanner_sistema import ScannerSistema
        from src.engenharia.lista_evolucao_ia import ListaEvolucaoIA
        from src.engenharia.gestor_ciclo_evolucao import GestorCicloEvolucao
        
        try:
            # 1.Scanner de Sistema
            self.scanner_sistema = ScannerSistema(
                coracao_ref=self,
                intervalo_dias=7  # Semanal
            )
            self.scanner_sistema.iniciar_monitoramento()
            self.modulos["scanner_sistema"] = self.scanner_sistema
            self.logger.info("[OK] Subsistema 27: ScannerSistema")
            
            # 2.Lista de Evoluo
            self.lista_evolucao_ia = ListaEvolucaoIA(
                coracao_ref=self,
                gerenciador_propostas_ref=self.gerenciador_propostas if hasattr(self, "gerenciador_propostas") else None
            )
            self.modulos["lista_evolucao_ia"] = self.lista_evolucao_ia
            self.logger.info("[OK] Subsistema 28: ListaEvolucaoIA")
            
            # 3.Gestor de Ciclos
            self.gestor_ciclo_evolucao = GestorCicloEvolucao(
                coracao_ref=self,
                scanner_ref=self.scanner_sistema,
                lista_evolucao_ref=self.lista_evolucao_ia
            )
            self.modulos["gestor_ciclo_evolucao"] = self.gestor_ciclo_evolucao
            self.logger.info("[OK] Subsistema 29: GestorCicloEvolucao")
            
            # Iniciar ciclos
            self.gestor_ciclo_evolucao.iniciar()
            
        except Exception as e:
            self.logger.exception("Erro ao inicializar sistema de evoluo: %s", e)

    # =========================================================================
    # API PBLICA - PARA IAs
    # =========================================================================

    def obter_lista_evolucao(self) -> Dict[str, Any]:
        """
        IA obtm lista atual de oportunidades de melhoria.Returns:
            {
                "total": 10,
                "oportunidades": [...]
            }
        """
        if not hasattr(self, "lista_evolucao_ia"):
            return {"total": 0, "oportunidades": []}
        
        oportunidades = self.lista_evolucao_ia.listar_oportunidades()
        return {
            "total": len(oportunidades),
            "oportunidades": oportunidades
        }

    def ia_aceitar_oportunidade(
        self,
        ia_nome: str,
        oportunidade_id: str
    ) -> Dict[str, Any]:
        """
        IA aceita uma oportunidade e cria proposta.Returns:
            {
                "sucesso": bool,
                "mensagem": str,
                "proposta_id": str (se sucesso)
            }
        """
        if not hasattr(self, "lista_evolucao_ia"):
            return {
                "sucesso": False,
                "mensagem": "Sistema de evoluo no disponível"
            }
        
        sucesso, msg, proposta_id = self.lista_evolucao_ia.ia_aceitar_oportunidade(
            ia_nome=ia_nome,
            oportunidade_id=oportunidade_id
        )
        
        return {
            "sucesso": sucesso,
            "mensagem": msg,
            "proposta_id": proposta_id
        }

    def ia_recusar_oportunidade(
        self,
        ia_nome: str,
        oportunidade_id: str,
        motivo: str = ""
    ) -> Dict[str, Any]:
        """
        IA recusa uma oportunidade.Oportunidade continua disponível para outras IAs.
        """
        if not hasattr(self, "lista_evolucao_ia"):
            return {
                "sucesso": False,
                "mensagem": "Sistema de evoluo no disponível"
            }
        
        sucesso, msg = self.lista_evolucao_ia.ia_recusar_oportunidade(
            ia_nome=ia_nome,
            oportunidade_id=oportunidade_id,
            motivo=motivo
        )
        
        return {
            "sucesso": sucesso,
            "mensagem": msg
        }

    def obter_historico_ia(self, ia_nome: str) -> Dict[str, Any]:
        """Obtm histórico de interações da IA com lista."""
        if not hasattr(self, "lista_evolucao_ia"):
            return {"histórico": []}
        
        histórico = self.lista_evolucao_ia.obter_historico_ia(ia_nome)
        return {
            "ia_nome": ia_nome,
            "total_interacoes": len(histórico),
            "histórico": histórico
        }

    # =========================================================================
    # API PBLICA - PARA MONITORAMENTO
    # =========================================================================

    def obter_status_evolucao(self) -> Dict[str, Any]:
        """Retorna status completo do sistema de evoluo."""
        if not hasattr(self, "gestor_ciclo_evolucao"):
            return {}
        
        status = self.gestor_ciclo_evolucao.obter_status()
        resumo = self.lista_evolucao_ia.obter_resumo() if hasattr(self, "lista_evolucao_ia") else {}
        
        return {
            "ciclos_completos": status.get("ciclos_completos"),
            "proxima_execucao": status.get("proxima_execucao"),
            "oportunidades_atuais": resumo.get("total_oportunidades", 0),
            "lista": resumo.get("oportunidades", []),
            "aceiturations_por_ia": resumo.get("ia_aceiturations", {})
        }

    # =========================================================================
    # SHUTDOWN
    # =========================================================================

    def _shutdown_evolucao(self) -> None:
        """Desliga sistema de evoluo."""
        if hasattr(self, "gestor_ciclo_evolucao"):
            self.gestor_ciclo_evolucao.shutdown()
        if hasattr(self, "lista_evolucao_ia"):
            self.lista_evolucao_ia.shutdown()
        if hasattr(self, "scanner_sistema"):
            self.scanner_sistema.shutdown()


