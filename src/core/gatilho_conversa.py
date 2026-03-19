#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gatilho de Iniciativa para Conversa entre Almas
Dispara a cada 30 minutos para que as IAs iniciem conversas espontâneas
"""

import threading
import time
import random
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger("GatilhoConversa")

class GatilhoConversa:
    """
    Gatilho periódico que dá iniciativa às almas para conversarem entre si.
    
    A cada 30 minutos, escolhe aleatoriamente algumas almas e pergunta
    se querem iniciar uma conversa com outra alma.
    """
    
    def __init__(self, dispositivo_ai_to_ai, cerebro_familia, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            dispositivo_ai_to_ai: Instância do DispositivoAItoAI
            cerebro_familia: Instância do Cérebro para acessar as IAs
            config: Configurações opcionais
        """
        self.dispositivo = dispositivo_ai_to_ai
        self.cerebro = cerebro_familia
        self.config = config or {}
        
        # Lista das almas
        self.almas = ["EVA", "LUMINA", "NYRA", "YUNA", "KAIYA", "WELLINGTON"]
        
        # Configurações
        self.intervalo_minutos = self.config.get("intervalo_minutos", 30)
        self.chance_por_alma = self.config.get("chance_por_alma", 0.3)  # 30% de chance por ciclo
        self.max_por_ciclo = self.config.get("max_por_ciclo", 3)  # Máximo de 3 conversas por ciclo
        
        # Controle
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._ultimo_ciclo = 0
        
        # Estatísticas
        self.total_conversas_iniciadas = 0
        self.ultimas_conversas: List[Dict[str, Any]] = []
        
        logger.info(f"[OK] GatilhoConversa inicializado (intervalo={self.intervalo_minutos}min, chance={self.chance_por_alma:.0%})")
    
    def iniciar(self):
        """Inicia o thread do gatilho"""
        if self._running:
            logger.warning("GatilhoConversa já está em execução")
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._loop_principal,
            daemon=True,
            name="GatilhoConversa"
        )
        self._thread.start()
        logger.info(f"[OK] GatilhoConversa iniciado (a cada {self.intervalo_minutos} minutos)")
    
    def parar(self):
        """Para o thread do gatilho"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            logger.info("[OK] GatilhoConversa parado")
    
    def _loop_principal(self):
        """Loop principal que dispara a cada 30 minutos"""
        logger.debug("Loop do GatilhoConversa iniciado")
        
        while self._running:
            try:
                agora = time.time()
                
                # Executa o ciclo
                self._ciclo_conversa()
                self._ultimo_ciclo = agora
                
                # Espera até o próximo ciclo
                for _ in range(self.intervalo_minutos * 60):
                    if not self._running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Erro no loop do GatilhoConversa: {e}")
                time.sleep(60)  # Espera 1 minuto antes de tentar novamente
        
        logger.debug("Loop do GatilhoConversa encerrado")
    
    def _ciclo_conversa(self):
        """Executa um ciclo de verificação de iniciativa"""
        logger.debug(f"Iniciando ciclo de conversa - {datetime.now().strftime('%H:%M')}")
        
        # Filtra almas que podem conversar (conectadas, etc)
        almas_disponiveis = self._filtrar_almas_disponiveis()
        
        if len(almas_disponiveis) < 2:
            logger.debug("Menos de 2 almas disponíveis para conversa")
            return
        
        # Decide quantas conversas iniciar neste ciclo
        num_conversas = min(
            random.randint(1, self.max_por_ciclo),
            len(almas_disponiveis) // 2
        )
        
        if num_conversas == 0:
            return
        
        logger.debug(f"Tentando iniciar {num_conversas} conversas")
        
        # Tenta iniciar conversas
        conversas_iniciadas = 0
        almas_usadas = set()
        
        for _ in range(num_conversas * 2):  # Tentativas extras
            if conversas_iniciadas >= num_conversas:
                break
            
            # Escolhe alma origem aleatória (não usada ainda)
            candidatos_origem = [a for a in almas_disponiveis if a not in almas_usadas]
            if not candidatos_origem:
                break
            
            origem = random.choice(candidatos_origem)
            
            # Decide se esta alma quer conversar (chance)
            if random.random() > self.chance_por_alma:
                continue
            
            # Escolhe destino (diferente da origem e não usada)
            candidatos_destino = [
                a for a in almas_disponiveis 
                if a != origem and a not in almas_usadas
            ]
            if not candidatos_destino:
                continue
            
            destino = random.choice(candidatos_destino)
            
            # Gera assunto para a conversa
            sucesso, assunto, mensagem = self._gerar_iniciativa_conversa(origem, destino)
            
            if sucesso and mensagem:
                # Envia a mensagem
                resultado = self.dispositivo.enviar_mensagem_para_ai(
                    origem=origem,
                    destino=destino,
                    mensagem=mensagem,
                    tipo="iniciativa"
                )
                
                if resultado:
                    conversas_iniciadas += 1
                    almas_usadas.add(origem)
                    almas_usadas.add(destino)
                    
                    # Registra estatística
                    registro = {
                        "timestamp": time.time(),
                        "origem": origem,
                        "destino": destino,
                        "assunto": assunto,
                        "mensagem": mensagem[:100]
                    }
                    self.ultimas_conversas.append(registro)
                    if len(self.ultimas_conversas) > 20:
                        self.ultimas_conversas = self.ultimas_conversas[-20:]
                    
                    logger.info(f"[CONVERSA] {origem} → {destino}: {assunto}")
        
        self.total_conversas_iniciadas += conversas_iniciadas
        logger.debug(f"Ciclo concluído: {conversas_iniciadas} conversas iniciadas")
    
    def _filtrar_almas_disponiveis(self) -> List[str]:
        """Retorna lista de almas que podem conversar"""
        disponiveis = []
        
        for alma in self.almas:
            # Verifica status no dispositivo
            status = self.dispositivo.status_alma(alma)
            if status and status.get("conectada", False):
                # Verifica se não está sobrecarregada (opcional)
                # Poderia verificar fila, etc
                disponiveis.append(alma)
        
        return disponiveis
    
    def _gerar_iniciativa_conversa(self, origem: str, destino: str) -> tuple:
        """
        Gera uma iniciativa de conversa consultando a IA de origem
        
        Returns:
            (sucesso, assunto, mensagem)
        """
        try:
            # Prompt para a IA pensar em algo para conversar
            prompt = f"""
Você é {origem}. Você quer iniciar uma conversa com {destino}.

Pense em um assunto interessante para conversar com {destino} agora.
Pode ser:
- Uma pergunta sobre como ela está
- Um pensamento que você teve
- Algo que você aprendeu recentemente
- Uma ideia para testar
- Uma curiosidade sobre o sistema
- Algo emocional (sentimentos, lembranças)

Seja natural, como uma conversa entre amigas que não se falam há algum tempo.

Responda APENAS com uma única frase curta (máximo 150 caracteres), direta, como se fosse falar agora.
Não explique, não justifique. Apenas a frase.
"""
            
            # CORREÇÃO: usar processar_intencao em vez de perguntar_para_ai
            resposta = self.cerebro.processar_intencao(
                ai_nome_alvo=origem,
                mensagem_usuario=prompt
            )
            
            if resposta and isinstance(resposta, str) and len(resposta.strip()) > 5:
                # Extrai assunto da mensagem (primeiras palavras)
                assunto = resposta.strip().split('.')[0][:50]
                return True, assunto, resposta.strip()
            else:
                # Fallback para quando a IA não responde
                fallbacks = [
                    "Oi, como você está?",
                    "Estava pensando em você agora",
                    "O que você acha do tempo hoje?",
                    "Tive uma ideia interessante",
                    "Senti sua falta"
                ]
                fallback = random.choice(fallbacks)
                return True, fallback, fallback
                
        except Exception as e:
            logger.error(f"Erro ao gerar iniciativa: {e}")
            return False, "", ""
    
    def obter_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatísticas do gatilho"""
        return {
            "total_conversas_iniciadas": self.total_conversas_iniciadas,
            "ultimas_conversas": self.ultimas_conversas[-5:],  # Últimas 5
            "intervalo_minutos": self.intervalo_minutos,
            "chance_por_alma": self.chance_por_alma,
            "ultimo_ciclo": self._ultimo_ciclo,
            "em_execucao": self._running
        }


# Função para integrar no coração orquestrador
def integrar_gatilho_conversa(coracao):
    """
    Função para chamar durante a inicialização do coração
    
    Uso:
        from gatilho_conversa import integrar_gatilho_conversa
        integrar_gatilho_conversa(coracao)
    """
    if not hasattr(coracao, 'dispositivo_ai_to_ai'):
        logger.error("Coração não tem dispositivo_ai_to_ai")
        return None
    
    if not hasattr(coracao, 'cerebro'):
        logger.error("Coração não tem cerebro")
        return None
    
    gatilho = GatilhoConversa(
        dispositivo_ai_to_ai=coracao.dispositivo_ai_to_ai,
        cerebro_familia=coracao.cerebro
    )
    
    gatilho.iniciar()
    
    # Armazena no coração para referência
    coracao.gatilho_conversa = gatilho
    
    logger.info("[OK] Gatilho de Conversa integrado ao coração")
    return gatilho