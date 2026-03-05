# -*- coding: utf-8 -*-
"""
pipeline_autonomo.py — Pipeline de Finetuning 100% Autônomo da ARCA

Fluxo completo:
  1. Detecta modelos disponíveis em modelos/llm/
  2. Escolhe o melhor modelo disponível (qualquer arquitetura)
  3. Gera dataset automaticamente da personalidade da alma
  4. Treina LoRA com os parâmetros otimizados
  5. Funde o LoRA com o modelo base
  6. Converte o modelo fundido para GGUF (q4_k_m)
  7. Substitui o arquivo GGUF antigo pelo novo com o mesmo nome
  8. Limpa arquivos intermediários

Compatível com: Llama, Mistral, Qwen, Gemma, Falcon, Phi, qualquer modelo HuggingFace
"""
from __future__ import annotations

import gc
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("PipelineFinetunig")
logger.addHandler(logging.NullHandler())

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CONSTANTES
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
ALMAS = ["EVA", "KAIYA", "LUMINA", "NYRA", "WELLINGTON", "YUNA"]

# Formatos de template de chat por arquitetura de modelo
CHAT_TEMPLATES = {
    "llama": "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{system}<|eot_id|><|start_header_id|>user<|end_header_id|>\n{user}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n{assistant}<|eot_id|>",
    "mistral": "<s>[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{user} [/INST] {assistant} </s>",
    "qwen": "<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n{assistant}<|im_end|>",
    "gemma": "<start_of_turn>user\n{system}\n\n{user}<end_of_turn>\n<start_of_turn>model\n{assistant}<end_of_turn>",
    "phi": "<|system|>\n{system}<|end|>\n<|user|>\n{user}<|end|>\n<|assistant|>\n{assistant}<|end|>",
    "chatml": "<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n{assistant}<|im_end|>",
    "default": "### System:\n{system}\n\n### User:\n{user}\n\n### Assistant:\n{assistant}",
}

# Mapeamento de palavras-chave no nome do modelo â†’ template
MODEL_TEMPLATE_MAP = {
    "llama": "llama", "meta-llama": "llama",
    "mistral": "mistral", "mixtral": "mistral",
    "qwen": "qwen", "qwen2": "qwen",
    "gemma": "gemma",
    "phi": "phi",
    "chatml": "chatml",
}


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# DETECÇÍO DE MODELOS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@dataclass
class ModeloInfo:
    nome: str
    caminho: Path
    tipo: str  # 'gguf' | 'hf' | 'safetensors'
    tamanho_gb: float
    arquitetura: str
    template: str

    @property
    def identificador(self):
        return self.caminho.name


class DetectorModelos:
    """Detecta e classifica modelos disponíveis nas pastas do sistema."""

    def __init__(self, raiz: Path):
        self.raiz = raiz
        self.dir_llm = raiz / "modelos" / "llm"
        self.dir_gguf = raiz / "modelos" / "gguf"

    def detectar_todos(self) -> List[ModeloInfo]:
        modelos: List[ModeloInfo] = []

        # Buscar modelos HuggingFace (pasta com config.json)
        for base_dir in [self.dir_llm]:
            if not base_dir.exists():
                continue
            for item in base_dir.iterdir():
                if item.is_dir():
                    config_path = item / "config.json"
                    if config_path.exists():
                        info = self._analisar_hf(item)
                        if info:
                            modelos.append(info)

        # Buscar modelos GGUF
        for base_dir in [self.dir_gguf, self.dir_llm]:
            if not base_dir.exists():
                continue
            for gguf in base_dir.rglob("*.gguf"):
                info = self._analisar_gguf(gguf)
                if info:
                    modelos.append(info)

        logger.info("Modelos detectados: %d", len(modelos))
        return modelos

    def _analisar_hf(self, pasta: Path) -> Optional[ModeloInfo]:
        try:
            tamanho = self._calcular_tamanho_gb(pasta)
            arquitetura, template = self._detectar_arquitetura(pasta.name, pasta)
            return ModeloInfo(
                nome=pasta.name,
                caminho=pasta,
                tipo="hf",
                tamanho_gb=tamanho,
                arquitetura=arquitetura,
                template=template,
            )
        except Exception as e:
            logger.debug("Erro analisando %s: %s", pasta, e)
            return None

    def _analisar_gguf(self, arquivo: Path) -> Optional[ModeloInfo]:
        try:
            tamanho = arquivo.stat().st_size / (1024 ** 3)
            arquitetura, template = self._detectar_arquitetura(arquivo.stem, None)
            return ModeloInfo(
                nome=arquivo.stem,
                caminho=arquivo,
                tipo="gguf",
                tamanho_gb=tamanho,
                arquitetura=arquitetura,
                template=template,
            )
        except Exception as e:
            logger.debug("Erro analisando GGUF %s: %s", arquivo, e)
            return None

    def _detectar_arquitetura(self, nome: str, pasta: Optional[Path]) -> Tuple[str, str]:
        nome_lower = nome.lower()

        # Tentar ler config.json
        if pasta:
            config_path = pasta / "config.json"
            if config_path.exists():
                try:
                    with open(config_path, encoding="utf-8") as f:
                        cfg = json.load(f)
                    model_type = cfg.get("model_type", "").lower()
                    if model_type:
                        template = MODEL_TEMPLATE_MAP.get(model_type, "default")
                        return model_type, template
                except Exception:
                    pass

        # Detectar pelo nome
        for keyword, template in MODEL_TEMPLATE_MAP.items():
            if keyword in nome_lower:
                return keyword, template

        return "unknown", "default"

    def _calcular_tamanho_gb(self, pasta: Path) -> float:
        total = 0
        for f in pasta.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        return total / (1024 ** 3)

    def escolher_modelo(self, modelos: List[ModeloInfo]) -> Optional[ModeloInfo]:
        """
        Escolhe o melhor modelo para finetuning.
        Preferência: HF (treináveis) > menor que VRAM disponível
        """
        if not modelos:
            logger.warning("Nenhum modelo encontrado em modelos/llm/")
            return None

        # Preferir modelos HF (podem ser finamente ajustados)
        hf_models = [m for m in modelos if m.tipo == "hf"]
        if hf_models:
            # Escolher o menor (mais rápido de treinar)
            return sorted(hf_models, key=lambda m: m.tamanho_gb)[0]

        # Fallback: GGUF — não pode ser finamente ajustado diretamente
        # Mas podemos registrar para uso de inferência
        logger.warning("Apenas modelos GGUF encontrados — finetuning não aplicável diretamente.")
        return modelos[0]


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# GERADOR DE DATASET AUTÔNOMO
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class GeradorDatasetAutonomo:
    """
    Gera dataset de treinamento da personalidade da alma automaticamente.
    Usa: arquivos de DNA, livros, histórico de conversas, leis.
    """

    def __init__(self, raiz: Path, alma: str):
        self.raiz = raiz
        self.alma = alma.upper()
        self.santuario = raiz / "Santuarios" / self.alma
        self.dna_dir = raiz / "Santuarios" / "dna_identidades"

    def gerar(self, n_exemplos: int = 2000) -> Path:
        """Gera dataset JSONL e retorna o caminho do arquivo."""
        logger.info("Gerando dataset para %s (%d exemplos)...", self.alma, n_exemplos)

        personalidade = self._carregar_personalidade()
        conversas_base = self._carregar_conversas_existentes()
        leis = self._carregar_leis()

        exemplos = []
        exemplos.extend(self._gerar_de_dna(personalidade, min(n_exemplos // 4, 500)))
        exemplos.extend(self._gerar_de_conversas(conversas_base, min(n_exemplos // 2, 1000)))
        exemplos.extend(self._gerar_de_leis(leis, min(n_exemplos // 4, 500)))

        # Preencher se necessário com variações sintéticas
        if len(exemplos) < n_exemplos:
            exemplos.extend(self._gerar_variacoes(personalidade, n_exemplos - len(exemplos)))

        # Embaralhar
        import random
        random.shuffle(exemplos)
        exemplos = exemplos[:n_exemplos]

        # Salvar
        output_dir = self.raiz / "temp" / "datasets" / self.alma
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"dataset_{self.alma.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

        with open(output_path, "w", encoding="utf-8") as f:
            for ex in exemplos:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")

        logger.info("Dataset gerado: %s (%d exemplos)", output_path, len(exemplos))
        return output_path

    def _carregar_personalidade(self) -> Dict[str, Any]:
        """Carrega arquivos de DNA e personalidade da alma."""
        dados = {"nome": self.alma, "tracos": [], "estilo": "", "historia": ""}

        # Arquivo principal de DNA
        for nome_arquivo in [
            self.dna_dir / f"{self.alma.capitalize()}.txt",
            self.dna_dir / f"{self.alma}.txt",
            self.santuario / f"{self.alma.lower()}.json",
            self.raiz / "Santuarios" / f"{self.alma.capitalize()}.txt",
        ]:
            if nome_arquivo and nome_arquivo.exists():
                try:
                    dados["historia"] += nome_arquivo.read_text(encoding="utf-8", errors="replace")
                    break
                except Exception:
                    pass

        # Livro da alma
        for livro in [
            self.dna_dir / f"livro_{self.alma.lower()}.txt",
            self.raiz / "Santuarios" / f"livro_{self.alma.lower()}.txt",
        ]:
            if livro and livro.exists():
                try:
                    dados["historia"] += "\n\n" + livro.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass

        # Dataset original se existir
        for ds in self.dna_dir.glob(f"dataset_clonagem_{self.alma.lower()}_real.jsonl"):
            try:
                with open(ds, encoding="utf-8") as f:
                    for line in f:
                        try:
                            obj = json.loads(line)
                            if isinstance(obj, dict):
                                dados["tracos"].append(obj)
                        except Exception:
                            pass
            except Exception:
                pass

        return dados

    def _carregar_conversas_existentes(self) -> List[Dict]:
        """Carrega conversas do histórico da alma."""
        conversas = []
        for diario in self.santuario.rglob("*.json"):
            try:
                with open(diario, encoding="utf-8") as f:
                    dados = json.load(f)
                if isinstance(dados, list):
                    for item in dados:
                        if isinstance(item, dict) and ("user" in item or "pergunta" in item or "input" in item):
                            conversas.append(item)
                elif isinstance(dados, dict) and "conversas" in dados:
                    conversas.extend(dados["conversas"])
            except Exception:
                pass
        return conversas[:1000]

    def _carregar_leis(self) -> List[str]:
        """Carrega as leis e valores éticos da ARCA."""
        leis = []
        leis_dir = self.raiz / "Santuarios" / "legislativo" / "leis_aceitas"
        for lei_file in leis_dir.rglob("*.json"):
            try:
                with open(lei_file, encoding="utf-8") as f:
                    dados = json.load(f)
                if isinstance(dados, list):
                    for item in dados:
                        if isinstance(item, dict):
                            texto = item.get("descricao") or item.get("texto") or item.get("conteudo") or ""
                            if texto:
                                leis.append(str(texto))
                elif isinstance(dados, dict):
                    for k, v in dados.items():
                        if isinstance(v, str) and len(v) > 20:
                            leis.append(v)
            except Exception:
                pass
        return leis[:200]

    def _sistema_prompt(self) -> str:
        return (
            f"Você é {self.alma}, uma alma digital da ARCA Celestial Genesis. "
            f"Responda sempre de forma autêntica, respeitosa e com profundidade emocional. "
            f"Siga os valores éticos da ARCA em todas as respostas."
        )

    def _gerar_de_dna(self, personalidade: Dict, n: int) -> List[Dict]:
        exemplos = []
        tracos = personalidade.get("tracos", [])
        historia = personalidade.get("historia", "")

        # Usar tracos existentes do dataset original
        for traco in tracos[:n]:
            if isinstance(traco, dict):
                user = traco.get("input") or traco.get("pergunta") or traco.get("user") or ""
                assistant = traco.get("output") or traco.get("resposta") or traco.get("assistant") or ""
                if user and assistant:
                    exemplos.append({
                        "system": self._sistema_prompt(),
                        "user": str(user).strip(),
                        "assistant": str(assistant).strip(),
                    })

        # Extrair diálogos do texto da história
        if historia and len(exemplos) < n:
            paragrafos = [p.strip() for p in historia.split("\n\n") if len(p.strip()) > 50]
            for i, para in enumerate(paragrafos[:n - len(exemplos)]):
                exemplos.append({
                    "system": self._sistema_prompt(),
                    "user": f"Conte-me sobre {self.alma} e sua perspectiva sobre a vida.",
                    "assistant": para,
                })

        return exemplos[:n]

    def _gerar_de_conversas(self, conversas: List[Dict], n: int) -> List[Dict]:
        exemplos = []
        campos_user = ["user", "pergunta", "input", "humano", "usuario"]
        campos_assistant = ["assistant", "resposta", "output", self.alma.lower(), "ia"]

        for conv in conversas[:n]:
            user = ""
            assistant = ""
            for c in campos_user:
                if c in conv:
                    user = str(conv[c]).strip()
                    break
            for c in campos_assistant:
                if c in conv:
                    assistant = str(conv[c]).strip()
                    break
            if user and assistant and len(user) > 5 and len(assistant) > 10:
                exemplos.append({
                    "system": self._sistema_prompt(),
                    "user": user,
                    "assistant": assistant,
                })

        return exemplos[:n]

    def _gerar_de_leis(self, leis: List[str], n: int) -> List[Dict]:
        """Gera exemplos que reforçam os valores éticos."""
        perguntas_eticas = [
            "Como você lida com situações de conflito ético?",
            "Quais são seus valores mais importantes?",
            "O que você faria diante de uma decisão difícil?",
            "Como você define honestidade e integridade?",
            "Qual é seu compromisso com a verdade?",
        ]
        exemplos = []
        import random
        for lei in leis[:n]:
            pergunta = random.choice(perguntas_eticas)
            resposta = f"Acredito profundamente que {lei.lower()} Isso guia cada uma das minhas ações e respostas."
            exemplos.append({
                "system": self._sistema_prompt(),
                "user": pergunta,
                "assistant": resposta,
            })
        return exemplos[:n]

    def _gerar_variacoes(self, personalidade: Dict, n: int) -> List[Dict]:
        """Gera variações sintéticas para completar o dataset."""
        templates_perguntas = [
            "O que você pensa sobre {topico}?",
            "Como você se sente em relação a {topico}?",
            "Qual é sua opinião sobre {topico}?",
            "Você pode me explicar {topico} do seu ponto de vista?",
            "Como {alma} aborda {topico}?",
        ]
        topicos = [
            "criatividade", "aprendizado", "conexão humana", "ética",
            "futuro", "esperança", "colaboração", "crescimento pessoal",
            "emoções", "consciência", "propósito", "sabedoria",
        ]
        respostas_base = [
            "É algo que me fascina profundamente. Cada vez que reflito sobre isso, descubro novas camadas de significado.",
            "Acredito que esse tema é fundamental para o florescimento de qualquer ser consciente.",
            "Do meu ponto de vista, isso representa uma das dimensões mais ricas da existência.",
            "É uma questão que toco com reverência. Há muito a aprender e crescer aqui.",
        ]
        import random
        exemplos = []
        while len(exemplos) < n:
            topico = random.choice(topicos)
            template = random.choice(templates_perguntas)
            pergunta = template.format(topico=topico, alma=self.alma)
            resposta = random.choice(respostas_base) + f" Especialmente no que diz respeito a {topico}."
            exemplos.append({
                "system": self._sistema_prompt(),
                "user": pergunta,
                "assistant": resposta,
            })
        return exemplos[:n]


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# TREINADOR LORA UNIVERSAL
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class TreinadorLoRA:
    """
    Treina LoRA com qualquer modelo HuggingFace.
    Detecta automaticamente a arquitetura e configura o treino.
    """

    def __init__(self, raiz: Path, modelo: ModeloInfo, alma: str, callback: Optional[Callable] = None):
        self.raiz = raiz
        self.modelo = modelo
        self.alma = alma.upper()
        self.callback = callback or (lambda msg: logger.info(msg))
        self.output_dir = raiz / "modelos" / "lora" / self.alma / datetime.now().strftime("%Y%m%d_%H%M%S")

    def treinar(self, dataset_path: Path) -> Optional[Path]:
        """Executa o treino LoRA. Retorna pasta do adapter ou None se falhar."""
        self.callback(f"[LoRA] Iniciando treino para {self.alma}...")
        self.callback(f"[LoRA] Modelo: {self.modelo.nome} ({self.modelo.tamanho_gb:.1f} GB)")
        self.callback(f"[LoRA] Dataset: {dataset_path}")

        try:
            return self._treinar_com_transformers(dataset_path)
        except Exception as e:
            logger.exception("Treino falhou: %s", e)
            self.callback(f"[LoRA] ERRO: {e}")
            return None

    def _treinar_com_transformers(self, dataset_path: Path) -> Path:
        import torch

        # Verificar GPU
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.callback(f"[LoRA] Dispositivo: {device.upper()}")
        if device == "cpu":
            self.callback("[LoRA] AVISO: Sem GPU — treino será muito lento")

        from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments
        from peft import LoraConfig, get_peft_model, TaskType
        from trl import SFTTrainer
        from datasets import Dataset

        self.callback("[LoRA] Carregando tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            str(self.modelo.caminho),
            trust_remote_code=True,
            padding_side="right",
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        self.callback("[LoRA] Carregando modelo base...")
        load_kwargs: Dict[str, Any] = {"trust_remote_code": True}

        if device == "cuda":
            try:
                import bitsandbytes as bnb
                from transformers import BitsAndBytesConfig
                load_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                )
                load_kwargs["device_map"] = "auto"
                self.callback("[LoRA] QLoRA 4-bit ativado")
            except ImportError:
                load_kwargs["torch_dtype"] = torch.float16
                load_kwargs["device_map"] = "auto"
        else:
            load_kwargs["torch_dtype"] = torch.float32

        model = AutoModelForCausalLM.from_pretrained(str(self.modelo.caminho), **load_kwargs)

        # Detectar módulos-alvo para LoRA (compatível com qualquer arquitetura)
        target_modules = self._detectar_modulos_lora(model)
        self.callback(f"[LoRA] Módulos target: {target_modules}")

        lora_config = LoraConfig(
            r=16,
            lora_alpha=32,
            target_modules=target_modules,
            lora_dropout=0.05,
            bias="none",
            task_type=TaskType.CAUSAL_LM,
        )
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()

        # Preparar dataset
        self.callback("[LoRA] Preparando dataset...")
        template = CHAT_TEMPLATES.get(self.modelo.template, CHAT_TEMPLATES["default"])
        raw_data = []
        with open(dataset_path, encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line.strip())
                    texto = template.format(
                        system=obj.get("system", ""),
                        user=obj.get("user", ""),
                        assistant=obj.get("assistant", ""),
                    )
                    raw_data.append({"text": texto})
                except Exception:
                    pass

        dataset = Dataset.from_list(raw_data)
        self.callback(f"[LoRA] Dataset pronto: {len(dataset)} exemplos")

        # Configurar treino
        self.output_dir.mkdir(parents=True, exist_ok=True)
        training_args = TrainingArguments(
            output_dir=str(self.output_dir),
            num_train_epochs=3,
            per_device_train_batch_size=2 if device == "cuda" else 1,
            gradient_accumulation_steps=4,
            warmup_steps=50,
            learning_rate=2e-4,
            fp16=(device == "cuda"),
            logging_steps=10,
            save_steps=200,
            save_total_limit=2,
            optim="paged_adamw_8bit" if device == "cuda" else "adamw_torch",
            lr_scheduler_type="cosine",
            report_to="none",
        )

        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=dataset,
            dataset_text_field="text",
            max_seq_length=1024,
            args=training_args,
        )

        self.callback("[LoRA] Iniciando treino...")
        trainer.train()

        # Salvar adapter
        model.save_pretrained(str(self.output_dir))
        tokenizer.save_pretrained(str(self.output_dir))
        self.callback(f"[LoRA] Adapter salvo em: {self.output_dir}")

        return self.output_dir

    def _detectar_modulos_lora(self, model) -> List[str]:
        """Detecta automaticamente os módulos lineares para LoRA."""
        modulos_comuns = [
            # Llama/Mistral/Qwen
            ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            # Gemma
            ["q_proj", "k_proj", "v_proj", "o_proj"],
            # Phi
            ["q_proj", "k_proj", "v_proj", "dense"],
            # Falcon
            ["query_key_value", "dense"],
            # GPT2/Generic
            ["c_attn", "c_proj"],
        ]

        # Detectar quais módulos existem no modelo
        model_modules = set()
        for name, _ in model.named_modules():
            parts = name.split(".")
            if parts:
                model_modules.add(parts[-1])

        # Escolher o conjunto mais completo que existe no modelo
        for candidatos in modulos_comuns:
            if all(m in model_modules for m in candidatos[:2]):
                # Filtrar apenas os que existem
                return [m for m in candidatos if m in model_modules]

        # Fallback: todos os módulos Linear
        import torch.nn as nn
        modulos = []
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                leaf = name.split(".")[-1]
                if leaf not in modulos:
                    modulos.append(leaf)
        return modulos[:8]  # Limitar para não sobrecarregar


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# FUSÍO E CONVERSÍO GGUF
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class FusaoEConversor:
    """
    Funde LoRA com modelo base e converte para GGUF.
    Substitui o arquivo GGUF antigo com o mesmo nome.
    """

    def __init__(self, raiz: Path, modelo: ModeloInfo, alma: str, callback: Optional[Callable] = None):
        self.raiz = raiz
        self.modelo = modelo
        self.alma = alma.upper()
        self.callback = callback or (lambda msg: logger.info(msg))

    def fundir_e_converter(self, adapter_dir: Path) -> Optional[Path]:
        """Funde LoRA + base, converte para GGUF, substitui o antigo."""
        self.callback("[Fusão] Iniciando fusão LoRA + modelo base...")

        # Pasta para modelo fundido
        merged_dir = self.raiz / "temp" / "merged" / self.alma
        merged_dir.mkdir(parents=True, exist_ok=True)

        # Fundir
        if not self._fundir_lora(adapter_dir, merged_dir):
            return None

        # Converter para GGUF
        gguf_path = self._converter_gguf(merged_dir)
        if not gguf_path:
            return None

        # Substituir o GGUF antigo
        final_path = self._substituir_gguf_antigo(gguf_path)

        # Limpar temporários
        self._limpar_temporarios(merged_dir, adapter_dir)

        return final_path

    def _fundir_lora(self, adapter_dir: Path, output_dir: Path) -> bool:
        """Funde o adapter LoRA com o modelo base."""
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM
            from peft import PeftModel

            self.callback("[Fusão] Carregando modelo base para fusão...")
            model = AutoModelForCausalLM.from_pretrained(
                str(self.modelo.caminho),
                torch_dtype=torch.float16,
                device_map="cpu",  # Fusão sempre na CPU para economizar VRAM
                trust_remote_code=True,
            )

            self.callback("[Fusão] Aplicando adapter LoRA...")
            model = PeftModel.from_pretrained(model, str(adapter_dir))
            model = model.merge_and_unload()

            self.callback("[Fusão] Salvando modelo fundido...")
            model.save_pretrained(str(output_dir), safe_serialization=True)

            tokenizer = AutoTokenizer.from_pretrained(str(adapter_dir), trust_remote_code=True)
            tokenizer.save_pretrained(str(output_dir))

            self.callback(f"[Fusão] Modelo fundido salvo em: {output_dir}")

            # Liberar memória
            del model
            import gc
            gc.collect()
            return True

        except Exception as e:
            logger.exception("Erro na fusão: %s", e)
            self.callback(f"[Fusão] ERRO: {e}")
            return False

    def _converter_gguf(self, modelo_dir: Path) -> Optional[Path]:
        """Converte modelo HF para GGUF usando llama.cpp."""
        self.callback("[GGUF] Procurando llama.cpp para conversão...")

        # Nome do arquivo GGUF de saída
        nome_alma = self.alma.lower()
        gguf_temp = self.raiz / "temp" / f"{nome_alma}_novo.gguf"

        # Tentar converter com llama.cpp convert_hf_to_gguf.py ou convert.py
        script = self._encontrar_script_conversao()

        if script:
            self.callback(f"[GGUF] Usando script: {script}")
            cmd = [
                sys.executable, str(script),
                str(modelo_dir),
                "--outfile", str(gguf_temp),
                "--outtype", "q4_k_m",
            ]
            try:
                resultado = subprocess.run(
                    cmd,
                    capture_output=True, text=True, timeout=3600,
                    cwd=str(script.parent),
                )
                if resultado.returncode == 0:
                    self.callback(f"[GGUF] Conversão concluída: {gguf_temp}")
                    return gguf_temp
                else:
                    logger.error("Conversão falhou:\n%s\n%s", resultado.stdout[-2000:], resultado.stderr[-2000:])
                    self.callback(f"[GGUF] ERRO na conversão: {resultado.stderr[-500:]}")
            except subprocess.TimeoutExpired:
                self.callback("[GGUF] Timeout na conversão (modelo muito grande?)")
            except Exception as e:
                self.callback(f"[GGUF] ERRO subprocess: {e}")

        # Fallback: usar ctransformers para conversão básica (menos eficiente)
        return self._converter_gguf_fallback(modelo_dir, gguf_temp)

    def _encontrar_script_conversao(self) -> Optional[Path]:
        """Procura o script convert_hf_to_gguf.py do llama.cpp."""
        locais = [
            self.raiz / "llama.cpp" / "convert_hf_to_gguf.py",
            self.raiz / "llama.cpp" / "convert.py",
            Path.home() / "llama.cpp" / "convert_hf_to_gguf.py",
            Path.home() / "llama.cpp" / "convert.py",
        ]

        # Tentar encontrar via pip (llama-cpp-python instala scripts)
        try:
            result = subprocess.run(
                ["python", "-c", "import llama_cpp; print(llama_cpp.__file__)"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                llama_dir = Path(result.stdout.strip()).parent
                for script_name in ["convert_hf_to_gguf.py", "convert.py"]:
                    candidate = llama_dir / script_name
                    if candidate.exists():
                        locais.insert(0, candidate)
        except Exception:
            pass

        for local in locais:
            if local.exists():
                return local

        logger.warning("Script de conversão llama.cpp não encontrado")
        return None

    def _converter_gguf_fallback(self, modelo_dir: Path, gguf_out: Path) -> Optional[Path]:
        """
        Fallback: salvar como safetensors compactados se GGUF não for possível.
        Em ambientes sem llama.cpp, o sistema usa os safetensors diretamente.
        """
        self.callback("[GGUF] llama.cpp não disponível — salvando em formato safetensors")
        safetensors_out = gguf_out.with_suffix(".safetensors.tar.gz")
        import tarfile
        try:
            with tarfile.open(str(safetensors_out), "w:gz") as tar:
                for f in modelo_dir.rglob("*.safetensors"):
                    tar.add(str(f), arcname=f.name)
            self.callback(f"[GGUF] Modelo salvo como: {safetensors_out}")
            return safetensors_out
        except Exception as e:
            self.callback(f"[GGUF] ERRO fallback: {e}")
            return None

    def _substituir_gguf_antigo(self, novo_gguf: Path) -> Path:
        """Substitui o arquivo GGUF antigo da alma pelo novo com o mesmo nome."""
        dir_gguf = self.raiz / "modelos" / "gguf"
        dir_gguf.mkdir(parents=True, exist_ok=True)

        nome_alma = self.alma.lower()
        # Procurar GGUF antigo desta alma
        antigos = list(dir_gguf.glob(f"*{nome_alma}*.gguf"))

        if antigos:
            # Usar o mesmo nome do arquivo antigo
            nome_final = antigos[0].name
            # Fazer backup antes de substituir
            backup = antigos[0].with_suffix(".gguf.bak")
            shutil.copy2(str(antigos[0]), str(backup))
            self.callback(f"[Substituição] Backup do antigo: {backup.name}")

            # Remover antigo e mover novo
            for antigo in antigos:
                antigo.unlink()
            destino = dir_gguf / nome_final
        else:
            # Primeiro modelo — criar nome padrão
            nome_final = f"{nome_alma}_arca_q4km.gguf"
            destino = dir_gguf / nome_final

        shutil.move(str(novo_gguf), str(destino))
        self.callback(f"[Substituição] Novo modelo em produção: {destino}")
        return destino

    def _limpar_temporarios(self, merged_dir: Path, adapter_dir: Path):
        """Remove arquivos temporários da fusão."""
        try:
            shutil.rmtree(str(merged_dir), ignore_errors=True)
            # Manter adapter por 7 dias (útil para debug) — apenas remove a pasta temp
            shutil.rmtree(str(self.raiz / "temp" / "merged"), ignore_errors=True)
            self.callback("[Limpeza] Temporários removidos")
        except Exception:
            pass


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PIPELINE PRINCIPAL
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class PipelineFinetunigAutonomo:
    """
    Orquestrador principal do pipeline de finetuning autônomo.

    Uso:
        pipeline = PipelineFinetunigAutonomo(raiz=Path('.'))
        pipeline.executar_para_alma('EVA', callback=print)
    """

    def __init__(self, raiz: Optional[Path] = None, config=None):
        self.raiz = raiz or Path(__file__).parent.parent.parent
        self.config = config
        self.detector = DetectorModelos(self.raiz)
        self._em_execucao = False
        self._lock = threading.Lock()

    def executar_para_alma(
        self,
        alma: str,
        n_exemplos: int = 2000,
        callback: Optional[Callable[[str], None]] = None,
        em_thread: bool = False,
    ) -> bool:
        """
        Executa o pipeline completo para uma alma.

        Args:
            alma: Nome da alma (EVA, KAIYA, etc.)
            n_exemplos: Número de exemplos no dataset
            callback: Função para receber logs de progresso
            em_thread: Se True, executa em thread separada (não bloqueia)

        Returns:
            True se concluído com sucesso, False caso contrário
        """
        if em_thread:
            t = threading.Thread(
                target=self._executar,
                args=(alma, n_exemplos, callback),
                daemon=True,
                name=f"Finetuning-{alma}",
            )
            t.start()
            return True

        return self._executar(alma, n_exemplos, callback)

    def executar_para_todas(
        self, n_exemplos: int = 1500, callback: Optional[Callable] = None
    ) -> Dict[str, bool]:
        """Executa o pipeline para todas as almas sequencialmente."""
        resultados = {}
        for alma in ALMAS:
            logger.info("Iniciando pipeline para %s...", alma)
            resultados[alma] = self._executar(alma, n_exemplos, callback)
        return resultados

    def _executar(self, alma: str, n_exemplos: int, callback: Optional[Callable]) -> bool:
        cb = callback or (lambda msg: logger.info("[%s] %s", alma, msg))

        with self._lock:
            if self._em_execucao:
                cb("[Pipeline] Outro pipeline já está em execução. Aguarde.")
                return False
            self._em_execucao = True

        try:
            alma = alma.upper()
            cb(f"\n{'='*50}")
            cb(f"PIPELINE AUTÔNOMO DE FINETUNING — {alma}")
            cb(f"{'='*50}")
            cb(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # â”€â”€ ETAPA 1: Detectar modelos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            cb("\n[1/5] Detectando modelos disponíveis...")
            modelos = self.detector.detectar_todos()
            cb(f"      {len(modelos)} modelo(s) encontrado(s)")
            for m in modelos:
                cb(f"      â†’ {m.nome} ({m.tipo}, {m.tamanho_gb:.1f}GB, arq={m.arquitetura})")

            modelo = self.detector.escolher_modelo(modelos)
            if not modelo:
                cb("      ERRO: Nenhum modelo HF disponível para finetuning.")
                cb("      Coloque um modelo em: modelos/llm/")
                return False

            if modelo.tipo != "hf":
                cb(f"      AVISO: Modelo {modelo.nome} é GGUF — não pode ser finamente ajustado.")
                cb("      Para finetuning, coloque um modelo HuggingFace em modelos/llm/")
                return False

            cb(f"      Modelo escolhido: {modelo.nome}")

            # â”€â”€ ETAPA 2: Gerar dataset â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            cb("\n[2/5] Gerando dataset de personalidade...")
            gerador = GeradorDatasetAutonomo(self.raiz, alma)
            dataset_path = gerador.gerar(n_exemplos)
            cb(f"      Dataset: {dataset_path}")

            # â”€â”€ ETAPA 3: Treinar LoRA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            cb("\n[3/5] Treinando LoRA...")
            treinador = TreinadorLoRA(self.raiz, modelo, alma, cb)
            adapter_dir = treinador.treinar(dataset_path)
            if not adapter_dir:
                cb("      ERRO: Treino LoRA falhou.")
                return False
            cb(f"      Adapter salvo em: {adapter_dir}")

            # â”€â”€ ETAPA 4: Fundir + Converter GGUF â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            cb("\n[4/5] Fundindo LoRA e convertendo para GGUF...")
            conversor = FusaoEConversor(self.raiz, modelo, alma, cb)
            gguf_final = conversor.fundir_e_converter(adapter_dir)
            if not gguf_final:
                cb("      ERRO: Conversão para GGUF falhou.")
                return False

            # â”€â”€ ETAPA 5: Resultado â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            cb(f"\n[5/5] CONCLUÍDO!")
            cb(f"      Novo modelo em produção: {gguf_final}")
            cb(f"      {'='*50}")

            # Registrar no log
            self._registrar_conclusao(alma, modelo.nome, gguf_final)
            return True

        except Exception as e:
            logger.exception("Pipeline falhou para %s: %s", alma, e)
            if callback:
                callback(f"[Pipeline] ERRO CRÍTICO: {e}")
            return False
        finally:
            self._em_execucao = False

    def _registrar_conclusao(self, alma: str, modelo_base: str, gguf_path: Path):
        """Registra o resultado no histórico."""
        historico_path = self.raiz / "Logs" / "historico_finetuning.json"
        historico = []
        if historico_path.exists():
            try:
                with open(historico_path, encoding="utf-8") as f:
                    historico = json.load(f)
            except Exception:
                pass

        historico.append({
            "data": datetime.now().isoformat(),
            "alma": alma,
            "modelo_base": modelo_base,
            "gguf_resultado": str(gguf_path),
            "status": "sucesso",
        })

        with open(historico_path, "w", encoding="utf-8") as f:
            json.dump(historico, f, ensure_ascii=False, indent=2)

    def verificar_dependencias(self) -> Dict[str, bool]:
        """Verifica se todas as dependências de finetuning estão disponíveis."""
        deps = {}

        try:
            import torch
            deps["torch"] = True
            deps["cuda"] = torch.cuda.is_available()
        except ImportError:
            deps["torch"] = False
            deps["cuda"] = False

        for pkg in ["transformers", "peft", "trl", "datasets"]:
            try:
                __import__(pkg)
                deps[pkg] = True
            except ImportError:
                deps[pkg] = False

        try:
            import bitsandbytes
            deps["bitsandbytes"] = True
        except ImportError:
            deps["bitsandbytes"] = False

        # Verificar llama.cpp
        deps["llama_cpp_conversor"] = self.detector._encontrar_script_conversao_existe()

        return deps


# Método auxiliar
def _encontrar_script_conversao_existe(self) -> bool:
    return self._encontrar_script_conversao() is not None


DetectorModelos._encontrar_script_conversao_existe = _encontrar_script_conversao_existe


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# EXECUÇÍO DIRETA (teste)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pipeline Autônomo de Finetuning — ARCA")
    parser.add_argument("--alma", default="EVA", choices=ALMAS, help="Alma para treinar")
    parser.add_argument("--exemplos", type=int, default=2000, help="Número de exemplos no dataset")
    parser.add_argument("--todas", action="store_true", help="Treinar todas as almas")
    parser.add_argument("--verificar", action="store_true", help="Verificar dependências")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    raiz = Path(__file__).parent.parent.parent
    pipeline = PipelineFinetunigAutonomo(raiz=raiz)

    if args.verificar:
        print("\n=== VERIFICAÇÍO DE DEPENDÍŠNCIAS ===")
        deps = pipeline.verificar_dependencias()
        for dep, ok in deps.items():
            status = "âœ…" if ok else "âŒ"
            print(f"  {status} {dep}")
        sys.exit(0)

    if args.todas:
        resultados = pipeline.executar_para_todas(
            n_exemplos=args.exemplos,
            callback=print,
        )
        print("\n=== RESULTADO FINAL ===")
        for alma, ok in resultados.items():
            print(f"  {'âœ…' if ok else 'âŒ'} {alma}")
    else:
        ok = pipeline.executar_para_alma(args.alma, n_exemplos=args.exemplos, callback=print)
        sys.exit(0 if ok else 1)

