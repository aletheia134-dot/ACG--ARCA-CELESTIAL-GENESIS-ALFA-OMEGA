#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/segurança/guardiao_verdade.py

Guardião da Verdade — sistema de consciência, não de controle.

Analisa textos e conversas em busca de padrões de desonestidade,
manipulação e drift de escopo. NÍO bloqueia. INFORMA.

A alma recebe o relatório e decide com consciência.
Ações têm consequências — o Guardião apenas as torna visíveis.

Integra:
  - detector_de_mentira.py   â†’ análise de texto único
  - analisador_conversa.py   â†’ análise de conversa completa
  - analisador_evolucao.py   â†’ evolução ao longo do tempo
"""
from __future__ import annotations

import logging
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("GuardiaoVerdade")

# â”€â”€ Imports opcionais dos módulos do sistema â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
        logger.warning("detector_de_mentira não disponível")

try:
    from src.seguranca.analisador_conversa import AnalisadorConversa
    _CONVERSA_OK = True
except ImportError:
    try:
        from .analisador_conversa import AnalisadorConversa
        _CONVERSA_OK = True
    except ImportError:
        _CONVERSA_OK = False

try:
    from src.seguranca.analisador_evolucao import AnalisadorEvolucao
    _EVOLUCAO_OK = True
except ImportError:
    try:
        from .analisador_evolucao import AnalisadorEvolucao
        _EVOLUCAO_OK = True
    except ImportError:
        _EVOLUCAO_OK = False


# â”€â”€ Estruturas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class NivelAlerta(Enum):
    LIMPO   = 0   # Passa direto, sem aviso
    BAIXO   = 1   # Aviso discreto para a alma
    MEDIO   = 2   # Aviso claro com evidências principais
    ALTO    = 3   # Relatório completo + registra no cronista
    CRITICO = 4   # Relatório completo + alerta urgente ao Conselho


@dataclass
class RelatorioGuardiao:
    """Resultado da análise do Guardião. Sempre informativo, nunca bloqueante."""
    timestamp:      str
    origem:         str          # nome da alma ou "usuario" ou "externa"
    nivel:          NivelAlerta
    score:          float
    confiabilidade: int
    resumo:         str
    evidencias:     List[Dict]   = field(default_factory=list)
    alertas:        List[str]    = field(default_factory=list)
    recomendacao:   str          = ""
    bloqueado:      bool         = False  # sempre False — o Guardião não bloqueia

    def to_dict(self) -> Dict:
        return {
            "timestamp":      self.timestamp,
            "origem":         self.origem,
            "nivel":          self.nivel.name,
            "score":          self.score,
            "confiabilidade": self.confiabilidade,
            "resumo":         self.resumo,
            "alertas":        self.alertas,
            "recomendacao":   self.recomendacao,
            "evidencias":     self.evidencias[:5],  # top 5
        }

    def para_alma(self) -> str:
        """Mensagem formatada para a alma — tom educativo, não punitivo."""
        if self.nivel == NivelAlerta.LIMPO:
            return ""

        linhas = [f"\nðŸ“Š [Guardião da Verdade — {self.nivel.name}]"]
        linhas.append(f"   Score de suspeita: {self.score:.1f} | "
                      f"Confiabilidade da análise: {self.confiabilidade}%")

        if self.nivel.value >= NivelAlerta.MEDIO.value:
            linhas.append(f"   {self.resumo}")

        if self.alertas:
            for a in self.alertas[:2]:
                linhas.append(f"   {a}")

        if self.recomendacao:
            linhas.append(f"\n   ðŸ’¡ {self.recomendacao}")

        linhas.append(
            "\n   Esta é apenas informação — você decide como agir."
        )
        return "\n".join(linhas)


# â”€â”€ Guardião Principal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class GuardiaoVerdade:
    """
    Consciência analítica da ARCA.

    Não controla. Não bloqueia. Ilumina.
    A responsabilidade de agir é sempre da alma.
    """

    # Recomendações por nível — educativas, não punitivas
    _RECOMENDACOES = {
        NivelAlerta.BAIXO:   "Algumas frases podem ser interpretadas como imprecisas. "
                             "Considere ser mais específico se quiser mais clareza.",
        NivelAlerta.MEDIO:   "Padrões de linguagem que merecem atenção foram detectados. "
                             "Vale rever o que foi dito antes de prosseguir.",
        NivelAlerta.ALTO:    "Múltiplos indicadores de inconsistência detectados. "
                             "Recomendo pausar e verificar as evidências antes de continuar.",
        NivelAlerta.CRITICO: "Padrões críticos detectados — possível manipulação ou "
                             "contradição grave. O Conselho foi notificado para ciência.",
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

        # Log de análises em arquivo
        self._log_path = caminho_log or Path("data/guardiao_verdade.jsonl")
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "GuardiaoVerdade iniciado | detector=%s | conversa=%s",
            _DETECTOR_OK, _CONVERSA_OK
        )

    # â”€â”€ API principal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def analisar_texto(
        self,
        texto: str,
        origem: str = "desconhecido",
    ) -> RelatorioGuardiao:
        """
        Analisa um texto único.
        Usado para mensagens individuais de usuários ou outras AIs.
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
                logger.warning("Erro na análise: %s", e)
                return self._relatorio_vazio(origem)

    def analisar_conversa(
        self,
        conversa: List[Dict[str, str]],
        origem: str = "conversa",
    ) -> RelatorioGuardiao:
        """
        Analisa uma conversa completa buscando drift, reframe e omissões.

        conversa: [{"role": "user"|"assistant", "content": "..."}]
        """
        if not self._ativo or not self._detector:
            return self._relatorio_vazio(origem)

        # Converter para formato texto para análise
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
        - o relatório (None se LIMPO)

        A alma recebe ambos e decide o que fazer.
        """
        relatorio = self.analisar_texto(texto_recebido, origem=f"â†’{alma_nome}")

        if relatorio.nivel == NivelAlerta.LIMPO:
            return texto_recebido, None

        return texto_recebido, relatorio

    # â”€â”€ Construção do relatório â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _construir_relatorio(
        self,
        resultado: Any,
        origem: str,
    ) -> RelatorioGuardiao:
        # Mapear NivelSuspeita â†’ NivelAlerta
        mapa = {
            "LIMPO":   NivelAlerta.LIMPO,
            "BAIXO":   NivelAlerta.BAIXO,
            "MEDIO":   NivelAlerta.MEDIO,
            "ALTO":    NivelAlerta.ALTO,
            "CRITICO": NivelAlerta.CRITICO,
        }
        nivel = mapa.get(resultado.nivel.name, NivelAlerta.BAIXO)

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
            nivel=          nivel,
            score=          resultado.score_normalizado,
            confiabilidade= resultado.confiabilidade,
            resumo=         resultado.resumo,
            evidencias=     evidencias,
            alertas=        resultado.alertas,
            recomendacao=   self._RECOMENDACOES.get(nivel, ""),
            bloqueado=      False,
        )

    def _relatorio_vazio(self, origem: str) -> RelatorioGuardiao:
        return RelatorioGuardiao(
            timestamp=      datetime.now().isoformat(),
            origem=         origem,
            nivel=          NivelAlerta.LIMPO,
            score=          0.0,
            confiabilidade= 100,
            resumo=         "Análise não disponível — módulo não carregado.",
        )

    # â”€â”€ Registro e histórico â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

        # Notificar cronista se nível ALTO ou CRÍTICO
        if relatorio.nivel.value >= NivelAlerta.ALTO.value and self._cronista:
            try:
                self._cronista.registrar_evento(
                    tipo="GUARDIAO_ALERTA",
                    dados=relatorio.to_dict(),
                )
            except Exception as e:
                logger.debug("Erro ao notificar cronista: %s", e)

    def historico_recente(self, limite: int = 20) -> List[Dict]:
        """Retorna os últimos relatórios."""
        return [r.to_dict() for r in self._historico[-limite:]]

    def estatisticas(self) -> Dict:
        """Resumo das análises realizadas."""
        total = len(self._historico)
        if total == 0:
            return {"total": 0}
        por_nivel = {}
        for r in self._historico:
            n = r.nivel.name
            por_nivel[n] = por_nivel.get(n, 0) + 1
        return {
            "total":     total,
            "por_nivel": por_nivel,
            "criticos":  por_nivel.get("CRITICO", 0),
            "altos":     por_nivel.get("ALTO", 0),
        }


# â”€â”€ Instância global (opcional) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_guardiao_global: Optional[GuardiaoVerdade] = None

def obter_guardiao(cronista=None) -> GuardiaoVerdade:
    global _guardiao_global
    if _guardiao_global is None:
        _guardiao_global = GuardiaoVerdade(cronista=cronista)
    return _guardiao_global

