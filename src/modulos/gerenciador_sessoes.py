from src.diagnostico.erros import LLMTimeoutError, LLMUnavailableError, LLMExecutionError, MemoriaIndisponivelError, DryRunError, PlaceholderError
from __future__ import annotations

from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import datetime
import json
import threading
import hashlib
import logging
import sqlite3

class ConfigError(Exception):
    pass

class ConfigManager:
    def __init__(self):
        self.SESSOES_CONVERSA_DB_PATH = Path('./data/sessoes_conversas.db')
        self.LIMIAR_M1_DIAS = 7
        self.LIMIAR_M2_DIAS = 30
        self.ALMAS_NOMES = ['eva', 'lumina', 'yuna', 'kaiya', 'nyra']

_config_instance: Optional[ConfigManager] = None

def get_config() -> ConfigManager:
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance

class GerenciadorSessoesError(Exception):
    pass

class GerenciadorSessoes:
    def __init__(self):
        self.logger = logging.getLogger('GerenciadorSessoes')
        self.config = get_config()

        self.db_path = Path(self.config.SESSOES_CONVERSA_DB_PATH)
        self.limiar_m1_dias = int(self.config.LIMIAR_M1_DIAS)
        self.limiar_m2_dias = int(self.config.LIMIAR_M2_DIAS)
        self.almas_nomes = [n.lower() for n in (self.config.ALMAS_NOMES or [])]

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conexao: Optional[sqlite3.Connection] = None
        self._lock = threading.RLock()

        self._inicializar_db()
        self.logger.info("[SESSÕES] Gerenciador de Sessões iniciado.DB: %s", self.db_path)

    def _inicializar_db(self) -> None:
        try:
            self.conexao = sqlite3.connect(str(self.db_path), check_same_thread=False)
            try:
                self.conexao.execute("PRAGMA foreign_keys = ON;")
            except Exception:
                pass

            cursor = self.conexao.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessoes (
                    sessao_id TEXT PRIMARY KEY,
                    personalidade TEXT NOT NULL,
                    tema TEXT NOT NULL,
                    resumivel INTEGER DEFAULT 0,
                    data_inicio DATETIME DEFAULT CURRENT_TIMESTAMP,
                    data_ultimo_acesso DATETIME DEFAULT CURRENT_TIMESTAMP,
                    data_arquivada DATETIME,
                    camada_atual TEXT DEFAULT 'M1',
                    ultimo_turno_numero INTEGER DEFAULT 0,
                    resumo_m3 TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS turnos (
                    turno_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sessao_id TEXT NOT NULL,
                    numero_turno INTEGER NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    input_usuario TEXT NOT NULL,
                    resposta_ia TEXT NOT NULL,
                    FOREIGN KEY(sessao_id) REFERENCES sessoes(sessao_id) ON DELETE CASCADE
                )
            """)
            self.conexao.commit()
            self.logger.info("[SESSÕES] Banco de dados inicializado.")
        except Exception as e:
            self.logger.critical("[SESSÕES] Erro ao inicializar DB %s: %s", self.db_path, e, exc_info=True)
            raise ConfigError(f"Falha ao inicializar GerenciadorSessoes: {e}")

    def _gerar_id_sessao(self, user_id: str, personalidade: str, tema: str) -> str:
        chave = f'{user_id}_{personalidade}_{tema}'.encode('utf-8')
        return hashlib.sha256(chave).hexdigest()[:16]

    def obter_sessao(self, user_id: str, personalidade: str, tema: str, resumivel: bool = False) -> str:
        if not user_id or not personalidade or not tema:
            self.logger.error("[SESSÕES] Parâmetros inválidos para obter_sessao.")
            raise ValueError("user_id, personalidade e tema são obrigatórios")

        personalidade_lower = personalidade.lower()
        if personalidade_lower not in self.almas_nomes:
            self.logger.warning("[SESSÕES] Personalidade desconhecida: %s", personalidade)
            raise ValueError(f"Personalidade inválida: {personalidade}. Escolha entre {', '.join(self.almas_nomes)}.")

        sessao_id = self._gerar_id_sessao(user_id, personalidade_lower, tema.lower())

        with self._lock:
            try:
                cursor = self.conexao.cursor()
                cursor.execute("SELECT sessao_id FROM sessoes WHERE sessao_id = ?", (sessao_id,))
                if not cursor.fetchone():
                    cursor.execute(
                        """INSERT INTO sessoes (sessao_id, personalidade, tema, resumivel, camada_atual)
                           VALUES (?, ?, ?, ?, 'M1')""",
                        (sessao_id, personalidade_lower, tema.lower(), 1 if resumivel else 0)
                    )
                    self.logger.info("[SESSÕES] Nova sessão criada: %s (Alma=%s, Tema=%s)", sessao_id[:8], personalidade_lower, tema.lower())
                else:
                    cursor.execute(
                        "UPDATE sessoes SET data_ultimo_acesso = ? WHERE sessao_id = ?",
                        (datetime.datetime.now().isoformat(), sessao_id)
                    )
                    self.logger.info("[SESSÕES] Sessão retomada: %s (Alma=%s, Tema=%s)", sessao_id[:8], personalidade_lower, tema.lower())

                self.conexao.commit()
                return sessao_id
            except Exception as e:
                self.logger.error("[SESSÕES] Erro ao obter/criar sessão %s: %s", sessao_id[:8], e, exc_info=True)
                self.conexao.rollback()
                raise GerenciadorSessoesError(f"Falha ao obter/criar sessão: {e}")

    def obter_sessao_dados(self, sessao_id: str) -> Dict[str, Any]:
        with self._lock:
            try:
                cursor = self.conexao.cursor()
                cursor.execute(
                    """SELECT sessao_id, personalidade, tema, resumivel, data_inicio,
                              data_ultimo_acesso, ultimo_turno_numero, resumo_m3, camada_atual
                       FROM sessoes WHERE sessao_id = ?""",
                    (sessao_id,)
                )
                row = cursor.fetchone()
                if row:
                    return {
                        'sessao_id': row[0],
                        'personalidade': row[1],
                        'tema': row[2],
                        'resumivel': bool(row[3]),
                        'data_inicio': row[4],
                        'data_ultimo_acesso': row[5],
                        'ultimo_turno_numero': row[6],
                        'resumo_m3': row[7],
                        'camada_atual': row[8]
                    }
                self.logger.warning("[SESSÕES] Sessão %s não encontrada.", sessao_id[:8])
                return {}
            except Exception as e:
                self.logger.error("[SESSÕES] Erro ao obter dados sessão %s: %s", sessao_id[:8], e, exc_info=True)
                return {}

    def carregar_contexto_completo(self, sessao_id: str, limite_turnos: Optional[int] = None) -> str:
        with self._lock:
            try:
                cursor = self.conexao.cursor()
                if limite_turnos:
                    cursor.execute(
                        """SELECT numero_turno, input_usuario, resposta_ia
                           FROM turnos
                           WHERE sessao_id = ?
                           ORDER BY numero_turno DESC
                           LIMIT ?""",
                        (sessao_id, limite_turnos)
                    )
                    rows = list(reversed(cursor.fetchall()))
                else:
                    cursor.execute(
                        """SELECT numero_turno, input_usuario, resposta_ia
                           FROM turnos
                           WHERE sessao_id = ?
                           ORDER BY numero_turno ASC""",
                        (sessao_id,)
                    )
                    rows = cursor.fetchall()

                if not rows:
                    return '[NOVA CONVERSA - SEM HISTÓRICO]'

                contexto = ['[HISTÓRICO DA CONVERSA]\n']
                for numero, input_user, resposta in rows:
                    contexto.append(f'Turno {numero}:\nCriador: {input_user}\nAlma: {resposta}\n')
                return "\n".join(contexto).strip()
            except Exception as e:
                self.logger.error("[SESSÕES] Erro ao carregar contexto %s: %s", sessao_id[:8], e, exc_info=True)
                raise MemoriaIndisponivelError("Erro ao carregar contexto")

    def registrar_turno(self, sessao_id: str, input_usuario: str, resposta_ia: str) -> int:
        with self._lock:
            try:
                cursor = self.conexao.cursor()
                cursor.execute("SELECT ultimo_turno_numero FROM sessoes WHERE sessao_id = ?", (sessao_id,))
                row = cursor.fetchone()
                if row is None:
                    self.logger.error("[SESSÕES] Sessão %s não encontrada para registrar turno.", sessao_id[:8])
                    raise GerenciadorSessoesError(f"Sessão '{sessao_id[:8]}' não encontrada.Turno não registrado.")

                proximo_turno = int(row[0]) + 1
                cursor.execute(
                    """INSERT INTO turnos (sessao_id, numero_turno, input_usuario, resposta_ia)
                       VALUES (?, ?, ?, ?)""",
                    (sessao_id, proximo_turno, input_usuario, resposta_ia)
                )
                cursor.execute(
                    "UPDATE sessoes SET ultimo_turno_numero = ?, data_ultimo_acesso = ? WHERE sessao_id = ?",
                    (proximo_turno, datetime.datetime.now().isoformat(), sessao_id)
                )
                self.conexao.commit()
                self.logger.debug("[SESSÕES] Turno %d registrado para sessão %s", proximo_turno, sessao_id[:8])
                return proximo_turno
            except Exception as e:
                self.logger.error("[SESSÕES] Erro ao registrar turno para sessão %s: %s", sessao_id[:8], e, exc_info=True)
                self.conexao.rollback()
                raise GerenciadorSessoesError(f"Falha ao registrar turno: {e}")

    def arquivar_para_m3_com_resumo(self, sessao_id: str, resumo_texto: str) -> bool:
        with self._lock:
            try:
                cursor = self.conexao.cursor()
                cursor.execute("SELECT resumivel, tema FROM sessoes WHERE sessao_id = ?", (sessao_id,))
                row = cursor.fetchone()
                if not row:
                    self.logger.error("[SESSÕES] Sessão %s não encontrada para arquivamento M3.", sessao_id[:8])
                    return False
                resumivel, tema = row
                if not resumivel:
                    self.logger.warning("[SESSÕES] Sessão %s não marcada como resumível; não será arquivada.", sessao_id[:8])
                    return False
                cursor.execute(
                    """UPDATE sessoes
                       SET camada_atual = 'M3', data_arquivada = ?, resumo_m3 = ?
                       WHERE sessao_id = ?""",
                    (datetime.datetime.now().isoformat(), resumo_texto, sessao_id)
                )
                self.conexao.commit()
                self.logger.info("[SESSÕES] Sessão %s arquivada em M3 com resumo.", sessao_id[:8])
                return True
            except Exception as e:
                self.logger.error("[SESSÕES] Erro ao arquivar sessão %s em M3: %s", sessao_id[:8], e, exc_info=True)
                self.conexao.rollback()
                return False

    def arquivar_para_m3_sem_resumo(self, sessao_id: str) -> bool:
        with self._lock:
            try:
                cursor = self.conexao.cursor()
                cursor.execute(
                    """UPDATE sessoes
                       SET camada_atual = 'M3', data_arquivada = ?
                       WHERE sessao_id = ?""",
                    (datetime.datetime.now().isoformat(), sessao_id)
                )
                self.conexao.commit()
                self.logger.info("[SESSÕES] Sessão %s arquivada em M3 (sem resumo).", sessao_id[:8])
                return True
            except Exception as e:
                self.logger.error("[SESSÕES] Erro ao arquivar sessão %s sem resumo: %s", sessao_id[:8], e, exc_info=True)
                self.conexao.rollback()
                return False

    def recuperar_de_m3(self, sessao_id: str) -> Dict[str, Any]:
        with self._lock:
            try:
                cursor = self.conexao.cursor()
                cursor.execute(
                    "SELECT tema, resumo_m3, data_arquivada, personalidade, camada_atual FROM sessoes WHERE sessao_id = ?",
                    (sessao_id,)
                )
                row = cursor.fetchone()
                if not row:
                    self.logger.warning("[SESSÕES] Sessão %s não encontrada ao recuperar de M3.", sessao_id[:8])
                    return {'erro': 'Sessão não encontrada.'}
                tema, resumo, data_arquivada, personalidade, camada_atual = row
                if resumo:
                    return {
                        'tipo': 'RESUMO_M3',
                        'sessao_id': sessao_id,
                        'personalidade': personalidade,
                        'tema': tema,
                        'resumo': resumo,
                        'data_arquivada': data_arquivada,
                        'nota': 'Resumo carregado.Contexto completo via carregar_contexto_completo().'
                    }
                return {
                    'tipo': 'COMPLETO_M3_SEM_RESUMO',
                    'sessao_id': sessao_id,
                    'personalidade': personalidade,
                    'tema': tema,
                    'data_arquivada': data_arquivada,
                    'nota': 'Sem resumo; use carregar_contexto_completo() para histórico completo.'
                }
            except Exception as e:
                self.logger.error("[SESSÕES] Erro ao recuperar sessão %s de M3: %s", sessao_id[:8], e, exc_info=True)
                return {'erro': str(e)}

    def listar_conversas_ativas(self, user_id: str, camada: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            try:
                cursor = self.conexao.cursor()
                query = """SELECT sessao_id, personalidade, tema, resumivel, data_ultimo_acesso, ultimo_turno_numero, camada_atual
                           FROM sessoes
                           WHERE sessao_id LIKE ? """
                params: Tuple[Any, ...] = (f'{user_id}%',)
                if camada:
                    query += "AND camada_atual = ? "
                    params += (camada,)
                query += "ORDER BY data_ultimo_acesso DESC"
                cursor.execute(query, params)
                rows = cursor.fetchall()
                resultado: List[Dict[str, Any]] = []
                for sessao_id, personalidade, tema, resumivel, data_ultimo, num_turnos, camada_atual in rows:
                    resultado.append({
                        'sessao_id': sessao_id,
                        'personalidade': personalidade,
                        'tema': tema,
                        'resumivel': bool(resumivel),
                        'data_ultimo_acesso': data_ultimo,
                        'tempo_desde': self._tempo_decorrido(data_ultimo),
                        'turnos': num_turnos,
                        'camada_atual': camada_atual
                    })
                return resultado
            except Exception as e:
                self.logger.error("[SESSÕES] Erro ao listar conversas para %s: %s", user_id, e, exc_info=True)
                return []

    def listar_conversas_por_tema(self, user_id: str, tema: str) -> List[Dict[str, Any]]:
        with self._lock:
            try:
                cursor = self.conexao.cursor()
                cursor.execute(
                    """SELECT sessao_id, personalidade, camada_atual, data_ultimo_acesso, resumivel, ultimo_turno_numero
                       FROM sessoes
                       WHERE sessao_id LIKE ? AND tema = ?
                       ORDER BY data_ultimo_acesso DESC""",
                    (f"{user_id}%", tema.lower())
                )
                rows = cursor.fetchall()
                resultado: List[Dict[str, Any]] = []
                for sessao_id, personalidade, camada, data_ultimo, resumivel, num_turnos in rows:
                    resultado.append({
                        "sessao_id": sessao_id,
                        "personalidade": personalidade,
                        "camada": camada,
                        "resumivel": bool(resumivel),
                        "data_ultimo_acesso": data_ultimo,
                        "tempo_desde": self._tempo_decorrido(data_ultimo),
                        "turnos": num_turnos
                    })
                return resultado
            except Exception as e:
                self.logger.error("[SESSÕES] Erro ao listar conversas por tema %s para %s: %s", tema, user_id, e, exc_info=True)
                return []

    def exportar_conversa_texto(self, sessao_id: str) -> str:
        with self._lock:
            try:
                cursor = self.conexao.cursor()
                cursor.execute('SELECT personalidade, tema FROM sessoes WHERE sessao_id = ?', (sessao_id,))
                row = cursor.fetchone()
                if not row:
                    return f"Sessão '{sessao_id[:8]}' não encontrada."
                personalidade, tema = row
                cursor.execute("""SELECT numero_turno, input_usuario, resposta_ia
                                  FROM turnos
                                  WHERE sessao_id = ?
                                  ORDER BY numero_turno ASC""", (sessao_id,))
                turnos = cursor.fetchall()
                export_str = f"=== CONVERSA: {tema.upper()} com {personalidade.upper()} ===\nSessão ID: {sessao_id}\n\n"
                for numero, input_user, resposta in turnos:
                    export_str += f"[{numero}] Criador: {input_user}\n    {personalidade.title()}: {resposta}\n\n"
                return export_str.strip()
            except Exception as e:
                self.logger.error("[SESSÕES] Erro ao exportar sessão %s: %s", sessao_id[:8], e, exc_info=True)
                return f"Erro ao exportar sessão '{sessao_id[:8]}': {e}"

    def contar_turnos(self, sessao_id: str) -> int:
        with self._lock:
            try:
                cursor = self.conexao.cursor()
                cursor.execute("SELECT ultimo_turno_numero FROM sessoes WHERE sessao_id = ?", (sessao_id,))
                row = cursor.fetchone()
                return int(row[0]) if row else 0
            except Exception as e:
                self.logger.error("[SESSÕES] Erro ao contar turnos para %s: %s", sessao_id[:8], e, exc_info=True)
                return 0

    def deletar_sessao(self, sessao_id: str) -> bool:
        with self._lock:
            try:
                cursor = self.conexao.cursor()
                cursor.execute('DELETE FROM turnos WHERE sessao_id = ?', (sessao_id,))
                cursor.execute('DELETE FROM sessoes WHERE sessao_id = ?', (sessao_id,))
                self.conexao.commit()
                self.logger.info("[SESSÕES] Sessão %s deletada.", sessao_id[:8])
                return True
            except Exception as e:
                self.logger.error("[SESSÕES] Erro ao deletar sessão %s: %s", sessao_id[:8], e, exc_info=True)
                self.conexao.rollback()
                return False

    def transicionar_m1_para_m2(self) -> int:
        with self._lock:
            try:
                cursor = self.conexao.cursor()
                data_limite = (datetime.datetime.now() - datetime.timedelta(days=self.limiar_m1_dias)).isoformat()
                cursor.execute(
                    """UPDATE sessoes
                       SET camada_atual = 'M2'
                       WHERE camada_atual = 'M1'
                       AND datetime(data_ultimo_acesso) < ?""",
                    (data_limite,)
                )
                self.conexao.commit()
                total = cursor.rowcount
                if total > 0:
                    self.logger.info("[SESSÕES] %d sessões movidas M1->M2.", total)
                return total
            except Exception as e:
                self.logger.error("[SESSÕES] Erro transicionando M1->M2: %s", e, exc_info=True)
                self.conexao.rollback()
                return 0

    def transicionar_m2_para_m3(self) -> int:
        with self._lock:
            try:
                cursor = self.conexao.cursor()
                data_limite = (datetime.datetime.now() - datetime.timedelta(days=self.limiar_m2_dias)).isoformat()
                cursor.execute(
                    """UPDATE sessoes
                       SET camada_atual = 'M3', data_arquivada = ?
                       WHERE camada_atual = 'M2'
                       AND datetime(data_ultimo_acesso) < ?""",
                    (datetime.datetime.now().isoformat(), data_limite)
                )
                self.conexao.commit()
                total = cursor.rowcount
                if total > 0:
                    self.logger.info("[SESSÕES] %d sessões movidas M2->M3.", total)
                return total
            except Exception as e:
                self.logger.error("[SESSÕES] Erro transicionando M2->M3: %s", e, exc_info=True)
                self.conexao.rollback()
                return 0

    def obter_estatisticas(self) -> Dict[str, Any]:
        with self._lock:
            try:
                cursor = self.conexao.cursor()
                cursor.execute("SELECT COUNT(*) FROM sessoes")
                total_sessoes = cursor.fetchone()[0] or 0
                cursor.execute("SELECT camada_atual, COUNT(*) FROM sessoes GROUP BY camada_atual")
                por_camada = {row[0]: row[1] for row in cursor.fetchall()}
                cursor.execute("SELECT COUNT(*) FROM turnos")
                total_turnos = cursor.fetchone()[0] or 0
                media_turnos = total_turnos / total_sessoes if total_sessoes > 0 else 0
                return {
                    "total_sessoes": total_sessoes,
                    "sessoes_por_camada": por_camada,
                    "total_turnos": total_turnos,
                    "media_turnos_por_sessao": round(media_turnos, 2)
                }
            except Exception as e:
                self.logger.error("[SESSÕES] Erro ao gerar estatísticas: %s", e, exc_info=True)
                return {}

    def _tempo_decorrido(self, timestamp_str: Optional[str]) -> str:
        if not timestamp_str:
            return "?"
        try:
            ultimo = datetime.datetime.fromisoformat(timestamp_str)
            agora = datetime.datetime.now()
            delta = agora - ultimo
            if delta.days > 365:
                return f"{delta.days // 365}a"
            if delta.days > 30:
                return f"{delta.days // 30}m"
            if delta.days > 0:
                return f"{delta.days}d"
            if delta.seconds > 3600:
                return f"{delta.seconds // 3600}h"
            if delta.seconds > 60:
                return f"{delta.seconds // 60}min"
            return "agora"
        except Exception:
            return "?"

    def desligar(self) -> None:
        with self._lock:
            try:
                if self.conexao:
                    self.conexao.close()
                self.logger.info("[SESSÕES] Gerenciador desligado.Conexão fechada.")
            except Exception as e:
                self.logger.error("[SESSÕES] Erro ao desligar: %s", e, exc_info=True)


