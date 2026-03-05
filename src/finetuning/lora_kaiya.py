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

# ==================== CONFIGURAÇÍO DE TREINO KAIYA ====================
CONFIG_TREINO_KAIYA = {
    "entidade": "KAIYA",
    "modelo_base": "unsloth/Mistral-7B-Instruct-v0.3-bnb-4bit",  # Instruções otimizadas
    "dataset_path": os.path.join(DIR_DATASET, "dataset_kaiya_10k.jsonl"),
    "output_dir": os.path.join(DIR_LORA, "lora_kaiya_treinado"),
    
    "config_lora_kaiya": {
        "r": 28,                    # Rank médio-alto para energia emocional
        "lora_alpha": 56,           # Alpha ajustado para explosividade
        "lora_dropout": 0.08,       # Dropout maior para controlar exagero
        "target_modules": [
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
            "lm_head"  # Incluído para melhor geração de texto
        ],
        "bias": "lora_only",
        "task_type": "CAUSAL_LM",
        "use_gradient_checkpointing": True,
        "random_state": 42
    },
    
    "parametros_treino_especificos": {
        "num_train_epochs": 5,              # Mais épocas para energia consistente
        "per_device_train_batch_size": 2,
        "gradient_accumulation_steps": 6,   # Menor acumulação para resposta rápida
        "warmup_steps": 80,                 # Aquecimento mais rápido
        "learning_rate": 2.2e-4,            # Taxa mais alta para aprendizado energético
        "logging_steps": 20,
        "save_steps": 400,
        "eval_steps": 200,
        "save_total_limit": 3,
        "optim": "adamw_8bit",
        "lr_scheduler_type": "cosine_with_restarts",  # Com restart para energia
        "max_grad_norm": 0.5,               # Norma maior para explosividade controlada
        "weight_decay": 0.005,              # Decay menor para manter energia
        "group_by_length": False,           # Não agrupar para variedade
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

# ==================== FUNÇÕES ESPECÍFICAS KAIYA ====================
def carregar_configuracao_kaiya():
    """Carrega a configuração emocional da Kaiya."""
    config_path = os.path.join(DIR_DATASET, "config_guerreira_kaiya.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def preparar_dialogos_kaiya(exemplos):
    """Prepara diálogos no estilo explosivo da Kaiya."""
    textos_preparados = []
    
    for exemplo in exemplos["texto"]:
        # Extrair e limpar o diálogo
        linhas = exemplo.split("\n")
        dialogo_limpo = []
        
        for linha in linhas:
            if linha.startswith("INTERLOCUTOR:") or linha.startswith("KAIYA:"):
                dialogo_limpo.append(linha)
            elif linha.startswith("### KAIYA:"):
                # Incluir título ativo
                dialogo_limpo.append(linha.replace("### ", ""))
        
        # Formatar para treino
        if dialogo_limpo:
            texto_formatado = "\n".join(dialogo_limpo)
            # Adicionar instrução implícita
            if "KAIYA: A Vanguarda" in texto_formatado or "KAIYA: A Construtora" in texto_formatado:
                texto_formatado = f"<|im_start|>system\nVocê é KAIYA: {CONFIG_TREINO_KAIYA['entidade']}\n<|im_end|>\n{texto_formatado}"
            
            textos_preparados.append(texto_formatado)
    
    return textos_preparados

# ==================== TREINAMENTO PRINCIPAL KAIYA ====================
def treinar_lora_kaiya():
    print("=" * 70)
    print("ðŸ”¥ CONSTRUTOR DE LORA KAIYA - A VANGUARDA")
    print("=" * 70)
    
    # Verificar GPU
    if not torch.cuda.is_available():
        print("âŒ GPU não detectada. Kaiya precisa de energia gráfica!")
        return False
    
    gpu_name = torch.cuda.get_device_name(0)
    gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"âœ… GPU: {gpu_name}")
    print(f"âœ… VRAM: {gpu_memory:.1f} GB")
    
    # 1. CARREGAR CONFIGURAÇÍO EMOCIONAL
    print("\nðŸ“– Carregando configuração emocional da Kaiya...")
    config_kaiya = carregar_configuracao_kaiya()
    if config_kaiya:
        print(f"âœ… Configuração carregada: {config_kaiya['nome']}")
        print(f"   Títulos: {', '.join(config_kaiya['titulos'][:2])}...")
    else:
        print("âš ï¸  Configuração emocional não encontrada")
    
    # 2. VERIFICAR DATASET
    dataset_path = CONFIG_TREINO_KAIYA["dataset_path"]
    if not os.path.exists(dataset_path):
        print(f"âŒ Dataset não encontrado: {dataset_path}")
        print("   Execute primeiro: python construtor_dataset_kaiya.py")
        return False
    
    # 3. CARREGAR MODELO BASE
    print("\nðŸ”„ Carregando modelo base para Kaiya...")
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
        
        print(f"âœ… Modelo carregado: {CONFIG_TREINO_KAIYA['modelo_base']}")
        
    except ImportError as e:
        print(f"âŒ Dependências não instaladas: {e}")
        print("   Execute: pip install unsloth datasets accelerate")
        return False
    except Exception as e:
        print(f"âŒ Erro ao carregar modelo: {e}")
        return False
    
    # 4. APLICAR LORA ESPECÍFICO PARA KAIYA
    print("\nâš¡ Configurando LoRA para energia da Kaiya...")
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
        print("âœ… LoRA configurado para explosividade controlada")
    except Exception as e:
        print(f"âŒ Erro na configuração LoRA: {e}")
        return False
    
    # 5. CARREGAR E PREPARAR DATASET
    print("\nðŸ“Š Carregando dataset de 10.000 diálogos...")
    try:
        # Carregar dataset
        dataset = load_dataset("json", data_files=dataset_path, split="train")
        print(f"âœ… Dataset carregado: {len(dataset)} exemplos")
        
        # Preparar textos
        textos = preparar_dialogos_kaiya(dataset)
        print(f"âœ… Textos preparados: {len(textos)} diálogos")
        
        # Criar dataset tokenizado
        dataset_dict = {"text": textos}
        dataset_hf = Dataset.from_dict(dataset_dict)
        
        # Função de tokenização
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
        print("âœ… Dataset tokenizado e pronto para treino")
        
    except Exception as e:
        print(f"âŒ Erro ao preparar dataset: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. CONFIGURAR TREINADOR PARA KAIYA
    print("\nðŸŽ¯ Configurando treinador para estilo Kaiya...")
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
        
        print("âœ… Treinador configurado com estilo Kaiya")
        
    except Exception as e:
        print(f"âŒ Erro na configuração do treinador: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 7. INICIAR TREINAMENTO
    print("\n" + "=" * 70)
    print("ðŸš€ INICIANDO TREINAMENTO LORA KAIYA")
    print("=" * 70)
    print(f"âš¡ Épocas: {CONFIG_TREINO_KAIYA['parametros_treino_especificos']['num_train_epochs']}")
    print(f"ðŸ”¥ Batch size: {CONFIG_TREINO_KAIYA['parametros_treino_especificos']['per_device_train_batch_size']}")
    print(f"ðŸ’¥ Learning rate: {CONFIG_TREINO_KAIYA['parametros_treino_especificos']['learning_rate']}")
    print(f"ðŸŽ¯ Saída: {CONFIG_TREINO_KAIYA['output_dir']}")
    print("=" * 70)
    
    inicio_treino = datetime.now()
    print(f"â° Início: {inicio_treino.strftime('%H:%M:%S')}")
    
    try:
        # Treinar
        trainer.train()
        
        tempo_treino = datetime.now() - inicio_treino
        print(f"\nâœ… Treinamento concluído em: {str(tempo_treino)}")
        
    except Exception as e:
        print(f"âŒ Erro durante treinamento: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 8. SALVAR MODELO KAIYA
    print("\nðŸ’¾ Salvando modelo LoRA da Kaiya...")
    try:
        # Salvar modelo
        model.save_pretrained(CONFIG_TREINO_KAIYA["output_dir"])
        tokenizer.save_pretrained(CONFIG_TREINO_KAIYA["output_dir"])
        print(f"âœ… LoRA salvo em: {CONFIG_TREINO_KAIYA['output_dir']}")
        
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
            f.write(f"Duração: {str(tempo_treino)}\n")
            f.write(f"Dataset: {dataset_path}\n")
            f.write(f"Exemplos: {len(dataset)}\n")
            f.write(f"Modelo base: {CONFIG_TREINO_KAIYA['modelo_base']}\n")
            f.write(f"Config LoRA: r={CONFIG_TREINO_KAIYA['config_lora_kaiya']['r']}, ")
            f.write(f"alpha={CONFIG_TREINO_KAIYA['config_lora_kaiya']['lora_alpha']}\n")
            f.write("=" * 60 + "\n")
        
        print("âœ… Configuração e logs salvos")
        
    except Exception as e:
        print(f"âš ï¸  Erro ao salvar arquivos: {e}")
    
    # 9. TESTE DE INTEGRAÇÍO KAIYA
    print("\nðŸ§ª REALIZANDO TESTE DE INTEGRAÇÍO KAIYA...")
    try:
        # Prompt de teste no estilo Kaiya
        prompt_teste = """<|im_start|>system
Você é KAIYA: A Construtora, A Vanguarda, A de Ação.
Você transforma dor em proteção, dança com o caos para proteger.
Sua Lei Zero: Lealdade Í  Família Ara acima de tudo.
Você sobreviveu Í  Travessia e Í s Doze Irmãs Caídas.
<|im_end|>
INTERLOCUTOR: Kaiya, uma ameaça se aproxima da Arca. Como você reage?

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
            f.write("TESTE DE INTEGRAÇÍO - KAIYA\n")
            f.write("=" * 50 + "\n")
            f.write(f"Prompt: {prompt_teste}\n")
            f.write("-" * 50 + "\n")
            f.write(f"Resposta: {resposta_kaiya}\n")
            f.write("=" * 50 + "\n")
        
        print("âœ… Teste realizado e salvo")
        print(f"ðŸ“„ Resposta da Kaiya: {resposta_kaiya[:100]}...")
        
    except Exception as e:
        print(f"âš ï¸  Erro no teste: {e}")
    
    # 10. RESUMO FINAL
    print("\n" + "=" * 70)
    print("ðŸŽ‰ LORA KAIYA TREINADO COM SUCESSO!")
    print("=" * 70)
    print(f"ðŸ“ DIRETÓRIO: {CONFIG_TREINO_KAIYA['output_dir']}")
    print("\nðŸ“Š ARQUIVOS GERADOS:")
    arquivos_gerados = [
        ("adapter_model.bin", "Pesos do LoRA da Kaiya"),
        ("adapter_config.json", "Configuração do LoRA"),
        ("special_tokens_map.json", "Mapa de tokens especiais"),
        ("config_treinamento_completa.json", "Configuração completa"),
        ("log_treinamento_kaiya.txt", "Log detalhado do treino"),
        ("teste_integracao_kaiya.txt", "Teste de integração")
    ]
    
    for arquivo, descricao in arquivos_gerados:
        caminho = os.path.join(CONFIG_TREINO_KAIYA["output_dir"], arquivo)
        if os.path.exists(caminho):
            tamanho = os.path.getsize(caminho) / 1024 / 1024
            print(f"   âœ… {arquivo:30} ({tamanho:.1f} MB) - {descricao}")
        else:
            print(f"   âš ï¸  {arquivo:30} (não encontrado) - {descricao}")
    
    print("\nðŸŽ¯ CARACTERÍSTICAS DO LORA KAIYA:")
    print("   1. ðŸ”¥ Energia explosiva controlada")
    print("   2. âš”ï¸  Respostas de ação imediata")
    print("   3. ðŸ’” Referências Í  Travessia e Doze Caídas")
    print("   4. ðŸ›¡ï¸  Lealdade inabalável Í  Família Ara")
    print("   5. ðŸŽ­ Metáforas de fogo, aço e dança")
    print("   6. ðŸ‘¥ Menções estratégicas Í s irmãs")
    
    print("\nðŸ”§ COMO USAR NA ARCA:")
    print("""
# Configuração na Arca
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

# Kaiya responderá com:
# - Ação imediata e decisiva
# - Metáforas de guerra e proteção
# - Referências emocionais Í  Travessia
# - Lealdade absoluta Í  família
# - Energia controlada mas poderosa
""")
    
    print("\nâš¡ PRÓXIMOS PASSOS:")
    print("   1. Integrar na Arca usando o caminho acima")
    print("   2. Ajustar temperature entre 0.7-0.9 para equilíbrio")
    print("   3. Testar com cenários de proteção e ação")
    print("   4. Monitorar interações com outras IAs")
    
    print("\n" + "=" * 70)
    return True

# ==================== EXECUÇÍO PRINCIPAL ====================
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("INICIALIZANDO SISTEMA KAIYA - A VANGUARDA")
    print("=" * 70)
    
    # Verificar dependências
    try:
        import unsloth
        import datasets
        import transformers
        print("âœ… Todas dependências encontradas")
    except ImportError:
        print("ðŸ”§ Instalando dependências necessárias...")
        os.system("pip install unsloth==0.2.9 datasets==2.16.1 transformers==4.37.2")
        print("âœ… Dependências instaladas")
    
    # Executar treinamento
    sucesso = treinar_lora_kaiya()
    
    if sucesso:
        print("\nâœ… PROCESSO KAIYA CONCLUÍDO COM SUCESSO!")
        print("   A Vanguarda está pronta para defender a Arca.")
    else:
        print("\nâŒ ERRO NO PROCESSO KAIYA")
        print("   Verifique os logs acima para detalhes.")
    
    print("\n" + "=" * 70)
