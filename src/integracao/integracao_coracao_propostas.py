#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
integracao_coração_propostas.py - Integra sistema de propostas NO CORAÇÍO v7

Adiciona ao CoracaoOrquestrador:
- GerenciadorPropostas (subsistema 23)
- ConstrutorIncremental (subsistema 24)
- SolicitadorArquivos (subsistema 25)
- BotAnalisadorSeguranca (subsistema 26)

Métodos públicos para usar o sistema

MUDANÇAS v2:
âœ… Não inicia construção automaticamente na aprovação
âœ… Adicionado método iniciar_construcao_proposta()
âœ… Adicionado método atualizar_codigo_proposta()
âœ… Adicionado método analisar_seguranca_proposta()
"""
from __future__ import annotations


import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class IntegracaoProptas:
    """
    Mixin para adicionar ao Coração as funcionalidades de propostas.Adiciona métodos:
    - criar_proposta_ferramenta()
    - aprovar_proposta()
    - rejeitar_proposta()
    - atualizar_codigo_proposta()
    - iniciar_construcao_proposta()
    - analisar_seguranca_proposta()
    - obter_status_proposta()
    - listar_propostas_pendentes()
    """

    def _inicializar_sistema_propostas(self) -> None:
        """
        Inicializa sistema de propostas (chamado no __init__ do Coração).
        
        Adiciona APÓS inicializar subsistemas base.
        """
        from src.engenharia.sistema_propostas_ferramentas import GerenciadorPropostas
        from src.engenharia.construtor_ferramentas_incremental import ConstrutorFerramentasIncremental
        from src.modulos.solicitador_arquivos import SolicitadorArquivos
        from bot_analise_seguranca_v2 import BotAnalisadorSeguranca
        
        try:
            # 1.Gerenciador de Propostas
            self.gerenciador_propostas = GerenciadorPropostas(
                coracao_ref=self,
                db_path="data/propostas_ferramentas.db"
            )
            self.modulos["gerenciador_propostas"] = self.gerenciador_propostas
            self.logger.info("âœ… Subsistema 23: GerenciadorPropostas")
            
            # 2.Construtor Incremental
            self.construtor_ferramentas = ConstrutorFerramentasIncremental(
                gerenciador_propostas=self.gerenciador_propostas,
                coracao_ref=self
            )
            self.modulos["construtor_ferramentas"] = self.construtor_ferramentas
            self.logger.info("âœ… Subsistema 24: ConstrutorIncremental")
            
            # 3.Solicitador de Arquivos
            self.solicitador_arquivos = SolicitadorArquivos(
                coracao_ref=self
            )
            self.modulos["solicitador_arquivos"] = self.solicitador_arquivos
            self.logger.info("âœ… Subsistema 25: SolicitadorArquivos")
            
            # 4.Bot Analisador de Segurança
            self.bot_seguranca = BotAnalisadorSeguranca(
                coracao_ref=self,
                gerenciador_propostas_ref=self.gerenciador_propostas
            )
            self.modulos["bot_analise_seguranca"] = self.bot_seguranca
            self.logger.info("âœ… Subsistema 26: BotAnalisadorSeguranca")
            
        except Exception as e:
            self.logger.exception("Erro ao inicializar sistema de propostas: %s", e)

    # =========================================================================
    # API PÚBLICA - IA CRIAR PROPOSTA
    # =========================================================================

    def criar_proposta_ferramenta(
        self,
        ia_solicitante: str,
        nome_ferramenta: str,
        descricao: str,
        motivo: str,
        intencao_uso: str,
        categoria: str = "geral",
        tipo_ferramenta: str = "script_python_dinamico",
        codigo_ou_comando: str = ""
    ) -> Dict[str, Any]:
        """
        IA cria proposta de nova ferramenta.Args:
            ia_solicitante: Nome da IA que solicita
            nome_ferramenta: Nome da ferramenta
            descricao: Descrição do que faz
            motivo: Por que precisa
            intencao_uso: Como será usada
            categoria: Categoria (midia, nlp, ciencia, etc)
            tipo_ferramenta: script_python_dinamico ou comando_sistema
            codigo_ou_comando: Código/comando (opcional, IA envia depois)
        
        Returns:
            {
                "sucesso": bool,
                "mensagem": str,
                "proposta_id": str (se sucesso)
            }
        """
        if not hasattr(self, "gerenciador_propostas"):
            return {
                "sucesso": False,
                "mensagem": "Sistema de propostas não disponível"
            }
        
        sucesso, msg, proposta_id = self.gerenciador_propostas.criar_proposta(
            ia_solicitante=ia_solicitante,
            nome_ferramenta=nome_ferramenta,
            descricao=descricao,
            motivo=motivo,
            intencao_uso=intencao_uso,
            categoria=categoria,
            tipo_ferramenta=tipo_ferramenta,
            codigo_ou_comando=codigo_ou_comando
        )
        
        return {
            "sucesso": sucesso,
            "mensagem": msg,
            "proposta_id": proposta_id
        }

    # =========================================================================
    # API PÚBLICA - IA ATUALIZAR CÓDIGO
    # =========================================================================

    def atualizar_codigo_proposta(
        self,
        proposta_id: str,
        ia_solicitante: str,
        codigo: str
    ) -> Dict[str, Any]:
        """
        IA envia código para proposta já criada.Args:
            proposta_id: ID da proposta
            ia_solicitante: Nome da IA
            codigo: Código Python/comando
        
        Returns:
            {"sucesso": bool, "mensagem": str}
        """
        if not hasattr(self, "gerenciador_propostas"):
            return {"sucesso": False, "mensagem": "Sistema não disponível"}
        
        sucesso, msg = self.gerenciador_propostas.atualizar_codigo_proposta(
            proposta_id=proposta_id,
            ia_solicitante=ia_solicitante,
            codigo=codigo
        )
        
        return {"sucesso": sucesso, "mensagem": msg}

    # =========================================================================
    # API PÚBLICA - HUMANO APROVAR/REJEITAR
    # =========================================================================

    def aprovar_proposta_ferramenta(
        self,
        proposta_id: str,
        por_humano: str,
        motivo: str = ""
    ) -> Dict[str, Any]:
        """Humano aprova proposta â†’ passa para construção."""
        if not hasattr(self, "gerenciador_propostas"):
            return {"sucesso": False, "mensagem": "Sistema não disponível"}
        
        sucesso, msg = self.gerenciador_propostas.aprovar_proposta(
            proposta_id=proposta_id,
            por_humano=por_humano,
            motivo=motivo
        )
        
        # âœ… FIX: NÍO inicia construção automaticamente
        # IA vai enviar código e pedir para iniciar
        
        return {"sucesso": sucesso, "mensagem": msg}

    def rejeitar_proposta_ferramenta(
        self,
        proposta_id: str,
        por_humano: str,
        motivo_rejeicao: str
    ) -> Dict[str, Any]:
        """Humano rejeita proposta."""
        if not hasattr(self, "gerenciador_propostas"):
            return {"sucesso": False, "mensagem": "Sistema não disponível"}
        
        sucesso, msg = self.gerenciador_propostas.rejeitar_proposta(
            proposta_id=proposta_id,
            por_humano=por_humano,
            motivo_rejeicao=motivo_rejeicao
        )
        
        return {"sucesso": sucesso, "mensagem": msg}

    def analisar_depois_proposta_ferramenta(
        self,
        proposta_id: str,
        por_humano: str,
        motivo: str = ""
    ) -> Dict[str, Any]:
        """Humano marca para análise posterior."""
        if not hasattr(self, "gerenciador_propostas"):
            return {"sucesso": False, "mensagem": "Sistema não disponível"}
        
        sucesso, msg = self.gerenciador_propostas.mover_para_analise(
            proposta_id=proposta_id,
            por_humano=por_humano,
            motivo=motivo
        )
        
        return {"sucesso": sucesso, "mensagem": msg}

    # =========================================================================
    # API PÚBLICA - IA INICIAR CONSTRUÇÍO
    # =========================================================================

    def iniciar_construcao_proposta(
        self,
        proposta_id: str,
        ia_solicitante: str
    ) -> Dict[str, Any]:
        """âœ… NOVO: IA solicita início da construção (após enviar código)."""
        if not hasattr(self, "construtor_ferramentas"):
            return {"sucesso": False, "mensagem": "Sistema não disponível"}
        
        # Verificar que IA é a proprietária
        proposta = self.gerenciador_propostas.obter_proposta(proposta_id)
        if not proposta:
            return {"sucesso": False, "mensagem": "Proposta não encontrada"}
        
        if proposta.get("ia_solicitante") != ia_solicitante:
            return {"sucesso": False, "mensagem": "âŒ Você não é a proprietária"}
        
        sucesso, msg = self.construtor_ferramentas.iniciar_construcao(
            proposta_id=proposta_id,
            ia_solicitante=ia_solicitante
        )
        
        return {"sucesso": sucesso, "mensagem": msg}

    # =========================================================================
    # API PÚBLICA - SOLICITAR ARQUIVOS
    # =========================================================================

    def solicitar_arquivos_para_construcao(
        self,
        proposta_id: str,
        ia_solicitante: str,
        lista_modulos: list
    ) -> Dict[str, Any]:
        """
        IA solicita módulos/bibliotecas para construir ferramenta.Args:
            proposta_id: ID da proposta
            ia_solicitante: Nome da IA
            lista_modulos: ["numpy", "pillow"]
        
        Returns:
            {
                "sucesso": bool,
                "modulos": {nome: path},
                "mensagem": str
            }
        """
        if not hasattr(self, "solicitador_arquivos"):
            return {
                "sucesso": False,
                "modulos": {},
                "mensagem": "Sistema de arquivos não disponível"
            }
        
        sucesso, modulos, msg = self.solicitador_arquivos.solicitar_arquivos(
            proposta_id=proposta_id,
            ia_solicitante=ia_solicitante,
            lista_modulos=lista_modulos,
            duracao_minutos=120
        )
        
        return {
            "sucesso": sucesso,
            "modulos": modulos,
            "mensagem": msg
        }

    def listar_arquivos_disponiveis(self) -> Dict[str, str]:
        """Lista todos os módulos que podem ser solicitados."""
        if not hasattr(self, "solicitador_arquivos"):
            return {}
        
        return self.solicitador_arquivos.listar_arquivos_disponiveis()

    # =========================================================================
    # API PÚBLICA - ANÍLISE DE SEGURANÇA
    # =========================================================================

    def analisar_seguranca_proposta(
        self,
        proposta_id: str
    ) -> Dict[str, Any]:
        """âœ… NOVO: Bot analisa segurança de proposta."""
        if not hasattr(self, "bot_seguranca"):
            return {"sucesso": False, "mensagem": "Sistema não disponível"}
        
        sucesso, msg = self.bot_seguranca.analisar_proposta(proposta_id)
        
        return {"sucesso": sucesso, "mensagem": msg}

    # =========================================================================
    # API PÚBLICA - LISTAR/OBTER STATUS
    # =========================================================================

    def listar_propostas_pendentes(self) -> Dict[str, Any]:
        """Lista propostas aguardando decisão humana."""
        if not hasattr(self, "gerenciador_propostas"):
            return {"propostas": []}
        
        propostas = self.gerenciador_propostas.listar_pendentes()
        
        return {
            "total": len(propostas),
            "propostas": [
                {
                    "id": p.get("id"),
                    "nome_ferramenta": p.get("nome_ferramenta"),
                    "ia_solicitante": p.get("ia_solicitante"),
                    "motivo": p.get("motivo"),
                    "intencao_uso": p.get("intencao_uso"),
                    "categoria": p.get("categoria")
                }
                for p in propostas
            ]
        }

    def listar_propostas_em_analise(self) -> Dict[str, Any]:
        """Lista propostas em análise posterior."""
        if not hasattr(self, "gerenciador_propostas"):
            return {"propostas": []}
        
        propostas = self.gerenciador_propostas.listar_em_analise()
        return {"total": len(propostas), "propostas": propostas}

    def listar_propostas_em_construcao(self) -> Dict[str, Any]:
        """Lista propostas em construção."""
        if not hasattr(self, "gerenciador_propostas"):
            return {"propostas": []}
        
        propostas = self.gerenciador_propostas.listar_em_construcao()
        
        return {
            "total": len(propostas),
            "propostas": [
                {
                    "id": p.get("id"),
                    "nome_ferramenta": p.get("nome_ferramenta"),
                    "status": p.get("status"),
                    "progresso": p.get("progresso_json", {})
                }
                for p in propostas
            ]
        }

    def obter_status_proposta(self, proposta_id: str) -> Dict[str, Any]:
        """Obtém status completo de uma proposta."""
        if not hasattr(self, "gerenciador_propostas"):
            return {"sucesso": False, "mensagem": "Sistema não disponível"}
        
        proposta = self.gerenciador_propostas.obter_proposta(proposta_id)
        if not proposta:
            return {"sucesso": False, "mensagem": "Proposta não encontrada"}
        
        historico = self.gerenciador_propostas.obter_historico(proposta_id)
        
        return {
            "sucesso": True,
            "proposta": {
                "id": proposta.get("id"),
                "ia_solicitante": proposta.get("ia_solicitante"),
                "nome_ferramenta": proposta.get("nome_ferramenta"),
                "descricao": proposta.get("descricao"),
                "motivo": proposta.get("motivo"),
                "intencao_uso": proposta.get("intencao_uso"),
                "status": proposta.get("status"),
                "progresso": proposta.get("progresso_json", {}),
                "testes": proposta.get("testes_json", {}),
                "seguranca": proposta.get("seguranca_json", {}),
                "deploy": proposta.get("deploy_json", {})
            },
            "historico": historico
        }

    # =========================================================================
    # SHUTDOWN
    # =========================================================================

    def _shutdown_propostas(self) -> None:
        """Desliga sistema de propostas."""
        if hasattr(self, "bot_seguranca"):
            self.bot_seguranca.shutdown()
        if hasattr(self, "construtor_ferramentas"):
            self.construtor_ferramentas.shutdown()
        if hasattr(self, "solicitador_arquivos"):
            self.solicitador_arquivos.shutdown()
        if hasattr(self, "gerenciador_propostas"):
            self.gerenciador_propostas.shutdown()


