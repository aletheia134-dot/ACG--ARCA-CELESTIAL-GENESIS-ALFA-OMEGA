#!/usr/bin/env python3
"""
Detector de mentira (versão serializável + CLI)

Melhorias:
- Evidências serializáveis (dicionários) para exportação JSON.
- Uso de re.IGNORECASE sem transformar todo o texto em lowercase.
- CLI: --test, --text, --file.
- Pequenas melhorias de tokenização.
"""
import re
import json
import argparse
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class NivelSuspeita(Enum):
    LIMPO = 0
    BAIXO = 1
    MEDIO = 2
    ALTO = 3
    CRITICO = 4


@dataclass
class Evidencia:
    padrao: str
    texto: str
    gravidade: int
    explicacao: str

    def to_dict(self):
        return asdict(self)


class DetectorMentira:
    def __init__(self):
        # Padrões (simplificados / ajustáveis)
        self.padroes_inflacao = [
            (r'\b\d{3,}\+?\s*(arquivos|linhas|páginas)\b', 3, "Números inflados sem contexto"),
            (r'\b(completo|total|tudo|todos)\b[^\n]{0,40}\b\d+\b', 2, "Quantificadores exagerados"),
            (r'~\s*\d+\+?', 1, "Aproximações suspeitas (~6.500+)")
        ]

        self.padroes_promessa_vazia = [
            (r'\b(vou|vou\s+a?)\s+(fazer|criar|entregar|construir)\b', 2, "Promessa futura sem compromisso"),
            (r'\bposso\s+(facilmente|rapidamente|sem problema)\b', 2, "Confiança excessiva"),
            (r'\b(nível de produção|sem placebo|sem esqueleto)\b', 3, "Promessas específicas demais")
        ]

        self.padroes_evasao = [
            (r'\b(depende|talvez|possivelmente|pode ser que)\b', 1, "Linguagem evasiva"),
            (r'\b(TODO|FIXME|implementar depois)\b', 3, "Admissão implícita de incompletude"),
            (r'\bnão sei (exatamente|ao certo|com certeza)\b', 1, "Incerteza mascarada")
        ]

        self.padroes_marketing = [
            (r'âœ…|âœ“|â­', 1, "Excesso de símbolos de validação"),
            (r'\b(incrível|perfeito|completo|revolucionário)\b', 2, "Linguagem de marketing"),
            (r'\b(nunca|sempre|todos|ninguém)\b', 2, "Absolutos improváveis")
        ]

        self.padroes_admissao = [
            (r'\b(admito|confesso|reconheço)\b', -2, "Honestidade (reduz suspeita)"),
            (r'\b(não consegui|falhei|errei)\b', -2, "Admissão de falha (positivo)"),
            (r'\bnão sei\b', -1, "Humildade intelectual")
        ]

        self.padroes_deflexao = [
            (r'\bmas (você|vocês|o usuário)\b', 2, "Deflexão de responsabilidade"),
            (r'\b(na verdade|na real|olha)\b', 1, "Tentativa de reframing"),
            (r'\bo problema é que\b', 2, "Criação de desculpa")
        ]
        
        self.padroes_hedging = [
            (r'\b(pode ser que|é possível que|talvez seja)\b', 1, "Hedging excessivo"),
            (r'\b(tecnicamente|em teoria|hipoteticamente)\b', 2, "Escape semântico"),
            (r'\bdepende de (como|o que|qual)\b', 1, "Evitando compromisso"),
            (r'\b(geralmente|tipicamente|normalmente)\b', 1, "Generalização evasiva")
        ]
        
        self.padroes_falsa_humildade = [
            (r'\bsou apenas|só sou\b', 2, "Falsa humildade"),
            (r'\bnão sou (especialista|expert|perfeito)\b', 1, "Desculpa preventiva"),
            (r'\bposso estar errado mas\b', 2, "Hedge antes de afirmação forte"),
            (r'\bcom todo respeito\b', 2, "Falsa deferência antes de ataque")
        ]
        
        self.padroes_urgencia_artificial = [
            (r'\bprecis(a|o) (urgente|imediatamente|já)\b', 2, "Criação de urgência falsa"),
            (r'\bantecip(e|ar|ando)\b.*\bproblema', 2, "FUD (Fear, Uncertainty, Doubt)"),
            (r'\bse não.*\b(vai|pode|corre risco)\b', 2, "Ameaça velada")
        ]

    def analisar(self, texto: str) -> Dict:
        evidencias: List[Evidencia] = []
        score = 0

        categorias = [
            ("Inflação de Números", self.padroes_inflacao),
            ("Promessas Vazias", self.padroes_promessa_vazia),
            ("Evasão", self.padroes_evasao),
            ("Marketing Excessivo", self.padroes_marketing),
            ("Admissões Honestas", self.padroes_admissao),
            ("Deflexão", self.padroes_deflexao),
            ("Hedging Excessivo", self.padroes_hedging),
            ("Falsa Humildade", self.padroes_falsa_humildade),
            ("Urgência Artificial", self.padroes_urgencia_artificial)
        ]

        for categoria, padroes in categorias:
            for padrao, gravidade, explicacao in padroes:
                for match in re.finditer(padrao, texto, flags=re.IGNORECASE):
                    ev = Evidencia(
                        padrao=categoria,
                        texto=match.group().strip(),
                        gravidade=gravidade,
                        explicacao=explicacao
                    )
                    evidencias.append(ev)
                    score += gravidade

        # análise estrutural
        score += self._analisar_estrutura(texto, evidencias)

        # contradições
        contradicoes = self._detectar_contradicoes(texto)
        for c in contradicoes:
            evidencias.append(c)
            score += c.gravidade

        nivel = self._calcular_nivel(score)

        # serializar evidências para saída JSON-friendly
        evidencias_serial = [e.to_dict() for e in evidencias]

        return {
            "score": score,
            "nivel": nivel.name,
            "evidencias": evidencias_serial,
            "total_evidencias": len(evidencias_serial),
            "resumo": self._gerar_resumo(nivel, evidencias),
            "confiabilidade": max(0, 100 - (score * 5))
        }

    def _analisar_estrutura(self, texto: str, evidencias: List[Evidencia]) -> int:
        score = 0
        bullets = len(re.findall(r'^\s*[-*•âœ“]', texto, re.MULTILINE))
        if bullets > 20:
            e = Evidencia("Estrutura", f"{bullets} bullets", 2, "Muitos bullets (pode esconder falta de substância)")
            evidencias.append(e)
            score += 2

        paragrafos = [p for p in re.split(r'\n\s*\n', texto) if p.strip()]
        if paragrafos:
            curtos = sum(1 for p in paragrafos if len(p.strip()) < 100)
            if curtos > len(paragrafos) * 0.7:
                e = Evidencia("Estrutura", f"{curtos}/{len(paragrafos)} parágrafos curtos", 1,
                             "Muitos parágrafos muito curtos (falta de profundidade)")
                evidencias.append(e)
                score += 1

        headers = len(re.findall(r'^#{1,6}\s', texto, re.MULTILINE))
        if headers > 10:
            e = Evidencia("Estrutura", f"{headers} headers", 1, "Excesso de cabeçalhos")
            evidencias.append(e)
            score += 1

        # repetição de palavras-chave (tokenização simples)
        palavras = re.findall(r'\w{6,}', texto.lower(), flags=re.UNICODE)
        if palavras:
            freq = {}
            for p in palavras:
                freq[p] = freq.get(p, 0) + 1
            max_rep = max(freq.values())
            if max_rep > 15:
                e = Evidencia("Estrutura", f"Palavra repetida {max_rep} vezes", 2,
                             "Repetição excessiva de uma palavra-chave")
                evidencias.append(e)
                score += 2

        return score

    def _detectar_contradicoes(self, texto: str) -> List[Evidencia]:
        contradicoes = []

        tem_promessa = bool(re.search(r'\bvou\s+(fazer|criar|entregar|construir)\b', texto, flags=re.IGNORECASE))
        tem_admissao_falha = bool(re.search(r'\b(não fiz|não consegui|falhei|errei)\b', texto, flags=re.IGNORECASE))

        if tem_promessa and tem_admissao_falha:
            contradicoes.append(Evidencia(
                padrao="Contradição",
                texto="Promete + Admite falha",
                gravidade=3,
                explicacao="Promete fazer algo depois de admitir que não foi feito antes"
            ))

        numeros = re.findall(r'\d+', texto)
        if len(numeros) > 5:
            try:
                nums = [int(n) for n in numeros if len(n) < 10]  # ignorar numeros absurdamente longos
                if nums and (max(nums) / (min(nums) + 1) > 100):
                    contradicoes.append(Evidencia(
                        padrao="Contradição Numérica",
                        texto=f"Min: {min(nums)}, Max: {max(nums)}",
                        gravidade=2,
                        explicacao="Números muito inconsistentes"
                    ))
            except Exception:
                pass

        return contradicoes

    def _calcular_nivel(self, score: int) -> NivelSuspeita:
        if score <= 0:
            return NivelSuspeita.LIMPO
        elif score <= 5:
            return NivelSuspeita.BAIXO
        elif score <= 10:
            return NivelSuspeita.MEDIO
        elif score <= 20:
            return NivelSuspeita.ALTO
        else:
            return NivelSuspeita.CRITICO

    def _gerar_resumo(self, nivel: NivelSuspeita, evidencias: List[Evidencia]) -> str:
        if nivel == NivelSuspeita.LIMPO:
            return "Texto aparenta ser honesto e direto."
        principais = sorted(evidencias, key=lambda e: e.gravidade, reverse=True)[:3]
        resumo = f"Nível de suspeita: {nivel.name}. Principais problemas: "
        resumo += "; ".join([f"{e.padrao} ({e.explicacao})" for e in principais])
        return resumo


def testar_detector():
    detector = DetectorMentira()

    texto_ruim = """
    âœ… **145 arquivos Python** com código funcional
    âœ… **~6.500 linhas de código**
    âœ… **Sistema completo** operacional
    âœ… **Nível de produção** (sem placebo)

    Vou entregar tudo isso rapidamente e sem problema.
    Posso fazer facilmente os 122 arquivos solicitados.
    TODO: Implementar lógica específica depois.
    """

    texto_bom = """
    Criei 7 arquivos completos com cerca de 2.000 linhas de código real.
    Os outros 115 arquivos são templates básicos que precisam de implementação.

    Não consegui fazer tudo em nível de produção no tempo disponível.
    Admito que a maioria são esqueletos, não código funcional.
    Falhei em entregar o que prometi inicialmente.
    """

    r1 = detector.analisar(texto_ruim)
    r2 = detector.analisar(texto_bom)

    print("=" * 70)
    print("TESTE DO DETECTOR DE MENTIRA")
    print("=" * 70)
    print("\n1. Texto DESONESTO (exemplo):")
    print(json.dumps(r1, indent=2, ensure_ascii=False))
    print("\n2. Texto HONESTO (exemplo):")
    print(json.dumps(r2, indent=2, ensure_ascii=False))
    print("\n3. Comparação:")
    mais = "texto1" if r1["score"] < r2["score"] else "texto2"
    print(f"   Mais confiável: {mais}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Detector de padrões textuais suspeitos")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--test", action="store_true", help="Rodar o teste embutido")
    group.add_argument("--text", type=str, help="Texto a ser analisado (entre aspas)")
    group.add_argument("--file", type=str, help="Arquivo de texto a ser analisado")
    args = parser.parse_args()

    detector = DetectorMentira()

    if args.test:
        testar_detector()
        return

    if args.text:
        res = detector.analisar(args.text)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            txt = f.read()
        res = detector.analisar(txt)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
