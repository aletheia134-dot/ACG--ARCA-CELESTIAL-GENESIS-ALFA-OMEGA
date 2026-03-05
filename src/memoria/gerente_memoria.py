from __future__ import annotations

import logging
import os
import uuid
import shutil
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

CHROMADB_DISPONIVEL = False
try:
    import chromadb  # type: ignore
    try:
        PersistentClient = getattr(chromadb, "PersistentClient", None) or getattr(chromadb, "Client", None)
    except:
        logging.getLogger(__name__).warning("âš ï¸ PersistentClient nÃ£o disponÃ­vel")
    PersistentClient = None
    try:
        from chromadb.utils import embedding_functions  # type: ignore
    except:
        logging.getLogger(__name__).warning("âš ï¸ PersistentClient nÃ£o disponÃ­vel")
    PersistentClient = None
    if PersistentClient is not None and embedding_functions is not None:
        CHROMADB_DISPONIVEL = True
    else:
        CHROMADB_DISPONIVEL = False
except Exception as e:
    logging.critical("ERRO CRÃTICO: DependÃªncias de MemÃ³ria/RAG nÃ£o instaladas.Detalhe: %s", e)

try:
    from memoria.metabolismo import MetabolismoMemoria  # type: ignore
    METABOLISMO_DISPONIVEL = True
except:
    logging.getLogger(__name__).warning("âš ï¸ PersistentClient nÃ£o disponÃ­vel")
    PersistentClient = None  # type: ignore
    METABOLISMO_DISPONIVEL = False

logger = logging.getLogger('GerenteMemoria')
logger.addHandler(logging.NullHandler())


class GerenteMemoria:
    def __init__(self, config_manager: Any):
        self.config = config_manager
        self.client = None
        self.embedding_function = None
        self.metabolismo = None
        self.is_initialized = False

        try:
            self._memory_db_path = getattr(self.config, "MEMORY_DB_PATH", None) or getattr(self.config, "MEMORY_DB_DIR", None)
            self._embedding_model = getattr(self.config, "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
            self._almas_nomes = getattr(self.config, "ALMAS_NOMES", []) or []
        except Exception:
            self._memory_db_path = None
            self._embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
            self._almas_nomes = []

        if not CHROMADB_DISPONIVEL:
            logger.error("GerenteMemoria desativado: chromadb/embeddings nÃ£o disponÃ­veis.")
            return

        try:
            SentenceTransformerEmbeddingFunction = getattr(embedding_functions, "SentenceTransformerEmbeddingFunction", None)
            if SentenceTransformerEmbeddingFunction is None:
                raise RuntimeError("embedding_functions.SentenceTransformerEmbeddingFunction nÃ£o encontrado")
            self.embedding_function = SentenceTransformerEmbeddingFunction(
                model_name=self._embedding_model,
                device=getattr(self.config, "EMBEDDING_DEVICE", "cpu")
            )
            logger.info("Modelo de embedding carregado: %s", self._embedding_model)
        except Exception as e:
            logger.critical("Falha ao carregar o modelo de embedding: %s", e, exc_info=True)
            self.embedding_function = None

    def initialize(self) -> None:
        if self.is_initialized:
            logger.info("GerenteMemoria jÃ¡ inicializado.")
            return

        if not CHROMADB_DISPONIVEL or self.embedding_function is None:
            logger.critical("NÃ£o foi possÃ­vel inicializar GerenteMemoria: dependÃªncias ausentes.")
            return

        if not self._memory_db_path:
            logger.critical("Caminho do banco de memÃ³ria nÃ£o configurado (config.MEMORY_DB_PATH).")
            return

        try:
            os.makedirs(self._memory_db_path, exist_ok=True)
        except Exception as e:
            logger.critical("Falha ao criar diretÃ³rio de memÃ³ria '%s': %s", self._memory_db_path, e, exc_info=True)
            return

        try:
            logger.warning("Se houver erros de ChromaDB ('no such column'), apague '%s' e reinicie.", self._memory_db_path)
            ClientClass = PersistentClient
            if ClientClass is None:
                raise RuntimeError("PersistentClient/Client nÃ£o disponÃ­vel na versÃ£o instalada do chromadb")
            try:
                self.client = ClientClass(path=self._memory_db_path)
            except TypeError:
                settings = getattr(chromadb, "Settings", None)
                if settings:
                    self.client = ClientClass(path=self._memory_db_path, settings=settings(anonymized_telemetry=False))
                else:
                    self.client = ClientClass(self._memory_db_path)

            logger.info("Cliente ChromaDB conectado em: %s", self._memory_db_path)

            if METABOLISMO_DISPONIVEL and MetabolismoMemoria is not None:
                try:
                    self.metabolismo = MetabolismoMemoria(self.client, self.embedding_function, self.config)
                    colecoes = list(self._almas_nomes) + ["sistema", "todas", "default", "user"]
                    self.metabolismo.inicializar_colecoes(colecoes)
                    logger.info("Metabolismo de MemÃ³ria inicializado com coleÃ§Ãµes: %s", colecoes)
                except Exception as e:
                    logger.critical("Falha ao inicializar MetabolismoMemoria: %s", e, exc_info=True)
                    self.metabolismo = None
            else:
                logger.warning("MetabolismoMemoria nÃ£o disponÃ­vel; funcionalidades metabolicas desabilitadas.")
                self.metabolismo = None

            self.is_initialized = True if self.client is not None else False

        except Exception as e:
            logger.critical("Falha ao conectar/inicializar ChromaDB/Metabolismo: %s", e, exc_info=True)
            self.client = None
            self.is_initialized = False

    def get_context(self, query: str, alma_nome: str = "sistema", k: int = 3) -> List[str]:
        if not self.is_initialized or not self.metabolismo:
            logger.warning("GerenteMemoria nÃ£o inicializado/metabolismo ausente.Retornando []")
            return []
        try:
            contexto, metadados = self.metabolismo.buscar_com_metabolismo(query, alma_nome, k)
            logger.debug("Busca metabolizada: %s -> %d resultados", alma_nome, len(contexto))
            for meta in metadados or []:
                if meta.get('camada_original') in ('m2', 'm3'):
                    logger.info("MEMÃ“RIA PROMOVIDA: %s camada=%s id=%s", alma_nome, meta.get('camada_original'), meta.get('id', ''))
            return contexto or []
        except Exception as e:
            logger.error("Erro durante busca metabolizada: %s", e, exc_info=True)
            return []

    def get_context_detalhado(self, query: str, alma_nome: str = "sistema", k: int = 5) -> Tuple[List[str], List[Dict[str, Any]]]:
        if not self.is_initialized or not self.metabolismo:
            return [], []
        try:
            contexto, metadados = self.metabolismo.buscar_com_metabolismo(query, alma_nome, k)
            return contexto or [], metadados or []
        except Exception as e:
            logger.error("Erro na busca detalhada: %s", e, exc_info=True)
            return [], []

    def save_memory(self, content: str, alma_nome: str = "sistema", metadata: Optional[Dict[str, Any]] = None) -> bool:
        if not self.is_initialized or not self.metabolismo:
            logger.warning("GerenteMemoria nÃ£o inicializado/metabolismo ausente.Ignorando save_memory.")
            return False
        try:
            metadata_completo = dict(metadata) if metadata else {}
            timestamp = self._get_timestamp()
            metadata_completo.setdefault('alma', alma_nome)
            metadata_completo.setdefault('tipo', metadata_completo.get('tipo', 'experiencia'))
            metadata_completo.setdefault('timestamp_criacao', timestamp)
            metadata_completo.setdefault('data_entrada_m1', timestamp)
            metadata_completo.setdefault('acessos', metadata_completo.get('acessos', 0))
            content_str = str(content) if content is not None else ''
            self.metabolismo.salvar_memoria(alma_nome, content_str, metadata_completo)
            logger.info("MemÃ³ria salva (metabolismo): alma=%s tipo=%s", alma_nome, metadata_completo.get('tipo'))
            return True
        except Exception as e:
            logger.error("Falha ao salvar memÃ³ria com metabolismo: %s", e, exc_info=True)
            return False

    def save_conversation_memory(self, pergunta: str, resposta: str, alma_nome: str, metadata_extra: Optional[Dict[str, Any]] = None) -> bool:
        content = f"PERGUNTA: {pergunta} | RESPOSTA: {resposta}"
        metadata = {
            'tipo': 'conversa',
            'alma': alma_nome,
            'pergunta': pergunta[:200],
            'resposta_tamanho': len(resposta) if resposta is not None else 0,
            'timestamp': self._get_timestamp()
        }
        if metadata_extra:
            metadata.update(metadata_extra)
        return self.save_memory(content, alma_nome, metadata)

    def get_estatisticas_memoria(self, alma_nome: Optional[str] = None) -> Dict[str, Any]:
        if not self.is_initialized or not self.metabolismo or not hasattr(self.metabolismo, 'colecoes'):
            return {}
        try:
            estatisticas: Dict[str, Any] = {'total_almas': len(self.metabolismo.colecoes), 'almas': {}, 'timestamp': self._get_timestamp()}
            for alma, colecoes in self.metabolismo.colecoes.items():
                if alma_nome and alma != alma_nome:
                    continue
                estatisticas_alma: Dict[str, Any] = {}
                for camada, colecao in (colecoes or {}).items():
                    try:
                        count = colecao.count() if hasattr(colecao, 'count') else None
                        estatisticas_alma[camada] = count
                    except Exception as e:
                        estatisticas_alma[camada] = f"erro: {e}"
                estatisticas['almas'][alma] = estatisticas_alma
            return estatisticas
        except Exception as e:
            logger.error("Erro ao coletar estatÃ­sticas: %s", e, exc_info=True)
            return {}

    def get_historico_promocoes(self, alma_nome: str, limite: int = 10) -> List[Dict[str, Any]]:
        if not self.is_initialized or not self.metabolismo or not hasattr(self.metabolismo, 'colecoes'):
            return []
        try:
            historico: List[Dict[str, Any]] = []
            alma_key = alma_nome.lower()
            colecoes = self.metabolismo.colecoes.get(alma_key)
            if not colecoes:
                return []
            for camada, colecao in (colecoes or {}).items():
                try:
                    resultados = colecao.get(include=["metadatas", "documents"]) if hasattr(colecao, 'get') else {}
                    metadatas = resultados.get('metadatas', []) if isinstance(resultados, dict) else []
                    documents = resultados.get('documents', []) if isinstance(resultados, dict) else []
                    for i, metadata in enumerate(metadatas):
                        evento = None
                        if metadata.get('data_promocao'):
                            evento = {'tipo': 'PROMOCAO', 'data': metadata['data_promocao'], 'de': metadata.get('camada_original', 'desconhecido'), 'para': camada, 'documento': (documents[i][:100] + '...') if documents else '', 'id': metadata.get('id', 'desconhecido')}
                        elif metadata.get('data_demissao'):
                            evento = {'tipo': 'DEMISSAO', 'data': metadata['data_demissao'], 'de': camada, 'para': self._inferir_camada_destino(camada), 'documento': (documents[i][:100] + '...') if documents else '', 'id': metadata.get('id', 'desconhecido')}
                        if evento:
                            historico.append(evento)
                except Exception as e:
                    logger.error("Erro analisando histÃ³rico na camada %s: %s", camada, e, exc_info=True)
            try:
                historico.sort(key=lambda x: x.get('data', ''), reverse=True)
            except Exception:
                pass
            return historico[:limite]
        except Exception as e:
            logger.error("Erro geral no histÃ³rico de promoÃ§Ãµes: %s", e, exc_info=True)
            return []

    def _inferir_camada_destino(self, camada_origem: str) -> str:
        if camada_origem == 'm1':
            return 'm2'
        if camada_origem == 'm2':
            return 'm3'
        return 'm3'

    def executar_limpeza_manual(self) -> bool:
        if self.metabolismo and hasattr(self.metabolismo, 'executar_limpeza'):
            try:
                self.metabolismo.executar_limpeza()
                logger.info("Limpeza manual do metabolismo executada.")
                return True
            except Exception as e:
                logger.exception("Erro ao executar limpeza manual: %s", e)
                return False
        logger.info("Metabolismo nÃ£o disponÃ­vel para limpeza manual.")
        return False

    def backup_memoria(self, caminho_backup: str) -> bool:
        try:
            if not getattr(self, "client", None) and not os.path.exists(self._memory_db_path):
                logger.warning("Nenhuma base de memÃ³ria encontrada para backup.")
                return False
            shutil.copytree(self._memory_db_path, caminho_backup, dirs_exist_ok=True)
            logger.info("Backup criado: %s", caminho_backup)
            return True
        except Exception as e:
            logger.error("Erro no backup: %s", e, exc_info=True)
            return False

    def shutdown(self) -> None:
        try:
            if self.metabolismo and hasattr(self.metabolismo, 'shutdown'):
                self.metabolismo.shutdown()
            logger.info("GerenteMemoria finalizado.")
        except Exception:
            logger.exception("Erro durante shutdown do GerenteMemoria")

    def _get_timestamp(self) -> str:
        return datetime.now().isoformat()

    def query(self, prompt: str, k_total: int = 5) -> Tuple[str, List[Any]]:
        contexto = self.get_context(prompt, "sistema", k_total)
        contexto_formatado = "\n".join(contexto) if contexto else "Nenhuma memÃ³ria relevante encontrada."
        return contexto_formatado, []

    def promote_chunk(self, doc: Any) -> bool:
        logger.info("PromoÃ§Ã£o automÃ¡tica gerenciada pelo metabolismo (proxy).")
        return True


