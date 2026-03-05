from collections import defaultdict, Counter
from difflib import SequenceMatcher
import datetime
import logging
from typing import List, Dict, Any


# Logger para depuração
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# =====================================================================
# ANÍLISE DE PADRÕES (MÓDULO BASE)
# =====================================================================

class AnalisadorDePadroes:
    """
    Analisador de padrões para transformar dados de eventos e textos em informações úteis.
    """

    def hierarquia_valores(self, itens: List[str]) -> List[Tuple[str, int]]:
        """
        Cria uma hierarquia a partir da contagem de itens.
        Exemplo: Retorna os itens mais frequentes.
        """
        cnt = Counter(itens)
        return cnt.most_common()

    def mapear_associacoes_semanticas(self, texto: str, janela: int = 4) -> Dict[str, List[str]]:
        """
        Analisa um texto e encontra palavras frequentemente associadas umas Í s outras.
        """
        tokens = texto.split()
        assoc = defaultdict(Counter)
        for i, palavra in enumerate(tokens):
            inicio = max(0, i - janela)
            fim = min(len(tokens), i + janela + 1)
            for j in range(inicio, fim):
                if j != i:
                    assoc[palavra][tokens[j]] += 1
        return {k: [v for v, _ in contador.most_common(3)] for k, contador in assoc.items()}

    def perfil_aprendizado(self, historico: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analisa um histórico de eventos e calcula taxas de sucesso e aprendizado.
        """
        total = len(historico)
        estatisticas = defaultdict(lambda: {"sucesso": 0, "total": 0})

        for evento in historico:
            tag = evento.get("tag", "geral")
            sucesso = evento.get("sucesso", False)
            estatisticas[tag]["total"] += 1
            if sucesso:
                estatisticas[tag]["sucesso"] += 1

        for tag, valores in estatisticas.items():
            valores["taxa_sucesso"] = valores["sucesso"] / valores["total"] if valores["total"] > 0 else 0

        return {
            "total_eventos": total,
            "estatisticas_por_tag": estatisticas,
        }


# =====================================================================
# GERADOR DE PERFIS DINÂMICOS (EXTENSÍO)
# =====================================================================

class GeradorPerfilComportamental(AnalisadorDePadroes):
    """
    Extensão do Analisador para gerar perfis comportamentais individualizados.
    """

    def __init__(self):
        super().__init__()
        self.perfis = {}  # Base de perfis comportamentais
        self.historico = []  # Histórico de eventos analisados

    def analisar_evento(self, id_objeto: str, evento: Dict[str, Any]) -> None:
        """
        Analisa um evento individual e ajusta o perfil comportamental correspondente.
        """
        logger.info("Analisando evento para '%s': %s", id_objeto, evento)

        # Inicializa o perfil caso não exista
        if id_objeto not in self.perfis:
            self.perfis[id_objeto] = {
                "curiosidade": 50,
                "assertividade": 50,
                "paciência": 50,
                "otimismo": 50,
                "eventos_processados": 0,
            }

        perfil = self.perfis[id_objeto]
        impacto = evento.get("impacto", 0)
        tipo = evento.get("tipo", "").lower()

        if tipo == "erro":
            perfil["assertividade"] = max(0, perfil["assertividade"] - 5)
            perfil["otimismo"] = max(0, perfil["otimismo"] + impacto)
        elif tipo == "sucesso":
            perfil["curiosidade"] = min(100, perfil["curiosidade"] + impacto)
            perfil["otimismo"] = min(100, perfil["otimismo"] + 10)
        elif tipo == "sugestao":
            perfil["assertividade"] = min(100, perfil["assertividade"] + impacto)
            perfil["curiosidade"] = min(100, perfil["curiosidade"] + impacto)

        # Atualiza contador de eventos e histórico
        perfil["eventos_processados"] += 1
        self.historico.append({"id": id_objeto, "evento": evento, "timestamp": datetime.datetime.now()})

    def gerar_perfil_texto(self, id_objeto: str, texto: str) -> None:
        """
        Gera ajustes de perfil com base no entendimento do texto.
        """
        associacoes_semanticas = self.mapear_associacoes_semanticas(texto)
        logger.debug("Associações semânticas geradas para '%s': %s", id_objeto, associacoes_semanticas)

        for palavra in texto.split():
            if palavra in ["descobrir", "investigar", "explorar"]:
                self.perfis[id_objeto]["curiosidade"] += 5

    def obter_perfil(self, id_objeto: str) -> Dict[str, Any]:
        """
        Retorna o perfil comportamental completo de um objeto.
        """
        return self.perfis.get(id_objeto, {})

    def ajustar_com_base_historico(self, id_objeto: str):
        """
        Ajusta o perfil baseado em todos os eventos registrados no histórico.
        """
        eventos_obj = [evt for evt in self.historico if evt["id"] == id_objeto]
        for evento in eventos_obj:
            self.analisar_evento(id_objeto, evento.get("evento", {}))
