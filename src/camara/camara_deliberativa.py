from __future__ import annotations
import threading
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json

from src.config.config import get_config

logger = logging.getLogger("CamaraDeliberativa")

class ScannerSistema:
    """
    Implementao base que fornece operações reais de coleta e relatrio.
    """
    def __init__(
        self,
        *,
        coracao_ref: Any = None,
        sistema_precedentes_ref: Any = None,
        modo_vidro_ref: Any = None,
        sistema_julgamento_ref: Any = None,
        scr_ref: Any = None,
        limite_historico: Optional[int] = None,
    ):
        self.coracao = coracao_ref
        self.logger = logging.getLogger("ScannerSistema")

        self.sistema_precedentes = sistema_precedentes_ref
        self.modo_vidro = modo_vidro_ref
        self.sistema_julgamento = sistema_julgamento_ref
        self.scr = scr_ref

        self._lock = threading.RLock()
        self.relatorios_historicos: List[Dict[str, Any]] = []

        if limite_historico is None:
            try:
                cfg = get_config()
                limite_historico = int(cfg.get("SCANNER", "LIMITE_HISTORICO_RELATORIOS", fallback=50))
            except Exception:
                limite_historico = 50
        self.limite_historico = limite_historico

        self.logger.info(" Scanner Sistema (Relatrio) inicializado (limite=%s)", self.limite_historico)

    def gerar_relatorio_manual(self, nome_alma: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            relatorio = {
                "timestamp": datetime.utcnow().isoformat(),
                "tipo": "relatorio_eventos",
                "eventos": self._coletar_eventos(nome_alma)
            }
            self.relatorios_historicos.append(relatorio)
            if len(self.relatorios_historicos) > self.limite_historico:
                self.relatorios_historicos.pop(0)

            if nome_alma and self.sistema_precedentes:
                for evento in relatorio["eventos"]:
                    try:
                        self.sistema_precedentes.registrar_precedente(
                            nome_alma, evento.get("tipo"), evento.get("detalhes"), precedente=True
                        )
                    except Exception:
                        self.logger.exception("Falha ao registrar precedente para %s", nome_alma)

            if self.coracao and hasattr(self.coracao, "ui_queue") and self.coracao.ui_queue is not None:
                try:
                    self.coracao.ui_queue.put_nowait({
                        "tipo_resp": "RELATORIO_EVENTOS",
                        "relatorio": relatorio,
                        "mensagem": f" Relatrio gerado para {nome_alma or 'todas as almas'}."
                    })
                except Exception:
                    self.logger.exception("Falha ao enviar relatrio para UI queue")

            return relatorio

    def consultar_registros_vidro(self, nome_alma: str) -> List[Dict[str, Any]]:
        if not self.modo_vidro:
            return []
        try:
            registros = self.modo_vidro.obter_historico_alma_vidro(nome_alma)
        except Exception:
            self.logger.exception("Falha ao consultar registros vidro")
            return []
        if self.sistema_precedentes and registros:
            for reg in registros:
                try:
                    self.sistema_precedentes.registrar_precedente(nome_alma, "vidro_aplicado", reg, precedente=True)
                except Exception:
                    self.logger.exception("Falha ao registrar precedente vidro")
        return registros

    def consultar_julgamentos(self, nome_alma: str) -> List[Dict[str, Any]]:
        if not self.sistema_julgamento:
            return []
        try:
            registros = self.sistema_julgamento.obter_historico_alma_julgamentos(nome_alma)
        except Exception:
            self.logger.debug("Sistema de julgamento no tem método de histórico ou falhou")
            return []
        if self.sistema_precedentes:
            for reg in registros:
                try:
                    self.sistema_precedentes.registrar_precedente(nome_alma, "julgamento", reg, precedente=True)
                except Exception:
                    self.logger.exception("Falha ao registrar precedente julgamentos")
        return registros

    def consultar_scr(self, nome_alma: str) -> List[Dict[str, Any]]:
        if not self.scr:
            return []
        try:
            registros = self.scr.obter_historico_correcao(nome_alma)
        except Exception:
            self.logger.debug("SCR no tem método de histórico ou falhou")
            return []
        if self.sistema_precedentes:
            for reg in registros:
                try:
                    self.sistema_precedentes.registrar_precedente(nome_alma, "correcao_scr", reg, precedente=True)
                except Exception:
                    self.logger.exception("Falha ao registrar precedente SCR")
        return registros

    def _coletar_eventos(self, nome_alma: Optional[str]) -> List[Dict[str, Any]]:
        eventos: List[Dict[str, Any]] = []
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

    def shutdown(self) -> None:
        self.logger.info(" Scanner Sistema (Relatrio) desligado")


class CamaraDeliberativa(ScannerSistema):
    """
    Implementao real de CamaraDeliberativa, compatvel com o restante do sistema.
    """
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        coracao_ref: Any = None,
        biblioteca_ref: Any = None,
        camara_legislativa_ref: Any = None,
        modo_vidro_ref: Any = None,
        sistema_precedentes_ref: Any = None,
        sistema_julgamento_ref: Any = None,
        scr_ref: Any = None,
        enable_periodic_scan: bool = False,
        scan_interval_sec: int = 3600,
    ):
        limite = None
        try:
            if config and isinstance(config, dict):
                limite = int(config.get("SCANNER_LIMITE_HISTORICO", limite or 50))
        except Exception:
            limite = limite or 50

        super().__init__(
            coracao_ref=coracao_ref,
            sistema_precedentes_ref=sistema_precedentes_ref,
            modo_vidro_ref=modo_vidro_ref,
            sistema_julgamento_ref=sistema_julgamento_ref,
            scr_ref=scr_ref,
            limite_historico=limite,
        )

        self.config = config or {}
        self.biblioteca = biblioteca_ref
        self.camara_legislativa = camara_legislativa_ref

        self._periodic_thread: Optional[threading.Thread] = None
        self._periodic_stop = threading.Event()
        self.scan_interval_sec = max(1, int(scan_interval_sec))
        self.enable_periodic_scan = bool(enable_periodic_scan)

        if self.enable_periodic_scan:
            self.start_periodic_scan()

        self.logger = logging.getLogger("CamaraDeliberativa")
        self.logger.info("CamaraDeliberativa inicializada (enable_periodic_scan=%s, interval=%s)",
                         self.enable_periodic_scan, self.scan_interval_sec)

    def start_periodic_scan(self):
        if self._periodic_thread and self._periodic_thread.is_alive():
            return
        self._periodic_stop.clear()
        self._periodic_thread = threading.Thread(target=self._periodic_worker, name="CamaraDeliberativa-Scanner", daemon=True)
        self._periodic_thread.start()
        self.logger.debug("Periodic scan thread started")

    def stop_periodic_scan(self):
        if not self._periodic_thread:
            return
        self._periodic_stop.set()
        self._periodic_thread.join(timeout=5)
        self._periodic_thread = None
        self.logger.debug("Periodic scan thread stopped")

    def _periodic_worker(self):
        self.logger.info("Periodic scanner running (interval %s s)", self.scan_interval_sec)
        while not self._periodic_stop.wait(self.scan_interval_sec):
            try:
                self.logger.debug("Periodic scan: gerando relatrio automático")
                self.gerar_relatorio_manual(None)
            except Exception:
                self.logger.exception("Erro durante periodic scan")

    def injetar_ui_queue(self, fila_ui: Any):
        if self.coracao is None:
            self.coracao = type("CoracaoStub", (), {})()
        setattr(self.coracao, "ui_queue", fila_ui)
        self.logger.info("Fila UI injetada na CamaraDeliberativa")

    def injetar_consulado(self, instancia_consulado: Any):
        self.consulado = instancia_consulado
        self.logger.info("Consulado injetado na CamaraDeliberativa")

    def shutdown(self) -> None:
        try:
            self.stop_periodic_scan()
        except Exception:
            self.logger.exception("Erro ao parar periodic scan")
        super().shutdown()
