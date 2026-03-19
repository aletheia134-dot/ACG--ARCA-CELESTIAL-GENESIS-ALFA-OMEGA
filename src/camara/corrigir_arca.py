#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de correção automática para a Arca Celestial Genesis
Executar com: python corrigir_arca.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).parent.absolute()

def executar_comando(comando, descricao):
    """Executa um comando e mostra resultado"""
    print(f"\n▶ {descricao}...")
    try:
        resultado = subprocess.run(comando, shell=True, capture_output=True, text=True)
        if resultado.returncode == 0:
            print(f"  ✅ Sucesso")
            if resultado.stdout:
                print(f"     {resultado.stdout[:200]}")
        else:
            print(f"  ⚠️  Aviso: {resultado.stderr[:200]}")
        return resultado
    except Exception as e:
        print(f"  ❌ Erro: {e}")
        return None

def instalar_dependencias():
    """Instala todas as dependências necessárias"""
    print("\n" + "="*60)
    print(" INSTALANDO DEPENDÊNCIAS")
    print("="*60)
    
    # Ambiente CORE
    print("\n🔧 Ambiente CORE:")
    os.chdir(ROOT_DIR)
    executar_comando(
        f'cmd /c "venvs\\core\\Scripts\\activate && pip uninstall numpy -y && pip install numpy<2"',
        "Downgrade NumPy"
    )
    executar_comando(
        'cmd /c "venvs\\core\\Scripts\\activate && pip install chromadb sentence-transformers onnxruntime"',
        "Instalar ChromaDB"
    )
    executar_comando(
        'cmd /c "venvs\\core\\Scripts\\activate && pip install PyAudio SpeechRecognition opencv-python"',
        "Instalar áudio e visão"
    )
    
    # Ambiente FINETUNING
    print("\n🔧 Ambiente FINETUNING:")
    executar_comando(
        'cmd /c "venvs\\finetuning\\Scripts\\activate && pip install fastapi uvicorn httpx"',
        "Instalar FastAPI"
    )
    executar_comando(
        'cmd /c "venvs\\finetuning\\Scripts\\activate && pip install llama-cpp-python"',
        "Instalar llama-cpp"
    )

def corrigir_imports():
    """Corrige problemas de importação"""
    print("\n" + "="*60)
    print(" CORRIGINDO IMPORTAÇÕES")
    print("="*60)
    
    # Criar __init__.py para seguranca
    seguranca_init = ROOT_DIR / "src" / "seguranca" / "__init__.py"
    if not seguranca_init.exists():
        with open(seguranca_init, "w", encoding="utf-8") as f:
            f.write('"""\nPacote de segurança da Arca\n"""\n')
            f.write('from .detector_de_mentira import DetectorMentira\n\n')
            f.write('# Alias para compatibilidade\n')
            f.write('DetectorDeMentira = DetectorMentira\n\n')
            f.write('__all__ = [\'DetectorMentira\', \'DetectorDeMentira\']\n')
        print("  ✅ Criado src/seguranca/__init__.py")
    else:
        print("  ⏩ src/seguranca/__init__.py já existe")

def corrigir_config():
    """Corrige configurações"""
    print("\n" + "="*60)
    print(" CONFIGURANDO CAMINHOS")
    print("="*60)
    
    # Configurar avatares
    config_dir = ROOT_DIR / "config"
    config_dir.mkdir(exist_ok=True)
    
    avatares_config = config_dir / "avatares_config.json"
    if not avatares_config.exists():
        config = {
            "AVATARES_2D_PATH": str(ROOT_DIR / "assets" / "Avatares"),
            "AVATARES_POR_ALMA": {
                "EVA": "EVA",
                "LUMINA": "LUMINA", 
                "NYRA": "NYRA",
                "YUNA": "YUNA",
                "KAIYA": "KAIYA",
                "WELLINGTON": "WELLINGTON"
            }
        }
        import json
        with open(avatares_config, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"  ✅ Criado {avatares_config}")
    
    # Verificar/configurar config.ini
    config_ini = config_dir / "config.ini"
    if not config_ini.exists():
        with open(config_ini, "w", encoding="utf-8") as f:
            f.write("""[CAMINHOS]
SANTUARIOS_BASE_PATH = ./Santuarios
LOGS_PATH = ./Logs
ASSETS_PATH = ./assets
AVATARES_2D_PATH = ./assets/Avatares

[CORACAO]
MAX_WORKERS = 10
TIMEOUT_PADRAO = 30

[GPU]
USAR_GPU = True
""")
        print(f"  ✅ Criado {config_ini}")
    else:
        # Verificar se já tem AVATARES_2D_PATH
        with open(config_ini, "r", encoding="utf-8") as f:
            content = f.read()
        if "AVATARES_2D_PATH" not in content:
            with open(config_ini, "a", encoding="utf-8") as f:
                f.write("\nAVATARES_2D_PATH = ./assets/Avatares\n")
            print("  ✅ Adicionado AVATARES_2D_PATH ao config.ini")

def verificar_arquivos():
    """Verifica se todos os arquivos necessários existem"""
    print("\n" + "="*60)
    print(" VERIFICANDO ARQUIVOS")
    print("="*60)
    
    arquivos_criticos = [
        ("gatilho_conversa.py", ROOT_DIR / "src" / "core" / "gatilho_conversa.py"),
        ("detector_de_mentira.py", ROOT_DIR / "src" / "seguranca" / "detector_de_mentira.py"),
        ("modo_vidro_sentenca.py", ROOT_DIR / "src" / "julgamento" / "modo_vidro_sentenca.py"),
    ]
    
    for nome, caminho in arquivos_criticos:
        if caminho.exists():
            print(f"  ✅ {nome} encontrado")
        else:
            print(f"  ❌ {nome} NÃO encontrado em {caminho}")

def main():
    print("="*60)
    print(" ARCA CELESTIAL GENESIS - CORREÇÃO AUTOMÁTICA")
    print("="*60)
    
    # Verificar se está no diretório correto
    if not (ROOT_DIR / "venvs").exists():
        print("❌ ERRO: Execute este script da raiz do projeto (onde está a pasta 'venvs')")
        sys.exit(1)
    
    print(f"📁 Diretório raiz: {ROOT_DIR}")
    
    # Menu
    print("\nO que deseja corrigir?")
    print("1 - Tudo (recomendado)")
    print("2 - Apenas dependências")
    print("3 - Apenas imports e configurações")
    print("4 - Sair")
    
    opcao = input("\nEscolha (1-4): ").strip()
    
    if opcao == "1":
        instalar_dependencias()
        corrigir_imports()
        corrigir_config()
        verificar_arquivos()
    elif opcao == "2":
        instalar_dependencias()
    elif opcao == "3":
        corrigir_imports()
        corrigir_config()
        verificar_arquivos()
    else:
        print("Saindo...")
        return
    
    print("\n" + "="*60)
    print(" CORREÇÕES FINALIZADAS!")
    print("="*60)
    print("\nPróximos passos:")
    print("1. Execute: python main.py")
    print("2. Verifique se todos os erros foram resolvidos")
    print("3. Se ainda houver problemas, compartilhe o novo log")

if __name__ == "__main__":
    main()