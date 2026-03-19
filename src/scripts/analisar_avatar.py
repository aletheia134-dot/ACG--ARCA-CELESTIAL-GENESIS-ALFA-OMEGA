# analisar_avatar.py
import cv2
import numpy as np
from pathlib import Path

class AnalisadorAvatar:
    def __init__(self, pasta_alma):
        self.pasta = Path(pasta_alma)
        self.caracteristicas = {}
        
    def analisar_imagens(self):
        """Extrai características das imagens 2D"""
        
        # Pega todas as imagens estáticas
        imagens = list(self.pasta.glob("static/*.png"))
        
        for img_path in imagens:
            # Carrega imagem
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            
            # Detecta rosto
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) > 0:
                x, y, w, h = faces[0]
                rosto = img[y:y+h, x:x+w]
                
                # Extrai características
                self.caracteristicas[img_path.stem] = {
                    "cor_olhos": self._cor_olhos(rosto),
                    "cor_cabelo": self._cor_cabelo(rosto),
                    "formato_rosto": w/h,
                    "expressao": img_path.stem
                }
        
        return self.caracteristicas
    
    def _cor_olhos(self, rosto):
        """Detecta cor dos olhos (aproximada)"""
        h, w = rosto.shape[:2]
        # Região aproximada dos olhos
        olhos = rosto[h//3:h//2, w//4:3*w//4]
        return np.mean(olhos, axis=(0,1)).tolist()
    
    def _cor_cabelo(self, rosto):
        """Detecta cor do cabelo (parte superior)"""
        cabelo = rosto[:rosto.shape[0]//4, :]
        return np.mean(cabelo, axis=(0,1)).tolist()

# USAR:
# ana = AnalisadorAvatar("assets/Avatares/EVA")
# caracteristicas = ana.analisar_imagens()
# print(caracteristicas)