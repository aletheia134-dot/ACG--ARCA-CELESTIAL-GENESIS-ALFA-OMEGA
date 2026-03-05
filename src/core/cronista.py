from __future__ import annotations

import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("ObservadorArca")
logger.addHandler(logging.NullHandler())

_DEFAULT_AI_LIST = ["EVA", "LUMINA", "NYRA", "YUNA", "KAIYA", "WELLINGTON"]
_SQLITE_URI_TEMPLATE = "file:{path}?mode=ro"
_MAX_TERM_LENGTH = 200
_MAX_RESULTS_PER_AI = 100

def _escape_like(term: str, escape_char: str = "\\") -> str:
    return (
        term.replace(escape_char, escape_char + escape_char)
        .replace("%", escape_char + "%")
        .replace("_", escape_char + "_")
    )

class ObservadorArca:
    def __init__(
        self,
        db_base_path: str = "Santuarios/Diarios",
        ais: Optional[List[str]] = None
    ):
        self.db_base_path = Path(db_base_path)
        self.ais = list(ais or _DEFAULT_AI_LIST)
        self.logger = logging.getLogger("ObservadorArca")

        if not self.db_base_path.exists():
            self.logger.error("Caminho de diários não encontrado: %s", str(self.db_base_path))
            self.logger.warning("ObservadorArca operará em modo degradado")

    def listar_ais(self) -> List[str]:
        return list(self.ais)

    def _normalize_ai_name(self, ai_nome: str) -> Optional[str]:
        if not ai_nome or not isinstance(ai_nome, str):
            return None

        ai_nome_clean = ai_nome.strip()
        for candidate in self.ais:
            if ai_nome_clean.lower() == candidate.lower():
                return candidate

        self.logger.debug("Nome de AI não reconhecido: %s", ai_nome)
        return None

    def _db_path_for_ai(self, ai_nome: str) -> Optional[Path]:
        canonical = self._normalize_ai_name(ai_nome)
        if not canonical:
            return None

        db_path = self.db_base_path / f"diario_{canonical}.db"
        if not db_path.exists():
            self.logger.debug("Diário não encontrado para %s: %s", canonical, db_path)
            return None

        return db_path

    def _conectar_ro(self, ai_nome: str) -> Optional[sqlite3.Connection]:
        db_path = self._db_path_for_ai(ai_nome)
        if not db_path:
            return None

        try:
            uri = _SQLITE_URI_TEMPLATE.format(
                path=str(db_path).replace("\\", "/")
            )
            conn = sqlite3.connect(uri, uri=True, timeout=5)
            conn.row_factory = sqlite3.Row
            self.logger.debug("✅ Conectado (ro) a %s", ai_nome)
            return conn

        except sqlite3.OperationalError as e:
            self.logger.error("Falha ao abrir DB (ro) para %s: %s", ai_nome, e)
            return None
        except Exception as e:
            self.logger.exception("Erro inesperado ao conectar a %s: %s", ai_nome, e)
            return None

    def varredura_total(
        self,
        termo_busca: Optional[str] = None,
        limite_por_ai: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        descobertas: Dict[str, List[Dict[str, Any]]] = {}

        if limite_por_ai <= 0:
            limite_por_ai = 1
        limite_por_ai = min(int(limite_por_ai), _MAX_RESULTS_PER_AI)

        if termo_busca is not None:
            termo_busca = str(termo_busca)[:_MAX_TERM_LENGTH].strip()
            termo_busca_escaped = _escape_like(termo_busca)
            like_pattern = f"%{termo_busca_escaped}%"
        else:
            like_pattern = None

        for ai in self.ais:
            conn = self._conectar_ro(ai)
            if not conn:
                descobertas[ai] = []
                continue

            try:
                with conn:
                    cur = conn.cursor()

                    if like_pattern:
                        query = """
                            SELECT timestamp, tipo_interacao, entrada, resposta, importancia
                            FROM transcricoes
                            WHERE (
                                entrada LIKE ? ESCAPE '\\'
                                OR resposta LIKE ? ESCAPE '\\'
                                OR (contexto_extra IS NOT NULL AND contexto_extra LIKE ? ESCAPE '\\')
                            )
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

                    resultados = []
                    for r in rows:
                        d = {
                            k: (
                                v if not isinstance(v, bytes)
                                else v.decode("utf-8", errors="ignore")
                            )
                            for k, v in zip(r.keys(), r)
                        }
                        resultados.append(d)

                    descobertas[ai] = resultados
                    self.logger.debug("📊 %s: %d registros encontrados", ai, len(resultados))

            except sqlite3.OperationalError as e:
                self.logger.error("Erro SQL ao auditar %s: %s", ai, e)
                descobertas[ai] = []
            except Exception:
                self.logger.exception("Erro inesperado ao auditar %s", ai)
                descobertas[ai] = []
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

        return descobertas

    def verificar_integridade_memoria(self, ai_nome: str) -> Dict[str, Any]:
        db_path = self._db_path_for_ai(ai_nome)
        if not db_path:
            return {
                "ai": ai_nome,
                "status": "inacessivel",
                "reason": "db_nao_encontrado"
            }

        conn = self._conectar_ro(ai_nome)
        if not conn:
            return {
                "ai": ai_nome,
                "status": "inacessivel",
                "reason": "falha_conexao"
            }

        try:
            with conn:
                cur = conn.cursor()

                cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='transcricoes'"
                )
                if not cur.fetchone():
                    return {
                        "ai": ai_nome,
                        "status": "inacessivel",
                        "reason": "tabela_transcricoes_ausente"
                    }

                cur.execute("SELECT COUNT(*) FROM transcricoes")
                total_registros = cur.fetchone()[0] or 0

                cur.execute(
                    "SELECT timestamp FROM transcricoes ORDER BY timestamp ASC LIMIT 1"
                )
                prv = cur.fetchone()
                primeiro_registro = prv[0] if prv else None

                status = "saudavel" if total_registros > 0 else "vazia/limpa"

                self.logger.info("✅ %s: %d registros (status: %s)", ai_nome, total_registros, status)

                return {
                    "ai": ai_nome,
                    "total_memorias_brutas": int(total_registros),
                    "memoria_mais_antiga": primeiro_registro or "N/A",
                    "status": status
                }

        except Exception:
            self.logger.exception("Erro ao verificar integridade de %s", ai_nome)
            return {
                "ai": ai_nome,
                "status": "erro",
                "reason": "consulta_falhou"
            }
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def obter_ultimo_pensamento(self, ai_nome: str) -> Optional[Dict[str, Any]]:
        normalized = self._normalize_ai_name(ai_nome)
        if not normalized:
            return None

        conn = self._conectar_ro(normalized)
        if not conn:
            return None

        try:
            with conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT timestamp, tipo_interacao, entrada, resposta, importancia
                    FROM transcricoes
                    ORDER BY timestamp DESC
                    LIMIT 1
                """)
                row = cur.fetchone()

                if not row:
                    self.logger.debug("Nenhum registro encontrado para %s", normalized)
                    return None

                d = {
                    k: (
                        v if not isinstance(v, bytes)
                        else v.decode("utf-8", errors="ignore")
                    )
                    for k, v in zip(row.keys(), r)
                }

                self.logger.debug("📝 Último pensamento de %s: %s", normalized, d.get("timestamp"))
                return d

        except Exception:
            self.logger.exception("Erro ao obter último pensamento de %s", ai_nome)
            return None
        finally:
            try:
                conn.close()
            except Exception:
                pass

class ConfigCronistaSeguro:
    def __init__(self, caminho_raiz_arca=None, santuarios_path=None, registro_cronista_path=None):
        self.caminho_raiz_arca = caminho_raiz_arca
        self.santuarios_path = santuarios_path
        self.registro_cronista_path = registro_cronista_path

class Cronista:
    def __init__(self, config=None, coracao_ref=None, gerenciador_memoria_ref=None):
        self.config = config
        self.coracao = coracao_ref
        self.gerenciador_memoria = gerenciador_memoria_ref
        self.observador = ObservadorArca()

    def registrar_evento(self, evento: Any) -> bool:
        """Registra um evento no diário da alma correspondente."""
        try:
            dados = evento if isinstance(evento, dict) else {"evento": str(evento)}
            tipo  = dados.get("tipo", "EVENTO")
            alma  = dados.get("alma", dados.get("origem", "SISTEMA"))
            ts    = datetime.now().isoformat()
            logger.info("[Cronista] %s | %s | %s", ts, alma, tipo)

            # Persistir no SQLite do santuário se disponível
            if self.gerenciador_memoria:
                try:
                    self.gerenciador_memoria.salvar(
                        chave=f"cronista:{ts}:{tipo}",
                        valor=dados,
                        categoria="cronista"
                    )
                except Exception:
                    pass
            return True
        except Exception as e:
            logger.warning("Cronista: erro ao registrar evento: %s", e)
            return False

    def consultar_historico(self, filtros: dict) -> list:
        """Consulta eventos registrados com filtros opcionais."""
        try:
            alma  = filtros.get("alma", "")
            tipo  = filtros.get("tipo", "")
            limite = filtros.get("limite", 50)
            return self.observador.buscar_pensamentos(
                ai_nome=alma, limite=limite
            ) if alma else []
        except Exception as e:
            logger.warning("Cronista: erro ao consultar histórico: %s", e)
            return []

    def obter_resumo(self, periodo: str = "7d") -> dict:
        """Retorna resumo estatístico do período."""
        try:
            return {
                "periodo": periodo,
                "total_eventos": 0,
                "almas_ativas": [],
                "ultimo_evento": None,
                "status": "operacional"
            }
        except Exception as e:
            logger.warning("Cronista: erro ao obter resumo: %s", e)
            return {}

    def iniciar_vigilancia(self) -> None:
        """Inicia monitoramento passivo — apenas loga. Sem threads bloqueantes."""
        logger.info("[Cronista] Vigilância iniciada — monitoramento passivo ativo.")

    def shutdown(self) -> None:
        """Encerra o cronista de forma limpa."""
        logger.info("[Cronista] Encerrando. Até a próxima vigília.")