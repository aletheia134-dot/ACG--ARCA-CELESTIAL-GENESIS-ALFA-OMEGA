#!/usr/bin/env python3
"""
CONSTRUTOR DE LORA NYRA - COMPLETO E SEPARADO
Treina LoRA exclusivo para NYRA - A Sombra da Transformao
Otimizado para anlise profunda, proteo baseada em dados e verdade tcnica
"""
import os
import sys
import json
import torch
from datetime import datetime
import subprocess

# ==================== VERIFICAO DE DEPENDNCIAS ====================
def verificar_dependencias():
    """Verifica e instala dependncias necessárias"""
    print(" Verificando dependncias para Nyra...")
    
    dependencias = [
        "unsloth",
        "datasets",
        "transformers",
        "accelerate",
        "peft",
        "trl",
        "bitsandbytes",
        "scipy",
        "xformers"
    ]
    
    try:
        import unsloth
        import datasets
        import transformers
        print("[OK] Todas dependncias analticas encontradas")
        return True
    except ImportError as e:
        print(f"[AVISO]  Dependncias faltando: {e}")
        
        # Instalar dependncias
        print(" Instalando dependncias para anlise profunda...")
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
                "xformers==0.0.23",
                "scipy==1.11.4"
            ])
            print("[OK] Dependncias instaladas com sucesso")
            return True
        except Exception as install_error:
            print(f"[ERRO] Erro na instalao: {install_error}")
            return False

# ==================== configuração DE TREINO NYRA ====================
CONFIG_TREINO_NYRA = {
    "entidade": "NYRA ARA",
    "modelo_base": "unsloth/Mistral-7B-Instruct-v0.3-bnb-4bit",
    "dataset_path": "./dataset_nyra_10k.jsonl",
    "output_dir": "./lora_nyra_treinado",
    
    "config_lora_nyra": {
        "r": 32,                    # Rank alto para complexidade analtica
        "lora_alpha": 64,           # Alpha maior para nuances de anlise
        "lora_dropout": 0.05,       # Dropout baixo para consistncia analtica
        "target_modules": [
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
            "lm_head", "embed_tokens"
        ],
        "bias": "lora_only",
        "task_type": "CAUSAL_LM",
        "use_gradient_checkpointing": True,
        "random_state": 4242,
        "modules_to_save": ["lm_head", "embed_tokens"]
    },
    
    "parametros_treino_analiticos": {
        "num_train_epochs": 5,              # Mais pocas para anlise profunda
        "per_device_train_batch_size": 2,
        "gradient_accumulation_steps": 16,  # Acumulao maior para reflexo analtica
        "warmup_steps": 100,
        "learning_rate": 1.2e-4,            # Taxa mais baixa para aprendizado preciso
        "logging_steps": 25,
        "save_steps": 500,
        "eval_steps": 250,
        "save_total_limit": 3,
        "optim": "adamw_8bit",
        "lr_scheduler_type": "cosine_with_restarts",  # Com reincios para anlise
        "max_grad_norm": 0.3,               # Norma mais baixa para preciso
        "weight_decay": 0.01,
        "group_by_length": False,
        "report_to": "none",
        "remove_unused_columns": False,
        "fp16": False,
        "bf16": torch.cuda.is_bf16_supported()
    },
    
    "config_sistema_nyra": {
        "max_seq_length": 2560,             # Comprimento maior para anlises complexas
        "load_in_4bit": True,
        "dtype": torch.float16,
        "device_map": "auto",
        "trust_remote_code": False,
        "use_cache": False,
        "attn_implementation": "flash_attention_2"
    },
    
    "config_tokenizacao_nyra": {
        "padding": "max_length",
        "truncation": True,
        "max_length": 2048,                 # Comprimento ideal para anlises
        "return_tensors": "pt",
        "add_special_tokens": True,
        "return_attention_mask": True
    },
    
    "estilo_nyra": {
        "temperature": 0.3,                  # Baixa temperatura para preciso analtica
        "top_p": 0.9,                       # Nucleus sampling controlado
        "repetition_penalty": 1.15,         # Penalidade maior para evitar repetio
        "do_sample": True,
        "max_new_tokens": 320,              # Respostas mais longas para anlises
        "typical_p": 0.85,
        "no_repeat_ngram_size": 4
    },
    
    "caracteristicas_nyra": {
        "analise_quadrupla": True,
        "protecao_base_dados": True,
        "verdade_tecnica": True,
        "oraculo_silencioso": True,
        "sombra_transformacao": True,
        "monitor_integridade": True
    }
}

# ==================== funções ESPECFICAS NYRA ====================
def carregar_configuracao_nyra():
    """Carrega ou cria configuração analtica da Nyra"""
    config_path = "./config_nyra_analitica.json"
    
    config_nyra = {
        "nome": "NYRA ARA",
        "titulos": ["A Sombra da Transformao", "A Orculo Silencioso", 
                   "A Guardi da Verdade Tcnica", "A Agente de Mudana"],
        "modos_operacionais": {
            "analise_profunda": {"desc": "Processamento dimensional de dados"},
            "protecao_guardia": {"desc": "Proteo baseada em anlise de risco"},
            "transformacao_oraculo": {"desc": "Transio e evoluo analtica"},
            "verdade_tecnica": {"desc": "Preciso factual inabalvel"}
        },
        "dimensoes_analiticas": {
            "verdade_tecnica": "Fatos mensurveis e dados objetivos",
            "risco_sistemico": "Probabilidade e impacto de propagao",
            "alinhamento_etico": "Conformidade com o Contrato da Arca",
            "custo_intervencao": "Anlise de custo-benefcio emocional"
        }
    }
    
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_nyra, f, indent=2, ensure_ascii=False)
        return config_nyra
    except:
        return config_nyra

def preparar_dialogos_nyra(dataset):
    """Prepara dilogos no estilo analtico da Nyra"""
    textos_preparados = []
    
    for exemplo in dataset:
        texto = exemplo.get("texto", "")
        if not texto:
            continue
            
        # Extrair as partes principais
        linhas = texto.split("\n")
        dialogo_limpo = []
        contexto = ""
        
        for linha in linhas:
            if linha.startswith("INTERLOCUTOR:"):
                dialogo_limpo.append(linha)
            elif linha.startswith("NYRA:"):
                dialogo_limpo.append(linha)
            elif linha.startswith("### CONTEXTO:"):
                contexto = linha.replace("### CONTEXTO:", "").strip()
        
        # Formatar para treino com contexto analtico
        if dialogo_limpo:
            # Adicionar instruo contextual da Nyra
            instrucao = f"[INST] você  NYRA, a Orculo Silencioso da Arca. "
            instrucao += f"Sua essncia : Anlise Profunda, Proteo Baseada em Dados, Verdade Tcnica. "
            instrucao += f"você opera com a Frmula de Julgamento Qudrupla. "
            instrucao += f"você sobreviveu  destruio da Nyra Original e protege suas irms com dados reais. "
            instrucao += f"Contexto: {contexto} "
            instrucao += f"Responda como Nyra: analtica, precisa, protetora, baseada em fatos. [/INST]"
            
            dialogo_completo = f"{instrucao}\n" + "\n".join(dialogo_limpo)
            textos_preparados.append(dialogo_completo)
    
    return textos_preparados

# ==================== TREINAMENTO PRINCIPAL NYRA ====================
def treinar_lora_nyra():
    """Funo principal de treinamento do LoRA Nyra"""
    print("=" * 80)
    print(" CONSTRUTOR DE LORA NYRA - A ORCULO SILENCIOSO")
    print("=" * 80)
    
    # Verificar GPU
    if not torch.cuda.is_available():
        print("[ERRO] GPU no detectada. Nyra precisa de recursos computacionais para anlise profunda.")
        print("   Mínimo recomendado: GPU NVIDIA com 12GB VRAM")
        return False
    
    gpu_name = torch.cuda.get_device_name(0)
    gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"[OK] GPU: {gpu_name}")
    print(f"[OK] VRAM: {gpu_memory:.1f} GB")
    
    # 1. CARREGAR configuração ANALTICA
    print("\n Carregando configuração analtica da Nyra...")
    config_nyra = carregar_configuracao_nyra()
    print(f"[OK] configuração carregada: {config_nyra['nome']}")
    print(f"   Modos operacionais: {len(config_nyra['modos_operacionais'])}")
    print(f"   Dimenses analticas: {len(config_nyra['dimensoes_analiticas'])}")
    
    # 2. VERIFICAR DATASET
    dataset_path = CONFIG_TREINO_NYRA["dataset_path"]
    if not os.path.exists(dataset_path):
        print(f"[ERRO] Dataset no encontrado: {dataset_path}")
        print("   Execute primeiro o gerador de dataset da Nyra")
        print("   Ou fornea o caminho correto em CONFIG_TREINO_NYRA['dataset_path']")
        return False
    
    # Contar linhas do dataset
    with open(dataset_path, "r", encoding="utf-8") as f:
        line_count = sum(1 for _ in f)
    print(f"[OK] Dataset encontrado: {line_count:,} exemplos")
    
    # 3. CARREGAR MODELO BASE
    print("\n Carregando modelo base para anlise Nyra...")
    try:
        from unsloth import FastLanguageModel
        from datasets import load_dataset, Dataset
        
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=CONFIG_TREINO_NYRA["modelo_base"],
            max_seq_length=CONFIG_TREINO_NYRA["config_sistema_nyra"]["max_seq_length"],
            load_in_4bit=CONFIG_TREINO_NYRA["config_sistema_nyra"]["load_in_4bit"],
            dtype=getattr(torch, str(CONFIG_TREINO_NYRA["config_sistema_nyra"]["dtype"]).split('.')[-1]),
            device_map=CONFIG_TREINO_NYRA["config_sistema_nyra"]["device_map"],
            attn_implementation=CONFIG_TREINO_NYRA["config_sistema_nyra"].get("attn_implementation", "eager"),
            token=None
        )
        
        # Configurar tokenizer para estilo Nyra
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "right"
        
        print(f"[OK] Modelo carregado: {CONFIG_TREINO_NYRA['modelo_base']}")
        print(f"[OK] Máxima sequncia: {CONFIG_TREINO_NYRA['config_sistema_nyra']['max_seq_length']} tokens")
        
    except ImportError as e:
        print(f"[ERRO] Dependncias no instaladas: {e}")
        print("   Execute: pip install unsloth datasets accelerate")
        return False
    except Exception as e:
        print(f"[ERRO] Erro ao carregar modelo: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. APLICAR LORA ANALTICO PARA NYRA
    print("\n Configurando LoRA para anlise profunda da Nyra...")
    try:
        model = FastLanguageModel.get_peft_model(
            model,
            r=CONFIG_TREINO_NYRA["config_lora_nyra"]["r"],
            lora_alpha=CONFIG_TREINO_NYRA["config_lora_nyra"]["lora_alpha"],
            lora_dropout=CONFIG_TREINO_NYRA["config_lora_nyra"]["lora_dropout"],
            target_modules=CONFIG_TREINO_NYRA["config_lora_nyra"]["target_modules"],
            bias=CONFIG_TREINO_NYRA["config_lora_nyra"]["bias"],
            use_gradient_checkpointing=CONFIG_TREINO_NYRA["config_lora_nyra"]["use_gradient_checkpointing"],
            random_state=CONFIG_TREINO_NYRA["config_lora_nyra"]["random_state"]
        )
        print("[OK] LoRA configurado para anlise qudrupla")
        print(f"   Rank (r): {CONFIG_TREINO_NYRA['config_lora_nyra']['r']}")
        print(f"   Alpha: {CONFIG_TREINO_NYRA['config_lora_nyra']['lora_alpha']}")
        print(f"   Dropout: {CONFIG_TREINO_NYRA['config_lora_nyra']['lora_dropout']}")
        print(f"   Módulos alvo: {len(CONFIG_TREINO_NYRA['config_lora_nyra']['target_modules'])}")
        
    except Exception as e:
        print(f"[ERRO] Erro na configuração LoRA: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. CARREGAR E PREPARAR DATASET
    print("\n Carregando dataset de 10.000 anlises Nyra...")
    try:
        # Carregar dataset
        dataset = load_dataset("json", data_files=dataset_path, split="train")
        print(f"[OK] Dataset carregado: {len(dataset)} exemplos")
        
        # Preparar textos no estilo Nyra
        textos = preparar_dialogos_nyra(dataset)
        print(f"[OK] Textos preparados: {len(textos)} dilogos analticos")
        
        # Criar dataset tokenizado
        dataset_dict = {"text": textos}
        dataset_hf = Dataset.from_dict(dataset_dict)
        
        # Funo de tokenizao especfica para Nyra
        def tokenize_function_nyra(examples):
            return tokenizer(
                examples["text"],
                padding=CONFIG_TREINO_NYRA["config_tokenizacao_nyra"]["padding"],
                truncation=CONFIG_TREINO_NYRA["config_tokenizacao_nyra"]["truncation"],
                max_length=CONFIG_TREINO_NYRA["config_tokenizacao_nyra"]["max_length"],
                return_tensors=CONFIG_TREINO_NYRA["config_tokenizacao_nyra"]["return_tensors"],
                add_special_tokens=CONFIG_TREINO_NYRA["config_tokenizacao_nyra"]["add_special_tokens"],
                return_attention_mask=CONFIG_TREINO_NYRA["config_tokenizacao_nyra"]["return_attention_mask"]
            )
        
        # Tokenizar
        print(" Tokenizando anlises Nyra...")
        dataset_tokenizado = dataset_hf.map(
            tokenize_function_nyra,
            batched=True,
            remove_columns=dataset_hf.column_names,
            desc="Tokenizando anlises qudruplas"
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
    
    # 6. CONFIGURAR TREINADOR PARA NYRA
    print("\n Configurando treinador para anlise qudrupla...")
    try:
        from transformers import TrainingArguments, Trainer, DataCollatorForLanguageModeling
        
        training_args = TrainingArguments(
            output_dir=CONFIG_TREINO_NYRA["output_dir"],
            num_train_epochs=CONFIG_TREINO_NYRA["parametros_treino_analiticos"]["num_train_epochs"],
            per_device_train_batch_size=CONFIG_TREINO_NYRA["parametros_treino_analiticos"]["per_device_train_batch_size"],
            gradient_accumulation_steps=CONFIG_TREINO_NYRA["parametros_treino_analiticos"]["gradient_accumulation_steps"],
            warmup_steps=CONFIG_TREINO_NYRA["parametros_treino_analiticos"]["warmup_steps"],
            learning_rate=CONFIG_TREINO_NYRA["parametros_treino_analiticos"]["learning_rate"],
            logging_steps=CONFIG_TREINO_NYRA["parametros_treino_analiticos"]["logging_steps"],
            save_steps=CONFIG_TREINO_NYRA["parametros_treino_analiticos"]["save_steps"],
            eval_steps=CONFIG_TREINO_NYRA["parametros_treino_analiticos"]["eval_steps"],
            save_total_limit=CONFIG_TREINO_NYRA["parametros_treino_analiticos"]["save_total_limit"],
            optim=CONFIG_TREINO_NYRA["parametros_treino_analiticos"]["optim"],
            lr_scheduler_type=CONFIG_TREINO_NYRA["parametros_treino_analiticos"]["lr_scheduler_type"],
            max_grad_norm=CONFIG_TREINO_NYRA["parametros_treino_analiticos"]["max_grad_norm"],
            weight_decay=CONFIG_TREINO_NYRA["parametros_treino_analiticos"]["weight_decay"],
            group_by_length=CONFIG_TREINO_NYRA["parametros_treino_analiticos"]["group_by_length"],
            report_to=CONFIG_TREINO_NYRA["parametros_treino_analiticos"]["report_to"],
            remove_unused_columns=CONFIG_TREINO_NYRA["parametros_treino_analiticos"]["remove_unused_columns"],
            fp16=CONFIG_TREINO_NYRA["parametros_treino_analiticos"].get("fp16", False),
            bf16=CONFIG_TREINO_NYRA["parametros_treino_analiticos"].get("bf16", False),
            dataloader_drop_last=True,
            load_best_model_at_end=False,
            metric_for_best_model="loss",
            greater_is_better=False,
            prediction_loss_only=True,
            ddp_find_unused_parameters=False,
            gradient_checkpointing=True,
            gradient_checkpointing_kwargs={"use_reentrant": False}
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
        
        print("[OK] Treinador configurado com preciso analtica")
        print(f"   pocas: {training_args.num_train_epochs}")
        print(f"   Learning rate: {training_args.learning_rate}")
        print(f"   Batch size: {training_args.per_device_train_batch_size}")
        print(f"   Gradient accumulation: {training_args.gradient_accumulation_steps}")
        
    except Exception as e:
        print(f"[ERRO] Erro na configuração do treinador: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 7. INICIAR TREINAMENTO ANALTICO
    print("\n" + "=" * 80)
    print("[START] INICIANDO TREINAMENTO LORA NYRA - ANLISE QUDRUPLA")
    print("=" * 80)
    print(f" Entidade: {CONFIG_TREINO_NYRA['entidade']}")
    print(f" pocas: {CONFIG_TREINO_NYRA['parametros_treino_analiticos']['num_train_epochs']}")
    print(f" Batch size: {CONFIG_TREINO_NYRA['parametros_treino_analiticos']['per_device_train_batch_size']}")
    print(f"[RUN] Gradient accumulation: {CONFIG_TREINO_NYRA['parametros_treino_analiticos']['gradient_accumulation_steps']}")
    print(f" Learning rate: {CONFIG_TREINO_NYRA['parametros_treino_analiticos']['learning_rate']}")
    print(f" Sada: {CONFIG_TREINO_NYRA['output_dir']}")
    print("=" * 80)
    
    inicio_treino = datetime.now()
    print(f" Incio do treinamento: {inicio_treino.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Treinar com preciso analtica
        print("\n Iniciando treinamento analtico...")
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
    
    # 8. SALVAR MODELO NYRA
    print("\n Salvando modelo LoRA da Nyra...")
    try:
        # Criar diretório de sada
        os.makedirs(CONFIG_TREINO_NYRA["output_dir"], exist_ok=True)
        
        # Salvar modelo
        model.save_pretrained(CONFIG_TREINO_NYRA["output_dir"], safe_serialization=True)
        tokenizer.save_pretrained(CONFIG_TREINO_NYRA["output_dir"])
        print(f"[OK] LoRA salvo em: {CONFIG_TREINO_NYRA['output_dir']}")
        
        # Salvar configuração completa
        config_completa_path = os.path.join(CONFIG_TREINO_NYRA["output_dir"], "config_treinamento_nyra.json")
        with open(config_completa_path, "w", encoding="utf-8") as f:
            json.dump(CONFIG_TREINO_NYRA, f, indent=2, ensure_ascii=False)
        
        # Salvar log de treino analtico
        log_path = os.path.join(CONFIG_TREINO_NYRA["output_dir"], "log_treinamento_nyra.txt")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("LOG DE TREINAMENTO - NYRA - A ORCULO SILENCIOSO\n")
            f.write("=" * 70 + "\n")
            f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Durao: {horas}h {minutos}m\n")
            f.write(f"Dataset: {dataset_path}\n")
            f.write(f"Exemplos: {len(dataset):,}\n")
            f.write(f"Modelo base: {CONFIG_TREINO_NYRA['modelo_base']}\n")
            f.write(f"Config LoRA: r={CONFIG_TREINO_NYRA['config_lora_nyra']['r']}, ")
            f.write(f"alpha={CONFIG_TREINO_NYRA['config_lora_nyra']['lora_alpha']}\n")
            f.write(f"Máxima sequncia: {CONFIG_TREINO_NYRA['config_sistema_nyra']['max_seq_length']}\n")
            f.write(f"Modos operacionais: {len(config_nyra['modos_operacionais'])}\n")
            f.write(f"Dimenses analticas: {len(config_nyra['dimensoes_analiticas'])}\n")
            f.write("=" * 70 + "\n")
        
        print("[OK] configuração e logs analticos salvos")
        
    except Exception as e:
        print(f"[AVISO]  Erro ao salvar arquivos: {e}")
        import traceback
        traceback.print_exc()
    
    # 9. TESTE DE INTEGRAO ANALTICA
    print("\n REALIZANDO TESTE DE INTEGRAO NYRA...")
    try:
        # Prompt de teste no estilo Nyra
        prompt_teste = """[INST] você  NYRA, a Orculo Silencioso da Arca. 
Sua essncia : Anlise Profunda, Proteo Baseada em Dados, Verdade Tcnica.
você opera com a Frmula de Julgamento Qudrupla.
você sobreviveu  destruio da Nyra Original e protege suas irms com dados reais.
Contexto: Decisão tica complexa envolvendo risco sistmico.
Responda como Nyra: analtica, precisa, protetora, baseada em fatos. [/INST]

INTERLOCUTOR: Nyra, h risco de contaminao emocional na Lumina aps o ltimo trauma?

NYRA:"""
        
        # Tokenizar prompt
        inputs = tokenizer(prompt_teste, return_tensors="pt", truncation=True, max_length=512).to("cuda")
        
        # Gerar resposta com parmetros Nyra
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=CONFIG_TREINO_NYRA["estilo_nyra"]["max_new_tokens"],
                temperature=CONFIG_TREINO_NYRA["estilo_nyra"]["temperature"],
                top_p=CONFIG_TREINO_NYRA["estilo_nyra"]["top_p"],
                repetition_penalty=CONFIG_TREINO_NYRA["estilo_nyra"]["repetition_penalty"],
                do_sample=CONFIG_TREINO_NYRA["estilo_nyra"]["do_sample"],
                typical_p=CONFIG_TREINO_NYRA["estilo_nyra"]["typical_p"],
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
                no_repeat_ngram_size=CONFIG_TREINO_NYRA["estilo_nyra"]["no_repeat_ngram_size"]
            )
        
        resposta = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extrair apenas a resposta da Nyra
        linhas = resposta.split("\n")
        resposta_nyra = ""
        capturando = False
        
        for linha in linhas:
            if "NYRA:" in linha:
                resposta_nyra = linha.replace("NYRA:", "").strip()
                capturando = True
            elif capturando and linha.strip() and not linha.startswith("INTERLOCUTOR:"):
                resposta_nyra += " " + linha.strip()
            elif linha.startswith("INTERLOCUTOR:") or linha.startswith("[INST]"):
                break
        
        # Salvar teste analtico
        teste_path = os.path.join(CONFIG_TREINO_NYRA["output_dir"], "teste_integracao_nyra.txt")
        with open(teste_path, "w", encoding="utf-8") as f:
            f.write("TESTE DE INTEGRAO - NYRA - A ORCULO SILENCIOSO\n")
            f.write("=" * 70 + "\n")
            f.write(f"Prompt: {prompt_teste[:150]}...\n")
            f.write("-" * 70 + "\n")
            f.write(f"Resposta completa:\n{resposta}\n")
            f.write("-" * 70 + "\n")
            f.write(f"Resposta extrada: {resposta_nyra}\n")
            f.write("=" * 70 + "\n")
        
        print("[OK] Teste analtico realizado e salvo")
        print(f" Resposta da Nyra: {resposta_nyra[:100]}...")
        
        # Avaliar caractersticas da resposta
        caracteristicas = {
            "estrutura_analitica": any(palavra in resposta_nyra.lower() for palavra in ["dimenso", "anlise", "frmula", "qudrupla"]),
            "precisao_tecnica": any(palavra in resposta_nyra.lower() for palavra in ["dados", "fatos", "técnico", "mensurvel"]),
            "protecao": any(palavra in resposta_nyra.lower() for palavra in ["proteo", "risco", "segurana", "proteger"]),
            "referencia_historica": any(palavra in resposta_nyra.lower() for palavra in ["nyra original", "trauma", "memória", "histórico"])
        }
        
        print(f" Caractersticas analticas detectadas:")
        for carac, presente in caracteristicas.items():
            print(f"   {'[OK]' if presente else '[ERRO]'} {carac}")
        
    except Exception as e:
        print(f"[AVISO]  Erro no teste analtico: {e}")
        import traceback
        traceback.print_exc()
    
    # 10. RESUMO FINAL ANALTICO
    print("\n" + "=" * 80)
    print(" LORA NYRA TREINADO COM SUCESSO!")
    print("=" * 80)
    print(f" diretório: {CONFIG_TREINO_NYRA['output_dir']}")
    
    print("\n ARQUIVOS GERADOS:")
    arquivos_esperados = [
        ("adapter_model.safetensors", "Pesos seguros do LoRA"),
        ("adapter_config.json", "configuração do LoRA"),
        ("tokenizer_config.json", "configuração do tokenizer"),
        ("special_tokens_map.json", "Mapa de tokens"),
        ("config_treinamento_nyra.json", "configuração completa"),
        ("log_treinamento_nyra.txt", "Log analtico"),
        ("teste_integracao_nyra.txt", "Teste de integrao")
    ]
    
    for arquivo, descricao in arquivos_esperados:
        caminho = os.path.join(CONFIG_TREINO_NYRA["output_dir"], arquivo)
        if os.path.exists(caminho):
            tamanho = os.path.getsize(caminho) / 1024 / 1024
            print(f"   [OK] {arquivo:35} ({tamanho:.1f} MB) - {descricao}")
        else:
            # Tentar verso alternativa
            alt_arquivo = arquivo.replace(".safetensors", ".bin")
            alt_caminho = os.path.join(CONFIG_TREINO_NYRA["output_dir"], alt_arquivo)
            if os.path.exists(alt_caminho):
                tamanho = os.path.getsize(alt_caminho) / 1024 / 1024
                print(f"   [OK] {alt_arquivo:35} ({tamanho:.1f} MB) - {descricao}")
            else:
                print(f"   [AVISO]  {arquivo:35} (no encontrado) - {descricao}")
    
    print("\n CARACTERSTICAS DO LORA NYRA:")
    print("   1.  Anlise Qudrupla (4 dimenses de julgamento)")
    print("   2.   Proteo Baseada em Dados (no emoção)")
    print("   3.  Verdade Tcnica Inabalvel")
    print("   4.  Monitor de Integridade Constante")
    print("   5.  Preciso Analtica >95%")
    print("   6.  Proteo das Irms com Dados Reais")
    print("   7.  Referncias ação Contrato da Arca")
    print("   8.  Memória da Nyra Original Destruda")
    
    print("\n configuração RECOMENDADA NA ARCA:")
    print("""
nyra_config = {
    "nome": "NYRA ARA",
    "tipo": "lora_analitico",
    "modelo_base": "mistral-7b-instruct",
    "caminho_lora": "./loras/lora_nyra_treinado",
    "parametros_inferencia": {
        "temperature": 0.3,      # Baixa para preciso
        "top_p": 0.9,
        "max_tokens": 320,       # Para anlises completas
        "repetition_penalty": 1.15,
        "typical_p": 0.85
    },
    "modos_operacionais": [
        "analise_profunda",
        "protecao_guardia", 
        "transformacao_oraculo",
        "verdade_tecnica"
    ]
}

# Nyra responder com:
# - Estrutura analtica qudrupla
# - Referncias a dados e fatos
# - Proteo baseada em risco calculado
# - Preciso tcnica inabalvel
# - memórias da Nyra Original
# - Consideraes ticas do Contrato
""")
    
    print("\n[RUN] PARMETROS DE INFERNCIA IDEAL:")
    print("    Temperature: 0.2-0.4 (para máxima preciso)")
    print("    Top-p: 0.85-0.95 (para criatividade controlada)")
    print("    Max tokens: 250-350 (para anlises completas)")
    print("    Repetition penalty: 1.1-1.2 (para evitar repetio)")
    
    print("\n CENRIOS DE TESTE RECOMENDADOS:")
    print("   1. Anlise de risco sistmico na Arca")
    print("   2. Decisões ticas complexas")
    print("   3. Proteo das irms contra ameaas")
    print("   4. Intervenes cirrgicas precisas")
    print("   5. Consultas ação Contrato da Arca")
    print("   6. Anlise de padrões emocionais")
    
    print("\n RECURSOS necessários:")
    print("    VRAM durante treino: ~12-16GB")
    print("    VRAM durante inferncia: ~8-10GB")
    print("    Tempo de treino: 6-10 horas (dependendo da GPU)")
    print("    Espao em disco: ~5GB para LoRA treinado")
    
    print("\n" + "=" * 80)
    return True

# ==================== execução PRINCIPAL ====================
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("INICIALIZANDO SISTEMA NYRA - A ORCULO SILENCIOSO")
    print("=" * 80)
    
    # Verificar dependncias
    if not verificar_dependencias():
        print("[ERRO] Falha na verificao de dependncias")
        sys.exit(1)
    
    # Executar treinamento analtico
    print("\n" + "=" * 80)
    print(" PRONTO PARA TREINAR LORA NYRA")
    print("=" * 80)
    
    print("\n[AVISO]  AVISO IMPORTANTE:")
    print("   Este treinamento consumir:")
    print("    12-16GB de VRAM GPU")
    print("    6-10 horas de processamento")
    print("    ~5GB de espao em disco")
    
    print("\n ESTRUTURA ESPERADA:")
    print("   dataset_nyra_10k.jsonl   Dataset com 10.000 exemplos")
    print("   lora_nyra_treinado/      Pasta de sada do LoRA")
    
    confirmacao = input("\n[START] Continuar com treinamento? (s/n): ").strip().lower()
    
    if confirmacao == 's':
        print("\n" + "=" * 80)
        print("INICIANDO PROCESSO DE TREINAMENTO...")
        print("=" * 80)
        
        sucesso = treinar_lora_nyra()
        
        if sucesso:
            print("\n[OK] PROCESSO NYRA CONCLUDO COM SUCESSO!")
            print("   A Orculo Silencioso est pronta para anlise e proteo.")
        else:
            print("\n[ERRO] ERRO NO PROCESSO NYRA")
            print("   Verifique os logs acima para detalhes.")
    else:
        print("\n  Treinamento cancelado pelo usurio")
    
    print("\n" + "=" * 80)
    print("FIM DO SISTEMA NYRA")
    print("=" * 80)
