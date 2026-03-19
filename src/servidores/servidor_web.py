"""
SERVIDOR WEB - Automação de navegadores
Roda no ambiente WEB (porta 5003)
"""

import os
import sys
import logging
import signal
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

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
    logging.getLogger("web_server").info(f"\n🛑 Recebido sinal {signum}. Desligando servidor web...")
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
        logging.FileHandler(f"Logs/web_{datetime.now().strftime('%Y%m%d')}.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("web_server")

# ============================================================================
# PLAYWRIGHT (lazy loading)
# ============================================================================

_playwright_disponivel = False

try:
    from playwright.async_api import async_playwright
    _playwright_disponivel = True
    logger.info("✅ Playwright disponível")
except ImportError:
    logger.warning("⚠️ Playwright não instalado - execute: pip install playwright && playwright install chromium")


class NavegadorRequest(BaseModel):
    url: str
    acao: str  # "abrir", "capturar", "titulo", "conteudo", "pdf"
    esperar: int = 0  # segundos para esperar após carregar
    screenshot_path: Optional[str] = None


class ScriptRequest(BaseModel):
    url: str
    script: str  # código JavaScript a executar


app = FastAPI(title="Arca Web Server", version="2.0")


@app.get("/")
async def root():
    return {
        "servidor": "Web",
        "status": "ativo",
        "porta": 5003,
        "playwright": _playwright_disponivel
    }


@app.get("/health")
async def health():
    return {"status": "ok", "playwright": _playwright_disponivel}


@app.get("/status")
async def status():
    """Status do servidor"""
    return {
        "servidor": "web",
        "porta": 5003,
        "playwright": _playwright_disponivel,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/navegador")
async def navegador(request: NavegadorRequest):
    """Controlar navegador via Playwright"""
    logger.info(f"🌐 Navegador: {request.acao} em {request.url}")

    if not _playwright_disponivel:
        raise HTTPException(status_code=503, detail={
            "erro": "Playwright não disponível",
            "solucao": "pip install playwright && playwright install chromium"
        })

    try:
        async with async_playwright() as p:
            # Lançar navegador
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-dev-shm-usage']
            )
            page = await browser.new_page()
            
            # Navegar
            logger.info(f"⏳ Navegando para {request.url}")
            await page.goto(request.url, wait_until="networkidle", timeout=30000)
            
            # Esperar se solicitado
            if request.esperar > 0:
                logger.info(f"⏳ Aguardando {request.esperar}s...")
                await page.wait_for_timeout(request.esperar * 1000)
            
            resultado = {"url": request.url, "acao": request.acao}
            
            # Executar ação
            if request.acao == "capturar" or request.acao == "screenshot":
                # Gerar nome do arquivo
                if request.screenshot_path:
                    caminho = request.screenshot_path
                else:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    caminho = f"Logs/screenshot_{ts}.png"
                
                await page.screenshot(path=caminho, full_page=True)
                resultado["screenshot"] = caminho
                logger.info(f"✅ Screenshot salvo: {caminho}")
                
            elif request.acao == "titulo":
                titulo = await page.title()
                resultado["titulo"] = titulo
                logger.info(f"✅ Título obtido: {titulo}")
                
            elif request.acao == "conteudo":
                conteudo = await page.content()
                resultado["conteudo_tamanho"] = len(conteudo)
                resultado["conteudo_amostra"] = conteudo[:500] + "..." if len(conteudo) > 500 else conteudo
                logger.info(f"✅ Conteúdo obtido: {len(conteudo)} caracteres")
                
            elif request.acao == "pdf":
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                caminho = f"Logs/page_{ts}.pdf"
                await page.pdf(path=caminho)
                resultado["pdf"] = caminho
                logger.info(f"✅ PDF gerado: {caminho}")
                
            else:  # "abrir" ou qualquer outra ação
                titulo = await page.title()
                resultado["titulo"] = titulo
                resultado["mensagem"] = f"Página aberta: {titulo}"
                logger.info(f"✅ Página aberta: {titulo}")
            
            await browser.close()
            return {"status": "ok", "resultado": resultado}
            
    except Exception as e:
        logger.error(f"❌ Erro no navegador: {e}")
        raise HTTPException(status_code=500, detail={"erro": str(e)})


@app.post("/executar")
async def executar_script(request: ScriptRequest):
    """Executa JavaScript na página"""
    logger.info(f"📜 Executando script em {request.url}")
    
    if not _playwright_disponivel:
        raise HTTPException(status_code=503, detail="Playwright não disponível")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(request.url, wait_until="networkidle")
            
            resultado = await page.evaluate(request.script)
            
            await browser.close()
            
            return {
                "status": "ok",
                "url": request.url,
                "resultado": resultado
            }
    except Exception as e:
        logger.error(f"❌ Erro no script: {e}")
        raise HTTPException(status_code=500, detail={"erro": str(e)})


@app.get("/info")
async def info_navegador():
    """Informações sobre o navegador"""
    if not _playwright_disponivel:
        raise HTTPException(status_code=503, detail="Playwright não disponível")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            version = browser.version
            await browser.close()
            
            return {
                "navegador": "Chromium",
                "versao": version,
                "playwright": True
            }
    except Exception as e:
        logger.error(f"❌ Erro ao obter info: {e}")
        raise HTTPException(status_code=500, detail={"erro": str(e)})


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🌐 SERVIDOR WEB - Porta 5003")
    logger.info(f"   Playwright: {'✅' if _playwright_disponivel else '❌'}")
    logger.info("=" * 60)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5003,
        log_level="info",
        workers=1,          # single-process — mais estável no Windows
        loop="asyncio",     # evita conflito de event loop no Windows
        timeout_keep_alive=30,
    )