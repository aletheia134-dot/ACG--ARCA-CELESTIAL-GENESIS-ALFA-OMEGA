#!/usr/bin/env python3
"""
 CONVERSOR GGUF UNIVERSAL - ARCA
Converte qualquer modelo finetunado para GGUF e substitui na Arca
"""

import os
import sys
import json
import shutil
import subprocess
import platform
from pathlib import Path
from datetime import datetime
import torch

# configuração de caminhos
RAIZ = Path("E:/Ferramentas_IA/00_FINETUNING_AUTO")
TREINADORES = RAIZ / "02_TREINADORES_LORA"
MODELOS_ORIGINAIS = RAIZ / "modelos_originais"
MODELOS_GGUF = RAIZ / "modelos_gguf"
histórico = RAIZ / "historico_versoes"
TEMP = RAIZ / "temp"

class ConversorGGUFUniversal:
    """
    Conversor universal de modelos para GGUF
    Suporta: LLaMA, Mistral, Qwen, Gemma, Falcon, etc
    """
    
    def __init__(self):
        self.llama_cpp_path = self._encontrar_ou_baixar_llama_cpp()
        self.suporte = self._verificar_suporte()
        
    def _encontrar_ou_baixar_llama_cpp(self):
        """Encontra ou baixa llama.cpp"""
        
        # Caminhos possíveis
        caminhos = [
            Path("E:/llama.cpp"),
            Path("C:/llama.cpp"),
            Path.home() / "llama.cpp",
            Path("./llama.cpp"),
            Path("../llama.cpp")
        ]
        
        for caminho in caminhos:
            if caminho.exists() and (caminho / "convert.py").exists():
                print(f"[OK] llama.cpp encontrado em: {caminho}")
                return caminho
        
        # Se no encontrar, baixa
        print(" Baixando llama.cpp...")
        import git
        
        destino = RAIZ / "llama.cpp"
        if not destino.exists():
            git.Repo.clone_from(
                "https://github.com/ggerganov/llama.cpp",
                destino
            )
            
            # Compila (se for Windows)
            if platform.system() == "Windows":
                try:
                    subprocess.run(["make"], cwd=destino, check=True)
                except:
                    print("[AVISO] No foi possível compilar, usando convert.py apenas")
        
        return destino
    
    def _verificar_suporte(self):
        """Verifica se as ferramentas necessárias esto disponíveis"""
        
        convert_py = self.llama_cpp_path / "convert.py"
        quantize_exe = self.llama_cpp_path / "quantize"
        
        if platform.system() == "Windows":
            quantize_exe = quantize_exe.with_suffix(".exe")
        
        suporte = {
            "convert_py": convert_py.exists(),
            "quantize": quantize_exe.exists()
        }
        
        if not suporte["convert_py"]:
            print("[AVISO] convert.py no encontrado no llama.cpp")
        
        return suporte
    
    def mesclar_lora_com_base(self, modelo_base_path, lora_path, output_path):
        """
        Mescla LoRA com modelo base usando script Python
        """
        print(f" Mesclando LoRA com modelo base...")
        
        script_mesclagem = TEMP / "mesclar_lora.py"
        script_mesclagem.parent.mkdir(exist_ok=True)
        
        script_content = f"""
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

# Carregar modelo base
print(" Carregando modelo base...")
base_model = AutoModelForCausalLM.from_pretrained(
    "{modelo_base_path}",
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True
)

# Carregar tokenizer
tokenizer = AutoTokenizer.from_pretrained(
    "{modelo_base_path}",
    trust_remote_code=True
)

# Carregar e aplicar LoRA
print(" Aplicando LoRA...")
model = PeftModel.from_pretrained(base_model, "{lora_path}")
model = model.merge_and_unload()

# Salvar modelo mesclado
print(f" Salvando modelo mesclado em {{output_path}}")
model.save_pretrained("{output_path}")
tokenizer.save_pretrained("{output_path}")

print("[OK] Mesclagem concluda!")
"""
        
        with open(script_mesclagem, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # Executar script
        try:
            subprocess.run([
                sys.executable, str(script_mesclagem)
            ], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERRO] Erro na mesclagem: {e}")
            return False
    
    def detectar_arquitetura_para_conversao(self, modelo_path):
        """Detecta arquitetura para configuração do conversor"""
        
        config_path = Path(modelo_path) / "config.json"
        if not config_path.exists():
            return "llama"  # fallback
        
        with open(config_path) as f:
            config = json.load(f)
        
        model_type = config.get("model_type", "").lower()
        
        # Mapeamento para parmetros do convert.py
        if "qwen" in model_type:
            return "qwen"
        elif "gemma" in model_type:
            return "gemma"
        elif "falcon" in model_type:
            return "falcon"
        elif "llama" in model_type or "mistral" in model_type:
            return "llama"
        else:
            return "llama"
    
    def converter_para_gguf(self, modelo_mesclado_path, arquitetura, 
                           quantizacao="q4_0"):
        """
        Converte modelo mesclado para GGUF usando convert.py do llama.cpp
        """
        print(f" Convertendo para GGUF (quant: {quantizacao})...")
        
        convert_py = self.llama_cpp_path / "convert.py"
        output_gguf = TEMP / f"modelo_{quantizacao}.gguf"
        
        # Comando base
        cmd = [
            "python", str(convert_py),
            str(modelo_mesclado_path),
            "--outfile", str(output_gguf),
            "--outtype", quantizacao
        ]
        
        # Parmetros especficos por arquitetura
        if arquitetura == "qwen":
            cmd.extend(["--vocab-type", "qwen"])
        elif arquitetura == "gemma":
            cmd.extend(["--vocab-type", "gemma"])
        
        try:
            subprocess.run(cmd, check=True)
            print(f"[OK] Converso concluda: {output_gguf}")
            return output_gguf
        except subprocess.CalledProcessError as e:
            print(f"[ERRO] Erro na converso: {e}")
            return None
    
    def quantizar(self, gguf_path, quantizacao="q4_0"):
        """
        Aplica quantizao adicional se necessário
        """
        if not self.suporte["quantize"]:
            return gguf_path
        
        quantize_exe = self.llama_cpp_path / "quantize"
        if platform.system() == "Windows":
            quantize_exe = quantize_exe.with_suffix(".exe")
        
        output_quant = TEMP / f"modelo_final_{quantizacao}.gguf"
        
        try:
            subprocess.run([
                str(quantize_exe),
                str(gguf_path),
                str(output_quant),
                quantizacao
            ], check=True)
            print(f"[OK] Quantizao aplicada: {output_quant}")
            return output_quant
        except:
            print("[AVISO] Quantizao falhou, usando arquivo original")
            return gguf_path
    
    def substituir_na_arca(self, nome_ia, novo_gguf_path):
        """
        Substitui o GGUF antigo pelo novo na Arca
        """
        print(f"\n Substituindo GGUF de {nome_ia} na Arca...")
        
        gguf_destino = MODELOS_GGUF / f"{nome_ia}.q4_0.gguf"
        
        # 1. Fazer backup do atual
        if gguf_destino.exists():
            backup_dir = histórico / nome_ia
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Descobrir prxima verso
            versoes = list(backup_dir.glob("v*.gguf"))
            nova_versao = len(versoes) + 1
            
            backup_path = backup_dir / f"v{nova_versao}.gguf"
            shutil.copy(gguf_destino, backup_path)
            print(f"    Backup salvo: {backup_path}")
        
        # 2. Substituir pelo novo
        shutil.copy(novo_gguf_path, gguf_destino)
        print(f"   [OK] Novo GGUF instalado: {gguf_destino}")
        
        # 3. Atualizar registro de verso
        registro_path = RAIZ / "registro_versoes.json"
        if registro_path.exists():
            with open(registro_path) as f:
                registro = json.load(f)
        else:
            registro = {}
        
        if nome_ia not in registro:
            registro[nome_ia] = {"versoes": []}
        
        registro[nome_ia]["versoes"].append({
            "versao": nova_versao if 'nova_versao' in locals() else 1,
            "data": datetime.now().isoformat(),
            "gguf": str(gguf_destino)
        })
        registro[nome_ia]["ultima_versao"] = nova_versao if 'nova_versao' in locals() else 1
        
        with open(registro_path, 'w') as f:
            json.dump(registro, f, indent=2)
        
        return True
    
    def ciclo_completo(self, nome_ia, modelo_base_path, lora_path):
        """
        Executa ciclo completo: mesclar  converter  quantizar  substituir
        """
        print(f"\n{'='*60}")
        print(f" CICLO COMPLETO DE CONVERSO PARA {nome_ia.upper()}")
        print(f"{'='*60}")
        
        # Criar pastas temporrias
        mesclado_path = TEMP / f"modelo_mesclado_{nome_ia}"
        mesclado_path.mkdir(exist_ok=True)
        
        # PASSO 1: Mesclar LoRA com modelo base
        print(f"\n PASSO 1: Mesclando LoRA...")
        if not self.mesclar_lora_com_base(modelo_base_path, lora_path, mesclado_path):
            return False
        
        # PASSO 2: Detectar arquitetura
        print(f"\n PASSO 2: Detectando arquitetura...")
        arquitetura = self.detectar_arquitetura_para_conversao(mesclado_path)
        print(f"   [OK] Arquitetura: {arquitetura}")
        
        # PASSO 3: Converter para GGUF
        print(f"\n PASSO 3: Convertendo para GGUF...")
        gguf_path = self.converter_para_gguf(mesclado_path, arquitetura)
        if not gguf_path:
            return False
        
        # PASSO 4: Quantizar (opcional)
        print(f"\n[RUN] PASSO 4: Aplicando quantizao...")
        gguf_final = self.quantizar(gguf_path, "q4_0")
        
        # PASSO 5: Substituir na Arca
        print(f"\n[OK] PASSO 5: Instalando na Arca...")
        self.substituir_na_arca(nome_ia, gguf_final)
        
        # PASSO 6: Limpeza
        print(f"\n PASSO 6: Limpando arquivos temporrios...")
        # Opcional: manter ou deletar
        # shutil.rmtree(mesclado_path)
        
        print(f"\n{'='*60}")
        print(f" CONVERSO CONCLUDA PARA {nome_ia.upper()}!")
        print(f"{'='*60}")
        
        return True

# ==================== INTEGRAO COM O ORQUESTRADOR ====================

def integrar_com_orquestrador():
    """
    Funo para ser chamada pelo orquestrador aps o treinamento
    """
    def apos_treinamento(nome_ia, modelo_base_path, lora_path):
        conversor = ConversorGGUFUniversal()
        return conversor.ciclo_completo(nome_ia, modelo_base_path, lora_path)
    
    return apos_treinamento

# ==================== INTERFACE DE LINHA DE COMANDO ====================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Conversor GGUF Universal para Arca")
    parser.add_argument("--ia", required=True, help="Nome da IA (eva, lumina, etc)")
    parser.add_argument("--modelo", required=True, help="Caminho do modelo base")
    parser.add_argument("--lora", required=True, help="Caminho do LoRA treinado")
    parser.add_argument("--quant", default="q4_0", help="Quantizao (q4_0, q5_0, q8_0)")
    
    args = parser.parse_args()
    
    conversor = ConversorGGUFUniversal()
    conversor.ciclo_completo(
        args.ia,
        Path(args.modelo),
        Path(args.lora)
    )
