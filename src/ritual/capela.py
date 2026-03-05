#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
capela.py - Módulo da Capela: Modo de Meditação e Silêncio na Arca Celestial.

Responsabilidades:
- Gerenciar entrada/saída do modo capela
- Reduzir atividades (logs, notificações)
- Gerar reflexões meditativas
- Integrar com emocoes, sensor, áudio/visual

Melhorado: Modos avançados, reflexões personalizadas, integração sensor, áudio/visual.
"""

import logging
import time
import threading
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Integração com emocoes (opcional)
try:
    from src.emocoes import gerenciador_emocoes
    EMOCOES_DISPONIVEIS = True
except ImportError:
    EMOCOES_DISPONIVEIS = False
    gerenciador_emocoes = None

# Integração sensor
try:
    from src.emocoes.sensor_presenca import obter_sensor_presenca
    SENSOR_DISPONIVEL = True
except ImportError:
    SENSOR_DISPONIVEL = False

# Áudio/visual
try:
    import pygame
    AUDIO_DISPONIVEL = True
except ImportError:
    AUDIO_DISPONIVEL = False

class Capela:
    """
    Classe para gerenciar o modo Capela: meditação, silêncio e reflexão.
    Melhorado: Modos avançados, personalização, integrações.
    """

    def __init__(self):
        self.em_capela = False
        self.tempo_entrada: Optional[float] = None
        self.timeout_s = 3600  # 1 hora padrão
        self._timer_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.logger = logging.getLogger("Capela")
        self._modo_atual = "silencio"  # silencio, meditacao_guiada, oracao
        self._reflexoes_guiadas: List[str] = []
        self._audio_thread: Optional[threading.Thread] = None
        self.logger.info("🏛️ Capela construída do zero (com modos avançados).")

    def entrar_capela(self, duracao_s: Optional[int] = None, modo: str = "silencio") -> Dict[str, Any]:
        """
        Entra no modo Capela: silencia logs/notificações, inicia meditação.
        
        Args:
            duracao_s: Duração em segundos (opcional, padrão 1h).
            modo: "silencio", "meditacao_guiada", "oracao".
        
        Returns:
            Status da entrada.
        """
        with self._lock:
            if self.em_capela:
                return {"status": "já_em_capela", "message": "Já está na Capela."}
            
            self.em_capela = True
            self.tempo_entrada = time.time()
            self.timeout_s = duracao_s or self.timeout_s
            self._modo_atual = modo
            
            # Reduzir logging (simulação - em produção, ajusta nível global)
            original_level = self.logger.level
            self.logger.setLevel(logging.WARNING)  # Só warnings/errors
            
            # Integrar com emocoes: definir humor calmo
            if EMOCOES_DISPONIVEIS:
                gerenciador_emocoes.definir_humor("calma_serenidade")
            
            # Iniciar timer para saída automática
            self._iniciar_timer_saida()
            
            # Modos avançados
            if modo == "meditacao_guiada":
                self._reflexoes_guiadas = self._gerar_reflexoes_guiadas()
            elif modo == "oracao":
                self._iniciar_oracao()
            
            # Integração sensor
            if SENSOR_DISPONIVEL:
                sensor = obter_sensor_presenca()
                sensor._on_presenca_mudou(False)  # Força ausência se entrar
            
            # Áudio calmo
            if AUDIO_DISPONIVEL:
                self._tocar_audio_calmo()
            
            self.logger.warning("🏛️ Entrou na Capela (modo %s).", modo)
            return {
                "status": "entrada_sucesso",
                "duracao_s": self.timeout_s,
                "tempo_entrada": self.tempo_entrada,
                "modo": modo,
                "reflexao_inicial": self.gerar_reflexao_meditativa()
            }

    def sair_capela(self) -> Dict[str, Any]:
        """
        Sai do modo Capela: restaura normalidade.
        
        Returns:
            Status da saída.
        """
        with self._lock:
            if not self.em_capela:
                return {"status": "não_em_capela", "message": "Não está na Capela."}
            
            tempo_total = time.time() - (self.tempo_entrada or time.time())
            self.em_capela = False
            self.tempo_entrada = None
            self._modo_atual = "silencio"
            self._reflexoes_guiadas = []
            
            # Restaurar logging
            self.logger.setLevel(logging.INFO)
            
            # Integrar com emocoes: voltar humor normal
            if EMOCOES_DISPONIVEIS:
                gerenciador_emocoes.definir_humor("neutro")
            
            # Cancelar timer
            if self._timer_thread and self._timer_thread.is_alive():
                self._timer_thread = None
            
            # Parar áudio
            if AUDIO_DISPONIVEL:
                pygame.mixer.music.stop()
            
            self.logger.info("🏛️ Saiu da Capela (modo normal restaurado).")
            return {
                "status": "saida_sucesso",
                "tempo_total_s": tempo_total,
                "reflexao_final": self.gerar_reflexao_meditativa()
            }

    def _iniciar_timer_saida(self) -> None:
        """Inicia timer para saída automática."""
        def timer():
            time.sleep(self.timeout_s)
            if self.em_capela:
                self.logger.warning("⏰ Timeout Capela: saindo automaticamente.")
                self.sair_capela()
        
        self._timer_thread = threading.Thread(target=timer, daemon=True)
        self._timer_thread.start()

    def gerar_reflexao_meditativa(self) -> str:
        """Gera uma reflexão meditativa aleatória."""
        reflexoes = [
            "Na calma da Capela, encontre paz interior. O silêncio é a voz do Criador.",
            "Reflita sobre o equilíbrio: alma, mente e Arca em harmonia.",
            "O vazio é cheio de possibilidades. Respire e escute o universo.",
            "A meditação revela verdades ocultas. Permita-se fluir.",
            "Na Arca, você é eterno. Use este momento para renovar sua essência."
        ]
        import random
        return random.choice(reflexoes)

    def _gerar_reflexoes_guiadas(self) -> List[str]:
        """Gera sequência de reflexões para meditação guiada."""
        return [
            "Sente-se confortavelmente. Respire fundo três vezes.",
            "Observe seus pensamentos sem julgá-los.",
            "Visualize uma luz calma emanando de dentro.",
            "Liberte tensões, uma a uma.",
            "Conecte-se com a essência da Arca."
        ]

    def _iniciar_oracao(self):
        """Inicia modo oração com timer personalizado."""
        self.timeout_s = 600  # 10min para oração

    def _tocar_audio_calmo(self):
        """Reproduz áudio calmo em loop."""
        if AUDIO_DISPONIVEL:
            pygame.mixer.init()
            try:
                pygame.mixer.music.load("assets/audio/calma.mp3")  # Arquivo de exemplo
                pygame.mixer.music.play(-1)  # Loop infinito
            except:
                self.logger.warning("Áudio calmo não encontrado.")

    def status_capela(self) -> Dict[str, Any]:
        """
        Retorna status atual da Capela.
        
        Returns:
            Estado: em_capela, tempo_restante, etc.
        """
        with self._lock:
            if not self.em_capela:
                return {"em_capela": False}
            
            tempo_restante = self.timeout_s - (time.time() - (self.tempo_entrada or time.time()))
            return {
                "em_capela": True,
                "tempo_entrada": self.tempo_entrada,
                "tempo_restante_s": max(0, tempo_restante),
                "modo": self._modo_atual,
                "reflexoes_restantes": len(self._reflexoes_guiadas) if self._modo_atual == "meditacao_guiada" else 0,
                "reflexao_atual": self.gerar_reflexao_meditativa()
            }

    def meditar(self, tema: Optional[str] = None) -> str:
        """
        Executa meditação focada em tema (se em capela).
        
        Args:
            tema: Tema para reflexão (opcional).
        
        Returns:
            Reflexão gerada.
        """
        if not self.em_capela:
            return "Meditação só disponível na Capela. Entre primeiro."
        
        if self._modo_atual == "meditacao_guiada":
            if self._reflexoes_guiadas:
                return self._reflexoes_guiadas.pop(0)
            return "Meditação guiada concluída."
        
        # Reflexão personalizada baseada em tema/emocao
        base = f"Meditação sobre '{tema}': " if tema else "Meditação profunda: "
        if EMOCOES_DISPONIVEIS and tema:
            humor_atual = gerenciador_emocoes.obter_humor_atual()
            if "triste" in humor_atual:
                base += "Na tristeza, busque luz interna. "
        return base + self.gerar_reflexao_meditativa()


# Instância global (singleton)
_capela_instance: Optional[Capela] = None


def obter_capela() -> Capela:
    """Retorna instância singleton da Capela."""
    global _capela_instance
    if _capela_instance is None:
        _capela_instance = Capela()
    return _capela_instance


# Teste do módulo
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("🏛️ Teste Capela")
    print("=" * 40)
    
    capela = obter_capela()
    
    # Entrar
    print("Entrando na Capela (meditação guiada)...")
    status = capela.entrar_capela(duracao_s=10, modo="meditacao_guiada")  # 10s para teste
    print(f"Status: {status}")
    
    # Status
    print("Status atual:")
    print(capela.status_capela())
    
    # Meditar
    print("Meditando:")
    for _ in range(3):
        print(capela.meditar("paz"))
        time.sleep(1)
    
    # Aguardar saída automática
    time.sleep(12)
    
    # Status após saída
    print("Status após saída:")
    print(capela.status_capela())
    
    print("✅ Capela testada (com modos avançados)!")

# --- FIM DO ARQUIVO capela.py ---