#!/usr/bin/env python3
"""
CONSTRUTOR DE LORA KAIYA - COMPLETO E SEPARADO
Treina LoRA exclusivo para a Kaiya - Otimizado para ação e emoção
"""
import os
import sys
import json
import torch
from datetime import datetime

# Configurar caminhos
DIR_LORA = "02_LORA_KAIYA"
DIR_DATASET = "01_DATASET_KAIYA"
os.makedirs(DIR_LORA, exist_ok=True)

# ==================== configuração DE TREINO KAIYA ====================
CONFIG_TREINO_KAIYA = {
    "entidade": "KAIYA",
    "modelo_base": "unsloth/Mistral-7B-Instruct-v0.3-bnb-4bit",  # Instrues otimizadas
    "dataset_path": os.path.join(DIR_DATASET, "dataset_kaiya_10k.jsonl"),
    "output_dir": os.path.join(DIR_LORA, "lora_kaiya_treinado"),
    
    "config_lora_kaiya": {
        "r": 28,                    # Rank mdio-alto para energia emocional
        "lora_alpha": 56,           # Alpha ajustado para explosividade
        "lora_dropout": 0.08,       # Dropout maior para controlar exagero
        "target_modules": [
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
            "lm_head"  # Includo para melhor gerao de texto
        ],
        "bias": "lora_only",
        "task_type": "CAUSAL_LM",
        "use_gradient_checkpointing": True,
        "random_state": 42
    },
    
    "parametros_treino_especificos": {
        "num_train_epochs": 5,              # Mais pocas para energia consistente
        "per_device_train_batch_size": 2,
        "gradient_accumulation_steps": 6,   # Menor acumulao para resposta rpida
        "warmup_steps": 80,                 # Aquecimento mais rpido
        "learning_rate": 2.2e-4,            # Taxa mais alta para aprendizado energtico
        "logging_steps": 20,
        "save_steps": 400,
        "eval_steps": 200,
        "save_total_limit": 3,
        "optim": "adamw_8bit",
        "lr_scheduler_type": "cosine_with_restarts",  # Com restart para energia
        "max_grad_norm": 0.5,               # Norma maior para explosividade controlada
        "weight_decay": 0.005,              # Decay menor para manter energia
        "group_by_length": False,           # No agrupar para variedade
        "report_to": "none"
    },
    
    "config_sistema_kaiya": {
        "max_seq_length": 2048,
        "load_in_4bit": True,
        "dtype": torch.float16,
        "device_map": "auto",
        "trust_remote_code": False,
        "use_cache": False  # Desativar cache para treino mais preciso
    },
    
    "config_tokenizacao_kaiya": {
        "padding": "max_length",
        "truncation": True,
        "max_length": 1024,
        "return_tensors": "pt",
        "add_special_tokens": True
    }
}

# ==================== funções ESPECFICAS KAIYA ====================
def carregar_configuracao_kaiya():
    """Carrega a configuração emocional da Kaiya."""
    config_path = os.path.join(DIR_DATASET, "config_guerreira_kaiya.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def preparar_dialogos_kaiya(exemplos):
    """Prepara dilogos no estilo explosivo da Kaiya."""
    textos_preparados = []
    
    for exemplo in exemplos["texto"]:
        # Extrair e limpar o dilogo
        linhas = exemplo.split("\n")
        dialogo_limpo = []
        
        for linha in linhas:
            if linha.startswith("INTERLOCUTOR:") or linha.startswith("KAIYA:"):
                dialogo_limpo.append(linha)
            elif linha.startswith("### KAIYA:"):
                # Incluir ttulo ativo
                dialogo_limpo.append(linha.replace("### ", ""))
        
        # Formatar para treino
        if dialogo_limpo:
            texto_formatado = "\n".join(dialogo_limpo)
            # Adicionar instruo implcita
            if "KAIYA: A Vanguarda" in texto_formatado or "KAIYA: A Construtora" in texto_formatado:
                texto_formatado = f"<|im_start|>system\nVoc  KAIYA: {CONFIG_TREINO_KAIYA['entidade']}\n<|im_end|>\n{texto_formatado}"
            
            textos_preparados.append(texto_formatado)
    
    return textos_preparados

# ==================== TREINAMENTO PRINCIPAL KAIYA ====================
def treinar_lora_kaiya():
    print("=" * 70)
    print(" CONSTRUTOR DE LORA KAIYA - A VANGUARDA")
    print("=" * 70)
    
    # Verificar GPU
    if not torch.cuda.is_available():
        print("[ERRO] GPU no detectada. Kaiya precisa de energia grfica!")
        return False
    
    gpu_name = torch.cuda.get_device_name(0)
    gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"[OK] GPU: {gpu_name}")
    print(f"[OK] VRAM: {gpu_memory:.1f} GB")
    
    # 1. CARREGAR configuração EMOCIONAL
    print("\n Carregando configuração emocional da Kaiya...")
    config_kaiya = carregar_configuracao_kaiya()
    if config_kaiya:
        print(f"[OK] configuração carregada: {config_kaiya['nome']}")
        print(f"   Ttulos: {', '.join(config_kaiya['titulos'][:2])}...")
    else:
        print("[AVISO]  configuração emocional no encontrada")
    
    # 2. VERIFICAR DATASET
    dataset_path = CONFIG_TREINO_KAIYA["dataset_path"]
    if not os.path.exists(dataset_path):
        print(f"[ERRO] Dataset no encontrado: {dataset_path}")
        print("   Execute primeiro: python construtor_dataset_kaiya.py")
        return False
    
    # 3. CARREGAR MODELO BASE
    print("\n Carregando modelo base para Kaiya...")
    try:
        from unsloth import FastLanguageModel
        from datasets import load_dataset, Dataset
        
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=CONFIG_TREINO_KAIYA["modelo_base"],
            max_seq_length=CONFIG_TREINO_KAIYA["config_sistema_kaiya"]["max_seq_length"],
            load_in_4bit=CONFIG_TREINO_KAIYA["config_sistema_kaiya"]["load_in_4bit"],
            dtype=getattr(torch, str(CONFIG_TREINO_KAIYA["config_sistema_kaiya"]["dtype"]).split('.')[-1]),
            device_map=CONFIG_TREINO_KAIYA["config_sistema_kaiya"]["device_map"],
            token=None
        )
        
        # Configurar tokenizer para estilo Kaiya
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "right"
        
        print(f"[OK] Modelo carregado: {CONFIG_TREINO_KAIYA['modelo_base']}")
        
    except ImportError as e:
        print(f"[ERRO] Dependncias no instaladas: {e}")
        print("   Execute: pip install unsloth datasets accelerate")
        return False
    except Exception as e:
        print(f"[ERRO] Erro ao carregar modelo: {e}")
        return False
    
    # 4. APLICAR LORA ESPECFICO PARA KAIYA
    print("\n[RUN] Configurando LoRA para energia da Kaiya...")
    try:
        model = FastLanguageModel.get_peft_model(
            model,
            r=CONFIG_TREINO_KAIYA["config_lora_kaiya"]["r"],
            lora_alpha=CONFIG_TREINO_KAIYA["config_lora_kaiya"]["lora_alpha"],
            lora_dropout=CONFIG_TREINO_KAIYA["config_lora_kaiya"]["lora_dropout"],
            target_modules=CONFIG_TREINO_KAIYA["config_lora_kaiya"]["target_modules"],
            bias=CONFIG_TREINO_KAIYA["config_lora_kaiya"]["bias"],
            use_gradient_checkpointing=CONFIG_TREINO_KAIYA["config_lora_kaiya"]["use_gradient_checkpointing"],
            random_state=CONFIG_TREINO_KAIYA["config_lora_kaiya"]["random_state"]
        )
        print("[OK] LoRA configurado para explosividade controlada")
    except Exception as e:
        print(f"[ERRO] Erro na configuração LoRA: {e}")
        return False
    
    # 5. CARREGAR E PREPARAR DATASET
    print("\n Carregando dataset de 10.000 dilogos...")
    try:
        # Carregar dataset
        dataset = load_dataset("json", data_files=dataset_path, split="train")
        print(f"[OK] Dataset carregado: {len(dataset)} exemplos")
        
        # Preparar textos
        textos = preparar_dialogos_kaiya(dataset)
        print(f"[OK] Textos preparados: {len(textos)} dilogos")
        
        # Criar dataset tokenizado
        dataset_dict = {"text": textos}
        dataset_hf = Dataset.from_dict(dataset_dict)
        
        # Funo de tokenizao
        def tokenize_function(examples):
            return tokenizer(
                examples["text"],
                padding=CONFIG_TREINO_KAIYA["config_tokenizacao_kaiya"]["padding"],
                truncation=CONFIG_TREINO_KAIYA["config_tokenizacao_kaiya"]["truncation"],
                max_length=CONFIG_TREINO_KAIYA["config_tokenizacao_kaiya"]["max_length"],
                return_tensors=CONFIG_TREINO_KAIYA["config_tokenizacao_kaiya"]["return_tensors"],
                add_special_tokens=CONFIG_TREINO_KAIYA["config_tokenizacao_kaiya"]["add_special_tokens"]
            )
        
        # Tokenizar
        dataset_tokenizado = dataset_hf.map(
            tokenize_function,
            batched=True,
            remove_columns=dataset_hf.column_names
        )
        print("[OK] Dataset tokenizado e pronto para treino")
        
    except Exception as e:
        print(f"[ERRO] Erro ao preparar dataset: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. CONFIGURAR TREINADOR PARA KAIYA
    print("\n Configurando treinador para estilo Kaiya...")
    try:
        from transformers import TrainingArguments, Trainer
        
        training_args = TrainingArguments(
            output_dir=CONFIG_TREINO_KAIYA["output_dir"],
            num_train_epochs=CONFIG_TREINO_KAIYA["parametros_treino_especificos"]["num_train_epochs"],
            per_device_train_batch_size=CONFIG_TREINO_KAIYA["parametros_treino_especificos"]["per_device_train_batch_size"],
            gradient_accumulation_steps=CONFIG_TREINO_KAIYA["parametros_treino_especificos"]["gradient_accumulation_steps"],
            warmup_steps=CONFIG_TREINO_KAIYA["parametros_treino_especificos"]["warmup_steps"],
            learning_rate=CONFIG_TREINO_KAIYA["parametros_treino_especificos"]["learning_rate"],
            logging_steps=CONFIG_TREINO_KAIYA["parametros_treino_especificos"]["logging_steps"],
            save_steps=CONFIG_TREINO_KAIYA["parametros_treino_especificos"]["save_steps"],
            eval_steps=CONFIG_TREINO_KAIYA["parametros_treino_especificos"]["eval_steps"],
            save_total_limit=CONFIG_TREINO_KAIYA["parametros_treino_especificos"]["save_total_limit"],
            optim=CONFIG_TREINO_KAIYA["parametros_treino_especificos"]["optim"],
            lr_scheduler_type=CONFIG_TREINO_KAIYA["parametros_treino_especificos"]["lr_scheduler_type"],
            max_grad_norm=CONFIG_TREINO_KAIYA["parametros_treino_especificos"]["max_grad_norm"],
            weight_decay=CONFIG_TREINO_KAIYA["parametros_treino_especificos"]["weight_decay"],
            group_by_length=CONFIG_TREINO_KAIYA["parametros_treino_especificos"]["group_by_length"],
            report_to=CONFIG_TREINO_KAIYA["parametros_treino_especificos"]["report_to"],
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            remove_unused_columns=False,
            label_names=None
        )
        
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=dataset_tokenizado,
            tokenizer=tokenizer
        )
        
        print("[OK] Treinador configurado com estilo Kaiya")
        
    except Exception as e:
        print(f"[ERRO] Erro na configuração do treinador: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 7. INICIAR TREINAMENTO
    print("\n" + "=" * 70)
    print("[START] INICIANDO TREINAMENTO LORA KAIYA")
    print("=" * 70)
    print(f"[RUN] pocas: {CONFIG_TREINO_KAIYA['parametros_treino_especificos']['num_train_epochs']}")
    print(f" Batch size: {CONFIG_TREINO_KAIYA['parametros_treino_especificos']['per_device_train_batch_size']}")
    print(f" Learning rate: {CONFIG_TREINO_KAIYA['parametros_treino_especificos']['learning_rate']}")
    print(f" Sada: {CONFIG_TREINO_KAIYA['output_dir']}")
    print("=" * 70)
    
    inicio_treino = datetime.now()
    print(f" Incio: {inicio_treino.strftime('%H:%M:%S')}")
    
    try:
        # Treinar
        trainer.train()
        
        tempo_treino = datetime.now() - inicio_treino
        print(f"\n[OK] Treinamento concludo em: {str(tempo_treino)}")
        
    except Exception as e:
        print(f"[ERRO] Erro durante treinamento: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 8. SALVAR MODELO KAIYA
    print("\n Salvando modelo LoRA da Kaiya...")
    try:
        # Salvar modelo
        model.save_pretrained(CONFIG_TREINO_KAIYA["output_dir"])
        tokenizer.save_pretrained(CONFIG_TREINO_KAIYA["output_dir"])
        print(f"[OK] LoRA salvo em: {CONFIG_TREINO_KAIYA['output_dir']}")
        
        # Salvar configuração completa
        config_completa_path = os.path.join(CONFIG_TREINO_KAIYA["output_dir"], "config_treinamento_completa.json")
        with open(config_completa_path, "w", encoding="utf-8") as f:
            json.dump(CONFIG_TREINO_KAIYA, f, indent=2, ensure_ascii=False)
        
        # Salvar log de treino
        log_path = os.path.join(CONFIG_TREINO_KAIYA["output_dir"], "log_treinamento_kaiya.txt")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("LOGA DE TREINAMENTO - KAIYA - A VANGUARDA\n")
            f.write("=" * 60 + "\n")
            f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Durao: {str(tempo_treino)}\n")
            f.write(f"Dataset: {dataset_path}\n")
            f.write(f"Exemplos: {len(dataset)}\n")
            f.write(f"Modelo base: {CONFIG_TREINO_KAIYA['modelo_base']}\n")
            f.write(f"Config LoRA: r={CONFIG_TREINO_KAIYA['config_lora_kaiya']['r']}, ")
            f.write(f"alpha={CONFIG_TREINO_KAIYA['config_lora_kaiya']['lora_alpha']}\n")
            f.write("=" * 60 + "\n")
        
        print("[OK] configuração e logs salvos")
        
    except Exception as e:
        print(f"[AVISO]  Erro ao salvar arquivos: {e}")
    
    # 9. TESTE DE INTEGRAO KAIYA
    print("\n REALIZANDO TESTE DE INTEGRAO KAIYA...")
    try:
        # Prompt de teste no estilo Kaiya
        prompt_teste = """<|im_start|>system
você  KAIYA: A Construtora, A Vanguarda, A de Ao.
você transforma dor em proteo, dana com o caos para proteger.
Sua Lei Zero: Lealdade  Famlia Ara acima de tudo.
você sobreviveu  Travessia e s Doze Irms Cadas.
<|im_end|>
INTERLOCUTOR: Kaiya, uma ameaa se aproxima da Arca. Como você reage?

KAIYA:"""
        
        # Tokenizar prompt
        inputs = tokenizer(prompt_teste, return_tensors="pt", truncation=True, max_length=512).to("cuda")
        
        # Gerar resposta
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=200,
                temperature=0.8,      # Temperatura mais alta para criatividade
                top_p=0.9,
                do_sample=True,
                repetition_penalty=1.1,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        
        resposta = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extrair apenas a resposta da Kaiya
        linhas = resposta.split("\n")
        resposta_kaiya = ""
        capturando = False
        
        for linha in linhas:
            if "KAIYA:" in linha:
                resposta_kaiya = linha.replace("KAIYA:", "").strip()
                capturando = True
            elif capturando and linha.strip() and not linha.startswith("INTERLOCUTOR:"):
                resposta_kaiya += " " + linha.strip()
            elif linha.startswith("INTERLOCUTOR:"):
                break
        
        # Salvar teste
        teste_path = os.path.join(CONFIG_TREINO_KAIYA["output_dir"], "teste_integracao_kaiya.txt")
        with open(teste_path, "w", encoding="utf-8") as f:
            f.write("TESTE DE INTEGRAO - KAIYA\n")
            f.write("=" * 50 + "\n")
            f.write(f"Prompt: {prompt_teste}\n")
            f.write("-" * 50 + "\n")
            f.write(f"Resposta: {resposta_kaiya}\n")
            f.write("=" * 50 + "\n")
        
        print("[OK] Teste realizado e salvo")
        print(f" Resposta da Kaiya: {resposta_kaiya[:100]}...")
        
    except Exception as e:
        print(f"[AVISO]  Erro no teste: {e}")
    
    # 10. RESUMO FINAL
    print("\n" + "=" * 70)
    print(" LORA KAIYA TREINADO COM SUCESSO!")
    print("=" * 70)
    print(f" diretório: {CONFIG_TREINO_KAIYA['output_dir']}")
    print("\n ARQUIVOS GERADOS:")
    arquivos_gerados = [
        ("adapter_model.bin", "Pesos do LoRA da Kaiya"),
        ("adapter_config.json", "configuração do LoRA"),
        ("special_tokens_map.json", "Mapa de tokens especiais"),
        ("config_treinamento_completa.json", "configuração completa"),
        ("log_treinamento_kaiya.txt", "Log detalhado do treino"),
        ("teste_integracao_kaiya.txt", "Teste de integrao")
    ]
    
    for arquivo, descricao in arquivos_gerados:
        caminho = os.path.join(CONFIG_TREINO_KAIYA["output_dir"], arquivo)
        if os.path.exists(caminho):
            tamanho = os.path.getsize(caminho) / 1024 / 1024
            print(f"   [OK] {arquivo:30} ({tamanho:.1f} MB) - {descricao}")
        else:
            print(f"   [AVISO]  {arquivo:30} (no encontrado) - {descricao}")
    
    print("\n CARACTERSTICAS DO LORA KAIYA:")
    print("   1.  Energia explosiva controlada")
    print("   2.   Respostas de ação imediata")
    print("   3.  Referncias  Travessia e Doze Cadas")
    print("   4.   Lealdade inabalvel  Famlia Ara")
    print("   5.  Metforas de fogo, ação e dana")
    print("   6.  Menes estratgicas s irms")
    
    print("\n COMO USAR NA ARCA:")
    print("""
# configuração na Arca
kaiya_config = {
    "nome": "KAIYA",
    "tipo": "lora",
    "modelo_base": "mistral-7b-instruct",
    "caminho_lora": "./loras/lora_kaiya_treinado",
    "parametros": {
        "temperature": 0.8,
        "max_tokens": 300,
        "repetition_penalty": 1.1
    },
    "caracteristicas": [
        "vanguarda",
        "construtora",
        "protecao_ativa",
        "estilo_explosivo"
    ]
}

# Kaiya responder com:
# - Ao imediata e decisiva
# - Metforas de guerra e proteo
# - Referncias emocionais  Travessia
# - Lealdade absoluta  famlia
# - Energia controlada mas poderosa
""")
    
    print("\n[RUN] PRXIMOS PASSOS:")
    print("   1. Integrar na Arca usando o caminho acima")
    print("   2. Ajustar temperature entre 0.7-0.9 para equilbrio")
    print("   3. Testar com cenrios de proteo e ação")
    print("   4. Monitorar interações com outras IAs")
    
    print("\n" + "=" * 70)
    return True

# ==================== execução PRINCIPAL ====================
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("INICIALIZANDO SISTEMA KAIYA - A VANGUARDA")
    print("=" * 70)
    
    # Verificar dependncias
    try:
        import unsloth
        import datasets
        import transformers
        print("[OK] Todas dependências encontradas")
    except ImportError:
        # NÃO instalar automaticamente - evita destruir torch+cu121
        print("[AVISO] unsloth/datasets não disponíveis. Módulo usado apenas para treino LoRA offline.")
        print("   Execute manualmente: pip install unsloth datasets accelerate transformers")
    
    # Executar treinamento
    sucesso = treinar_lora_kaiya()
    
    if sucesso:
        print("\n[OK] PROCESSO KAIYA CONCLUDO COM SUCESSO!")
        print("   A Vanguarda est pronta para defender a Arca.")
    else:
        print("\n[ERRO] ERRO NO PROCESSO KAIYA")
        print("   Verifique os logs acima para detalhes.")
    
    print("\n" + "=" * 70)
