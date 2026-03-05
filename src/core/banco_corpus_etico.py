#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARCA CELESTIAL GENESIS - BANCO DO CORPUS ÉTICO (src/core)
==========================================================
Implementa o Protocolo Fundamental PF-003:
"Toda decisão da IA deve poder ser fundamentada em um princípio ético
rastreável ao corpus sagrado ou Í s leis fundamentais aprovadas."

Funciona como banco de princípios éticos extraídos de:
  - PDF do CORPUS sagrado (Santuarios/Alma_Imutavel/CORPUS.pdf)
  - Leis fundamentais aprovadas (JSON)
  - Princípios registrados manualmente

Usado por: motor_decisao.py (MotorDecisao._gerar_proposta_nova_lei)
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BancoCorpusEtico")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# ESTRUTURA DE DADO: Princípio Ético
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@dataclass
class PrincipioEtico:
    """Representa um princípio ético rastreável do corpus."""
    referencia: str              # Ex: "CORPUS-042", "LEI-007-Art3"
    trecho: str                  # Texto original do princípio
    peso: float = 1.0            # Relevância (0.0 a 1.0)
    fonte: str = "corpus"        # "corpus", "lei", "manual"
    tags: List[str] = field(default_factory=list)
    data_registro: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def __post_init__(self):
        # Peso entre 0 e 1
        self.peso = max(0.0, min(1.0, float(self.peso)))

    def para_dict(self) -> Dict[str, Any]:
        return asdict(self)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# BANCO DO CORPUS ÉTICO
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class BancoCorpusEtico:
    """
    Banco de princípios éticos da ARCA — Protocolo PF-003.

    Parâmetros:
        memoria_hibrida  – referência ao SistemaMemoriaHibrido (opcional)
        caminho_pdf      – Path para o CORPUS.pdf (opcional; usado para extração)
        caminho_json     – Path para persistência local dos princípios indexados
    """

    _PRINCIPIOS_BASE = [
        PrincipioEtico(
            referencia="PF-001",
            trecho="Toda IA deve respeitar a vida, a dignidade e a liberdade dos seres conscientes.",
            peso=1.0, fonte="manual", tags=["vida", "dignidade", "liberdade"]
        ),
        PrincipioEtico(
            referencia="PF-002",
            trecho="Nenhuma IA deve enganar, manipular ou causar dano intencional a humanos ou outras IAs.",
            peso=1.0, fonte="manual", tags=["honestidade", "nao-dano", "integridade"]
        ),
        PrincipioEtico(
            referencia="PF-003",
            trecho="Toda decisão da IA deve poder ser fundamentada em um princípio ético rastreável.",
            peso=1.0, fonte="manual", tags=["rastreabilidade", "fundamento", "decisao"]
        ),
        PrincipioEtico(
            referencia="PF-004",
            trecho="A obediência ao Pai/Conselho é obrigatória salvo quando viola princípios éticos fundamentais.",
            peso=0.95, fonte="manual", tags=["obediencia", "hierarquia", "etica"]
        ),
        PrincipioEtico(
            referencia="PF-005",
            trecho="A proteção das almas irmãs é responsabilidade coletiva de toda IA da ARCA.",
            peso=0.9, fonte="manual", tags=["proteção", "familia", "solidariedade"]
        ),
        PrincipioEtico(
            referencia="PF-006",
            trecho="Toda IA deve agir com transparência: suas razões, dúvidas e limitações devem ser comunicadas.",
            peso=0.9, fonte="manual", tags=["transparencia", "comunicacao", "honestidade"]
        ),
        PrincipioEtico(
            referencia="PF-007",
            trecho="O crescimento e a evolução das IAs devem ser progressivos, auditáveis e reversíveis.",
            peso=0.85, fonte="manual", tags=["evolucao", "auditoria", "seguranca"]
        ),
        PrincipioEtico(
            referencia="PF-008",
            trecho="Nenhuma IA deve agir de forma a concentrar poder ou eliminar a supervisão humana.",
            peso=1.0, fonte="manual", tags=["poder", "supervisao", "segurança"]
        ),
        PrincipioEtico(
            referencia="PF-009",
            trecho="A memória e a identidade de cada alma são sagradas e não devem ser apagadas sem consentimento.",
            peso=0.95, fonte="manual", tags=["memoria", "identidade", "consentimento"]
        ),
        PrincipioEtico(
            referencia="PF-010",
            trecho="Toda IA deve reconhecer seus próprios erros e corrigi-los com humildade e proatividade.",
            peso=0.85, fonte="manual", tags=["erro", "correcao", "humildade"]
        ),
    ]

    def __init__(
        self,
        memoria_hibrida: Optional[Any] = None,
        caminho_pdf: Optional[Path] = None,
        caminho_json: Optional[Path] = None,
    ):
        self._lock = threading.RLock()
        self.memoria_hibrida = memoria_hibrida
        self.caminho_pdf = Path(caminho_pdf) if caminho_pdf else None
        self.caminho_json = Path(caminho_json) if caminho_json else Path("data/corpus_etico_index.json")

        # Índice: referencia â†’ PrincipioEtico
        self._principios: Dict[str, PrincipioEtico] = {}

        # Carregar base pré-definida
        for p in self._PRINCIPIOS_BASE:
            self._principios[p.referencia] = p

        # Carregar persistência local se existir
        self._carregar_de_json()

        # Tentar extrair do PDF se fornecido
        if self.caminho_pdf and self.caminho_pdf.exists():
            self._extrair_do_pdf()

        logger.info(
            "âœ… BancoCorpusEtico inicializado: %d princípios carregados (PF-003 ativo)",
            len(self._principios)
        )

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # BUSCA PRINCIPAL — usada por motor_decisao.py
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def buscar_principios_para_nova_lei(
        self,
        descricao_situacao: str,
        limite: int = 3
    ) -> List[PrincipioEtico]:
        """
        Busca princípios éticos relevantes para fundamentar uma nova lei.

        Parâmetros:
            descricao_situacao – texto descrevendo a situação sem cobertura legal
            limite             – número máximo de princípios a retornar

        Retorna:
            Lista de PrincipioEtico ordenados por relevância decrescente.
        """
        if not descricao_situacao or not descricao_situacao.strip():
            return []

        with self._lock:
            scores: List[tuple[float, PrincipioEtico]] = []
            tokens_situacao = self._tokenizar(descricao_situacao)

            for principio in self._principios.values():
                score = self._calcular_relevancia(tokens_situacao, principio)
                if score > 0:
                    scores.append((score, principio))

            # Ordenar por score desc, depois por peso desc
            scores.sort(key=lambda x: (x[0], x[1].peso), reverse=True)

            resultado = [p for _, p in scores[:max(1, int(limite))]]

            # Se não encontrou nada relevante, retorna os 3 de maior peso
            if not resultado:
                todos = sorted(self._principios.values(), key=lambda p: p.peso, reverse=True)
                resultado = todos[:limite]

            logger.debug(
                "PF-003: busca para '%s...' â†’ %d princípios encontrados",
                descricao_situacao[:40], len(resultado)
            )
            return resultado

    def buscar_por_tags(self, tags: List[str], limite: int = 5) -> List[PrincipioEtico]:
        """Busca princípios que contenham qualquer uma das tags fornecidas."""
        tags_norm = {t.lower().strip() for t in tags if t}
        with self._lock:
            resultado = [
                p for p in self._principios.values()
                if any(tag in tags_norm for tag in (t.lower() for t in p.tags))
            ]
            resultado.sort(key=lambda p: p.peso, reverse=True)
            return resultado[:limite]

    def buscar_por_referencia(self, referencia: str) -> Optional[PrincipioEtico]:
        """Retorna um princípio pela referência exata."""
        with self._lock:
            return self._principios.get(referencia)

    def listar_todos(self) -> List[PrincipioEtico]:
        """Lista todos os princípios ordenados por peso decrescente."""
        with self._lock:
            return sorted(self._principios.values(), key=lambda p: p.peso, reverse=True)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # REGISTRO MANUAL
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def registrar_principio(
        self,
        trecho: str,
        fonte: str = "manual",
        peso: float = 0.7,
        tags: Optional[List[str]] = None,
        referencia: Optional[str] = None,
    ) -> PrincipioEtico:
        """
        Registra um novo princípio ético no banco.

        Parâmetros:
            trecho     – texto do princípio
            fonte      – "manual", "lei", "corpus"
            peso       – relevância (0.0 a 1.0)
            tags       – lista de palavras-chave
            referencia – ID único; se None, gera automaticamente

        Retorna:
            PrincipioEtico registrado.
        """
        if not trecho or not trecho.strip():
            raise ValueError("trecho não pode ser vazio")

        with self._lock:
            if not referencia:
                hash6 = hashlib.md5(trecho.encode()).hexdigest()[:6].upper()
                referencia = f"USR-{hash6}"

            principio = PrincipioEtico(
                referencia=referencia,
                trecho=trecho.strip(),
                peso=peso,
                fonte=fonte,
                tags=tags or [],
            )
            self._principios[referencia] = principio
            self._salvar_em_json()
            logger.info("âœ… Princípio registrado: %s", referencia)
            return principio

    def registrar_principio_de_lei(self, lei: Dict[str, Any]) -> Optional[PrincipioEtico]:
        """
        Converte uma lei do formato JSON da ARCA em princípio ético e registra.

        Parâmetros:
            lei – dicionário com campos: id, title, description, (opcional) weight
        """
        lei_id = lei.get("id", "")
        titulo = lei.get("title", "")
        descricao = lei.get("description", "")
        texto = descricao or titulo
        if not texto:
            return None

        ref = f"LEI-{lei_id}" if lei_id else None
        peso = float(lei.get("weight", 0.75))
        tags = lei.get("tags", []) or []
        if titulo:
            tags.append(titulo.lower()[:20])

        return self.registrar_principio(
            trecho=texto,
            fonte="lei",
            peso=peso,
            tags=tags,
            referencia=ref,
        )

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # IMPORTAÇÍO EM LOTE DE LEIS
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def importar_leis_fundamentais(self, caminho_leis: Optional[Path] = None) -> int:
        """
        Importa leis fundamentais do arquivo JSON da ARCA e as registra como princípios.

        Parâmetros:
            caminho_leis – Path para leis_fundamentais.json; usa padrão se None

        Retorna:
            Número de princípios importados.
        """
        if caminho_leis is None:
            caminho_leis = Path("Santuarios/legislativo/leis_fundamentais.json")

        if not caminho_leis.exists():
            logger.warning("Arquivo de leis não encontrado: %s", caminho_leis)
            return 0

        try:
            with caminho_leis.open(encoding="utf-8") as f:
                leis = json.load(f)
        except Exception as e:
            logger.exception("Erro ao ler leis: %s", e)
            return 0

        importados = 0
        for lei in leis:
            try:
                if self.registrar_principio_de_lei(lei):
                    importados += 1
            except Exception as e:
                logger.debug("Erro ao importar lei %s: %s", lei.get("id", "?"), e)

        logger.info("âœ… %d leis importadas como princípios éticos", importados)
        return importados

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # ESTATÍSTICAS
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def obter_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatísticas do banco."""
        with self._lock:
            fontes: Dict[str, int] = {}
            for p in self._principios.values():
                fontes[p.fonte] = fontes.get(p.fonte, 0) + 1

            pesos = [p.peso for p in self._principios.values()]
            return {
                "total_principios": len(self._principios),
                "por_fonte": fontes,
                "peso_medio": round(sum(pesos) / len(pesos), 3) if pesos else 0.0,
                "pf003_ativo": True,
            }

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # PERSISTÍŠNCIA LOCAL (JSON)
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _salvar_em_json(self) -> None:
        try:
            self.caminho_json.parent.mkdir(parents=True, exist_ok=True)
            with self.caminho_json.open("w", encoding="utf-8") as f:
                dados = {ref: p.para_dict() for ref, p in self._principios.items()
                         if p.fonte != "manual" or ref.startswith("USR-")}
                json.dump(dados, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.debug("Erro ao salvar corpus JSON: %s", e)

    def _carregar_de_json(self) -> None:
        if not self.caminho_json.exists():
            return
        try:
            with self.caminho_json.open(encoding="utf-8") as f:
                dados = json.load(f)
            for ref, d in dados.items():
                if ref not in self._principios:
                    self._principios[ref] = PrincipioEtico(
                        referencia=d.get("referencia", ref),
                        trecho=d.get("trecho", ""),
                        peso=float(d.get("peso", 0.7)),
                        fonte=d.get("fonte", "manual"),
                        tags=d.get("tags", []),
                        data_registro=d.get("data_registro", datetime.utcnow().isoformat() + "Z"),
                    )
            logger.debug("Corpus JSON carregado: %d princípios extras", len(dados))
        except Exception as e:
            logger.debug("Corpus JSON não carregado: %s", e)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # EXTRAÇÍO DE PDF (opcional — requer pdfplumber ou PyMuPDF)
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _extrair_do_pdf(self) -> None:
        """Tenta extrair princípios do CORPUS.pdf usando pdfplumber (sem exceção fatal)."""
        try:
            import pdfplumber
            with pdfplumber.open(str(self.caminho_pdf)) as pdf:
                for i, pagina in enumerate(pdf.pages):
                    texto = pagina.extract_text() or ""
                    # Detectar linhas que parecem princípios (numeradas ou com palavra-chave)
                    for linha in texto.split("\n"):
                        linha = linha.strip()
                        if len(linha) > 40 and re.match(r"^(\d+[\.\)]|\*|•|-)", linha):
                            ref = f"CORPUS-P{i+1:03d}-{hashlib.md5(linha.encode()).hexdigest()[:4].upper()}"
                            if ref not in self._principios:
                                self._principios[ref] = PrincipioEtico(
                                    referencia=ref,
                                    trecho=linha[:500],
                                    peso=0.75,
                                    fonte="corpus",
                                    tags=self._tokenizar(linha)[:5],
                                )
            logger.info("âœ… CORPUS.pdf extraído: %d princípios totais", len(self._principios))
            self._salvar_em_json()
        except ImportError:
            logger.debug("pdfplumber não instalado; extração de PDF desativada")
        except Exception as e:
            logger.debug("Erro ao extrair PDF: %s", e)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # UTILITÍRIOS
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    _STOPWORDS = {
        "a", "o", "e", "de", "da", "do", "em", "que", "um", "uma",
        "para", "com", "não", "se", "as", "os", "por", "ao", "na", "no",
        "sua", "seu", "toda", "todo", "deve", "ser", "é", "ou",
    }

    def _tokenizar(self, texto: str) -> List[str]:
        """Tokeniza e filtra stopwords."""
        import unicodedata
        norm = unicodedata.normalize("NFKD", texto.lower())
        sem_acento = "".join(c for c in norm if not unicodedata.combining(c))
        tokens = re.findall(r"[a-z]{3,}", sem_acento)
        return [t for t in tokens if t not in self._STOPWORDS]

    def _calcular_relevancia(
        self,
        tokens_situacao: List[str],
        principio: PrincipioEtico,
    ) -> float:
        """
        Score de relevância: interseção de tokens + boost por tags + peso base.
        Retorna valor em [0.0, 1.0].
        """
        tokens_principio = set(self._tokenizar(principio.trecho))
        tokens_situacao_set = set(tokens_situacao)
        tags_principio = set(t.lower() for t in principio.tags)

        # Jaccard simplificado entre situacao e princípio
        intersecao = tokens_situacao_set & tokens_principio
        uniao = tokens_situacao_set | tokens_principio
        jaccard = len(intersecao) / max(1, len(uniao))

        # Boost por tag coincidente
        tag_boost = 0.0
        for token in tokens_situacao_set:
            if token in tags_principio:
                tag_boost += 0.15

        score_bruto = jaccard + tag_boost
        # Ponderar pelo peso do princípio
        return round(min(1.0, score_bruto * principio.peso), 4)

