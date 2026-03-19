from __future__ import annotations

import logging
from src.engenharia.sistema_propostas_ferramentas import GerenciadorPropostas  # Importa o gerenciador
from typing import Any, Dict, Optional, Tuple, List

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class IntegracaoProptas:
    """
    Classe para intermediar o uso do Gerenciador de Propostas de Ferramentas.
    """

    def __init__(self, coracao_ref: Any, gerenciador: GerenciadorPropostas):
        """
        Inicializa o intermedirio do gerenciador de propostas.
        :param coracao_ref: Referência ao sistema do Coração Orquestrador.
        :param gerenciador: Instncia do GerenciadorPropostas.
        """
        self.coracao = coracao_ref
        self.gerenciador_propostas = gerenciador

    def criar_proposta_ferramenta(
        self,
        nome: str,
        descricao: str,
        ia_solicitante: str,
        categoria: str,
        tipo: str,
        motivo: str,
        codigo_ou_comando: str = ""
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Cria uma nova proposta de ferramenta.
        :param nome: Nome da ferramenta proposta.
        :param descricao: Descrio da ferramenta.
        :param ia_solicitante: Identificador da IA solicitante.
        :param categoria: Categoria da ferramenta.
        :param tipo: Tipo de ferramenta (e.g., script Python, shell, etc.).
        :param motivo: Motivo ou justificativa para a proposta.
        :param codigo_ou_comando: Opcional. Cdigo ou comando associado.
        :return: Tupla (sucesso, mensagem, proposta_id).
        """
        logger.info("Solicitando nova proposta de ferramenta: %s", nome)
        sucesso, mensagem, proposta_id = self.gerenciador_propostas.criar_proposta(
            ia_solicitante=ia_solicitante,
            nome_ferramenta=nome,
            descricao=descricao,
            motivo=motivo,
            intencao_uso="Automatizar ou otimizar tarefas",
            categoria=categoria,
            tipo_ferramenta=tipo,
            codigo_ou_comando=codigo_ou_comando,
        )

        if sucesso:
            logger.info("Proposta criada com ID: %s", proposta_id)
        else:
            logger.warning("Falha ao criar proposta: %s", mensagem)

        return sucesso, mensagem, proposta_id

    def obter_status_proposta(self, proposta_id: str) -> Optional[Dict[str, Any]]:
        """
        Consulta o status de uma proposta de ferramenta.
        :param proposta_id: ID da proposta a ser consultada.
        :return: Dicionrio com dados da proposta, ou None se no encontrada.
        """
        proposta = self.gerenciador_propostas.obter_proposta(proposta_id)
        if proposta:
            logger.info("Status da proposta %s: %s", proposta_id, proposta.get("status"))
        else:
            logger.warning("Proposta %s no encontrada", proposta_id)
        return proposta

    def listar_propostas_pendentes(self) -> List[Dict[str, Any]]:
        """
        Lista todas as propostas pendentes de anlise humana.
        :return: Lista de propostas cujo status  'PENDENTE_ANALISE'.
        """
        propostas_pendentes = self.gerenciador_propostas.listar_pendentes()
        logger.info("Propostas pendentes: %d encontrada(s)", len(propostas_pendentes))
        return propostas_pendentes

    def aprovar_proposta(self, proposta_id: str, humano: str, motivo: str = "") -> Tuple[bool, str]:
        """
        Aprova uma proposta de ferramenta.
        :param proposta_id: ID da proposta a ser aprovada.
        :param humano: Identificador do humano responsvel pela aprovao.
        :param motivo: Justificativa para a aprovao.
        :return: Tupla (sucesso, mensagem).
        """
        logger.info("Aprovando proposta %s por %s", proposta_id, humano)
        sucesso, msg = self.gerenciador_propostas.aprovar_proposta(
            proposta_id=proposta_id,
            por_humano=humano,
            motivo=motivo,
        )
        if sucesso:
            logger.info("Proposta %s aprovada com sucesso.", proposta_id)
        else:
            logger.warning("Falha ao aprovar proposta %s: %s", proposta_id, msg)
        return sucesso, msg

    def rejeitar_proposta(self, proposta_id: str, humano: str, motivo: str) -> Tuple[bool, str]:
        """
        Rejeita uma proposta de ferramenta.
        :param proposta_id: ID da proposta a ser rejeitada.
        :param humano: Identificador do humano responsvel pela rejeio.
        :param motivo: Justificativa para a rejeio.
        :return: Tupla (sucesso, mensagem).
        """
        logger.info("Rejeitando proposta %s por %s", proposta_id, humano)
        sucesso, msg = self.gerenciador_propostas.rejeitar_proposta(
            proposta_id=proposta_id,
            por_humano=humano,
            motivo_rejeicao=motivo,
        )
        if sucesso:
            logger.info("Proposta %s rejeitada com sucesso.", proposta_id)
        else:
            logger.warning("Falha ao rejeitar proposta %s: %s", proposta_id, msg)
        return sucesso, msg
