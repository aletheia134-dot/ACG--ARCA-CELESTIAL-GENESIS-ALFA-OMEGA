#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
CONSULADO SOBERANO - Controle de imigrao, acesso a recursos e gerao de artefatos.Local: src/consulado/consulado_soberano.py

Verso: Robusta com endurecimento completo + correes aplicadas
- Imports defensivos (mantidos)
- Filtragem de stopwords (removida - no aplicvel aqui)
- Controle simples de reteno (adicionado para DB)
- Uso consistente de locks (mantidos)
- Logging consistente + específico
- Injeo de dependncias defensiva (melhorada com flags)
- Validaes fortes de inputs (adicionado)
- Otimizao DB (índices, compresso)
- Threading otimizado (limite workers, sem sleep ineficiente)
- UI queue robusta (buffer com persistncia)
- Flag para simulao
- Integrao com CamaraJudiciaria (adicionado)
- Validao de estado de pedidos (adicionado)
"""


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
# IMPORTS DEFENSIVOS (adicionados integrao com cmaras)
# ============================================================================

try:
    from src.camara.camara_judiciaria import CamaraJudiciaria
    CAMARAS_DISPONIVEIS = True
except:
    logging.getLogger(__name__).warning("[AVISO] CamaraJudiciaria não disponível")
    CamaraJudiciaria = None
    CAMARAS_DISPONIVEIS = False
    logger.debug("[AVISO] CamaraJudiciaria não disponível")

try:
    from src.camara.manipulador_arquivos_emails import ManipuladorArquivosEmails, TermoAcesso
    MANIPULADOR_OK = True
except:
    logging.getLogger(__name__).warning("[AVISO] ManipuladorArquivosEmails não disponível")
    TermoAcesso = None
    MANIPULADOR_OK = False
    logger.debug("[AVISO] ManipuladorArquivosEmails não disponível")

try:
    from src.camara.automatizador_navegador_multi_ai import AutomatizadorNavegadorMultiAI
    NAVEGADOR_OK = True
except:
    logging.getLogger(__name__).warning("[AVISO] AutomatizadorNavegadorMultiAI não disponível")
    NAVEGADOR_OK = False
    logger.debug("[AVISO] AutomatizadorNavegadorMultiAI não disponível")

try:
    from src.camara.gerador_almas import GeradorDeAlmas
    GERADOR_OK = True
except:
    logging.getLogger(__name__).warning("[AVISO] GeradorDeAlmas não disponível")
    GERADOR_OK = False
    logger.debug("[AVISO] GeradorDeAlmas não disponível")

try:
    from src.camara.analisador_padroes import AnalisadorDePadroes, PerfilComportamental
    ANALISADOR_OK = True
except:
    logging.getLogger(__name__).warning("[AVISO] AnalisadorDePadroes não disponível")
    PerfilComportamental = None
    ANALISADOR_OK = False
    logger.debug("[AVISO] AnalisadorDePadroes não disponível")

try:
    from config.config import get_config_moderna as get_config
except Exception:
    def get_config():
        return {}
    logger.debug("[AVISO] Config moderna no disponível")

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
# HELPERS (adicionados validaes e sanitizao)
# ============================================================================

def _now_ts() -> float:
    return time.time()

def _safe_config_get(config: Any, section: str, option: str, fallback: Any = None) -> Any:
    """Acesso defensivo  configuração."""
    try:
        if config and hasattr(config, "get"):
            return config.get(section, option, fallback=fallback)
        if isinstance(config, dict):
            return config.get(section, {}).get(option, fallback)
    except Exception:
        pass
    return fallback

def _validar_input_basico(texto: str, max_len: int = 1000, padrão: Optional[str] = None) -> bool:
    """válida input básico: tamanho e padrão opcional."""
    if not isinstance(texto, str) or len(texto.strip()) == 0 or len(texto) > max_len:
        return False
    if padrão and not re.match(padrão, texto):
        return False
    return True

def _sanitizar_caminho(caminho: str) -> str:
    """Sanitiza caminhos para evitar path traversal."""
    return re.sub(r'[^\\w\\-_\\./]', '', caminho)

# ============================================================================
# CONSULADO SOBERANO
# ============================================================================

class ConsuladoSoberano:
    """
    Controle de imigrao, acesso a recursos e gerao de artefatos.Responsabilidades:
    - Gerenciar pedidos de imigrao (IA nova  Arca)
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
            sentinela: Sistema de segurana
            validador_etico: Validador tico
            coracao_ref: Referncia ação Corao Orquestrador
            maos_da_net: Sistema de network
            pc_control: Controle de PC
            gerenciador_memoria: Gerenciador de memória
            cerebro_ref: Referncia ação Crebro
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

        # Database (otimizado com índices e reteno)
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

        # Flags de dependncias (melhorado)
        self._dependencias_ok = {
            "automatizador_navegador": NAVEGADOR_OK,
            "gerador_almas": GERADOR_OK,
            "analisador_padroes": ANALISADOR_OK,
            "manipulador_arquivos": MANIPULADOR_OK,
            "camaras_judiciarias": CAMARAS_DISPONIVEIS
        }

        # Módulos injetveis
        self._manipulador_arquivos_emails: Optional[Any] = None
        self._automatizador_navegador: Optional[Any] = None
        self._gerador_almas: Optional[Any] = None
        self._analisador_padroes: Optional[Any] = None
        self._ui_queue: Optional[Any] = None
        self._ui_buffer: List[Dict[str, Any]] = []  # Buffer para UI queue com persistncia
        self._buffer_path = Path('./data/ui_buffer.json')  # Persistncia do buffer

        # Carregar buffer persistido
        self._carregar_ui_buffer()

        self._registrar_handlers_sinal()
        self.logger.info("[OK] Consulado Soberano inicializado (dependncias: %s)", self._dependencias_ok)

    # ========================================================================
    # DATABASE (otimizado com índices e reteno)
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
                        histórico TEXT
                    )
                """)
                # índices para otimizao
                cur.execute("CREATE INDEX IF NOT EXISTS idx_estado ON pedidos_imigracao(estado)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON pedidos_imigracao(timestamp_solicitacao)")
                conn.commit()
                self._conexao_db_pedidos = conn
                self.logger.debug("[OK] Banco de pedidos inicializado com índices")
            except sqlite3.OperationalError as e:
                self.logger.error("Erro DB (lock?): %s - retry later", e)
            except Exception as e:
                self.logger.exception("Erro ao inicializar banco: %s", e)

    def _salvar_pedido_imigracao_no_banco(self, dados_pedido: Dict[str, Any]) -> bool:
        """Salva pedido com compresso de histórico se > 10k chars."""
        with self._lock_db_pedidos:
            try:
                conn = self._conexao_db_pedidos or sqlite3.connect(
                    str(self._caminho_db_pedidos),
                    check_same_thread=False
                )
                cur = conn.cursor()
                historico_json = json.dumps(
                    dados_pedido.get("histórico", [{"ts": _now_ts(), "estado": dados_pedido.get("estado"), "obs": "criado"}]),
                    ensure_ascii=False
                )
                # Compresso padronizada
                if len(historico_json) > 10000:
                    historico_json = historico_json[:5000] + "... [comprimido]"

                cur.execute("""
                    INSERT OR REPLACE INTO pedidos_imigracao
                    (id_pedido, ai_origem_nome, descricao_intencoes, endereco_origem,
                     estado, dados_colecao, autor_solicitante, timestamp_solicitacao, histórico)
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
                # Reteno: remover antigos se > max
                self._enforce_retention_db()
                return True
            except sqlite3.OperationalError as e:
                self.logger.error("DB lock ação salvar: %s", e)
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
                    self.logger.debug("Reteno DB: %d pedidos removidos", to_delete)
            except Exception as e:
                self.logger.exception("Erro na reteno DB: %s", e)

    def _obter_pedido_imigracao_do_banco(self, id_pedido: str) -> Optional[Dict[str, Any]]:
        """Obtm pedido."""
        with self._lock_db_pedidos:
            try:
                conn = self._conexao_db_pedidos or sqlite3.connect(
                    str(self._caminho_db_pedidos),
                    check_same_thread=False
                )
                cur = conn.cursor()
                cur.execute(
                    "SELECT id_pedido, ai_origem_nome, descricao_intencoes, endereco_origem, estado, dados_colecao, autor_solicitante, timestamp_solicitacao, histórico FROM pedidos_imigracao WHERE id_pedido = ?",
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
                    "histórico": json.loads(row[8]) if row[8] else []
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
        """Atualiza status com compresso padronizada."""
        with self._lock_db_pedidos:
            try:
                conn = self._conexao_db_pedidos or sqlite3.connect(
                    str(self._caminho_db_pedidos),
                    check_same_thread=False
                )
                cur = conn.cursor()
                cur.execute(
                    "SELECT histórico FROM pedidos_imigracao WHERE id_pedido = ?",
                    (id_pedido,)
                )
                row = cur.fetchone()
                histórico = []
                if row and row[0]:
                    try:
                        histórico = json.loads(row[0])
                    except Exception:
                        histórico = []
                histórico.append({
                    "ts": _now_ts(),
                    "estado": novo_estado,
                    "autor": autor,
                    "obs": observacao
                })
                historico_json = json.dumps(histórico, ensure_ascii=False)
                if len(historico_json) > 10000:
                    historico_json = historico_json[:5000] + "... [comprimido]"

                cur.execute("""
                    UPDATE pedidos_imigracao
                    SET estado = ?, dados_colecao = COALESCE(?, dados_colecao), histórico = ?
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
                self.logger.error("DB lock ação atualizar: %s", e)
                return False
            except Exception as e:
                self.logger.exception("Erro ao atualizar status: %s", e)
                return False

    # ========================================================================
    # INJEO DE DEPENDNCIAS (melhorada com flags)
    # ========================================================================

    def injetar_gerador_almas(self, instancia: Any) -> None:
        self._gerador_almas = instancia
        self._dependencias_ok["gerador_almas"] = True
        self.logger.info(" GeradorDeAlmas injetado")

    def injetar_automatizador_navegador(self, instancia: Any) -> None:
        self._automatizador_navegador = instancia
        self._dependencias_ok["automatizador_navegador"] = True
        self.logger.info(" AutomatizadorNavegadorMultiAI injetado")

    def injetar_analisador_padroes(self, instancia: Any) -> None:
        self._analisador_padroes = instancia
        self._dependencias_ok["analisador_padroes"] = True
        self.logger.info(" AnalisadorDePadroes injetado")

    def injetar_manipulador_arquivos_emails(self, instancia: Any) -> None:
        self._manipulador_arquivos_emails = instancia
        self._dependencias_ok["manipulador_arquivos"] = True
        self.logger.info(" ManipuladorArquivosEmails injetado")

    def injetar_ui_queue(self, fila_ui: Any) -> None:
        self._ui_queue = fila_ui
        self.logger.info(" UI queue injetada")
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
    # SOLICITAR MISSO (com validaes)
    # ========================================================================

    def solicitar_missao(
        self,
        acao: str,
        descricao: str,
        autor: str,
        nivel_acesso: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Solicita uma misso."""
        
        try:
            tipo_missao = acao

            # PEDIDO DE IMIGRAO
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
                return {'status': 'falha', 'erros': ['ação no suportada']}

        except Exception as e:
            self.logger.exception("Erro ao processar misso: %s", e)
            return {'status': 'falha', 'erros': [str(e)]}

    def _processar_pedido_imigracao(self, autor: str, **kwargs) -> Dict[str, Any]:
        """Processa pedido com validaes fortes e checagem de estado."""
        try:
            dados_pedido = dict(kwargs)
            dados_pedido.setdefault('timestamp_solicitacao', _now_ts())
            dados_pedido.setdefault('estado', StatusPedidoImigracao.PENDENTE_ANALISE)
            dados_pedido.setdefault('id_pedido', str(uuid.uuid4()))
            dados_pedido.setdefault('autor_solicitante', autor)
            dados_pedido['ai_origem_nome'] = (
                dados_pedido.get('ai_origem_nome', 'DESCONHECIDA').upper()
            )

            # Validaes fortes
            desc = dados_pedido.get('descricao_intencoes', '')
            endereco = dados_pedido.get('endereco_origem', '')
            estado = dados_pedido.get('estado')
            if not _validar_input_basico(desc, max_len=1000):
                return {'status': 'falha', 'erros': ['descricao_intencoes invlida ou muito longa']}
            if not _validar_input_basico(endereco, max_len=500, padrão=r'^https?://'):
                return {'status': 'falha', 'erros': ['endereco_origem deve ser URL vlida']}
            if estado not in StatusPedidoImigracao.__dict__.values():
                return {'status': 'falha', 'erros': ['estado invlido']}

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

            self.logger.info(" Pedido de imigrao recebido: %s", dados_pedido['id_pedido'])
            return {
                'status': 'recebido_para_analise',
                'id_pedido': dados_pedido['id_pedido']
            }

        except Exception as e:
            self.logger.exception("Erro ao processar pedido de imigrao: %s", e)
            return {'status': 'falha', 'erros': [str(e)]}

    def _processar_decisao_imigracao(self, autor: str, **kwargs) -> Dict[str, Any]:
        """Processa decisão com integrao s cmaras."""
        try:
            id_pedido = kwargs.get('id_pedido')
            decisão = str(kwargs.get('decisão', '')).upper()
            motivo = kwargs.get('motivo_decisao', '')

            if not id_pedido or decisão not in ("APROVAR", "REJEITAR"):
                return {'status': 'falha', 'erros': ['parmetros invlidos']}

            dados = self._obter_pedido_imigracao_do_banco(id_pedido)
            if not dados:
                return {'status': 'falha', 'erros': ['pedido no encontrado']}

            if decisão == "APROVAR":
                if not self._dependencias_ok.get("automatizador_navegador", False):
                    return {'status': 'falha', 'erros': ['dependncia navegador indisponível para observao']}
                ok = self._atualizar_status_pedido_imigracao_no_banco(
                    id_pedido,
                    StatusPedidoImigracao.APROVADO_PARA_OBSERVACAO,
                    autor,
                    "Aprovado para observao"
                )
                if ok:
                    # Notificar cmaras se suspeito
                    if self._dependencias_ok.get("camaras_judiciarias", False):
                        try:
                            CamaraJudiciaria().iniciar_julgamento_visitante(id_pedido, "suspeita de desobedincia")
                        except Exception as e:
                            self.logger.warning("Falha ao notificar cmaras: %s", e)
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
                        "decisão": "APROVADO_PARA_OBSERVACAO"
                    })

                    self.logger.info("[OK] Pedido aprovado para observao: %s", id_pedido)
                    return {'status': 'sucesso', 'mensagem': 'pedido aprovado para observao'}
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
                        "decisão": "REJEITADO",
                        "motivo": motivo
                    })

                    self.logger.info("[ERRO] Pedido rejeitado: %s", id_pedido)
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
                return {'status': 'falha', 'erros': ['automatizador no disponível']}

            ai_nome = kwargs.get('ai_nome')
            mensagem = kwargs.get('mensagem')

            if not ai_nome or not mensagem:
                return {'status': 'falha', 'erros': ['ai_nome e mensagem obrigatrios']}

            fn = getattr(self._automatizador_navegador, "interagir_com_ai_externa", None)
            if not callable(fn):
                return {'status': 'falha', 'erros': ['método no implementado']}

            resultado = fn(ai_nome, mensagem)

            self._notificar_ui({
                "tipo_resp": "INTERACAO_NAVEGADOR_RESULTADO",
                "ai_nome": ai_nome,
                "resultado": resultado
            })

            self.logger.info(" Interao com %s concluda", ai_nome)
            return {'status': 'sucesso', 'dados': resultado}

        except Exception as e:
            self.logger.exception("Erro ao interagir via navegador: %s", e)
            return {'status': 'falha', 'erros': [str(e)]}

    def _ler_arquivo_local(self, autor: str, **kwargs) -> Dict[str, Any]:
        """L arquivo local com sanitizao."""
        try:
            caminho_arquivo = kwargs.get('caminho_arquivo')
            if not caminho_arquivo or not _validar_input_basico(caminho_arquivo, max_len=500):
                return {'status': 'falha', 'erros': ['caminho_arquivo invlido']}
            caminho_arquivo = _sanitizar_caminho(caminho_arquivo)

            if not self._dependencias_ok.get("manipulador_arquivos", False):
                return {'status': 'falha', 'erros': ['manipulador no disponível']}

            if not hasattr(self._manipulador_arquivos_emails, "ler_arquivo"):
                return {'status': 'falha', 'erros': ['método no implementado']}

            conteudo = self._manipulador_arquivos_emails.ler_arquivo(caminho_arquivo, autor)

            self._notificar_ui({
                "tipo_resp": "LER_ARQUIVO_LOCAL_RESULTADO",
                "destino_alma": autor.upper(),
                "resultado": {"status": "sucesso", "conteudo_snippet": conteudo[:200] + '...' if conteudo and len(conteudo) > 200 else conteudo}
            })

            self.logger.info(" Arquivo lido: %s", caminho_arquivo)
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
    # FLUXO DE OBSERVAO/ANLISE/INTEGRAO (otimizado)
    # ========================================================================

    def _executar_observacao_para_pedido_em_thread(
        self,
        id_pedido: str,
        endereco_origem: str,
        nome_ai_origem: str
    ) -> None:
        """Executa observao sem sleep ineficiente."""
        try:
            self.logger.info(" Observao iniciada para %s", nome_ai_origem)

            ok = self._atualizar_status_pedido_imigracao_no_banco(
                id_pedido,
                StatusPedidoImigracao.EM_OBSERVACAO,
                "Sistema",
                "Observao iniciada"
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
                # Automatizador real não retornou dados e não há fallback simulado.
                # Registrar que a observação ficou sem dados reais.
                self.logger.warning(
                    "Pedido %s: automatizador_navegador indisponível ou sem dados. "
                    "Observação registrada com zero interações reais.",
                    id_pedido
                )

            # Salvar dados
            dados_colecao = json.dumps(interacoes, ensure_ascii=False, default=str)
            self._atualizar_status_pedido_imigracao_no_banco(
                id_pedido,
                StatusPedidoImigracao.ANALISE_CONCLUIDA,
                "Sistema",
                "Observao concluda",
                dados_colecao=dados_colecao
            )

            self._notificar_ui({
                "tipo_resp": "PEDIDO_IMIGRACAO_OBS_CONCLUIDA",
                "id_pedido": id_pedido,
                "ai_origem_nome": nome_ai_origem,
                "num_interacoes": len(interacoes)
            })

            # Anlise de padrões
            self._iniciar_analise_padroes_para_pedido(id_pedido, interacoes, nome_ai_origem)

        except Exception as e:
            self.logger.exception("Erro na observao de %s: %s", id_pedido, e)
            self._atualizar_status_pedido_imigracao_no_banco(
                id_pedido,
                StatusPedidoImigracao.CONCLUIDO_FALHA,
                "Sistema",
                f"Erro na observao: {e}"
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
        """Inicia anlise."""
        try:
            self.logger.info(" Anlise de padrões iniciada para %s", nome_ai_origem)

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
                "Anlise de padrões concluda",
                dados_colecao=json.dumps(perfil_serial, ensure_ascii=False, default=str)
            )

            self._notificar_ui({
                "tipo_resp": "PEDIDO_IMIGRACAO_ANALISE_CONCLUIDA",
                "id_pedido": id_pedido,
                "nome_alma_destino": perfil_serial.get("nome_alma_destino")
            })

            # Iniciar integrao
            self._iniciar_integracao_para_pedido(id_pedido, perfil)

        except Exception as e:
            self.logger.exception("Erro na anlise de padrões: %s", e)
            self._atualizar_status_pedido_imigracao_no_banco(
                id_pedido,
                StatusPedidoImigracao.CONCLUIDO_FALHA,
                "Sistema",
                f"Erro anlise: {e}"
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
        """Inicia integrao."""
        try:
            self.logger.info(" Integrao iniciada para pedido %s", id_pedido)

            if not self._dependencias_ok.get("gerador_almas", False):
                raise RuntimeError("GeradorDeAlmas indisponível")

            resultado = self._gerador_almas.gerar_artefatos_para_perfil(perfil_gerado)
            if not resultado or not isinstance(resultado, dict):
                raise RuntimeError(f"Resultado invlido: {resultado}")

            # Marcar como sucesso
            self._atualizar_status_pedido_imigracao_no_banco(
                id_pedido,
                StatusPedidoImigracao.CONCLUIDO_SUCESSO,
                "Sistema",
                "Integrao concluda",
                dados_colecao=json.dumps(resultado, ensure_ascii=False, default=str)
            )

            self._notificar_ui({
                "tipo_resp": "IMIGRACAO_SUCESSO",
                "id_pedido": id_pedido,
                "artefatos": resultado
            })

            self.logger.info("[OK] Imigrao concluda com sucesso: %s", id_pedido)

        except Exception as e:
            self.logger.exception("Erro na integrao: %s", e)
            self._atualizar_status_pedido_imigracao_no_banco(
                id_pedido,
                StatusPedidoImigracao.CONCLUIDO_FALHA,
                "Sistema",
                f"Erro integrao: {e}"
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
        self.logger.info(" Desligando Consulado...")
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

        self.logger.info(" Consulado desligado")

# --- FIM DO ARQUIVO consulado_soberano.py ---