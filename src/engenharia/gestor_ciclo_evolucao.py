#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
gestor_ciclo_evolucao.py - Coordena Ciclo Semanal de Evoluo

Orquestra todo processo:
1.Scanner roda (segunda-feira)
2.Lista atualizada
3.IAs escolhem
4.Semana seguinte, repetir

Responsabilidades:
- Coordenar Scanner + Lista
- Agendar próximo scan
- Notificar IAs
- Rastrear evoluo
"""


import datetime
import logging
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class GestorCicloEvolucao:
    """
    Coordena ciclo semanal de evoluo da ARCA.Fluxo:
    1.Agendador detecta segunda-feira (ou intervalo configurado)
    2.Scanner executa
    3.Lista  atualizada
    4.IAs veem oportunidades
    5.IAs aceitam/recusam
    6.Aguarda prxima semana
    """

    def __init__(
        self,
        coracao_ref: Any,
        scanner_ref: Any,
        lista_evolucao_ref: Any
    ):
        """
        Args:
            coracao_ref: Ref ação Corao
            scanner_ref: Ref ação ScannerSistema
            lista_evolucao_ref: Ref ação ListaEvolucaoIA
        """
        self.coracao = coracao_ref
        self.scanner = scanner_ref
        self.lista_evolucao = lista_evolucao_ref
        self.logger = logging.getLogger("GestorCicloEvolucao")
        
        self._monitorando = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # histórico de ciclos
        self.ciclos_completos = 0
        self.proxima_execucao: Optional[datetime.datetime] = None

    def iniciar(self) -> None:
        """Inicia gestor de ciclos."""
        if self._monitorando:
            return
        
        self._monitorando = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop_ciclos,
            daemon=True,
            name="GestorEvolucao"
        )
        self._thread.start()
        self.logger.info("[OK] Gestor de Ciclo de Evoluo iniciado (semanal)")

    def parar(self) -> None:
        """Para gestor."""
        if not self._monitorando:
            return
        
        self._monitorando = False
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        self.logger.info(" Gestor de Ciclo parado")

    def _loop_ciclos(self) -> None:
        """Loop principal que coordena ciclos."""
        self.logger.debug("Loop de ciclos iniciado")
        
        while self._monitorando and not self._stop_event.is_set():
            try:
                agora = datetime.datetime.utcnow()
                
                # Calcular prxima execução (segunda-feira 00:00 UTC)
                if self.proxima_execucao is None:
                    # Primeira execução: agora
                    self.proxima_execucao = agora
                
                # Verificar se chegou a hora
                if agora >= self.proxima_execucao:
                    self._executar_ciclo()
                    
                    # Agendar próximo ciclo (7 dias depois)
                    self.proxima_execucao = agora + datetime.timedelta(days=7)
                    self.logger.info(" Próximo ciclo agendado para: %s", self.proxima_execucao.isoformat())
                
                # Aguardar 1 hora antes de checar novamente
                if self._stop_event.wait(timeout=3600):
                    break
                    
            except Exception as e:
                self.logger.exception("Erro no loop de ciclos: %s", e)
                if self._stop_event.wait(timeout=300):
                    break
        
        self.logger.debug("Loop de ciclos finalizado")

    def _executar_ciclo(self) -> None:
        """Executa um ciclo completo de evoluo."""
        self.logger.info(" INICIANDO CICLO DE EVOLUO #%d", self.ciclos_completos + 1)
        
        try:
            # 1.Scanner executa
            self.logger.info("  [1/2] Executando scan do sistema...")
            oportunidades = self.scanner.obter_oportunidades_atuais()
            
            if not oportunidades:
                self.logger.warning("  [AVISO] Nenhuma oportunidade detectada")
            else:
                self.logger.info("  [OK] %d oportunidades detectadas", len(oportunidades))
            
            # 2.Atualizar lista
            self.logger.info("  [2/2] Atualizando lista para IAs...")
            self.lista_evolucao.atualizar_lista(oportunidades)
            
            # Registrar ciclo completo
            with self._lock:
                self.ciclos_completos += 1
            
            # Notificar
            self._notificar_ciclo_completo(oportunidades)
            
            self.logger.info("[OK] CICLO #%d CONCLUDO", self.ciclos_completos)
            self.logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            self.logger.info("Oportunidades disponíveis para IAs escolherem:")
            for i, op in enumerate(oportunidades, 1):
                self.logger.info("  %d. %s [%s] - %s", 
                               i, op.get("nome"), op.get("impacto"), op.get("motivo"))
            self.logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
        except Exception as e:
            self.logger.exception("Erro ao executar ciclo: %s", e)

    def _notificar_ciclo_completo(self, oportunidades: list) -> None:
        """Notifica Corao que ciclo foi concludo."""
        try:
            if hasattr(self.coracao, "ui_queue"):
                self.coracao.ui_queue.put_nowait({
                    "tipo_resp": "CICLO_EVOLUCAO_COMPLETO",
                    "ciclo_numero": self.ciclos_completos,
                    "oportunidades": oportunidades,
                    "timestamp": datetime.datetime.utcnow().isoformat()
                })
        except Exception as e:
            self.logger.debug("Erro ao notificar: %s", e)

    def obter_status(self) -> Dict[str, Any]:
        """Retorna status do gestor."""
        with self._lock:
            return {
                "ativo": self._monitorando,
                "ciclos_completos": self.ciclos_completos,
                "proxima_execucao": self.proxima_execucao.isoformat() if self.proxima_execucao else None,
                "oportunidades_atuais": len(self.lista_evolucao.oportunidades_atuais)
            }

    def shutdown(self) -> None:
        """Desliga."""
        self.parar()
        self.logger.info("[OK] GestorCicloEvolucao desligado")


