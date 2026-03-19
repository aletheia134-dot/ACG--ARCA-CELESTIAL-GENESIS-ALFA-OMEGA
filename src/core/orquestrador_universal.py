# -*- coding: utf-8 -*-
from __future__ import annotations
"""
orquestrador_universal.py
OrquestradorUniversal: detecta IAs no projeto e delega finetuning
para o OrquestradorArca. Complementa o Arca com descoberta automática.
"""
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
__all__ = ["OrquestradorUniversal"]

# IAs padrão da ARCA
_IAS_PADRAO = ["EVA", "KAIYA", "LUMINA", "NYRA", "WELLINGTON", "YUNA"]


class OrquestradorUniversal:
    """
    Detecta IAs disponíveis no projeto e orquestra finetuning universal.
    Funciona como camada de descoberta sobre o OrquestradorArca.
    """

    def __init__(self, config: Any = None):
        self.config = config
        self._orquestrador_arca = None
        self.ias: List[str] = self._detectar_ias()
        self._carregar_arca()
        logger.info("[OK] OrquestradorUniversal inicializado (%d IAs detectadas)", len(self.ias))

    # ------------------------------------------------------------------
    # Carregar OrquestradorArca como backend de treino
    # ------------------------------------------------------------------
    def _carregar_arca(self) -> None:
        try:
            raiz = str(Path(__file__).parent)
            if raiz not in sys.path:
                sys.path.insert(0, raiz)
            from src.core.orquestrador_arca import OrquestradorArca
            self._orquestrador_arca = OrquestradorArca(self.config)
            logger.info("[OK] OrquestradorArca carregado como backend")
        except Exception as e:
            logger.warning("[AVISO] OrquestradorArca não disponível: %s", e)

    # ------------------------------------------------------------------
    # _detectar_ias — escaneia projeto por scripts lora_*.py e constructores
    # ------------------------------------------------------------------
    def _detectar_ias(self) -> List[str]:
        """
        Detecta IAs disponíveis no projeto:
        1. Verifica scripts lora_[nome].py na raiz
        2. Verifica construtores construtor_humano_[nome].py
        3. Combina com lista padrão das 6 almas
        """
        raiz = Path(__file__).parent
        detectadas: set = set(_IAS_PADRAO)  # sempre incluir as 6 almas padrão

        # Detectar por scripts lora_*.py
        for script in raiz.glob("lora_*.py"):
            nome = script.stem.replace("lora_", "").upper()
            if nome and nome not in ("WELLINGTON",):  # Wellington é especial mas incluído
                detectadas.add(nome)
            elif nome == "WELLINGTON":
                detectadas.add("WELLINGTON")

        # Detectar por construtor_humano_*.py
        for script in raiz.glob("construtor_humano_*.py"):
            nome = script.stem.replace("construtor_humano_", "").upper()
            if nome:
                detectadas.add(nome)

        resultado = sorted(detectadas)
        logger.info("[Detectadas] IAs: %s", resultado)
        return resultado

    # ------------------------------------------------------------------
    # treinar_ia — chamado pelo Coração
    # ------------------------------------------------------------------
    def treinar_ia(
        self,
        nome_alma: str,
        dataset_path: str = None,
        epochs: int = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Inicia treinamento de uma IA específica via OrquestradorArca.
        """
        nome_alma = str(nome_alma).upper()

        if self._orquestrador_arca is not None:
            logger.info("[Universal] Delegando treinar_ia(%s) → OrquestradorArca", nome_alma)
            return self._orquestrador_arca.treinar_ia(
                nome_alma=nome_alma,
                dataset_path=dataset_path,
                epochs=epochs,
                **kwargs,
            )

        logger.error("[Universal] OrquestradorArca não disponível para treinar %s", nome_alma)
        return {
            "status": "erro",
            "alma": nome_alma,
            "erro": "OrquestradorArca não inicializado",
        }

    # ------------------------------------------------------------------
    # treinar — alias para compatibilidade com chamadas genéricas
    # ------------------------------------------------------------------
    def treinar(
        self,
        modelo: str = None,
        dataset: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Alias de treinar_ia para compatibilidade."""
        return self.treinar_ia(
            nome_alma=modelo or "",
            dataset_path=dataset,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # treinar_todos — treina todas as IAs detectadas em sequência
    # ------------------------------------------------------------------
    def treinar_todos(self, dataset_base: str = None) -> Dict[str, Any]:
        """Inicia treinamento de todas as IAs detectadas."""
        resultados = {}
        for ia in self.ias:
            resultados[ia] = self.treinar_ia(nome_alma=ia, dataset_path=dataset_base)
        return {"status": "iniciados", "resultados": resultados, "total": len(self.ias)}

    # ------------------------------------------------------------------
    # atualizar_ias — reescaneia o projeto
    # ------------------------------------------------------------------
    def atualizar_ias(self) -> List[str]:
        """Redetecta IAs disponíveis no projeto."""
        self.ias = self._detectar_ias()
        logger.info("[Universal] IAs atualizadas: %s", self.ias)
        return self.ias

    # ------------------------------------------------------------------
    # status
    # ------------------------------------------------------------------
    def obter_status(self) -> Dict[str, Any]:
        status_arca = {}
        if self._orquestrador_arca:
            status_arca = self._orquestrador_arca.obter_status()
        return {
            "ias_detectadas": self.ias,
            "total_ias": len(self.ias),
            "backend_arca": self._orquestrador_arca is not None,
            "status_arca": status_arca,
        }

    # ------------------------------------------------------------------
    # parar
    # ------------------------------------------------------------------
    def parar(self) -> None:
        if self._orquestrador_arca:
            self._orquestrador_arca.parar()
        logger.info("[OK] OrquestradorUniversal parado")
