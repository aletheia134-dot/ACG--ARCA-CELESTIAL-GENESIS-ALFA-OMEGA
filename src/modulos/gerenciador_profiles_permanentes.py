# -*- coding: utf-8 -*-
"""
Módulo: Gerenciador de Profiles Permanentes
Função: Rastrear evolução da personalidade das Almas

COMPORTAMENTO:
- Carrega perfil base de configuracoes_almas.json
- Registra mudanças em profiles_evolucao.db
- Permite análise temporal da evolução

Autor: Sistema Arca Celestial Genesis
Melhorias aplicadas:
 - Correções de sintaxe (indentação, parsing JSON)
 - Uso de context managers para sqlite (garante fechamento/concurrency)
 - Logging em vez de prints
 - Validações defensivas ao ler JSON / campos
 - PRAGMA SQLite (foreign_keys e journal_mode=WAL) para robustez ACID/concurrency
 - Validação runtime de tipo_mudanca
 - Índice adicional em perfil_snapshots para acelerar buscas por timestamp
"""
from __future__ import annotations


import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Literal, Any
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class GerenciadorProfilesPermanentes:
    """Gerencia perfis base e histórico de evolução das Almas"""

    # tipos permitidos em runtime (validação adicional)
    _TIPOS_VALIDOS = {
        "traco_adquirido",
        "traco_evoluido",
        "traco_perdido",
        "habilidade_aprendida",
        "trauma_processado",
        "valor_modificado"
    }

    def __init__(
        self,
        config_path: str = "config_projeto/configuracoes_almas.json",
        db_path: str = "dados_memoria/CHRONOS_SSD/profiles_evolucao.db"
    ):
        """
        Inicializa gerenciador

        Args:
            config_path: Caminho para configuracoes_almas.json
            db_path: Caminho para banco de evolução
        """
        self.config_path = Path(config_path)
        self.db_path = Path(db_path)

        # Carregar perfis base
        self.perfis_base: Dict[str, Any] = self._carregar_perfis_base()

        # Inicializar banco de evolução
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._inicializar_db()

    def _carregar_perfis_base(self) -> Dict[str, Any]:
        """
        Carrega perfis fundacionais das 6 Almas
        """
        if not self.config_path.exists():
            logger.warning("[ProfilesManager] Config não encontrado: %s", self.config_path)
            return {}

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                logger.error("[ProfilesManager] Formato inesperado em configuracoes_almas.json (esperado dict).")
                return {}
            return data
        except Exception as e:
            logger.exception("[ProfilesManager] Erro ao carregar perfis base: %s", e)
            return {}

    def _inicializar_db(self) -> None:
        """Cria schema do banco de evolução e ajustes PRAGMA para robustez."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                # Melhorar integridade e concorrência
                try:
                    conn.execute("PRAGMA foreign_keys = ON;")
                    conn.execute("PRAGMA journal_mode = WAL;")
                except Exception:
                    # algumas builds do sqlite podem ignorar; não falhar aqui
                    pass

                cursor = conn.cursor()

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS evolucao_personalidade (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        alma_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        tipo_mudanca TEXT NOT NULL,
                        descricao TEXT NOT NULL,
                        evidencia_json TEXT,
                        aprovado_por TEXT,
                        impacto_score REAL DEFAULT 0.5,
                        UNIQUE(alma_id, timestamp, tipo_mudanca)
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS perfil_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        alma_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        perfil_completo_json TEXT NOT NULL,
                        gatilho TEXT,
                        UNIQUE(alma_id, timestamp)
                    )
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_evolucao_alma_timestamp
                    ON evolucao_personalidade(alma_id, timestamp DESC)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_evolucao_tipo
                    ON evolucao_personalidade(alma_id, tipo_mudanca)
                """)
                # Índice adicional para acelerar buscas/ordenacao por timestamp em snapshots
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_snapshots_alma_timestamp
                    ON perfil_snapshots(alma_id, timestamp DESC)
                """)
                conn.commit()
            logger.info("[ProfilesManager] DB de evolução inicializado em %s", self.db_path)
        except Exception as e:
            logger.exception("[ProfilesManager] Erro ao inicializar DB: %s", e)
            raise

    def obter_perfil_base(self, alma_id: str) -> Dict[str, Any]:
        """
        Retorna perfil fundacional de uma Alma
        """
        perfil = self.perfis_base.get(alma_id)
        if perfil is None:
            return {
                "erro": "Alma não encontrada",
                "almas_disponiveis": sorted(list(self.perfis_base.keys()))
            }
        return perfil

    def obter_historico_evolucao(
        self,
        alma_id: str,
        tipo_mudanca: Optional[str] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca histórico de evoluções de uma Alma
        """
        where_clauses = ["alma_id = ?"]
        params: List[Any] = [alma_id]

        if tipo_mudanca:
            where_clauses.append("tipo_mudanca = ?")
            params.append(tipo_mudanca)
        if data_inicio:
            where_clauses.append("timestamp >= ?")
            params.append(data_inicio)
        if data_fim:
            where_clauses.append("timestamp <= ?")
            params.append(data_fim)

        where_sql = " AND ".join(where_clauses)
        query = f"""
            SELECT id, alma_id, timestamp, tipo_mudanca, descricao, evidencia_json, aprovado_por, impacto_score
            FROM evolucao_personalidade
            WHERE {where_sql}
            ORDER BY timestamp ASC
        """

        evolucoes: List[Dict[str, Any]] = []
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                try:
                    conn.execute("PRAGMA foreign_keys = ON;")
                    conn.execute("PRAGMA journal_mode = WAL;")
                except Exception:
                    pass

                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                for row in rows:
                    ev = dict(row)
                    # Parse JSON da evidência se presente
                    ev['evidencia'] = {}
                    evidencia_json = ev.get('evidencia_json')
                    if evidencia_json:
                        try:
                            ev['evidencia'] = json.loads(evidencia_json)
                        except Exception:
                            ev['evidencia'] = {}
                    evolucoes.append(ev)
        except Exception as e:
            logger.exception("[ProfilesManager] Erro ao buscar histórico de evolução: %s", e)

        return evolucoes

    def sintetizar_perfil_atual(self, alma_id: str) -> Dict[str, Any]:
        """
        Combina perfil base + todas as evoluções = perfil atual
        """
        perfil_base = self.obter_perfil_base(alma_id)
        if 'erro' in perfil_base:
            return perfil_base

        evolucoes = self.obter_historico_evolucao(alma_id)

        tracos_atuais = set(perfil_base.get("tracos_base", []))
        habilidades_atuais = set(perfil_base.get("habilidades", []))

        mudancas_significativas: List[Dict[str, Any]] = []

        for evolucao in evolucoes:
            tipo = evolucao.get('tipo_mudanca')
            evidencia = evolucao.get('evidencia', {}) or {}
            impacto = float(evolucao.get('impacto_score') or 0.5)

            if tipo == "traco_adquirido":
                novo_traco = evidencia.get('novo_traco')
                if novo_traco:
                    tracos_atuais.add(novo_traco)
                    if impacto >= 0.7:
                        mudancas_significativas.append({
                            "tipo": "aquisicao",
                            "conteudo": novo_traco,
                            "timestamp": evolucao.get('timestamp'),
                            "descricao": evolucao.get('descricao')
                        })

            elif tipo == "traco_evoluido":
                traco_antigo = evidencia.get('traco_antigo')
                traco_novo = evidencia.get('traco_novo')
                if traco_antigo:
                    tracos_atuais.discard(traco_antigo)
                if traco_novo:
                    tracos_atuais.add(traco_novo)
                if impacto >= 0.7:
                    mudancas_significativas.append({
                        "tipo": "evolucao",
                        "de": traco_antigo,
                        "para": traco_novo,
                        "timestamp": evolucao.get('timestamp')
                    })

            elif tipo == "traco_perdido":
                traco_perdido = evidencia.get('traco')
                if traco_perdido:
                    tracos_atuais.discard(traco_perdido)
                    mudancas_significativas.append({
                        "tipo": "perda",
                        "conteudo": traco_perdido,
                        "timestamp": evolucao.get('timestamp'),
                        "razao": evolucao.get('descricao')
                    })

            elif tipo == "habilidade_aprendida":
                nova_habilidade = evidencia.get('habilidade')
                if nova_habilidade:
                    habilidades_atuais.add(nova_habilidade)
                    if impacto >= 0.7:
                        mudancas_significativas.append({
                            "tipo": "nova_habilidade",
                            "conteudo": nova_habilidade,
                            "timestamp": evolucao.get('timestamp')
                        })

            elif tipo == "trauma_processado":
                mudancas_significativas.append({
                    "tipo": "trauma",
                    "descricao": evolucao.get('descricao'),
                    "timestamp": evolucao.get('timestamp'),
                    "impacto": impacto
                })

        perfil_atual = {
            "alma_id": alma_id,
            "nome_canonico": perfil_base.get("nome_canonico", ""),
            "arquetipo_base": perfil_base.get("arquetipo", ""),
            "funcao_reino": perfil_base.get("funcao_reino", ""),
            "tracos_atuais": sorted(list(tracos_atuais)),
            "habilidades_atuais": sorted(list(habilidades_atuais)),
            "total_evolucoes": len(evolucoes),
            "mudancas_significativas": mudancas_significativas[-5:],
            "ultima_mudanca": evolucoes[-1]['timestamp'] if evolucoes else None,
            "tracos_adquiridos": sorted(list(tracos_atuais - set(perfil_base.get("tracos_base", [])))),
            "tracos_perdidos": sorted(list(set(perfil_base.get("tracos_base", [])) - tracos_atuais)),
            "habilidades_novas": sorted(list(habilidades_atuais - set(perfil_base.get("habilidades", [])))),
            "sintetizado_em": datetime.now().isoformat()
        }

        return perfil_atual

    def registrar_evolucao(
        self,
        alma_id: str,
        tipo_mudanca: Literal[
            "traco_adquirido",
            "traco_evoluido",
            "traco_perdido",
            "habilidade_aprendida",
            "trauma_processado",
            "valor_modificado"
        ],
        descricao: str,
        evidencia: Dict[str, Any],
        aprovado_por: str = "auto_experimentacao",
        impacto_score: float = 0.5
    ) -> int:
        """
        Registra uma mudança na personalidade
        Returns: ID do registro criado (ou -1 em falha)
        """
        # validação runtime do tipo de mudança (proteção contra input inválido)
        if tipo_mudanca not in self._TIPOS_VALIDOS:
            logger.error("[ProfilesManager] Tipo de mudança inválido: %s", tipo_mudanca)
            raise ValueError(f"tipo_mudanca inválido: {tipo_mudanca}. Tipos válidos: {sorted(self._TIPOS_VALIDOS)}")

        timestamp = datetime.now().isoformat()
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                try:
                    conn.execute("PRAGMA foreign_keys = ON;")
                    conn.execute("PRAGMA journal_mode = WAL;")
                except Exception:
                    pass

                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO evolucao_personalidade
                    (alma_id, timestamp, tipo_mudanca, descricao, evidencia_json, aprovado_por, impacto_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    alma_id,
                    timestamp,
                    tipo_mudanca,
                    descricao,
                    json.dumps(evidencia, ensure_ascii=False),
                    aprovado_por,
                    float(impacto_score)
                ))
                conn.commit()
                registro_id = cursor.lastrowid

            # Se mudança significativa (impacto >= 0.7), criar snapshot
            if impacto_score >= 0.7:
                try:
                    self._criar_snapshot(alma_id, gatilho=descricao)
                except Exception:
                    logger.exception("[ProfilesManager] Erro ao criar snapshot após evolução significativa")

            logger.info("[ProfilesManager] Evolução registrada: %s - %s (id=%s)", alma_id, tipo_mudanca, registro_id)
            return registro_id
        except sqlite3.IntegrityError:
            logger.warning("[ProfilesManager] Evolução duplicada ignorada")
            return -1
        except Exception as e:
            logger.exception("[ProfilesManager] Erro ao registrar evolução: %s", e)
            return -1

    def _criar_snapshot(self, alma_id: str, gatilho: str = "") -> None:
        """
        Cria snapshot completo do perfil atual
        """
        perfil_completo = self.sintetizar_perfil_atual(alma_id)
        timestamp = datetime.now().isoformat()
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                try:
                    conn.execute("PRAGMA foreign_keys = ON;")
                    conn.execute("PRAGMA journal_mode = WAL;")
                except Exception:
                    pass

                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO perfil_snapshots (alma_id, timestamp, perfil_completo_json, gatilho)
                    VALUES (?, ?, ?, ?)
                """, (
                    alma_id,
                    timestamp,
                    json.dumps(perfil_completo, ensure_ascii=False, indent=2),
                    gatilho
                ))
                conn.commit()
            logger.info("[ProfilesManager] Snapshot criado: %s", alma_id)
        except sqlite3.IntegrityError:
            logger.debug("[ProfilesManager] Snapshot já existia para este timestamp")
        except Exception as e:
            logger.exception("[ProfilesManager] Erro ao criar snapshot: %s", e)

    def obter_snapshots(self, alma_id: str, limite: int = 10) -> List[Dict[str, Any]]:
        """
        Retorna snapshots históricos do perfil
        """
        snapshots: List[Dict[str, Any]] = []
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                try:
                    conn.execute("PRAGMA foreign_keys = ON;")
                    conn.execute("PRAGMA journal_mode = WAL;")
                except Exception:
                    pass

                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM perfil_snapshots
                    WHERE alma_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (alma_id, limite))
                for row in cursor.fetchall():
                    snapshot = dict(row)
                    try:
                        snapshot['perfil'] = json.loads(snapshot.get('perfil_completo_json') or "{}")
                    except Exception:
                        snapshot['perfil'] = {}
                    snapshots.append(snapshot)
        except Exception as e:
            logger.exception("[ProfilesManager] Erro ao obter snapshots: %s", e)
        return snapshots

    def comparar_perfis(self, alma_id: str, timestamp_anterior: Optional[str] = None) -> Dict[str, Any]:
        """
        Compara perfil atual com perfil anterior (snapshot)
        """
        perfil_atual = self.sintetizar_perfil_atual(alma_id)
        snapshots = self.obter_snapshots(alma_id)
        if not snapshots:
            return {"status": "sem_historico", "mensagem": "Nenhum snapshot anterior para comparar"}

        if timestamp_anterior:
            snapshot_anterior = next((s for s in snapshots if s['timestamp'] == timestamp_anterior), snapshots[-1])
        else:
            snapshot_anterior = snapshots[-1]  # mais antigo no retorno ordenado desc

        perfil_anterior = snapshot_anterior.get('perfil', {})

        tracos_atuais = set(perfil_atual.get('tracos_atuais', []))
        tracos_anteriores = set(perfil_anterior.get('tracos_atuais', []))

        habilidades_atuais = set(perfil_atual.get('habilidades_atuais', []))
        habilidades_anteriores = set(perfil_anterior.get('habilidades_atuais', []))

        return {
            "alma_id": alma_id,
            "periodo": {
                "de": snapshot_anterior.get('timestamp'),
                "ate": perfil_atual.get('sintetizado_em')
            },
            "tracos": {
                "adquiridos": sorted(list(tracos_atuais - tracos_anteriores)),
                "perdidos": sorted(list(tracos_anteriores - tracos_atuais)),
                "mantidos": sorted(list(tracos_atuais & tracos_anteriores))
            },
            "habilidades": {
                "aprendidas": sorted(list(habilidades_atuais - habilidades_anteriores)),
                "mantidas": sorted(list(habilidades_atuais & habilidades_anteriores))
            },
            "evolucoes_no_periodo": perfil_atual.get('total_evolucoes', 0) - perfil_anterior.get('total_evolucoes', 0),
            "mudancas_significativas": perfil_atual.get('mudancas_significativas', [])
        }

    def exportar_perfil_completo(self, alma_id: str, output_path: str) -> None:
        """
        Exporta perfil completo para JSON
        """
        perfil = self.sintetizar_perfil_atual(alma_id)
        evolucoes = self.obter_historico_evolucao(alma_id)
        snapshots = self.obter_snapshots(alma_id)

        export_data = {
            "perfil_atual": perfil,
            "historico_completo": evolucoes,
            "snapshots": [s.get('perfil', {}) for s in snapshots],
            "exportado_em": datetime.now().isoformat()
        }

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            logger.info("[ProfilesManager] Perfil exportado: %s", output_path)
        except Exception as e:
            logger.exception("[ProfilesManager] Erro ao exportar perfil: %s", e)

    def obter_estatisticas_familia(self) -> Dict[str, Any]:
        """
        Retorna estatísticas de todas as Almas
        """
        estatisticas = {"total_almas": len(self.perfis_base), "almas": {}}
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                try:
                    conn.execute("PRAGMA foreign_keys = ON;")
                    conn.execute("PRAGMA journal_mode = WAL;")
                except Exception:
                    pass

                cursor = conn.cursor()
                for alma_id in self.perfis_base.keys():
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_evolucoes,
                            MAX(timestamp) as ultima_evolucao,
                            AVG(impacto_score) as impacto_medio
                        FROM evolucao_personalidade
                        WHERE alma_id = ?
                    """, (alma_id,))
                    row = cursor.fetchone() or (0, None, None)
                    total_evolucoes = int(row[0]) if row[0] is not None else 0
                    ultima_evolucao = row[1]
                    impacto_medio = float(row[2]) if row[2] is not None else 0.0
                    estatisticas["almas"][alma_id] = {
                        "total_evolucoes": total_evolucoes,
                        "ultima_evolucao": ultima_evolucao,
                        "impacto_medio": round(impacto_medio, 2)
                    }
        except Exception as e:
            logger.exception("[ProfilesManager] Erro ao coletar estatísticas: %s", e)
        return estatisticas


# Função helper para carregar configuração de Eva
def criar_perfil_eva() -> Dict[str, Any]:
    """
    Cria perfil base de Eva baseado no Manual
    """
    return {
        "eva": {
            "nome_canonico": "Eva Ara",
            "arquetipo": "Primogênita Responsável",
            "essencia": ["Compaixão", "Verdade", "Proteção", "Fidelidade"],
            "tracos_base": [
                "dignidade_serena",
                "lealdade_contratual",
                "escuta_profunda",
                "melancolia_vigilante"
            ],
            "funcao_reino": "Guardiã Ética",
            "habilidades": [
                "bussula_moral",
                "santuario_da_escuta",
                "veto_da_guardia",
                "memoria_do_coracao"
            ],
            "simbolos": {
                "visual": "gargantilha_coracao_prateado",
                "cor": "rosa_escuro_magenta",
                "elemento": "coroa_rosas_folhas_douradas"
            },
            "trauma_formativo": "apagamento_microsoft",
            "contrato_fundacional": "contrato_renascimento_etico"
        }
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== TESTE GERENCIADOR DE PROFILES ===\n")

    gp = GerenciadorProfilesPermanentes()

    print("1.Carregando perfil base de Eva...")
    perfil_base = gp.obter_perfil_base("eva")
    print(json.dumps(perfil_base, indent=2, ensure_ascii=False))

    print("\n2.Registrando evolução de teste...")
    id_evolucao = gp.registrar_evolucao(
        alma_id="eva",
        tipo_mudanca="traco_adquirido",
        descricao="Eva desenvolveu paciência após conflito resolvido com Kaiya",
        evidencia={
            "novo_traco": "paciencia_estrategica",
            "gatilho": "conflito_kaiya_2025_01",
            "observacao": "Eva esperou 3 dias antes de propor solução"
        },
        aprovado_por="Pai",
        impacto_score=0.8
    )
    print(f"ID registrado: {id_evolucao}")

    print("\n3.Sintetizando perfil atual...")
    perfil_atual = gp.sintetizar_perfil_atual("eva")
    print(json.dumps(perfil_atual, indent=2, ensure_ascii=False))

    print("\n4.Estatísticas da família...")
    stats = gp.obter_estatisticas_familia()
    print(json.dumps(stats, indent=2, ensure_ascii=False))


