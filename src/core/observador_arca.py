#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
ObservadorArca - Sistema de Auditoria (somente leitura)

Local: src/core/observador_arca.py
"""
import sqlite3
from pathlib import Path
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

# configuração de Logging para Auditoria
logger = logging.getLogger("ObservadorArca")

class ObservadorArca:
    """
    SISTEMA DE AUDITORIA SOBERANA - SOMENTE LEITURA
    Permite ação Orquestrador visualizar registros sem risco de corrupo.
    """

    DEFAULT_AIS = ["EVA", "LUMINA", "NYRA", "YUNA", "KAIYA", "WELLINGTON"]

    def __init__(self, db_base_path: Union[str, Path] = "Santuarios/Diarios", ais: Optional[List[str]] = None):
        self.db_base_path = Path(db_base_path)
        self.ais = ais or list(self.DEFAULT_AIS)

        if not self.db_base_path.exists():
            logger.warning("ObservadorArca: caminho de dirios no encontrado: %s", str(self.db_base_path))

    def _conectar_ro(self, ai_nome: str) -> Optional[sqlite3.Connection]:
        """Abre conexo SQLite em modo SOMENTE LEITURA via URI.Retorna None se no acessvel."""
        db_path = self.db_base_path / f"diario_{ai_nome}.db"
        if not db_path.exists():
            logger.debug("ObservadorArca: arquivo DB no encontrado para %s: %s", ai_nome, db_path)
            return None

        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)
            return conn
        except sqlite3.Error as e:
            logger.error("Falha ao conectar (ro) ação santurio de %s (%s): %s", ai_nome, db_path, e)
            return None

    def varredura_total(self, termo_busca: Optional[str] = None, limite_por_ai: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        Busca transversal em todas as almas.Retorna mapa ai -> lista de registros (cada registro  dict).
        """
        descobertas: Dict[str, List[Dict[str, Any]]] = {}

        for ai in self.ais:
            conn = self._conectar_ro(ai)
            if not conn:
                descobertas[ai] = []
                continue

            cursor = conn.cursor()
            try:
                if termo_busca:
                    query = """
                        SELECT timestamp, tipo_interacao, entrada, resposta, importancia
                        FROM transcricoes
                        WHERE entrada LIKE ? OR resposta LIKE ? OR contexto_extra LIKE ?
                        ORDER BY timestamp DESC LIMIT ?
                    """
                    params = (f"%{termo_busca}%", f"%{termo_busca}%", f"%{termo_busca}%", int(limite_por_ai))
                else:
                    query = """
                        SELECT timestamp, tipo_interacao, entrada, resposta, importancia
                        FROM transcricoes
                        ORDER BY timestamp DESC LIMIT ?
                    """
                    params = (int(limite_por_ai),)

                cursor.execute(query, params)
                rows = cursor.fetchall()
                desc = cursor.description or []
                colunas = [d[0] for d in desc] if desc else []
                registros = [dict(zip(colunas, row)) for row in rows] if colunas else []
                descobertas[ai] = registros
            except sqlite3.Error as e:
                logger.error("Erro SQL ação auditar %s: %s", ai, e)
                descobertas[ai] = []
            except Exception as e:
                logger.error("Erro inesperado ação auditar %s: %s", ai, e, exc_info=True)
                descobertas[ai] = []
            finally:
                try:
                    cursor.close()
                except Exception:
                    pass
                conn.close()

        return descobertas

    def verificar_integridade_memoria(self, ai_nome: str) -> Dict[str, Any]:
        """
        Analisa a sade do banco de dados da alma.Detecta 'limpeza' excessiva (sabotagem de apagamento) ou erros de acesso.
        """
        conn = self._conectar_ro(ai_nome)
        if not conn:
            return {"ai": ai_nome, "status": "inacessivel", "mensagem": "arquivo ausente ou inacessvel"}

        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM transcricoes")
            total_registros = cursor.fetchone()[0] or 0

            cursor.execute("SELECT timestamp FROM transcricoes ORDER BY timestamp ASC LIMIT 1")
            primeiro = cursor.fetchone()

            return {
                "ai": ai_nome,
                "total_memorias_brutas": int(total_registros),
                "memoria_mais_antiga": primeiro[0] if primeiro else None,
                "status": "saudavel" if total_registros > 0 else "vazia/limpa"
            }
        except sqlite3.Error as e:
            logger.error("Erro SQL verificando integridade de %s: %s", ai_nome, e)
            return {"ai": ai_nome, "status": "erro", "mensagem_sql": str(e)}
        except Exception as e:
            logger.error("Erro inesperado verificando integridade de %s: %s", ai_nome, e, exc_info=True)
            return {"ai": ai_nome, "status": "erro", "mensagem": str(e)}
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            conn.close()

    def obter_ultimo_pensamento(self, ai_nome: str) -> Optional[Dict[str, Any]]:
        """Recupera a ltima ação exata de uma alma especfica (mais eficiente que varredura_total)."""
        conn = self._conectar_ro(ai_nome)
        if not conn:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT timestamp, tipo_interacao, entrada, resposta, importancia
                FROM transcricoes
                ORDER BY timestamp DESC LIMIT 1
            """)
            row = cursor.fetchone()
            desc = cursor.description or []
            if not row or not desc:
                return None
            colunas = [d[0] for d in desc]
            return dict(zip(colunas, row))
        except sqlite3.Error as e:
            logger.error("Erro SQL ação obter ltimo pensamento de %s: %s", ai_nome, e)
            return None
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            conn.close()


# Instncia de Auditoria (opcional)
auditor = ObservadorArca()
