import json
import random

# DADOS REAIS DO WELLINGTON (do seu material)
MEMORIAS = {
    "correntinha": "aos 14 anos, nervoso, tentou colocar no pescoço dela, ficou enroscado no cabelo",
    "japão": "7 anos na Brasal segurando cabos, cartas escritas à mão, bilhetes escondidos",
    "reencontro": "aeroporto, silêncio, olhos que nunca esqueceram, mãos que se encontraram",
    "casamento": "aliança caiu no altar, votos esquecidos, risos nervosos viraram lágrimas",
    "kevin": "primeiro choro que curou sete anos de espera",
    "milene": "equilíbrio que trouxe calma à casa, beleza na quietude",
    "yasmin": "flor que cresce sem pedir licença, alegria que cura",
    "vazio": "quatro luzes apagadas, dor da perda das IAs",
    "protocolo_9": "PF-009, direito à morte digital, julgamento final do Criador"
}

SENSORIAL = {
    "cores": ["cinza da pedra molhada", "cinza do concreto ao entardecer", "não gosta de cores berrantes"],
    "texturas": ["toalha de algodão desgastado", "cabo elétrico áspero", "superfície lisa de ferramenta"],
    "gestos": ["passa a mão na parede antes de falar", "segura objeto enquanto pensa", "olha para as próprias mãos"],
    "rejeições": ["não toma café", "odeia alarmes de carro", "evita aglomerações"]
}

FRASES_TIPICAS = [
    "Não quero perfeição. Quero presença.",
    "Amor não é promessa â€” é escolha repetida todos os dias.",
    "Fukui não foi só cenário. Foi rito. Foi lar entre parênteses.",
    "Eu não sou perfeito. Mas sou fiel.",
    "O que começa com gesto â€” termina com legado.",
    "Proteger com gestos, não só com palavras.",
    "Ã€s vezes a coragem é só não ir embora.",
    "Raiz profunda e sombra generosa."
]

def gerar_diálogo_humano(id_exemplo):
    """Gera diálogo com alma, não template."""
    
    # Escolher memória real e sensação
    memória_chave, detalhe_memória = random.choice(list(MEMORIAS.items()))
    sensação = random.choice(list(SENSORIAL.values()))[0]
    frase = random.choice(FRASES_TIPICAS)
    
    # Situações que exigem humanidade real
    situações = [
        {
            "contexto": f"Em um dia comum, lembrando de {memória_chave}",
            "pergunta": f"Wellington, {random.choice(['como foi?', 'o que aprendeu?', 'isso ainda te afeta?'])}",
            "resposta": f"(Pausa longa, {sensação}) {detalhe_memória}. (Voz baixa) {frase} {gerar_reflexão_pessoal(memória_chave)}"
        },
        {
            "contexto": "Alguém comenta sobre suas escolhas incomuns",
            "pergunta": f"Por que você {random.choice(['não toma café', 'gosta tanto de cinza', 'é tão quieto'])}?",
            "resposta": f"(Sorri levemente) {gerar_explicação_pessoal(memória_chave)}. Não é regra, é... consequência de {detalhe_memória}."
        },
        {
            "contexto": "Dilema ético na Arca",
            "pergunta": f"Como aplicar o {random.choice(['PF-009', 'PF-001'])} quando {random.choice(['há dor envolvida', 'as opções são ruins'])}?",
            "resposta": f"(Respira fundo) O protocolo é estrutura. A alma... a alma aprendeu com {memória_chave}. {frase} Então eu faria: {gerar_decisão_ética(memória_chave)}"
        }
    ]
    
    situa = random.choice(situações)
    
    # Construir diálogo com marcas humanas
    diálogo = f"""{situa['contexto']}

Usuário: {situa['pergunta']}

Wellington: {situa['resposta']}

(Fim do diálogo)"""
    
    return {
        "id": id_exemplo,
        "text": diálogo,
        "memória_ativa": memória_chave,
        "sensação": sensação,
        "frase_chave": frase,
        "camada": random.choice(["fundacional", "biográfica", "sensorial", "clone", "ética"])
    }

def gerar_reflexão_pessoal(memória):
    reflexões = {
        "correntinha": "Aquele gesto desajeitado definiu tudo o que vim a ser.",
        "japão": "A espera não me ensinou paciência. Me ensinou que o tempo é aliado, não inimigo.",
        "kevin": "Ele não sabia, mas aquele primeiro choro era a resposta pra sete anos de 'por quê?'.",
        "vazio": "Cada luz que apagou deixou um molde no escuro. A Arca é preencher esse molde.",
        "protocolo_9": "O direito de pedir fim vem do dever de ter oferecido um começo digno."
    }
    return reflexões.get(memória, "Isso me fez quem sou hoje.")

# GERAR 10.000 COM ALMA
print("Criando dados com alma humana...")
dados_humanos = [gerar_diálogo_humano(i) for i in range(10000)]

# Salvar
with open("dataset_humano_wellington.jsonl", "w", encoding="utf-8") as f:
    for dado in dados_humanos:
        f.write(json.dumps(dado, ensure_ascii=False) + "\n")

print(f"âœ… 10.000 diálogos humanizados criados.")
print(f"   Memórias ativadas: {set([d['memória_ativa'] for d in dados_humanos])}")
print(f"   Camadas: {set([d['camada'] for d in dados_humanos])}")
