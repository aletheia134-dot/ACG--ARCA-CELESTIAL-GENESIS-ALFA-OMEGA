"""
SERVIDOR CORE - Orquestrador dos servidores da Arca
Roda na porta 5000
GERENCIA: media (5001), finetuning (5002), web (5003), embeddings (5004), gpu_llm (5005)
"""

import asyncio
import logging
import os
import subprocess
import sys
import signal
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import httpx

# ============================================================================
# HANDLER DE SINAIS
# ============================================================================

def handle_shutdown(signum, frame):
    logging.info(f"\n🛑 Recebido sinal {signum}. Desligando servidor core...")
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
        logging.FileHandler(f"Logs/core_{datetime.now().strftime('%Y%m%d')}.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("core_server")

app = FastAPI(title="Arca Core Server", version="2.0")

# CONFIGURAÇÃO DOS 5 SERVIDORES
SERVIDORES = {
    "media": {
        "porta": 5001,
        "venv": "media",
        "script": "servidor_media.py",
        "processo": None,
        "status": "parado",
        "descricao": "Câmera, áudio, TTS",
        "health_path": "/health"
    },
    "finetuning": {
        "porta": 5002,
        "venv": "finetuning",
        "script": "servidor_finetuning.py",
        "processo": None,
        "status": "parado",
        "descricao": "Treinamento, LoRA",
        "health_path": "/health"
    },
    "web": {
        "porta": 5003,
        "venv": "web",
        "script": "servidor_web.py",
        "processo": None,
        "status": "parado",
        "descricao": "Automação de navegador",
        "health_path": "/health"
    },
    "embeddings": {
        "porta": 5004,
        "venv": "embeddings",
        "script": "servidor_embeddings.py",
        "processo": None,
        "status": "parado",
        "descricao": "Embeddings com sentence-transformers",
        "health_path": "/health"
    },
    "gpu_llm": {
        "porta": 5005,
        "venv": "gpu_llm",
        "script": "servidor_gpu_llm.py",
        "processo": None,
        "status": "parado",
        "descricao": "🎮 LLMs com GPU (Pascal 6.1)",
        "health_path": "/health"
    }
}


class ComandoRequest(BaseModel):
    servidor: str  # "media", "finetuning", "web", "embeddings", "gpu_llm" ou "todos"
    acao: str      # "iniciar", "parar", "reiniciar", "status"


@app.get("/")
async def root():
    return {
        "servidor": "Core",
        "status": "ativo",
        "porta": 5000,
        "servidores_gerenciados": list(SERVIDORES.keys())
    }


@app.get("/status")
async def status():
    """Status de todos os servidores"""
    resultado = {}
    for nome, config in SERVIDORES.items():
        # Verifica processo
        if config["processo"]:
            if config["processo"].poll() is None:
                config["status"] = "rodando"
            else:
                config["status"] = "morreu"
                config["processo"] = None
        else:
            config["status"] = "parado"
        
        # Health check HTTP
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"http://localhost:{config['porta']}{config['health_path']}", timeout=2)
                config["status_http"] = "ok" if resp.status_code == 200 else f"http_{resp.status_code}"
        except Exception as e:
            config["status_http"] = f"offline ({str(e)[:30]})"
        
        resultado[nome] = {
            "porta": config["porta"],
            "status_processo": config["status"],
            "status_http": config.get("status_http", "desconhecido"),
            "venv": config["venv"],
            "descricao": config.get("descricao", "")
        }
    
    return {
        "timestamp": datetime.now().isoformat(),
        "servidores": resultado
    }


@app.get("/status/{nome}")
async def status_servidor(nome: str):
    """Status de um servidor específico"""
    if nome not in SERVIDORES:
        raise HTTPException(status_code=404, detail="Servidor não encontrado")
    
    config = SERVIDORES[nome]
    
    # Verifica processo
    if config["processo"]:
        if config["processo"].poll() is None:
            config["status"] = "rodando"
        else:
            config["status"] = "morreu"
            config["processo"] = None
    else:
        config["status"] = "parado"
    
    # Health check HTTP
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://localhost:{config['porta']}{config['health_path']}", timeout=2)
            config["status_http"] = "ok" if resp.status_code == 200 else f"http_{resp.status_code}"
    except Exception as e:
        config["status_http"] = f"offline ({str(e)[:30]})"
    
    return {
        "nome": nome,
        "porta": config["porta"],
        "status_processo": config["status"],
        "status_http": config.get("status_http", "desconhecido"),
        "venv": config["venv"],
        "descricao": config.get("descricao", ""),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/comando")
async def comando(req: ComandoRequest):
    """Envia comando para um servidor"""
    logger.info(f"Comando: {req.acao} para {req.servidor}")
    
    if req.servidor == "todos":
        servidores_alvo = SERVIDORES.items()
    elif req.servidor in SERVIDORES:
        servidores_alvo = [(req.servidor, SERVIDORES[req.servidor])]
    else:
        raise HTTPException(status_code=404, detail="Servidor não encontrado")
    
    resultados = {}
    for nome, config in servidores_alvo:
        if req.acao == "iniciar":
            resultados[nome] = await _iniciar_servidor(nome, config)
        elif req.acao == "parar":
            resultados[nome] = await _parar_servidor(nome, config)
        elif req.acao == "reiniciar":
            await _parar_servidor(nome, config)
            await asyncio.sleep(2)
            resultados[nome] = await _iniciar_servidor(nome, config)
        elif req.acao == "status":
            resultados[nome] = {"status": config["status"]}
        else:
            raise HTTPException(status_code=400, detail="Ação inválida")
    
    return {"resultados": resultados}


async def _iniciar_servidor(nome: str, config: Dict) -> Dict:
    """Inicia um servidor em seu venv"""
    if config["processo"] and config["processo"].poll() is None:
        return {"erro": "Servidor já está rodando", "status": "falha"}
    
    raiz = Path(__file__).parent.parent.parent  # sobe 3 níveis: src/servidores/ → raiz
    venv_python = raiz / "venvs" / config["venv"] / "Scripts" / "python.exe"
    
    if not venv_python.exists():
        return {"erro": f"Venv {config['venv']} não encontrado em {venv_python}", "status": "falha"}
    
    script_path = raiz / "src" / "servidores" / config["script"]
    if not script_path.exists():
        script_path = raiz / config["script"]
    
    if not script_path.exists():
        return {"erro": f"Script {config['script']} não encontrado", "status": "falha"}
    
    try:
        logger.info(f"🚀 Iniciando {nome} (venv: {config['venv']}, porta: {config['porta']})...")
        
        # Garantir que a porta está livre
        await _kill_process_on_port(config['porta'])
        
        processo = subprocess.Popen(
            [str(venv_python), str(script_path)],
            cwd=str(raiz),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        config["processo"] = processo
        config["status"] = "iniciando"
        
        logger.info(f"⏳ Aguardando servidor {nome} na porta {config['porta']}...")
        
        for i in range(30):
            await asyncio.sleep(1)
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"http://localhost:{config['porta']}{config['health_path']}", timeout=2)
                    if resp.status_code == 200:
                        config["status"] = "rodando"
                        logger.info(f"✅ Servidor {nome} iniciado na porta {config['porta']}")
                        return {"status": "ok", "porta": config["porta"]}
            except:
                continue
        
        config["status"] = "falha_inicio"
        logger.error(f"❌ Servidor {nome} não respondeu após 30 segundos")
        
        if processo and processo.poll() is None:
            processo.kill()
        
        return {"erro": "Servidor não respondeu", "status": "falha"}
        
    except Exception as e:
        config["status"] = "erro"
        logger.error(f"❌ Erro ao iniciar {nome}: {e}")
        return {"erro": str(e), "status": "falha"}


async def _parar_servidor(nome: str, config: Dict) -> Dict:
    """Para um servidor"""
    if not config["processo"]:
        return {"status": "já_parado"}
    
    try:
        logger.info(f"🛑 Parando servidor {nome}...")
        config["processo"].terminate()
        
        for _ in range(5):
            if config["processo"].poll() is not None:
                break
            await asyncio.sleep(1)
        
        if config["processo"].poll() is None:
            config["processo"].kill()
            await asyncio.sleep(1)
        
        config["processo"] = None
        config["status"] = "parado"
        logger.info(f"✅ Servidor {nome} parado")
        return {"status": "parado"}
    except Exception as e:
        logger.error(f"Erro ao parar {nome}: {e}")
        return {"erro": str(e), "status": "falha"}


async def _kill_process_on_port(porta: int):
    """Mata processo usando a porta (Windows)"""
    if sys.platform == 'win32':
        try:
            result = subprocess.run(
                f'netstat -ano | findstr :{porta}',
                shell=True, capture_output=True, text=True
            )
            for line in result.stdout.split('\n'):
                if f':{porta}' in line and 'LISTENING' in line:
                    parts = line.strip().split()
                    if parts:
                        pid = parts[-1]
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                        logger.info(f"✅ Processo na porta {porta} (PID {pid}) morto")
        except:
            pass


@app.post("/reiniciar-todos")
async def reiniciar_todos():
    """Reinicia todos os servidores"""
    logger.info("🔄 Reiniciando todos os servidores...")
    
    resultados = {}
    for nome, config in SERVIDORES.items():
        await _parar_servidor(nome, config)
        await asyncio.sleep(1)
        resultados[nome] = await _iniciar_servidor(nome, config)
    
    return {"resultados": resultados}


@app.get("/health")
async def health():
    return {"status": "ok", "servidor": "core"}


@app.on_event("startup")
async def startup():
    """Inicia todos os servidores automaticamente"""
    logger.info("=" * 60)
    logger.info("🚀 CORE SERVER INICIADO - INICIANDO SERVIDORES FILHOS...")
    logger.info("=" * 60)
    
    for nome, config in SERVIDORES.items():
        logger.info(f"📋 {nome}: {config['descricao']} (porta {config['porta']})")
    
    logger.info("=" * 60)
    
    for nome, config in SERVIDORES.items():
        await _iniciar_servidor(nome, config)
    
    logger.info("=" * 60)
    logger.info("✅ TODOS OS SERVIDORES PROCESSADOS")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown():
    """Para todos os servidores ao desligar"""
    logger.info("=" * 60)
    logger.info("🛑 CORE SERVER DESLIGANDO - PARANDO SERVIDORES FILHOS...")
    logger.info("=" * 60)
    
    for nome, config in SERVIDORES.items():
        await _parar_servidor(nome, config)
    
    logger.info("=" * 60)
    logger.info("✅ TODOS OS SERVIDORES PARADOS")
    logger.info("=" * 60)


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🚀 INICIANDO SERVIDOR CORE (ORQUESTRADOR) - PORTA 5000")
    logger.info("=" * 60)
    logger.info("Servidores gerenciados:")
    for nome, config in SERVIDORES.items():
        logger.info(f"  - {nome}: porta {config['porta']} ({config['descricao']})")
    logger.info("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=5000)