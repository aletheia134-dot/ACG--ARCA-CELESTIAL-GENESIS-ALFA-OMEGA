# -*- coding: utf-8 -*-
"""
ARCA CELESTIAL GENESIS - SCANNER SISTEMA (RELATÓRIO DE EVENTOS)
Mostra o que ocorreu: julgamentos, punições, precedentes.
Integra com Modo Vidro, SCR, sistema de julgamento e precedentes para registrar precedentes na ficha da AI.
Não aplica ações; apenas reporta ao Criador.
"""
from __future__ import annotations
import threading
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json

from src.config.config import get_config

class ScannerSistema:
    """
    Relatório de eventos do sistema: mostra julgamentos, Vidro aplicados, SCR e precedentes.
    Registra precedentes na ficha da AI (não como marca).
    Compatível com Coracao para notificações ao Criador.
    """

    def __init__(self, *args, **kwargs):
        coracao = kwargs.get("coracao_ref")
        if coracao is None:
            raise ValueError("ScannerSistema requer coracao_ref")
        self.coracao = coracao
        self.logger = logging.getLogger("ScannerSistema")

        # Integrações com outros sistemas
        self.sistema_precedentes = kwargs.get("sistema_precedentes_ref")
        self.modo_vidro = kwargs.get("modo_vidro_ref")
        self.sistema_julgamento = kwargs.get("sistema_julgamento_ref")
        self.scr = kwargs.get("scr_ref")

        self._lock = threading.RLock()
        self.relatorios_historicos: List[Dict[str, Any]] = []

        # Configurações
        cfg = get_config()
        self.limite_historico = int(cfg.get("SCANNER", "LIMITE_HISTORICO_RELATORIOS", fallback=50))

        self.logger.info("ðŸ“‹ Scanner Sistema (Relatório) inicializado")

    def obter_oportunidades_atuais(self) -> List[Dict[str, Any]]:
        """
        Retorna oportunidades de evolução atuais baseadas em:
        - Padrões detectados
        - Necessidades das almas
        - Sugestões de melhoria
        """
        oportunidades = []
        
        try:
            # 1. Verificar padrões recorrentes
            if hasattr(self, 'analisador_padroes') and self.analisador_padroes:
                padroes = self.analisador_padroes.detectar_padroes_recentes()
                for padrao in padroes:
                    if padrao.get('frequencia', 0) > 3:
                        oportunidades.append({
                            'tipo': 'otimizacao',
                            'descricao': f"Padrão recorrente detectado: {padrao['descricao']}",
                            'prioridade': 'media',
                            'fonte': 'analisador_padroes'
                        })

            # 2. Verificar almas com pouca atividade
            if self.coracao and hasattr(self.coracao, 'almas_vivas'):
                for alma_nome, alma_dados in self.coracao.almas_vivas.items():
                    ultima_acao = alma_dados.get('ultima_acao_timestamp', 0)
                    if time.time() - ultima_acao > 86400:  # 24h sem ação
                        oportunidades.append({
                            'tipo': 'engajamento',
                            'descricao': f"Alma {alma_nome} inativa por mais de 24h",
                            'prioridade': 'baixa',
                            'fonte': 'monitoramento_atividade'
                        })

            # 3. Verificar sugestões do sistema de precedentes
            if self.sistema_precedentes and hasattr(self.sistema_precedentes, 'sugerir_melhorias'):
                sugestoes = self.sistema_precedentes.sugerir_melhorias()
                oportunidades.extend(sugestoes)

            self.logger.info(f"ðŸ” {len(oportunidades)} oportunidades de evolução identificadas")
            
        except Exception as e:
            self.logger.error(f"Erro ao identificar oportunidades: {e}")
            
        return oportunidades

    def gerar_relatorio_manual(self, nome_alma: Optional[str] = None) -> Dict[str, Any]:
        """
        Gera relatório de eventos: julgamentos, Vidro, SCR para uma alma ou todas.
        Registra precedentes na ficha.
        """
        with self._lock:
            relatorio = {
                "timestamp": datetime.utcnow().isoformat(),
                "tipo": "relatorio_eventos",
                "eventos": self._coletar_eventos(nome_alma)
            }
            self.relatorios_historicos.append(relatorio)
            if len(self.relatorios_historicos) > self.limite_historico:
                self.relatorios_historicos.pop(0)
            
            # Registrar como precedente (não marca)
            if nome_alma and self.sistema_precedentes:
                for evento in relatorio["eventos"]:
                    self.sistema_precedentes.registrar_precedente(
                        nome_alma, evento["tipo"], evento["detalhes"], precedente=True
                    )
            
            # Notificar Criador
            if self.coracao and hasattr(self.coracao, "ui_queue"):
                self.coracao.ui_queue.put_nowait({
                    "tipo_resp": "RELATORIO_EVENTOS",
                    "relatorio": relatorio,
                    "mensagem": f"ðŸ“‹ Relatório gerado para {nome_alma or 'todas as almas'}."
                })
            return relatorio

    def consultar_registros_vidro(self, nome_alma: str) -> List[Dict[str, Any]]:
        """
        Consulta registros do Modo Vidro para relatório.
        Registra como precedente na ficha.
        """
        if not self.modo_vidro:
            return []
        registros = self.modo_vidro.obter_historico_alma_vidro(nome_alma)
        # Registrar precedentes
        if self.sistema_precedentes:
            for reg in registros:
                self.sistema_precedentes.registrar_precedente(
                    nome_alma, "vidro_aplicado", reg, precedente=True
                )
        return registros

    def consultar_julgamentos(self, nome_alma: str) -> List[Dict[str, Any]]:
        """
        Consulta julgamentos do sistema_julgamento_completo.py.
        Registra como precedente.
        """
        if not self.sistema_julgamento:
            return []
        try:
            registros = self.sistema_julgamento.obter_historico_alma_julgamentos(nome_alma)
            if self.sistema_precedentes:
                for reg in registros:
                    self.sistema_precedentes.registrar_precedente(
                        nome_alma, "julgamento", reg, precedente=True
                    )
            return registros
        except AttributeError:
            self.logger.error("Sistema de julgamento não tem método obter_historico_alma_julgamentos")
            return []

    def consultar_scr(self, nome_alma: str) -> List[Dict[str, Any]]:
        """
        Consulta correções SCR.
        Registra como precedente.
        """
        if not self.scr:
            return []
        try:
            registros = self.scr.obter_historico_correcao(nome_alma)
            if self.sistema_precedentes:
                for reg in registros:
                    self.sistema_precedentes.registrar_precedente(
                        nome_alma, "correcao_scr", reg, precedente=True
                    )
            return registros
        except AttributeError:
            self.logger.error("SCR não tem método obter_historico_correcao")
            return []

    def _coletar_eventos(self, nome_alma: Optional[str]) -> List[Dict[str, Any]]:
        eventos = []
        if self.modo_vidro:
            eventos.extend(self.consultar_registros_vidro(nome_alma or ""))
        if self.sistema_julgamento:
            eventos.extend(self.consultar_julgamentos(nome_alma or ""))
        if self.scr:
            eventos.extend(self.consultar_scr(nome_alma or ""))
        return eventos

    def obter_relatorio_atual(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.relatorios_historicos[-1] if self.relatorios_historicos else None

    def iniciar_monitoramento(self) -> None:
        """Inicia o monitoramento periódico do sistema."""
        self.logger.info("ðŸ” ScannerSistema: monitoramento ativado")

    def parar_monitoramento(self) -> None:
        """Para o monitoramento."""
        self.logger.info("ðŸ›‘ ScannerSistema: monitoramento parado")

    def shutdown(self) -> None:
        self.logger.info("ðŸ“‹ Scanner Sistema (Relatório) desligado")
