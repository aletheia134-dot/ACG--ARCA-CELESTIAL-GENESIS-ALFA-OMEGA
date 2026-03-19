#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
lista_evolucao_ia.py - Lista de Oportunidades para IAs Escolherem

Gerencia a lista de compras do sistema:
- Apresenta 10 oportunidades
- IAs aceitam/recusam
- Atualiza semanalmente
- Rastreia aceitaes
- Mx 10 propostas por IA
"""


import datetime
import json
import logging
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class ListaEvolucaoIA:
    """
    Lista de oportunidades de melhoria que IAs podem escolher construir.Funciona como "lista de compras" do sistema.
    """

    def __init__(self, coracao_ref: Any, gerenciador_propostas_ref: Any):
        """
        Args:
            coracao_ref: Ref ação Corao
            gerenciador_propostas_ref: Ref ação GerenciadorPropostas
        """
        self.coracao = coracao_ref
        self.gerenciador_propostas = gerenciador_propostas_ref
        self.logger = logging.getLogger("ListaEvolucaoIA")
        
        # Oportunidades atuais
        self.oportunidades_atuais: List[Dict[str, Any]] = []
        
        # Rastreamento de aceitaes/recusas
        self.historico_interacoes: Dict[str, List[Dict[str, Any]]] = {}  # ia_name -> [interacoes]
        
        self._lock = threading.RLock()

    def atualizar_lista(self, novas_oportunidades: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Atualiza lista com novas oportunidades (chamado aps scan).
        
        Args:
            novas_oportunidades: Lista do scanner
        
        Returns:
            (sucesso, mensagem)
        """
        with self._lock:
            self.oportunidades_atuais = novas_oportunidades[:10]  # Mx 10
        
        msg = f"[OK] Lista atualizada: {len(self.oportunidades_atuais)} oportunidades"
        self.logger.info(msg)
        
        # Notificar
        self._notificar_ia_nova_lista()
        
        return True, msg

    def listar_oportunidades(self) -> List[Dict[str, Any]]:
        """Retorna lista atual de oportunidades."""
        with self._lock:
            return list(self.oportunidades_atuais)

    def obter_oportunidade(self, oportunidade_id: str) -> Optional[Dict[str, Any]]:
        """Obtm detalhes de uma oportunidade."""
        with self._lock:
            for op in self.oportunidades_atuais:
                if op.get("id") == oportunidade_id:
                    return op
        return None

    def ia_aceitar_oportunidade(
        self,
        ia_nome: str,
        oportunidade_id: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        IA aceita uma oportunidade e cria proposta.Returns:
            (sucesso, mensagem, proposta_id)
        """
        # Verificar limite de 10 propostas por IA
        ias_propostas = self._contar_propostas_ia(ia_nome)
        if ias_propostas >= 10:
            return False, f"[ERRO] {ia_nome} j tem 10 propostas pendentes", None
        
        # Obter oportunidade
        op = self.obter_oportunidade(oportunidade_id)
        if not op:
            return False, "[ERRO] Oportunidade no encontrada", None
        
        # Criar proposta
        sucesso, msg, proposta_id = self.gerenciador_propostas.criar_proposta(
            ia_solicitante=ia_nome,
            nome_ferramenta=op.get("nome"),
            descricao=op.get("descricao"),
            motivo=op.get("motivo"),
            intencao_uso=op.get("intencao_uso"),
            categoria=op.get("categoria"),
            tipo_ferramenta=op.get("tipo_ferramenta"),
            codigo_ou_comando=""  # IA preencher depois
        )
        
        if sucesso:
            # Registrar aceitao
            self._registrar_interacao(ia_nome, oportunidade_id, "ACEITA", proposta_id)
            
            msg_final = f"[OK] {ia_nome} aceitou: {op.get('nome')} (Proposta: {proposta_id})"
            self.logger.info(msg_final)
            
            return True, msg_final, proposta_id
        else:
            return False, msg, None

    def ia_recusar_oportunidade(
        self,
        ia_nome: str,
        oportunidade_id: str,
        motivo: str = ""
    ) -> Tuple[bool, str]:
        """
        IA recusa uma oportunidade.Oportunidade continua na lista para outra IA.
        """
        op = self.obter_oportunidade(oportunidade_id)
        if not op:
            return False, "[ERRO] Oportunidade no encontrada"
        
        # Registrar recusa
        self._registrar_interacao(ia_nome, oportunidade_id, "RECUSA", None, motivo)
        
        msg = f" {ia_nome} recusou: {op.get('nome')}"
        self.logger.info(msg)
        
        return True, msg

    def _contar_propostas_ia(self, ia_nome: str) -> int:
        """Conta quantas propostas pendentes a IA tem."""
        try:
            if not hasattr(self.gerenciador_propostas, "propostas_cache"):
                return 0
            
            count = 0
            for prop in self.gerenciador_propostas.propostas_cache.values():
                if prop.get("ia_solicitante") == ia_nome:
                    if prop.get("status") in ["PENDENTE_ANALISE", "EM_ANALISE", "APROVADO_CONSTRUO", "EM_CONSTRUCAO"]:
                        count += 1
            
            return count
        except Exception:
            return 0

    def _registrar_interacao(
        self,
        ia_nome: str,
        oportunidade_id: str,
        tipo: str,  # ACEITA, RECUSA
        proposta_id: Optional[str] = None,
        motivo: str = ""
    ) -> None:
        """Registra interao da IA com oportunidade."""
        with self._lock:
            if ia_nome not in self.historico_interacoes:
                self.historico_interacoes[ia_nome] = []
            
            self.historico_interacoes[ia_nome].append({
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "oportunidade_id": oportunidade_id,
                "tipo": tipo,
                "proposta_id": proposta_id,
                "motivo": motivo
            })

    def obter_historico_ia(self, ia_nome: str) -> List[Dict[str, Any]]:
        """Retorna histórico de interações da IA."""
        with self._lock:
            return self.historico_interacoes.get(ia_nome, [])

    def _notificar_ia_nova_lista(self) -> None:
        """Notifica IAs que h nova lista disponível."""
        try:
            if hasattr(self.coracao, "ui_queue"):
                self.coracao.ui_queue.put_nowait({
                    "tipo_resp": "LISTA_EVOLUCAO_ATUALIZADA",
                    "total_oportunidades": len(self.oportunidades_atuais),
                    "timestamp": datetime.datetime.utcnow().isoformat()
                })
        except Exception as e:
            self.logger.debug("Erro ao notificar: %s", e)

    def obter_resumo(self) -> Dict[str, Any]:
        """Retorna resumo da lista."""
        with self._lock:
            return {
                "total_oportunidades": len(self.oportunidades_atuais),
                "oportunidades": self.oportunidades_atuais,
                "ia_aceiturations": {
                    ia: len([i for i in interacoes if i.get("tipo") == "ACEITA"])
                    for ia, interacoes in self.historico_interacoes.items()
                }
            }

    def shutdown(self) -> None:
        """Desliga."""
        self.logger.info(" Desligando ListaEvolucaoIA...")
        with self._lock:
            self.oportunidades_atuais.clear()
        self.logger.info("[OK] ListaEvolucaoIA desligado")


