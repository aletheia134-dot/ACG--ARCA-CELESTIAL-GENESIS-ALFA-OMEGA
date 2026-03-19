"""
Fbrica de Dataset Automtica para LoRA
========================================
Gera datasets de image captioning prontos para fine-tuning LoRA.

CORREO PRINCIPAL:
 - 'captiv' NO  UM PACOTE REAL. O arquivo original falhava imediatamente no import.
 - Substitudo por BLIP-2 via HuggingFace Transformers (pacote real, amplamente usado).
 - Adicionado modo alternativo com BLIP base (mais leve, sem necessidade de GPU potente).
 - Adicionado argparse para rodar sem input() interativo (automatizvel).
 - Adicionado tratamento real de erros no carregamento do modelo.
 - GIF e BMP excludos: BLIP/BLIP-2 no suportam bem esses formatos.

DEPENDNCIAS REAIS:
    pip install transformers pillow tqdm torch torchvision
    (para BLIP-2 com GPU: necessita ~20GB VRAM; sem GPU usa float32 lento mas funciona)
"""

import os
import json
import argparse
import random
import logging
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Verificao de dependncias antes de qualquer coisa
try:
    from PIL import Image
except ImportError:
    print("ERRO: Pillow no instalado. Execute: pip install pillow")
    raise SystemExit(1)

try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False
    logger.warning("PyTorch no encontrado. O carregamento do modelo vai falhar.")


def carregar_modelo(modo: str):
    """
    Carrega o modelo de captioning real.
    
    Opes:
      'blip'   - Salesforce/blip-image-captioning-base (~1GB, roda em CPU mas lento)
      'blip2'  - Salesforce/blip2-opt-2.7b (~15GB, precisa GPU com VRAM suficiente)
    
    Retorna: (processor, model, device)
    """
    try:
        from transformers import (
            BlipProcessor, BlipForConditionalGeneration,
            Blip2Processor, Blip2ForConditionalGeneration
        )
    except ImportError:
        print("ERRO: transformers no instalado. Execute: pip install transformers")
        raise SystemExit(1)

    device = "cuda" if (_TORCH_AVAILABLE and torch.cuda.is_available()) else "cpu"
    logger.info("Dispositivo: %s", device.upper())

    if modo == "blip2":
        model_id = "Salesforce/blip2-opt-2.7b"
        logger.info("Carregando BLIP-2 (%s)... Isso pode demorar na primeira vez (~15GB).", model_id)
        if device == "cpu":
            logger.warning("BLIP-2 em CPU ser extremamente lento. Considere usar --modo blip para CPU.")
        try:
            processor = Blip2Processor.from_pretrained(model_id)
            dtype = torch.float16 if device == "cuda" else torch.float32
            model = Blip2ForConditionalGeneration.from_pretrained(model_id, torch_dtype=dtype)
            model.to(device)
            model.eval()
        except Exception as e:
            logger.error("Falha ao carregar BLIP-2: %s", e)
            logger.error("Verifique sua conexo, espao em disco e VRAM disponível.")
            raise
    else:
        model_id = "Salesforce/blip-image-captioning-base"
        logger.info("Carregando BLIP base (%s)...", model_id)
        try:
            processor = BlipProcessor.from_pretrained(model_id)
            model = BlipForConditionalGeneration.from_pretrained(model_id)
            model.to(device)
            model.eval()
        except Exception as e:
            logger.error("Falha ao carregar BLIP base: %s", e)
            raise

    logger.info("Modelo carregado com sucesso.")
    return processor, model, device


def descrever_imagem(processor, model, device, img_path: Path, modo: str) -> str:
    """
    Gera descrio de uma imagem usando o modelo carregado.
    Retorna string vazia em caso de falha (no lana exceo  o loop de batch no para).
    """
    try:
        import torch
        image = Image.open(img_path).convert("RGB")

        if modo == "blip2":
            inputs = processor(image, return_tensors="pt").to(device, torch.float16 if device == "cuda" else torch.float32)
            with torch.no_grad():
                output = model.generate(**inputs, max_new_tokens=100)
            descricao = processor.decode(output[0], skip_special_tokens=True).strip()
        else:
            inputs = processor(image, return_tensors="pt").to(device)
            with torch.no_grad():
                output = model.generate(**inputs, max_new_tokens=100)
            descricao = processor.decode(output[0], skip_special_tokens=True).strip()

        return descricao
    except Exception as e:
        logger.debug("Erro ao processar %s: %s", img_path.name, e)
        return ""


def gerar_perguntas(img_name: str) -> list:
    """
    Gera variaes de perguntas para uma imagem.
    Mantido do original  esta parte estava correta.
    """
    return [
        f"Descreva a imagem {img_name}",
        f"O que tem na foto {img_name}?",
        f"Explique o contedo da imagem {img_name}",
        f"Como  a cena mostrada em {img_name}?",
        f"Me conte sobre a foto {img_name}",
        "Me descreve essa foto",
        "O que você v aqui?",
        "Pode explicar essa imagem?",
        "Conta o que tem nessa foto",
        f"Descreva {img_name} em detalhes",
        f"Resumo da imagem {img_name}",
    ]


def main():
    parser = argparse.ArgumentParser(description="Fbrica de Dataset para LoRA via Image Captioning")
    parser.add_argument("--pasta", required=True, help="Pasta com as imagens")
    parser.add_argument("--modo", choices=["blip", "blip2"], default="blip",
                        help="Modelo a usar: 'blip' (leve, CPU ok) ou 'blip2' (potente, requer GPU)")
    parser.add_argument("--split", type=float, default=0.8,
                        help="Proporo de treino (0.0 a 1.0, default: 0.8)")
    parser.add_argument("--seed", type=int, default=42, help="Seed para reproducibilidade")
    args = parser.parse_args()

    random.seed(args.seed)

    pasta_path = Path(args.pasta)
    if not pasta_path.exists() or not pasta_path.is_dir():
        logger.error("Pasta no encontrada: %s", args.pasta)
        raise SystemExit(1)

    # BLIP/BLIP-2 funcionam bem com JPG e PNG. GIF e BMP excludos intencionalmente.
    extensoes_suportadas = ['*.jpg', '*.jpeg', '*.png']
    imagens = []
    for ext in extensoes_suportadas:
        imagens.extend(pasta_path.glob(ext))
        imagens.extend(pasta_path.glob(ext.upper()))

    if not imagens:
        logger.error("Nenhuma imagem JPG/PNG encontrada em: %s", pasta_path)
        raise SystemExit(1)

    logger.info("Encontradas %d imagens.", len(imagens))

    # Carrega modelo
    processor, model, device = carregar_modelo(args.modo)

    # Pasta de sada
    pasta_saida = pasta_path / "dataset_lora"
    pasta_saida.mkdir(exist_ok=True)
    pasta_txt = pasta_saida / "descricoes_individuais"
    pasta_txt.mkdir(exist_ok=True)

    dataset = []
    erros = []

    logger.info("Processando imagens...")
    for img_path in tqdm(imagens, desc="Gerando descries"):
        descricao = descrever_imagem(processor, model, device, img_path, args.modo)

        if not descricao:
            erros.append(f"{img_path.name}: falha na gerao de descrio")
            continue

        # Salva descrio individual
        txt_path = pasta_txt / f"{img_path.stem}.txt"
        try:
            txt_path.write_text(descricao, encoding="utf-8")
        except Exception as e:
            logger.warning("No foi possível salvar TXT para %s: %s", img_path.name, e)

        # Gera mltiplas entradas por imagem
        for pergunta in gerar_perguntas(img_path.name):
            dataset.append({
                "instruction": pergunta,
                "input": "",
                "output": descricao,
                "image_name": img_path.name,
                "image_path": str(img_path.resolve()),
                "modelo_usado": f"BLIP-2" if args.modo == "blip2" else "BLIP-base",
                "data_processamento": datetime.now().isoformat()
            })

    logger.info("%d itens de treinamento gerados. %d erros.", len(dataset), len(erros))

    if not dataset:
        logger.error("Nenhum item gerado. Verifique as imagens e o modelo.")
        raise SystemExit(1)

    # Divide treino/validao
    random.shuffle(dataset)
    split_idx = max(1, int(len(dataset) * args.split))
    treino = dataset[:split_idx]
    validacao = dataset[split_idx:] if split_idx < len(dataset) else []

    # Salva arquivos
    def salvar_json(dados, nome):
        caminho = pasta_saida / nome
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        logger.info("Salvo: %s (%d itens)", caminho, len(dados))
        return caminho

    salvar_json(dataset, "dataset_completo.json")
    salvar_json(treino, "treino_lora.json")
    if validacao:
        salvar_json(validacao, "validacao_lora.json")
    else:
        logger.warning("Dataset muito pequeno para criar validao separada.")

    # configuração LoRA
    config_lora = {
        "nome_projeto": pasta_path.name,
        "data_criacao": datetime.now().isoformat(),
        "total_imagens_processadas": len(imagens) - len(erros),
        "total_imagens_com_erro": len(erros),
        "total_exemplos_treino": len(treino),
        "total_exemplos_validacao": len(validacao),
        "modelo_captioning": f"BLIP-2 (blip2-opt-2.7b)" if args.modo == "blip2" else "BLIP base",
        "dispositivo_usado": device,
        "dataset_treino": "treino_lora.json",
        "dataset_validacao": "validacao_lora.json" if validacao else None,
        "configuracao_lora_sugerida": {
            "r": 16,
            "alpha": 32,
            "dropout": 0.1,
            "bias": "none",
            "target_modules": ["q_proj", "v_proj"]
        },
        "formato_dataset": "instruction-input-output (Alpaca format)"
    }

    config_path = pasta_saida / "config_lora.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_lora, f, indent=2, ensure_ascii=False)

    # Log de erros
    if erros:
        erros_path = pasta_saida / "erros.log"
        erros_path.write_text("\n".join(erros), encoding="utf-8")
        logger.warning("%d erros registrados em: %s", len(erros), erros_path)

    print("\n" + "=" * 50)
    print("DATASET GERADO COM SUCESSO")
    print("=" * 50)
    print(f"Pasta de sada: {pasta_saida.resolve()}")
    print(f"Itens para treino: {len(treino)}")
    print(f"Itens para validao: {len(validacao)}")
    print(f"Erros: {len(erros)}")
    print("=" * 50)


if __name__ == "__main__":
    main()
