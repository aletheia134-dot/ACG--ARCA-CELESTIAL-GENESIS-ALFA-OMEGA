"""
SERVIDOR MEDIA - Câmera, Áudio, TTS, Expressão
Roda no ambiente MEDIA (porta 5001)
"""

import os
import sys
import base64
import logging
import signal
import gc
from pathlib import Path
from datetime import datetime

# Garantir que o cwd é a raiz do projeto
_ROOT = Path(__file__).parent.parent.parent
os.chdir(str(_ROOT))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import uvicorn

# ============================================================================
# HANDLER DE SINAIS
# ============================================================================

def handle_shutdown(signum, frame):
    logging.info(f"\n🛑 Recebido sinal {signum}. Desligando servidor media...")
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
        logging.FileHandler(f"Logs/media_{datetime.now().strftime('%Y%m%d')}.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("media_server")

# ============================================================================
# VERIFICAÇÃO DE DEPENDÊNCIAS
# ============================================================================

# OpenCV
try:
    import cv2
    CV2_DISPONIVEL = True
    logger.info("✅ OpenCV (cv2) disponível")
except ImportError:
    cv2 = None
    CV2_DISPONIVEL = False
    logger.warning("⚠️ cv2 não instalado - câmera desabilitada")

# PyAudio
try:
    import pyaudio
    PYAUDIO_DISPONIVEL = True
    logger.info("✅ PyAudio disponível")
except ImportError:
    pyaudio = None
    PYAUDIO_DISPONIVEL = False
    logger.warning("⚠️ PyAudio não instalado - microfone desabilitado")

# pyttsx3
try:
    import pyttsx3
    TTS_DISPONIVEL = True
    logger.info("✅ pyttsx3 disponível")
except ImportError:
    pyttsx3 = None
    TTS_DISPONIVEL = False
    logger.warning("⚠️ pyttsx3 não instalado - TTS desabilitado")

# ============================================================================
# MODELOS
# ============================================================================

class TTSRequest(BaseModel):
    texto: str
    voz: str = "default"
    velocidade: float = 1.0


class AudioRequest(BaseModel):
    duracao: int = 5  # segundos


# ============================================================================
# LIFESPAN (substitui o @app.on_event deprecated do FastAPI)
# ============================================================================

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("✅ Servidor Media iniciando (porta 5001)...")
    yield
    logger.info("🧹 Limpando arquivos temporários...")
    for f in Path(".").glob("temp_audio_*.wav"):
        try:
            f.unlink()
            logger.info(f"   Removido {f}")
        except:
            pass


app = FastAPI(title="Arca Media Server", version="2.0", lifespan=lifespan)


@app.get("/")
async def root():
    return {
        "servidor": "Media",
        "status": "ativo",
        "porta": 5001,
        "modulos": {
            "camera": CV2_DISPONIVEL,
            "microfone": PYAUDIO_DISPONIVEL,
            "tts": TTS_DISPONIVEL
        }
    }


@app.get("/health")
async def health():
    return {"status": "ok", "modulos": {
        "camera": CV2_DISPONIVEL,
        "microfone": PYAUDIO_DISPONIVEL,
        "tts": TTS_DISPONIVEL
    }}


@app.get("/status")
async def status():
    """Status detalhado do servidor"""
    camera_ok = False
    if CV2_DISPONIVEL and cv2:
        try:
            cap = cv2.VideoCapture(0)
            camera_ok = cap.isOpened()
            cap.release()
        except:
            camera_ok = False

    return {
        "servidor": "media",
        "porta": 5001,
        "modulos": {
            "camera": {
                "disponivel": CV2_DISPONIVEL,
                "funcionando": camera_ok
            },
            "microfone": {
                "disponivel": PYAUDIO_DISPONIVEL
            },
            "tts": {
                "disponivel": TTS_DISPONIVEL
            }
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/camera")
async def camera():
    """Captura imagem da câmera"""
    logger.info("📸 Capturando imagem da câmera")
    
    if not CV2_DISPONIVEL or not cv2:
        raise HTTPException(status_code=503, detail={
            "erro": "OpenCV não disponível",
            "solucao": "pip install opencv-python no venv media"
        })
    
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise HTTPException(status_code=404, detail="Câmera não disponível")
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise HTTPException(status_code=500, detail="Falha ao capturar imagem")
        
        # Redimensionar para economizar banda
        height, width = frame.shape[:2]
        if width > 640:
            scale = 640 / width
            new_width = 640
            new_height = int(height * scale)
            frame = cv2.resize(frame, (new_width, new_height))
        
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        logger.info(f"✅ Imagem capturada: {new_width}x{new_height}, {len(img_base64)/1024:.1f}KB")
        
        return {
            "imagem": img_base64,
            "formato": "jpg",
            "largura": new_width,
            "altura": new_height
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro na câmera: {e}")
        raise HTTPException(status_code=500, detail={"erro": str(e)})


@app.post("/tts")
async def tts(req: TTSRequest):
    """Text-to-Speech - gera áudio"""
    logger.info(f"🔊 TTS: {req.texto[:50]}...")
    
    if not TTS_DISPONIVEL or not pyttsx3:
        raise HTTPException(status_code=503, detail={
            "erro": "pyttsx3 não disponível",
            "solucao": "pip install pyttsx3 no venv media"
        })
    
    try:
        engine = pyttsx3.init()
        
        # Ajustar velocidade
        rate = engine.getProperty('rate')
        engine.setProperty('rate', rate * req.velocidade)
        
        # Gerar arquivo temporário
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo = f"temp_audio_{timestamp}.wav"
        
        engine.save_to_file(req.texto, arquivo)
        engine.runAndWait()
        
        logger.info(f"✅ Áudio gerado: {arquivo}")
        
        return FileResponse(
            arquivo,
            media_type="audio/wav",
            filename=f"fala_{timestamp}.wav",
            headers={"Content-Disposition": f"attachment; filename=fala_{timestamp}.wav"}
        )
    except Exception as e:
        logger.error(f"❌ Erro no TTS: {e}")
        raise HTTPException(status_code=500, detail={"erro": str(e)})


@app.post("/microfone")
async def gravar_audio(req: AudioRequest):
    """Grava áudio do microfone"""
    logger.info(f"🎤 Gravando áudio por {req.duracao}s")
    
    if not PYAUDIO_DISPONIVEL or not pyaudio:
        raise HTTPException(status_code=503, detail={
            "erro": "PyAudio não disponível",
            "solucao": "pip install pyaudio no venv media"
        })
    
    try:
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        
        p = pyaudio.PyAudio()
        
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        frames = []
        for i in range(0, int(RATE / CHUNK * req.duracao)):
            data = stream.read(CHUNK)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo = f"temp_audio_{timestamp}.wav"
        
        import wave
        wf = wave.open(arquivo, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        logger.info(f"✅ Áudio gravado: {arquivo}")
        
        return FileResponse(
            arquivo,
            media_type="audio/wav",
            filename=f"gravacao_{timestamp}.wav"
        )
    except Exception as e:
        logger.error(f"❌ Erro ao gravar áudio: {e}")
        raise HTTPException(status_code=500, detail={"erro": str(e)})


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🎬 SERVIDOR MEDIA - Porta 5001")
    logger.info("   Câmera, Áudio, TTS")
    logger.info(f"   OpenCV: {'✅' if CV2_DISPONIVEL else '❌'}")
    logger.info(f"   PyAudio: {'✅' if PYAUDIO_DISPONIVEL else '❌'}")
    logger.info(f"   pyttsx3: {'✅' if TTS_DISPONIVEL else '❌'}")
    logger.info("=" * 60)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5001,
        log_level="info",
        workers=1,
        loop="asyncio",
        timeout_keep_alive=30,
    )