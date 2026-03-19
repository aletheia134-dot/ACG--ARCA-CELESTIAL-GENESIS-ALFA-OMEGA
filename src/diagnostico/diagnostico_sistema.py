"""
Diagnstico do Sistema para Arca Celestial Genesis
=====================================================
CORREO:
 - Verificao separada de package vs import: agora reporta QUAL parte falhou,
   em vez de tratar ambas as falhas como "pacote faltando" sem distino.
 - Adicionado diagnstico de causa raiz quando import falha mas pacote est instalado.
"""

import sys
import platform
import subprocess
import importlib.util
import argparse


def check_package(package_name: str) -> tuple[bool, str]:
    """
    Verifica se um pacote est instalado via pip.
    Retorna (instalado: bool, verso: str)
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", package_name],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            # Extrai verso da sada do pip show
            for line in result.stdout.splitlines():
                if line.startswith("Version:"):
                    return True, line.split(":", 1)[1].strip()
            return True, "desconhecida"
        return False, ""
    except Exception:
        return False, ""


def check_import(module_name: str) -> tuple[bool, str]:
    """
    Verifica se um módulo pode ser importado.
    Retorna (importvel: bool, erro: str se falhou)
    """
    try:
        importlib.import_module(module_name)
        return True, ""
    except ImportError as e:
        return False, str(e)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def check_cuda():
    importavel, erro = check_import("torch")
    if not importavel:
        return f"PyTorch no importvel: {erro}"
    try:
        import torch
        return torch.cuda.is_available()
    except Exception as e:
        return f"Erro ao verificar CUDA: {e}"


def install_package(package_name: str) -> bool:
    try:
        print(f"  Instalando {package_name}...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", package_name],
            timeout=300
        )
        print(f"  OK: {package_name} instalado com sucesso.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  FALHA ação instalar {package_name}: {e}")
        return False
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT ação instalar {package_name}.")
        return False


def main(install_mode=False):
    print("DIAGNÓSTICO DO SISTEMA PARA ARCA CELESTIAL GENESIS")
    print("=" * 60)

    print(f"SO: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python: {sys.version}")
    if sys.version_info < (3, 8):
        print("AVISO crítico: Python < 3.8  muitas dependncias no vo funcionar.")

    cuda_status = check_cuda()
    if cuda_status is True:
        print("GPU/CUDA: disponível")
    elif cuda_status is False:
        print("GPU/CUDA: No disponível (CPU ser usado)")
    else:
        print(f"GPU/CUDA: {cuda_status}")

    print("\nVERIFICANDO PACOTES ESSENCIAIS:")
    print(f"{'PACOTE':<25} {'STATUS':<12} {'VERSO':<15} OBSERVAO")
    print("-" * 75)

    # (nome_pip, nome_import)  separados para diagnstico correto
    required_packages = [
        ("python-dotenv", "dotenv"),
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("llama-cpp-python", "llama_cpp"),
        ("chromadb", "chromadb"),
        ("speechrecognition", "speech_recognition"),
        ("pyttsx3", "pyttsx3"),
        ("torch", "torch"),
        ("spacy", "spacy"),
        ("transformers", "transformers"),
        ("nltk", "nltk"),
        ("pandas", "pandas"),
    ]

    missing_to_install = []

    for pip_name, import_name in required_packages:
        pkg_ok, versao = check_package(pip_name)
        imp_ok, imp_erro = check_import(import_name)

        if pkg_ok and imp_ok:
            print(f"  {'OK':<10} {pip_name:<25} {versao:<15}")
        elif pkg_ok and not imp_ok:
            # CORREO: Este caso era tratado como "faltando" antes  mas o pacote EST instalado.
            # O import falha por outro motivo (dependncia quebrada, verso incompatvel, etc.)
            print(f"  {'ERRO IMPORT':<10} {pip_name:<25} {versao:<15} Instalado mas no importvel: {imp_erro}")
            # No adiciona na lista de install  pip install no vai resolver
        elif not pkg_ok:
            print(f"  {'FALTANDO':<10} {pip_name:<25} {'':<15}")
            missing_to_install.append(pip_name)
        else:
            print(f"  {'DESCONHECIDO':<10} {pip_name:<25} {'':<15}")

    # Tkinter (built-in, no instalvel via pip)
    tk_ok, tk_erro = check_import("tkinter")
    if tk_ok:
        print(f"  {'OK':<10} {'tkinter (built-in)':<25}")
    else:
        print(f"  {'FALTANDO':<10} {'tkinter (built-in)':<25} {'':<15} Reinstale Python com tcl/tk marcado.")

    # Módulos do projeto
    print("\nMDULOS DO PROJETO (precisam ser rodados da raiz do projeto):")
    project_modules = ["src.config", "src.core.coracao_orquestrador"]
    for module in project_modules:
        imp_ok, imp_erro = check_import(module)
        if imp_ok:
            print(f"  OK       {module}")
        else:
            print(f"  ERRO     {module}: {imp_erro}")

    # Virtualenv
    in_venv = sys.prefix != sys.base_prefix
    venv_path = sys.prefix if in_venv else "(no ativo)"
    print(f"\nVirtualenv: {'Ativo em ' + venv_path if in_venv else 'NO ATIVO  recomendado usar venv'}")

    # Instalao automtica
    print("\nINSTALAO:")
    if missing_to_install:
        if install_mode:
            print(f"Instalando {len(missing_to_install)} pacotes faltantes...")
            for pkg in missing_to_install:
                install_package(pkg)
        else:
            print("Pacotes faltantes detectados. Use --install para instalar automaticamente.")
            print("Comandos manuais:")
            for pkg in missing_to_install:
                print(f"  pip install {pkg}")
    else:
        print("Todos os pacotes verificados esto instalados.")

    print("\nDICAS:")
    print("- Pacotes com 'ERRO IMPORT' esto instalados mas quebrados  tente reinstalar:")
    print("  pip install --force-reinstall <pacote>")
    print("- Para GPU: instale PyTorch com CUDA em https://pytorch.org")
    print("- Para spacy em pt: python -m spacy download pt_core_news_sm")
    print("- Verifique se est no venv correto antes de qualquer instalao.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Diagnstico e Instalador para Arca Celestial Genesis")
    parser.add_argument("--install", action="store_true", help="Ativar modo instalador automático")
    args = parser.parse_args()
    main(install_mode=args.install)
