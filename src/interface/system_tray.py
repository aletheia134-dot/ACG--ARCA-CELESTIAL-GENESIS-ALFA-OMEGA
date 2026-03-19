# system_tray.py - Atualizado
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
system_tray.py - cone na Bandeja do Sistema para Controle da Arca

Integra com pystray para cone persistente na bandeja.
Permite abrir UI, fechar sistema, ver status.
"""

import pystray
from PIL import Image, ImageDraw
import threading
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)

class SystemTray:
    """
    Gerenciador do cone na bandeja do sistema.
    """
    
    def __init__(
        self,
        on_show_ui: Callable = None,
        on_shutdown: Callable = None,
        on_status: Callable = None
    ):
        self.on_show_ui = on_show_ui
        self.on_shutdown = on_shutdown
        self.on_status = on_status
        
        self.icon: Optional[pystray.Icon] = None
        self._running = False
        
        # Menu
        self.menu = pystray.Menu(
            pystray.MenuItem("Mostrar UI", self._show_ui),
            pystray.MenuItem("Status Sistema", self._show_status),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Sair", self._shutdown)
        )
        
        # cone simples
        self.image = self._create_icon()
    
    def _create_icon(self) -> Image.Image:
        """Cria cone simples."""
        width, height = 64, 64
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Crculo azul
        draw.ellipse((8, 8, 56, 56), fill=(0, 123, 255, 255))
        
        # "A" branca
        draw.text((28, 28), "A", fill=(255, 255, 255, 255), anchor="mm")
        
        return image
    
    def start(self) -> None:
        """Inicia o cone na bandeja."""
        if self._running:
            return
            
        self._running = True
        
        self.icon = pystray.Icon(
            "arca_system",
            self.image,
            "Arca Celestial",
            self.menu
        )
        
        # Iniciar em thread separada
        thread = threading.Thread(target=self.icon.run, daemon=True)
        thread.start()
        
        logger.info("[OK] cone da bandeja iniciado")
    
    def stop(self) -> None:
        """Para o cone."""
        self._running = False
        if self.icon:
            self.icon.stop()
            logger.info("[OK] cone da bandeja parado")
    
    def _show_ui(self) -> None:
        """Callback para mostrar UI."""
        if self.on_show_ui:
            try:
                self.on_show_ui()
            except Exception as e:
                logger.exception(f"Erro ao mostrar UI: {e}")
    
    def _show_status(self) -> None:
        """Callback para mostrar status."""
        if self.on_status:
            try:
                self.on_status()
            except Exception as e:
                logger.exception(f"Erro ao mostrar status: {e}")
    
    def _shutdown(self) -> None:
        """Callback para shutdown."""
        if self.on_shutdown:
            try:
                self.on_shutdown()
            except Exception as e:
                logger.exception(f"Erro no shutdown: {e}")
        
        self.stop()
    
    def update_tooltip(self, tooltip: str) -> None:
        """Atualiza tooltip do cone."""
        if self.icon:
            self.icon.title = tooltip

if __name__ == "__main__":
    import time
    
    def show_ui():
        print("UI aberta")
    
    def shutdown():
        print("Shutdown iniciado")
    
    def status():
        print("Status: OK")
    
    tray = SystemTray(
        on_show_ui=show_ui,
        on_shutdown=shutdown,
        on_status=status
    )
    
    tray.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        tray.stop()
