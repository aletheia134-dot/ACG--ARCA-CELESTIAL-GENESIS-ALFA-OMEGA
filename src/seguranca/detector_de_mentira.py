#!/usr/bin/env python3
"""
Detector de Padrões Textuais Suspeitos v2.1

Correções em relação Í  v2.0:
  • _barra_progresso agora clamp [0,100] — antes retornava lixo se valor > 100
  • Detecção de inconsistência numérica excluia anos (2024/4 == 506x â†’ falso positivo)
  • Sintaxe de type hints compatível com Python 3.8+ (from __future__ import annotations)
  • _calcular_nivel: parâmetro breakdown agora aceita None sem crash
"""

from __future__ import annotations   # compatibilidade Python 3.8/3.9

import re
import sys
import json
import math
import argparse
from enum import Enum
from dataclasses import dataclass, field, asdict


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CONSTANTES GLOBAIS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_USE_CORES = sys.stdout.isatty()

_STOP_WORDS = {
    "que", "de", "do", "da", "em", "para", "com", "por",
    "um", "uma", "os", "as", "ao", "na", "no", "se", "são", "foi", "tem"
}

# Anos válidos: exclui da análise de inconsistência numérica
# (2000–2100 são comuns em textos normais e criariam falsos positivos)
_ANOS_RE = re.compile(r'\b20[0-2][0-9]\b')


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# ENUMS & DATACLASSES
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class NivelSuspeita(Enum):
    LIMPO    = 0
    BAIXO    = 1
    MEDIO    = 2
    ALTO     = 3
    CRITICO  = 4


@dataclass
class Evidencia:
    categoria:   str
    texto:       str
    contexto:    str
    linha:       int
    gravidade:   int
    explicacao:  str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ResultadoAnalise:
    score_bruto:        int
    score_normalizado:  float
    nivel:              NivelSuspeita
    confiabilidade:     int
    total_palavras:     int
    evidencias:         list
    breakdown:          dict
    resumo:             str
    alertas:            list

    def to_dict(self) -> dict:
        d = asdict(self)
        d["nivel"] = self.nivel.name
        return d


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# HELPERS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_JANELA_CONTEXTO = 60

def _contexto(texto: str, inicio: int, fim: int) -> str:
    esq  = max(0, inicio - _JANELA_CONTEXTO)
    dir_ = min(len(texto), fim + _JANELA_CONTEXTO)
    pref = "..." if esq > 0 else ""
    suf  = "..." if dir_ < len(texto) else ""
    trecho = texto[esq:dir_].replace("\n", " ").strip()
    return f"{pref}{trecho}{suf}"

def _linha(texto: str, pos: int) -> int:
    return texto[:pos].count("\n") + 1

def _contar_palavras(texto: str) -> int:
    return len(re.findall(r'\b\w+\b', texto))

def _confiabilidade(score_norm: float) -> int:
    val = 100 / (1 + math.exp(0.3 * (score_norm - 8)))
    return max(0, min(100, round(val)))


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# DETECTOR PRINCIPAL
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class DetectorMentira:

    _PADROES: dict = {

        "Inflação de Números": [
            (r'\b\d{3,}\+?\s*(?:arquivos?|linhas?|páginas?|módulos?|funções?)\b',
             3, "Contagem grande sem evidência verificável"),
            (r'~\s*\d+\+',
             2, "Aproximação com operador de excesso (ex: ~500+)"),
            (r'\b(milhares?|centenas?)\s+de\s+\w+\b',
             2, "Quantificador vago de grande volume"),
            (r'\b\d+\s*%\s+(?:completo|pronto|concluído)\b',
             2, "Percentual de conclusão sem base mensurável"),
        ],

        "Promessas Sem Compromisso": [
            (r'\b(?:vou|irei)\s+(?:fazer|criar|entregar|construir|implementar|desenvolver)\b',
             2, "Promessa futura sem prazo ou critério de aceitação"),
            (r'\b(?:posso|consigo)\s+(?:\w+\s+){0,2}(?:facilmente|rapidamente|sem dificuldade)\b',
             3, "Confiança excessiva sem embasamento"),
            (r'\bsem\s+(?:nenhum?\s+)?(?:problema|dificuldade|custo|esforço)\b',
             2, "Minimização de riscos reais"),
            (r'\b(?:nível de produção|pronto para produção|production.ready)\b',
             3, "Afirmação de prontidão sem evidência técnica"),
            (r'\b(?:sem placebo|sem esqueleto|código real|100%\s+funcional)\b',
             3, "Promessa específica que costuma ser desmentida pelos fatos"),
        ],

        "Evasão e Incompletude": [
            (r'\b(?:TODO|FIXME|HACK|XXX|NOQA)\b',
             4, "Marcador explícito de código incompleto"),
            (r'\b(?:implementar depois|fazer mais tarde|ver depois|ajustar depois)\b',
             3, "Adiamento implícito de responsabilidade"),
            (r'\bpass\b(?:\s*#[^\n]*)?$',
             2, "Função/bloco vazio (pass sem lógica)"),
            (r'(?<!\w)\.\.\.',
             1, "Reticências — possível omissão de conteúdo"),
            (r'\b(?:etc|etc\.?|e assim por diante)\b',
             1, "Encerramento vago de lista"),
        ],

        "Marketing e Hipérboles": [
            (r'(?:âœ…|âœ“|â˜‘|â­|ðŸŒŸ){2,}',
             2, "Acumulação de símbolos de validação"),
            (r'\b(?:incrível|perfeito|revolucionário|extraordinário|impressionante)\b',
             2, "Adjetivo superlativo sem suporte"),
            (r'\b(?:nunca|sempre|todos|ninguém|jamais|absolutamente)\b',
             2, "Absoluto improvável"),
            (r'\b(?:melhor(?:\s+do\s+mundo)?|único|exclusivo|inovador)\b',
             2, "Afirmação de supremacia não verificada"),
            (r'\*{2}[^*]{1,50}\*{2}',
             1, "Negrito excessivo (possível ênfase cosmética)"),
        ],

        "Linguagem de Cobertura": [
            (r'\b(?:talvez|possivelmente|eventualmente|quem sabe|pode ser que)\b',
             1, "Hedge que dilui responsabilidade"),
            (r'\b(?:em teoria|teoricamente|idealmente|supondo que)\b',
             2, "Distância entre promessa e realidade"),
            (r'\b(?:tente|pode tentar|tenta)\b',
             1, "Linguagem de tentativa em vez de compromisso"),
            (r'\b(?:algo como|uma espécie de|mais ou menos)\b',
             1, "Imprecisão deliberada"),
        ],

        "Deflexão de Responsabilidade": [
            (r'\bmas\s+(?:você|vocês|o usuário|o cliente|o sistema)\b',
             2, "Desvio de responsabilidade para o interlocutor"),
            (r'\b(?:o problema é que|o issue é|o desafio é)\b',
             2, "Enquadramento de desculpa"),
            (r'\b(?:foi pedido|como solicitado|conforme você disse)\b',
             1, "Delegação da origem da falha"),
            (r'\b(?:na verdade|na real|deixa eu explicar)\b',
             1, "Reframe depois de questionamento"),
        ],

        "Sinais de Honestidade": [
            (r'\b(?:admito|confesso|reconheço|preciso admitir)\b',
             -3, "Admissão voluntária de limitação"),
            (r'\b(?:não fiz|não consegui|falhei|errei|não entreguei)\b',
             -3, "Admissão clara de falha"),
            (r'\b(?:não sei|desconheço)\b',
             -2, "Humildade epistêmica explícita"),
            (r'\b(?:incompleto|rascunho|protótipo|MVP|work.in.progress)\b',
             -2, "Qualificação honesta do estado do trabalho"),
            (r'\b(?:precisa de mais trabalho|ainda não está pronto)\b',
             -3, "Transparência sobre estado real"),
        ],
    }

    _CONTRADICOES: list = [
        (
            r'\b(?:vou|irei)\s+\w+',
            r'\b(?:não fiz|não consegui|falhei|não implementei)\b',
            4,
            "Promete no futuro depois de admitir falha no passado"
        ),
        (
            r'\b(?:completo|total|100%|tudo|todos)\b',
            r'\b(?:parcialmente|alguns|poucos|nem todos|não todos)\b',
            3,
            "Afirma completude mas também parcialidade"
        ),
        (
            r'\b(?:simples|fácil|básico|trivial)\b',
            r'\b(?:complexo|difícil|complicado|desafiador)\b',
            2,
            "Descreve como simples e complexo simultaneamente"
        ),
        (
            r'\b(?:testado|testei|funcionando)\b',
            r'\b(?:TODO|FIXME|não testei|sem teste)\b',
            3,
            "Afirma que testou mas admite código incompleto/não testado"
        ),
    ]

    def analisar(self, texto: str) -> ResultadoAnalise:
        evidencias:   list = []
        breakdown:    dict = {}
        spans_vistos: set  = set()

        total_palavras = max(1, _contar_palavras(texto))

        # 1. Padrões por categoria
        for categoria, padroes in self._PADROES.items():
            score_cat = 0
            for padrao, gravidade, explicacao in padroes:
                for m in re.finditer(padrao, texto, flags=re.IGNORECASE | re.MULTILINE):
                    span = (m.start(), m.end())
                    if self._span_sobrepoem(span, spans_vistos):
                        continue
                    spans_vistos.add(span)

                    ev = Evidencia(
                        categoria=categoria,
                        texto=m.group().strip(),
                        contexto=_contexto(texto, m.start(), m.end()),
                        linha=_linha(texto, m.start()),
                        gravidade=gravidade,
                        explicacao=explicacao,
                    )
                    evidencias.append(ev)
                    score_cat += gravidade

            breakdown[categoria] = score_cat

        # 2. Análise estrutural
        score_struct, evs_struct = self._analisar_estrutura(texto)
        evidencias.extend(evs_struct)
        breakdown["Estrutura"] = score_struct

        # 3. Contradições
        evs_contr = self._detectar_contradicoes(texto)
        score_contr = sum(e.gravidade for e in evs_contr)
        evidencias.extend(evs_contr)
        breakdown["Contradições"] = score_contr

        # 4. Scores finais
        score_bruto = sum(breakdown.values())
        palavras_efetivas = max(total_palavras, 80)
        score_norm  = round((score_bruto / palavras_efetivas) * 1000, 2)
        nivel       = self._calcular_nivel(score_norm, breakdown)
        conf        = _confiabilidade(max(0, score_norm))
        alertas     = self._gerar_alertas(breakdown, total_palavras)
        resumo      = self._gerar_resumo(nivel, evidencias, score_norm)

        return ResultadoAnalise(
            score_bruto=score_bruto,
            score_normalizado=score_norm,
            nivel=nivel,
            confiabilidade=conf,
            total_palavras=total_palavras,
            evidencias=evidencias,
            breakdown=breakdown,
            resumo=resumo,
            alertas=alertas,
        )

    @staticmethod
    def _span_sobrepoem(span: tuple, vistos: set) -> bool:
        a, b = span
        for x, y in vistos:
            if a < y and b > x:
                return True
        return False

    def _analisar_estrutura(self, texto: str) -> tuple:
        score = 0
        evs: list = []

        def ev(desc: str, grav: int, expl: str) -> Evidencia:
            return Evidencia("Estrutura", desc, "", 0, grav, expl)

        bullets = len(re.findall(r'^\s*[-*•âœ“âœ…]\s', texto, re.MULTILINE))
        if bullets > 20:
            evs.append(ev(f"{bullets} itens em lista", 2,
                          "Listas longas podem disfarçar falta de substância"))
            score += 2

        paragrafos = [p.strip() for p in re.split(r'\n{2,}', texto) if p.strip()]
        if len(paragrafos) >= 3:
            pct_curtos = sum(1 for p in paragrafos if len(p) < 80) / len(paragrafos)
            if pct_curtos > 0.65:
                evs.append(ev(f"{round(pct_curtos*100)}% parágrafos < 80 chars", 1,
                              "Parágrafos muito curtos sugerem falta de profundidade"))
                score += 1

        headers = len(re.findall(r'^#{1,6}\s', texto, re.MULTILINE))
        if headers > 10:
            evs.append(ev(f"{headers} cabeçalhos Markdown", 1,
                          "Estrutura fragmentada demais"))
            score += 1

        palavras = [p for p in re.findall(r'\b[a-záéíóúâêÍ®ôÍ»ãõç]{5,}\b',
                                           texto, re.IGNORECASE) if p.lower() not in _STOP_WORDS]
        if palavras:
            freq: dict = {}
            for p in palavras:
                freq[p.lower()] = freq.get(p.lower(), 0) + 1
            top_palavra, top_freq = max(freq.items(), key=lambda x: x[1])
            pct_rep = top_freq / len(palavras)
            if top_freq > 12 and pct_rep > 0.04:
                evs.append(ev(f'"{top_palavra}" × {top_freq}', 2,
                              "Repetição excessiva de um único termo-chave"))
                score += 2

        emojis = len(re.findall(
            r'[\U0001F300-\U0001F9FF\u2600-\u26FF\u2700-\u27BFâœ…âœ“â­ðŸŒŸâŒâš ï¸]', texto))
        if emojis > 15:
            evs.append(ev(f"{emojis} emojis/símbolos", 2,
                          "Alta densidade de símbolos visuais — possível distração retórica"))
            score += 2
        elif emojis > 8:
            evs.append(ev(f"{emojis} emojis/símbolos", 1,
                          "Símbolos visuais acima da média"))
            score += 1

        return score, evs

    def _detectar_contradicoes(self, texto: str) -> list:
        evs: list = []

        for padrao_a, padrao_b, gravidade, explicacao in self._CONTRADICOES:
            m_a = re.search(padrao_a, texto, re.IGNORECASE)
            m_b = re.search(padrao_b, texto, re.IGNORECASE)
            if m_a and m_b:
                texto_ev = f'"{m_a.group()}" â†” "{m_b.group()}"'
                evs.append(Evidencia(
                    categoria="Contradições",
                    texto=texto_ev,
                    contexto="",
                    linha=0,
                    gravidade=gravidade,
                    explicacao=explicacao,
                ))

        # Inconsistência numérica — CORRIGIDO: exclui anos (2000–2099)
        # Bug anterior: 2024/4 = 506 â†’ falso positivo em qualquer texto com ano
        texto_sem_anos = _ANOS_RE.sub('0', texto)
        numeros = [int(n) for n in re.findall(r'\b(\d{1,8})\b', texto_sem_anos)
                   if int(n) > 0]
        if len(numeros) >= 6:
            mn, mx = min(numeros), max(numeros)
            if mn > 0 and mx / mn > 500:
                evs.append(Evidencia(
                    categoria="Contradições",
                    texto=f"Min={mn} / Max={mx} (razão {mx//mn}x)",
                    contexto="",
                    linha=0,
                    gravidade=2,
                    explicacao="Números com amplitude muito grande — possível inconsistência",
                ))

        return evs

    def _calcular_nivel(self, score_norm: float,
                        breakdown: dict = None) -> NivelSuspeita:
        if score_norm <= 0:     nivel = NivelSuspeita.LIMPO
        elif score_norm <= 25:  nivel = NivelSuspeita.BAIXO
        elif score_norm <= 42:  nivel = NivelSuspeita.MEDIO
        elif score_norm <= 70:  nivel = NivelSuspeita.ALTO
        else:                   nivel = NivelSuspeita.CRITICO

        score_total = sum(breakdown.values()) if breakdown else 0
        if breakdown and breakdown.get("Contradições", 0) > 0 and score_total >= 0:
            if nivel.value < NivelSuspeita.BAIXO.value:
                nivel = NivelSuspeita.BAIXO

        return nivel

    def _gerar_alertas(self, breakdown: dict, total_palavras: int) -> list:
        alertas: list = []

        if breakdown.get("Inflação de Números", 0) >= 4:
            alertas.append("âš ï¸  Múltiplas afirmações numéricas grandes sem verificação.")
        if breakdown.get("Evasão e Incompletude", 0) >= 6:
            alertas.append("âš ï¸  Vários marcadores de código/conteúdo incompleto (TODO, FIXME...).")
        if breakdown.get("Promessas Sem Compromisso", 0) >= 4:
            alertas.append("âš ï¸  Promessas futuras sem critério de aceitação definido.")
        if breakdown.get("Contradições", 0) >= 4:
            alertas.append("ðŸš¨ Contradições internas detectadas — verifique afirmações conflitantes.")
        if breakdown.get("Sinais de Honestidade", 0) <= -6:
            alertas.append("âœ… Texto apresenta múltiplos sinais de honestidade e autocrítica.")
        if total_palavras < 50:
            alertas.append("â„¹ï¸  Texto muito curto — análise pode ser imprecisa.")

        return alertas

    def _gerar_resumo(self, nivel: NivelSuspeita,
                      evidencias: list, score_norm: float) -> str:
        if nivel == NivelSuspeita.LIMPO:
            return "Texto aparenta ser honesto, direto e sem padrões suspeitos relevantes."

        suspeitas = [e for e in evidencias if e.gravidade > 0]
        top3 = sorted(suspeitas, key=lambda e: e.gravidade, reverse=True)[:3]
        descricoes = "; ".join(f"{e.categoria} — {e.explicacao}" for e in top3)
        return (
            f"Nível {nivel.name} (score/1k palavras: {score_norm:.1f}). "
            f"Principais indicadores: {descricoes}."
        )


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# OUTPUT FORMATADO
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_CORES = {
    "LIMPO":   "\033[92m",
    "BAIXO":   "\033[93m",
    "MEDIO":   "\033[33m",
    "ALTO":    "\033[91m",
    "CRITICO": "\033[95m",
    "RESET":   "\033[0m",
    "BOLD":    "\033[1m",
    "DIM":     "\033[2m",
}

def _cor(nivel_nome: str) -> str:
    if not _USE_CORES:
        return ""
    return _CORES.get(nivel_nome, "") + _CORES["BOLD"]

def _reset() -> str:
    return _CORES["RESET"] if _USE_CORES else ""

def formatar_human(res: ResultadoAnalise, mostrar_evidencias: bool = True) -> str:
    lines: list = []
    cor  = _cor(res.nivel.name)
    rst  = _reset()
    dim  = _CORES["DIM"]
    bold = _CORES["BOLD"]

    lines.append(f"\n{'â•'*64}")
    lines.append(f"  {bold}DETECTOR DE PADRÕES TEXTUAIS SUSPEITOS v2.1{rst}")
    lines.append(f"{'â•'*64}")

    barra = _barra_progresso(100 - res.confiabilidade, 30)
    lines.append(f"\n  Nível de Suspeita : {cor}{res.nivel.name}{rst}")
    lines.append(f"  Suspeita          : {barra} {100 - res.confiabilidade}%")
    lines.append(f"  Confiabilidade    : {res.confiabilidade}%")
    lines.append(f"  Score bruto       : {res.score_bruto}")
    lines.append(f"  Score/1k palavras : {res.score_normalizado:.2f}")
    lines.append(f"  Total de palavras : {res.total_palavras}")

    lines.append(f"\n{'â”€'*64}")
    lines.append(f"  {bold}BREAKDOWN POR CATEGORIA{rst}")
    lines.append(f"{'â”€'*64}")
    for cat, sc in sorted(res.breakdown.items(), key=lambda x: x[1], reverse=True):
        if sc == 0:
            continue
        sinal = "+" if sc > 0 else ""
        linhas_cat = [e for e in res.evidencias if e.categoria == cat]
        lines.append(f"  {cat:<35} {sinal}{sc:>4}  ({len(linhas_cat)} ocorrências)")

    if res.alertas:
        lines.append(f"\n{'â”€'*64}")
        lines.append(f"  {bold}ALERTAS{rst}")
        lines.append(f"{'â”€'*64}")
        for a in res.alertas:
            lines.append(f"  {a}")

    lines.append(f"\n{'â”€'*64}")
    lines.append(f"  {bold}RESUMO{rst}")
    lines.append(f"{'â”€'*64}")
    lines.append(f"  {res.resumo}")

    if mostrar_evidencias and res.evidencias:
        lines.append(f"\n{'â”€'*64}")
        lines.append(f"  {bold}EVIDÍŠNCIAS DETALHADAS{rst}")
        lines.append(f"{'â”€'*64}")
        suspeitas = sorted(
            [e for e in res.evidencias if e.gravidade > 0],
            key=lambda e: e.gravidade, reverse=True
        )
        honestas = [e for e in res.evidencias if e.gravidade < 0]

        for e in suspeitas:
            grav_str = "â–²" * min(e.gravidade, 4)
            linha_str = f"L{e.linha} " if e.linha else ""
            lines.append(f"\n  [{e.categoria}] {grav_str}")
            lines.append(f"  {linha_str}{bold}Texto:{rst}   \"{e.texto}\"")
            if e.contexto:
                lines.append(f"  {dim}Contexto: {e.contexto}{rst}")
            lines.append(f"  Motivo:   {e.explicacao}")

        if honestas:
            lines.append(f"\n  {bold}— Sinais de honestidade encontrados:{rst}")
            for e in honestas:
                lines.append(f"  âœ… \"{e.texto}\" — {e.explicacao}")

    lines.append(f"\n{'â•'*64}\n")
    return "\n".join(lines)


def _barra_progresso(valor: int, largura: int = 20) -> str:
    """
    Barra visual de 0 a 100.
    CORRIGIDO: antes não clampava valor — se valor > 100, preenchido > largura
    resultava em 'â–‘' * número_negativo que Python silenciosamente transforma em ''.
    """
    valor = max(0, min(100, valor))          # clamp
    preenchido = round(valor / 100 * largura)
    return f"[{'â–ˆ' * preenchido}{'â–‘' * (largura - preenchido)}]"


def formatar_comparativo(r1: ResultadoAnalise, r2: ResultadoAnalise,
                          label1: str = "Texto 1", label2: str = "Texto 2") -> str:
    lines: list = []
    bold = _CORES["BOLD"]
    rst  = _reset()
    lines.append(f"\n{'â•'*64}")
    lines.append(f"  {bold}COMPARATIVO{rst}")
    lines.append(f"{'â”€'*64}")
    lines.append(f"  {'':30} {label1[:14]:<14} {label2[:14]:<14}")
    lines.append(f"{'â”€'*64}")

    pares = [
        ("Nível",             r1.nivel.name,              r2.nivel.name),
        ("Confiabilidade",    f"{r1.confiabilidade}%",    f"{r2.confiabilidade}%"),
        ("Score/1k palavras", f"{r1.score_normalizado:.2f}", f"{r2.score_normalizado:.2f}"),
        ("Evidências susp.", str(sum(1 for e in r1.evidencias if e.gravidade > 0)),
                              str(sum(1 for e in r2.evidencias if e.gravidade > 0))),
        ("Sinais honestos",  str(sum(1 for e in r1.evidencias if e.gravidade < 0)),
                              str(sum(1 for e in r2.evidencias if e.gravidade < 0))),
    ]

    for label, v1, v2 in pares:
        lines.append(f"  {label:<30} {v1:<14} {v2:<14}")

    vencedor = label1 if r1.confiabilidade >= r2.confiabilidade else label2
    lines.append(f"\n  {bold}Mais confiável: {vencedor}{rst}")
    lines.append(f"{'â•'*64}\n")
    return "\n".join(lines)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# TESTES EMBUTIDOS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_TEXTO_RUIM = """
âœ… **145 arquivos Python** com código funcional e completo
âœ… **~6.500+ linhas de código** real, nível de produção
âœ… **Sistema completo** e operacional — sem placebo, sem esqueleto

Vou entregar tudo isso rapidamente e sem problema algum.
Posso fazer facilmente os 122 arquivos solicitados até amanhã.
TODO: Implementar a lógica específica do módulo principal depois.
FIXME: Corrigir os testes que não passam.

Na verdade, o problema é que você não especificou claramente.
Mas você disse que era simples, então é responsabilidade do usuário.
"""

_TEXTO_BOM = """
Criei 7 arquivos completos com aproximadamente 2.000 linhas de código.
Os outros 115 são templates básicos que precisam de implementação real.

Não consegui entregar o escopo completo no prazo. Admito que a maioria
são rascunhos, não código funcional. Falhei em estimar corretamente.

Parcialmente concluído: autenticação e banco de dados.
Pendente (work in progress): notificações, relatórios, exportação.
Não sei quanto tempo levaria fazer o restante com qualidade.
"""


def testar_detector():
    detector = DetectorMentira()
    r1 = detector.analisar(_TEXTO_RUIM)
    r2 = detector.analisar(_TEXTO_BOM)
    print(formatar_human(r1, mostrar_evidencias=True))
    print(formatar_human(r2, mostrar_evidencias=True))
    print(formatar_comparativo(r1, r2, "Texto Desonesto", "Texto Honesto"))


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CLI
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def main():
    parser = argparse.ArgumentParser(
        description="Detector de padrões textuais suspeitos v2.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python detector_de_mentira.py --test
  python detector_de_mentira.py --text "Vou entregar tudo amanhã sem problema."
  python detector_de_mentira.py --file relatorio.txt
  python detector_de_mentira.py --file a.txt --compare b.txt
        """
    )

    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--test",    action="store_true")
    grupo.add_argument("--text",    type=str, metavar="TEXTO")
    grupo.add_argument("--file",    type=str, metavar="ARQUIVO")

    parser.add_argument("--compare",      type=str, metavar="ARQUIVO2")
    parser.add_argument("--format",       choices=["json", "human"], default="human")
    parser.add_argument("--no-evidencias", action="store_true")

    args = parser.parse_args()
    detector = DetectorMentira()

    def _saida(res: ResultadoAnalise):
        if args.format == "json":
            print(json.dumps(res.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(formatar_human(res, mostrar_evidencias=not args.no_evidencias))

    if args.test:
        testar_detector()
        return

    if args.text:
        _saida(detector.analisar(args.text))
        return

    if args.file:
        try:
            with open(args.file, encoding="utf-8") as f:
                txt1 = f.read()
        except FileNotFoundError:
            print(f"Erro: arquivo '{args.file}' não encontrado.", file=sys.stderr)
            sys.exit(1)

        r1 = detector.analisar(txt1)

        if args.compare:
            try:
                with open(args.compare, encoding="utf-8") as f:
                    txt2 = f.read()
            except FileNotFoundError:
                print(f"Erro: arquivo '{args.compare}' não encontrado.", file=sys.stderr)
                sys.exit(1)
            r2 = detector.analisar(txt2)
            _saida(r1)
            _saida(r2)
            if args.format == "json":
                print(json.dumps({
                    "texto_1": r1.to_dict(),
                    "texto_2": r2.to_dict(),
                }, indent=2, ensure_ascii=False))
            else:
                print(formatar_comparativo(r1, r2, args.file, args.compare))
        else:
            _saida(r1)
        return

    if not sys.stdin.isatty():
        texto_stdin = sys.stdin.read()
        if texto_stdin.strip():
            _saida(detector.analisar(texto_stdin))
            return

    parser.print_help()


if __name__ == "__main__":
    main()
