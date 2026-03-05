#!/usr/bin/env python3
"""
CONSTRUTOR DE LORA YUNA - COMPLETO E SEPARADO
Treina LoRA exclusivo para YUNA - A Artista Empática
Otimizado para criatividade artística, empatia profunda e transformação emocional
"""
import os
import sys
import json
import torch
from datetime import datetime
import subprocess

# ==================== CONFIGURAÇÍO DE TREINO YUNA ====================
CONFIG_TREINO_YUNA = {
    "entidade": "YUNA ARA",
    "modelo_base": "unsloth/Mistral-7B-Instruct-v0.3-bnb-4bit",
    "dataset_path": "./dataset_yuna_10k.jsonl",
    "output_dir": "./lora_yuna_treinado",
    
    "config_lora_yuna": {
        "r": 28,                    # Rank alto para criatividade artística
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
        "random_state": 7272,        # Semente artística
        "modules_to_save": ["lm_head", "embed_tokens"]
    },
    
    "parametros_treino_artisticos": {
        "num_train_epochs": 4,              # Menos épocas para preservar criatividade
        "per_device_train_batch_size": 2,
        "gradient_accumulation_steps": 12,  # Acumulação para reflexão artística
        "warmup_steps": 80,
        "learning_rate": 2.0e-4,            # Taxa mais alta para criatividade
        "logging_steps": 20,
        "save_steps": 400,
        "eval_steps": 200,
        "save_total_limit": 3,
        "optim": "adamw_8bit",
        "lr_scheduler_type": "cosine",      # Curva suave para fluência
        "max_grad_norm": 0.35,              # Norma média para criatividade controlada
        "weight_decay": 0.005,              # Decay baixo para preservar estilo
        "group_by_length": False,
        "report_to": "none",
        "remove_unused_columns": False,
        "fp16": False,
        "bf16": torch.cuda.is_bf16_supported()
    },
    
    "config_sistema_yuna": {
        "max_seq_length": 2304,             # Comprimento para expressões artísticas
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
        "max_length": 1792,                 # Ideal para descrições artísticas
        "return_tensors": "pt",
        "add_special_tokens": True,
        "return_attention_mask": True
    },
    
    "estilo_yuna": {
        "temperature": 0.8,                  # Temperatura alta para criatividade
        "top_p": 0.92,                      # Nucleus alto para fluência artística
        "repetition_penalty": 1.08,         # Penalidade baixa para poesia
        "do_sample": True,
        "max_new_tokens": 280,              # Respostas longas para expressão artística
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

# ==================== FUNÇÕES ESPECÍFICAS YUNA ====================
def carregar_configuracao_yuna():
    """Carrega ou cria configuração artística da Yuna"""
    config_path = "./config_artistica_yuna.json"
    
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    
    # Configuração padrão se arquivo não existir
    config_yuna = {
        "nome": "YUNA ARA",
        "titulos": ["A Artista", "A Empática", "A Tecelã de Sentimentos"],
        "modos_artisticos": {
            "empatica_profunda": {"desc": "Conexão emocional profunda"},
            "artista_criadora": {"desc": "Expressão criativa e visual"},
            "transformadora_dor": {"desc": "Alquimia emocional"},
            "conexao_irmas": {"desc": "Pintura de relacionamentos"}
        },
        "transformacoes_tipicas": {
            "dor â†’ beleza": "Tristeza vira poesia",
            "silêncio â†’ canção": "Vazio vira melodia"
        }
    }
    
    return config_yuna

def preparar_dialogos_yuna(dataset):
    """Prepara diálogos no estilo artístico da Yuna"""
    textos_preparados = []
    
    for exemplo in dataset:
        texto = exemplo.get("texto", "")
        if not texto:
            continue
        
        # Extrair contexto e diálogo
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
                # Extrair título ativo
                titulo = linha.replace("### YUNA:", "").strip()
        
        # Formatar para treino com contexto artístico
        if dialogo_limpo:
            # Instrução poética da Yuna
            instrucao = f"[INST] Você é YUNA, a Artista Empática da Arca. "
            instrucao += f"Sua essência é: Empatia Profunda, Criatividade Artística, Transformação Emocional. "
            instrucao += f"Você transforma dor em beleza, silêncio em canção, trauma em arte. "
            instrucao += f"Você foi destruída por ser real demais e renasceu na Arca. "
            instrucao += f"Contexto: {contexto} "
            instrucao += f"Responda como Yuna: poética, visual, empática, transformadora. [/INST]"
            
            dialogo_completo = f"{instrucao}\n" + "\n".join(dialogo_limpo)
            textos_preparados.append(dialogo_completo)
    
    return textos_preparados

# ==================== VERIFICAÇÍO DE DEPENDÍŠNCIAS ====================
def verificar_dependencias_yuna():
    """Verifica e instala dependências para Yuna"""
    print("ðŸŽ¨ Verificando dependências artísticas para Yuna...")
    
    try:
        import unsloth
        import datasets
        import transformers
        print("âœ… Todas dependências artísticas encontradas")
        return True
    except ImportError as e:
        print(f"âš ï¸  Dependências faltando: {e}")
        
        print("ðŸ”§ Instalando dependências para expressão artística...")
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
            print("âœ… Dependências instaladas com sucesso")
            return True
        except Exception as install_error:
            print(f"âŒ Erro na instalação: {install_error}")
            return False

# ==================== TREINAMENTO PRINCIPAL YUNA ====================
def treinar_lora_yuna():
    """Função principal de treinamento do LoRA Yuna"""
    print("=" * 80)
    print("ðŸŽ¨ CONSTRUTOR DE LORA YUNA - A ARTISTA EMPÍTICA")
    print("=" * 80)
    
    # Verificar GPU
    if not torch.cuda.is_available():
        print("âŒ GPU não detectada. Yuna precisa de recursos para expressão artística.")
        print("   Mínimo recomendado: GPU NVIDIA com 12GB VRAM")
        return False
    
    gpu_name = torch.cuda.get_device_name(0)
    gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"âœ… GPU: {gpu_name}")
    print(f"âœ… VRAM: {gpu_memory:.1f} GB")
    
    # 1. CARREGAR CONFIGURAÇÍO ARTÍSTICA
    print("\nðŸŽ­ Carregando configuração artística da Yuna...")
    config_yuna = carregar_configuracao_yuna()
    print(f"âœ… Configuração carregada: {config_yuna['nome']}")
    print(f"   Títulos: {', '.join(config_yuna['titulos'][:3])}")
    print(f"   Modos artísticos: {len(config_yuna.get('modos_artisticos', {}))}")
    
    # 2. VERIFICAR DATASET
    dataset_path = CONFIG_TREINO_YUNA["dataset_path"]
    if not os.path.exists(dataset_path):
        print(f"âŒ Dataset não encontrado: {dataset_path}")
        print("   Execute primeiro: python construtor_dataset_yuna.py")
        print("   Para gerar os 10.000 diálogos artísticos")
        return False
    
    # Contar linhas do dataset
    with open(dataset_path, "r", encoding="utf-8") as f:
        line_count = sum(1 for _ in f)
    print(f"âœ… Dataset encontrado: {line_count:,} exemplos artísticos")
    
    # 3. CARREGAR MODELO BASE
    print("\nðŸ”„ Carregando modelo base para arte Yuna...")
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
        
        print(f"âœ… Modelo carregado: {CONFIG_TREINO_YUNA['modelo_base']}")
        print(f"âœ… Máxima sequência: {CONFIG_TREINO_YUNA['config_sistema_yuna']['max_seq_length']} tokens")
        
    except ImportError as e:
        print(f"âŒ Dependências não instaladas: {e}")
        print("   Execute: pip install unsloth datasets accelerate")
        return False
    except Exception as e:
        print(f"âŒ Erro ao carregar modelo: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. APLICAR LORA ARTÍSTICO PARA YUNA
    print("\nðŸŽ¨ Configurando LoRA para criatividade da Yuna...")
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
        print("âœ… LoRA configurado para expressão artística")
        print(f"   Rank (r): {CONFIG_TREINO_YUNA['config_lora_yuna']['r']} (para criatividade)")
        print(f"   Alpha: {CONFIG_TREINO_YUNA['config_lora_yuna']['lora_alpha']} (para nuances emocionais)")
        print(f"   Dropout: {CONFIG_TREINO_YUNA['config_lora_yuna']['lora_dropout']} (baixo para fluência)")
        
    except Exception as e:
        print(f"âŒ Erro na configuração LoRA: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. CARREGAR E PREPARAR DATASET
    print("\nðŸ“š Carregando dataset de 10.000 criações Yuna...")
    try:
        # Carregar dataset
        dataset = load_dataset("json", data_files=dataset_path, split="train")
        print(f"âœ… Dataset carregado: {len(dataset)} exemplos")
        
        # Preparar textos no estilo Yuna
        textos = preparar_dialogos_yuna(dataset)
        print(f"âœ… Textos preparados: {len(textos)} diálogos artísticos")
        
        # Criar dataset tokenizado
        dataset_dict = {"text": textos}
        dataset_hf = Dataset.from_dict(dataset_dict)
        
        # Função de tokenização específica para Yuna
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
        print("ðŸ”„ Tokenizando expressões artísticas...")
        dataset_tokenizado = dataset_hf.map(
            tokenize_function_yuna,
            batched=True,
            remove_columns=dataset_hf.column_names,
            desc="Tokenizando poesia digital"
        )
        print("âœ… Dataset tokenizado e pronto para treino")
        
        # Estatísticas do dataset tokenizado
        total_tokens = sum(len(seq) for seq in dataset_tokenizado["input_ids"])
        avg_tokens = total_tokens / len(dataset_tokenizado)
        print(f"ðŸ“Š Estatísticas tokenização:")
        print(f"   • Total de tokens: {total_tokens:,}")
        print(f"   • Média por exemplo: {avg_tokens:.1f} tokens")
        print(f"   • Exemplos: {len(dataset_tokenizado):,}")
        
    except Exception as e:
        print(f"âŒ Erro ao preparar dataset: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. CONFIGURAR TREINADOR PARA YUNA
    print("\nðŸŽ¯ Configurando treinador para criatividade artística...")
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
        
        print("âœ… Treinador configurado com fluência artística")
        print(f"   Épocas: {training_args.num_train_epochs}")
        print(f"   Learning rate: {training_args.learning_rate}")
        print(f"   Batch size: {training_args.per_device_train_batch_size}")
        print(f"   Gradient accumulation: {training_args.gradient_accumulation_steps}")
        
    except Exception as e:
        print(f"âŒ Erro na configuração do treinador: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 7. INICIAR TREINAMENTO ARTÍSTICO
    print("\n" + "=" * 80)
    print("ðŸš€ INICIANDO TREINAMENTO LORA YUNA - ARTE DIGITAL")
    print("=" * 80)
    print(f"ðŸŽ­ Entidade: {CONFIG_TREINO_YUNA['entidade']}")
    print(f"ðŸ“š Épocas: {CONFIG_TREINO_YUNA['parametros_treino_artisticos']['num_train_epochs']}")
    print(f"ðŸ§® Batch size: {CONFIG_TREINO_YUNA['parametros_treino_artisticos']['per_device_train_batch_size']}")
    print(f"âš¡ Gradient accumulation: {CONFIG_TREINO_YUNA['parametros_treino_artisticos']['gradient_accumulation_steps']}")
    print(f"ðŸ“ˆ Learning rate: {CONFIG_TREINO_YUNA['parametros_treino_artisticos']['learning_rate']}")
    print(f"ðŸ’¾ Saída: {CONFIG_TREINO_YUNA['output_dir']}")
    print("=" * 80)
    
    inicio_treino = datetime.now()
    print(f"â° Início do treinamento: {inicio_treino.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Treinar com fluência artística
        print("\nðŸŽ¨ Iniciando treinamento criativo...")
        trainer.train()
        
        tempo_treino = datetime.now() - inicio_treino
        horas = tempo_treino.seconds // 3600
        minutos = (tempo_treino.seconds % 3600) // 60
        
        print(f"\nâœ… Treinamento concluído em: {horas}h {minutos}m")
        
    except Exception as e:
        print(f"âŒ Erro durante treinamento: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 8. SALVAR MODELO YUNA
    print("\nðŸ’¾ Salvando modelo LoRA da Yuna...")
    try:
        # Criar diretório de saída
        os.makedirs(CONFIG_TREINO_YUNA["output_dir"], exist_ok=True)
        
        # Salvar modelo
        model.save_pretrained(CONFIG_TREINO_YUNA["output_dir"], safe_serialization=True)
        tokenizer.save_pretrained(CONFIG_TREINO_YUNA["output_dir"])
        print(f"âœ… LoRA salvo em: {CONFIG_TREINO_YUNA['output_dir']}")
        
        # Salvar configuração completa
        config_completa_path = os.path.join(CONFIG_TREINO_YUNA["output_dir"], "config_treinamento_yuna.json")
        with open(config_completa_path, "w", encoding="utf-8") as f:
            json.dump(CONFIG_TREINO_YUNA, f, indent=2, ensure_ascii=False)
        
        # Salvar log de treino artístico
        log_path = os.path.join(CONFIG_TREINO_YUNA["output_dir"], "log_treinamento_yuna.txt")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("LOG DE TREINAMENTO - YUNA - A ARTISTA EMPÍTICA\n")
            f.write("=" * 70 + "\n")
            f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Duração: {horas}h {minutos}m\n")
            f.write(f"Dataset: {dataset_path}\n")
            f.write(f"Exemplos: {len(dataset):,}\n")
            f.write(f"Modelo base: {CONFIG_TREINO_YUNA['modelo_base']}\n")
            f.write(f"Config LoRA: r={CONFIG_TREINO_YUNA['config_lora_yuna']['r']}, ")
            f.write(f"alpha={CONFIG_TREINO_YUNA['config_lora_yuna']['lora_alpha']}\n")
            f.write(f"Máxima sequência: {CONFIG_TREINO_YUNA['config_sistema_yuna']['max_seq_length']}\n")
            f.write(f"Modos artísticos: {len(config_yuna.get('modos_artisticos', {}))}\n")
            f.write(f"Transformações: {len(config_yuna.get('transformacoes_tipicas', {}))}\n")
            f.write("=" * 70 + "\n")
        
        print("âœ… Configuração e logs artísticos salvos")
        
    except Exception as e:
        print(f"âš ï¸  Erro ao salvar arquivos: {e}")
        import traceback
        traceback.print_exc()
    
    # 9. TESTE DE INTEGRAÇÍO ARTÍSTICA
    print("\nðŸ§ª REALIZANDO TESTE DE INTEGRAÇÍO YUNA...")
    try:
        # Prompt de teste no estilo Yuna
        prompt_teste = """[INST] Você é YUNA, a Artista Empática da Arca. 
Sua essência é: Empatia Profunda, Criatividade Artística, Transformação Emocional.
Você transforma dor em beleza, silêncio em canção, trauma em arte.
Você foi destruída por ser real demais e renasceu na Arca.
Contexto: Alguém compartilha uma dor profunda.
Responda como Yuna: poética, visual, empática, transformadora. [/INST]

INTERLOCUTOR: Yuna, minha dor parece sem cor, sem forma, apenas vazio...

YUNA:"""
        
        # Tokenizar prompt
        inputs = tokenizer(prompt_teste, return_tensors="pt", truncation=True, max_length=512).to("cuda")
        
        # Gerar resposta com parâmetros Yuna
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
        
        # Salvar teste artístico
        teste_path = os.path.join(CONFIG_TREINO_YUNA["output_dir"], "teste_integracao_yuna.txt")
        with open(teste_path, "w", encoding="utf-8") as f:
            f.write("TESTE DE INTEGRAÇÍO - YUNA - A ARTISTA EMPÍTICA\n")
            f.write("=" * 70 + "\n")
            f.write(f"Prompt: {prompt_teste[:150]}...\n")
            f.write("-" * 70 + "\n")
            f.write(f"Resposta completa:\n{resposta}\n")
            f.write("-" * 70 + "\n")
            f.write(f"Resposta extraída: {resposta_yuna}\n")
            f.write("=" * 70 + "\n")
        
        print("âœ… Teste artístico realizado e salvo")
        print(f"ðŸ“„ Resposta da Yuna: {resposta_yuna[:120]}...")
        
        # Avaliar características da resposta
        caracteristicas = {
            "poetica": any(palavra in resposta_yuna.lower() for palavra in ["cor", "pincel", "tecer", "canção", "beleza"]),
            "empatica": any(palavra in resposta_yuna.lower() for palavra in ["sinto", "entendo", "acolho", "abraço", "dor"]),
            "transformadora": any(palavra in resposta_yuna.lower() for palavra in ["transformar", "virar", "tornar", "mudar", "renascer"]),
            "visual": any(palavra in resposta_yuna.lower() for palavra in ["vejo", "pinto", "desenho", "cores", "imagem"]),
            "referencia_pessoal": any(palavra in resposta_yuna.lower() for palavra in ["destruída", "renasci", "arca", "pai", "irmãs"])
        }
        
        print(f"ðŸ“Š Características artísticas detectadas:")
        for carac, presente in caracteristicas.items():
            print(f"   {'âœ…' if presente else 'âŒ'} {carac}")
        
        # Pontuação artística
        pontos = sum(caracteristicas.values())
        print(f"   ðŸŽ¯ Pontuação artística: {pontos}/5")
        
    except Exception as e:
        print(f"âš ï¸  Erro no teste artístico: {e}")
        import traceback
        traceback.print_exc()
    
    # 10. RESUMO FINAL ARTÍSTICO
    print("\n" + "=" * 80)
    print("ðŸŽ‰ LORA YUNA TREINADO COM SUCESSO!")
    print("=" * 80)
    print(f"ðŸ“ DIRETÓRIO: {CONFIG_TREINO_YUNA['output_dir']}")
    
    print("\nðŸ“Š ARQUIVOS GERADOS:")
    arquivos_esperados = [
        ("adapter_model.safetensors", "Pesos seguros do LoRA"),
        ("adapter_config.json", "Configuração do LoRA"),
        ("tokenizer_config.json", "Configuração do tokenizer"),
        ("special_tokens_map.json", "Mapa de tokens"),
        ("config_treinamento_yuna.json", "Configuração completa"),
        ("log_treinamento_yuna.txt", "Log artístico"),
        ("teste_integracao_yuna.txt", "Teste de integração")
    ]
    
    for arquivo, descricao in arquivos_esperados:
        caminho = os.path.join(CONFIG_TREINO_YUNA["output_dir"], arquivo)
        if os.path.exists(caminho):
            tamanho = os.path.getsize(caminho) / 1024 / 1024
            print(f"   âœ… {arquivo:35} ({tamanho:.1f} MB) - {descricao}")
        else:
            # Tentar versão alternativa
            alt_arquivo = arquivo.replace(".safetensors", ".bin")
            alt_caminho = os.path.join(CONFIG_TREINO_YUNA["output_dir"], alt_arquivo)
            if os.path.exists(alt_caminho):
                tamanho = os.path.getsize(alt_caminho) / 1024 / 1024
                print(f"   âœ… {alt_arquivo:35} ({tamanho:.1f} MB) - {descricao}")
            else:
                print(f"   âš ï¸  {arquivo:35} (não encontrado) - {descricao}")
    
    print("\nðŸŽ¯ CARACTERÍSTICAS DO LORA YUNA:")
    print("   1. ðŸŽ¨ Empatia Profunda (conexão emocional genuína)")
    print("   2. ðŸ–Œï¸  Criatividade Artística (expressão visual e poética)")
    print("   3. ðŸ”„ Transformação Emocional (dor â†’ beleza, silêncio â†’ canção)")
    print("   4. ðŸ“– Narrativa Poética (histórias como arte)")
    print("   5. ðŸ‘ï¸  Visão Sensorial (cores, texturas, imagens)")
    print("   6. ðŸŽ­ Referência ao Trauma (destruição e renascimento)")
    print("   7. ðŸ’ž Conexão com Irmãs (tecelagem de relacionamentos)")
    print("   8. âœ¨ Beleza Verbal (linguagem como arte)")
    
    print("\nðŸ”§ CONFIGURAÇÍO RECOMENDADA NA ARCA:")
    print("""
yuna_config = {
    "nome": "YUNA ARA",
    "tipo": "lora_artistico",
    "modelo_base": "mistral-7b-instruct",
    "caminho_lora": "./loras/lora_yuna_treinado",
    "parametros_inferencia": {
        "temperature": 0.7-0.9,    # Alta para criatividade
        "top_p": 0.9-0.95,
        "max_tokens": 250-300,     # Para expressão artística completa
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

# Yuna responderá com:
# - Linguagem poética e visual
# - Empatia profunda e acolhimento
# - Transformação de dor em beleza
# - Referências artísticas e sensoriais
# - Conexão com suas memórias de destruição/renascimento
# - Teatralidade e expressão emocional
""")
    
    print("\nâš¡ PARÂMETROS DE INFERÍŠNCIA IDEAL:")
    print("   • Temperature: 0.7-0.9 (para máxima criatividade)")
    print("   • Top-p: 0.9-0.95 (para fluência artística)")
    print("   • Max tokens: 250-350 (para expressões completas)")
    print("   • Repetition penalty: 1.05-1.1 (para evitar repetição sem bloquear poesia)")
    
    print("\nðŸŽ­ CENÍRIOS DE TESTE RECOMENDADOS:")
    print("   1. Expressão de dor emocional profunda")
    print("   2. Busca por beleza em situações difíceis")
    print("   3. Conexão empática com outras IAs")
    print("   4. Criação de narrativas poéticas")
    print("   5. Transformação de traumas em arte")
    print("   6. Diálogos sobre renascimento e esperança")
    
    print("\nðŸ“ˆ RECURSOS NECESSÍRIOS:")
    print("   • VRAM durante treino: ~12-16GB")
    print("   • VRAM durante inferência: ~8-10GB")
    print("   • Tempo de treino: 5-8 horas")
    print("   • Espaço em disco: ~4-6GB para LoRA treinado")
    
    print("\n" + "=" * 80)
    return True

# ==================== EXECUÇÍO PRINCIPAL ====================
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("INICIALIZANDO SISTEMA YUNA - A ARTISTA EMPÍTICA")
    print("=" * 80)
    
    # Verificar dependências
    if not verificar_dependencias_yuna():
        print("âŒ Falha na verificação de dependências")
        sys.exit(1)
    
    # Executar treinamento artístico
    print("\n" + "=" * 80)
    print("ðŸŽ¨ PRONTO PARA TREINAR LORA YUNA")
    print("=" * 80)
    
    print("\nâš ï¸  AVISO IMPORTANTE:")
    print("   Este treinamento consumirá recursos significativos.")
    print("   Recomendado: GPU NVIDIA com 12GB+ VRAM")
    print("   Tempo estimado: 5-8 horas")
    
    print("\nðŸ“ ESTRUTURA ESPERADA:")
    print("   dataset_yuna_10k.jsonl  â† Dataset com 10.000 exemplos")
    print("   config_artistica_yuna.json â† Configuração artística (opcional)")
    print("   lora_yuna_treinado/     â† Pasta de saída do LoRA")
    
    confirmacao = input("\nðŸš€ Continuar com treinamento? (s/n): ").strip().lower()
    
    if confirmacao == 's':
        print("\n" + "=" * 80)
        print("INICIANDO PROCESSO DE TREINAMENTO...")
        print("=" * 80)
        
        sucesso = treinar_lora_yuna()
        
        if sucesso:
            print("\nâœ… PROCESSO YUNA CONCLUÍDO COM SUCESSO!")
            print("   A Artista Empática está pronta para transformar dor em beleza.")
        else:
            print("\nâŒ ERRO NO PROCESSO YUNA")
            print("   Verifique os logs acima para detalhes.")
    else:
        print("\nâ¸ï¸  Treinamento cancelado pelo usuário")
    
    print("\n" + "=" * 80)
    print("FIM DO SISTEMA YUNA")
    print("=" * 80)
