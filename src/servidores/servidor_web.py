"""
SERVIDOR WEB - Automação de navegadores
Roda no ambiente WEB (porta 5003)
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import logging
from datetime import datetime
import asyncio

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"scripts/logs/web_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("web_server")

app = FastAPI(title="Arca Web Server")

class NavegadorRequest(BaseModel):
    url: str
    acao: str  # "abrir", "capturar", "clicar"

@app.get("/")
async def root():
    return {"servidor": "Web", "status": "ativo"}

@app.post("/navegador")
async def navegador(request: NavegadorRequest):
    """Controlar navegador"""
    logger.info(f"Navegador: {request.acao} em {request.url}")
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(request.url)
            
            if request.acao == "capturar":
                screenshot = await page.screenshot()
                # Salvar ou retornar screenshot
                with open(f"temp_screenshot_{datetime.now().timestamp()}.png", "wb") as f:
                    f.write(screenshot)
                await browser.close()
                return {"status": "capturado", "url": request.url}
            
            elif request.acao == "titulo":
                titulo = await page.title()
                await browser.close()
                return {"status": "ok", "titulo": titulo}
            
            await browser.close()
            return {"status": "ok", "acao": request.acao, "url": request.url}
            
    except Exception as e:
        logger.error(f"Erro no navegador: {e}")
        return {"erro": str(e)}

@app.get("/status")
async def status():
    """Status do servidor"""
    return {
        "servidor": "web",
        "playwright": True,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5003)