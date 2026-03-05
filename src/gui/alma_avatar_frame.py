# alma_avatar_frame.py - Atualizado
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alma_avatar_frame.py - Frame para Exibição de Avatar de Alma

Exibe avatar animado com expressões faciais e texto de fala.
Integra com motores de expressão individual.
"""

import tkinter as tk
from tkinter import ttk, font
from PIL import Image, ImageTk, ImageDraw
import threading
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class AlmaAvatarFrame(ttk.Frame):
    """
    Frame que exibe avatar de uma alma com expressões e fala.
    """
    
    def __init__(self, master, nome_alma: str, coracao_ref=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.nome_alma = nome_alma
        self.coracao_ref = coracao_ref
        
        self._expressao_atual = "neutra"
        self._fala_atual = ""
        self._animating = False
        
        # Canvas para avatar
        self.canvas = tk.Canvas(self, width=200, height=250, bg='white')
        self.canvas.pack(pady=10)
        
        # Label para fala
        self.label_fala = ttk.Label(self, text="", wraplength=180, justify="center")
        self.label_fala.pack(pady=5)
        
        # Label para status
        self.label_status = ttk.Label(self, text=f"Alma: {nome_alma}", font=("Arial", 10, "bold"))
        self.label_status.pack(pady=5)
        
        # Carregar avatar base
        self._carregar_avatar_base()
        
        # Iniciar atualização periódica
        self._running = True
        self._thread_atualizacao = threading.Thread(target=self._loop_atualizacao, daemon=True)
        self._thread_atualizacao.start()
    
    def _carregar_avatar_base(self) -> None:
        """Carrega avatar base (círculo simples)."""
        self.avatar_base = Image.new('RGBA', (150, 150), (255, 255, 255, 0))
        draw = ImageDraw.Draw(self.avatar_base)
        
        # Cabeça
        draw.ellipse((25, 25, 125, 125), fill=(255, 200, 150, 255))
        
        # Olhos
        draw.ellipse((50, 60, 70, 80), fill=(0, 0, 0, 255))
        draw.ellipse((80, 60, 100, 80), fill=(0, 0, 0, 255))
        
        # Boca
        draw.arc((60, 85, 90, 105), start=0, end=180, fill=(0, 0, 0, 255), width=2)
        
        self.photo_avatar = ImageTk.PhotoImage(self.avatar_base)
        self.canvas.create_image(100, 75, image=self.photo_avatar)
    
    def atualizar_expressao(self, expressao: str) -> None:
        """Atualiza expressão facial."""
        self._expressao_atual = expressao
        
        # Modificar boca baseada na expressão
        avatar_modificado = self.avatar_base.copy()
        draw = ImageDraw.Draw(avatar_modificado)
        
        if expressao == "feliz":
            draw.arc((60, 85, 90, 105), start=0, end=180, fill=(255, 0, 0, 255), width=3)
        elif expressao == "triste":
            draw.arc((60, 95, 90, 115), start=180, end=0, fill=(0, 0, 255, 255), width=3)
        elif expressao == "surpreso":
            draw.ellipse((75, 85, 85, 105), fill=(255, 255, 0, 255))
        
        self.photo_avatar = ImageTk.PhotoImage(avatar_modificado)
        self.canvas.create_image(100, 75, image=self.photo_avatar)
        
        self.label_status.config(text=f"Alma: {self.nome_alma} ({expressao})")
    
    def falar(self, texto: str) -> None:
        """Define texto de fala."""
        self._fala_atual = texto
        self.label_fala.config(text=texto)
        
        # Auto-clear após 5 segundos
        self.after(5000, lambda: self.label_fala.config(text=""))
    
    def _loop_atualizacao(self) -> None:
        """Loop de atualização para animações."""
        while self._running:
            try:
                time.sleep(0.1)
                
                # Verificar se há motores individuais
                if self.coracao_ref:
                    motor = self.coracao_ref.obter_motor_expressao_individual(self.nome_alma)
                    if motor and hasattr(motor, 'obter_estado_atual'):
                        estado = motor.obter_estado_atual()
                        if estado.get('expressao') != self._expressao_atual:
                            self.atualizar_expressao(estado['expressao'])
                        
                        if estado.get('fala') != self._fala_atual:
                            self.falar(estado['fala'])
                            
            except Exception as e:
                logger.debug(f"Erro na atualização: {e}")
    
    def destroy(self) -> None:
        """Destrói o frame."""
        self._running = False
        super().destroy()

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Teste Alma Avatar")
    
    frame = AlmaAvatarFrame(root, "Eva")
    frame.pack(padx=20, pady=20)
    
    # Teste
    frame.atualizar_expressao("feliz")
    frame.falar("Olá, eu sou Eva!")
    
    root.mainloop()
