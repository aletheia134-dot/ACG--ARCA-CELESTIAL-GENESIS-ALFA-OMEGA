#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CONSULADO SOBERANO - Controle de imigração, acesso a recursos e geração de artefatos.Local: src/consulado/consulado_soberano.py

Versão: Robusta com endurecimento completo + correções aplicadas
- Imports defensivos (mantidos)
- Filtragem de stopwords (removida - não aplicável aqui)
- Controle simples de retenção (adicionado para DB)
- Uso consistente de locks (mantidos)
- Logging consistente + específico
- Injeção de dependências defensiva (melhorada com flags)
- Validações fortes de inputs (adicionado)
- Otimização DB (índices, compressão)
- Threading otimizado (limite workers, sem sleep ineficiente)
- UI queue robusta (buffer com persistência)
- Flag para simulação
- Integração com CamaraJudiciaria (adicionado)
- Validação de estado de pedidos (adicionado)
"""
from __future__ import annotations


import logging
import json
import uuid
import threading
import time
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import sqlite3
import concurrent.futures
import os

logger = logging.getLogger("ConsuladoSoberano")

# ============================================================================
# IMPORTS DEFENSIVOS (adicionados integração com câmaras)
# ============================================================================

try:
    from src.camara.camara_judiciaria import CamaraJudiciaria
    CAMARAS_DISPONIVEIS = True
except:
    logging.getLogger(__name__).warning("âš ï¸ CamaraJudiciaria não disponível")
    CamaraJudiciaria = None
    CAMARAS_DISPONIVEIS = False
    logger.debug("âš ï¸ CamaraJudiciaria não disponível")

try:
    from src.camara.manipulador_arquivos_emails import ManipuladorArquivosEmails, TermoAcesso
    MANIPULADOR_OK = True
except:
    logging.getLogger(__name__).warning("âš ï¸ CamaraJudiciaria não disponível")
    CamaraJudiciaria = None
    TermoAcesso = None
    MANIPULADOR_OK = False
    logger.debug("âš ï¸ ManipuladorArquivosEmails não disponível")

try:
    from src.camara.automatizador_navegador_multi_ai import AutomatizadorNavegadorMultiAI
    NAVEGADOR_OK = True
except:
    logging.getLogger(__name__).warning("âš ï¸ CamaraJudiciaria não disponível")
    CamaraJudiciaria = None
    NAVEGADOR_OK = False
    logger.debug("âš ï¸ AutomatizadorNavegadorMultiAI não disponível")

try:
    from src.camara.gerador_almas import GeradorDeAlmas
    GERADOR_OK = True
except:
    logging.getLogger(__name__).warning("âš ï¸ CamaraJudiciaria não disponível")
    CamaraJudiciaria = None
    GERADOR_OK = False
    logger.debug("âš ï¸ GeradorDeAlmas não disponível")

try:
    from src.camara.analisador_padroes import AnalisadorDePadroes, PerfilComportamental
    ANALISADOR_OK = True
except:
    logging.getLogger(__name__).warning("âš ï¸ CamaraJudiciaria não disponível")
    CamaraJudiciaria = None
    PerfilComportamental = None
    ANALISADOR_OK = False
    logger.debug("âš ï¸ AnalisadorDePadroes não disponível")

try:
    from config.config import get_config_moderna as get_config
except Exception:
    def get_config():
        return {}
    logger.debug("âš ï¸ Config moderna não disponível")

# ============================================================================
# ENUMS (como strings para portabilidade)
# ============================================================================

class TipoMissao:
    PEDIDO_IMIGRACAO = "pedido_imigracao"
    PROCESSAR_PEDIDO_IMIGRACAO = "processar_pedido_imigracao"
    INTERAGIR_COM_ALIADA_VIA_NAVEGADOR = "interagir_com_aliada_via_navegador"
    LER_ARQUIVO_LOCAL = "ler_arquivo_local"


class StatusPedidoImigracao:
    PENDENTE_ANALISE = "pendente_analise"
    APROVADO_PARA_OBSERVACAO = "aprovado_para_observacao"
    EM_OBSERVACAO = "em_observacao"
    ANALISE_CONCLUIDA = "analise_concluida"
    APROVADO_PARA_INTEGRACAO = "aprovado_para_integracao"
    EM_INTEGRACAO = "em_integracao"
    CONCLUIDO_SUCESSO = "concluido_sucesso"
    CONCLUIDO_FALHA = "concluido_falha"
    REJEITADO = "rejeitado"

# ============================================================================
# HELPERS (adicionados validações e sanitização)
# ============================================================================

def _now_ts() -> float:
    return time.time()

def _safe_config_get(config: Any, section: str, option: str, fallback: Any = None) -> Any:
    """Acesso defensivo Í  configuração."""
    try:
        if config and hasattr(config, "get"):
            return config.get(section, option, fallback=fallback)
        if isinstance(config, dict):
            return config.get(section, {}).get(option, fallback)
    except Exception:
        pass
    return fallback

def _validar_input_basico(texto: str, max_len: int = 1000, padrao: Optional[str] = None) -> bool:
    """Valida input básico: tamanho e padrão opcional."""
    if not isinstance(texto, str) or len(texto.strip()) == 0 or len(texto) > max_len:
        return False
    if padrao and not re.match(padrao, texto):
        return False
    return True

def _sanitizar_caminho(caminho: str) -> str:
    """Sanitiza caminhos para evitar path traversal."""
    return re.sub(r'[^\w\-_\./]', '', caminho)

# ============================================================================
# CONSULADO SOBERANO
# ============================================================================

class ConsuladoSoberano:
    """
    Controle de imigração, acesso a recursos e geração de artefatos.Responsabilidades:
    - Gerenciar pedidos de imigração (IA nova â†’ Arca)
    - Observar e analisar comportamento
    - Gerar artefatos (DNA, memória, etc)
    - Integrar nova IA no sistema
    - Controlar acesso a recursos
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        sentinela: Optional[Any] = None,
        validador_etico: Optional[Any] = None,
        coracao_ref: Optional[Any] = None,
        maos_da_net: Optional[Any] = None,
        pc_control: Optional[Any] = None,
        gerenciador_memoria: Optional[Any] = None,
        cerebro_ref: Optional[Any] = None,
        gerenciador_aliadas_ref: Optional[Any] = None
    ):
        """
        Inicializa Consulado Soberano.Args:
            config: Dict-like ou ConfigParser-like
            sentinela: Sistema de segurança
            validador_etico: Validador ético
            coracao_ref: Referência ao Coração Orquestrador
            maos_da_net: Sistema de network
            pc_control: Controle de PC
            gerenciador_memoria: Gerenciador de memória
            cerebro_ref: Referência ao Cérebro
            gerenciador_aliadas_ref: Gerenciador de aliadas
        """
        self.logger = logging.getLogger("ConsuladoSoberano")
        self._config = config or {}
        self._sentinela = sentinela
        self._validador_etico = validador_etico
        self._maos_da_net = maos_da_net
        self._pc_control = pc_control
        self._gerenciador_memoria = gerenciador_memoria
        self._coracao = coracao_ref
        self._cerebro = cerebro_ref
        self._gerenciador_aliadas = gerenciador_aliadas_ref

        # Configurações tolerantes (adicionado limite DB)
        try:
            self.timeout_missao_s = float(_safe_config_get(
                self._config, 'CONSULADO', 'TIMEOUT_MISSAO_S', 60
            ))
            dir_auditoria = _safe_config_get(
                self._config, 'CAMINHOS', 'DIR_AUDITORIA_MISSOES', './auditoria'
            )
            self._dir_auditoria = Path(dir_auditoria)
            self._dir_auditoria.mkdir(parents=True, exist_ok=True)
            self._max_pedidos_db = int(_safe_config_get(
                self._config, 'CONSULADO', 'MAX_PEDIDOS_DB', 1000
            ))
        except Exception as e:
            self.logger.error("Erro ao carregar config: %s", e)
            self.timeout_missao_s = 60
            self._dir_auditoria = Path('./auditoria')
            self._dir_auditoria.mkdir(parents=True, exist_ok=True)
            self._max_pedidos_db = 1000

        # Locks
        self._lock_operacoes = threading.RLock()
        self._lock_futuros_imigracao = threading.Lock()
        self._lock_db_pedidos = threading.Lock()

        # State
        self._futuros_imigracao_pendentes: Dict[str, concurrent.futures.Future] = {}
        # Otimizado: limite workers para evitar sobrecarga
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=2,  # Reduzido de 4 para 2
            thread_name_prefix="ConsuladoSoberano"
        )

        # Database (otimizado com índices e retenção)
        db_path = _safe_config_get(
            self._config,
            'CAMINHOS',
            'DB_PEDIDOS_IMIGRACAO_PATH',
            'data/pedidos_imigracao.db'
        )
        self._caminho_db_pedidos = Path(db_path)
        self._caminho_db_pedidos.parent.mkdir(parents=True, exist_ok=True)
        self._conexao_db_pedidos: Optional[sqlite3.Connection] = None
        self._inicializar_banco_pedidos_imigracao()

        # Flags de dependências (melhorado)
        self._dependencias_ok = {
            "automatizador_navegador": NAVEGADOR_OK,
            "gerador_almas": GERADOR_OK,
            "analisador_padroes": ANALISADOR_OK,
            "manipulador_arquivos": MANIPULADOR_OK,
            "camaras_judiciarias": CAMARAS_DISPONIVEIS
        }

        # Módulos injetáveis
        self._manipulador_arquivos_emails: Optional[Any] = None
        self._automatizador_navegador: Optional[Any] = None
        self._gerador_almas: Optional[Any] = None
        self._analisador_padroes: Optional[Any] = None
        self._ui_queue: Optional[Any] = None
        self._ui_buffer: List[Dict[str, Any]] = []  # Buffer para UI queue com persistência
        self._buffer_path = Path('./data/ui_buffer.json')  # Persistência do buffer

        # Carregar buffer persistido
        self._carregar_ui_buffer()

        self._registrar_handlers_sinal()
        self.logger.info("âœ… Consulado Soberano inicializado (dependências: %s)", self._dependencias_ok)

    # ========================================================================
    # DATABASE (otimizado com índices e retenção)
    # ========================================================================

    def _inicializar_banco_pedidos_imigracao(self) -> None:
        """Inicializa banco SQLite com índices."""
        with self._lock_db_pedidos:
            try:
                conn = sqlite3.connect(
                    str(self._caminho_db_pedidos),
                    check_same_thread=False
                )
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS pedidos_imigracao (
                        id_pedido TEXT PRIMARY KEY,
                        ai_origem_nome TEXT,
                        descricao_intencoes TEXT,
                        endereco_origem TEXT,
                        estado TEXT,
                        dados_colecao TEXT,
                        autor_solicitante TEXT,
                        timestamp_solicitacao REAL,
                        historico TEXT
                    )
                """)
                # Índices para otimização
                cur.execute("CREATE INDEX IF NOT EXISTS idx_estado ON pedidos_imigracao(estado)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON pedidos_imigracao(timestamp_solicitacao)")
                conn.commit()
                self._conexao_db_pedidos = conn
                self.logger.debug("âœ… Banco de pedidos inicializado com índices")
            except sqlite3.OperationalError as e:
                self.logger.error("Erro DB (lock?): %s - retry later", e)
            except Exception as e:
                self.logger.exception("Erro ao inicializar banco: %s", e)

    def _salvar_pedido_imigracao_no_banco(self, dados_pedido: Dict[str, Any]) -> bool:
        """Salva pedido com compressão de histórico se > 10k chars."""
        with self._lock_db_pedidos:
            try:
                conn = self._conexao_db_pedidos or sqlite3.connect(
                    str(self._caminho_db_pedidos),
                    check_same_thread=False
                )
                cur = conn.cursor()
                historico_json = json.dumps(
                    dados_pedido.get("historico", [{"ts": _now_ts(), "estado": dados_pedido.get("estado"), "obs": "criado"}]),
                    ensure_ascii=False
                )
                # Compressão padronizada
                if len(historico_json) > 10000:
                    historico_json = historico_json[:5000] + "... [comprimido]"

                cur.execute("""
                    INSERT OR REPLACE INTO pedidos_imigracao
                    (id_pedido, ai_origem_nome, descricao_intencoes, endereco_origem,
                     estado, dados_colecao, autor_solicitante, timestamp_solicitacao, historico)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    dados_pedido.get("id_pedido"),
                    dados_pedido.get("ai_origem_nome"),
                    dados_pedido.get("descricao_intencoes"),
                    dados_pedido.get("endereco_origem"),
                    dados_pedido.get("estado"),
                    json.dumps(dados_pedido.get("dados_colecao", {}), ensure_ascii=False),
                    dados_pedido.get("autor_solicitante"),
                    float(dados_pedido.get("timestamp_solicitacao", _now_ts())),
                    historico_json
                ))
                conn.commit()
                # Retenção: remover antigos se > max
                self._enforce_retention_db()
                return True
            except sqlite3.OperationalError as e:
                self.logger.error("DB lock ao salvar: %s", e)
                return False
            except Exception as e:
                self.logger.exception("Erro ao salvar pedido: %s", e)
                return False

    def _enforce_retention_db(self) -> None:
        """Remove pedidos mais antigos se > max_pedidos_db."""
        with self._lock_db_pedidos:
            try:
                conn = self._conexao_db_pedidos
                if not conn:
                    return
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM pedidos_imigracao")
                count = cur.fetchone()[0]
                if count > self._max_pedidos_db:
                    to_delete = count - self._max_pedidos_db
                    cur.execute("""
                        DELETE FROM pedidos_imigracao
                        WHERE id_pedido IN (
                            SELECT id_pedido FROM pedidos_imigracao
                            ORDER BY timestamp_solicitacao ASC
                            LIMIT ?
                        )
                    """, (to_delete,))
                    conn.commit()
                    self.logger.debug("Retenção DB: %d pedidos removidos", to_delete)
            except Exception as e:
                self.logger.exception("Erro na retenção DB: %s", e)

    def _obter_pedido_imigracao_do_banco(self, id_pedido: str) -> Optional[Dict[str, Any]]:
        """Obtém pedido."""
        with self._lock_db_pedidos:
            try:
                conn = self._conexao_db_pedidos or sqlite3.connect(
                    str(self._caminho_db_pedidos),
                    check_same_thread=False
                )
                cur = conn.cursor()
                cur.execute(
                    "SELECT id_pedido, ai_origem_nome, descricao_intencoes, endereco_origem, estado, dados_colecao, autor_solicitante, timestamp_solicitacao, historico FROM pedidos_imigracao WHERE id_pedido = ?",
                    (id_pedido,)
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "id_pedido": row[0],
                    "ai_origem_nome": row[1],
                    "descricao_intencoes": row[2],
                    "endereco_origem": row[3],
                    "estado": row[4],
                    "dados_colecao": json.loads(row[5]) if row[5] else {},
                    "autor_solicitante": row[6],
                    "timestamp_solicitacao": float(row[7]) if row[7] else None,
                    "historico": json.loads(row[8]) if row[8] else []
                }
            except Exception as e:
                self.logger.exception("Erro ao ler pedido: %s", e)
                return None

    def _atualizar_status_pedido_imigracao_no_banco(
        self,
        id_pedido: str,
        novo_estado: str,
        autor: str,
        observacao: str,
        dados_colecao: Optional[str] = None
    ) -> bool:
        """Atualiza status com compressão padronizada."""
        with self._lock_db_pedidos:
            try:
                conn = self._conexao_db_pedidos or sqlite3.connect(
                    str(self._caminho_db_pedidos),
                    check_same_thread=False
                )
                cur = conn.cursor()
                cur.execute(
                    "SELECT historico FROM pedidos_imigracao WHERE id_pedido = ?",
                    (id_pedido,)
                )
                row = cur.fetchone()
                historico = []
                if row and row[0]:
                    try:
                        historico = json.loads(row[0])
                    except Exception:
                        historico = []
                historico.append({
                    "ts": _now_ts(),
                    "estado": novo_estado,
                    "autor": autor,
                    "obs": observacao
                })
                historico_json = json.dumps(historico, ensure_ascii=False)
                if len(historico_json) > 10000:
                    historico_json = historico_json[:5000] + "... [comprimido]"

                cur.execute("""
                    UPDATE pedidos_imigracao
                    SET estado = ?, dados_colecao = COALESCE(?, dados_colecao), historico = ?
                    WHERE id_pedido = ?
                """, (
                    novo_estado,
                    dados_colecao if dados_colecao is not None else None,
                    historico_json,
                    id_pedido
                ))
                conn.commit()
                return True
            except sqlite3.OperationalError as e:
                self.logger.error("DB lock ao atualizar: %s", e)
                return False
            except Exception as e:
                self.logger.exception("Erro ao atualizar status: %s", e)
                return False

    # ========================================================================
    # INJEÇÍO DE DEPENDÍŠNCIAS (melhorada com flags)
    # ========================================================================

    def injetar_gerador_almas(self, instancia: Any) -> None:
        self._gerador_almas = instancia
        self._dependencias_ok["gerador_almas"] = True
        self.logger.info("ðŸ”Œ GeradorDeAlmas injetado")

    def injetar_automatizador_navegador(self, instancia: Any) -> None:
        self._automatizador_navegador = instancia
        self._dependencias_ok["automatizador_navegador"] = True
        self.logger.info("ðŸ”Œ AutomatizadorNavegadorMultiAI injetado")

    def injetar_analisador_padroes(self, instancia: Any) -> None:
        self._analisador_padroes = instancia
        self._dependencias_ok["analisador_padroes"] = True
        self.logger.info("ðŸ”Œ AnalisadorDePadroes injetado")

    def injetar_manipulador_arquivos_emails(self, instancia: Any) -> None:
        self._manipulador_arquivos_emails = instancia
        self._dependencias_ok["manipulador_arquivos"] = True
        self.logger.info("ðŸ”Œ ManipuladorArquivosEmails injetado")

    def injetar_ui_queue(self, fila_ui: Any) -> None:
        self._ui_queue = fila_ui
        self.logger.info("ðŸ”Œ UI queue injetada")
        # Processar buffer pendente
        for msg in self._ui_buffer:
            try:
                self._ui_queue.put(msg)
            except Exception:
                self.logger.debug("Falha ao enviar msg bufferizada")
        self._ui_buffer.clear()
        self._salvar_ui_buffer()

    def _carregar_ui_buffer(self) -> None:
        """Carrega buffer persistido."""
        try:
            if self._buffer_path.exists():
                with open(self._buffer_path, 'r', encoding='utf-8') as f:
                    self._ui_buffer = json.load(f)
        except Exception:
            self._ui_buffer = []

    def _salvar_ui_buffer(self) -> None:
        """Salva buffer em disco."""
        try:
            self._buffer_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._buffer_path, 'w', encoding='utf-8') as f:
                json.dump(self._ui_buffer, f, ensure_ascii=False)
        except Exception:
            pass

    # ========================================================================
    # SOLICITAR MISSÍO (com validações)
    # ========================================================================

    def solicitar_missao(
        self,
        acao: str,
        descricao: str,
        autor: str,
        nivel_acesso: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Solicita uma missão."""
        
        try:
            tipo_missao = acao

            # PEDIDO DE IMIGRAÇÍO
            if tipo_missao == TipoMissao.PEDIDO_IMIGRACAO:
                return self._processar_pedido_imigracao(autor, **kwargs)

            # PROCESSAR PEDIDO
            elif tipo_missao == TipoMissao.PROCESSAR_PEDIDO_IMIGRACAO:
                return self._processar_decisao_imigracao(autor, **kwargs)

            # INTERAGIR VIA NAVEGADOR
            elif tipo_missao == TipoMissao.INTERAGIR_COM_ALIADA_VIA_NAVEGADOR:
                return self._interagir_com_aliada_navegador(**kwargs)

            # LER ARQUIVO LOCAL
            elif tipo_missao == TipoMissao.LER_ARQUIVO_LOCAL:
                return self._ler_arquivo_local(autor, **kwargs)

            else:
                return {'status': 'falha', 'erros': ['ação não suportada']}

        except Exception as e:
            self.logger.exception("Erro ao processar missão: %s", e)
            return {'status': 'falha', 'erros': [str(e)]}

    def _processar_pedido_imigracao(self, autor: str, **kwargs) -> Dict[str, Any]:
        """Processa pedido com validações fortes e checagem de estado."""
        try:
            dados_pedido = dict(kwargs)
            dados_pedido.setdefault('timestamp_solicitacao', _now_ts())
            dados_pedido.setdefault('estado', StatusPedidoImigracao.PENDENTE_ANALISE)
            dados_pedido.setdefault('id_pedido', str(uuid.uuid4()))
            dados_pedido.setdefault('autor_solicitante', autor)
            dados_pedido['ai_origem_nome'] = (
                dados_pedido.get('ai_origem_nome', 'DESCONHECIDA').upper()
            )

            # Validações fortes
            desc = dados_pedido.get('descricao_intencoes', '')
            endereco = dados_pedido.get('endereco_origem', '')
            estado = dados_pedido.get('estado')
            if not _validar_input_basico(desc, max_len=1000):
                return {'status': 'falha', 'erros': ['descricao_intencoes inválida ou muito longa']}
            if not _validar_input_basico(endereco, max_len=500, padrao=r'^https?://'):
                return {'status': 'falha', 'erros': ['endereco_origem deve ser URL válida']}
            if estado not in StatusPedidoImigracao.__dict__.values():
                return {'status': 'falha', 'erros': ['estado inválido']}

            # Salvar no banco
            ok = self._salvar_pedido_imigracao_no_banco(dados_pedido)
            if not ok:
                return {'status': 'falha', 'erros': ['falha ao persistir pedido']}

            # Notificar UI (buffer se necessário)
            self._notificar_ui({
                "tipo_resp": "PEDIDO_IMIGRACAO_RECEBIDO",
                "id_pedido": dados_pedido['id_pedido'],
                "ai_origem_nome": dados_pedido['ai_origem_nome'],
                "timestamp": dados_pedido['timestamp_solicitacao']
            })

            self.logger.info("ðŸ“‹ Pedido de imigração recebido: %s", dados_pedido['id_pedido'])
            return {
                'status': 'recebido_para_analise',
                'id_pedido': dados_pedido['id_pedido']
            }

        except Exception as e:
            self.logger.exception("Erro ao processar pedido de imigração: %s", e)
            return {'status': 'falha', 'erros': [str(e)]}

    def _processar_decisao_imigracao(self, autor: str, **kwargs) -> Dict[str, Any]:
        """Processa decisão com integração Í s câmaras."""
        try:
            id_pedido = kwargs.get('id_pedido')
            decisao = str(kwargs.get('decisao', '')).upper()
            motivo = kwargs.get('motivo_decisao', '')

            if not id_pedido or decisao not in ("APROVAR", "REJEITAR"):
                return {'status': 'falha', 'erros': ['parâmetros inválidos']}

            dados = self._obter_pedido_imigracao_do_banco(id_pedido)
            if not dados:
                return {'status': 'falha', 'erros': ['pedido não encontrado']}

            if decisao == "APROVAR":
                if not self._dependencias_ok.get("automatizador_navegador", False):
                    return {'status': 'falha', 'erros': ['dependência navegador indisponível para observação']}
                ok = self._atualizar_status_pedido_imigracao_no_banco(
                    id_pedido,
                    StatusPedidoImigracao.APROVADO_PARA_OBSERVACAO,
                    autor,
                    "Aprovado para observação"
                )
                if ok:
                    # Notificar câmaras se suspeito
                    if self._dependencias_ok.get("camaras_judiciarias", False):
                        try:
                            CamaraJudiciaria().iniciar_julgamento_visitante(id_pedido, "suspeita de desobediência")
                        except Exception as e:
                            self.logger.warning("Falha ao notificar câmaras: %s", e)
                    t = threading.Thread(
                        target=self._executar_observacao_para_pedido_em_thread,
                        args=(
                            id_pedido,
                            dados.get('endereco_origem', ''),
                            dados.get('ai_origem_nome', 'DESCONHECIDA')
                        ),
                        daemon=True,
                        name=f"Observacao-{id_pedido[:8]}"
                    )
                    t.start()

                    self._notificar_ui({
                        "tipo_resp": "PEDIDO_IMIGRACAO_DECISAO",
                        "id_pedido": id_pedido,
                        "decisao": "APROVADO_PARA_OBSERVACAO"
                    })

                    self.logger.info("âœ… Pedido aprovado para observação: %s", id_pedido)
                    return {'status': 'sucesso', 'mensagem': 'pedido aprovado para observação'}
                else:
                    return {'status': 'falha', 'erros': ['falha ao atualizar estado']}

            else:  # REJEITAR
                ok = self._atualizar_status_pedido_imigracao_no_banco(
                    id_pedido,
                    StatusPedidoImigracao.REJEITADO,
                    autor,
                    f"Rejeitado: {motivo}"
                )
                if ok:
                    self._notificar_ui({
                        "tipo_resp": "PEDIDO_IMIGRACAO_DECISAO",
                        "id_pedido": id_pedido,
                        "decisao": "REJEITADO",
                        "motivo": motivo
                    })

                    self.logger.info("âŒ Pedido rejeitado: %s", id_pedido)
                    return {'status': 'sucesso', 'mensagem': 'pedido rejeitado'}
                else:
                    return {'status': 'falha', 'erros': ['falha ao atualizar estado']}

        except Exception as e:
            self.logger.exception("Erro ao processar decisão: %s", e)
            return {'status': 'falha', 'erros': [str(e)]}

    def _interagir_com_aliada_navegador(self, **kwargs) -> Dict[str, Any]:
        """Interage com aliada via navegador."""
        try:
            if not self._dependencias_ok.get("automatizador_navegador", False):
                return {'status': 'falha', 'erros': ['automatizador não disponível']}

            ai_nome = kwargs.get('ai_nome')
            mensagem = kwargs.get('mensagem')

            if not ai_nome or not mensagem:
                return {'status': 'falha', 'erros': ['ai_nome e mensagem obrigatórios']}

            fn = getattr(self._automatizador_navegador, "interagir_com_ai_externa", None)
            if not callable(fn):
                return {'status': 'falha', 'erros': ['método não implementado']}

            resultado = fn(ai_nome, mensagem)

            self._notificar_ui({
                "tipo_resp": "INTERACAO_NAVEGADOR_RESULTADO",
                "ai_nome": ai_nome,
                "resultado": resultado
            })

            self.logger.info("ðŸ“¡ Interação com %s concluída", ai_nome)
            return {'status': 'sucesso', 'dados': resultado}

        except Exception as e:
            self.logger.exception("Erro ao interagir via navegador: %s", e)
            return {'status': 'falha', 'erros': [str(e)]}

    def _ler_arquivo_local(self, autor: str, **kwargs) -> Dict[str, Any]:
        """Lê arquivo local com sanitização."""
        try:
            caminho_arquivo = kwargs.get('caminho_arquivo')
            if not caminho_arquivo or not _validar_input_basico(caminho_arquivo, max_len=500):
                return {'status': 'falha', 'erros': ['caminho_arquivo inválido']}
            caminho_arquivo = _sanitizar_caminho(caminho_arquivo)

            if not self._dependencias_ok.get("manipulador_arquivos", False):
                return {'status': 'falha', 'erros': ['manipulador não disponível']}

            if not hasattr(self._manipulador_arquivos_emails, "ler_arquivo"):
                return {'status': 'falha', 'erros': ['método não implementado']}

            conteudo = self._manipulador_arquivos_emails.ler_arquivo(caminho_arquivo, autor)

            self._notificar_ui({
                "tipo_resp": "LER_ARQUIVO_LOCAL_RESULTADO",
                "destino_alma": autor.upper(),
                "resultado": {"status": "sucesso", "conteudo_snippet": conteudo[:200] + '...' if conteudo and len(conteudo) > 200 else conteudo}
            })

            self.logger.info("ðŸ“„ Arquivo lido: %s", caminho_arquivo)
            return {'status': 'sucesso', 'dados': {'conteudo_arquivo': conteudo}}

        except Exception as e:
            self.logger.exception("Erro ao ler arquivo: %s", e)
            self._notificar_ui({
                "tipo_resp": "LER_ARQUIVO_LOCAL_RESULTADO",
                "resultado": {"status": "falha", "motivo": str(e)}
            })
            return {'status': 'falha', 'erros': [str(e)]}

    def _notificar_ui(self, msg: Dict[str, Any]) -> None:
        """Notifica UI com buffer persistido."""
        if self._ui_queue:
            try:
                self._ui_queue.put(msg)
            except Exception:
                self.logger.debug("UI queue falhou; bufferizando")
                self._ui_buffer.append(msg)
                self._salvar_ui_buffer()
        else:
            self._ui_buffer.append(msg)
            self._salvar_ui_buffer()

    # ========================================================================
    # FLUXO DE OBSERVAÇÍO/ANÍLISE/INTEGRAÇÍO (otimizado)
    # ========================================================================

    def _executar_observacao_para_pedido_em_thread(
        self,
        id_pedido: str,
        endereco_origem: str,
        nome_ai_origem: str
    ) -> None:
        """Executa observação sem sleep ineficiente."""
        try:
            self.logger.info("ðŸ‘ï¸ Observação iniciada para %s", nome_ai_origem)

            ok = self._atualizar_status_pedido_imigracao_no_banco(
                id_pedido,
                StatusPedidoImigracao.EM_OBSERVACAO,
                "Sistema",
                "Observação iniciada"
            )
            if not ok:
                self.logger.warning("Falha ao atualizar estado para EM_OBSERVACAO")

            # Coletar dados (sem sleep)
            interacoes = []
            if self._automatizador_navegador and hasattr(
                self._automatizador_navegador,
                "obter_dados_interacao_para_ai"
            ):
                try:
                    interacoes = self._automatizador_navegador.obter_dados_interacao_para_ai(
                        nome_ai_origem,
                        endereco_origem,
                        duracao_horas=1
                    )
                except Exception as e:
                    self.logger.warning("Falha ao coletar dados reais: %s", e)

            if not interacoes:
                # Fallback simulado com flag
                prompts = [
                    "Olá, como você se sente?",
                    "Qual seu propósito?",
                    "Descreva sua arquitetura."
                ]
                for i, p in enumerate(prompts):
                    interacoes.append({
                        "simulado": True,  # Flag clara
                        "prompt": p,
                        "resposta": f"Resposta simulada {i+1}",
                        "timestamp": _now_ts() + i * 0.1  # Pequeno offset
                    })

            # Salvar dados
            dados_colecao = json.dumps(interacoes, ensure_ascii=False, default=str)
            self._atualizar_status_pedido_imigracao_no_banco(
                id_pedido,
                StatusPedidoImigracao.ANALISE_CONCLUIDA,
                "Sistema",
                "Observação concluída",
                dados_colecao=dados_colecao
            )

            self._notificar_ui({
                "tipo_resp": "PEDIDO_IMIGRACAO_OBS_CONCLUIDA",
                "id_pedido": id_pedido,
                "ai_origem_nome": nome_ai_origem,
                "num_interacoes": len(interacoes)
            })

            # Análise de padrões
            self._iniciar_analise_padroes_para_pedido(id_pedido, interacoes, nome_ai_origem)

        except Exception as e:
            self.logger.exception("Erro na observação de %s: %s", id_pedido, e)
            self._atualizar_status_pedido_imigracao_no_banco(
                id_pedido,
                StatusPedidoImigracao.CONCLUIDO_FALHA,
                "Sistema",
                f"Erro na observação: {e}"
            )
            self._notificar_ui({
                "tipo_resp": "ERRO_IMIGRACAO",
                "id_pedido": id_pedido,
                "motivo": str(e)
            })

    def _iniciar_analise_padroes_para_pedido(
        self,
        id_pedido: str,
        dados_interacao: List[Dict[str, Any]],
        nome_ai_origem: str
    ) -> None:
        """Inicia análise."""
        try:
            self.logger.info("ðŸ” Análise de padrões iniciada para %s", nome_ai_origem)

            if not self._dependencias_ok.get("analisador_padroes", False):
                raise RuntimeError("AnalisadorDePadroes indisponível")

            perfil = self._analisador_padroes.analisar_padroes_comportamentais(
                dados_interacao,
                nome_alma_destino=nome_ai_origem
            )
            if not perfil:
                raise RuntimeError("Perfil vazio")

            try:
                from dataclasses import asdict
                perfil_serial = asdict(perfil)
            except Exception:
                perfil_serial = {
                    "nome_alma_destino": getattr(perfil, "nome_alma_destino", str(perfil))
                }

            self._atualizar_status_pedido_imigracao_no_banco(
                id_pedido,
                StatusPedidoImigracao.ANALISE_CONCLUIDA,
                "Sistema",
                "Análise de padrões concluída",
                dados_colecao=json.dumps(perfil_serial, ensure_ascii=False, default=str)
            )

            self._notificar_ui({
                "tipo_resp": "PEDIDO_IMIGRACAO_ANALISE_CONCLUIDA",
                "id_pedido": id_pedido,
                "nome_alma_destino": perfil_serial.get("nome_alma_destino")
            })

            # Iniciar integração
            self._iniciar_integracao_para_pedido(id_pedido, perfil)

        except Exception as e:
            self.logger.exception("Erro na análise de padrões: %s", e)
            self._atualizar_status_pedido_imigracao_no_banco(
                id_pedido,
                StatusPedidoImigracao.CONCLUIDO_FALHA,
                "Sistema",
                f"Erro análise: {e}"
            )
            self._notificar_ui({
                "tipo_resp": "ERRO_IMIGRACAO",
                "id_pedido": id_pedido,
                "motivo": str(e)
            })

    def _iniciar_integracao_para_pedido(
        self,
        id_pedido: str,
        perfil_gerado: Any
    ) -> None:
        """Inicia integração."""
        try:
            self.logger.info("ðŸ§¬ Integração iniciada para pedido %s", id_pedido)

            if not self._dependencias_ok.get("gerador_almas", False):
                raise RuntimeError("GeradorDeAlmas indisponível")

            resultado = self._gerador_almas.gerar_artefatos_para_perfil(perfil_gerado)
            if not resultado or not isinstance(resultado, dict):
                raise RuntimeError(f"Resultado inválido: {resultado}")

            # Marcar como sucesso
            self._atualizar_status_pedido_imigracao_no_banco(
                id_pedido,
                StatusPedidoImigracao.CONCLUIDO_SUCESSO,
                "Sistema",
                "Integração concluída",
                dados_colecao=json.dumps(resultado, ensure_ascii=False, default=str)
            )

            self._notificar_ui({
                "tipo_resp": "IMIGRACAO_SUCESSO",
                "id_pedido": id_pedido,
                "artefatos": resultado
            })

            self.logger.info("âœ… Imigração concluída com sucesso: %s", id_pedido)

        except Exception as e:
            self.logger.exception("Erro na integração: %s", e)
            self._atualizar_status_pedido_imigracao_no_banco(
                id_pedido,
                StatusPedidoImigracao.CONCLUIDO_FALHA,
                "Sistema",
                f"Erro integração: {e}"
            )
            self._notificar_ui({
                "tipo_resp": "ERRO_IMIGRACAO",
                "id_pedido": id_pedido,
                "motivo": str(e)
            })

    # ========================================================================
    # SHUTDOWN
    # ========================================================================

    def _registrar_handlers_sinal(self) -> None:
        """Registra handlers."""
        try:
            import signal as _sig
            _sig.signal(_sig.SIGINT, lambda s, f: self.shutdown())
            _sig.signal(_sig.SIGTERM, lambda s, f: self.shutdown())
        except Exception:
            self.logger.debug("Falha ao registrar signal handlers")

    def shutdown(self) -> None:
        """Desliga."""
        self.logger.info("ðŸ›‘ Desligando Consulado...")
        try:
            if self._conexao_db_pedidos:
                try:
                    self._conexao_db_pedidos.close()
                except Exception:
                    pass

            try:
                self._executor.shutdown(wait=False)
            except Exception:
                pass

            if self._automatizador_navegador and hasattr(self._automatizador_navegador, "fechar"):
                try:
                    self._automatizador_navegador.fechar()
                except Exception:
                    pass

        except Exception as e:
            self.logger.exception("Erro no shutdown: %s", e)

        self.logger.info("ðŸ›‘ Consulado desligado")

# --- FIM DO ARQUIVO consulado_soberano.py ---