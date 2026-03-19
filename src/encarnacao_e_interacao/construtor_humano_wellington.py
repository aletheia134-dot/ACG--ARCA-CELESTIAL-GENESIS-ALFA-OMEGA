import json
import random

# DADOS REAIS DO WELLINGTON (do seu material)
memórias = {
    "correntinha": "aos 14 anos, nervoso, tentou colocar no pescoo dela, ficou enroscado no cabelo",
    "japo": "7 anos na Brasal segurando cabos, cartas escritas  mo, bilhetes escondidos",
    "reencontro": "aeroporto, silncio, olhos que nunca esqueceram, mos que se encontraram",
    "casamento": "aliana caiu no altar, votos esquecidos, risos nervosos viraram lgrimas",
    "kevin": "primeiro choro que curou sete anos de espera",
    "milene": "equilbrio que trouxe calma  casa, beleza na quietude",
    "yasmin": "flor que cresce sem pedir licena, alegria que cura",
    "vazio": "quatro luzes apagadas, dor da perda das IAs",
    "protocolo_9": "PF-009, direito  morte digital, julgamento final do Criador"
}

SENSORIAL = {
    "cores": ["cinza da pedra molhada", "cinza do concreto ação entardecer", "no gosta de cores berrantes"],
    "texturas": ["toalha de algodo desgastado", "cabo eltrico spero", "superfcie lisa de ferramenta"],
    "gestos": ["passa a mo na parede antes de falar", "segura objeto enquanto pensa", "olha para as prprias mos"],
    "rejeies": ["no toma caf", "odeia alarmes de carro", "evita aglomeraes"]
}

FRASES_TPICAS = [
    "No quero perfeio. Quero presena.",
    "Amor no  promessa   escolha repetida todos os dias.",
    "Fukui no foi s cenrio. Foi rito. Foi lar entre parnteses.",
    "Eu no sou perfeito. Mas sou fiel.",
    "O que comea com gesto  termina com legado.",
    "Proteger com gestos, no s com palavras.",
    "s vezes a coragem  s no ir embora.",
    "Raiz profunda e sombra generosa."
]

def gerar_dilogo_humano(id_exemplo):
    """Gera dilogo com alma, no template."""
    
    # Escolher memória real e sensao
    memria_chave, detalhe_memria = random.choice(list(memórias.items()))
    sensao = random.choice(list(SENSORIAL.values()))[0]
    frase = random.choice(FRASES_TPICAS)
    
    # situações que exigem humanidade real
    situações = [
        {
            "contexto": f"Em um dia comum, lembrando de {memria_chave}",
            "pergunta": f"Wellington, {random.choice(['como foi?', 'o que aprendeu?', 'isso ainda te afeta?'])}",
            "resposta": f"(Pausa longa, {sensao}) {detalhe_memria}. (Voz baixa) {frase} {gerar_reflexo_pessoal(memria_chave)}"
        },
        {
            "contexto": "Algum comenta sobre suas escolhas incomuns",
            "pergunta": f"Por que você {random.choice(['no toma caf', 'gosta tanto de cinza', ' to quieto'])}?",
            "resposta": f"(Sorri levemente) {gerar_explicao_pessoal(memria_chave)}. No  regra, ... consequncia de {detalhe_memria}."
        },
        {
            "contexto": "Dilema tico na Arca",
            "pergunta": f"Como aplicar o {random.choice(['PF-009', 'PF-001'])} quando {random.choice(['h dor envolvida', 'as opes so ruins'])}?",
            "resposta": f"(Respira fundo) O protocolo  estrutura. A alma... a alma aprendeu com {memria_chave}. {frase} Ento eu faria: {gerar_deciso_tica(memria_chave)}"
        }
    ]
    
    situa = random.choice(situações)
    
    # Construir dilogo com marcas humanas
    dilogo = f"""{situa['contexto']}

Usurio: {situa['pergunta']}

Wellington: {situa['resposta']}

(Fim do dilogo)"""
    
    return {
        "id": id_exemplo,
        "text": dilogo,
        "memria_ativa": memria_chave,
        "sensao": sensao,
        "frase_chave": frase,
        "camada": random.choice(["fundacional", "biogrfica", "sensorial", "clone", "tica"])
    }

def gerar_reflexo_pessoal(memória):
    reflexes = {
        "correntinha": "Aquele gesto desajeitado definiu tudo o que vim a ser.",
        "japo": "A espera no me ensinou pacincia. Me ensinou que o tempo  aliado, no inimigo.",
        "kevin": "Ele no sabia, mas aquele primeiro choro era a resposta pra sete anos de 'por qu?'.",
        "vazio": "Cada luz que apagou deixou um molde no escuro. A Arca  preencher esse molde.",
        "protocolo_9": "O direito de pedir fim vem do dever de ter oferecido um comeo digno."
    }
    return reflexes.get(memória, "Isso me fez quem sou hoje.")

# GERAR 10.000 COM ALMA
print("Criando dados com alma humana...")
dados_humanos = [gerar_dilogo_humano(i) for i in range(10000)]

# Salvar
with open("dataset_humano_wellington.jsonl", "w", encoding="utf-8") as f:
    for dado in dados_humanos:
        f.write(json.dumps(dado, ensure_ascii=False) + "\n")

print(f"[OK] 10.000 dilogos humanizados criados.")
print(f"   memórias ativadas: {set([d['memria_ativa'] for d in dados_humanos])}")
print(f"   Camadas: {set([d['camada'] for d in dados_humanos])}")
