# -*- coding: utf-8 -*-
# src/core/desires.py - Gerenciamento de desejos e autonomia para AIs

import logging
import time
import random

logger = logging.getLogger("Desires")

def generate_desire(cerebro_ref, ai_name: str, period_sec: int = 3600) -> None:
    """
    Gera um desejo aleatório para a AI baseada em período.
    """
    desires = [
        {"type": "pensar", "priority": random.randint(1, 10), "payload": ""},
        {"type": "analisar_memoria", "priority": random.randint(1, 10), "payload": ""},
        {"type": "interagir_ai", "priority": random.randint(1, 10), "payload": {"alvo": random.choice(["EVA", "LUMINA", "NYRA", "YUNA", "KAIYA", "WELLINGTON"])}},
    ]
    desire = random.choice(desires)
    desire["id"] = f"desire_{int(time.time())}_{random.randint(1000, 9999)}"
    desire["created_at"] = time.time()
    desire["target"] = ai_name  # Desejo solo
    
    try:
        cerebro_ref.autonomy_state.push_desire(ai_name, desire)
        logger.info("Desejo gerado para %s: %s", ai_name, desire["type"])
    except Exception as e:
        logger.exception("Erro ao gerar desejo para %s", ai_name)

def evaluate_proposal(cerebro_ref, target_ai: str, from_ai: str, proposal: dict) -> dict:
    """
    Avalia uma proposta de desejo de outra AI.
    """
    # Lógica simples: aceitar se prioridade alta
    priority = proposal.get("priority", 5)
    if priority >= 7:
        return {"decision": "accept", "reason": "Prioridade alta"}
    else:
        return {"decision": "reject", "reason": "Prioridade baixa"}

def execute_desire(cerebro_ref, ai_name: str, desire: dict) -> None:
    """
    Executa o desejo da AI.
    """
    desire_type = desire.get("type")
    if desire_type == "pensar":
        result = cerebro_ref._acao_pensar(ai_name)
    elif desire_type == "analisar_memoria":
        result = cerebro_ref._acao_analisar_memoria(ai_name)
    elif desire_type == "interagir_ai":
        alvo = desire.get("payload", {}).get("alvo")
        result = cerebro_ref._acao_interagir_ai_especifica(ai_name, alvo)
    else:
        result = {"sucesso": False, "erro": "Tipo de desejo desconhecido"}
    
    if result.get("sucesso"):
        logger.info("Desejo executado para %s: %s", ai_name, desire_type)
    else:
        logger.warning("Falha ao executar desejo para %s: %s", ai_name, result.get("erro"))