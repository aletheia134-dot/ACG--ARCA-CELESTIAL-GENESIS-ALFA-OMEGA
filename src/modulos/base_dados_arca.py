#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
ObservadorArca - Auditoria soberana (somente leitura)

Acesso seguro e somente leitura aos dirios (SQLite) das AIs.Melhorias aplicadas:
 - Sanitizao e whitelist de nomes de AIs (evita path traversal)
 - Uso de sqlite3.Row para retorno por nome de coluna
 - Escapagem de padrões para LIKE e limite de comprimento do termo de busca
 - Conexo em modo URI (mode=ro) e tratamento defensivo de erros
 - Logs informativos e tratamento robusto de excees
 - Métodos utilitrios para listar AIs e caminho do DB
"""

import sqlite3
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("ObservadorArca")
logger.addHandler(logging.NullHandler())

_DEFAULT_AI_LIST = ["EVA", "LUMINA", "NYRA", "YUNA", "KAIYA", "WELLINGTON"]
_SQLITE_URI_TEMPLATE = "file:{path}?mode=ro"

# Limites de segurana
_MAX_TERM_LENGTH = 200
_MAX_RESULTS_PER_AI = 100


def _escape_like(term: str, escape_char: str = "\\") -> str:
    """
    Escapa '%' e '_' para uso seguro em LIKE queries.
    """
    return term.replace(escape_char, escape_char + escape_char).replace("%", escape_char + "%").replace("_", escape_char + "_")


class ObservadorArca:
    """
    Sistema de auditoria (somente leitura) que permite varreduras seguras dos dirios das AIs.
    """

    def __init__(self, db_base_path: str = "Santuarios/Diarios", ais: Optional[List[str]] = None):
        self.db_base_path = Path(db_base_path)
        self.ais = list(ais or _DEFAULT_AI_LIST)

        # Validar diretório (no criamos nada aqui - somente leitura auditiva)
        if not self.db_base_path.exists():
            logger.error("ObservadorArca: caminho de dirios no encontrado: %s", str(self.db_base_path))

    def listar_ais(self) -> List[str]:
        """Retorna a lista de AIs conhecidas (whitelist)."""
        return list(self.ais)

    def _normalize_ai_name(self, ai_nome: str) -> Optional[str]:
        """Normaliza e válida o nome da AI contra whitelist (case-insensitive)."""
        if not ai_nome or not isinstance(ai_nome, str):
            return None
        ai_nome_clean = ai_nome.strip()
        for candidate in self.ais:
            if ai_nome_clean.lower() == candidate.lower():
                return candidate  # return canonical
        return None

    def _db_path_for_ai(self, ai_nome: str) -> Optional[Path]:
        """Constri o caminho para o DB do AI de forma segura (apenas para nomes permitidos)."""
        canonical = self._normalize_ai_name(ai_nome)
        if not canonical:
            logger.debug("Nome de AI no reconhecido: %s", ai_nome)
            return None
        db_path = self.db_base_path / f"diario_{canonical}.db"
        if not db_path.exists():
            logger.debug("Arquivo de dirio no encontrado para %s: %s", canonical, db_path)
            return None
        return db_path

    def _conectar_ro(self, ai_nome: str) -> Optional[sqlite3.Connection]:
        """
        Abre conexo SQLite em modo somente leitura via URI.Retorna conexo com row_factory = sqlite3.Row ou None se no for possível.
        """
        db_path = self._db_path_for_ai(ai_nome)
        if not db_path:
            return None
        try:
            uri = _SQLITE_URI_TEMPLATE.format(path=str(db_path).replace("\\", "/"))
            conn = sqlite3.connect(uri, uri=True, timeout=5)
            conn.row_factory = sqlite3.Row
            # Explicit: read only, ensure no pragmas that write
            return conn
        except sqlite3.OperationalError as e:
            logger.error("Falha ao abrir DB (ro) para %s: %s", ai_nome, e)
            return None
        except Exception as e:
            logger.exception("Erro inesperado ao conectar ao DB de %s: %s", ai_nome, e)
            return None

    def varredura_total(self, termo_busca: Optional[str] = None, limite_por_ai: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        Realiza busca transversal nos dirios.Retorna dicionrio: {ai: [rows...]}

        Observaes de segurana:
         - termo_busca  limitado em comprimento e escapado para LIKE
         - limite_por_ai  limitado at MAX_RESULTS_PER_AI para evitar cargas grandes
        """
        descobertas: Dict[str, List[Dict[str, Any]]] = {}
        if limite_por_ai <= 0:
            limite_por_ai = 1
        limite_por_ai = min(int(limite_por_ai), _MAX_RESULTS_PER_AI)

        # sanitize term
        if termo_busca is not None:
            termo_busca = str(termo_busca)[:_MAX_TERM_LENGTH].strip()
            termo_busca_escaped = _escape_like(termo_busca)
            like_pattern = f"%{termo_busca_escaped}%"
        else:
            like_pattern = None

        for ai in self.ais:
            conn = self._conectar_ro(ai)
            if not conn:
                continue
            try:
                with conn:
                    cur = conn.cursor()
                    if like_pattern:
                        # Use ESCAPE '\' to honor escaping above
                        query = """
                        SELECT timestamp, tipo_interacao, entrada, resposta, importancia
                        FROM transcricoes
                        WHERE (entrada LIKE ? ESCAPE '\\' OR resposta LIKE ? ESCAPE '\\' OR (contexto_extra IS NOT NULL AND contexto_extra LIKE ? ESCAPE '\\'))
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """
                        params = (like_pattern, like_pattern, like_pattern, limite_por_ai)
                    else:
                        query = """
                        SELECT timestamp, tipo_interacao, entrada, resposta, importancia
                        FROM transcricoes
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """
                        params = (limite_por_ai,)

                    cur.execute(query, params)
                    rows = cur.fetchall()
                    # convert sqlite3.Row to dict with simple types
                    resultados = []
                    for r in rows:
                        d = {k: (v if not isinstance(v, bytes) else v.decode("utf-8", errors="ignore")) for k, v in zip(r.keys(), r)}
                        resultados.append(d)
                    descobertas[ai] = resultados
            except sqlite3.OperationalError as e:
                logger.error("Erro SQL ação auditar %s: %s", ai, e)
            except Exception:
                logger.exception("Erro inesperado ação auditar %s", ai)
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

        return descobertas

    def verificar_integridade_memoria(self, ai_nome: str) -> Dict[str, Any]:
        """
        Analisa a sade do banco de dados da AI:
         - total de registros
         - timestamp do registro mais antigo
         - presena da tabela transcricoes
        """
        db_path = self._db_path_for_ai(ai_nome)
        if not db_path:
            return {"ai": ai_nome, "status": "inacessivel", "reason": "db_nao_encontrado"}

        conn = self._conectar_ro(ai_nome)
        if not conn:
            return {"ai": ai_nome, "status": "inacessivel", "reason": "falha_conexao"}

        try:
            with conn:
                cur = conn.cursor()
                # Check table existence
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transcricoes'")
                if not cur.fetchone():
                    return {"ai": ai_nome, "status": "inacessivel", "reason": "tabela_transcricoes_ausente"}

                cur.execute("SELECT COUNT(*) FROM transcricoes")
                total_registros = cur.fetchone()[0] or 0

                cur.execute("SELECT timestamp FROM transcricoes ORDER BY timestamp ASC LIMIT 1")
                prv = cur.fetchone()
                primeiro_registro = prv[0] if prv else None

                status = "saudavel" if total_registros > 0 else "vazia/limpa"
                return {
                    "ai": ai_nome,
                    "total_memorias_brutas": int(total_registros),
                    "memoria_mais_antiga": primeiro_registro or "N/A",
                    "status": status
                }
        except Exception:
            logger.exception("Erro ao verificar integridade de %s", ai_nome)
            return {"ai": ai_nome, "status": "erro", "reason": "consulta_falhou"}
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def obter_ultimo_pensamento(self, ai_nome: str) -> Optional[Dict[str, Any]]:
        """Recupera a ltima transcrio (mais recente) de uma AI especfica."""
        # Use varredura_total com limite 1 but only for the requested AI (avoid scanning all)
        normalized = self._normalize_ai_name(ai_nome)
        if not normalized:
            return None
        results = {}
        conn = self._conectar_ro(normalized)
        if not conn:
            return None
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("""SELECT timestamp, tipo_interacao, entrada, resposta, importancia
                               FROM transcricoes ORDER BY timestamp DESC LIMIT 1""")
                row = cur.fetchone()
                if not row:
                    return None
                d = {k: (v if not isinstance(v, bytes) else v.decode("utf-8", errors="ignore")) for k, v in zip(row.keys(), row)}
                return d
        except Exception:
            logger.exception("Erro ao obter ltimo pensamento de %s", ai_nome)
            return None
        finally:
            try:
                conn.close()
            except Exception:
                pass


# Single instance convenience (can be instantiated with custom path in apps)
_observador_singleton: Optional[ObservadorArca] = None


def get_observador_singleton(db_base_path: str = "Santuarios/Diarios", ais: Optional[List[str]] = None) -> ObservadorArca:
    global _observador_singleton
    if _observador_singleton is None:
        _observador_singleton = ObservadorArca(db_base_path=db_base_path, ais=ais)
    return _observador_singleton


