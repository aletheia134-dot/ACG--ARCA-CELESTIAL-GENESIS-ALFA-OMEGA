"""
SERVIDOR LLM - Fine-tuning, Inferncia, GPU
Roda no ambiente LLM (porta 5002)
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import torch
import logging
from datetime import datetime
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"scripts/logs/llm_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("llm_server")

app = FastAPI(title="Arca LLM Server")

class TreinoRequest(BaseModel):
    alma: str
    epochs: int = 3
    learning_rate: float = 2e-4

@app.get("/")
async def root():
    return {"servidor": "LLM", "status": "ativo"}

@app.get("/gpu")
async def gpu_info():
    """Informaes da GPU"""
    logger.info("Verificando GPU")
    try:
        if torch.cuda.is_available():
            return {
                "gpu_disponivel": True,
                "gpu_nome": torch.cuda.get_device_name(0),
                "vram_total": f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB",
                "vram_livre": f"{torch.cuda.memory_reserved(0) / 1e9:.2f} GB",
                "cuda_version": torch.version.cuda
            }
        else:
            return {"gpu_disponivel": False}
    except Exception as e:
        logger.error(f"Erro ao verificar GPU: {e}")
        return {"erro": str(e)}

@app.post("/treinar")
async def treinar(request: TreinoRequest):
    """Iniciar fine-tuning de uma alma"""
    logger.info(f"Requisio para treinar {request.alma}")
    
    # Aqui você vai chamar seus scripts de treinamento
    # Por enquanto, apenas simula
    
    return {
        "status": "iniciado",
        "alma": request.alma,
        "epochs": request.epochs,
        "gpu": torch.cuda.is_available()
    }

@app.get("/status")
async def status():
    """Status do servidor"""
    return {
        "servidor": "llm",
        "gpu": torch.cuda.is_available(),
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5002)