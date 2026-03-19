# scripts/gerar_144_emocoes.py
"""
Gerador de 144 expressões faciais baseado em combinações matemáticas
"""

import json
import math
from pathlib import Path

class GeradorEmocoes3D:
    def __init__(self, nome_alma):
        self.nome_alma = nome_alma
        self.emocoes = {}
        
        # Cores base por alma (para shader)
        self.cores = {
            "EVA": [0.4, 0.6, 1.0],     # Azul celestial
            "LUMINA": [1.0, 0.7, 0.8],   # Rosa suave
            "NYRA": [0.6, 0.4, 0.8],     # Roxo místico
            "YUNA": [0.9, 0.8, 0.5],      # Dourado suave
            "KAIYA": [0.3, 0.8, 0.6],     # Verde esperança
            "WELLINGTON": [0.5, 0.5, 0.7] # Azul noturno
        }
        
    def gerar_todas(self):
        """Gera 144 expressões combinando parâmetros"""
        
        # Parâmetros base (cada um com 3-4 variações)
        sobrancelhas = [-0.8, -0.4, 0.0, 0.4, 0.8]  # 5 variações
        olhos = [-0.5, 0.0, 0.3, 0.6, 0.9]          # 5 variações
        boca = [-0.8, -0.4, 0.0, 0.4, 0.8]          # 5 variações
        bochecha = [0.0, 0.3, 0.6, 0.9]              # 4 variações
        
        # 5 × 5 × 5 × 4 = 500 combinações (mais que 144)
        # Vamos selecionar as mais significativas
        
        index = 0
        for sb in sobrancelhas:
            for ol in olhos:
                for bc in boca:
                    for bq in bochecha:
                        # Pula combinações muito extremas
                        if abs(sb) > 0.7 and abs(bc) > 0.7:
                            continue  # Evita raiva + alegria extrema
                        
                        # Nome da emoção baseado nos valores
                        nome = self._nomear_emocao(sb, ol, bc, bq)
                        
                        self.emocoes[nome] = {
                            "sobrancelhas": sb,
                            "olhos": ol,
                            "boca": bc,
                            "bochecha": bq,
                            "cor_base": self.cores.get(self.nome_alma, [0.5, 0.5, 0.5])
                        }
                        
                        index += 1
                        if index >= 144:
                            break
                    if index >= 144: break
                if index >= 144: break
            if index >= 144: break
        
        return self.emocoes
    
    def _nomear_emocao(self, sb, ol, bc, bq):
        """Gera nome baseado nos parâmetros"""
        
        # Determina emoção principal
        if bc > 0.3:
            if sb > 0.3:
                base = "alegria"
            elif ol > 0.5:
                base = "entusiasmo"
            else:
                base = "contentamento"
        elif bc < -0.3:
            if sb < -0.3:
                base = "tristeza"
            elif ol < -0.2:
                base = "melancolia"
            else:
                base = "desapontamento"
        else:
            if sb > 0.4:
                base = "surpresa"
            elif sb < -0.4:
                base = "preocupacao"
            elif ol > 0.5:
                base = "curiosidade"
            else:
                base = "neutralidade"
        
        # Intensidade
        intensidade = ""
        if abs(bc) > 0.6 or abs(sb) > 0.6:
            intensidade = "forte"
        elif abs(bc) > 0.3 or abs(sb) > 0.3:
            intensidade = "media"
        else:
            intensidade = "leve"
        
        # Adjetivo baseado na bochecha
        tom = ""
        if bq > 0.7:
            tom = "apaixonada"
        elif bq > 0.4:
            tom = "calorosa"
        elif bq > 0.1:
            tom = "suave"
        
        # Combina
        partes = [p for p in [base, intensidade, tom] if p]
        return "_".join(partes)
    
    def salvar_json(self):
        """Salva mapeamento para usar no avatar"""
        caminho = Path(f"assets/Avatares/{self.nome_alma}/3d/emocoes.json")
        caminho.parent.mkdir(parents=True, exist_ok=True)
        
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(self.emocoes, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 144 emoções salvas em {caminho}")
        return caminho


# Gerar para todas as almas
if __name__ == "__main__":
    for alma in ["EVA", "LUMINA", "NYRA", "YUNA", "KAIYA", "WELLINGTON"]:
        gerador = GeradorEmocoes3D(alma)
        gerador.gerar_todas()
        gerador.salvar_json()
        print(f"✨ {alma}: 144 emoções geradas")