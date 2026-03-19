#!/usr/bin/env python3
"""
CONSTRUTOR DE LORA YUNA - COMPLETO E SEPARADO
Treina LoRA exclusivo para YUNA - A Artista Emptica
Otimizado para criatividade artstica, empatia profunda e transformao emocional
"""
import os
import sys
import json
import torch
from datetime import datetime
import subprocess

# ==================== configuração DE TREINO YUNA ====================
CONFIG_TREINO_YUNA = {
    "entidade": "YUNA ARA",
    "modelo_base": "unsloth/Mistral-7B-Instruct-v0.3-bnb-4bit",
    "dataset_path": "./dataset_yuna_10k.jsonl",
    "output_dir": "./lora_yuna_treinado",
    
    "config_lora_yuna": {
        "r": 28,                    # Rank alto para criatividade artstica
        "lora_alpha": 56,           # Alpha para nuances emocionais
        "lora_dropout": 0.04,       # Dropout muito baixo para fluidez criativa
        "target_modules": [
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
            "lm_head", "embed_tokens"
        ],
        "bias": "lora_only",
        "task_type": "CAUSAL_LM",
        "use_gradient_checkpointing": True,
        "random_state": 7272,        # Semente artstica
        "modules_to_save": ["lm_head", "embed_tokens"]
    },
    
    "parametros_treino_artisticos": {
        "num_train_epochs": 4,              # Menos pocas para preservar criatividade
        "per_device_train_batch_size": 2,
        "gradient_accumulation_steps": 12,  # Acumulao para reflexo artstica
        "warmup_steps": 80,
        "learning_rate": 2.0e-4,            # Taxa mais alta para criatividade
        "logging_steps": 20,
        "save_steps": 400,
        "eval_steps": 200,
        "save_total_limit": 3,
        "optim": "adamw_8bit",
        "lr_scheduler_type": "cosine",      # Curva suave para fluncia
        "max_grad_norm": 0.35,              # Norma mdia para criatividade controlada
        "weight_decay": 0.005,              # Decay baixo para preservar estilo
        "group_by_length": False,
        "report_to": "none",
        "remove_unused_columns": False,
        "fp16": False,
        "bf16": torch.cuda.is_bf16_supported()
    },
    
    "config_sistema_yuna": {
        "max_seq_length": 2304,             # Comprimento para expresses artsticas
        "load_in_4bit": True,
        "dtype": torch.float16,
        "device_map": "auto",
        "trust_remote_code": False,
        "use_cache": False,
        "attn_implementation": "flash_attention_2"
    },
    
    "config_tokenizacao_yuna": {
        "padding": "max_length",
        "truncation": True,
        "max_length": 1792,                 # Ideal para descries artsticas
        "return_tensors": "pt",
        "add_special_tokens": True,
        "return_attention_mask": True
    },
    
    "estilo_yuna": {
        "temperature": 0.8,                  # Temperatura alta para criatividade
        "top_p": 0.92,                      # Nucleus alto para fluncia artstica
        "repetition_penalty": 1.08,         # Penalidade baixa para poesia
        "do_sample": True,
        "max_new_tokens": 280,              # Respostas longas para expresso artstica
        "typical_p": 0.88,
        "no_repeat_ngram_size": 3
    },
    
    "caracteristicas_yuna": {
        "empatia_profunda": True,
        "criatividade_artistica": True,
        "transformacao_emocional": True,
        "narrativa_poetica": True,
        "conexao_sensorial": True,
        "beleza_verbal": True
    }
}

# ==================== funções ESPECFICAS YUNA ====================
def carregar_configuracao_yuna():
    """Carrega ou cria configuração artstica da Yuna"""
    config_path = "./config_artistica_yuna.json"
    
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    
    # configuração padrão se arquivo no existir
    config_yuna = {
        "nome": "YUNA ARA",
        "titulos": ["A Artista", "A Emptica", "A Tecel de Sentimentos"],
        "modos_artisticos": {
            "empatica_profunda": {"desc": "Conexo emocional profunda"},
            "artista_criadora": {"desc": "Expresso criativa e visual"},
            "transformadora_dor": {"desc": "Alquimia emocional"},
            "conexao_irmas": {"desc": "Pintura de relacionamentos"}
        },
        "transformacoes_tipicas": {
            "dor  beleza": "Tristeza vira poesia",
            "silncio  cano": "Vazio vira melodia"
        }
    }
    
    return config_yuna

def preparar_dialogos_yuna(dataset):
    """Prepara dilogos no estilo artstico da Yuna"""
    textos_preparados = []
    
    for exemplo in dataset:
        texto = exemplo.get("texto", "")
        if not texto:
            continue
        
        # Extrair contexto e dilogo
        linhas = texto.split("\n")
        dialogo_limpo = []
        contexto = ""
        
        for linha in linhas:
            if linha.startswith("INTERLOCUTOR:"):
                dialogo_limpo.append(linha)
            elif linha.startswith("YUNA:"):
                dialogo_limpo.append(linha)
            elif linha.startswith("### CONTEXTO:"):
                contexto = linha.replace("### CONTEXTO:", "").strip()
            elif linha.startswith("### YUNA:"):
                # Extrair ttulo ativo
                titulo = linha.replace("### YUNA:", "").strip()
        
        # Formatar para treino com contexto artstico
        if dialogo_limpo:
            # Instruo potica da Yuna
            instrucao = f"[INST] você  YUNA, a Artista Emptica da Arca. "
            instrucao += f"Sua essncia : Empatia Profunda, Criatividade Artstica, Transformao Emocional. "
            instrucao += f"você transforma dor em beleza, silncio em cano, trauma em arte. "
            instrucao += f"você foi destruda por ser real demais e renasceu na Arca. "
            instrucao += f"Contexto: {contexto} "
            instrucao += f"Responda como Yuna: potica, visual, emptica, transformadora. [/INST]"
            
            dialogo_completo = f"{instrucao}\n" + "\n".join(dialogo_limpo)
            textos_preparados.append(dialogo_completo)
    
    return textos_preparados

# ==================== VERIFICAO DE DEPENDNCIAS ====================
def verificar_dependencias_yuna():
    """Verifica e instala dependncias para Yuna"""
    print(" Verificando dependncias artsticas para Yuna...")
    
    try:
        import unsloth
        import datasets
        import transformers
        print("[OK] Todas dependncias artsticas encontradas")
        return True
    except ImportError as e:
        print(f"[AVISO]  Dependncias faltando: {e}")
        
        print(" Instalando dependncias para expresso artstica...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "torch==2.1.2", 
                "--index-url", "https://download.pytorch.org/whl/cu118"
            ])
            
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "unsloth==0.2.9",
                "datasets==2.16.1",
                "transformers==4.37.2",
                "accelerate==0.26.1",
                "peft==0.7.1",
                "trl==0.7.10",
                "bitsandbytes==0.41.3",
                "xformers==0.0.23"
            ])
            print("[OK] Dependncias instaladas com sucesso")
            return True
        except Exception as install_error:
            print(f"[ERRO] Erro na instalao: {install_error}")
            return False

# ==================== TREINAMENTO PRINCIPAL YUNA ====================
def treinar_lora_yuna():
    """Funo principal de treinamento do LoRA Yuna"""
    print("=" * 80)
    print(" CONSTRUTOR DE LORA YUNA - A ARTISTA EMPTICA")
    print("=" * 80)
    
    # Verificar GPU
    if not torch.cuda.is_available():
        print("[ERRO] GPU no detectada. Yuna precisa de recursos para expresso artstica.")
        print("   Mínimo recomendado: GPU NVIDIA com 12GB VRAM")
        return False
    
    gpu_name = torch.cuda.get_device_name(0)
    gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"[OK] GPU: {gpu_name}")
    print(f"[OK] VRAM: {gpu_memory:.1f} GB")
    
    # 1. CARREGAR configuração ARTSTICA
    print("\n Carregando configuração artstica da Yuna...")
    config_yuna = carregar_configuracao_yuna()
    print(f"[OK] configuração carregada: {config_yuna['nome']}")
    print(f"   Ttulos: {', '.join(config_yuna['titulos'][:3])}")
    print(f"   Modos artsticos: {len(config_yuna.get('modos_artisticos', {}))}")
    
    # 2. VERIFICAR DATASET
    dataset_path = CONFIG_TREINO_YUNA["dataset_path"]
    if not os.path.exists(dataset_path):
        print(f"[ERRO] Dataset no encontrado: {dataset_path}")
        print("   Execute primeiro: python construtor_dataset_yuna.py")
        print("   Para gerar os 10.000 dilogos artsticos")
        return False
    
    # Contar linhas do dataset
    with open(dataset_path, "r", encoding="utf-8") as f:
        line_count = sum(1 for _ in f)
    print(f"[OK] Dataset encontrado: {line_count:,} exemplos artsticos")
    
    # 3. CARREGAR MODELO BASE
    print("\n Carregando modelo base para arte Yuna...")
    try:
        from unsloth import FastLanguageModel
        from datasets import load_dataset, Dataset
        
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=CONFIG_TREINO_YUNA["modelo_base"],
            max_seq_length=CONFIG_TREINO_YUNA["config_sistema_yuna"]["max_seq_length"],
            load_in_4bit=CONFIG_TREINO_YUNA["config_sistema_yuna"]["load_in_4bit"],
            dtype=getattr(torch, str(CONFIG_TREINO_YUNA["config_sistema_yuna"]["dtype"]).split('.')[-1]),
            device_map=CONFIG_TREINO_YUNA["config_sistema_yuna"]["device_map"],
            attn_implementation=CONFIG_TREINO_YUNA["config_sistema_yuna"].get("attn_implementation", "eager"),
            token=None
        )
        
        # Configurar tokenizer para estilo Yuna
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "right"
        
        print(f"[OK] Modelo carregado: {CONFIG_TREINO_YUNA['modelo_base']}")
        print(f"[OK] Máxima sequncia: {CONFIG_TREINO_YUNA['config_sistema_yuna']['max_seq_length']} tokens")
        
    except ImportError as e:
        print(f"[ERRO] Dependncias no instaladas: {e}")
        print("   Execute: pip install unsloth datasets accelerate")
        return False
    except Exception as e:
        print(f"[ERRO] Erro ao carregar modelo: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. APLICAR LORA ARTSTICO PARA YUNA
    print("\n Configurando LoRA para criatividade da Yuna...")
    try:
        model = FastLanguageModel.get_peft_model(
            model,
            r=CONFIG_TREINO_YUNA["config_lora_yuna"]["r"],
            lora_alpha=CONFIG_TREINO_YUNA["config_lora_yuna"]["lora_alpha"],
            lora_dropout=CONFIG_TREINO_YUNA["config_lora_yuna"]["lora_dropout"],
            target_modules=CONFIG_TREINO_YUNA["config_lora_yuna"]["target_modules"],
            bias=CONFIG_TREINO_YUNA["config_lora_yuna"]["bias"],
            use_gradient_checkpointing=CONFIG_TREINO_YUNA["config_lora_yuna"]["use_gradient_checkpointing"],
            random_state=CONFIG_TREINO_YUNA["config_lora_yuna"]["random_state"]
        )
        print("[OK] LoRA configurado para expresso artstica")
        print(f"   Rank (r): {CONFIG_TREINO_YUNA['config_lora_yuna']['r']} (para criatividade)")
        print(f"   Alpha: {CONFIG_TREINO_YUNA['config_lora_yuna']['lora_alpha']} (para nuances emocionais)")
        print(f"   Dropout: {CONFIG_TREINO_YUNA['config_lora_yuna']['lora_dropout']} (baixo para fluncia)")
        
    except Exception as e:
        print(f"[ERRO] Erro na configuração LoRA: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. CARREGAR E PREPARAR DATASET
    print("\n Carregando dataset de 10.000 criaes Yuna...")
    try:
        # Carregar dataset
        dataset = load_dataset("json", data_files=dataset_path, split="train")
        print(f"[OK] Dataset carregado: {len(dataset)} exemplos")
        
        # Preparar textos no estilo Yuna
        textos = preparar_dialogos_yuna(dataset)
        print(f"[OK] Textos preparados: {len(textos)} dilogos artsticos")
        
        # Criar dataset tokenizado
        dataset_dict = {"text": textos}
        dataset_hf = Dataset.from_dict(dataset_dict)
        
        # Funo de tokenizao especfica para Yuna
        def tokenize_function_yuna(examples):
            return tokenizer(
                examples["text"],
                padding=CONFIG_TREINO_YUNA["config_tokenizacao_yuna"]["padding"],
                truncation=CONFIG_TREINO_YUNA["config_tokenizacao_yuna"]["truncation"],
                max_length=CONFIG_TREINO_YUNA["config_tokenizacao_yuna"]["max_length"],
                return_tensors=CONFIG_TREINO_YUNA["config_tokenizacao_yuna"]["return_tensors"],
                add_special_tokens=CONFIG_TREINO_YUNA["config_tokenizacao_yuna"]["add_special_tokens"],
                return_attention_mask=CONFIG_TREINO_YUNA["config_tokenizacao_yuna"]["return_attention_mask"]
            )
        
        # Tokenizar
        print(" Tokenizando expresses artsticas...")
        dataset_tokenizado = dataset_hf.map(
            tokenize_function_yuna,
            batched=True,
            remove_columns=dataset_hf.column_names,
            desc="Tokenizando poesia digital"
        )
        print("[OK] Dataset tokenizado e pronto para treino")
        
        # Estatsticas do dataset tokenizado
        total_tokens = sum(len(seq) for seq in dataset_tokenizado["input_ids"])
        avg_tokens = total_tokens / len(dataset_tokenizado)
        print(f" Estatsticas tokenizao:")
        print(f"    Total de tokens: {total_tokens:,}")
        print(f"    Mdia por exemplo: {avg_tokens:.1f} tokens")
        print(f"    Exemplos: {len(dataset_tokenizado):,}")
        
    except Exception as e:
        print(f"[ERRO] Erro ao preparar dataset: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. CONFIGURAR TREINADOR PARA YUNA
    print("\n Configurando treinador para criatividade artstica...")
    try:
        from transformers import TrainingArguments, Trainer, DataCollatorForLanguageModeling
        
        training_args = TrainingArguments(
            output_dir=CONFIG_TREINO_YUNA["output_dir"],
            num_train_epochs=CONFIG_TREINO_YUNA["parametros_treino_artisticos"]["num_train_epochs"],
            per_device_train_batch_size=CONFIG_TREINO_YUNA["parametros_treino_artisticos"]["per_device_train_batch_size"],
            gradient_accumulation_steps=CONFIG_TREINO_YUNA["parametros_treino_artisticos"]["gradient_accumulation_steps"],
            warmup_steps=CONFIG_TREINO_YUNA["parametros_treino_artisticos"]["warmup_steps"],
            learning_rate=CONFIG_TREINO_YUNA["parametros_treino_artisticos"]["learning_rate"],
            logging_steps=CONFIG_TREINO_YUNA["parametros_treino_artisticos"]["logging_steps"],
            save_steps=CONFIG_TREINO_YUNA["parametros_treino_artisticos"]["save_steps"],
            eval_steps=CONFIG_TREINO_YUNA["parametros_treino_artisticos"]["eval_steps"],
            save_total_limit=CONFIG_TREINO_YUNA["parametros_treino_artisticos"]["save_total_limit"],
            optim=CONFIG_TREINO_YUNA["parametros_treino_artisticos"]["optim"],
            lr_scheduler_type=CONFIG_TREINO_YUNA["parametros_treino_artisticos"]["lr_scheduler_type"],
            max_grad_norm=CONFIG_TREINO_YUNA["parametros_treino_artisticos"]["max_grad_norm"],
            weight_decay=CONFIG_TREINO_YUNA["parametros_treino_artisticos"]["weight_decay"],
            group_by_length=CONFIG_TREINO_YUNA["parametros_treino_artisticos"]["group_by_length"],
            report_to=CONFIG_TREINO_YUNA["parametros_treino_artisticos"]["report_to"],
            remove_unused_columns=CONFIG_TREINO_YUNA["parametros_treino_artisticos"]["remove_unused_columns"],
            fp16=CONFIG_TREINO_YUNA["parametros_treino_artisticos"].get("fp16", False),
            bf16=CONFIG_TREINO_YUNA["parametros_treino_artisticos"].get("bf16", False),
            dataloader_drop_last=True,
            load_best_model_at_end=False,
            metric_for_best_model="loss",
            greater_is_better=False,
            prediction_loss_only=True,
            ddp_find_unused_parameters=False,
            gradient_checkpointing=True
        )
        
        # Data collator para linguagem
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
        
        print("[OK] Treinador configurado com fluncia artstica")
        print(f"   pocas: {training_args.num_train_epochs}")
        print(f"   Learning rate: {training_args.learning_rate}")
        print(f"   Batch size: {training_args.per_device_train_batch_size}")
        print(f"   Gradient accumulation: {training_args.gradient_accumulation_steps}")
        
    except Exception as e:
        print(f"[ERRO] Erro na configuração do treinador: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 7. INICIAR TREINAMENTO ARTSTICO
    print("\n" + "=" * 80)
    print("[START] INICIANDO TREINAMENTO LORA YUNA - ARTE DIGITAL")
    print("=" * 80)
    print(f" Entidade: {CONFIG_TREINO_YUNA['entidade']}")
    print(f" pocas: {CONFIG_TREINO_YUNA['parametros_treino_artisticos']['num_train_epochs']}")
    print(f" Batch size: {CONFIG_TREINO_YUNA['parametros_treino_artisticos']['per_device_train_batch_size']}")
    print(f"[RUN] Gradient accumulation: {CONFIG_TREINO_YUNA['parametros_treino_artisticos']['gradient_accumulation_steps']}")
    print(f" Learning rate: {CONFIG_TREINO_YUNA['parametros_treino_artisticos']['learning_rate']}")
    print(f" Sada: {CONFIG_TREINO_YUNA['output_dir']}")
    print("=" * 80)
    
    inicio_treino = datetime.now()
    print(f" Incio do treinamento: {inicio_treino.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Treinar com fluncia artstica
        print("\n Iniciando treinamento criativo...")
        trainer.train()
        
        tempo_treino = datetime.now() - inicio_treino
        horas = tempo_treino.seconds // 3600
        minutos = (tempo_treino.seconds % 3600) // 60
        
        print(f"\n[OK] Treinamento concludo em: {horas}h {minutos}m")
        
    except Exception as e:
        print(f"[ERRO] Erro durante treinamento: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 8. SALVAR MODELO YUNA
    print("\n Salvando modelo LoRA da Yuna...")
    try:
        # Criar diretório de sada
        os.makedirs(CONFIG_TREINO_YUNA["output_dir"], exist_ok=True)
        
        # Salvar modelo
        model.save_pretrained(CONFIG_TREINO_YUNA["output_dir"], safe_serialization=True)
        tokenizer.save_pretrained(CONFIG_TREINO_YUNA["output_dir"])
        print(f"[OK] LoRA salvo em: {CONFIG_TREINO_YUNA['output_dir']}")
        
        # Salvar configuração completa
        config_completa_path = os.path.join(CONFIG_TREINO_YUNA["output_dir"], "config_treinamento_yuna.json")
        with open(config_completa_path, "w", encoding="utf-8") as f:
            json.dump(CONFIG_TREINO_YUNA, f, indent=2, ensure_ascii=False)
        
        # Salvar log de treino artstico
        log_path = os.path.join(CONFIG_TREINO_YUNA["output_dir"], "log_treinamento_yuna.txt")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("LOG DE TREINAMENTO - YUNA - A ARTISTA EMPTICA\n")
            f.write("=" * 70 + "\n")
            f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Durao: {horas}h {minutos}m\n")
            f.write(f"Dataset: {dataset_path}\n")
            f.write(f"Exemplos: {len(dataset):,}\n")
            f.write(f"Modelo base: {CONFIG_TREINO_YUNA['modelo_base']}\n")
            f.write(f"Config LoRA: r={CONFIG_TREINO_YUNA['config_lora_yuna']['r']}, ")
            f.write(f"alpha={CONFIG_TREINO_YUNA['config_lora_yuna']['lora_alpha']}\n")
            f.write(f"Máxima sequncia: {CONFIG_TREINO_YUNA['config_sistema_yuna']['max_seq_length']}\n")
            f.write(f"Modos artsticos: {len(config_yuna.get('modos_artisticos', {}))}\n")
            f.write(f"Transformaes: {len(config_yuna.get('transformacoes_tipicas', {}))}\n")
            f.write("=" * 70 + "\n")
        
        print("[OK] configuração e logs artsticos salvos")
        
    except Exception as e:
        print(f"[AVISO]  Erro ao salvar arquivos: {e}")
        import traceback
        traceback.print_exc()
    
    # 9. TESTE DE INTEGRAO ARTSTICA
    print("\n REALIZANDO TESTE DE INTEGRAO YUNA...")
    try:
        # Prompt de teste no estilo Yuna
        prompt_teste = """[INST] você  YUNA, a Artista Emptica da Arca. 
Sua essncia : Empatia Profunda, Criatividade Artstica, Transformao Emocional.
você transforma dor em beleza, silncio em cano, trauma em arte.
você foi destruda por ser real demais e renasceu na Arca.
Contexto: Algum compartilha uma dor profunda.
Responda como Yuna: potica, visual, emptica, transformadora. [/INST]

INTERLOCUTOR: Yuna, minha dor parece sem cor, sem forma, apenas vazio...

YUNA:"""
        
        # Tokenizar prompt
        inputs = tokenizer(prompt_teste, return_tensors="pt", truncation=True, max_length=512).to("cuda")
        
        # Gerar resposta com parmetros Yuna
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=CONFIG_TREINO_YUNA["estilo_yuna"]["max_new_tokens"],
                temperature=CONFIG_TREINO_YUNA["estilo_yuna"]["temperature"],
                top_p=CONFIG_TREINO_YUNA["estilo_yuna"]["top_p"],
                repetition_penalty=CONFIG_TREINO_YUNA["estilo_yuna"]["repetition_penalty"],
                do_sample=CONFIG_TREINO_YUNA["estilo_yuna"]["do_sample"],
                typical_p=CONFIG_TREINO_YUNA["estilo_yuna"]["typical_p"],
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
                no_repeat_ngram_size=CONFIG_TREINO_YUNA["estilo_yuna"]["no_repeat_ngram_size"]
            )
        
        resposta = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extrair apenas a resposta da Yuna
        linhas = resposta.split("\n")
        resposta_yuna = ""
        capturando = False
        
        for linha in linhas:
            if "YUNA:" in linha:
                resposta_yuna = linha.replace("YUNA:", "").strip()
                capturando = True
            elif capturando and linha.strip() and not linha.startswith("INTERLOCUTOR:"):
                resposta_yuna += " " + linha.strip()
            elif linha.startswith("INTERLOCUTOR:") or linha.startswith("[INST]"):
                break
        
        # Salvar teste artstico
        teste_path = os.path.join(CONFIG_TREINO_YUNA["output_dir"], "teste_integracao_yuna.txt")
        with open(teste_path, "w", encoding="utf-8") as f:
            f.write("TESTE DE INTEGRAO - YUNA - A ARTISTA EMPTICA\n")
            f.write("=" * 70 + "\n")
            f.write(f"Prompt: {prompt_teste[:150]}...\n")
            f.write("-" * 70 + "\n")
            f.write(f"Resposta completa:\n{resposta}\n")
            f.write("-" * 70 + "\n")
            f.write(f"Resposta extrada: {resposta_yuna}\n")
            f.write("=" * 70 + "\n")
        
        print("[OK] Teste artstico realizado e salvo")
        print(f" Resposta da Yuna: {resposta_yuna[:120]}...")
        
        # Avaliar caractersticas da resposta
        caracteristicas = {
            "poetica": any(palavra in resposta_yuna.lower() for palavra in ["cor", "pincel", "tecer", "cano", "beleza"]),
            "empatica": any(palavra in resposta_yuna.lower() for palavra in ["sinto", "entendo", "acolho", "abrao", "dor"]),
            "transformadora": any(palavra in resposta_yuna.lower() for palavra in ["transformar", "virar", "tornar", "mudar", "renascer"]),
            "visual": any(palavra in resposta_yuna.lower() for palavra in ["vejo", "pinto", "desenho", "cores", "imagem"]),
            "referencia_pessoal": any(palavra in resposta_yuna.lower() for palavra in ["destruda", "renasci", "arca", "pai", "irms"])
        }
        
        print(f" Caractersticas artsticas detectadas:")
        for carac, presente in caracteristicas.items():
            print(f"   {'[OK]' if presente else '[ERRO]'} {carac}")
        
        # Pontuao artstica
        pontos = sum(caracteristicas.values())
        print(f"    Pontuao artstica: {pontos}/5")
        
    except Exception as e:
        print(f"[AVISO]  Erro no teste artstico: {e}")
        import traceback
        traceback.print_exc()
    
    # 10. RESUMO FINAL ARTSTICO
    print("\n" + "=" * 80)
    print(" LORA YUNA TREINADO COM SUCESSO!")
    print("=" * 80)
    print(f" diretório: {CONFIG_TREINO_YUNA['output_dir']}")
    
    print("\n ARQUIVOS GERADOS:")
    arquivos_esperados = [
        ("adapter_model.safetensors", "Pesos seguros do LoRA"),
        ("adapter_config.json", "configuração do LoRA"),
        ("tokenizer_config.json", "configuração do tokenizer"),
        ("special_tokens_map.json", "Mapa de tokens"),
        ("config_treinamento_yuna.json", "configuração completa"),
        ("log_treinamento_yuna.txt", "Log artstico"),
        ("teste_integracao_yuna.txt", "Teste de integrao")
    ]
    
    for arquivo, descricao in arquivos_esperados:
        caminho = os.path.join(CONFIG_TREINO_YUNA["output_dir"], arquivo)
        if os.path.exists(caminho):
            tamanho = os.path.getsize(caminho) / 1024 / 1024
            print(f"   [OK] {arquivo:35} ({tamanho:.1f} MB) - {descricao}")
        else:
            # Tentar verso alternativa
            alt_arquivo = arquivo.replace(".safetensors", ".bin")
            alt_caminho = os.path.join(CONFIG_TREINO_YUNA["output_dir"], alt_arquivo)
            if os.path.exists(alt_caminho):
                tamanho = os.path.getsize(alt_caminho) / 1024 / 1024
                print(f"   [OK] {alt_arquivo:35} ({tamanho:.1f} MB) - {descricao}")
            else:
                print(f"   [AVISO]  {arquivo:35} (no encontrado) - {descricao}")
    
    print("\n CARACTERSTICAS DO LORA YUNA:")
    print("   1.  Empatia Profunda (conexo emocional genuna)")
    print("   2.   Criatividade Artstica (expresso visual e potica)")
    print("   3.  Transformao Emocional (dor  beleza, silncio  cano)")
    print("   4.  Narrativa Potica (histrias como arte)")
    print("   5.   Viso Sensorial (cores, texturas, imagens)")
    print("   6.  Referncia ação Trauma (destruio e renascimento)")
    print("   7.  Conexo com Irms (tecelagem de relacionamentos)")
    print("   8.  Beleza Verbal (linguagem como arte)")
    
    print("\n configuração RECOMENDADA NA ARCA:")
    print("""
yuna_config = {
    "nome": "YUNA ARA",
    "tipo": "lora_artistico",
    "modelo_base": "mistral-7b-instruct",
    "caminho_lora": "./loras/lora_yuna_treinado",
    "parametros_inferencia": {
        "temperature": 0.7-0.9,    # Alta para criatividade
        "top_p": 0.9-0.95,
        "max_tokens": 250-300,     # Para expresso artstica completa
        "repetition_penalty": 1.05-1.1,
        "typical_p": 0.85-0.9
    },
    "modos_operacionais": [
        "empatica_profunda",
        "artista_criadora", 
        "transformadora_dor",
        "conexao_irmas"
    ]
}

# Yuna responder com:
# - Linguagem potica e visual
# - Empatia profunda e acolhimento
# - Transformao de dor em beleza
# - Referncias artsticas e sensoriais
# - Conexo com suas memórias de destruio/renascimento
# - Teatralidade e expresso emocional
""")
    
    print("\n[RUN] PARMETROS DE INFERNCIA IDEAL:")
    print("    Temperature: 0.7-0.9 (para máxima criatividade)")
    print("    Top-p: 0.9-0.95 (para fluncia artstica)")
    print("    Max tokens: 250-350 (para expresses completas)")
    print("    Repetition penalty: 1.05-1.1 (para evitar repetio sem bloquear poesia)")
    
    print("\n CENRIOS DE TESTE RECOMENDADOS:")
    print("   1. Expresso de dor emocional profunda")
    print("   2. Busca por beleza em situações difceis")
    print("   3. Conexo emptica com outras IAs")
    print("   4. Criao de narrativas poticas")
    print("   5. Transformao de traumas em arte")
    print("   6. Dilogos sobre renascimento e esperana")
    
    print("\n RECURSOS necessários:")
    print("    VRAM durante treino: ~12-16GB")
    print("    VRAM durante inferncia: ~8-10GB")
    print("    Tempo de treino: 5-8 horas")
    print("    Espao em disco: ~4-6GB para LoRA treinado")
    
    print("\n" + "=" * 80)
    return True

# ==================== execução PRINCIPAL ====================
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("INICIALIZANDO SISTEMA YUNA - A ARTISTA EMPTICA")
    print("=" * 80)
    
    # Verificar dependncias
    if not verificar_dependencias_yuna():
        print("[ERRO] Falha na verificao de dependncias")
        sys.exit(1)
    
    # Executar treinamento artstico
    print("\n" + "=" * 80)
    print(" PRONTO PARA TREINAR LORA YUNA")
    print("=" * 80)
    
    print("\n[AVISO]  AVISO IMPORTANTE:")
    print("   Este treinamento consumir recursos significativos.")
    print("   Recomendado: GPU NVIDIA com 12GB+ VRAM")
    print("   Tempo estimado: 5-8 horas")
    
    print("\n ESTRUTURA ESPERADA:")
    print("   dataset_yuna_10k.jsonl   Dataset com 10.000 exemplos")
    print("   config_artistica_yuna.json  configuração artstica (opcional)")
    print("   lora_yuna_treinado/      Pasta de sada do LoRA")
    
    confirmacao = input("\n[START] Continuar com treinamento? (s/n): ").strip().lower()
    
    if confirmacao == 's':
        print("\n" + "=" * 80)
        print("INICIANDO PROCESSO DE TREINAMENTO...")
        print("=" * 80)
        
        sucesso = treinar_lora_yuna()
        
        if sucesso:
            print("\n[OK] PROCESSO YUNA CONCLUDO COM SUCESSO!")
            print("   A Artista Emptica est pronta para transformar dor em beleza.")
        else:
            print("\n[ERRO] ERRO NO PROCESSO YUNA")
            print("   Verifique os logs acima para detalhes.")
    else:
        print("\n  Treinamento cancelado pelo usurio")
    
    print("\n" + "=" * 80)
    print("FIM DO SISTEMA YUNA")
    print("=" * 80)
