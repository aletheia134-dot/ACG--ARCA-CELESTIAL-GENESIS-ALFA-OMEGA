"""
SERVIDOR FINETUNING - LLM local, treinamento, GGUF
Roda no ambiente FINETUNING (porta 5002)
"""

import os
import sys
import logging
import signal
import gc
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

# Garantir que o cwd é a raiz do projeto
_ROOT = Path(__file__).parent.parent.parent
os.chdir(str(_ROOT))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn

# ============================================================================
# HANDLER DE SINAIS
# ============================================================================

def handle_shutdown(signum, frame):
    logging.getLogger("finetuning_server").info(f"\n🛑 Recebido sinal {signum}. Desligando servidor finetuning...")
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
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"Logs/finetuning_{datetime.now().strftime('%Y%m%d')}.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("finetuning_server")

# ============================================================================
# ORQUESTRADORES (lazy loading)
# ============================================================================

_orquestrador_arca = None
_orq_conversor = None
_llm_client = None  # <--- MODIFICADO: antes era _parallel_llm, agora _llm_client
_treinos_ativos: Dict[str, Dict[str, Any]] = {}

# Tentar importar Orquestradores (seguros - não importam llama_cpp)
try:
    from src.core.orquestrador_arca import OrquestradorArca
    _orquestrador_arca = OrquestradorArca()
    logger.info("✅ OrquestradorArca carregado")
except Exception as e:
    logger.warning(f"⚠️ OrquestradorArca não disponível: {e}")

try:
    from src.finetuning.orquestrador_com_conversor import OrquestradorComConversor
    _orq_conversor = OrquestradorComConversor()
    logger.info("✅ OrquestradorComConversor carregado")
except Exception as e:
    logger.warning(f"⚠️ OrquestradorComConversor não disponível: {e}")

# ===== MODIFICADO: Agora usa LlamaExeClient em vez de ParallelLLMEngine =====
def _get_llm_client():
    """Retorna LlamaExeClient, instanciando na primeira chamada (lazy)."""
    global _llm_client
    if _llm_client is not None:
        return _llm_client
    try:
        from src.core.llama_exe_client import LlamaExeClient
        _llm_client = LlamaExeClient()
        logger.info("✅ LlamaExeClient carregado (lazy)")
    except Exception as e:
        logger.warning(f"⚠️ LlamaExeClient não disponível: {e}")
        _llm_client = None
    return _llm_client
# ============================================================================

logger.info("⏳ Inferência delegada para LlamaExeClient (executável direto)")


class TreinoRequest(BaseModel):
    alma: str
    dataset_path: str
    epochs: int = 3
    batch_size: int = 4
    learning_rate: float = 2e-4


class InferenciaRequest(BaseModel):
    alma: str
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.7


class StatusRequest(BaseModel):
    job_id: str


app = FastAPI(title="Arca Finetuning Server", version="2.0")


@app.get("/")
async def root():
    return {
        "servidor": "Finetuning",
        "status": "ativo",
        "porta": 5002,
        "orquestrador_arca": _orquestrador_arca is not None,
        "orq_conversor": _orq_conversor is not None,
        "llm_client_disponivel": _get_llm_client() is not None
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/status")
async def status():
    """Status do servidor"""
    return {
        "servidor": "finetuning",
        "porta": 5002,
        "modulos": {
            "orquestrador_arca": _orquestrador_arca is not None,
            "orq_conversor": _orq_conversor is not None,
            "llm_client": _get_llm_client() is not None
        },
        "treinos_ativos": len(_treinos_ativos),
        "timestamp": datetime.now().isoformat()
    }


def _executar_treino_background(req: TreinoRequest):
    """Executa treinamento real em background"""
    import uuid
    job_id = str(uuid.uuid4())[:8]
    
    _treinos_ativos[job_id] = {
        "alma": req.alma,
        "status": "executando",
        "inicio": datetime.now().isoformat(),
        "dataset": req.dataset_path,
        "epochs": req.epochs
    }
    
    try:
        if _orquestrador_arca is not None:
            logger.info(f"🚀 Iniciando treino {job_id} para {req.alma} via OrquestradorArca")
            
            resultado = _orquestrador_arca.treinar_ia(
                nome_alma=req.alma,
                dataset_path=req.dataset_path,
                epochs=req.epochs,
                batch_size=req.batch_size,
                learning_rate=req.learning_rate
            )
            
            _treinos_ativos[job_id]["status"] = resultado.get("status", "concluido")
            _treinos_ativos[job_id]["resultado"] = str(resultado)
            _treinos_ativos[job_id]["fim"] = datetime.now().isoformat()
            
            logger.info(f"✅ Treino {job_id} concluído")
            return
            
        elif _orq_conversor is not None:
            logger.info(f"🚀 Iniciando treino {job_id} para {req.alma} via OrquestradorComConversor")
            
            resultado = _orq_conversor.treinar_ia(
                nome_alma=req.alma,
                dataset_path=req.dataset_path,
                epochs=req.epochs
            )
            
            _treinos_ativos[job_id]["status"] = resultado.get("status", "concluido")
            _treinos_ativos[job_id]["resultado"] = str(resultado)
            _treinos_ativos[job_id]["fim"] = datetime.now().isoformat()
            
            logger.info(f"✅ Treino {job_id} concluído")
            return
            
        else:
            _treinos_ativos[job_id]["status"] = "erro"
            _treinos_ativos[job_id]["erro"] = "Nenhum orquestrador disponível"
            logger.error(f"❌ Treino {job_id} falhou: nenhum orquestrador")
            
    except Exception as e:
        _treinos_ativos[job_id]["status"] = "erro"
        _treinos_ativos[job_id]["erro"] = str(e)
        _treinos_ativos[job_id]["fim"] = datetime.now().isoformat()
        logger.exception(f"❌ Erro no treino {job_id}: {e}")


@app.post("/treinar")
async def treinar(req: TreinoRequest, background_tasks: BackgroundTasks):
    """Inicia treinamento em background"""
    logger.info(f"🎓 Treinamento solicitado para {req.alma}: {req.dataset_path}")

    # Verificar dataset
    dataset_path = Path(req.dataset_path)
    if not dataset_path.exists():
        raise HTTPException(status_code=404, detail={
            "erro": f"Dataset não encontrado: {req.dataset_path}",
            "solucao": "Verifique o caminho do dataset"
        })

    # Verificar orquestradores
    if _orquestrador_arca is None and _orq_conversor is None:
        raise HTTPException(status_code=503, detail={
            "erro": "Nenhum orquestrador de finetuning disponível",
            "disponivel": {
                "orquestrador_arca": _orquestrador_arca is not None,
                "orq_conversor": _orq_conversor is not None
            }
        })

    import uuid
    job_id = str(uuid.uuid4())[:8]
    
    _treinos_ativos[job_id] = {
        "alma": req.alma,
        "status": "enfileirado",
        "inicio": datetime.now().isoformat(),
        "dataset": req.dataset_path,
        "epochs": req.epochs
    }
    
    background_tasks.add_task(_executar_treino_background, req)

    return {
        "status": "iniciado",
        "job_id": job_id,
        "alma": req.alma,
        "dataset": req.dataset_path,
        "epochs": req.epochs,
        "mensagem": "Treinamento iniciado em background"
    }


@app.get("/treino/{job_id}")
async def status_treino(job_id: str):
    """Consultar status de um treino"""
    if job_id not in _treinos_ativos:
        raise HTTPException(status_code=404, detail=f"Job {job_id} não encontrado")
    return _treinos_ativos[job_id]


@app.get("/treinos")
async def listar_treinos():
    """Lista todos os treinos"""
    return {
        "total": len(_treinos_ativos),
        "treinos": _treinos_ativos
    }


@app.post("/inferir")
async def inferir(req: InferenciaRequest):
    """Gera inferência usando LlamaExeClient"""
    logger.info(f"⚡ Inferência solicitada para {req.alma}")
    
    cliente = _get_llm_client()
    if cliente is None:
        raise HTTPException(
            status_code=503,
            detail={
                "erro": "LlamaExeClient não disponível",
                "solucao": "Verifique se o executável existe em E:/Arca_Celestial_Genesis_Alfa_Omega/llama/llama-cli.exe"
            }
        )
    
    try:
        # Criar request no formato esperado pelo LlamaExeClient
        request = {
            'ai_id': req.alma,
            'prompt': req.prompt,
            'max_tokens': req.max_tokens,
            'temperature': req.temperature
        }
        
        resposta = cliente.generate_response(request)
        
        return {
            "status": "ok",
            "alma": req.alma,
            "resposta": resposta,
            "tokens_gerados": req.max_tokens
        }
    except Exception as e:
        logger.exception(f"Erro na inferência: {e}")
        raise HTTPException(status_code=500, detail={"erro": str(e)})


@app.get("/modelos")
async def listar_modelos():
    """Lista modelos GGUF disponíveis"""
    models_dir = Path("models")
    modelos = []
    
    if models_dir.exists():
        for f in models_dir.glob("**/*.gguf"):
            modelos.append({
                "nome": f.name,
                "caminho": str(f),
                "tamanho_mb": round(f.stat().st_size / 1024 / 1024, 1),
                "alma": f.stem.split('_')[0] if '_' in f.stem else f.stem
            })
    
    return {
        "total": len(modelos),
        "modelos": sorted(modelos, key=lambda x: x['alma'])
    }


@app.get("/gpu")
async def gpu_info():
    """Informações da GPU"""
    info = {"disponivel": False}
    try:
        import torch
        info["cuda"] = torch.cuda.is_available()
        if info["cuda"]:
            info["disponivel"] = True
            info["nome"] = torch.cuda.get_device_name(0)
            info["vram_gb"] = round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2)
    except:
        pass
    
    return info


@app.on_event("shutdown")
async def shutdown():
    """Limpeza ao desligar"""
    logger.info("🧹 Finalizando servidor finetuning...")
    global _treinos_ativos
    _treinos_ativos.clear()
    gc.collect()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🚀 INICIANDO SERVIDOR FINETUNING (PORTA 5002)")
    logger.info("=" * 60)
    logger.info(f"✅ OrquestradorArca: {_orquestrador_arca is not None}")
    logger.info(f"✅ OrquestradorConversor: {_orq_conversor is not None}")
    logger.info(f"⚡ Inferência usando LlamaExeClient (executável direto)")
    logger.info("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=5002, workers=1, loop="asyncio", timeout_keep_alive=30)