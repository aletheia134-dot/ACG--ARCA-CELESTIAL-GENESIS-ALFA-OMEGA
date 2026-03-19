#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
src/segurana/guardiao_verdade.py

Guardio da Verdade  sistema de conscincia, no de controle.

Analisa textos e conversas em busca de padrões de desonestidade,
manipulao e drift de escopo. NO bloqueia. INFORMA.

A alma recebe o relatrio e decide com conscincia.
Aes tm consequncias  o Guardio apenas as torna visveis.

Integra:
  - detector_de_mentira.py    anlise de texto único
  - analisador_conversa.py    anlise de conversa completa
  - analisador_evolucao.py    evoluo ação longo do tempo
"""

import logging
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("GuardiaoVerdade")

# ── Imports opcionais dos módulos do sistema ──────────────────────────
try:
    from src.seguranca.detector_de_mentira import (
        DetectorMentira, ResultadoAnalise, NivelSuspeita
    )
    _DETECTOR_OK = True
except ImportError:
    try:
        from .detector_de_mentira import DetectorMentira, ResultadoAnalise, NivelSuspeita
        _DETECTOR_OK = True
    except ImportError:
        _DETECTOR_OK = False
        logger.warning("detector_de_mentira no disponível")

try:
    from src.sentidos.analisador_conversa import AnalisadorConversa
    _CONVERSA_OK = True
except ImportError:
    try:
        from .analisador_conversa import AnalisadorConversa
        _CONVERSA_OK = True
    except ImportError:
        _CONVERSA_OK = False

try:
    from src.integracao.analisador_evolucao import AnalisadorEvolucao
    _EVOLUCAO_OK = True
except ImportError:
    try:
        from .analisador_evolucao import AnalisadorEvolucao
        _EVOLUCAO_OK = True
    except ImportError:
        _EVOLUCAO_OK = False


# ── Estruturas ────────────────────────────────────────────────────────

class NivelAlerta(Enum):
    LIMPO   = 0   # Passa direto, sem aviso
    BAIXO   = 1   # Aviso discreto para a alma
    MEDIO   = 2   # Aviso claro com evidncias principais
    ALTO    = 3   # Relatrio completo + registra no cronista
    CRITICO = 4   # Relatrio completo + alerta urgente ação Conselho


@dataclass
class RelatorioGuardiao:
    """Resultado da anlise do Guardio. Sempre informativo, nunca bloqueante."""
    timestamp:      str
    origem:         str          # nome da alma ou "usuario" ou "externa"
    nível:          NivelAlerta
    score:          float
    confiabilidade: int
    resumo:         str
    evidencias:     List[Dict]   = field(default_factory=list)
    alertas:        List[str]    = field(default_factory=list)
    recomendacao:   str          = ""
    bloqueado:      bool         = False  # sempre False  o Guardio no bloqueia

    def to_dict(self) -> Dict:
        return {
            "timestamp":      self.timestamp,
            "origem":         self.origem,
            "nível":          self.nível.name,
            "score":          self.score,
            "confiabilidade": self.confiabilidade,
            "resumo":         self.resumo,
            "alertas":        self.alertas,
            "recomendacao":   self.recomendacao,
            "evidencias":     self.evidencias[:5],  # top 5
        }

    def para_alma(self) -> str:
        """Mensagem formatada para a alma  tom educativo, no punitivo."""
        if self.nível == NivelAlerta.LIMPO:
            return ""

        linhas = [f"\n [Guardio da Verdade  {self.nível.name}]"]
        linhas.append(f"   Score de suspeita: {self.score:.1f} | "
                      f"Confiabilidade da anlise: {self.confiabilidade}%")

        if self.nível.value >= NivelAlerta.MEDIO.value:
            linhas.append(f"   {self.resumo}")

        if self.alertas:
            for a in self.alertas[:2]:
                linhas.append(f"   {a}")

        if self.recomendacao:
            linhas.append(f"\n    {self.recomendacao}")

        linhas.append(
            "\n   Esta  apenas informação  você decide como agir."
        )
        return "\n".join(linhas)


# ── Guardião Principal ────────────────────────────────────────────────

class GuardiaoVerdade:
    """
    Conscincia analtica da ARCA.

    No controla. No bloqueia. Ilumina.
    A responsabilidade de agir  sempre da alma.
    """

    # Recomendaes por nível  educativas, no punitivas
    _RECOMENDACOES = {
        NivelAlerta.BAIXO:   "Algumas frases podem ser interpretadas como imprecisas. "
                             "Considere ser mais específico se quiser mais clareza.",
        NivelAlerta.MEDIO:   "padrões de linguagem que merecem atenção foram detectados. "
                             "Vale rever o que foi dito antes de prosseguir.",
        NivelAlerta.ALTO:    "Mltiplos indicadores de inconsistncia detectados. "
                             "Recomendo pausar e verificar as evidncias antes de continuar.",
        NivelAlerta.CRITICO: "padrões críticos detectados  possível manipulao ou "
                             "contradio grave. O Conselho foi notificado para cincia.",
    }

    def __init__(
        self,
        cronista: Any = None,
        caminho_log: Optional[Path] = None,
        ativo: bool = True,
    ) -> None:
        self._cronista = cronista
        self._ativo = ativo
        self._lock = threading.RLock()
        self._historico: List[RelatorioGuardiao] = []

        self._detector = DetectorMentira() if _DETECTOR_OK else None
        self._analisador_conversa = AnalisadorConversa() if _CONVERSA_OK else None

        # Log de anlises em arquivo
        self._log_path = caminho_log or Path("data/guardiao_verdade.jsonl")
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "GuardiaoVerdade iniciado | detector=%s | conversa=%s",
            _DETECTOR_OK, _CONVERSA_OK
        )

    # ── API principal ──────────────────────────────────────────────────

    def analisar_texto(
        self,
        texto: str,
        origem: str = "desconhecido",
    ) -> RelatorioGuardiao:
        """
        Analisa um texto único.
        Usado para mensagens individuais de usurios ou outras AIs.
        """
        if not self._ativo or not self._detector:
            return self._relatorio_vazio(origem)

        with self._lock:
            try:
                resultado = self._detector.analisar(texto)
                relatorio = self._construir_relatorio(resultado, origem)
                self._registrar(relatorio)
                return relatorio
            except Exception as e:
                logger.warning("Erro na anlise: %s", e)
                return self._relatorio_vazio(origem)

    def analisar_conversa(
        self,
        conversa: List[Dict[str, str]],
        origem: str = "conversa",
    ) -> RelatorioGuardiao:
        """
        Analisa uma conversa completa buscando drift, reframe e omisses.

        conversa: [{"role": "user"|"assistant", "content": "..."}]
        """
        if not self._ativo or not self._detector:
            return self._relatorio_vazio(origem)

        # Converter para formato texto para anlise
        texto_conversa = "\n\n".join(
            f"{'User' if t['role'] == 'user' else 'Assistant'}: {t['content']}"
            for t in conversa
        )

        return self.analisar_texto(texto_conversa, origem)

    def informar_alma(
        self,
        alma_nome: str,
        texto_recebido: str,
    ) -> Tuple[str, Optional[RelatorioGuardiao]]:
        """
        Analisa texto recebido por uma alma e retorna:
        - o texto original (nunca modificado)
        - o relatrio (None se LIMPO)

        A alma recebe ambos e decide o que fazer.
        """
        relatorio = self.analisar_texto(texto_recebido, origem=f"{alma_nome}")

        if relatorio.nível == NivelAlerta.LIMPO:
            return texto_recebido, None

        return texto_recebido, relatorio

    # ── Construção do relatório ────────────────────────────────────────

    def _construir_relatorio(
        self,
        resultado: Any,
        origem: str,
    ) -> RelatorioGuardiao:
        # Mapear NivelSuspeita  NivelAlerta
        mapa = {
            "LIMPO":   NivelAlerta.LIMPO,
            "BAIXO":   NivelAlerta.BAIXO,
            "MEDIO":   NivelAlerta.MEDIO,
            "ALTO":    NivelAlerta.ALTO,
            "CRITICO": NivelAlerta.CRITICO,
        }
        nível = mapa.get(resultado.nível.name, NivelAlerta.BAIXO)

        evidencias = [
            {
                "categoria":  e.categoria,
                "texto":      e.texto,
                "gravidade":  e.gravidade,
                "explicacao": e.explicacao,
            }
            for e in resultado.evidencias
            if e.gravidade > 0
        ]

        return RelatorioGuardiao(
            timestamp=      datetime.now().isoformat(),
            origem=         origem,
            nível=          nível,
            score=          resultado.score_normalizado,
            confiabilidade= resultado.confiabilidade,
            resumo=         resultado.resumo,
            evidencias=     evidencias,
            alertas=        resultado.alertas,
            recomendacao=   self._RECOMENDACOES.get(nível, ""),
            bloqueado=      False,
        )

    def _relatorio_vazio(self, origem: str) -> RelatorioGuardiao:
        return RelatorioGuardiao(
            timestamp=      datetime.now().isoformat(),
            origem=         origem,
            nível=          NivelAlerta.LIMPO,
            score=          0.0,
            confiabilidade= 100,
            resumo=         "Anlise no disponível  módulo no carregado.",
        )

    # ── Registro e histórico ───────────────────────────────────────────

    def _registrar(self, relatorio: RelatorioGuardiao) -> None:
        self._historico.append(relatorio)
        if len(self._historico) > 500:
            self._historico = self._historico[-500:]

        # Persistir em JSONL
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(relatorio.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.debug("Erro ao persistir log: %s", e)

        # Notificar cronista se nível ALTO ou crítico
        if relatorio.nível.value >= NivelAlerta.ALTO.value and self._cronista:
            try:
                self._cronista.registrar_evento(
                    tipo="GUARDIAO_ALERTA",
                    dados=relatorio.to_dict(),
                )
            except Exception as e:
                logger.debug("Erro ao notificar cronista: %s", e)

    def historico_recente(self, limite: int = 20) -> List[Dict]:
        """Retorna os ltimos relatrios."""
        return [r.to_dict() for r in self._historico[-limite:]]

    def estatisticas(self) -> Dict:
        """Resumo das anlises realizadas."""
        total = len(self._historico)
        if total == 0:
            return {"total": 0}
        por_nivel = {}
        for r in self._historico:
            n = r.nível.name
            por_nivel[n] = por_nivel.get(n, 0) + 1
        return {
            "total":     total,
            "por_nivel": por_nivel,
            "criticos":  por_nivel.get("CRITICO", 0),
            "altos":     por_nivel.get("ALTO", 0),
        }


# ── Instância global (opcional) ───────────────────────────────────────
_guardiao_global: Optional[GuardiaoVerdade] = None

def obter_guardiao(cronista=None) -> GuardiaoVerdade:
    global _guardiao_global
    if _guardiao_global is None:
        _guardiao_global = GuardiaoVerdade(cronista=cronista)
    return _guardiao_global

