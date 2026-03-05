#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sistema_propostas_ferramentas.py - Gerenciador de Propostas de Ferramentas

Integrado com Coração v7 para:
- Criar propostas
- Verificar duplicatas
- Aprovar/Rejeitar/Analisar
- Rastrear histórico
- Registrar em BD

Responsabilidades:
- CRUD de propostas
- Verificação de duplicatas
- Histórico de status
- Integração com Coração (response_queue, ui_queue)
- Permissões por IA

MUDANÇAS v2:
âœ… Código agora é opcional na criação
âœ… Adicionado método atualizar_codigo_proposta()
âœ… Validação de similaridade melhorada
âœ… Imports corrigidos
"""
from __future__ import annotations


import datetime
import hashlib
import json
import logging
import sqlite3
import threading
import uuid
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class GerenciadorPropostas:
    """
    Gerencia ciclo de vida completo de propostas de ferramentas.Estados:
    - PENDENTE_ANALISE: Aguardando decisão do humano
    - EM_ANALISE: Humano marcou para analisar depois
    - APROVADO_CONSTRUÇÍO: Aprovado, pode construir
    - EM_CONSTRUCAO: Construindo
    - PRONTO_TESTES: Testes completados
    - PRONTO_SEGURANCA: Aguardando análise de segurança
    - EM_ANALISE_SEGURANCA: Bot analisando
    - PRONTO_APROVACAO_FINAL: Aguardando aprovação final
    - APROVADO_DEPLOY: Aprovado para deploy
    - EM_PRODUCAO: Ativo em produção
    - REJEITADO: Rejeitado (não pode duplicar)
    - FALHA_CONSTRUCAO: Construção falhou
    """

    def __init__(self, coracao_ref: Any, db_path: str = "data/propostas_ferramentas.db"):
        """
        Inicializa gerenciador.Args:
            coracao_ref: Referência ao Coração Orquestrador
            db_path: Caminho do banco de dados
        """
        self.coracao = coracao_ref
        self.logger = logging.getLogger("GerenciadorPropostas")
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Locks
        self._lock = threading.RLock()
        self._lock_db = threading.Lock()
        
        # Cache em memória
        self.propostas_cache: Dict[str, Dict[str, Any]] = {}
        
        # Inicializar banco
        self._inicializar_banco()
        
        # Carregar do banco para cache
        self._carregar_propostas_do_banco()
        
        self.logger.info("âœ… GerenciadorPropostas inicializado com %d propostas no banco", len(self.propostas_cache))

    # =====================================================================
    # DATABASE
    # =====================================================================

    def _inicializar_banco(self) -> None:
        """Cria tabelas se não existirem."""
        with self._lock_db:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            # Tabela principal
            cur.execute("""
                CREATE TABLE IF NOT EXISTS propostas (
                    id TEXT PRIMARY KEY,
                    ia_solicitante TEXT NOT NULL,
                    nome_ferramenta TEXT NOT NULL,
                    descricao TEXT,
                    motivo TEXT NOT NULL,
                    intencao_uso TEXT NOT NULL,
                    categoria TEXT,
                    tipo_ferramenta TEXT,
                    codigo_ou_comando TEXT,
                    status TEXT DEFAULT 'PENDENTE_ANALISE',
                    hash_conteudo TEXT UNIQUE,
                    timestamp_criacao TIMESTAMP,
                    timestamp_ultima_atualizacao TIMESTAMP,
                    progresso_json TEXT,
                    testes_json TEXT,
                    seguranca_json TEXT,
                    aprovacao_json TEXT,
                    deploy_json TEXT
                )
            """)
            
            # Histórico de status
            cur.execute("""
                CREATE TABLE IF NOT EXISTS propostas_historico_status (
                    id TEXT PRIMARY KEY,
                    proposta_id TEXT NOT NULL,
                    status_anterior TEXT,
                    status_novo TEXT NOT NULL,
                    por_humano TEXT,
                    motivo TEXT,
                    timestamp TIMESTAMP,
                    FOREIGN KEY(proposta_id) REFERENCES propostas(id)
                )
            """)
            
            # Propostas similares
            cur.execute("""
                CREATE TABLE IF NOT EXISTS propostas_similares (
                    id TEXT PRIMARY KEY,
                    proposta_original_id TEXT NOT NULL,
                    proposta_similar_id TEXT NOT NULL,
                    score_similaridade FLOAT,
                    FOREIGN KEY(proposta_original_id) REFERENCES propostas(id),
                    FOREIGN KEY(proposta_similar_id) REFERENCES propostas(id)
                )
            """)
            
            # Índices para performance
            cur.execute("CREATE INDEX IF NOT EXISTS idx_status ON propostas(status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ia ON propostas(ia_solicitante)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON propostas(timestamp_criacao)")
            
            conn.commit()
            conn.close()
            self.logger.debug("âœ… Banco de dados inicializado")

    def _carregar_propostas_do_banco(self) -> None:
        """Carrega todas as propostas do banco para cache."""
        with self._lock_db:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            cur.execute("SELECT * FROM propostas")
            rows = cur.fetchall()
            
            with self._lock:
                for row in rows:
                    proposta = dict(row)
                    # Parse JSON fields
                    for field in ["progresso_json", "testes_json", "seguranca_json", "aprovacao_json", "deploy_json"]:
                        if proposta.get(field):
                            try:
                                proposta[field] = json.loads(proposta[field])
                            except Exception:
                                proposta[field] = {}
                    self.propostas_cache[proposta["id"]] = proposta
            
            conn.close()

    def _salvar_proposta_no_banco(self, proposta_id: str) -> bool:
        """Salva proposta no banco."""
        with self._lock:
            proposta = self.propostas_cache.get(proposta_id)
        
        if not proposta:
            return False
        
        with self._lock_db:
            try:
                conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
                cur = conn.cursor()
                
                # Serializar JSON fields
                progresso_json = json.dumps(proposta.get("progresso_json") or {})
                testes_json = json.dumps(proposta.get("testes_json") or {})
                seguranca_json = json.dumps(proposta.get("seguranca_json") or {})
                aprovacao_json = json.dumps(proposta.get("aprovacao_json") or {})
                deploy_json = json.dumps(proposta.get("deploy_json") or {})
                
                cur.execute("""
                    INSERT OR REPLACE INTO propostas
                    (id, ia_solicitante, nome_ferramenta, descricao, motivo, intencao_uso,
                     categoria, tipo_ferramenta, codigo_ou_comando, status, hash_conteudo,
                     timestamp_criacao, timestamp_ultima_atualizacao,
                     progresso_json, testes_json, seguranca_json, aprovacao_json, deploy_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    proposta.get("id"),
                    proposta.get("ia_solicitante"),
                    proposta.get("nome_ferramenta"),
                    proposta.get("descricao"),
                    proposta.get("motivo"),
                    proposta.get("intencao_uso"),
                    proposta.get("categoria"),
                    proposta.get("tipo_ferramenta"),
                    proposta.get("codigo_ou_comando"),
                    proposta.get("status"),
                    proposta.get("hash_conteudo"),
                    proposta.get("timestamp_criacao"),
                    proposta.get("timestamp_ultima_atualizacao"),
                    progresso_json,
                    testes_json,
                    seguranca_json,
                    aprovacao_json,
                    deploy_json
                ))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.exception("Erro ao salvar proposta: %s", e)
                return False

    def _registrar_mudanca_status(self, proposta_id: str, status_anterior: str, status_novo: str, 
                                   por_humano: str = None, motivo: str = None) -> bool:
        """Registra mudança de status no histórico."""
        with self._lock_db:
            try:
                conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
                cur = conn.cursor()
                
                historico_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO propostas_historico_status
                    (id, proposta_id, status_anterior, status_novo, por_humano, motivo, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    historico_id,
                    proposta_id,
                    status_anterior,
                    status_novo,
                    por_humano,
                    motivo,
                    datetime.datetime.utcnow().isoformat()
                ))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.exception("Erro ao registrar mudança de status: %s", e)
                return False

    # =====================================================================
    # CRIAR PROPOSTA (IA solicita)
    # =====================================================================

    def criar_proposta(
        self,
        ia_solicitante: str,
        nome_ferramenta: str,
        descricao: str,
        motivo: str,
        intencao_uso: str,
        categoria: str,
        tipo_ferramenta: str,
        codigo_ou_comando: str = ""  # âœ… AGORA OPCIONAL
    ) -> Tuple[bool, str, Optional[str]]:
        """
        IA cria proposta de nova ferramenta.Returns:
            (sucesso, mensagem, proposta_id)
        """
        # âœ… FIX: Validar campos obrigatórios (SEM codigo_ou_comando)
        if not all([ia_solicitante, nome_ferramenta, motivo, intencao_uso, tipo_ferramenta]):
            return False, "Campos obrigatórios ausentes", None
        
        # Gerar hash do conteúdo (se houver código)
        if codigo_ou_comando:
            conteudo_hash = hashlib.sha256(
                f"{nome_ferramenta}:{codigo_ou_comando}".encode()
            ).hexdigest()
        else:
            conteudo_hash = hashlib.sha256(
                f"{nome_ferramenta}:{ia_solicitante}:{datetime.datetime.utcnow().isoformat()}".encode()
            ).hexdigest()
        
        # Verificar duplicatas exatas
        duplicata_exata = self._verificar_duplicata_exata(conteudo_hash)
        if duplicata_exata:
            return False, f"Proposta similar já existe: {duplicata_exata}", None
        
        proposta_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat()
        
        proposta = {
            "id": proposta_id,
            "ia_solicitante": ia_solicitante,
            "nome_ferramenta": nome_ferramenta,
            "descricao": descricao or "",
            "motivo": motivo,
            "intencao_uso": intencao_uso,
            "categoria": categoria or "geral",
            "tipo_ferramenta": tipo_ferramenta,
            "codigo_ou_comando": codigo_ou_comando,
            "status": "PENDENTE_ANALISE",
            "hash_conteudo": conteudo_hash,
            "timestamp_criacao": now,
            "timestamp_ultima_atualizacao": now,
            "progresso_json": {},
            "testes_json": {},
            "seguranca_json": {},
            "aprovacao_json": {},
            "deploy_json": {}
        }
        
        # Salvar em cache e banco
        with self._lock:
            self.propostas_cache[proposta_id] = proposta
        
        self._salvar_proposta_no_banco(proposta_id)
        self._registrar_mudanca_status(proposta_id, None, "PENDENTE_ANALISE")
        
        msg = f"âœ… Proposta '{nome_ferramenta}' criada com ID {proposta_id}"
        self.logger.info(msg)
        
        # Notificar Coração
        self._notificar_coacao("PROPOSTA_FERRAMENTA_CRIADA", {
            "proposta_id": proposta_id,
            "nome_ferramenta": nome_ferramenta,
            "ia_solicitante": ia_solicitante,
            "motivo": motivo
        })
        
        return True, msg, proposta_id

    # =====================================================================
    # âœ… NOVO: ATUALIZAR CÓDIGO (IA envia código após aprovação)
    # =====================================================================

    def atualizar_codigo_proposta(self, proposta_id: str, ia_solicitante: str, codigo: str) -> Tuple[bool, str]:
        """
        IA envia código para proposta já criada.Pode ser chamado após aprovação, antes de construir.
        """
        with self._lock:
            proposta = self.propostas_cache.get(proposta_id)
        
        if not proposta:
            return False, "âŒ Proposta não encontrada"
        
        if proposta.get("ia_solicitante") != ia_solicitante:
            return False, "âŒ Apenas a IA solicitante pode atualizar"
        
        if proposta.get("status") not in ["APROVADO_CONSTRUÇÍO"]:
            return False, f"âŒ Proposta não está em construção (status: {proposta.get('status')})"
        
        if not codigo or not codigo.strip():
            return False, "âŒ Código não pode ser vazio"
        
        with self._lock:
            proposta["codigo_ou_comando"] = codigo
            proposta["timestamp_ultima_atualizacao"] = datetime.datetime.utcnow().isoformat()
        
        self._salvar_proposta_no_banco(proposta_id)
        
        msg = "âœ… Código atualizado com sucesso"
        self.logger.info(msg)
        
        # Notificar
        self._notificar_coacao("PROPOSTA_CODIGO_ATUALIZADO", {
            "proposta_id": proposta_id,
            "ia_solicitante": ia_solicitante,
            "tamanho_codigo": len(codigo)
        })
        
        return True, msg

    # =====================================================================
    # VERIFICAR DUPLICATAS
    # =====================================================================

    def _verificar_duplicata_exata(self, hash_conteudo: str) -> Optional[str]:
        """Verifica se já existe proposta com hash idêntico."""
        with self._lock:
            for pid, prop in self.propostas_cache.items():
                if prop.get("hash_conteudo") == hash_conteudo:
                    if prop.get("status") != "REJEITADO":
                        return pid
        return None

    def verificar_duplicatas_similares(self, proposta_id: str, threshold: float = 0.7) -> List[Tuple[str, float]]:
        """
        Verifica propostas similares usando Levenshtein distance.Returns: [(proposta_id_similar, score_similaridade), ...]
        """
        with self._lock:
            proposta = self.propostas_cache.get(proposta_id)
        
        if not proposta:
            return []
        
        nome_base = proposta.get("nome_ferramenta", "").lower()
        similares = []
        
        with self._lock:
            for pid, prop in self.propostas_cache.items():
                if pid == proposta_id:
                    continue
                
                nome_comp = prop.get("nome_ferramenta", "").lower()
                score = self._calcular_similaridade(nome_base, nome_comp)
                
                if score >= threshold:
                    similares.append((pid, score))
        
        # Registrar no banco
        if similares:
            with self._lock_db:
                conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
                cur = conn.cursor()
                
                for similar_id, score in similares:
                    rel_id = str(uuid.uuid4())
                    try:
                        cur.execute("""
                            INSERT OR IGNORE INTO propostas_similares
                            (id, proposta_original_id, proposta_similar_id, score_similaridade)
                            VALUES (?, ?, ?, ?)
                        """, (rel_id, proposta_id, similar_id, score))
                    except Exception:
                        pass
                
                conn.commit()
                conn.close()
        
        return similares

    def _calcular_similaridade(self, str1: str, str2: str) -> float:
        """Calcula Levenshtein distance normalizada (0-1)."""
        return SequenceMatcher(None, str1, str2).ratio()

    # =====================================================================
    # LISTAR PROPOSTAS
    # =====================================================================

    def listar_pendentes(self) -> List[Dict[str, Any]]:
        """Lista propostas aguardando decisão humana (PENDENTE_ANALISE)."""
        with self._lock:
            return [
                p for p in self.propostas_cache.values()
                if p.get("status") == "PENDENTE_ANALISE"
            ]

    def listar_em_analise(self) -> List[Dict[str, Any]]:
        """Lista propostas em análise (EM_ANALISE)."""
        with self._lock:
            return [
                p for p in self.propostas_cache.values()
                if p.get("status") == "EM_ANALISE"
            ]

    def listar_em_construcao(self) -> List[Dict[str, Any]]:
        """Lista propostas em construção."""
        with self._lock:
            return [
                p for p in self.propostas_cache.values()
                if p.get("status") in ["APROVADO_CONSTRUÇÍO", "EM_CONSTRUCAO"]
            ]

    def listar_pronto_deploy(self) -> List[Dict[str, Any]]:
        """Lista propostas prontas para deploy."""
        with self._lock:
            return [
                p for p in self.propostas_cache.values()
                if p.get("status") == "PRONTO_APROVACAO_FINAL"
            ]

    def listar_em_producao(self) -> List[Dict[str, Any]]:
        """Lista ferramentas em produção."""
        with self._lock:
            return [
                p for p in self.propostas_cache.values()
                if p.get("status") == "EM_PRODUCAO"
            ]

    def obter_proposta(self, proposta_id: str) -> Optional[Dict[str, Any]]:
        """Obtém dados completos de uma proposta."""
        with self._lock:
            return self.propostas_cache.get(proposta_id)

    # =====================================================================
    # APROVAÇÍO / REJEIÇÍO / ANÍLISE
    # =====================================================================

    def aprovar_proposta(self, proposta_id: str, por_humano: str, motivo: str = "") -> Tuple[bool, str]:
        """
        Humano aprova proposta â†’ passa para APROVADO_CONSTRUÇÍO.IA pode começar a construir.
        """
        with self._lock:
            proposta = self.propostas_cache.get(proposta_id)
        
        if not proposta:
            return False, "Proposta não encontrada"
        
        if proposta.get("status") not in ["PENDENTE_ANALISE", "EM_ANALISE"]:
            return False, f"Proposta não pode ser aprovada (status: {proposta.get('status')})"
        
        # Atualizar
        status_anterior = proposta.get("status")
        with self._lock:
            proposta["status"] = "APROVADO_CONSTRUÇÍO"
            proposta["timestamp_ultima_atualizacao"] = datetime.datetime.utcnow().isoformat()
        
        self._salvar_proposta_no_banco(proposta_id)
        self._registrar_mudanca_status(proposta_id, status_anterior, "APROVADO_CONSTRUÇÍO", por_humano, motivo)
        
        msg = f"âœ… Proposta {proposta_id} aprovada por {por_humano}"
        self.logger.info(msg)
        
        # Notificar
        self._notificar_coacao("PROPOSTA_APROVADA", {
            "proposta_id": proposta_id,
            "nome_ferramenta": proposta.get("nome_ferramenta"),
            "por_humano": por_humano,
            "motivo": motivo
        })
        
        return True, msg

    def rejeitar_proposta(self, proposta_id: str, por_humano: str, motivo_rejeicao: str) -> Tuple[bool, str]:
        """
        Humano rejeita proposta â†’ passa para REJEITADO.Proposta não pode ser duplicada depois.
        """
        with self._lock:
            proposta = self.propostas_cache.get(proposta_id)
        
        if not proposta:
            return False, "Proposta não encontrada"
        
        # Atualizar
        status_anterior = proposta.get("status")
        with self._lock:
            proposta["status"] = "REJEITADO"
            proposta["timestamp_ultima_atualizacao"] = datetime.datetime.utcnow().isoformat()
        
        self._salvar_proposta_no_banco(proposta_id)
        self._registrar_mudanca_status(proposta_id, status_anterior, "REJEITADO", por_humano, motivo_rejeicao)
        
        msg = f"âŒ Proposta {proposta_id} rejeitada por {por_humano}: {motivo_rejeicao}"
        self.logger.info(msg)
        
        # Notificar
        self._notificar_coacao("PROPOSTA_REJEITADA", {
            "proposta_id": proposta_id,
            "nome_ferramenta": proposta.get("nome_ferramenta"),
            "por_humano": por_humano,
            "motivo": motivo_rejeicao
        })
        
        return True, msg

    def mover_para_analise(self, proposta_id: str, por_humano: str, motivo: str = "") -> Tuple[bool, str]:
        """
        Humano marca para analisar depois â†’ passa para EM_ANALISE.Não toma decisão agora, apenas estaciona.
        """
        with self._lock:
            proposta = self.propostas_cache.get(proposta_id)
        
        if not proposta:
            return False, "Proposta não encontrada"
        
        if proposta.get("status") != "PENDENTE_ANALISE":
            return False, "Proposta não está pendente"
        
        # Atualizar
        with self._lock:
            proposta["status"] = "EM_ANALISE"
            proposta["timestamp_ultima_atualizacao"] = datetime.datetime.utcnow().isoformat()
        
        self._salvar_proposta_no_banco(proposta_id)
        self._registrar_mudanca_status(proposta_id, "PENDENTE_ANALISE", "EM_ANALISE", por_humano, motivo)
        
        msg = f"â¸ï¸ Proposta {proposta_id} movida para análise posterior"
        self.logger.info(msg)
        
        return True, msg

    # =====================================================================
    # ATUALIZAR STATUS (durante construção)
    # =====================================================================

    def atualizar_progresso(self, proposta_id: str, percentual: int, etapa: str, log: str = "") -> bool:
        """Atualiza progresso durante construção."""
        with self._lock:
            proposta = self.propostas_cache.get(proposta_id)
        
        if not proposta:
            return False
        
        with self._lock:
            proposta["status"] = "EM_CONSTRUCAO"
            proposta["progresso_json"] = {
                "percentual": percentual,
                "etapa": etapa,
                "log": log,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            proposta["timestamp_ultima_atualizacao"] = datetime.datetime.utcnow().isoformat()
        
        self._salvar_proposta_no_banco(proposta_id)
        return True

    def marcar_pronto_testes(self, proposta_id: str) -> Tuple[bool, str]:
        """Marca como pronto para testes."""
        with self._lock:
            proposta = self.propostas_cache.get(proposta_id)
        
        if not proposta:
            return False, "Proposta não encontrada"
        
        status_anterior = proposta.get("status")
        with self._lock:
            proposta["status"] = "PRONTO_TESTES"
            proposta["timestamp_ultima_atualizacao"] = datetime.datetime.utcnow().isoformat()
        
        self._salvar_proposta_no_banco(proposta_id)
        self._registrar_mudanca_status(proposta_id, status_anterior, "PRONTO_TESTES")
        
        return True, "Proposta marcada como pronta para testes"

    def registrar_resultado_testes(self, proposta_id: str, passou: bool, detalhes: str) -> bool:
        """Registra resultado dos testes."""
        with self._lock:
            proposta = self.propostas_cache.get(proposta_id)
        
        if not proposta:
            return False
        
        with self._lock:
            proposta["testes_json"] = {
                "passou": passou,
                "detalhes": detalhes,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            
            if passou:
                proposta["status"] = "PRONTO_SEGURANCA"
            else:
                proposta["status"] = "FALHA_CONSTRUCAO"
            
            proposta["timestamp_ultima_atualizacao"] = datetime.datetime.utcnow().isoformat()
        
        self._salvar_proposta_no_banco(proposta_id)
        
        if passou:
            self._registrar_mudanca_status(proposta_id, "PRONTO_TESTES", "PRONTO_SEGURANCA")
        else:
            self._registrar_mudanca_status(proposta_id, "PRONTO_TESTES", "FALHA_CONSTRUCAO")
        
        return True

    def registrar_analise_seguranca(self, proposta_id: str, risco: str, score: int, relatorio: str) -> bool:
        """Registra resultado da análise de segurança."""
        with self._lock:
            proposta = self.propostas_cache.get(proposta_id)
        
        if not proposta:
            return False
        
        with self._lock:
            proposta["seguranca_json"] = {
                "risco": risco,  # BAIXO, MÉDIO, ALTO, CRÍTICO
                "score": score,  # 0-100
                "relatorio": relatorio,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            
            if risco != "CRÍTICO":
                proposta["status"] = "PRONTO_APROVACAO_FINAL"
            else:
                proposta["status"] = "REJEITADO"
            
            proposta["timestamp_ultima_atualizacao"] = datetime.datetime.utcnow().isoformat()
        
        self._salvar_proposta_no_banco(proposta_id)
        
        if risco != "CRÍTICO":
            self._registrar_mudanca_status(proposta_id, "PRONTO_SEGURANCA", "PRONTO_APROVACAO_FINAL")
        else:
            self._registrar_mudanca_status(proposta_id, "PRONTO_SEGURANCA", "REJEITADO", motivo="Risco crítico detectado")
        
        return True

    def aprovar_deploy(self, proposta_id: str, por_humano: str, motivo: str = "") -> Tuple[bool, str]:
        """Aprovação final â†’ deploy em produção."""
        with self._lock:
            proposta = self.propostas_cache.get(proposta_id)
        
        if not proposta:
            return False, "Proposta não encontrada"
        
        if proposta.get("status") != "PRONTO_APROVACAO_FINAL":
            return False, f"Proposta não está pronta para deploy (status: {proposta.get('status')})"
        
        status_anterior = proposta.get("status")
        with self._lock:
            proposta["status"] = "EM_PRODUCAO"
            proposta["deploy_json"] = {
                "em_producao": True,
                "versao": "1.0",
                "data_deploy": datetime.datetime.utcnow().isoformat(),
                "aprovado_por": por_humano,
                "uso_contador": 0
            }
            proposta["timestamp_ultima_atualizacao"] = datetime.datetime.utcnow().isoformat()
        
        self._salvar_proposta_no_banco(proposta_id)
        self._registrar_mudanca_status(proposta_id, status_anterior, "EM_PRODUCAO", por_humano, motivo)
        
        msg = f"âœ… Proposta {proposta_id} em produção!"
        self.logger.info(msg)
        
        # Notificar
        self._notificar_coacao("FERRAMENTA_DEPLOY", {
            "proposta_id": proposta_id,
            "nome_ferramenta": proposta.get("nome_ferramenta"),
            "versao": "1.0"
        })
        
        return True, msg

    # =====================================================================
    # HISTÓRICO
    # =====================================================================

    def obter_historico(self, proposta_id: str) -> List[Dict[str, Any]]:
        """Retorna histórico de mudanças de status."""
        with self._lock_db:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            cur.execute("""
                SELECT * FROM propostas_historico_status
                WHERE proposta_id = ?
                ORDER BY timestamp ASC
            """, (proposta_id,))
            
            historico = [dict(row) for row in cur.fetchall()]
            conn.close()
        
        return historico

    # =====================================================================
    # NOTIFICAÇÕES
    # =====================================================================

    def _notificar_coacao(self, tipo_evento: str, dados: Dict[str, Any]) -> None:
        """Notifica Coração sobre eventos importantes."""
        try:
            if hasattr(self.coracao, "ui_queue"):
                self.coracao.ui_queue.put_nowait({
                    "tipo_resp": f"PROPOSTAS_{tipo_evento}",
                    "dados": dados,
                    "timestamp": datetime.datetime.utcnow().isoformat()
                })
        except Exception as e:
            self.logger.debug("Erro ao notificar Coração: %s", e)

    # =====================================================================
    # SHUTDOWN
    # =====================================================================

    def shutdown(self) -> None:
        """Desliga gerenciador."""
        self.logger.info("ðŸ›‘ Desligando GerenciadorPropostas...")
        # Todas as propostas já foram salvas, nada a fazer
        self.logger.info("âœ… GerenciadorPropostas desligado")


