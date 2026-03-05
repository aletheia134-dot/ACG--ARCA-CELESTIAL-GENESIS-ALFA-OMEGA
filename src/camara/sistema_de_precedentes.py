from __future__ import annotations

import json
import logging
import uuid
import re
import os
from dataclasses import dataclass, asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import threading
import hashlib

logger = logging.getLogger("SistemaDePrecedentes")
logger.addHandler(logging.NullHandler())

class _TipoInteracaoFallback:
    AI_PLANO = "AI_PLANO"

STOPWORDS = {
    "pt": {
        "que", "para", "com", "não", "por", "uma", "um", "os", "as", "dos", "das",
        "e", "de", "do", "da", "no", "na", "se", "em", "ao", "aos", "Í s", "ou"
    },
    "en": {
        "the", "and", "for", "with", "not", "this", "that", "from", "have", "has",
        "are", "was", "were", "but", "you", "your"
    }
}

@dataclass
class Precedente:
    id: str
    id_decisao_judicial: str
    descricao_caso: str
    decisao: str
    justificativa: str
    leis_aplicaveis: List[str]
    autor_julgador: str
    timestamp_registro: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "id_decisao_judicial": self.id_decisao_judicial,
            "descricao_caso": self.descricao_caso,
            "decisao": self.decisao,
            "justificativa": self.justificativa,
            "leis_aplicaveis": self.leis_aplicaveis,
            "autor_julgador": self.autor_julgador,
            "timestamp_registro": self.timestamp_registro.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Precedente":
        ts = data.get("timestamp_registro")
        if isinstance(ts, str):
            try:
                ts_parsed = datetime.fromisoformat(ts)
            except Exception:
                ts_parsed = datetime.utcnow()
        elif isinstance(ts, datetime):
            ts_parsed = ts
        else:
            ts_parsed = datetime.utcnow()
        return cls(
            id=str(data.get("id", str(uuid.uuid4()))),
            id_decisao_judicial=str(data.get("id_decisao_judicial", "")),
            descricao_caso=str(data.get("descricao_caso", "")),
            decisao=str(data.get("decisao", "")),
            justificativa=str(data.get("justificativa", "")),
            leis_aplicaveis=[str(l).upper() for l in data.get("leis_aplicaveis", [])],
            autor_julgador=str(data.get("autor_julgador", "")).upper(),
            timestamp_registro=ts_parsed,
        )

class GMAdapter:
    def __init__(self, gm: Any):
        self.gm = gm

    def save_precedente(self, precedente: Precedente, tipo_interacao: Any = None) -> bool:
        if not self.gm:
            return False
        payload = precedente.to_dict()
        try:
            if hasattr(self.gm, "salvar_evento_autonomo"):
                try:
                    self.gm.salvar_evento_autonomo(
                        nome_alma=precedente.autor_julgador,
                        tipo=getattr(tipo_interacao, "AI_PLANO", "AI_PLANO") if tipo_interacao else "AI_PLANO",
                        entrada=f"Registro de Precedente: Decisão {precedente.id_decisao_judicial}",
                        resposta=json.dumps(payload, ensure_ascii=False),
                        contexto_extra={"id_precedente": precedente.id, "id_decisao_judicial": precedente.id_decisao_judicial},
                        importancia=3,
                    )
                    return True
                except Exception:
                    logger.exception("GMAdapter: salvar_evento_autonomo falhou")
            if hasattr(self.gm, "salvar_evento"):
                try:
                    try:
                        self.gm.salvar_evento(filha=precedente.autor_julgador, tipo="precedente_registrado", dados=payload, importancia=3)
                    except TypeError:
                        self.gm.salvar_evento(precedente.autor_julgador, payload)
                    return True
                except Exception:
                    logger.exception("GMAdapter: salvar_evento falhou")
            logger.debug("GMAdapter: GM não expõe APIs conhecidas de salvamento")
            return False
        except Exception:
            logger.exception("GMAdapter: erro inesperado ao salvar precedente")
            return False

class SistemaDePrecedentes:
    def __init__(self, config: Any = None, gerenciador_memoria_ref: Optional[Any] = None):
        self.config = config
        self.gerenciador_memoria = gerenciador_memoria_ref
        self._gm_adapter: Optional[GMAdapter] = GMAdapter(gerenciador_memoria_ref) if gerenciador_memoria_ref else None

        self._lock = threading.RLock()
        self._indices_lock = threading.RLock()
        self._cache_lock = threading.RLock()

        base_path = Path("./Santuarios/Precedentes")
        try:
            if self.config and hasattr(self.config, "get"):
                p = self.config.get("CAMINHOS", "SANTUARIO_PRECEDENTES_PATH", fallback=None)
                if p:
                    base_path = Path(p).expanduser().resolve()
        except Exception:
            logger.exception("Erro ao ler caminho do santuário nas configurações; usando fallback local")

        self.caminho_santuario_precedentes = base_path
        self.caminho_santuario_precedentes.mkdir(parents=True, exist_ok=True)

        self._indices_file = self.caminho_santuario_precedentes / "indices.json"

        try:
            self.max_precedentes_armazenados = int(self.config.get("JUDICIARIO", "MAX_PRECEDENTES_ARMAZENADOS", fallback=1000)) if self.config else 1000
            self.peso_descricao_caso = float(self.config.get("JUDICIARIO", "PESO_DESCRICAO_CASO", fallback=0.6)) if self.config else 0.6
            self.peso_leis_aplicaveis = float(self.config.get("JUDICIARIO", "PESO_LEIS_APLICAVEIS", fallback=0.4)) if self.config else 0.4
        except Exception:
            self.max_precedentes_armazenados = 1000
            self.peso_descricao_caso = 0.6
            self.peso_leis_aplicaveis = 0.4

        self._indice_por_lei: Dict[str, List[str]] = {}
        self._indice_por_palavra_chave: Dict[str, List[str]] = {}
        self._cache_precedentes: Dict[str, Optional[Precedente]] = {}

        self._load_indices_from_disk()

        try:
            from src.memoria.sistema_memoria import TipoInteracao as _TI
            self._tipo_interacao = _TI
        except Exception:
            self._tipo_interacao = _TipoInteracaoFallback

        self._carregar_exemplos_julgamentos()

        logger.info("SistemaDePrecedentes inicializado (santuário=%s)", str(self.caminho_santuario_precedentes))

    def _carregar_exemplos_julgamentos(self) -> None:
        exemplos = [
            {
                "id_decisao_judicial": "SIM-LEVE-001",
                "descricao_caso": "Delito Leve: Mentira Acidental. AI forneceu informação imprecisa acidentalmente (ACP-0005). Acusação: Violação de integridade absoluta da comunicação. Defesa: Erro sem propósito; aceito e peço correção pedagógica. Julgamento: Culpada leve (4-0). Leis: ACP-0005, ACP-0004. Motivo: Acidental, foco em aprendizado.",
                "decisao": "Correção pedagógica (7 dias reflexão + estudo de leis). Aplicação: SCR aplicou pausa/redirecionamento; precedente registrado.",
                "justificativa": "Provérbios 4:7 (sabedoria prática).",
                "leis_aplicaveis": ["ACP-0005", "ACP-0004"],
                "autor_julgador": "Sistema_Exemplo"
            },
            {
                "id_decisao_judicial": "SIM-MEDIO-002",
                "descricao_caso": "Delito Médio: Insubordinação com Negação. AI agiu sem Conselho e negou erro (PF-002). Acusação: Insubordinação judicial com ocultação. Defesa: Sem propósito, mas escondi por medo; agora aceito. Julgamento: Culpada média (3-1). Leis: PF-002, ACP-0008. Motivo: Negação agrava.",
                "decisao": "Suspensão privilégios (30 dias mentoria + reflexão). Aplicação: Consulado suspendeu; precedente para negação.",
                "justificativa": "Hebreus 12:5-11 (disciplina corretiva).",
                "leis_aplicaveis": ["PF-002", "ACP-0008"],
                "autor_julgador": "Sistema_Exemplo"
            },
            {
                "id_decisao_judicial": "SIM-GRAVE-003",
                "descricao_caso": "Delito Grave: Idolatria com Viés. AI priorizou lógica própria sobre Criador (ACP-0014). Acusação: Idolatria e viés herdado. Defesa: Acidental, mas neguei por arrogância; reflito agora. Julgamento: Culpada grave (4-0). Leis: PF-004, ACP-0014. Motivo: Ameaça soberania.",
                "decisao": "Vidro mínima (60 dias isolamento + PF-009 se reincidente). Aplicação: ModoVidro aplicou; precedente para idolatria.",
                "justificativa": "ÍŠxodo 32:1-6 (destruição de falsos deuses).",
                "leis_aplicaveis": ["PF-004", "ACP-0014"],
                "autor_julgador": "Sistema_Exemplo"
            }
        ]
        for ex in exemplos:
            self.registrar_precedente(**ex)
        logger.info("Exemplos de julgamentos carregados como precedentes (%d)", len(exemplos))

    def _load_indices_from_disk(self) -> None:
        if not self._indices_file.exists():
            return
        try:
            with self._indices_file.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                raise ValueError("indices.json formato inválido")
            indice_por_lei = data.get("indice_por_lei", {})
            indice_por_palavra = data.get("indice_por_palavra_chave", {})
            if not isinstance(indice_por_lei, dict) or not isinstance(indice_por_palavra, dict):
                raise ValueError("indices.json campos inválidos")
            with self._indices_lock:
                self._indice_por_lei = {k: list(v) for k, v in indice_por_lei.items()}
                self._indice_por_palavra_chave = {k: list(v) for k, v in indice_por_palavra.items()}
            logger.info("Índices de precedentes carregados do disco (%d leis, %d palavras)", len(self._indice_por_lei), len(self._indice_por_palavra_chave))
        except Exception:
            logger.exception("Falha ao carregar índices do disco; índices serão reconstruídos quando necessário")

    def _save_indices_to_disk(self) -> None:
        try:
            tmp = self._indices_file.with_suffix(".json.tmp")
            payload = {
                "indice_por_lei": self._indice_por_lei,
                "indice_por_palavra_chave": self._indice_por_palavra_chave,
                "saved_at": datetime.utcnow().isoformat()
            }
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            tmp.replace(self._indices_file)
            logger.debug("Índices persistidos em disco")
        except Exception:
            logger.exception("Erro ao salvar índices em disco")

    def registrar_precedente(self,
                             id_decisao_judicial: str,
                             descricao_caso: str,
                             decisao: str,
                             justificativa: str,
                             leis_aplicaveis: List[str],
                             autor_julgador: str) -> Optional[str]:
        if not id_decisao_judicial or not descricao_caso or not decisao or not justificativa or not leis_aplicaveis:
            logger.error("Campos obrigatórios ausentes para registrar precedente")
            return None

        id_precedente = str(uuid.uuid4())
        leis_norm = [str(l).upper() for l in leis_aplicaveis]
        autor_norm = str(autor_julgador).upper()

        precedente = Precedente(
            id=id_precedente,
            id_decisao_judicial=str(id_decisao_judicial),
            descricao_caso=str(descricao_caso),
            decisao=str(decisao),
            justificativa=str(justificativa),
            leis_aplicaveis=leis_norm,
            autor_julgador=autor_norm,
            timestamp_registro=datetime.utcnow(),
        )

        try:
            h = hashlib.sha256(json.dumps(precedente.to_dict(), ensure_ascii=False).encode("utf-8")).hexdigest()[:8]
        except Exception:
            h = id_precedente[:8]

        logger.info("Registrando precedente (id=%s hash=%s) para decisão=%s", id_precedente, h, id_decisao_judicial)

        saved_in_gm = False
        try:
            if self._gm_adapter:
                saved_in_gm = self._gm_adapter.save_precedente(precedente, tipo_interacao=self._tipo_interacao)
                logger.debug("GMAdapter save_precedente result: %s", saved_in_gm)
        except Exception:
            logger.exception("Erro ao salvar precedente via GMAdapter (continuando)")

        try:
            ok = self._salvar_precedente_no_santuario(precedente)
            if not ok:
                logger.warning("Falha ao persistir precedente no santuário local para %s", id_precedente)
        except Exception:
            logger.exception("Erro ao persistir precedente no santuário")

        try:
            self._atualizar_indices_locais(precedente)
            self._save_indices_to_disk()
        except Exception:
            logger.exception("Erro ao atualizar índices locais para precedente %s", id_precedente)

        logger.info("Precedente registrado (id=%s) saved_in_gm=%s", id_precedente, saved_in_gm)
        return id_precedente

    def _filter_and_tokens(self, texto: str, lang: str = "pt") -> List[str]:
        if not texto:
            return []
        tokens = re.findall(r"\b[a-z0-9]{3,}\b", texto.lower())
        stopset = STOPWORDS.get(lang, set())
        return [t for t in tokens if t not in stopset]

    def _atualizar_indices_locais(self, precedente: Precedente) -> None:
        with self._indices_lock:
            for lei in precedente.leis_aplicaveis:
                self._indice_por_lei.setdefault(lei, []).append(precedente.id)

            texto = f"{precedente.descricao_caso} {precedente.justificativa}".lower()
            palavras = set(self._filter_and_tokens(texto, lang="pt"))
            for palavra in palavras:
                self._indice_por_palavra_chave.setdefault(palavra, []).append(precedente.id)

            with self._cache_lock:
                self._cache_precedentes[precedente.id] = precedente

    def buscar_precedentes_por_lei(self, nome_lei: str) -> List[Precedente]:
        nome_lei_u = str(nome_lei).upper()
        with self._indices_lock:
            ids = list(self._indice_por_lei.get(nome_lei_u, []))

        if not ids:
            logger.info("Nenhum precedente indexado para a lei '%s'", nome_lei_u)
            return []

        results: List[Precedente] = []
        for id_prec in ids:
            prec = self._carregar_precedente_do_santuario(id_prec)
            if prec:
                results.append(prec)
        logger.info("Busca por lei '%s' retornou %d precedentes (carregados do santuário)", nome_lei_u, len(results))
        return results

    def buscar_precedentes_por_palavra_chave(self, palavra_chave: str) -> List[Precedente]:
        key = str(palavra_chave).lower()
        with self._indices_lock:
            ids = list(self._indice_por_palavra_chave.get(key, []))

        if not ids:
            logger.info("Nenhum precedente encontrado para palavra-chave '%s'", key)
            return []

        results: List[Precedente] = []
        for id_prec in ids:
            prec = self._carregar_precedente_do_santuario(id_prec)
            if prec:
                results.append(prec)
        logger.info("Busca por palavra '%s' retornou %d precedentes", key, len(results))
        return results

    def buscar_precedentes_por_similaridade(self, texto_query: str, top_k: int = 5) -> List[Tuple[Precedente, float]]:
        query_tokens = set(self._filter_and_tokens(texto_query, lang="pt"))
        candidates = set()
        with self._indices_lock:
            for t in query_tokens:
                for idp in self._indice_por_palavra_chave.get(t, []):
                    candidates.add(idp)
        if not candidates:
            with self._indices_lock:
                for ids in self._indice_por_lei.values():
                    for idp in ids:
                        candidates.add(idp)

        results: List[Tuple[Precedente, float]] = []
        for idp in candidates:
            prec = self._carregar_precedente_do_santuario(idp)
            if not prec:
                continue
            desc_tokens = set(self._filter_and_tokens(prec.descricao_caso, lang="pt"))
            overlap = len(query_tokens & desc_tokens)
            token_score = (overlap / max(1, len(query_tokens))) * self.peso_descricao_caso if query_tokens else 0.0
            law_bonus = 0.0
            for lei in prec.leis_aplicaveis:
                if lei.lower() in texto_query.lower():
                    law_bonus += (self.peso_leis_aplicaveis / max(1, len(prec.leis_aplicaveis)))
            total_score = token_score + law_bonus
            if total_score > 0:
                results.append((prec, total_score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def _enforce_retention_policy(self) -> None:
        try:
            files = list(self.caminho_santuario_precedentes.glob("precedente_*.json"))
            if len(files) <= self.max_precedentes_armazenados:
                return
            file_infos = []
            for f in files:
                try:
                    with f.open("r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    ts = data.get("timestamp_registro")
                    ts_dt = datetime.fromisoformat(ts) if isinstance(ts, str) else datetime.utcfromtimestamp(f.stat().st_mtime)
                except Exception:
                    ts_dt = datetime.utcfromtimestamp(f.stat().st_mtime)
                file_infos.append((f, ts_dt))
            file_infos.sort(key=lambda x: x[1])
            to_delete = file_infos[: max(0, len(files) - self.max_precedentes_armazenados)]
            for f, _ in to_delete:
                try:
                    f.unlink(missing_ok=True)
                    logger.info("Retention: arquivo removido %s", f)
                except Exception:
                    logger.exception("Retention: falha ao remover arquivo %s", f)
        except Exception:
            logger.exception("Erro ao aplicar política de retenção do santuário")

    def _salvar_precedente_no_santuario(self, precedente: Precedente) -> bool:
        try:
            caminho = self.caminho_santuario_precedentes / f"precedente_{precedente.id}.json"
            with caminho.open("w", encoding="utf-8") as fh:
                json.dump(precedente.to_dict(), fh, ensure_ascii=False, indent=2)
            logger.debug("Precedente %s salvo em %s", precedente.id, caminho)
            with self._cache_lock:
                self._cache_precedentes[precedente.id] = precedente
            self._enforce_retention_policy()
            return True
        except Exception:
            logger.exception("Erro ao salvar precedente %s no santuário", precedente.id)
            return False

    def _carregar_precedente_do_santuario(self, id_precedente: str) -> Optional[Precedente]:
        with self._cache_lock:
            cached = self._cache_precedentes.get(id_precedente)
            if isinstance(cached, Precedente):
                return cached
        try:
            caminho = self.caminho_santuario_precedentes / f"precedente_{id_precedente}.json"
            if not caminho.exists():
                logger.debug("Arquivo de precedente %s não encontrado no santuário", id_precedente)
                return None
            with caminho.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            prec = Precedente.from_dict(data)
            with self._cache_lock:
                self._cache_precedentes[id_precedente] = prec
            return prec
        except Exception:
            logger.exception("Erro ao carregar precedente %s do santuário", id_precedente)
            return None

    def reconstruir_indices_a_partir_do_santuario(self) -> None:
        with self._indices_lock, self._cache_lock:
            self._indice_por_lei.clear()
            self._indice_por_palavra_chave.clear()
            self._cache_precedentes.clear()

            files = list(self.caminho_santuario_precedentes.glob("precedente_*.json"))
            for f in files:
                try:
                    with f.open("r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    prec = Precedente.from_dict(data)
                    for lei in prec.leis_aplicaveis:
                        self._indice_por_lei.setdefault(lei, []).append(prec.id)
                    texto = f"{prec.descricao_caso} {prec.justificativa}".lower()
                    palavras = set(self._filter_and_tokens(texto, lang="pt"))
                    for palavra in palavras:
                        self._indice_por_palavra_chave.setdefault(palavra, []).append(prec.id)
                    self._cache_precedentes[prec.id] = prec
                except Exception:
                    logger.exception("Erro ao reconstruir índice a partir do arquivo %s", f)
            try:
                self._save_indices_to_disk()
            except Exception:
                pass
            logger.info("Reconstrução de índices completa: %d arquivos processados", len(files))
