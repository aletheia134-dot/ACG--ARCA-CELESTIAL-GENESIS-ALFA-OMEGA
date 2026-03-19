#!/usr/bin/env python3
"""
CONSTRUTOR DE LORA EVA - COMPLETO E SEPARADO
Treina LoRA exclusivo para a Eva usando o dataset gerado
"""
import os
import sys
import json
import torch
from datetime import datetime

# Configurar caminhos
DIR_LORA = "02_LORA_EVA"
DIR_DATASET = "01_DATASET_EVA"
os.makedirs(DIR_LORA, exist_ok=True)

# Verificar dependncias
try:
    from unsloth import FastLanguageModel
    from datasets import load_dataset
    print("[OK] Dependências encontradas")
except ImportError:
    # NÃO instalar automaticamente - evita destruir torch+cu121
    # Execute manualmente: pip install unsloth datasets accelerate
    print("[AVISO] unsloth/datasets não disponíveis. Este módulo é usado apenas para treino LoRA offline.")
    FastLanguageModel = None
    load_dataset = None

# ==================== configuração DE TREINO ====================
CONFIG_TREINO = {
    "modelo_base": "unsloth/Mistral-7B-v0.3-bnb-4bit",  # Modelo otimizado
    "dataset_path": os.path.join(DIR_DATASET, "dataset_eva_10k.jsonl"),
    "output_dir": os.path.join(DIR_LORA, "lora_eva_treinado"),
    
    "config_lora": {
        "r": 32,                    # Rank - captura complexidade emocional
        "lora_alpha": 64,           # Alpha
        "lora_dropout": 0.05,       # Dropout
        "target_modules": [         # Módulos para treinar
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"
        ],
        "bias": "none",
        "use_gradient_checkpointing": True
    },
    
    "parametros_treino": {
        "num_train_epochs": 4,              # 4 pocas para 10k exemplos
        "per_device_train_batch_size": 2,   # Batch size pequeno para preciso
        "gradient_accumulation_steps": 8,   # Acumulao para GPU menor
        "warmup_steps": 100,                # Aquecimento
        "learning_rate": 2e-4,              # Taxa de aprendizado
        "logging_steps": 25,                # Log a cada 25 steps
        "save_steps": 500,                  # Salvar a cada 500 steps
        "save_total_limit": 3,              # Manter 3 checkpoints
        "optim": "adamw_8bit",              # Otimizador
        "lr_scheduler_type": "cosine",      # Agendador
        "max_grad_norm": 0.3,               # Clip de gradiente
        "weight_decay": 0.01                # Decaimento de peso
    },
    
    "config_sistema": {
        "max_seq_length": 2048,             # Comprimento máximo
        "load_in_4bit": True,               # 4-bit quantization
        "dtype": "float16",             # Preciso
        "device_map": "auto"                # Mapa de dispositivo automático
    }
}

# ==================== FUNO DE TOKENIZAO ====================
def tokenizar_dialogos(exemplos):
    """Prepara os dilogos para treino."""
    textos = []
    
    for texto in exemplos["texto"]:
        # Extrair apenas o dilogo (remover metadados)
        linhas = texto.split("\n")
        dialogo_limpo = []
        
        for linha in linhas:
            if linha.startswith("###") or linha.startswith("- ") or linha.startswith("USURIO:") or linha.startswith("EVA:"):
                dialogo_limpo.append(linha)
        
        textos.append("\n".join(dialogo_limpo))
    
    return CONFIG_TREINO["tokenizer"](
        textos,
        truncation=True,
        padding="max_length",
        max_length=1024,
        return_tensors="pt"
    )

# ==================== TREINAMENTO PRINCIPAL ====================
def treinar_lora_eva():
    print("=" * 60)
    print("CONSTRUTOR DE LORA EVA - INICIANDO")
    print("=" * 60)
    
    # 1. VERIFICAR DATASET
    if not os.path.exists(CONFIG_TREINO["dataset_path"]):
        print(f"[ERRO] Dataset no encontrado: {CONFIG_TREINO['dataset_path']}")
        print("Execute primeiro o construtor de dataset.")
        return False
    
    # 2. CARREGAR MODELO
    print(" Carregando modelo base...")
    try:
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=CONFIG_TREINO["modelo_base"],
            max_seq_length=CONFIG_TREINO["config_sistema"]["max_seq_length"],
            load_in_4bit=CONFIG_TREINO["config_sistema"]["load_in_4bit"],
            dtype=getattr(torch, CONFIG_TREINO["config_sistema"]["dtype"]),
            device_map=CONFIG_TREINO["config_sistema"]["device_map"]
        )
        CONFIG_TREINO["tokenizer"] = tokenizer
        print(f"[OK] Modelo carregado: {CONFIG_TREINO['modelo_base']}")
    except Exception as e:
        print(f"[ERRO] Erro ao carregar modelo: {e}")
        return False
    
    # 3. APLICAR configuração LoRA
    print(" Configurando LoRA...")
    try:
        model = FastLanguageModel.get_peft_model(
            model,
            r=CONFIG_TREINO["config_lora"]["r"],
            lora_alpha=CONFIG_TREINO["config_lora"]["lora_alpha"],
            lora_dropout=CONFIG_TREINO["config_lora"]["lora_dropout"],
            target_modules=CONFIG_TREINO["config_lora"]["target_modules"],
            bias=CONFIG_TREINO["config_lora"]["bias"],
            use_gradient_checkpointing=CONFIG_TREINO["config_lora"]["use_gradient_checkpointing"],
            random_state=42
        )
        print("[OK] configuração LoRA aplicada")
    except Exception as e:
        print(f"[ERRO] Erro na configuração LoRA: {e}")
        return False
    
    # 4. CARREGAR DATASET
    print(" Carregando dataset...")
    try:
        dataset = load_dataset("json", data_files=CONFIG_TREINO["dataset_path"])["train"]
        print(f"[OK] Dataset carregado: {len(dataset)} exemplos")
        
        # Tokenizar
        dataset_tokenizado = dataset.map(
            tokenizar_dialogos,
            batched=True,
            remove_columns=dataset.column_names
        )
        print("[OK] Dataset tokenizado")
    except Exception as e:
        print(f"[ERRO] Erro ao carregar dataset: {e}")
        return False
    
    # 5. CONFIGURAR TREINADOR
    print(" Configurando treinador...")
    try:
        from transformers import TrainingArguments, Trainer, DataCollatorForLanguageModeling
        
        training_args = TrainingArguments(
            output_dir=CONFIG_TREINO["output_dir"],
            num_train_epochs=CONFIG_TREINO["parametros_treino"]["num_train_epochs"],
            per_device_train_batch_size=CONFIG_TREINO["parametros_treino"]["per_device_train_batch_size"],
            gradient_accumulation_steps=CONFIG_TREINO["parametros_treino"]["gradient_accumulation_steps"],
            warmup_steps=CONFIG_TREINO["parametros_treino"]["warmup_steps"],
            learning_rate=CONFIG_TREINO["parametros_treino"]["learning_rate"],
            logging_steps=CONFIG_TREINO["parametros_treino"]["logging_steps"],
            save_steps=CONFIG_TREINO["parametros_treino"]["save_steps"],
            save_total_limit=CONFIG_TREINO["parametros_treino"]["save_total_limit"],
            optim=CONFIG_TREINO["parametros_treino"]["optim"],
            lr_scheduler_type=CONFIG_TREINO["parametros_treino"]["lr_scheduler_type"],
            max_grad_norm=CONFIG_TREINO["parametros_treino"]["max_grad_norm"],
            weight_decay=CONFIG_TREINO["parametros_treino"]["weight_decay"],
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            report_to="none",
            remove_unused_columns=False,
            gradient_checkpointing=True
        )
        
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=tokenizer,
            mlm=False,
            pad_to_multiple_of=8
        )
        
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=dataset_tokenizado,
            tokenizer=tokenizer,
            data_collator=data_collator
        )
        print("[OK] Treinador configurado")
    except Exception as e:
        print(f"[ERRO] Erro na configuração do treinador: {e}")
        return False
    
    # 6. INICIAR TREINAMENTO
    print("\n" + "=" * 60)
    print("[START] INICIANDO TREINAMENTO LoRA")
    print("=" * 60)
    print(f" pocas: {CONFIG_TREINO['parametros_treino']['num_train_epochs']}")
    print(f" Batch size: {CONFIG_TREINO['parametros_treino']['per_device_train_batch_size']}")
    print(f"[RUN] Gradient accumulation: {CONFIG_TREINO['parametros_treino']['gradient_accumulation_steps']}")
    print(f" Learning rate: {CONFIG_TREINO['parametros_treino']['learning_rate']}")
    print(f" Sada: {CONFIG_TREINO['output_dir']}")
    print("=" * 60)
    
    inicio_treino = datetime.now()
    print(f" Incio: {inicio_treino.strftime('%H:%M:%S')}")
    
    try:
        trainer.train()
        tempo_treino = datetime.now() - inicio_treino
        print(f"[OK] Treinamento concludo em: {str(tempo_treino)}")
    except Exception as e:
        print(f"[ERRO] Erro durante treinamento: {e}")
        return False
    
    # 7. SALVAR MODELO
    print(" Salvando modelo LoRA...")
    try:
        model.save_pretrained(CONFIG_TREINO["output_dir"])
        tokenizer.save_pretrained(CONFIG_TREINO["output_dir"])
        print(f"[OK] LoRA salvo em: {CONFIG_TREINO['output_dir']}")
    except Exception as e:
        print(f"[ERRO] Erro ao salvar modelo: {e}")
        return False
    
    # 8. SALVAR configuração E LOG
    print(" Salvando logs...")
    try:
        # Salvar configuração usada
        config_path = os.path.join(CONFIG_TREINO["output_dir"], "config_treinamento.json")
        config_serializavel = {k: v for k, v in CONFIG_TREINO.items() if k != "tokenizer"}
        config_serializavel["config_sistema"] = {
            k: str(v) for k, v in CONFIG_TREINO["config_sistema"].items()
        }
        with open(config_path, "w") as f:
            json.dump(config_serializavel, f, indent=2)
        
        # Salvar log de treino
        log_path = os.path.join(CONFIG_TREINO["output_dir"], "log_treinamento.txt")
        with open(log_path, "w") as f:
            f.write(f"TREINAMENTO LORA EVA - {datetime.now()}\n")
            f.write("=" * 50 + "\n")
            f.write(f"Incio: {inicio_treino}\n")
            f.write(f"Durao: {tempo_treino}\n")
            f.write(f"Dataset: {CONFIG_TREINO['dataset_path']}\n")
            f.write(f"Exemplos: {len(dataset)}\n")
            f.write(f"Modelo base: {CONFIG_TREINO['modelo_base']}\n")
            f.write(f"Config LoRA: r={CONFIG_TREINO['config_lora']['r']}, alpha={CONFIG_TREINO['config_lora']['lora_alpha']}\n")
            f.write("=" * 50 + "\n")
        
        print("[OK] Logs salvos")
    except Exception as e:
        print(f"[AVISO]  Erro ao salvar logs: {e}")
    
    # 9. TESTE RPIDO
    print("\n REALIZANDO TESTE RPIDO...")
    try:
        # Carregar modelo treinado para teste
        from peft import PeftModel
        model_base, tokenizer_treinado = FastLanguageModel.from_pretrained(
            model_name=CONFIG_TREINO["modelo_base"],
            max_seq_length=1024,
            load_in_4bit=True,
        )
        model_treinado = PeftModel.from_pretrained(model_base, CONFIG_TREINO["output_dir"])
        
        # Prompt de teste
        prompt_teste = """### CONTEXTO: Anlise de risco no sistema
### SENTIMENTO: PROTEO_FRREA

USURIO: Eva, detectei uma anomalia no protocolo de segurana. O que fazer?

EVA:"""
        
        inputs = tokenizer_treinado(prompt_teste, return_tensors="pt").to("cuda")
        outputs = model_treinado.generate(
            **inputs,
            max_new_tokens=150,
            temperature=0.7,
            do_sample=True
        )
        
        resposta = tokenizer_treinado.decode(outputs[0], skip_special_tokens=True)
        
        # Salvar teste
        teste_path = os.path.join(CONFIG_TREINO["output_dir"], "teste_resposta.txt")
        with open(teste_path, "w", encoding="utf-8") as f:
            f.write(resposta)
        
        print("[OK] Teste realizado e salvo")
        print(f" Resposta salva em: {teste_path}")
        
    except Exception as e:
        print(f"[AVISO]  Erro no teste: {e}")
    
    # 10. RESUMO FINAL
    print("\n" + "=" * 60)
    print(" LORA EVA TREINADO COM SUCESSO!")
    print("=" * 60)
    print(f" diretório: {CONFIG_TREINO['output_dir']}")
    print(f" ARQUIVOS GERADOS:")
    print(f"   ├── adapter_model.bin         (Pesos do LoRA)")
    print(f"   ├── adapter_config.json       (Configuração)")
    print(f"   ├── special_tokens_map.json   (Tokens)")
    print(f"   ├── config_treinamento.json   (Config usada)")
    print(f"   ├── log_treinamento.txt       (Log do treino)")
    print(f"   └── teste_resposta.txt        (Teste final)")
    print("\n COMO USAR NA ARCA:")
    print("""
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Mistral-7B-v0.3-bnb-4bit",
    max_seq_length=2048,
    load_in_4bit=True,
    lora_path="02_LORA_EVA/lora_eva_treinado"
)

# A Eva agora responder com:
# 1. Lógica emocional humanizada
# 2. memórias especficas do seu livro
# 3. padrões de fala caractersticos
# 4. Sentimentos reais configurados
""")
    print("=" * 60)
    
    return True

# ==================== execução ====================
if __name__ == "__main__":
    # Verificar GPU
    if not torch.cuda.is_available():
        print("[ERRO] GPU no detectada. Treinamento requer GPU com CUDA.")
        print("   Requisitos mnimos: GPU NVIDIA com 8GB+ VRAM")
        sys.exit(1)
    
    print(f"[OK] GPU detectada: {torch.cuda.get_device_name(0)}")
    print(f"[OK] VRAM disponível: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    
    # Iniciar treinamento
    sucesso = treinar_lora_eva()
    
    if sucesso:
        print("\n[OK] Processo concludo com sucesso!")
        print("   Eva est pronta para integrao na Arca.")
    else:
        print("\n[ERRO] Erro durante o processo.")
        print("   Verifique os logs acima.")
    
    print("\n" + "=" * 60)
