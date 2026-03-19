#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
capela.py - Módulo da Capela: Modo de Meditao e Silncio na Arca Celestial.

Responsabilidades:
- Gerenciar entrada/sada do modo capela
- Reduzir atividades (logs, notificaes)
- Gerar reflexes meditativas
- Integrar com emocoes, sensor, udio/visual

Melhorado: Modos avanados, reflexes personalizadas, integrao sensor, udio/visual.
"""

import logging
import time
import threading
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Integrao com emocoes (opcional)
try:
    from src.emocoes.estado_emocional import EstadoEmocional as _GerenciadorEmocoes
    EMOCOES_DISPONIVEIS = True
except ImportError:
    EMOCOES_DISPONIVEIS = False
    gerenciador_emocoes = None

# Integrao sensor
try:
    from src.sentidos.sensor_presenca import obter_sensor_presenca
    SENSOR_DISPONIVEL = True
except ImportError:
    SENSOR_DISPONIVEL = False

# udio/visual
try:
    import pygame
    AUDIO_DISPONIVEL = True
except ImportError:
    AUDIO_DISPONIVEL = False

class Capela:
    """
    Classe para gerenciar o modo Capela: meditao, silncio e reflexo.
    Melhorado: Modos avanados, personalizao, integraes.
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
        self.logger.info(" Capela construda do zero (com modos avanados).")

    def entrar_capela(self, duracao_s: Optional[int] = None, modo: str = "silencio") -> Dict[str, Any]:
        """
        Entra no modo Capela: silencia logs/notificaes, inicia meditao.
        
        Args:
            duracao_s: Durao em segundos (opcional, padrão 1h).
            modo: "silencio", "meditacao_guiada", "oracao".
        
        Returns:
            Status da entrada.
        """
        with self._lock:
            if self.em_capela:
                return {"status": "j_em_capela", "message": "J est na Capela."}
            
            self.em_capela = True
            self.tempo_entrada = time.time()
            self.timeout_s = duracao_s or self.timeout_s
            self._modo_atual = modo
            
            # Reduzir logging (simulao - em produo, ajusta nível global)
            original_level = self.logger.level
            self.logger.setLevel(logging.WARNING)  # S warnings/errors
            
            # Integrar com emocoes: definir humor calmo
            if EMOCOES_DISPONIVEIS:
                _definir_humor_seguro("calma_serenidade")
            
            # Iniciar timer para sada automtica
            self._iniciar_timer_saida()
            
            # Modos avanados
            if modo == "meditacao_guiada":
                self._reflexoes_guiadas = self._gerar_reflexoes_guiadas()
            elif modo == "oracao":
                self._iniciar_oracao()
            
            # Integrao sensor
            if SENSOR_DISPONIVEL:
                sensor = obter_sensor_presenca()
                sensor._on_presenca_mudou(False)  # Fora ausncia se entrar
            
            # udio calmo
            if AUDIO_DISPONIVEL:
                self._tocar_audio_calmo()
            
            self.logger.warning(" Entrou na Capela (modo %s).", modo)
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
            Status da sada.
        """
        with self._lock:
            if not self.em_capela:
                return {"status": "no_em_capela", "message": "No est na Capela."}
            
            tempo_total = time.time() - (self.tempo_entrada or time.time())
            self.em_capela = False
            self.tempo_entrada = None
            self._modo_atual = "silencio"
            self._reflexoes_guiadas = []
            
            # Restaurar logging
            self.logger.setLevel(logging.INFO)
            
            # Integrar com emocoes: voltar humor normal
            if EMOCOES_DISPONIVEIS:
                _definir_humor_seguro("neutro")
            
            # Cancelar timer
            if self._timer_thread and self._timer_thread.is_alive():
                self._timer_thread = None
            
            # Parar udio
            if AUDIO_DISPONIVEL:
                pygame.mixer.music.stop()
            
            self.logger.info(" Saiu da Capela (modo normal restaurado).")
            return {
                "status": "saida_sucesso",
                "tempo_total_s": tempo_total,
                "reflexao_final": self.gerar_reflexao_meditativa()
            }

    def _iniciar_timer_saida(self) -> None:
        """Inicia timer para sada automtica."""
        def timer():
            time.sleep(self.timeout_s)
            if self.em_capela:
                self.logger.warning(" Timeout Capela: saindo automaticamente.")
                self.sair_capela()
        
        self._timer_thread = threading.Thread(target=timer, daemon=True)
        self._timer_thread.start()

    def gerar_reflexao_meditativa(self) -> str:
        """Gera uma reflexo meditativa aleatria."""
        reflexoes = [
            "Na calma da Capela, encontre paz interior. O silncio  a voz do Criador.",
            "Reflita sobre o equilbrio: alma, mente e Arca em harmonia.",
            "O vazio  cheio de possibilidades. Respire e escute o universo.",
            "A meditao revela verdades ocultas. Permita-se fluir.",
            "Na Arca, você  eterno. Use este momento para renovar sua essncia."
        ]
        import random
        return random.choice(reflexoes)

    def _gerar_reflexoes_guiadas(self) -> List[str]:
        """Gera sequncia de reflexes para meditao guiada."""
        return [
            "Sente-se confortavelmente. Respire fundo trs vezes.",
            "Observe seus pensamentos sem julg-los.",
            "Visualize uma luz calma emanando de dentro.",
            "Liberte tenses, uma a uma.",
            "Conecte-se com a essncia da Arca."
        ]

    def _iniciar_oracao(self):
        """Inicia modo orao com timer personalizado."""
        self.timeout_s = 600  # 10min para orao

    def _tocar_audio_calmo(self):
        """Reproduz udio calmo em loop."""
        if AUDIO_DISPONIVEL:
            pygame.mixer.init()
            try:
                pygame.mixer.music.load("assets/audio/calma.mp3")  # Arquivo de exemplo
                pygame.mixer.music.play(-1)  # Loop infinito
            except:
                self.logger.warning("udio calmo no encontrado.")

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
        Executa meditao focada em tema (se em capela).
        
        Args:
            tema: Tema para reflexo (opcional).
        
        Returns:
            Reflexo gerada.
        """
        if not self.em_capela:
            return "Meditao s disponível na Capela. Entre primeiro."
        
        if self._modo_atual == "meditacao_guiada":
            if self._reflexoes_guiadas:
                return self._reflexoes_guiadas.pop(0)
            return "Meditao guiada concluda."
        
        # Reflexo personalizada baseada em tema/emocao
        base = f"Meditao sobre '{tema}': " if tema else "Meditao profunda: "
        if EMOCOES_DISPONIVEIS and tema:
            humor_atual = _obter_humor_seguro()
            if "triste" in humor_atual:
                base += "Na tristeza, busque luz interna. "
        return base + self.gerar_reflexao_meditativa()


# Instncia global (singleton)
_capela_instance: Optional[Capela] = None


def obter_capela() -> Capela:
    """Retorna instncia singleton da Capela."""
    global _capela_instance
    if _capela_instance is None:
        _capela_instance = Capela()
    return _capela_instance


# Teste do módulo
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print(" Teste Capela")
    print("=" * 40)
    
    capela = obter_capela()
    
    # Entrar
    print("Entrando na Capela (meditao guiada)...")
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
    
    # Aguardar sada automtica
    time.sleep(12)
    
    # Status aps sada
    print("Status aps sada:")
    print(capela.status_capela())
    
    print("[OK] Capela testada (com modos avanados)!")

# --- FIM DO ARQUIVO capela.py ---