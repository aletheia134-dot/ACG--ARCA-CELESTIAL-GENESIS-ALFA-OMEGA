"""
SERVIDOR EMBEDDINGS - Transforma texto em vetores
Roda no ambiente embeddings (porta 5004)
OTIMIZADO PARA CPU (preserva VRAM para o LLM)
"""

import os
import sys
import logging
import signal
import gc
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Desabilitar telemetria ChromaDB ANTES de qualquer import do chromadb
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")
os.environ.setdefault("CHROMA_TELEMETRY", "false")

# Garantir que o cwd é a raiz do projeto
_ROOT = Path(__file__).parent.parent.parent
os.chdir(str(_ROOT))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

try:
    import numpy as np
    NUMPY_DISPONIVEL = True
except ImportError:
    np = None
    NUMPY_DISPONIVEL = False
    logging.warning("⚠️ numpy não instalado no venv embeddings — instale com: pip install numpy")

# ============================================================================
# HANDLER DE SINAIS
# ============================================================================

def handle_shutdown(signum, frame):
    logging.info(f"\n🛑 Recebido sinal {signum}. Desligando servidor embeddings...")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)
if sys.platform == 'win32':
    signal.signal(signal.SIGBREAK, handle_shutdown)

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

os.makedirs("Logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"Logs/embeddings_{datetime.now().strftime('%Y%m%d')}.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("embeddings_server")

# ============================================================================
# MODELO (lazy loading)
# ============================================================================

_modelo = None
_chromadb = None

def _get_modelo():
    """Carrega modelo de embeddings sob demanda (lazy)"""
    global _modelo
    if _modelo is not None:
        return _modelo
    
    try:
        from sentence_transformers import SentenceTransformer
        logger.info("🔄 Carregando modelo de embeddings (pode levar alguns segundos)...")
        
        # Forçar CPU para preservar VRAM
        import torch
        torch.cuda.empty_cache()
        
        _modelo = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device='cpu')
        logger.info("✅ Modelo de embeddings carregado (CPU mode)")
        return _modelo
    except Exception as e:
        logger.error(f"❌ Erro ao carregar modelo: {e}")
        return None


def _get_chromadb():
    """Inicializa ChromaDB sob demanda"""
    global _chromadb
    if _chromadb is not None:
        return _chromadb

    try:
        import chromadb
        from chromadb.config import Settings

        persist_dir = "data/chroma_db"
        os.makedirs(persist_dir, exist_ok=True)

        # API atual do chromadb >= 0.4.x  (PersistentClient)
        try:
            _chromadb = chromadb.PersistentClient(
                path=persist_dir,
                settings=Settings(anonymized_telemetry=False, allow_reset=False)
            )
        except Exception:
            # Fallback para versões mais antigas
            _chromadb = chromadb.Client()

        logger.info("✅ ChromaDB inicializado")
        return _chromadb
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar ChromaDB: {e}")
        return None


class TextoRequest(BaseModel):
    textos: List[str]


class ColecaoRequest(BaseModel):
    nome: str


class AdicionarRequest(BaseModel):
    colecao: str
    documentos: List[str]
    ids: Optional[List[str]] = None
    metadados: Optional[List[dict]] = None


app = FastAPI(title="Arca Embeddings Server", version="2.0")


@app.get("/")
async def root():
    return {
        "servidor": "Embeddings",
        "status": "ativo",
        "porta": 5004,
        "modo": "CPU (preserva VRAM para LLM)",
        "modelo": "paraphrase-multilingual-MiniLM-L12-v2"
    }


@app.get("/health")
async def health():
    return {"status": "ok", "modo": "cpu"}


@app.post("/embed")
async def embed(req: TextoRequest):
    """Gera embeddings para lista de textos"""
    logger.info(f"📊 Gerando embeddings para {len(req.textos)} texto(s)")
    
    modelo = _get_modelo()
    if modelo is None:
        raise HTTPException(status_code=503, detail="Modelo de embeddings não disponível")
    
    try:
        # Gerar embeddings (em CPU)
        embeddings = modelo.encode(req.textos).tolist()
        
        logger.info(f"✅ Embeddings gerados: {len(embeddings)} vetores de tamanho {len(embeddings[0]) if embeddings else 0}")
        
        return {
            "embeddings": embeddings,
            "dimensao": len(embeddings[0]) if embeddings else 0,
            "quantidade": len(embeddings)
        }
    except Exception as e:
        logger.error(f"❌ Erro ao gerar embeddings: {e}")
        raise HTTPException(status_code=500, detail={"erro": str(e)})


@app.post("/colecao/criar")
async def criar_colecao(req: ColecaoRequest):
    """Cria uma coleção no ChromaDB"""
    logger.info(f"📁 Criando coleção: {req.nome}")
    
    client = _get_chromadb()
    if client is None:
        raise HTTPException(status_code=503, detail="ChromaDB não disponível")
    
    try:
        colecao = client.create_collection(name=req.nome)
        return {
            "status": "ok",
            "nome": req.nome,
            "mensagem": f"Coleção '{req.nome}' criada"
        }
    except Exception as e:
        if "already exists" in str(e).lower():
            return {
                "status": "ok",
                "nome": req.nome,
                "mensagem": "Coleção já existe"
            }
        logger.error(f"❌ Erro ao criar coleção: {e}")
        raise HTTPException(status_code=500, detail={"erro": str(e)})


@app.post("/colecao/adicionar")
async def adicionar_documentos(req: AdicionarRequest):
    """Adiciona documentos a uma coleção"""
    logger.info(f"📝 Adicionando {len(req.documentos)} documentos à coleção '{req.colecao}'")
    
    client = _get_chromadb()
    if client is None:
        raise HTTPException(status_code=503, detail="ChromaDB não disponível")
    
    try:
        colecao = client.get_collection(name=req.colecao)
        
        # Gerar embeddings automaticamente
        modelo = _get_modelo()
        if modelo is None:
            raise HTTPException(status_code=503, detail="Modelo de embeddings não disponível")
        
        embeddings = modelo.encode(req.documentos).tolist()
        
        # Gerar IDs se não fornecidos
        ids = req.ids
        if ids is None:
            ids = [f"doc_{i}_{datetime.now().timestamp()}" for i in range(len(req.documentos))]
        
        colecao.add(
            documents=req.documentos,
            embeddings=embeddings,
            ids=ids,
            metadatas=req.metadados
        )
        
        return {
            "status": "ok",
            "colecao": req.colecao,
            "documentos_adicionados": len(req.documentos),
            "ids": ids
        }
    except Exception as e:
        logger.error(f"❌ Erro ao adicionar documentos: {e}")
        raise HTTPException(status_code=500, detail={"erro": str(e)})


@app.post("/colecao/buscar")
async def buscar_similares(
    colecao: str,
    query: str,
    n_resultados: int = 5
):
    """Busca documentos similares por texto"""
    logger.info(f"🔍 Buscando '{query}' em '{colecao}'")
    
    client = _get_chromadb()
    if client is None:
        raise HTTPException(status_code=503, detail="ChromaDB não disponível")
    
    try:
        colecao_obj = client.get_collection(name=colecao)
        
        # Gerar embedding da query
        modelo = _get_modelo()
        if modelo is None:
            raise HTTPException(status_code=503, detail="Modelo de embeddings não disponível")
        
        query_embedding = modelo.encode([query]).tolist()[0]
        
        # Buscar
        resultados = colecao_obj.query(
            query_embeddings=[query_embedding],
            n_results=n_resultados
        )
        
        return {
            "query": query,
            "resultados": [
                {
                    "documento": resultados['documents'][0][i] if resultados['documents'] else None,
                    "id": resultados['ids'][0][i],
                    "distancia": float(resultados['distances'][0][i]) if resultados.get('distances') else None,
                    "metadados": resultados['metadatas'][0][i] if resultados.get('metadatas') else None
                }
                for i in range(len(resultados['ids'][0]))
            ]
        }
    except Exception as e:
        logger.error(f"❌ Erro na busca: {e}")
        raise HTTPException(status_code=500, detail={"erro": str(e)})


@app.get("/status")
async def status():
    """Status do servidor"""
    client = _get_chromadb()
    colecoes = []
    if client:
        try:
            colecoes = [c.name for c in client.list_collections()]
        except:
            pass
    
    return {
        "servidor": "embeddings",
        "porta": 5004,
        "modelo_carregado": _modelo is not None,
        "chromadb": client is not None,
        "colecoes": colecoes,
        "modo": "cpu",
        "timestamp": datetime.now().isoformat()
    }


@app.on_event("shutdown")
async def shutdown():
    """Limpeza ao desligar"""
    logger.info("🧹 Finalizando servidor embeddings...")
    global _modelo
    _modelo = None
    gc.collect()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("📊 SERVIDOR EMBEDDINGS - Porta 5004")
    logger.info("   Modo CPU (preserva VRAM para LLM)")
    logger.info("   Modelo: paraphrase-multilingual-MiniLM-L12-v2")
    logger.info("=" * 60)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5004,
        log_level="info",
        workers=1,
        loop="asyncio",
        timeout_keep_alive=30,
    )