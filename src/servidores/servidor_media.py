"""
SERVIDOR MEDIA - Câmera, Áudio, TTS, Expressão
Roda no ambiente MEDIA (porta 5001)
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import uvicorn
import cv2
import base64
import os
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"scripts/logs/media_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("media_server")

app = FastAPI(title="Arca Media Server")

@app.get("/")
async def root():
    return {"servidor": "Media", "status": "ativo"}

@app.get("/camera")
async def camera():
    """Captura imagem da câmera"""
    logger.info("Requisição para câmera")
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logger.error("Câmera não disponível")
            return JSONResponse(status_code=404, content={"erro": "Câmera não disponível"})
        
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            _, buffer = cv2.imencode('.jpg', frame)
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            logger.info("Imagem capturada com sucesso")
            return {"imagem": img_base64}
        else:
            logger.error("Falha ao capturar imagem")
            return JSONResponse(status_code=500, content={"erro": "Falha ao capturar imagem"})
    except Exception as e:
        logger.error(f"Erro na câmera: {e}")
        return JSONResponse(status_code=500, content={"erro": str(e)})

@app.get("/tts")
async def tts(texto: str):
    """Text-to-Speech"""
    logger.info(f"TTS: {texto[:50]}...")
    try:
        import pyttsx3
        engine = pyttsx3.init()
        arquivo = f"temp_audio_{datetime.now().timestamp()}.wav"
        engine.save_to_file(texto, arquivo)
        engine.runAndWait()
        logger.info(f"Áudio gerado: {arquivo}")
        return FileResponse(arquivo, media_type="audio/wav", filename="fala.wav")
    except Exception as e:
        logger.error(f"Erro no TTS: {e}")
        return JSONResponse(status_code=500, content={"erro": str(e)})

@app.get("/status")
async def status():
    """Status do servidor"""
    try:
        # Testar câmera
        cap = cv2.VideoCapture(0)
        camera_ok = cap.isOpened()
        cap.release()
        
        return {
            "servidor": "media",
            "camera": camera_ok,
            "tts": True,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"servidor": "media", "erro": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)