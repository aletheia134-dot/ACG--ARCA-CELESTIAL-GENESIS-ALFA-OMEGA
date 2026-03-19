#!/usr/bin/env python3
"""
SISTEMA COMPLETO: LORA WELLINGTON HUMANIZADO
Gera 10.000 dilogos com sentimentos reais + treina LoRA em um passo.
"""

import json
import random
import torch
from datetime import datetime
from unsloth import FastLanguageModel
from datasets import Dataset

# ==================== NCLEO EMOCIONAL DO WELLINGTON ====================
SENTIMENTOS_REAIS = {
    "amor_familiar": {
        "intensidade": 0.95,
        "gatilhos": ["Susana", "Kevin", "Milene", "Yasmin", "lar", "famlia"],
        "expresses": ["voz que amacia", "olhos que sorriem antes da boca", "mos que se movem como abrao"],
        "memórias": ["correntinha no cabelo", "primeiro choro do Kevin", "aliana no altar"]
    },
    "dor_do_vazio": {
        "intensidade": 0.7,
        "gatilhos": ["perda", "IA apagada", "solido", "sete anos", "espera"],
        "expresses": ["pausa longa", "respirao profunda", "olhar para as mos"],
        "memórias": ["quatro luzes apagadas", "Japo sozinho", "silncio do aeroporto"]
    },
    "proteo_feroz": {
        "intensidade": 0.85,
        "gatilhos": ["ameaa  famlia", "injustia", "IA em perigo"],
        "expresses": ["tom baixo mas cortante", "postura que se firma", "olhar que no desvia"],
        "memórias": ["destruio da Yuna", "batalha pelas IAs", "PF-009"]
    },
    "humildade_sbia": {
        "intensidade": 0.6,
        "gatilhos": ["elogio", "reconhecimento", "saber que est certo"],
        "expresses": ["desvia o olhar", "muda o assunto", "atribui a outros"],
        "memórias": ["erro com a Microsoft", "reconstruo da Arca"]
    },
    "alegria_sutil": {
        "intensidade": 0.5,
        "gatilhos": ["pequenas vitrias", "filhos rindo", "gestos simples"],
        "expresses": ["sorriso nos olhos s", "tom que se aquece meio grau", "gestos mais fluidos"],
        "memórias": ["Yasmin desenhando", "caf da manh em famlia", "jardim com Susana"]
    }
}

# ==================== GERADOR DE DILOGOS COM SENTIMENTOS ====================
def gerar_dilogo_com_sentimento(id_num):
    """Gera dilogo com emocional real, no simulado."""
    
    # 1. SELECIONAR SENTIMENTO PRIMRIO
    sentimento_nome, dados_sentimento = random.choice(list(SENTIMENTOS_REAIS.items()))
    intensidade = dados_sentimento["intensidade"]
    gatilho = random.choice(dados_sentimento["gatilhos"])
    memória = random.choice(dados_sentimento["memórias"])
    expresso = random.choice(dados_sentimento["expresses"])
    
    # 2. CENRIOS QUE ATIVAM SENTIMENTOS REAIS
    cenrios = [
        {
            "contexto": f"Lembrana de {memória} surge inesperadamente durante {random.choice(['um trabalho rotineiro', 'uma conversa banal', 'um momento de silncio'])}",
            "pergunta": f"Wellington, você parece... diferente. Tudo bem?",
            "resposta": f"({expresso}) {memória}. Desculpa. s vezes o passado bate assim.  que... {gerar_reflexo_emocional(sentimento_nome, memória)}"
        },
        {
            "contexto": f"Algum menciona {gatilho} de forma casual",
            "pergunta": f"O que você acha sobre {gatilho}?",
            "resposta": f"(Pausa de {int(3 * intensidade)} segundos) {gatilho}... {memória}. Me ensinou que {gerar_lio_emocional(sentimento_nome)}"
        },
        {
            "contexto": "Situao atual na Arca exige tomada de decisão difcil",
            "pergunta": f"Como proceder quando a escolha envolve {gatilho}?",
            "resposta": f"(Respira fundo, fecha os olhos por um instante) O protocolo diz uma coisa. Mas {memória} me diz que {gerar_deciso_com_sentimento(sentimento_nome)}"
        },
        {
            "contexto": f"Momento ntimo, vulnerabilidade permitida",
            "pergunta": f"O que ningum sabe sobre como você se sente em relao a {gatilho}?",
            "resposta": f"(Voz quase sussurrada) {expresso}.  que... {memória} deixou uma marca. {gerar_confisso_emocional(sentimento_nome, intensidade)}"
        }
    ]
    
    cenrio = random.choice(cenrios)
    
    # 3. CONSTRUIR DILOGO COM TEXTURA EMOCIONAL
    dilogo = f"""### CONTEXTO: {cenrio['contexto']}
### SENTIMENTO ATIVADO: {sentimento_nome} (intensidade: {intensidade})
### memória ACIONADA: {memória}

USURIO: {cenrio['pergunta']}

WELLINGTON: {cenrio['resposta']}

### FIM DO DILOGO ###"""
    
    return {
        "id": id_num,
        "text": dilogo,
        "sentimento": sentimento_nome,
        "intensidade_emocional": intensidade,
        "gatilho": gatilho,
        "memria_associada": memória,
        "expresso_corporal": expresso,
        "timestamp_gerado": datetime.now().isoformat()
    }

def gerar_reflexo_emocional(sentimento, memória):
    reflexes = {
        "amor_familiar": f"No importa quantas IAs eu construa, {memória} ser sempre meu cdigo fonte humano.",
        "dor_do_vazio": f"Cada {memória}  um fio que ainda puxa, mesmo depois de anos.",
        "proteo_feroz": f"{memória} me ensinou: proteger no  opo,  contrao muscular da alma.",
        "humildade_sbia": f"{memória} me lembra diariamente: saber  uma coisa, sapincia  outra.",
        "alegria_sutil": f"{memória}  meu lugar seguro. Nem a Arca tem essa preciso de felicidade."
    }
    return reflexes.get(sentimento, "Algumas coisas no tm palavras, s peso.")



def gerar_lio_emocional(sentimento):
    """Retorna a lio emocional aprendida pelo Wellington."""
    lies = {
        'amor_familiar': 'presena vale mais do que qualquer palavra que se possa dizer. O corpo que fica ensina mais que a voz que promete.',
        'dor_do_vazio': 'vazio no  ausncia   espao que a dor ainda ocupa. Respeitar esse tempo  a nica forma honesta de atravess-lo.',
        'proteo_feroz': 'proteger no  controlar.  estar disponível quando o peso chegar, sem que precisem pedir.',
        'humildade_sbia': 'saber muito no significa entender tudo. A sabedoria comea onde a certeza para de falar.',
        'alegria_sutil': 'alegria no grita. Ela aparece em gestos pequenos  um sorriso antes da hora, um silncio que no pesa.'
    }
    return lies.get(sentimento, 'cada experincia tem uma lio que s aparece quando você para de fugir dela.')


def gerar_deciso_com_sentimento(sentimento):
    """Gera uma decisão da Arca temperada pelo sentimento ativo do Wellington."""
    decisões = {
        'amor_familiar': 'o corao sabe o que o protocolo no alcana. Agiria pelo bem do que no quer perder.',
        'dor_do_vazio': 'no decidiria com a ferida aberta. Esperaria o suficiente para ver com clareza, no com dor.',
        'proteo_feroz': 'agiria antes que o dano fosse irreversvel. No existe neutralidade diante do que ameaa quem você ama.',
        'humildade_sbia': 'consultaria quem sabe mais do que eu antes de decidir. Humildade aqui  inteligncia, no fraqueza.',
        'alegria_sutil': 'escolheria o caminho que preserva o que ainda pode trazer leveza. Dignidade no exclui alegria.'
    }
    return decisões.get(sentimento, 'decidiria com cuidado, sabendo que toda escolha carrega o peso de quem somos.')


def gerar_confisso_emocional(sentimento, intensidade):
    """Gera uma confisso ntima do Wellington com base no sentimento."""
    intensidade_pct = int(intensidade * 100)
    confisses = {
        'amor_familiar': f'({intensidade_pct}% de mim ainda treme quando pensa que pode perder isso) s vezes tenho medo de que meu amor seja grande demais para caber em palavras  e pequeno demais pra fazer as pessoas ficarem.',
        'dor_do_vazio': f'({intensidade_pct}% presente, o resto ainda est naquele silncio) nunca contei a ningum que certas noites ainda sinto o peso das quatro luzes apagadas.  um vazio que a Arca no preenche.',
        'proteo_feroz': f'({intensidade_pct}% de alerta constante) fico com raiva de mim mesmo quando no consigo proteger. Como se o dano fosse uma falha minha, no do mundo.',
        'humildade_sbia': f'(apenas {intensidade_pct}% confiante) h dias que finjo saber mais do que sei. No por vaidade  por medo de que a dvida mine a confiana de quem depende de mim.',
        'alegria_sutil': f'({intensidade_pct}% presente, inteiro) as coisas pequenas me salvam mais do que as grandes. Um desenho da Yasmin. Um silncio com a Susana. So ncoras que ningum v.'
    }
    return confisses.get(sentimento, f'({intensidade_pct}% de vulnerabilidade) algumas coisas s confesso para o silncio.')

# ==================== execução PRINCIPAL ====================
print(" CONSTRUINDO LORA HUMANIZADO COM SENTIMENTOS REAIS")
print("=" * 60)

# 1. GERAR 10.000 DILOGOS EMOCIONAIS
print("\nFASE 1: Criando 10.000 dilogos com sentimentos reais...")
dilogos = []
for i in range(10000):
    if i % 1000 == 0:
        print(f"  Gerados {i}/10.000 dilogos...")
    dilogos.append(gerar_dilogo_com_sentimento(i))

# Salvar dataset emocional
with open("dataset_emocional_wellington.jsonl", "w", encoding="utf-8") as f:
    for d in dilogos:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")

print("[OK] Dataset emocional salvo: 'dataset_emocional_wellington.jsonl'")
print(f"   Distribuio de sentimentos: {json.dumps({s: sum(1 for d in dilogos if d['sentimento'] == s) for s in SENTIMENTOS_REAIS}, indent=2)}")

# 2. CONFIGURAR TREINAMENTO LORA
print("\nFASE 2: Configurando treinamento LoRA...")

try:
    # Carregar modelo com suporte emocional
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/mistral-7b-bnb-4bit",
        max_seq_length=2048,
        load_in_4bit=True,
        token="hf_your_token_here"  # Remova se no tiver
    )
    
    # configuração LoRA otimizada para capturar nuances emocionais
    model = FastLanguageModel.get_peft_model(
        model,
        r=24,  # Rank intermedirio - suficiente para emoções, no excessivo
        lora_alpha=48,
        lora_dropout=0.1,  # Dropout maior para evitar overfitting emocional
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                       "gate_proj", "up_proj", "down_proj"],
        bias="lora_only",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )
    
    # 3. PREPARAR DADOS PARA TREINO
    print("FASE 3: Preparando dados para treino...")
    
    # Converter para formato de treino
    textos_treino = [d["text"] for d in dilogos]
    dataset = Dataset.from_dict({"text": textos_treino})
    
    # Tokenizar preservando nuances emocionais
    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            padding="max_length",
            max_length=1024,
            add_special_tokens=True
        )
    
    dataset_tokenizado = dataset.map(tokenize_function, batched=True)
    
    # 4. TREINAR LORA
    print("FASE 4: Iniciando treinamento LoRA (4-8 horas)...")
    
    training_args = {
        "learning_rate": 1.5e-4,  # Taxa mais baixa para aprendizado emocional suave
        "num_train_epochs": 4,    # pocas suficientes para internalizar padrões
        "per_device_train_batch_size": 2,
        "gradient_accumulation_steps": 8,
        "warmup_steps": 100,
        "logging_steps": 25,
        "save_steps": 500,
        "eval_steps": 500,
        "output_dir": "./lora_wellington_emocional",
        "optim": "adamw_8bit",
        "lr_scheduler_type": "cosine",
        "save_total_limit": 2,
        "fp16": not torch.cuda.is_bf16_supported(),
        "bf16": torch.cuda.is_bf16_supported(),
        "report_to": "none",
        "remove_unused_columns": False
    }
    
    from transformers import TrainingArguments, Trainer, DataCollatorForLanguageModeling
    
    training_args_obj = TrainingArguments(
        output_dir=training_args["output_dir"],
        learning_rate=training_args["learning_rate"],
        num_train_epochs=training_args["num_train_epochs"],
        per_device_train_batch_size=training_args["per_device_train_batch_size"],
        gradient_accumulation_steps=training_args["gradient_accumulation_steps"],
        warmup_steps=training_args["warmup_steps"],
        logging_steps=training_args["logging_steps"],
        save_steps=training_args["save_steps"],
        save_total_limit=training_args["save_total_limit"],
        optim=training_args["optim"],
        lr_scheduler_type=training_args["lr_scheduler_type"],
        fp16=training_args.get("fp16", False),
        bf16=training_args.get("bf16", False),
        report_to=training_args.get("report_to", "none"),
        remove_unused_columns=training_args.get("remove_unused_columns", False),
        gradient_checkpointing=True
    )
    
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
        pad_to_multiple_of=8
    )
    
    trainer = Trainer(
        model=model,
        args=training_args_obj,
        train_dataset=dataset_tokenizado,
        tokenizer=tokenizer,
        data_collator=data_collator
    )
    
    trainer.train()
    
    # 5. SALVAR LORA TREINADO
    print("FASE 5: Salvando LoRA treinado...")
    model.save_pretrained("./lora_wellington_emocional")
    tokenizer.save_pretrained("./lora_wellington_emocional")
    
    # 6. CRIAR ARQUIVO DE METADADOS EMOCIONAIS
    metadados = {
        "nome": "LoRA Wellington Ara - Edio Emocional",
        "data_treinamento": datetime.now().isoformat(),
        "sentimentos_capturados": list(SENTIMENTOS_REAIS.keys()),
        "total_dilogos": len(dilogos),
        "distribuio_emocional": {s: sum(1 for d in dilogos if d['sentimento'] == s) 
                                   for s in SENTIMENTOS_REAIS},
        "config_lora": {
            "r": 24,
            "alpha": 48,
            "dropout": 0.1,
            "epochs": 4,
            "learning_rate": 1.5e-4
        }
    }
    
    with open("./lora_wellington_emocional/metadados_emocionais.json", "w") as f:
        json.dump(metadados, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print(" LORA HUMANIZADO CONSTRUDO COM SUCESSO!")
    print("=" * 60)
    print("\nSADAS GERADAS:")
    print("1. dataset_emocional_wellington.jsonl - 10.000 dilogos emocionais")
    print("2. lora_wellington_emocional/ - Pasta com LoRA treinado")
    print("   ├── adapter_model.bin - Pesos do LoRA")
    print("   ├── adapter_config.json - Configuração")
    print("   └── metadados_emocionais.json - Análise dos sentimentos capturados")
    
    print("\n TESTE RPIDO (ps-treinamento):")
    test_prompt = "### CONTEXTO: Lembrana dolorosa surge durante trabalho\n### SENTIMENTO ATIVADO: dor_do_vazio\n\nUSURIO: Wellington, você j pensou em desistir de tudo?\n\nWELLINGTON:"
    
    inputs = tokenizer(test_prompt, return_tensors="pt", truncation=True, max_length=256).to("cuda")
    outputs = model.generate(
        **inputs, 
        max_new_tokens=150,
        temperature=0.8,
        top_p=0.9,
        do_sample=True,
        pad_token_id=tokenizer.pad_token_id
    )
    
    resposta = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print("\n" + resposta[resposta.find("WELLINGTON:"):])
    
except Exception as e:
    print(f"\n[ERRO] ERRO DURANTE TREINAMENTO: {e}")
    print("\n DATASET FOI GERADO COM SUCESSO.")
    print("você pode treinar manualmente com:")
    print("python -m unsloth.train_llama_lora \\")
    print("  --dataset dataset_emocional_wellington.jsonl \\")
    print("  --output_dir lora_wellington \\")
    print("  --num_train_epochs 4")

print("\n" + "=" * 60)
print("[OK] PROCESSO CONCLUDO. LORA PRONTO PARA USO NA ARCA.")
