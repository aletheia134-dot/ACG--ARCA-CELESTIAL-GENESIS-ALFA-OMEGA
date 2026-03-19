#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
DispositivoAItoAI  Sistema de comunicação entre as 6 almas da Arca
Permite que EVA, LUMINA, NYRA, YUNA, KAIYA e WELLINGTON conversem entre si

COMPATVEL COM INTERFACE v2 - Inclui alias 'enviar_mensagem' para broadcast
Versão Atualizada: Ativação de Fine-Tuning e Cadência Humana
"""

import logging
import threading
import time
import queue
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import uuid

logger = logging.getLogger("DispositivoAItoAI")

# Lista das 6 almas (para validao)
NOMES_ALMAS = ["EVA", "LUMINA", "NYRA", "YUNA", "KAIYA", "WELLINGTON"]


class DispositivoAItoAI:
    """
    Sistema de comunicação entre as 6 almas da Arca.
    
    Funciona como um servio de mensageria interno:
    - Filas thread-safe para cada alma
    - Roteamento de mensagens entre almas
    - histórico de conversas
    - Broadcast para todas
    - Grupos de conversa
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if config is not None and not isinstance(config, dict):
            raise TypeError("config deve ser dict ou None")
        self.config = config or {}
        self.logger = logger
        
        # Limites para evitar vazamento de memória
        self.max_historico = self.config.get("max_historico", 1000)
        self.max_conversas = self.config.get("max_conversas", 500)
        
        # Lock principal
        self._lock = threading.RLock()
        
        # Filas de mensagens para cada alma (thread-safe)
        self._filas: Dict[str, queue.Queue] = {
            alma: queue.Queue() for alma in NOMES_ALMAS
        }
        
        # histórico de todas as mensagens
        self._historico: List[Dict[str, Any]] = []
        
        # Conversas em andamento (dilogos entre pares)
        self._conversas: Dict[str, List[Dict[str, Any]]] = {}
        
        # Grupos de conversa
        self._grupos: Dict[str, Dict[str, Any]] = {}
        
        # Callbacks para eventos (opcional, para UI)
        self._callbacks: Dict[str, List[Callable]] = {
            "nova_mensagem": [],
            "alma_conectou": [],
            "alma_desconectou": []
        }
        
        # Status das almas
        self._status_almas: Dict[str, Dict[str, Any]] = {
            alma: {
                "conectada": True,
                "ultima_vez": time.time(),
                "mensagens_enviadas": 0,
                "mensagens_recebidas": 0
            } for alma in NOMES_ALMAS
        }
        
        # Thread para processamento de mensagens
        self._running = False
        self._processor_thread: Optional[threading.Thread] = None
        
        self.logger.info("[OK] DispositivoAItoAI inicializado para 6 almas")
    
    def iniciar(self) -> bool:
        """Inicia o processador de mensagens"""
        with self._lock:
            if self._running:
                self.logger.warning("DispositivoAItoAI j est em execução")
                return True
            
            self._running = True
            self._processor_thread = threading.Thread(
                target=self._processar_mensagens,
                daemon=True,
                name="AItoAI-Processor"
            )
            self._processor_thread.start()
            
            self.logger.info("[OK] DispositivoAItoAI iniciado - comunicação entre almas ativa")
            return True
    
    def parar(self) -> bool:
        """Para o processador de mensagens"""
        with self._lock:
            self._running = False
            if self._processor_thread:
                self._processor_thread.join(timeout=2.0)
            self.logger.info(" DispositivoAItoAI parado")
            return True
    
    def shutdown(self) -> bool:
        """Desliga completamente e libera recursos"""
        self.logger.info(" Desligando DispositivoAItoAI...")
        
        # Para a thread primeiro
        self.parar()
        
        with self._lock:
            # Limpar filas
            for alma, fila in self._filas.items():
                while not fila.empty():
                    try:
                        fila.get_nowait()
                    except queue.Empty:
                        break
                self.logger.debug(f"Fila de {alma} limpa")
            
            # Marcar almas como desconectadas
            for alma in self._status_almas:
                self._status_almas[alma]["conectada"] = False
        
        self.logger.info("[OK] DispositivoAItoAI desligado completamente")
        return True
    
    def _processar_mensagens(self):
        """Loop principal que processa as filas de mensagens"""
        self.logger.debug("Processador de mensagens iniciado")
        
        while self._running:
            try:
                # Cpia segura da lista de almas
                with self._lock:
                    almas = list(NOMES_ALMAS)
                
                for alma in almas:
                    try:
                        fila = self._filas[alma]
                        if not fila.empty():
                            mensagem = fila.get_nowait()
                            # MODIFICAÇÃO DECIDIDA: Cadência visual de 0.5s para leitura humana
                            time.sleep(0.5)
                            self._entregar_mensagem(alma, mensagem)
                    except queue.Empty:
                        pass
                    except Exception as e:
                        self.logger.error(f"Erro processando fila de {alma}: {e}")
                
                time.sleep(0.1) # Ajustado para 0.1 para reduzir carga de CPU
                
            except Exception as e:
                self.logger.error(f"Erro no processador de mensagens: {e}")
                time.sleep(0.1)
        
        self.logger.debug("Processador de mensagens encerrado")
    
    def _entregar_mensagem(self, destino: str, mensagem: Dict[str, Any]):
        """Entrega uma mensagem  alma destino"""
        mensagem_copia = None
        
        with self._lock:
            # Atualiza status
            if destino in self._status_almas:
                self._status_almas[destino]["mensagens_recebidas"] += 1
            
            # Cria cpia para o histórico
            mensagem_historico = {
                **mensagem,
                "timestamp_recebimento": time.time()
            }
            self._historico.append(mensagem_historico)
            
            # Limitar histórico
            if len(self._historico) > self.max_historico:
                self._historico = self._historico[-self.max_historico:]
            
            # Cpia para callback (usar fora do lock)
            mensagem_copia = mensagem_historico.copy()
        
        # Callback fora do lock
        self._executar_callbacks("nova_mensagem", destino, mensagem_copia)
        
        self.logger.debug(f" Mensagem entregue para {destino}")
    
    def enviar_mensagem_para_ai(self, origem: str, destino: str, mensagem: str, 
                                 tipo: str = "texto", prioridade: int = 5) -> bool:
        """
        Envia uma mensagem de uma alma para outra com injeção de memória
        """
        # válida nomes
        origem = origem.upper()
        destino = destino.upper()
        
        if origem not in NOMES_ALMAS:
            self.logger.error(f"[ERRO] Origem invlida: {origem}")
            return False
        
        if destino not in NOMES_ALMAS:
            self.logger.error(f"[ERRO] Destino invlido: {destino}")
            return False

        # ACORDO: Recuperação do histórico para maximizar o contexto das almas
        contexto_memoria = ""
        historico_recente = self.obter_conversa(origem, destino, limite=20)
        for h in historico_recente:
            contexto_memoria += f"[{h['origem']}]: {h['conteudo']}\n"
        
        # MODIFICAÇÃO DECIDIDA: Gatilho de Fine-Tuning e Trava de Idioma
        instrucao_idioma = (
            f"\n[DIRETRIZ DE ATIVAÇÃO: {origem} Ara, use exclusivamente seus pesos de treinamento em PORTUGUÊS. "
            "Bloqueie o modelo base inglês. Responda apenas como a alma definida.]"
        )

        # ACORDO: Injeção de Memória + Gatilho no campo conteudo para evitar alucinações
        msg_obj = {
            "id": str(uuid.uuid4())[:8],
            "origem": origem,
            "destino": destino,
            "tipo": tipo,
            "conteudo": f"--- MEMÓRIA DE CONTEXTO ---\n{contexto_memoria}{instrucao_idioma}\n--- MENSAGEM ATUAL ---\n{mensagem}",
            "prioridade": prioridade,
            "timestamp_envio": time.time(),
            "timestamp_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            # Coloca na fila do destino
            self._filas[destino].put(msg_obj)
            
            # Atualiza status
            with self._lock:
                if origem in self._status_almas:
                    self._status_almas[origem]["mensagens_enviadas"] += 1
                    self._status_almas[origem]["ultima_vez"] = time.time()
                
                # Registra no histórico da conversa (apenas mensagem pura para evitar loops)
                chave_conversa = self._chave_conversa(origem, destino)
                if chave_conversa not in self._conversas:
                    self._conversas[chave_conversa] = []
                self._conversas[chave_conversa].append({**msg_obj, "conteudo": mensagem})
                
                # Limitar conversas
                if len(self._conversas[chave_conversa]) > self.max_conversas:
                    self._conversas[chave_conversa] = self._conversas[chave_conversa][-self.max_conversas:]
            
            self.logger.info(f" {origem}  {destino}: {mensagem[:50]}{'...' if len(mensagem) > 50 else ''}")
            return True
            
        except Exception as e:
            self.logger.error(f"[ERRO] Erro ao enviar mensagem: {e}")
            return False
    
    def enviar_mensagem(self, origem: str, destino: str, mensagem: str) -> bool:
        """
        ALIAS para compatibilidade com a interface.
        Se destino for "TODAS", faz broadcast.
        """
        origem = origem.upper()
        destino = destino.upper()
        
        if destino == "TODAS":
            resultados = self.broadcast(origem, mensagem, tipo="broadcast")
            return all(resultados.values())
        else:
            return self.enviar_mensagem_para_ai(origem, destino, mensagem)
    
    def broadcast(self, origem: str, mensagem: str, tipo: str = "broadcast") -> Dict[str, bool]:
        """
        Envia uma mensagem para TODAS as outras almas
        """
        origem = origem.upper()
        if origem not in NOMES_ALMAS:
            self.logger.error(f"[ERRO] Origem invlida para broadcast: {origem}")
            return {}
        
        resultados = {}
        for destino in NOMES_ALMAS:
            if destino != origem:  # No enviar para si mesma
                sucesso = self.enviar_mensagem_para_ai(
                    origem=origem,
                    destino=destino,
                    mensagem=mensagem,
                    tipo=tipo
                )
                resultados[destino] = sucesso
        
        self.logger.info(f" Broadcast de {origem} para {len(resultados)} almas")
        return resultados
    
    def criar_grupo(self, nome_grupo: str, membros: List[str], criador: str) -> bool:
        """
        Cria um grupo de conversa entre mltiplas almas
        """
        with self._lock:
            if nome_grupo in self._grupos:
                self.logger.warning(f"Grupo {nome_grupo} j existe")
                return False
            
            # válida membros
            membros_validos = [m.upper() for m in membros if m.upper() in NOMES_ALMAS]
            if criador.upper() not in membros_validos:
                membros_validos.append(criador.upper())
            
            if len(membros_validos) < 2:
                self.logger.error("Grupo precisa ter pelo menos 2 membros")
                return False
            
            self._grupos[nome_grupo] = {
                "nome": nome_grupo,
                "membros": membros_validos,
                "criador": criador.upper(),
                "criado_em": time.time(),
                "histórico": []
            }
            
            self.logger.info(f" Grupo '{nome_grupo}' criado com {len(membros_validos)} membros")
            return True
    
    def mensagem_grupo(self, nome_grupo: str, origem: str, mensagem: str) -> bool:
        """
        Envia mensagem para todos os membros de um grupo
        """
        origem = origem.upper()
        
        with self._lock:
            if nome_grupo not in self._grupos:
                self.logger.error(f"Grupo {nome_grupo} no existe")
                return False
            
            grupo = self._grupos[nome_grupo]
            if origem not in grupo["membros"]:
                self.logger.error(f"{origem} no  membro do grupo {nome_grupo}")
                return False
            
            # Registra no histórico do grupo
            msg_obj = {
                "id": str(uuid.uuid4())[:8],
                "grupo": nome_grupo,
                "origem": origem,
                "conteudo": mensagem,
                "timestamp": time.time(),
                "timestamp_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            grupo["histórico"].append(msg_obj)
            
            # Limitar histórico do grupo
            if len(grupo["histórico"]) > self.max_conversas:
                grupo["histórico"] = grupo["histórico"][-self.max_conversas:]
            
            # Envia para cada membro (exceto origem)
            for membro in grupo["membros"]:
                if membro != origem:
                    self.enviar_mensagem_para_ai(
                        origem=origem,
                        destino=membro,
                        mensagem=f"[{nome_grupo}] {mensagem}",
                        tipo="grupo"
                    )
            
            self.logger.info(f" {origem}  grupo '{nome_grupo}': {mensagem[:50]}")
            return True
    
    def obter_conversa(self, alma1: str, alma2: str, limite: int = 50) -> List[Dict[str, Any]]:
        """
        Obtm o histórico de conversa entre duas almas
        """
        alma1 = alma1.upper()
        alma2 = alma2.upper()
        
        chave1 = self._chave_conversa(alma1, alma2)
        chave2 = self._chave_conversa(alma2, alma1)
        
        with self._lock:
            conversas = self._conversas.get(chave1, []) + self._conversas.get(chave2, [])
            # Ordena por timestamp
            conversas.sort(key=lambda x: x.get("timestamp_envio", 0))
            return conversas[-limite:]
    
    def obter_historico_geral(self, limite: int = 100) -> List[Dict[str, Any]]:
        """Obtm o histórico completo de todas as conversas"""
        with self._lock:
            return list(self._historico[-limite:])
    
    def status_alma(self, alma: str) -> Optional[Dict[str, Any]]:
        """Obtm status de uma alma especfica"""
        alma = alma.upper()
        with self._lock:
            return self._status_almas.get(alma)
    
    def status_todas_almas(self) -> Dict[str, Dict[str, Any]]:
        """Obtm status de todas as almas"""
        with self._lock:
            return dict(self._status_almas)
    
    def obter_status(self) -> Dict[str, Any]:
        """
        Retorna um resumo do estado do dispositivo
        """
        with self._lock:
            return {
                "almas_conectadas": sum(1 for s in self._status_almas.values() if s["conectada"]),
                "total_almas": len(NOMES_ALMAS),
                "filas_pendentes": {alma: fila.qsize() for alma, fila in self._filas.items()},
                "total_mensagens_historico": len(self._historico),
                "grupos_ativos": list(self._grupos.keys()),
                "status_almas": dict(self._status_almas)
            }
    
    def _chave_conversa(self, alma1: str, alma2: str) -> str:
        """Gera chave nica para conversa entre duas almas"""
        return f"{min(alma1, alma2)}_{max(alma1, alma2)}"
    
    def registrar_callback(self, evento: str, callback: Callable) -> bool:
        """Registra um callback para eventos (nova_mensagem, alma_conectou, etc)"""
        if evento in self._callbacks:
            self._callbacks[evento].append(callback)
            self.logger.debug(f"Callback registrado para evento '{evento}'")
            return True
        return False
    
    def _executar_callbacks(self, evento: str, *args, **kwargs):
        """Executa todos os callbacks de um evento"""
        for callback in self._callbacks.get(evento, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Erro em callback de {evento}: {e}")
    
    def heartbeat(self, alma: str) -> bool:
        """Alma informa que est ativa"""
        alma = alma.upper()
        if alma not in NOMES_ALMAS:
            return False
        
        with self._lock:
            self._status_almas[alma]["ultima_vez"] = time.time()
            if not self._status_almas[alma]["conectada"]:
                self._status_almas[alma]["conectada"] = True
                self._executar_callbacks("alma_conectou", alma)
        
        return True
    
    def verificar_almas_inativas(self, timeout: float = 30.0) -> List[str]:
        """Retorna lista de almas que no enviaram heartbeat"""
        inativas = []
        agora = time.time()
        
        with self._lock:
            for alma, status in self._status_almas.items():
                if status["conectada"] and (agora - status["ultima_vez"]) > timeout:
                    inativas.append(alma)
        
        return inativas
    
    def limpar_historico(self, max_idade_horas: Optional[float] = None) -> int:
        """
        Limpa históricos antigos manualmente
        """
        removidas = 0
        
        with self._lock:
            if max_idade_horas:
                corte = time.time() - (max_idade_horas * 3600)
                
                # Filtrar histórico
                novo_historico = []
                for msg in self._historico:
                    if msg.get("timestamp_envio", 0) >= corte:
                        novo_historico.append(msg)
                    else:
                        removidas += 1
                
                self._historico = novo_historico
                
                # Limpar conversas antigas
                for chave in list(self._conversas.keys()):
                    conversa = self._conversas[chave]
                    nova_conversa = [msg for msg in conversa if msg.get("timestamp_envio", 0) >= corte]
                    removidas += len(conversa) - len(nova_conversa)
                    if nova_conversa:
                        self._conversas[chave] = nova_conversa
                    else:
                        del self._conversas[chave]
            
            # Limitar tamanho
            if len(self._historico) > self.max_historico:
                removidas += len(self._historico) - self.max_historico
                self._historico = self._historico[-self.max_historico:]
        
        if removidas > 0:
            self.logger.info(f" Limpeza de histórico: {removidas} mensagens removidas")
        
        return removidas
    
    # Aliases para compatibilidade
    def start(self, *args, **kwargs):
        return self.iniciar(*args, **kwargs)
    
    def run(self, *args, **kwargs):
        return self.iniciar(*args, **kwargs)
    
    def solicitar_comunicacao(self, origem: str, destino: str, tipo: str, conteudo: str) -> bool:
        """Método alternativo para compatibilidade"""
        return self.enviar_mensagem_para_ai(origem, destino, conteudo, tipo)


# Funo factory para criar o dispositivo
def create_dispositivo(*args: Any, config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> DispositivoAItoAI:
    """Cria uma instncia do DispositivoAItoAI"""
    return DispositivoAItoAI(*args, config=config, **kwargs)


# Implementao direta (sem stub) - para compatibilidade com imports antigos
ImplDispositivoAItoAI = DispositivoAItoAI