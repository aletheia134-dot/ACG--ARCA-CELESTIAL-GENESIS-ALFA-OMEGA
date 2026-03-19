"""
SERVIDOR GPU_LLM - LLMs com GPU isolada para GTX 1070 (Pascal 6.1)
Roda no ambiente gpu_llm (porta 5005)
NÃO USA llama-cpp-python na inicialização (lazy loading)
"""

import os
import sys
import logging
import signal
import gc
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

# Garantir que o cwd é a raiz do projeto
_ROOT = Path(__file__).parent.parent.parent
os.chdir(str(_ROOT))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# ============================================================================
# HANDLER DE SINAIS
# ============================================================================

def handle_shutdown(signum, frame):
    logging.getLogger("gpu_llm_server").info(f"\n🛑 Recebido sinal {signum}. Desligando servidor gpu_llm...")
    # Limpar memória GPU
    try:
        import torch
        torch.cuda.empty_cache()
    except:
        pass
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
        logging.FileHandler(f"Logs/gpu_llm_{datetime.now().strftime('%Y%m%d')}.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("gpu_llm_server")

# ============================================================================
# ESTADO GLOBAL (lazy loading)
# ============================================================================

_llm_engine = None          # Instância do ParallelLLMEngine (carregado lazy)
_torch_available = False
_cuda_available = False
_gpu_name = "Desconhecida"
_vram_total = 0

# Verificar PyTorch na inicialização (seguro)
try:
    import torch
    _torch_available = True
    _cuda_available = torch.cuda.is_available()
    if _cuda_available:
        _gpu_name = torch.cuda.get_device_name(0)
        _vram_total = torch.cuda.get_device_properties(0).total_memory / 1e9
        logger.info(f"🎮 GPU detectada: {_gpu_name} com {_vram_total:.2f}GB VRAM")
    else:
        logger.warning("⚠️ CUDA não disponível - GPU_LLM rodará em CPU")
except ImportError as e:
    logger.warning(f"⚠️ PyTorch não disponível: {e}")

# ParallelLLMEngine: NÃO instanciar aqui — lazy init
logger.info("⏳ ParallelLLMEngine: lazy — será carregado na primeira requisição /inferir")

def _get_llm_engine():
    """Retorna ParallelLLMEngine, instanciando na primeira chamada (lazy)."""
    global _llm_engine
    if _llm_engine is not None:
        return _llm_engine
    
    try:
        # Configuração específica para GTX 1070
        config = {
            'N_GPU_LAYERS': -2,           # Auto-detect
            'N_CTX': 2048,                 # Contexto reduzido para caber na VRAM
            'GPU_MONITORING_ENABLED': 'true'
        }
        
        # Importar apenas aqui (lazy)
        from src.core.parallel_llm_engine import ParallelLLMEngine
        
        _llm_engine = ParallelLLMEngine(config)
        logger.info("✅ ParallelLLMEngine instanciado")
        
        # Carregar modelos (serial, um por um)
        logger.info("⏳ Carregando modelos (serial)...")
        sucesso = _llm_engine.carregar_modelos()
        
        if sucesso:
            logger.info("✅ Todos os 6 modelos carregados com sucesso")
        else:
            logger.warning(f"⚠️ Apenas {_llm_engine.get_status()['modelos_carregados']}/6 modelos carregados")
        
        # Mostrar status da GPU
        if _torch_available and _cuda_available:
            import torch
            vram = torch.cuda.memory_allocated(0) / 1e9
            logger.info(f"📊 VRAM usada após carga: {vram:.2f}GB")
        
        return _llm_engine
    except Exception as e:
        logger.error(f"❌ Erro ao carregar ParallelLLMEngine: {e}")
        _llm_engine = None
        return None


app = FastAPI(title="Arca GPU LLM Server", version="1.0")


class InferenciaRequest(BaseModel):
    alma: str
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.7
    use_gpu: bool = True


class ModeloInfo(BaseModel):
    nome: str
    caminho: str
    tamanho_mb: float
    carregado: bool = False


@app.get("/")
async def root():
    return {
        "servidor": "GPU_LLM",
        "status": "ativo",
        "porta": 5005,
        "gpu": {
            "disponivel": _cuda_available,
            "nome": _gpu_name,
            "vram_gb": round(_vram_total, 2) if _vram_total else 0
        },
        "modelos_carregados": _llm_engine.get_status()['modelos_carregados'] if _llm_engine else 0,
        "parallel_llm_carregado": _llm_engine is not None
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "gpu": _cuda_available,
        "gpu_nome": _gpu_name
    }


@app.get("/status")
async def status():
    """Status detalhado do servidor GPU"""
    engine = _get_llm_engine()
    status_info = {
        "servidor": "gpu_llm",
        "porta": 5005,
        "gpu": {
            "disponivel": _cuda_available,
            "nome": _gpu_name,
            "vram_gb": round(_vram_total, 2) if _vram_total else 0
        },
        "parallel_llm": engine.get_status() if engine else None,
        "memoria": {}
    }
    
    if _torch_available and _cuda_available:
        import torch
        status_info["memoria"] = {
            "alocada_gb": round(torch.cuda.memory_allocated(0) / 1e9, 2),
            "reservada_gb": round(torch.cuda.memory_reserved(0) / 1e9, 2),
            "cached_gb": round(torch.cuda.memory_cached(0) / 1e9, 2) if hasattr(torch.cuda, 'memory_cached') else 0
        }
    
    return status_info


@app.post("/inferir")
async def inferir(req: InferenciaRequest):
    """Gera resposta usando o LLM na GPU"""
    logger.info(f"⚡ Inferência solicitada para {req.alma}: {req.prompt[:50]}...")
    
    engine = _get_llm_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail={
            "erro": "ParallelLLMEngine não disponível",
            "solucao": "Verifique logs do servidor gpu_llm"
        })
    
    # Verificar se a alma está carregada
    status_engine = engine.get_status()
    if req.alma.upper() not in [a.upper() for a in status_engine['status_detalhado'].keys()]:
        raise HTTPException(status_code=404, detail=f"Alma {req.alma} não reconhecida")
    
    if status_engine['status_detalhado'].get(req.alma.upper(), 'erro') != 'carregado':
        raise HTTPException(status_code=503, detail=f"Modelo {req.alma} não carregado")
    
    try:
        # Preparar request
        request = {
            'ai_id': req.alma.upper(),
            'prompt': req.prompt,
            'max_tokens': req.max_tokens,
            'temperature': req.temperature
        }
        
        # Gerar resposta
        resposta = engine.generate_response(request)
        
        # Log de VRAM após inferência
        if _torch_available and _cuda_available:
            import torch
            vram = torch.cuda.memory_allocated(0) / 1e9
            logger.info(f"📊 VRAM após inferência: {vram:.2f}GB")
        
        return {
            "status": "ok",
            "alma": req.alma,
            "resposta": resposta,
            "tokens_gerados": req.max_tokens,
            "gpu_usada": _cuda_available
        }
    except Exception as e:
        logger.exception(f"❌ Erro na inferência: {e}")
        raise HTTPException(status_code=500, detail={"erro": str(e)})


@app.post("/carregar")
async def carregar_modelos():
    """Força o carregamento dos modelos (útil para pré-aquecer)"""
    logger.info("⏳ Carregando modelos sob demanda...")
    engine = _get_llm_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="Falha ao carregar engine")
    
    status = engine.get_status()
    return {
        "status": "ok",
        "modelos_carregados": status['modelos_carregados'],
        "total_modelos": status['total_modelos']
    }


@app.get("/modelos")
async def listar_modelos():
    """Lista modelos disponíveis e seus status"""
    engine = _get_llm_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine não disponível")
    
    status = engine.get_status()
    modelos = []
    
    for nome, estado in status['status_detalhado'].items():
        modelos.append({
            "alma": nome,
            "status": estado,
            "prioridade": status.get('gpu_manager', {}).get('models', {}).get(nome, {}).get('priority', 'N/A'),
            "device": status.get('gpu_manager', {}).get('models', {}).get(nome, {}).get('device', 'N/A')
        })
    
    return {
        "total": len(modelos),
        "carregados": status['modelos_carregados'],
        "modelos": modelos
    }


@app.post("/limpar")
async def limpar_cache():
    """Limpa cache da GPU"""
    logger.info("🧹 Limpando cache GPU...")
    if _torch_available and _cuda_available:
        import torch
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        vram = torch.cuda.memory_allocated(0) / 1e9
        logger.info(f"✅ Cache limpo. VRAM: {vram:.2f}GB")
        return {"status": "ok", "vram_gb": vram}
    return {"status": "ok", "mensagem": "CUDA não disponível"}


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🚀 INICIANDO SERVIDOR GPU_LLM (PORTA 5005)")
    logger.info("=" * 60)
    logger.info(f"🎮 GPU Detectada: {_gpu_name} ({_vram_total:.2f}GB)")
    logger.info("⏳ Modelos carregados sob demanda (lazy loading)")
    logger.info("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=5005, workers=1, loop="asyncio", timeout_keep_alive=60)