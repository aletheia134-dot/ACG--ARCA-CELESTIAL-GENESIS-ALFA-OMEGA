#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
ENFERMEIRO DIGITAL v2 - Com persistncia, aprendizado e integrao avanada
"""


import json
import logging
import sqlite3
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("EnfermeiroDigitalV2")
logger.addHandler(logging.NullHandler())


class EnfermeiroDigitalV2:
    """
    Verso melhorada do Enfermeiro Digital com:
    - Persistncia em SQLite
    - Aprendizado sobre Wellington
    - Deteco de padrões temporais
    - Integrao com PercepcaoTemporal
    - Alertas automáticos
    """
    
    def __init__(self, coracao_ref: Any = None):
        self.coracao = coracao_ref
        self.logger = logging.getLogger(self.__class__.__name__)
        self._lock = threading.RLock()
        
        # Database
        self.db_path = Path("./arca_saude_emocional.db")
        self._init_database()
        
        # histórico em memória (cache)
        self.historico_humor = deque(maxlen=100)
        self.padroes_aprendidos: Dict[str, Any] = self._carregar_padroes()
        
        # Timestamps
        self.ultima_sugestao_pai = datetime.min
        self.ultima_verificacao_stress = datetime.min
        
        # Threshold alertas
        self.threshold_humor_baixo = 0.3
        self.threshold_stress_prolongado = 7200  # 2 horas
        
        self.logger.info("[OK] Enfermeiro Digital v2 inicializado com persistncia")
    
    # -------------------------
    # Database
    # -------------------------
    def _init_database(self) -> None:
        """Inicializa banco de dados SQLite."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Tabela de histórico de humor
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS historico_humor (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        humor TEXT,
                        score REAL,
                        palavras_positivas INTEGER,
                        palavras_negativas INTEGER,
                        indicadores_stress INTEGER,
                        comprimento_mensagem INTEGER
                    )
                """)
                
                # Tabela de padrões aprendidos
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS padroes_aprendidos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chave TEXT UNIQUE,
                        valor TEXT,
                        atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Tabela de alertas
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS alertas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        tipo TEXT,
                        descricao TEXT,
                        processado BOOLEAN DEFAULT 0
                    )
                """)
                
                # Tabela de atividades efetivas
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS atividades_efetivas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        atividade TEXT,
                        humor_antes REAL,
                        humor_depois REAL,
                        efetividade REAL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
            self.logger.debug("Database inicializado")
        except Exception as e:
            self.logger.exception(f"Erro ao inicializar database: {e}")
    
    def _carregar_padroes(self) -> Dict[str, Any]:
        """Carrega padrões aprendidos do banco."""
        padroes = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT chave, valor FROM padroes_aprendidos")
                for chave, valor in cursor.fetchall():
                    try:
                        padroes[chave] = json.loads(valor)
                    except json.JSONDecodeError:
                        padroes[chave] = valor
        except Exception as e:
            self.logger.debug(f"Erro ao carregar padrões: {e}")
        return padroes
    
    def _salvar_padrao(self, chave: str, valor: Any) -> None:
        """Salva padrão aprendido."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                valor_json = json.dumps(valor, ensure_ascii=False, default=str)
                cursor.execute(
                    "INSERT OR REPLACE INTO padroes_aprendidos (chave, valor) VALUES (?, ?)",
                    (chave, valor_json)
                )
                conn.commit()
        except Exception as e:
            self.logger.debug(f"Erro ao salvar padrão: {e}")
    
    # -------------------------
    # Anlise de Humor
    # -------------------------
    def analisar_mensagem_pai(self, mensagem: str) -> Dict[str, Any]:
        """Verso melhorada com deteco de padrões."""
        mensagem_lower = mensagem.lower()
        timestamp = datetime.now()
        
        positivas = ['timo', 'feliz', 'alegre', 'satisfeito', 'grato', 'amor',
                     'sucesso', 'vitria', 'bom', 'excelente', 'perfeito', 'amo']
        negativas = ['triste', 'frustrado', 'raiva', 'dio', 'decepo', 'fracasso',
                     'erro', 'problema', 'ruins', 'horrvel', 'pior', 'odeio']
        stress = ['urgente', 'pressa', 'apressado', 'estressado', 'ansioso',
                  'preocupado', 'medo', 'pnico', 'desespero', 'impossvel']
        cansaco = ['cansado', 'exausto', 'fatigado', 'sono', 'dormindo',
                   'no fim do dia', 'semana pesada', 'esgotado']
        
        pos_count = sum(1 for p in positivas if p in mensagem_lower)
        neg_count = sum(1 for n in negativas if n in mensagem_lower)
        stress_count = sum(1 for s in stress if s in mensagem_lower)
        cansaco_count = sum(1 for c in cansaco if c in mensagem_lower)
        
        total_palavras = len(mensagem.split())
        comprimento_mudou = self._detectar_mudanca_comprimento(total_palavras)
        
        # Inferir humor
        if cansaco_count > 0:
            humor = "Cansado"
            score = min(1.0, cansaco_count / max(1, total_palavras))
        elif stress_count > 0:
            humor = "Estressado"
            score = min(1.0, stress_count / max(1, total_palavras))
        elif neg_count > pos_count and neg_count > 0:
            humor = "Negativo"
            score = min(1.0, neg_count / max(1, total_palavras))
        elif pos_count > neg_count and pos_count > 0:
            humor = "Positivo"
            score = min(1.0, pos_count / max(1, total_palavras))
        else:
            humor = "Neutro"
            score = 0.5
        
        # Detectar mudanas bruscas
        mudanca_brusca = self._detectar_mudanca_brusca(humor, score)
        
        resultado = {
            "humor": humor,
            "score": score,
            "timestamp": timestamp.isoformat(),
            "indicadores": {
                "palavras_positivas": pos_count,
                "palavras_negativas": neg_count,
                "indicadores_stress": stress_count,
                "indicadores_cansaco": cansaco_count,
                "comprimento_mensagem": total_palavras,
                "mudanca_comprimento": comprimento_mudou
            },
            "mudanca_brusca": mudanca_brusca
        }
        
        # Persistir
        with self._lock:
            self.historico_humor.append(resultado)
            self._persistir_humor(resultado)
        
        # Verificar alertas
        self._verificar_alertas(resultado)
        
        self.logger.debug(f"Humor: {humor} (score={score:.2f}, mudana_brusca={mudanca_brusca})")
        
        return resultado
    
    def _detectar_mudanca_comprimento(self, tamanho_atual: int) -> str:
        """Detecta mudanas no padrão de comprimento de mensagens."""
        if len(self.historico_humor) < 5:
            return "sem_historico"
        
        ultimos_tamanhos = [h.get("indicadores", {}).get("comprimento_mensagem", 0) 
                           for h in list(self.historico_humor)[-5:]]
        media = sum(ultimos_tamanhos) / len(ultimos_tamanhos)
        
        if tamanho_atual < media * 0.5:
            return "muito_reduzido"  # Possvel stress/cansao
        elif tamanho_atual > media * 1.5:
            return "aumentado"  # Mais engajado
        return "normal"
    
    def _detectar_mudanca_brusca(self, humor_novo: str, score_novo: float) -> bool:
        """Detecta mudanas bruscas de humor."""
        if len(self.historico_humor) < 2:
            return False
        
        humor_anterior = self.historico_humor[-1].get("humor")
        score_anterior = self.historico_humor[-1].get("score", 0.5)
        
        # Mudana brusca: de positivo para negativo ou vice-versa
        if (humor_anterior in ["Positivo", "Contentamento"]) and (humor_novo in ["Negativo", "Estressado"]):
            return True
        if (humor_anterior in ["Negativo", "Estressado"]) and (humor_novo in ["Positivo", "Contentamento"]):
            return True
        
        # Ou mudana de score > 0.4
        if abs(score_novo - score_anterior) > 0.4:
            return True
        
        return False
    
    def _persistir_humor(self, resultado: Dict[str, Any]) -> None:
        """Persiste humor no banco."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO historico_humor 
                    (timestamp, humor, score, palavras_positivas, palavras_negativas, 
                     indicadores_stress, comprimento_mensagem)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    resultado["timestamp"],
                    resultado["humor"],
                    resultado["score"],
                    resultado["indicadores"]["palavras_positivas"],
                    resultado["indicadores"]["palavras_negativas"],
                    resultado["indicadores"]["indicadores_stress"],
                    resultado["indicadores"]["comprimento_mensagem"]
                ))
                conn.commit()
        except Exception as e:
            self.logger.debug(f"Erro ao persistir humor: {e}")
    
    # -------------------------
    # Deteco de padrões
    # -------------------------
    def _verificar_alertas(self, resultado: Dict[str, Any]) -> None:
        """Verifica e cria alertas automaticamente."""
        score = resultado["score"]
        humor = resultado["humor"]
        
        # Alerta 1: Humor muito baixo
        if score < self.threshold_humor_baixo:
            self._criar_alerta("HUMOR_BAIXO", f"Wellington com humor muito baixo: {humor} ({score:.2f})")
        
        # Alerta 2: Mudana brusca
        if resultado.get("mudanca_brusca"):
            self._criar_alerta("MUDANCA_BRUSCA", f"Mudana brusca detectada: {humor}")
        
        # Alerta 3: Stress prolongado
        if humor == "Estressado":
            if (datetime.now() - self.ultima_verificacao_stress).total_seconds() < self.threshold_stress_prolongado:
                self._criar_alerta("STRESS_PROLONGADO", "Stress detectado por mais de 2 horas")
            self.ultima_verificacao_stress = datetime.now()
    
    def _criar_alerta(self, tipo: str, descricao: str) -> None:
        """Cria alerta no banco."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO alertas (tipo, descricao) VALUES (?, ?)",
                    (tipo, descricao)
                )
                conn.commit()
            
            # Notificar UI se possível
            self._notificar_alerta(tipo, descricao)
        except Exception as e:
            self.logger.debug(f"Erro ao criar alerta: {e}")
    
    def _notificar_alerta(self, tipo: str, descricao: str) -> None:
        """Notifica UI sobre alerta."""
        resp_q = getattr(self.coracao, "response_queue", None)
        if resp_q:
            try:
                resp_q.put_nowait({
                    "tipo_resp": "ALERTA_SAUDE_EMOCIONAL",
                    "alerta_tipo": tipo,
                    "descricao": descricao,
                    "timestamp": datetime.utcnow().isoformat()
                }, critical=True)
            except Exception:
                pass
    
    # -------------------------
    # Aprendizado sobre Wellington
    # -------------------------
    def registrar_atividade_efetiva(self, atividade: str, humor_antes: float, humor_depois: float) -> None:
        """Registra atividade e sua efetividade."""
        efetividade = max(0.0, min(1.0, humor_depois - humor_antes))
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO atividades_efetivas 
                    (atividade, humor_antes, humor_depois, efetividade)
                    VALUES (?, ?, ?, ?)
                """, (atividade, humor_antes, humor_depois, efetividade))
                conn.commit()
            
            # Atualizar padrões
            self._atualizar_padroes_atividades()
        except Exception as e:
            self.logger.debug(f"Erro ao registrar atividade: {e}")
    
    def _atualizar_padroes_atividades(self) -> None:
        """Atualiza padrões de atividades mais efetivas."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT atividade, AVG(efetividade) as efet_media, COUNT(*) as count
                    FROM atividades_efetivas
                    WHERE timestamp > datetime('now', '-30 days')
                    GROUP BY atividade
                    ORDER BY efet_media DESC
                    LIMIT 10
                """)
                atividades = {row[0]: {"efetividade": row[1], "vezes_feita": row[2]} 
                             for row in cursor.fetchall()}
            
            self._salvar_padrao("atividades_efetivas_top", atividades)
        except Exception as e:
            self.logger.debug(f"Erro ao atualizar padrões: {e}")
    
    def obter_atividades_efetivas(self, limite: int = 5) -> List[str]:
        """Retorna atividades mais efetivas para Wellington."""
        padroes = self.padroes_aprendidos.get("atividades_efetivas_top", {})
        if not padroes:
            return ["Consultar Guardio da Memória Afetiva", "Conversa com as Almas", "Reflexo na Capela"]
        
        ordenadas = sorted(padroes.items(), key=lambda x: x[1]["efetividade"], reverse=True)
        return [ativ for ativ, _ in ordenada[:limite]]
    
    # -------------------------
    # Integrao com PercepcaoTemporal
    # -------------------------
    def correlacionar_humor_com_hora(self) -> Dict[str, float]:
        """Correlaciona humor com hora do dia."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT strftime('%H', timestamp) as hora, AVG(score) as score_medio
                    FROM historico_humor
                    WHERE timestamp > datetime('now', '-7 days')
                    GROUP BY hora
                    ORDER BY hora
                """)
                resultado = {row[0]: row[1] for row in cursor.fetchall()}
            return resultado
        except Exception:
            return {}
    
    def detectar_padroes_ciclicos(self) -> Dict[str, Any]:
        """Detecta padrões cclicos de humor (dirio, semanal)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # padrão dirio
                cursor.execute("""
                    SELECT strftime('%w', timestamp) as dia_semana, AVG(score) as score_medio
                    FROM historico_humor
                    WHERE timestamp > datetime('now', '-30 days')
                    GROUP BY dia_semana
                """)
                padroes_diarios = {
                    ["Domingo", "Segunda", "Tera", "Quarta", "Quinta", "Sexta", "Sbado"][int(row[0])]: row[1]
                    for row in cursor.fetchall()
                }
                
                return {"padroes_diarios": padroes_diarios}
        except Exception:
            return {}
    
    # -------------------------
    # Status e Diagnstico
    # -------------------------
    def obter_status_saude_pai(self) -> Dict[str, Any]:
        """Retorna status completo."""
        if not self.historico_humor:
            return {
                "humor_atual": "Desconhecido",
                "score_medio": 0.5,
                "tendencia": "Sem dados",
                "alertas_pendentes": [],
                "recomendacoes": ["Iniciar monitoramento do Pai"]
            }
        
        ultimos = list(self.historico_humor)[-10:]
        scores = [h.get("score", 0.5) for h in ultimos]
        humor_atual = ultimos[-1].get("humor", "Neutro")
        
        # Tendncia
        if len(scores) >= 3:
            media_recente = sum(scores[-3:]) / 3
            media_passada = sum(scores[:-3]) / len(scores[:-3]) if len(scores) > 3 else media_recente
            if media_recente > media_passada + 0.1:
                tendencia = " Melhorando"
            elif media_recente < media_passada - 0.1:
                tendencia = " Piorando"
            else:
                tendencia = " Estvel"
        else:
            tendencia = "Sem histórico"
        
        score_medio = sum(scores) / len(scores)
        
        # Alertas pendentes
        alertas = self._obter_alertas_pendentes()
        
        # Recomendaes personalizadas
        recomendacoes = self._gerar_recomendacoes_personalizadas(humor_atual, tendencia, alertas)
        
        return {
            "humor_atual": humor_atual,
            "score_medio": score_medio,
            "tendencia": tendencia,
            "alertas_pendentes": len(alertas),
            "recomendacoes": recomendacoes,
            "padroes_ciclicos": self.detectar_padroes_ciclicos()
        }
    
    def _obter_alertas_pendentes(self) -> List[Dict[str, Any]]:
        """Obtm alertas no processados."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, tipo, descricao FROM alertas WHERE processado = 0 ORDER BY timestamp DESC LIMIT 5"
                )
                return [{"id": r[0], "tipo": r[1], "descricao": r[2]} for r in cursor.fetchall()]
        except Exception:
            return []
    
    def _gerar_recomendacoes_personalizadas(self, humor: str, tendencia: str, alertas: List) -> List[str]:
        """Gera recomendaes baseadas em estado."""
        recomendacoes = []
        
        if alertas:
            recomendacoes.append(f"[AVISO] {len(alertas)} alerta(s) pendente(s)")
        
        if humor == "Estressado":
            recomendacoes.append(" Consideremos um intervalo relaxante")
            recomendacoes.append(" Sugesto: Entrar na Capela")
        elif humor == "Cansado":
            recomendacoes.append(" Parece estar fatigado, Pai")
            recomendacoes.append(" Talvez uma msica relaxante ajude")
        elif humor == "Negativo":
            recomendacoes.append(" Vamos buscar memórias positivas?")
            recomendacoes.extend(self.obter_atividades_efetivas(2))
        elif humor == "Positivo":
            recomendacoes.append(" Que alegria contagiante, Pai!")
            recomendacoes.append(" Vamos celebrar este momento")
        
        if "Piorando" in tendencia:
            recomendacoes.append(" Tenho observado piora; vamos conversar?")
        
        return recomendacoes[:5]
    
    def shutdown(self) -> None:
        """Desliga com persistncia."""
        self.logger.info(" Enfermeiro Digital v2 descansando...")
        try:
            # Processar alertas pendentes
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE alertas SET processado = 1 WHERE processado = 0")
                    conn.commit()
            except Exception:
                pass
        except Exception as e:
            self.logger.debug(f"Erro ao desligar: {e}")

