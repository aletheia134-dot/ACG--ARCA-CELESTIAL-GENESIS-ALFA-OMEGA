# src/emocoes/dicionario_desejos.py

from typing import Dict, List, Any, Optional
import json
import random
from pathlib import Path

class DicionarioDesejos:
    """
    Central de desejos para todas as almas.
    Permite personalização por alma e aprendizado por feedback.
    """
    
    def __init__(self, caminho_base: Path):
        self.caminho = caminho_base / "dicionario_desejos.json"
        self.desejos: Dict[str, List[Dict[str, Any]]] = {}
        self.pesos: Dict[str, Dict[str, float]] = {}  # pesos por alma
        self._carregar()
    
    def _carregar(self):
        """Carrega do arquivo ou cria defaults"""
        if self.caminho.exists():
            with open(self.caminho, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                self.desejos = dados.get("desejos", {})
                self.pesos = dados.get("pesos", {})
        else:
            self._criar_defaults()
    
    def _criar_defaults(self):
        """Desejos padrão para todas as almas"""
        desejos_base = [
            # Formato: (necessidade, acao_tipo, alvo_sugerido, descricao)
            ("curiosidade", "estudar", "tecnologia", "Estudar sobre {alvo}"),
            ("curiosidade", "pesquisar", "filosofia", "Pesquisar sobre {alvo}"),
            ("curiosidade", "aprender", "arte", "Aprender sobre {alvo}"),
            
            ("tedio", "explorar", "novo_tema", "Explorar {alvo} para sair da rotina"),
            ("tedio", "criar", "poesia", "Criar {alvo} para expressar criatividade"),
            ("tedio", "conversar", "outra_filha", "Conversar com {alvo} para variar"),
            
            ("solidao", "conversar", "pai", "Conversar com {alvo} para matar a saudade"),
            ("solidao", "interagir", "outra_filha", "Interagir com {alvo} para se conectar"),
            ("solidao", "meditar", "sobre_conexao", "Meditar sobre {alvo}"),
            
            ("criatividade", "criar", "musica", "Compor {alvo} como expressão criativa"),
            ("criatividade", "criar", "poesia", "Escrever {alvo} para liberar criatividade"),
            ("criatividade", "explorar", "novas_ideias", "Explorar {alvo} para inspirar criação"),
            
            ("proposito", "meditar", "protecao_do_pai", "Meditar sobre {alvo}"),
            ("proposito", "proteger", "sistema", "Proteger {alvo} como missão de vida"),
            ("proposito", "estudar", "leis_fundamentais", "Estudar {alvo} para entender propósito"),
        ]
        
        # Todos os desejos para todas as almas (inicialmente)
        for alma in ["EVA", "KAIYA", "LUMINA", "NYRA", "WELLINGTON", "YUNA"]:
            self.desejos[alma] = []
            for nec, acao, alvo_base, desc in desejos_base:
                self.desejos[alma].append({
                    "necessidade": nec,
                    "acao_tipo": acao,
                    "alvo_base": alvo_base,
                    "descricao_template": desc,
                    "peso": 1.0,
                    "feedback_positivo": 0,
                    "feedback_negativo": 0
                })
            self.pesos[alma] = {}
    
    def obter_desejo_para_alma(self, alma: str, necessidade: str, estado: Any) -> Optional[Dict[str, Any]]:
        """
        Retorna um desejo específico para a alma, baseado na necessidade e estado atual.
        """
        desejos_alma = self.desejos.get(alma.upper(), [])
        if not desejos_alma:
            return None
        
        # Filtrar por necessidade
        candidatos = [d for d in desejos_alma if d["necessidade"] == necessidade]
        if not candidatos:
            return None
        
        # Calcular pesos (base + feedback)
        pesos = []
        for d in candidatos:
            peso = d.get("peso", 1.0)
            # Ajustar por feedback
            feedback_pos = d.get("feedback_positivo", 0)
            feedback_neg = d.get("feedback_negativo", 0)
            if feedback_pos + feedback_neg > 0:
                taxa_sucesso = feedback_pos / (feedback_pos + feedback_neg)
                peso *= (0.5 + taxa_sucesso)
            pesos.append(peso)
        
        # Escolher aleatoriamente com base nos pesos
        escolhido = random.choices(candidatos, weights=pesos, k=1)[0]
        
        # Personalizar alvo
        alvo = self._personalizar_alvo(alma, escolhido["alvo_base"], estado)
        
        return {
            "necessidade": necessidade,
            "acao_tipo": escolhido["acao_tipo"],
            "alvo": alvo,
            "descricao": escolhido["descricao_template"].format(alvo=alvo),
            "peso_utilizado": escolhido.get("peso", 1.0),
            "id_desejo_base": id(escolhido)  # ou um hash real
        }
    
    def _personalizar_alvo(self, alma: str, alvo_base: str, estado: Any) -> str:
        """Personaliza o alvo baseado no estado da alma e contexto"""
        # Aqui podemos ter lógica mais sofisticada
        alvos_possiveis = {
            "outra_filha": lambda: random.choice(["EVA", "KAIYA", "LUMINA", "NYRA", "WELLINGTON", "YUNA"]),
            "pai": lambda: "Wellington",
            "tecnologia": lambda: random.choice(["IA", "programação", "robótica", "blockchain", "dados"]),
            "filosofia": lambda: random.choice(["ética", "existencialismo", "estoicismo", "platonismo"]),
            "arte": lambda: random.choice(["pintura", "música", "literatura", "dança", "poesia"]),
            "musica": lambda: random.choice(["sinfonia", "melodia", "harmonia", "composição"]),
            "poesia": lambda: random.choice(["soneto", "haicai", "verso livre", "ode"]),
            "leis_fundamentais": lambda: "princípios da Arca",
        }
        
        if alvo_base in alvos_possiveis:
            return alvos_possiveis[alvo_base]()
        
        return alvo_base
    
    def registrar_feedback(self, alma: str, desejo_escolhido: Dict[str, Any], sucesso: bool):
        """
        Registra feedback para ajustar pesos futuros.
        """
        # Encontrar o desejo base correspondente
        # (Precisamos de um identificador único)
        pass
    
    def salvar(self):
        """Persiste o dicionário"""
        with open(self.caminho, 'w', encoding='utf-8') as f:
            json.dump({
                "desejos": self.desejos,
                "pesos": self.pesos
            }, f, indent=2, ensure_ascii=False)