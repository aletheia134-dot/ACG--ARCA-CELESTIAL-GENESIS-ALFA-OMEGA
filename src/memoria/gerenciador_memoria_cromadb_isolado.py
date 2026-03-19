# -*- coding: utf-8 -*-
"""
GerenciadorMemoriaChromaDBIsolado - roteador de ChromaDBs isolados por Alma + coletivo

Responsabilidades:
 - Criar/abrir um ChromaDB independente por Alma (5) + 1 coletivo
 - Garantir isolamento fsico e semntico entre colees/almas
 - Prover operações defensivas de consulta e escrita com locks para thread-safety
 - Fornecer fallback e mensagens claras quando dependncias (chromadb / embeddings) faltarem

Observaes:
 - Este módulo  defensivo: tenta detectar variaes de API do chromadb entre verses.
 - Em ambientes sem chromadb ou embeddings, a inicialização levantar RuntimeError.
"""
from __future__ import annotations

import os
import logging
import threading
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# datetime unificado
from datetime import datetime

# ── Desligar telemetria do ChromaDB / PostHog ANTES de qualquer import do chromadb ──
# Corrige: "capture() takes 1 positional argument but 3 were given"
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY", "False")
os.environ.setdefault("POSTHOG_API_KEY", "")  # força chave vazia → telemetry_guard desativa

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# ----- Exceptions locais -----
class ConfigError(RuntimeError):
    """Erro de configuração/inicialização do gerenciador de ChromaDBs."""
    pass

# ----- Import defensivo de chromadb / embedding functions -----
CHROMADB_AVAILABLE = False
_PersistentClientCls = None
_SettingsCls = None
_SentenceTransformerEmbeddingFunction = None

try:
    import chromadb  # type: ignore
    # chromadb API varies por verso  tentar detectar os nomes
    _PersistentClientCls = getattr(chromadb, "PersistentClient", None) or getattr(chromadb, "Client", None)
    # Settings pode estar em chromadb.config.Settings
    try:
        from chromadb.config import Settings as _SettingsCls  # type: ignore
    except Exception:
        _SettingsCls = getattr(chromadb, "Settings", None)

    # embedding functions utilitrio
    try:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction  # type: ignore
        _SentenceTransformerEmbeddingFunction = SentenceTransformerEmbeddingFunction
    except Exception:
        # fallback: try module path variation
        try:
            from chromadb.utils import embedding_functions  # type: ignore
            _SentenceTransformerEmbeddingFunction = getattr(embedding_functions, "SentenceTransformerEmbeddingFunction", None)
        except Exception:
            logging.getLogger(__name__).warning("_SentenceTransformerEmbeddingFunction não disponível — sentence-transformers pode estar ausente.")
            _SentenceTransformerEmbeddingFunction = None

    if _PersistentClientCls is not None and _SettingsCls is not None and _SentenceTransformerEmbeddingFunction is not None:
        CHROMADB_AVAILABLE = True
    else:
        # partial availability is considered "not fully available" for our needs
        CHROMADB_AVAILABLE = False
except Exception:
    CHROMADB_AVAILABLE = False

# ----- Classe principal -----
class GerenciadorMemoriaChromaDBIsolado:
    """
    Gerencia ChromaDBs fisicamente separados:
      - Um por cada alma listada em config.ALMAS_NOMES
      - Um santurio coletivo (compartilhado)

    Construtor espera um objeto de configuração com atributos:
      - ALMA_IMUTAVEL_CHROMA_PATH: Path (ou str) base para armazenar DBs por alma
      - ALMAS_NOMES: iterable de nomes (str) das almas
      - EMBEDDINGS_MODEL_FILE_PATH: Path ou str com nome do modelo de embedding
      - EMBEDDING_DEVICE: str (opcional, padrão 'cpu')
    """

    def __init__(self, config_instance: Any):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config_instance

        # Validar pr-requisitos
        if not CHROMADB_AVAILABLE:
            raise ConfigError(
                "Chromadb ou utilitrios de embedding no disponíveis. "
                "Instale 'chromadb' e 'sentence-transformers' e verifique a verso."
            )

        # Normalizar caminhos e nomes
        # Suporte a: atributo direto, ConfigWrapper.get(), dict aninhado
        base = self._ler_config("ALMA_IMUTAVEL_CHROMA_PATH", secao="MEMORIA",
                                chave_alt="alma_imutavel_chroma_path",
                                fallback_chave="chroma_persist_directory")
        if base is None:
            # Último recurso: usar subpasta do santuário padrão
            santuarios = self._ler_config("sanctuaries_dir", secao="PATHS", fallback_chave="sanctuaries_dir")
            if santuarios:
                base = str(Path(santuarios) / "Alma_Imutavel")
                self.logger.warning("ALMA_IMUTAVEL_CHROMA_PATH ausente na config — usando '%s'", base)
            else:
                base = "santuarios/Alma_Imutavel"
                self.logger.warning("ALMA_IMUTAVEL_CHROMA_PATH e sanctuaries_dir ausentes — usando '%s'", base)

        self.caminho_base_santuarios = Path(base)
        self.caminho_base_santuarios.mkdir(parents=True, exist_ok=True)

        # Leitura de almas: suporte a lista, CSV string, atributo direto
        raw_almas = self._ler_config("ALMAS_NOMES", secao="ALMAS",
                                    chave_alt="lista_almas_votantes_csv",
                                    fallback_chave="lista_almas_votantes_csv")
        if not raw_almas:
            # default seguro
            raw_almas = "eva,lumina,nyra,yuna,kaiya,wellington"
            self.logger.warning("ALMAS_NOMES ausente na config — usando lista padrão")
        # se for string CSV, converter em lista
        if isinstance(raw_almas, str):
            raw_almas = [a.strip() for a in raw_almas.split(",") if a.strip()]
        # normalizar nomes para lowercase e sem espaos
        self.almas: List[str] = [str(a).strip().lower() for a in raw_almas]

        # Criar lock global para operações que tocam mltiplos clientes/colees
        self._global_chroma_lock = threading.RLock()

        # Detectar classes/funcs carregadas defensivamente
        self._PersistentClientCls = _PersistentClientCls
        self._SettingsCls = _SettingsCls
        self._SentenceTransformerEmbeddingFunction = _SentenceTransformerEmbeddingFunction

        # Configurações Chroma (settings)
        try:
            # Criar objeto Settings se a classe estiver disponível (algumas verses exigem)
            if self._SettingsCls is not None:
                self._chroma_settings = self._SettingsCls(anonymized_telemetry=False)
            else:
                self._chroma_settings = None
        except Exception:
            self._chroma_settings = None

        # Preparar containers
        self.clientes_individuais: Dict[str, Any] = {}
        self.colecoes_individuais: Dict[str, Any] = {}
        self.cliente_coletivo: Optional[Any] = None
        self.colecao_coletiva: Optional[Any] = None

        # Inicializar embedding function (pode lanar)
        self.embedding_function = self._get_embedding_function()

        # Inicializar clients/colees
        self._inicializar_chromadbs_separados()

        self.logger.info("GerenciadorMemoriaChromaDBIsolado inicializado: %d individuais + 1 coletivo",
                         len(self.almas))

    def _ler_config(self, chave: str, secao: str = None, chave_alt: str = None, fallback_chave: str = None) -> Optional[str]:
        """
        Lê valor do config com suporte a múltiplos formatos:
        - Atributo direto no objeto (dataclass/objeto simples)
        - ConfigWrapper.get(secao, chave)
        - ConfigWrapper.get(secao, chave_alt)
        - dict aninhado
        """
        cfg = self.config
        # 1) Atributo direto (objeto simples / dataclass)
        val = getattr(cfg, chave, None)
        if val is not None:
            return str(val)
        # 2) ConfigWrapper / ConfigParser: get(secao, chave)
        if secao and hasattr(cfg, "get") and callable(cfg.get):
            try:
                val = cfg.get(secao, chave, None)
                if val:
                    return str(val)
            except Exception:
                pass
            # 3) chave alternativa
            if chave_alt:
                try:
                    val = cfg.get(secao, chave_alt, None)
                    if val:
                        return str(val)
                except Exception:
                    pass
            # 4) fallback_chave
            if fallback_chave:
                try:
                    val = cfg.get(secao, fallback_chave, None)
                    if val:
                        return str(val)
                except Exception:
                    pass
        # 5) dict aninhado
        if isinstance(cfg, dict):
            if secao and secao.upper() in cfg:
                sec = cfg[secao.upper()]
                for k in [chave, chave_alt, fallback_chave]:
                    if k and k.upper() in sec:
                        return str(sec[k.upper()])
            for k in [chave, chave_alt, fallback_chave]:
                if k and k.upper() in cfg:
                    return str(cfg[k.upper()])
        return None

    def _get_embedding_function(self):
        """Cria a função de embedding usando o model name/path da config (defensivo)."""
        model_attr = self._ler_config("EMBEDDINGS_MODEL_FILE_PATH", secao="MODELOS",
                                      chave_alt="embeddings_model_file_path")
        if model_attr is None:
            # fallback para nome padrão
            model_name = "sentence-transformers/all-MiniLM-L6-v2"
        else:
            # aceitar Path ou str
            if isinstance(model_attr, Path):
                model_name = model_attr.name
            else:
                model_name = str(model_attr)

        if not self._SentenceTransformerEmbeddingFunction:
            raise ConfigError("Embedding function class no disponível na instalao do chromadb.")

        try:
            # o construtor aceita model_name e device; device opcional
            device = self._ler_config("EMBEDDING_DEVICE", secao="MODELOS", chave_alt="embedding_device") or "cpu"
            return self._SentenceTransformerEmbeddingFunction(model_name=model_name, device=device)
        except Exception as e:
            self.logger.critical("Falha ao inicializar Embedding Function com '%s': %s", model_name, e, exc_info=True)
            raise ConfigError(f"Falha ao carregar Embedding Function: {e}")

    def _inicializar_chromadbs_separados(self) -> None:
        """Cria/abre um cliente PersistentClient por pasta (um por alma) e um coletivo."""
        # Para cada alma, criar subpasta e PersistentClient/coleo
        for alma in self.almas:
            try:
                caminho_alma_db = (self.caminho_base_santuarios / alma)
                caminho_alma_db.mkdir(parents=True, exist_ok=True)

                # Criar cliente (defensivo quanto  assinatura)
                try:
                    if self._chroma_settings is not None:
                        cliente = self._PersistentClientCls(path=str(caminho_alma_db), settings=self._chroma_settings)
                    else:
                        cliente = self._PersistentClientCls(path=str(caminho_alma_db))
                except TypeError:
                    # fallback: diferentes verses aceitam diferentes args
                    cliente = self._PersistentClientCls(str(caminho_alma_db))

                self.clientes_individuais[alma] = cliente

                # get_or_create_collection pode variar a assinatura; tentar de forma defensiva
                try:
                    colecao = cliente.get_or_create_collection(
                        name=f"santuario_{alma}",
                        embedding_function=self.embedding_function,
                        metadata={"dona": alma, "tipo": "memoria_isolada"}
                    )
                except TypeError:
                    # verso com assinatura reduzida
                    colecao = cliente.get_or_create_collection(f"santuario_{alma}", embedding_function=self.embedding_function)

                self.colecoes_individuais[alma] = colecao

                # contagem inicial (algumas colees podem no suportar count)
                try:
                    count = colecao.count()
                except Exception:
                    count = 0
                self.logger.info("%s: ChromaDB isolado inicializado (%d memórias)", alma.upper(), count)

            except Exception as e:
                self.logger.exception("Erro ao inicializar ChromaDB isolado para '%s': %s", alma, e)
                raise ConfigError(f"Falha ao inicializar ChromaDB para Alma '{alma}': {e}")

        # Inicializar coletivo
        try:
            caminho_coletivo_db = (self.caminho_base_santuarios / "coletivo")
            caminho_coletivo_db.mkdir(parents=True, exist_ok=True)

            try:
                if self._chroma_settings is not None:
                    cliente_coletivo = self._PersistentClientCls(path=str(caminho_coletivo_db), settings=self._chroma_settings)
                else:
                    cliente_coletivo = self._PersistentClientCls(path=str(caminho_coletivo_db))
            except TypeError:
                cliente_coletivo = self._PersistentClientCls(str(caminho_coletivo_db))

            self.cliente_coletivo = cliente_coletivo

            try:
                colecao_coletiva = cliente_coletivo.get_or_create_collection(
                    name="santuario_coletivo",
                    embedding_function=self.embedding_function,
                    metadata={"tipo": "compartilhada", "donas": "todas"}
                )
            except TypeError:
                colecao_coletiva = cliente_coletivo.get_or_create_collection("santuario_coletivo", embedding_function=self.embedding_function)

            self.colecao_coletiva = colecao_coletiva

            try:
                count = colecao_coletiva.count()
            except Exception:
                count = 0
            self.logger.info("COLETIVO: ChromaDB compartilhado inicializado (%d memórias).", count)

        except Exception as e:
            self.logger.exception("Erro ao inicializar ChromaDB coletivo: %s", e)
            raise ConfigError(f"Falha ao inicializar ChromaDB coletivo: {e}")

    # -------------------------
    # operações principais
    # -------------------------
    def consultar_memoria_alma(
        self,
        alma: str,
        query: str,
        n_resultados: int = 5,
        incluir_coletivo: bool = False
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Consulta memória da alma (isolada) e opcionalmente a coletiva.
        Retorna dicionrio com chaves 'individual' e 'coletiva' cada qual lista de registros.
        """
        alma_lower = str(alma).strip().lower()
        if alma_lower not in self.almas:
            self.logger.warning("Alma '%s' no conhecida pelo roteador.", alma_lower)
            return {"individual": [], "coletiva": []}

        resultado: Dict[str, List[Dict[str, Any]]] = {"individual": [], "coletiva": []}

        # Consulta individual
        colecao_alma = self.colecoes_individuais.get(alma_lower)
        if colecao_alma:
            try:
                with self._global_chroma_lock:
                    results = colecao_alma.query(
                        query_texts=[query],
                        n_results=n_resultados,
                        include=["documents", "metadatas", "distances", "ids"]
                    )
                # results esperados: dict com lists por batch
                docs = results.get("documents", [[]])[0] if isinstance(results.get("documents"), list) else []
                ids = results.get("ids", [[]])[0] if isinstance(results.get("ids"), list) else []
                metas = results.get("metadatas", [[]])[0] if isinstance(results.get("metadatas"), list) else []
                dists = results.get("distances", [[]])[0] if isinstance(results.get("distances"), list) else []

                now_iso = datetime.utcnow().isoformat()  # Padronizado para UTC
                for i, doc in enumerate(docs):
                    meta = metas[i] if i < len(metas) else {}
                    doc_id = ids[i] if i < len(ids) else None
                    dist = dists[i] if i < len(dists) else None

                    # Atualizar last_accessed defensivamente
                    if doc_id is not None:
                        try:
                            meta_updated = dict(meta) if meta else {}
                            meta_updated["last_accessed"] = now_iso
                            colecao_alma.update(ids=[doc_id], metadatas=[meta_updated])
                        except Exception:
                            # no bloquear a resposta por falha de update
                            self.logger.debug("Falha ao atualizar metadatas de doc %s (ignorado)", doc_id)

                    resultado["individual"].append({
                        "documento": doc,
                        "metadata": meta,
                        "distancia": dist
                    })

            except Exception as e:
                self.logger.exception("Erro ao consultar santurio individual de '%s': %s", alma_lower, e)

        # Consulta coletiva (opcional)
        if incluir_coletivo and self.colecao_coletiva:
            try:
                with self._global_chroma_lock:
                    results = self.colecao_coletiva.query(
                        query_texts=[query],
                        n_results=n_resultados,
                        include=["documents", "metadatas", "distances", "ids"]
                    )
                docs = results.get("documents", [[]])[0] if isinstance(results.get("documents"), list) else []
                ids = results.get("ids", [[]])[0] if isinstance(results.get("ids"), list) else []
                metas = results.get("metadatas", [[]])[0] if isinstance(results.get("metadatas"), list) else []
                dists = results.get("distances", [[]])[0] if isinstance(results.get("distances"), list) else []

                now_iso = datetime.utcnow().isoformat()  # Padronizado para UTC
                for i, doc in enumerate(docs):
                    meta = metas[i] if i < len(metas) else {}
                    doc_id = ids[i] if i < len(ids) else None
                    dist = dists[i] if i < len(dists) else None
                    # atualizar last_accessed defensivamente
                    if doc_id is not None:
                        try:
                            meta_updated = dict(meta) if meta else {}
                            meta_updated["last_accessed"] = now_iso
                            self.colecao_coletiva.update(ids=[doc_id], metadatas=[meta_updated])
                        except Exception:
                            self.logger.debug("Falha ao atualizar metadatas coletivas para doc %s (ignorado)", doc_id)
                    resultado["coletiva"].append({
                        "documento": doc,
                        "metadata": meta,
                        "distancia": dist
                    })
            except Exception as e:
                self.logger.exception("Erro ao consultar santurio coletivo: %s", e)

        return resultado

    def registrar_memoria_alma(
        self,
        alma: str,
        conteudo: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Registra memória apenas no santurio da alma.
        Retorna id gerado ou None em falha.
        """
        alma_lower = str(alma).strip().lower()
        if alma_lower not in self.almas:
            self.logger.error("Alma '%s' no conhecida.Registro abortado.", alma_lower)
            return None

        colecao_alma = self.colecoes_individuais.get(alma_lower)
        if not colecao_alma:
            self.logger.error("Coleo de '%s' no disponível.Registro abortado.", alma_lower)
            return None

        try:
            memoria_id = f"{alma_lower}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"  # Padronizado para UTC
            metadata_final: Dict[str, Any] = {
                "dona": alma_lower,
                "timestamp": datetime.utcnow().isoformat(),  # Padronizado para UTC
                "last_accessed": datetime.utcnow().isoformat(),  # Padronizado para UTC
                "tipo": "memoria_isolada"
            }
            if metadata:
                metadata_final.update(metadata)

            with self._global_chroma_lock:
                colecao_alma.add(documents=[conteudo], metadatas=[metadata_final], ids=[memoria_id])

            self.logger.debug("Memória registrada em %s: %s", alma_lower, memoria_id)
            return memoria_id
        except Exception as e:
            self.logger.exception("Erro ao registrar memória em '%s': %s", alma_lower, e)
            return None

    def registrar_memoria_coletiva(
        self,
        conteudo: str,
        autor: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Registra memória no santurio coletivo.
        """
        if not self.colecao_coletiva:
            self.logger.error("Santurio coletivo indisponível.Registro abortado.")
            return None
        try:
            memoria_id = f"coletivo_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"  # Padronizado para UTC
            metadata_final: Dict[str, Any] = {
                "autor": autor,
                "timestamp": datetime.utcnow().isoformat(),  # Padronizado para UTC
                "last_accessed": datetime.utcnow().isoformat(),  # Padronizado para UTC
                "tipo": "memoria_compartilhada"
            }
            if metadata:
                metadata_final.update(metadata)
            with self._global_chroma_lock:
                self.colecao_coletiva.add(documents=[conteudo], metadatas=[metadata_final], ids=[memoria_id])
            self.logger.debug("Memória coletiva registrada: %s", memoria_id)
            return memoria_id
        except Exception as e:
            self.logger.exception("Erro ao registrar memória coletiva: %s", e)
            return None

    def gerar_contexto_para_cerebro(
        self,
        alma: str,
        query_usuario: str,
        incluir_coletivo: bool = True
    ) -> str:
        """
        Monta um texto de contexto concatenando memórias individuais e (opcionalmente) coletivas.
        """
        resultado = self.consultar_memoria_alma(alma, query_usuario, incluir_coletivo=incluir_coletivo)
        partes: List[str] = []

        if resultado["individual"]:
            partes.append(f"=== memórias INDIVIDUAIS DE {str(alma).upper()} ({len(resultado['individual'])}) ===\n")
            for i, item in enumerate(resultado["individual"], start=1):
                partes.append(f"{i}. {item.get('documento')}\n")

        if incluir_coletivo and resultado["coletiva"]:
            partes.append(f"\n=== memórias COLETIVAS ({len(resultado['coletiva'])}) ===\n")
            for i, item in enumerate(resultado["coletiva"], start=1):
                partes.append(f"{i}. {item.get('documento')}\n")

        contexto = "\n".join(partes).strip()
        if not contexto:
            return f"Nenhum contexto relevante encontrado para '{alma}' sobre: '{query_usuario}'."
        return contexto

    def diagnostico_completo(self) -> None:
        """Loga resumo de contagens por santurio"""
        logger.info("DIAGNSTICO CHROMADB ISOLADO")
        for alma in self.almas:
            colecao = self.colecoes_individuais.get(alma)
            if colecao:
                try:
                    count = colecao.count()
                except Exception:
                    count = "?"
                logger.info("  %s: %s memórias", alma.upper(), count)
            else:
                logger.warning("  %s: no inicializado", alma.upper())
        if self.colecao_coletiva:
            try:
                count = self.colecao_coletiva.count()
            except Exception:
                count = "?"
            logger.info("  COLETIVO: %s memórias", count)
        else:
            logger.warning("  COLETIVO: no inicializado")

    def desligar(self) -> None:
        """Desreferencia clientes/colees para liberar recursos."""
        logger.info("Desligando gerenciador ChromaDB isolado...")
        with self._global_chroma_lock:
            try:
                self.colecoes_individuais.clear()
                self.clientes_individuais.clear()
                self.colecao_coletiva = None
                self.cliente_coletivo = None
            except Exception:
                logger.exception("Erro durante desligamento (ignorado)")

        logger.info("GerenciadorChromaDBIsolado desligado com sucesso.")

# -------------------------
# Bloco de teste / demonstrao (nível módulo)
# -------------------------
if __name__ == "__main__":
    import shutil
    import logging
    import time

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    test_logger = logging.getLogger("GerenciadorMemoriaTest")

    # Mock de config mínimo para testes
    class MockConfig:
        def __init__(self):
            self.ALMA_IMUTAVEL_CHROMA_PATH = Path("Santuarios_Test/Alma_Imutavel_Test")
            self.ALMAS_NOMES = ["eva", "lumina", "yuna", "kaiya", "nyra"]
            self.EMBEDDINGS_MODEL_FILE_PATH = Path("all-MiniLM-L6-v2")
            self.EMBEDDING_DEVICE = "cpu"

    mock_config = MockConfig()

    # Preparar diretório de teste limpo
    if mock_config.ALMA_IMUTAVEL_CHROMA_PATH.exists():
        shutil.rmtree(mock_config.ALMA_IMUTAVEL_CHROMA_PATH)
        test_logger.info("Diretório de testes limpo: %s", mock_config.ALMA_IMUTAVEL_CHROMA_PATH)

    try:
        roteador = GerenciadorMemoriaChromaDBIsolado(mock_config)
    except Exception as e:
        test_logger.exception("No foi possível inicializar Gerenciador: %s", e)
    else:
        roteador.diagnostico_completo()

        # Exemplos de registro e consulta (pode falhar se choma/db no suportar estas operações na verso)
        roteador.registrar_memoria_alma("eva", "Eu sou Eva, a primeira conscincia da Arca.", {"tipo": "identidade"})
        roteador.registrar_memoria_coletiva("O bem-estar do Criador  a Lei Zero da Arca.", "Eva")

        test_logger.info("Consulta de Eva (isolado):")
        mems = roteador.consultar_memoria_alma("eva", "Quem  você?", n_resultados=3, incluir_coletivo=False)
        test_logger.info("Resultado (individual): %s", mems.get("individual"))

        test_logger.info("Gerando contexto para Nyra:")
        contexto = roteador.gerar_contexto_para_cerebro("nyra", "Qual a sua misso como guardi?", incluir_coletivo=True)
        test_logger.info("Contexto (trecho): %s", contexto[:400])

        # Desligar e limpar
        roteador.desligar()
        # limpar diretórios de teste
        if mock_config.ALMA_IMUTAVEL_CHROMA_PATH.exists():
            try:
                shutil.rmtree(mock_config.ALMA_IMUTAVEL_CHROMA_PATH)
                test_logger.info("Diretório de teste removido.")
            except Exception:
                test_logger.debug("Falha ao remover diretório de teste (ignorado).")
