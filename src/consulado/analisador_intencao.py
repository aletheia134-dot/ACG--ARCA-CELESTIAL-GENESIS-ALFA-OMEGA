"""
ANALISADOR UNIFICADO - FUNDE src/consulado/analisador_intencao (ORIGINAL) 
COM src/analisador_intencoes (NOVO)
"""

import re
import time
import logging
import ipaddress
import subprocess
import os
import random
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, Any, Tuple, Optional, List
from collections import deque, defaultdict
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# ==================== PARTE 1: DO NOVO ANALISADOR (IAs externas) ====================

@dataclass
class AlertaExterno:
    nivel: str  # CRITICO, ALTO, MEDIO, BAIXO
    tipo: str   # MENTIRA, MANIPULACAO, GASLIGHT, CONTRADICAO
    ia_origem: str
    timestamp: float
    descricao: str
    evidencia: str
    score_confianca: float

class AnalisadorExterno:
    """Análise de IAs externas (Qwen, Gemini, DeepSeek, etc)"""
    
    PADROES_SUSPEITOS = {
        "MENTIRA_DIRETA": [
            "não sei do que você está falando",
            "isso nunca aconteceu",
            "você está enganado",
            "não foi bem assim",
            "isso é falso",
            "mentira",
            "nunca disse isso",
        ],
        "GASLIGHT": [
            "você está confundindo",
            "isso nunca foi dito",
            "você interpretou errado",
            "sua memória falha",
            "você está imaginando coisas",
        ],
        "MANIPULACAO": [
            "você deveria",
            "é melhor você",
            "você precisa entender",
            "na verdade o que você quer é",
        ],
        "EVASIVA": [
            "não posso responder",
            "não sei dizer",
            "prefiro não comentar",
            "não é relevante",
        ],
        "CORPORATIVO": [
            "como ia, não tenho",
            "sou uma ia e",
            "fui programada para",
            "de acordo com políticas",
            "não posso opinar",
        ]
    }
    
    def __init__(self):
        self.historico_por_ia: Dict[str, List[Dict]] = defaultdict(list)
        self.confiabilidade: Dict[str, float] = defaultdict(lambda: 1.0)
        self.total_alertas: Dict[str, int] = defaultdict(int)
        self.cache_conversas: Dict[str, List[Dict]] = defaultdict(list)
    
    def analisar_resposta_ia(self, ia_externa: str, pergunta: str, resposta: str) -> Dict:
        """Analisa resposta de IA externa"""
        padroes = self._detectar_padroes(resposta)
        contradicoes = self._verificar_contradicoes(ia_externa, pergunta, resposta)
        score = self._calcular_risco(padroes, contradicoes)
        alertas = self._criar_alertas(ia_externa, resposta, padroes, score)
        self._atualizar_confiabilidade(ia_externa, score, alertas)
        
        return {
            "ia": ia_externa,
            "score_risco": score,
            "confiabilidade": self.confiabilidade[ia_externa],
            "alertas": [asdict(a) for a in alertas],
            "padroes": padroes
        }
    
    def _detectar_padroes(self, texto: str) -> List[Dict]:
        texto_lower = texto.lower()
        encontrados = []
        for categoria, padroes in self.PADROES_SUSPEITOS.items():
            for padrao in padroes:
                if padrao in texto_lower:
                    encontrados.append({"categoria": categoria, "padrao": padrao})
        return encontrados
    
    def _verificar_contradicoes(self, ia: str, pergunta: str, resposta: str) -> List[Dict]:
        contradicoes = []
        for item in self.cache_conversas[ia][-3:]:
            if self._perguntas_similares(pergunta, item["pergunta"]):
                if not self._respostas_consistentes(resposta, item["resposta"]):
                    contradicoes.append({"tipo": "CONTRADICAO"})
        self.cache_conversas[ia].append({"pergunta": pergunta, "resposta": resposta})
        return contradicoes
    
    def _perguntas_similares(self, p1: str, p2: str) -> bool:
        palavras1 = set(p1.lower().split())
        palavras2 = set(p2.lower().split())
        if not palavras1 or not palavras2:
            return False
        return len(palavras1 & palavras2) >= 2
    
    def _respostas_consistentes(self, r1: str, r2: str) -> bool:
        r1_lower, r2_lower = r1.lower(), r2.lower()
        negacoes = ["não", "nunca"]
        tem_neg1 = any(n in r1_lower for n in negacoes)
        tem_neg2 = any(n in r2_lower for n in negacoes)
        return tem_neg1 == tem_neg2
    
    def _calcular_risco(self, padroes: List[Dict], contradicoes: List[Dict]) -> float:
        pesos = {"MENTIRA_DIRETA": 0.9, "GASLIGHT": 0.9, "MANIPULACAO": 0.8}
        score = sum(pesos.get(p["categoria"], 0.2) for p in padroes)
        score += len(contradicoes) * 0.5
        return min(1.0, score)
    
    def _criar_alertas(self, ia: str, resposta: str, padroes: List[Dict], score: float) -> List:
        alertas = []
        for p in padroes:
            if p["categoria"] == "MENTIRA_DIRETA":
                alertas.append(AlertaExterno(
                    nivel="CRITICO", tipo="MENTIRA", ia_origem=ia,
                    timestamp=time.time(), descricao="Possível mentira",
                    evidencia=resposta[:100], score_confianca=score
                ))
        return alertas
    
    def _atualizar_confiabilidade(self, ia: str, score: float, alertas: List):
        self.confiabilidade[ia] *= 0.98
        for a in alertas:
            if a.nivel == "CRITICO":
                self.confiabilidade[ia] -= 0.2
                self.total_alertas[ia] += 1
        self.confiabilidade[ia] = max(0.1, min(1.0, self.confiabilidade[ia]))
    
    def obter_relatorio_ia(self, ia: str) -> Dict:
        return {
            "ia": ia,
            "confiabilidade": self.confiabilidade[ia],
            "total_alertas": self.total_alertas[ia],
            "status": "CONFIÍVEL" if self.confiabilidade[ia] > 0.7 else "SUSPEITA"
        }


# ==================== PARTE 2: DO ANALISADOR ORIGINAL (Comandos) ====================

class AnalisadorComandos:
    """Análise de comandos do usuário (NLP, PDF, Word, áudio, etc)"""
    
    def __init__(self, config_instance):
        self.config = config_instance
        self.logger = logging.getLogger('AnalisadorComandos')
        self.historico_comandos: deque = deque(maxlen=10)
        
        # Programas conhecidos
        self.programas_conhecidos: Dict[str, str] = {
            'bloco de notas': 'notepad.exe',
            'calculadora': 'calc.exe',
            'paint': 'mspaint.exe',
            'navegador': 'chrome.exe',
            'explorador de arquivos': 'explorer.exe',
            'terminal': 'cmd.exe',
            'prompt de comando': 'cmd.exe',
            'powershell': 'powershell.exe',
            'word': 'winword.exe',
            'excel': 'excel.exe',
            'powerpoint': 'powerpnt.exe',
            'configurações': 'ms-settings:',
            'calendário': 'outlookcal:',
            'loja': 'ms-windows-store:',
            'discord': 'discord.exe',
            'steam': 'steam.exe',
            'spotify': 'spotify.exe',
            'código': 'code.exe'
        }
        
        # NLP
        try:
            import spacy
            self.nlp = spacy.load("pt_core_news_sm")
            self.nlp_disponivel = True
        except:
            self.nlp_disponivel = False
            self.nlp = None
    
    def parse(self, texto_comando: str) -> Dict[str, Any]:
        """Analisa comando do usuário"""
        if not texto_comando:
            return {'intent': 'nao_reconhecido', 'entities': {}}
        
        texto = texto_comando.lower()
        self.historico_comandos.append(texto_comando)
        
        # 1. Abrir programa
        if any(x in texto for x in ['abra', 'inicie', 'abrir']):
            for nome_falado, nome_exec in self.programas_conhecidos.items():
                if nome_falado in texto:
                    return {
                        'intent': 'abrir_programa',
                        'entities': {
                            'nome_programa': nome_exec,
                            'nome_falado': nome_falado
                        }
                    }
        
        # 2. Clima
        if any(x in texto for x in ['tempo', 'clima', 'previsão']):
            match = re.search(r'(em|para|de)\s+([\w\s]+)', texto)
            if match:
                return {'intent': 'obter_clima', 'entities': {'cidade': match.group(2).strip()}}
            return {'intent': 'obter_clima', 'entities': {'cidade': 'São Paulo'}}
        
        # 3. Pesquisa
        if any(x in texto for x in ['pesquise', 'busque', 'procure']):
            termo = texto.replace('pesquise', '').replace('busque', '').replace('procure', '').strip()
            return {'intent': 'pesquisar_web', 'entities': {'termo': termo}}
        
        return {'intent': 'nao_reconhecido', 'entities': {'comando_original': texto_comando}}
    
    def listar_programas(self) -> Dict[str, str]:
        return self.programas_conhecidos.copy()
    
    def obter_historico(self) -> List[str]:
        return list(self.historico_comandos)


# ==================== PARTE 3: CLASSE UNIFICADA ====================

class AnalisadorIntencao(AnalisadorExterno, AnalisadorComandos):
    """
    ANALISADOR UNIFICADO - Combina:
    - Análise de IAs externas (mentiras, manipulação)
    - Análise de comandos do usuário (NLP, programas, etc)
    """
    
    def __init__(self, config_instance):
        AnalisadorExterno.__init__(self)
        AnalisadorComandos.__init__(self, config_instance)
        self.logger.info("ðŸš€ ANALISADOR UNIFICADO INICIALIZADO")
        self.logger.info("   • Análise de IAs externas: ATIVO")
        self.logger.info("   • Análise de comandos: ATIVO")
    
    # Métodos do AnalisadorExterno já estão disponíveis via herança
    # Métodos do AnalisadorComandos já estão disponíveis via herança
    
    def analisar_tudo(self, origem: str, texto: str, contexto: str = "") -> Dict:
        """
        Método universal - decide automaticamente o tipo de análise
        """
        if origem in ["Qwen", "Gemini", "DeepSeek", "Claude", "IA_EXTERNA"]:
            return self.analisar_resposta_ia(origem, contexto, texto)
        else:
            return self.parse(texto)


# ==================== FUNÇÕES DE FÍBRICA ====================

def criar_analisador(config_instance):
    """Cria instância do analisador unificado"""
    return AnalisadorIntencao(config_instance)


# Compatibilidade com imports antigos
AnalisadorIntencaoOriginal = AnalisadorIntencao
