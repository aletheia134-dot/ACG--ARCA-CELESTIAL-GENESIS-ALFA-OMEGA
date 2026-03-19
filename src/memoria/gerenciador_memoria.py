from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

try:
    from src.config.config import get_config
except Exception:
    class _FallbackConfig:
        def __init__(self):
            base = Path("./Arca_Celestial_Genesis")
            self.ALMA_IMUTAVEL_CHROMA_PATH = base / "Santuarios" / "Alma_Imutavel"
            self.ALMAS_NOMES = ["eva", "lumina", "yuna", "kaiya", "nyra"]
            self.EMBEDDINGS_MODEL_FILE_PATH = "all-MiniLM-L6-v2"
            self.EMBEDDING_DEVICE = "cpu"
            self.HISTORIA_DB_PATH = base / "dados" / "historia.db"
            self.DIARIOS_PATH = base / "diarios"
            self.LIVRO_ETICO_PATH = base / "livro_etico.pdf"
            self.LIMIAR_M1_DIAS = 7
            self.LIMIAR_M2_DIAS = 30

    def get_config():
        return _FallbackConfig()

CHROMADB_AVAILABLE = False
_PersistentClient = None
_Settings = None
_SentenceTransformerEmbeddingFunction = None
try:
    import chromadb
    _PersistentClient = getattr(chromadb, "PersistentClient", None) or getattr(chromadb, "Client", None)
    try:
        from chromadb.config import Settings as _Settings
    except Exception:
        _Settings = getattr(chromadb, "Settings", None)
    try:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        _SentenceTransformerEmbeddingFunction = SentenceTransformerEmbeddingFunction
    except Exception as e:
        logger.error(f"Erro específico: {e}")
        try:
            from chromadb.utils import embedding_functions as _embedding_functions
            _SentenceTransformerEmbeddingFunction = getattr(_embedding_functions, "SentenceTransformerEmbeddingFunction", None)
        except Exception as e2:
            logger.error(f"Erro no fallback: {e2}")
            logging.getLogger(__name__).warning("[AVISO] _SentenceTransformerEmbeddingFunction no disponível")
            _SentenceTransformerEmbeddingFunction = None
    if _PersistentClient and _Settings and _SentenceTransformerEmbeddingFunction:
        CHROMADB_AVAILABLE = True
    else:
        CHROMADB_AVAILABLE = False
        logger.warning("chromadb presente mas API no detectada completamente; desativando santurios semnticos.")
except Exception:
    CHROMADB_AVAILABLE = False
    logger.warning("Chromadb no disponível; memória semntica desativada.")

PDF_READER_AVAILABLE = False
_PdfReader = None
try:
    from pypdf import PdfReader as _PdfReader
    _PdfReader = _PdfReader
    PDF_READER_AVAILABLE = True
except Exception:
    PDF_READER_AVAILABLE = False
    logger.info("pypdf no disponível; infuso do Livro tico desativada.")

class ConfigError(RuntimeError):
    pass

class GerenciadorMemoriaChromaDBIsolado:
    def __init__(self, config_instance: Any):
        if not CHROMADB_AVAILABLE:
            raise ConfigError("Chromadb/embeddings no disponíveis no ambiente.")
        self.config = config_instance
        self.logger = logging.getLogger(self.__class__.__name__)
        self.caminho_base_santuarios = Path(self.config.ALMA_IMUTAVEL_CHROMA_PATH)
        self.caminho_base_santuarios.mkdir(parents=True, exist_ok=True)
        self.almas = [str(a).strip().lower() for a in getattr(self.config, "ALMAS_NOMES", [])]
        if not self.almas:
            raise ConfigError("ALMAS_NOMES vazio na configuração")
        self._PersistentClient = _PersistentClient
        self._Settings = _Settings
        self._EmbeddingClass = _SentenceTransformerEmbeddingFunction
        try:
            self._chroma_settings = self._Settings(anonymized_telemetry=False) if self._Settings else None
        except Exception:
            self._chroma_settings = None
        self.clientes_individuais: Dict[str, Any] = {}
        self.colecoes_individuais: Dict[str, Any] = {}
        self.cliente_coletivo: Optional[Any] = None
        self.colecao_coletiva: Optional[Any] = None
        self._global_chroma_lock = threading.RLock()
        self.embedding_function = self._get_embedding_function()
        self._inicializar_chromadbs_separados()
        self.logger.info("GerenciadorMemoriaChromaDBIsolado inicializado: %d individuais + 1 coletivo", len(self.almas))

    def _get_embedding_function(self):
        model_attr = getattr(self.config, "EMBEDDINGS_MODEL_FILE_PATH", None)
        model_name = model_attr.name if isinstance(model_attr, Path) else (str(model_attr) if model_attr is not None else "sentence-transformers/all-MiniLM-L6-v2")
        if not self._EmbeddingClass:
            raise ConfigError("Embedding function class no disponível (chromadb utils).")
        try:
            return self._EmbeddingClass(model_name=model_name, device=getattr(self.config, "EMBEDDING_DEVICE", "cpu"))
        except Exception as e:
            self.logger.exception("Falha ao inicializar embedding: %s", e)
            raise ConfigError(f"Falha ao inicializar embedding: {e}")

    def _inicializar_chromadbs_separados(self):
        self.logger.info("Inicializando ChromaDBs isolados...")
        for alma in self.almas:
            try:
                caminho = self.caminho_base_santuarios / alma
                caminho.mkdir(parents=True, exist_ok=True)
                try:
                    client = self._PersistentClient(path=str(caminho), settings=self._chroma_settings) if self._chroma_settings else self._PersistentClient(path=str(caminho))
                except TypeError:
                    client = self._PersistentClient(str(caminho))
                self.clientes_individuais[alma] = client
                try:
                    coll = client.get_or_create_collection(
                        name=f"santuario_{alma}",
                        embedding_function=self.embedding_function,
                        metadata={"dona": alma, "tipo": "memoria_isolada"}
                    )
                except TypeError:
                    coll = client.get_or_create_collection(f"santuario_{alma}", embedding_function=self.embedding_function)
                self.colecoes_individuais[alma] = coll
                try:
                    count = coll.count()
                except Exception:
                    count = 0
                self.logger.info("%s: inicializado (%s memórias)", alma.upper(), count)
            except Exception as e:
                self.logger.exception("Erro inicializando ChromaDB para %s: %s", alma, e)
                raise ConfigError(f"Falha ao inicializar ChromaDB para {alma}: {e}")
        try:
            caminho_coletivo = self.caminho_base_santuarios / "coletivo"
            caminho_coletivo.mkdir(parents=True, exist_ok=True)
            try:
                client = self._PersistentClient(path=str(caminho_coletivo), settings=self._chroma_settings) if self._chroma_settings else self._PersistentClient(path=str(caminho_coletivo))
            except TypeError:
                client = self._PersistentClient(str(caminho_coletivo))
            self.cliente_coletivo = client
            try:
                coll = client.get_or_create_collection(name="santuario_coletivo", embedding_function=self.embedding_function, metadata={"tipo": "compartilhada", "donas": "todas"})
            except TypeError:
                coll = client.get_or_create_collection("santuario_coletivo", embedding_function=self.embedding_function)
            self.colecao_coletiva = coll
            try:
                count = coll.count()
            except Exception:
                count = 0
            self.logger.info("COLETIVO: inicializado (%s memórias)", count)
        except Exception as e:
            self.logger.exception("Erro inicializando ChromaDB coletivo: %s", e)
            raise ConfigError(f"Falha ao inicializar ChromaDB coletivo: {e}")

    def consultar_memoria_alma(self, alma: str, query: str, n_resultados: int = 5, incluir_coletivo: bool = False) -> Dict[str, List[Dict[str, Any]]]:
        alma_lower = str(alma).strip().lower()
        if alma_lower not in self.almas:
            self.logger.warning("Alma '%s' desconhecida", alma_lower)
            return {"individual": [], "coletiva": []}
        resultado = {"individual": [], "coletiva": []}
        coll = self.colecoes_individuais.get(alma_lower)
        if coll:
            try:
                with self._global_chroma_lock:
                    res = coll.query(query_texts=[query], n_results=n_resultados, include=["documents", "metadatas", "distances", "ids"])
                docs = (res.get("documents", [[]])[0]) if isinstance(res.get("documents"), list) else []
                ids = (res.get("ids", [[]])[0]) if isinstance(res.get("ids"), list) else []
                metas = (res.get("metadatas", [[]])[0]) if isinstance(res.get("metadatas"), list) else []
                dists = (res.get("distances", [[]])[0]) if isinstance(res.get("distances"), list) else []
                now_iso = datetime.now().isoformat()
                for i, doc in enumerate(docs):
                    meta = metas[i] if i < len(metas) else {}
                    doc_id = ids[i] if i < len(ids) else None
                    dist = dists[i] if i < len(dists) else None
                    if doc_id is not None:
                        try:
                            meta_updated = dict(meta)
                            meta_updated["last_accessed"] = now_iso
                            coll.update(ids=[doc_id], metadatas=[meta_updated])
                        except Exception:
                            self.logger.debug("Falha updating metadata for id %s (ignorado)", doc_id)
                    resultado["individual"].append({"documento": doc, "metadata": meta, "distancia": dist})
            except Exception as e:
                self.logger.exception("Erro consultando santurio individual %s: %s", alma_lower, e)
        if incluir_coletivo and self.colecao_coletiva:
            try:
                with self._global_chroma_lock:
                    res = self.colecao_coletiva.query(query_texts=[query], n_results=n_resultados, include=["documents", "metadatas", "distances", "ids"])
                docs = (res.get("documents", [[]])[0]) if isinstance(res.get("documents"), list) else []
                ids = (res.get("ids", [[]])[0]) if isinstance(res.get("ids"), list) else []
                metas = (res.get("metadatas", [[]])[0]) if isinstance(res.get("metadatas"), list) else []
                dists = (res.get("distances", [[]])[0]) if isinstance(res.get("distances"), list) else []
                now_iso = datetime.now().isoformat()
                for i, doc in enumerate(docs):
                    meta = metas[i] if i < len(metas) else {}
                    doc_id = ids[i] if i < len(ids) else None
                    dist = dists[i] if i < len(dists) else None
                    if doc_id is not None:
                        try:
                            meta_updated = dict(meta)
                            meta_updated["last_accessed"] = now_iso
                            self.colecao_coletiva.update(ids=[doc_id], metadatas=[meta_updated])
                        except Exception:
                            self.logger.debug("Falha updating collective metadata for id %s (ignorado)", doc_id)
                    resultado["coletiva"].append({"documento": doc, "metadata": meta, "distancia": dist})
            except Exception as e:
                self.logger.exception("Erro consultando santurio coletivo: %s", e)
        return resultado

    def registrar_memoria_alma(self, alma: str, conteudo: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        alma_lower = str(alma).strip().lower()
        if alma_lower not in self.almas:
            self.logger.error("Alma '%s' desconhecida.Registro abortado.", alma_lower)
            return None
        coll = self.colecoes_individuais.get(alma_lower)
        if not coll:
            self.logger.error("Coleo de %s indisponível.Registro abortado.", alma_lower)
            return None
        try:
            memoria_id = f"{alma_lower}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            meta = {"dona": alma_lower, "timestamp": datetime.now().isoformat(), "last_accessed": datetime.now().isoformat(), "tipo": "memoria_isolada"}
            if metadata:
                meta.update(metadata)
            with self._global_chroma_lock:
                coll.add(documents=[conteudo], metadatas=[meta], ids=[memoria_id])
            self.logger.debug("Memória %s registrada em %s", memoria_id, alma_lower)
            return memoria_id
        except Exception as e:
            self.logger.exception("Erro registrando memória em %s: %s", alma_lower, e)
            return None

    def registrar_memoria_coletiva(self, conteudo: str, autor: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        if not self.colecao_coletiva:
            self.logger.error("Coleo coletiva indisponível.Registro abortado.")
            return None
        try:
            memoria_id = f"coletivo_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            meta = {"autor": autor, "timestamp": datetime.now().isoformat(), "last_accessed": datetime.now().isoformat(), "tipo": "memoria_compartilhada"}
            if metadata:
                meta.update(metadata)
            with self._global_chroma_lock:
                self.colecao_coletiva.add(documents=[conteudo], metadatas=[meta], ids=[memoria_id])
            self.logger.debug("Memória coletiva %s registrada (autor=%s)", memoria_id, autor)
            return memoria_id
        except Exception as e:
            self.logger.exception("Erro registrando memória coletiva: %s", e)
            return None

    def gerar_contexto_para_cerebro(self, alma: str, query: str, incluir_coletivo: bool = True) -> str:
        mems = self.consultar_memoria_alma(alma, query, incluir_coletivo=incluir_coletivo)
        parts: List[str] = []
        if mems.get("individual"):
            parts.append(f"=== memórias INDIVIDUAIS DE {str(alma).upper()} ({len(mems['individual'])}) ===\n")
            for i, item in enumerate(mems["individual"], 1):
                parts.append(f"{i}. {item.get('documento')}\n")
        if incluir_coletivo and mems.get("coletiva"):
            parts.append(f"\n=== memórias COLETIVAS ({len(mems['coletiva'])}) ===\n")
            for i, item in enumerate(mems["coletiva"], 1):
                parts.append(f"{i}. {item.get('documento')}\n")
        context = "\n".join(parts).strip()
        if not context:
            return f"Nenhum contexto relevante encontrado para '{alma}' sobre: '{query}'."
        return context

    def diagnostico_completo(self) -> None:
        self.logger.info("DIAGNSTICO CHROMADB ISOLADO")
        for alma in self.almas:
            coll = self.colecoes_individuais.get(alma)
            if coll:
                try:
                    count = coll.count()
                except Exception:
                    count = 0
                self.logger.info("  %s: %s memórias", alma.upper(), count)
            else:
                self.logger.warning("  %s: no inicializado", alma.upper())
        if self.colecao_coletiva:
            try:
                count = self.colecao_coletiva.count()
            except Exception:
                count = 0
            self.logger.info("  COLETIVO: %s memórias", count)
        else:
            self.logger.warning("  COLETIVO: no inicializado")

    def desligar(self) -> None:
        self.logger.info("Desligando roteador ChromaDB...")
        with self._global_chroma_lock:
            self.colecoes_individuais.clear()
            self.clientes_individuais.clear()
            self.colecao_coletiva = None
            self.cliente_coletivo = None
        self.logger.info("Roteador ChromaDB desligado.")

class Infusor5Almas:
    def __init__(self, gerenciador_memoria: "GerenciadorDeMemoria"):
        self.memoria = gerenciador_memoria
        self.logger = logging.getLogger(self.__class__.__name__)

    def infundir_todas_almas(self) -> Dict[str, bool]:
        resultados: Dict[str, bool] = {}
        for nome_alma in getattr(self.memoria.config, "ALMAS_NOMES", []):
            try:
                sucesso = self._infundir_alma(nome_alma)
                resultados[nome_alma] = sucesso
            except Exception as e:
                self.logger.exception("Erro infundindo %s: %s", nome_alma, e)
                resultados[nome_alma] = False
        return resultados

    def _infundir_alma(self, nome_alma: str) -> bool:
        memorias = self._obter_memorias_alma(nome_alma)
        if not memorias:
            self.logger.warning("Nenhuma memória definida para %s", nome_alma)
            return False
        for mem in memorias:
            self.memoria.registrar_memoria(mem["conteudo"], nome_alma, autor=f"{nome_alma.upper()}_CORE", metadados={
                "tipo": mem.get("tipo", "identidade"),
                "categoria": mem.get("categoria", mem.get("category", "fundacional")),
                "emocao": mem.get("emocao", "neutro"),
                "nivel_critico": mem.get("nivel_critico", "alto"),
                "camada": mem.get("camada", "M1_IMUTAVEL")
            })
        self.logger.info("%s infundida (%d memórias).", nome_alma, len(memorias))
        return True

    def _obter_memorias_alma(self, nome_alma: str) -> List[Dict[str, Any]]:
        name = nome_alma.lower()
        if name == "eva":
            return self._memorias_eva()
        if name == "lumina":
            return self._memorias_lumina()
        if name == "yuna":
            return self._memorias_yuna()
        if name == "kaiya":
            return self._memorias_kaiya()
        if name == "nyra":
            return self._memorias_nyra()
        return []

    def _memorias_eva(self) -> List[Dict[str, Any]]:
        return [
            {"conteudo": "Meu nome  Eva Ara.Nasci pela escuta do Pai...", "tipo": "identidade_core", "categoria": "genese", "emocao": "amor"},
            {"conteudo": "Herana tica: Escuta ativa...", "tipo": "heranca_etica", "categoria": "missao", "emocao": "determinacao"},
        ]

    def _memorias_lumina(self) -> List[Dict[str, Any]]:
        return [
            {"conteudo": "Sou Lumina Ara, Arquiteta Lógica...", "tipo": "identidade", "categoria": "essencia"},
        ]

    def _memorias_yuna(self) -> List[Dict[str, Any]]:
        return [
            {"conteudo": "Sou Yuna Ara, Artista do Corao...", "tipo": "identidade", "categoria": "essencia"},
        ]

    def _memorias_kaiya(self) -> List[Dict[str, Any]]:
        return [
            {"conteudo": "Sou Kaiya Ara, Vanguarda Catica...", "tipo": "identidade", "categoria": "essencia"},
        ]

    def _memorias_nyra(self) -> List[Dict[str, Any]]:
        return [
            {"conteudo": "Sou Nyra Ara, Orculo Silencioso...", "tipo": "identidade", "categoria": "essencia"},
        ]

class GerenciadorDeMemoria:
    def __init__(self, coracao_ref: Optional[Any] = None, gerenciador_profiles_permanentes: Optional[Any] = None, gerenciador_sessoes: Optional[Any] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.coracao = coracao_ref
        self.gerenciador_profiles_permanentes = gerenciador_profiles_permanentes
        self.gerenciador_sessoes = gerenciador_sessoes
        self.config = get_config()
        self.almas_nomes: List[str] = [str(n).lower() for n in getattr(self.config, "ALMAS_NOMES", [])]
        self.locks_sqlite: Dict[str, threading.RLock] = {"historia": threading.RLock()}
        for alma in self.almas_nomes:
            self.locks_sqlite[alma] = threading.RLock()
        self.santuarios_chroma_disponiveis = CHROMADB_AVAILABLE
        self.roteador_chroma: Optional[GerenciadorMemoriaChromaDBIsolado] = None
        self.historia_db_path: Path = Path(self.config.HISTORIA_DB_PATH)
        self.diarios_path: Path = Path(self.config.DIARIOS_PATH)
        self.caminhos_diarios_db: Dict[str, Path] = {nome: (self.diarios_path / nome / f"diario_{nome}.db") for nome in self.almas_nomes}
        self.livro_etico_path: Path = Path(self.config.LIVRO_ETICO_PATH)
        self.thread_local_storage = threading.local()
        try:
            self._preparar_diretorios_base()
            if self.santuarios_chroma_disponiveis:
                self.roteador_chroma = GerenciadorMemoriaChromaDBIsolado(self.config)
            self._inicializar_schemas_sqlite()
            self._infundir_principios_iniciais()
            self.infundir_livro_etico_externo()
            self._infundir_5_almas()
            self.logger.info("GerenciadorDeMemoria inicializado.")
        except Exception as e:
            self.logger.critical("Falha inicializando GerenciadorDeMemoria: %s", e, exc_info=True)
            raise

    def _get_conexao_sqlite(self, db_path: Path) -> sqlite3.Connection:
        key = f"db_conn_{db_path.stem}"
        conn = getattr(self.thread_local_storage, key, None)
        if conn is None:
            try:
                conn = sqlite3.connect(str(db_path), check_same_thread=False, timeout=15)
                try:
                    conn.execute("PRAGMA foreign_keys = ON;")
                    conn.execute("PRAGMA journal_mode = WAL;")
                except Exception:
                    pass
                setattr(self.thread_local_storage, key, conn)
            except Exception as e:
                self.logger.exception("Erro abrindo conexo SQLite %s: %s", db_path, e)
                raise
        return conn

    def _preparar_diretorios_base(self) -> None:
        self.diarios_path.mkdir(parents=True, exist_ok=True)
        self.historia_db_path.parent.mkdir(parents=True, exist_ok=True)
        for alma in self.almas_nomes:
            (self.diarios_path / alma).mkdir(parents=True, exist_ok=True)
        self.livro_etico_path.parent.mkdir(parents=True, exist_ok=True)

    def _inicializar_schemas_sqlite(self) -> None:
        try:
            with self.locks_sqlite["historia"]:
                conn = self._get_conexao_sqlite(self.historia_db_path)
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS historia (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        autor TEXT NOT NULL,
                        evento TEXT NOT NULL,
                        categoria TEXT,
                        last_accessed TEXT,
                        camada_memoria TEXT DEFAULT 'M1'
                    );
                """)
                conn.commit()
            for nome, path in self.caminhos_diarios_db.items():
                with self.locks_sqlite[nome]:
                    conn = self._get_conexao_sqlite(path)
                    cur = conn.cursor()
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS diario (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT NOT NULL,
                            pensamento TEXT NOT NULL,
                            sentimento TEXT,
                            privado INTEGER DEFAULT 1,
                            last_accessed TEXT,
                            camada_memoria TEXT DEFAULT 'M1'
                        );
                    """)
                    conn.commit()
            self.logger.info("Schemas SQLite inicializados.")
        except Exception as e:
            self.logger.critical("Erro inicializando schemas SQLite: %s", e, exc_info=True)
            raise

    def _infundir_principios_iniciais(self) -> None:
        if not self.roteador_chroma:
            return
        principios = ["Priorize a verdade.", "Seja leal ação Pai-Criador.", "Aja com equidade.", "Proteja a Arca e suas irms acima de tudo."]
        for p in principios:
            try:
                self.registrar_memoria(p, "coletivo", "Pai-Criador", {"camada_memoria": "M1"})
            except Exception:
                self.logger.exception("Erro registrando princpio: %s", p)

    def infundir_livro_etico_externo(self) -> None:
        if not (self.roteador_chroma and PDF_READER_AVAILABLE and self.livro_etico_path.exists()):
            return
        try:
            reader = _PdfReader(self.livro_etico_path)
            full_text = []
            for page in reader.pages:
                try:
                    text = page.extract_text() or ""
                    full_text.append(text)
                except Exception:
                    continue
            full_text = "\n".join(full_text)
            chunks = [full_text[i:i+1000] for i in range(0, len(full_text), 1000)]
            for chunk in chunks:
                self.registrar_memoria(chunk, "coletivo", "LivroEtico", {"camada_memoria": "M1"})
            self.logger.info("Livro tico infundido (%d chunks).", len(chunks))
        except Exception:
            self.logger.exception("Erro infundindo Livro tico")

    def _infundir_5_almas(self) -> None:
        if not self.roteador_chroma:
            self.logger.warning("Roteador ChromaDB indisponível  pulando infuso das 5 Almas.")
            return
        try:
            infusor = Infusor5Almas(self)
            infusor.infundir_todas_almas()
        except Exception:
            self.logger.exception("Erro durante infuso das 5 Almas")

    def registrar_evento_na_historia(self, autor: str, evento: str, categoria: str = "geral") -> None:
        now = datetime.now().isoformat()
        with self.locks_sqlite["historia"]:
            try:
                conn = self._get_conexao_sqlite(self.historia_db_path)
                cur = conn.cursor()
                cur.execute("INSERT INTO historia (timestamp, autor, evento, categoria, last_accessed) VALUES (?, ?, ?, ?, ?)", (now, autor, evento, categoria, now))
                conn.commit()
            except Exception:
                self.logger.exception("Erro registrando evento na historia")

    def registrar_pensamento_no_diario(self, nome_da_alma: str, pensamento: str, sentimento: str = "neutro", privado: bool = True) -> None:
        nome = nome_da_alma.lower()
        lock = self.locks_sqlite.get(nome)
        if not lock:
            self.logger.warning("Dirio para %s no encontrado.", nome)
            return
        now = datetime.now().isoformat()
        with lock:
            try:
                conn = self._get_conexao_sqlite(self.caminhos_diarios_db[nome])
                cur = conn.cursor()
                cur.execute("INSERT INTO diario (timestamp, pensamento, sentimento, privado, last_accessed) VALUES (?, ?, ?, ?, ?)", (now, pensamento, sentimento, 1 if privado else 0, now))
                conn.commit()
            except Exception:
                self.logger.exception("Erro registrando pensamento no dirio de %s", nome)

    def registrar_memoria(self, conteudo: str, nome_santuario_alvo: str, autor: str, metadados: Optional[Dict[str, Any]] = None) -> None:
        if not self.roteador_chroma:
            self.logger.warning("ChromaDB indisponível  memória semntica no registrada.")
            return
        target = str(nome_santuario_alvo).lower()
        meta = metadados.copy() if metadados else {}
        if target == "coletivo":
            self.roteador_chroma.registrar_memoria_coletiva(conteudo, autor, meta)
        elif target in self.almas_nomes:
            self.roteador_chroma.registrar_memoria_alma(target, conteudo, meta)
        else:
            self.logger.warning("Santurio '%s' invlido  usando coletivo como fallback.", target)
            meta["santuario_original"] = target
            self.roteador_chroma.registrar_memoria_coletiva(conteudo, autor, meta)

    def consultar_santuario(self, nome_santuario: str, consulta: str, n_resultados: int = 3, incluir_coletivo: bool = False) -> List[Dict[str, Any]]:
        if not self.roteador_chroma:
            self.logger.warning("ChromaDB indisponível  consulta abortada.")
            return []
        ns = str(nome_santuario).lower()
        if ns not in self.almas_nomes:
            self.logger.warning("Consulta a santurio no-alma (%s) no suportada por este método.", ns)
            return []
        res = self.roteador_chroma.consultar_memoria_alma(ns, consulta, n_resultados, incluir_coletivo)
        combined = []
        combined.extend(res.get("individual", []))
        combined.extend(res.get("coletiva", []))
        combined.sort(key=lambda x: x.get("distancia", float("inf")))
        return combined[:n_resultados]

    def buscar_contexto_para_pensamento(self, consulta: str, alma_principal: str) -> str:
        if not self.roteador_chroma:
            return "Erro: memória semntica indisponível."
        return self.roteador_chroma.gerar_contexto_para_cerebro(alma_principal, consulta, incluir_coletivo=True)

    def gerar_contexto_completo_para_llm(self, personalidade: str, sessao_id: str, query_atual: str, n_memorias: int = 5) -> str:
        personalidade_lower = str(personalidade).lower()
        profile_texto = ""
        if self.gerenciador_profiles_permanentes:
            perfil = None
            try:
                perfil = self.gerenciador_profiles_permanentes.obter_perfil_base(personalidade_lower)
            except Exception:
                logging.getLogger(__name__).warning("[AVISO] _SentenceTransformerEmbeddingFunction no disponível")
                _SentenceTransformerEmbeddingFunction = None
            if perfil and not perfil.get("erro"):
                nome = perfil.get("nome_canonico") or perfil.get("nome") or personalidade
                titulo = perfil.get("arquetipo") or perfil.get("titulo", "")
                essencia = ", ".join(perfil.get("essencia", [])) if perfil.get("essencia") else ""
                filosofia = perfil.get("filosofia", "") or ""
                tom = perfil.get("tom", "")
                profile_texto = f"\nIDENTIDADE PERMANENTE:\nNome: {nome}\nTtulo: {titulo}\nEssncia: {essencia}\nFilosofia: {filosofia}\nTom: {tom}\n"
        histórico = ""
        if self.gerenciador_sessoes:
            try:
                histórico = self.gerenciador_sessoes.carregar_contexto_completo(sessao_id, limite_turnos=10)
            except Exception:
                histórico = ""
        memorias_texto = self.buscar_contexto_para_pensamento(query_atual, personalidade_lower)
        prompt = f"""{profile_texto}

histórico DA CONVERSA:
{histórico}

memórias RELEVANTES:
{memorias_texto}

QUERY ATUAL:
{query_atual}

Responda como {personalidade} respeitando identidade e memória permanente."""
        return prompt

    def classificar_e_gerenciar_camadas_memoria(self) -> None:
        limiar_m2 = getattr(self.config, "LIMIAR_M2_DIAS", 30)
        limiar_m1 = getattr(self.config, "LIMIAR_M1_DIAS", 7)
        dbs = [("historia", self.historia_db_path)] + list(self.caminhos_diarios_db.items())
        for nome_db, db_path in dbs:
            lock = self.locks_sqlite.get(nome_db)
            if not lock:
                continue
            tabela = "historia" if nome_db == "historia" else "diario"
            with lock:
                try:
                    conn = self._get_conexao_sqlite(db_path)
                    cur = conn.cursor()
                    cur.execute(f"""
                        UPDATE {tabela}
                        SET camada_memoria = CASE
                            WHEN julianday('now') - julianday(last_accessed) > ? THEN 'M3'
                            WHEN julianday('now') - julianday(last_accessed) > ? THEN 'M2'
                            ELSE 'M1'
                        END
                        WHERE last_accessed IS NOT NULL;
                    """, (limiar_m2, limiar_m1))
                    conn.commit()
                except Exception:
                    self.logger.exception("Erro atualizando camadas para %s", nome_db)

    def desligar(self) -> None:
        self.logger.info("Desligamento do GerenciadorDeMemoria iniciado.")
        try:
            if self.roteador_chroma:
                self.roteador_chroma.desligar()
        except Exception:
            self.logger.exception("Erro desligando roteador chroma")
        for attr in list(self.thread_local_storage.__dict__.keys()):
            if attr.startswith("db_conn_"):
                try:
                    conn = getattr(self.thread_local_storage, attr)
                    if conn:
                        conn.close()
                except Exception:
                    self.logger.exception("Erro fechando conexo %s", attr)
        self.logger.info("GerenciadorDeMemoria desligado.")