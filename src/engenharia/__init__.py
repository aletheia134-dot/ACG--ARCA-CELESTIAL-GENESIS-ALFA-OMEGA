"""Engenharia de ferramentas e evolução"""

import logging

# Configura logger para diagnóstico
logger = logging.getLogger(__name__)

# ============================================================================
# BLOCO 1: Verificação do ChromaDB (dependência crítica)
# ============================================================================
try:
    import chromadb
    CHROMA_AVAILABLE = True
    logger.info(f"✓ ChromaDB disponível (versão: {chromadb.__version__})")
except ImportError:
    CHROMA_AVAILABLE = False
    logger.warning("✗ ChromaDB não disponível. Funcionalidades de memória serão limitadas.")
except Exception as e:
    CHROMA_AVAILABLE = False
    logger.error(f"✗ Erro inesperado com ChromaDB: {e}")

# ============================================================================
# BLOCO 2: Importações com mapeamento correto de nomes
# ============================================================================

# Dicionário para armazenar classes disponíveis
classes_disponiveis = {}

# 1. GerenciadorPropostas
try:
    from src.engenharia.sistema_propostas_ferramentas import GerenciadorPropostas
    classes_disponiveis['GerenciadorPropostas'] = GerenciadorPropostas
    logger.debug("✓ GerenciadorPropostas importado")
except ImportError as e:
    logger.error(f"✗ Erro ao importar GerenciadorPropostas: {e}")
    GerenciadorPropostas = None

# 2. ConstrutorFerramentasIncremental
try:
    from src.engenharia.construtor_ferramentas_incremental import ConstrutorFerramentasIncremental
    classes_disponiveis['ConstrutorFerramentasIncremental'] = ConstrutorFerramentasIncremental
    logger.debug("✓ ConstrutorFerramentasIncremental importado")
except ImportError as e:
    logger.error(f"✗ Erro ao importar ConstrutorFerramentasIncremental: {e}")
    ConstrutorFerramentasIncremental = None

# 3. SolicitadorArquivos
try:
    from src.engenharia.solicitador_arquivos import SolicitadorArquivos
    classes_disponiveis['SolicitadorArquivos'] = SolicitadorArquivos
    logger.debug("✓ SolicitadorArquivos importado")
except ImportError as e:
    logger.error(f"✗ Erro ao importar SolicitadorArquivos: {e}")
    SolicitadorArquivos = None

# 4. INTEGRACAOPROPTAS - CORRIGIDO! (nome do arquivo: integracao_proptas.py, classe: IntegracaoProptas)
try:
    # Importa do arquivo correto
    from src.engenharia.integracao_proptas import IntegracaoProptas as IntegracaoProptasOriginal
    # Expõe com o nome esperado pelo coração (IntegracaoProptas)
    IntegracaoProptas = IntegracaoProptasOriginal
    classes_disponiveis['IntegracaoProptas'] = IntegracaoProptas
    logger.info("✓ IntegracaoProptas importado com sucesso")
except ImportError as e:
    logger.error(f"✗ Erro ao importar IntegracaoProptas: {e}")
    IntegracaoProptas = None
    # Tenta descobrir o problema
    try:
        import sys
        import os
        caminho_arquivo = os.path.join(os.path.dirname(__file__), 'integracao_proptas.py')
        if os.path.exists(caminho_arquivo):
            logger.error(f"  → Arquivo existe: {caminho_arquivo}")
            # Tenta ler o arquivo para ver o nome da classe
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                conteudo = f.read()
                if 'class IntegracaoProptas' in conteudo:
                    logger.error("  → Classe 'IntegracaoProptas' encontrada no arquivo")
                elif 'class IntegracaoProptas' in conteudo:
                    logger.error("  → Classe 'IntegracaoProptas' encontrada (com p minúsculo)")
                else:
                    logger.error("  → Nenhuma classe com nome similar encontrada")
        else:
            logger.error(f"  → Arquivo NÃO existe: {caminho_arquivo}")
    except Exception as ex:
        logger.error(f"  → Erro ao verificar arquivo: {ex}")

# 5. BotAnalisadorSeguranca (vem de src.seguranca, não de src.engenharia)
try:
    from src.seguranca.bot_analise_seguranca import BotAnalisadorSeguranca
    classes_disponiveis['BotAnalisadorSeguranca'] = BotAnalisadorSeguranca
    logger.debug("✓ BotAnalisadorSeguranca importado")
except ImportError as e:
    logger.error(f"✗ Erro ao importar BotAnalisadorSeguranca: {e}")
    BotAnalisadorSeguranca = None

# 6. ScannerSistema
try:
    from src.engenharia.scanner_sistema import ScannerSistema
    classes_disponiveis['ScannerSistema'] = ScannerSistema
    logger.debug("✓ ScannerSistema importado")
except ImportError as e:
    logger.error(f"✗ Erro ao importar ScannerSistema: {e}")
    ScannerSistema = None

# 7. ListaEvolucaoIA
try:
    from src.engenharia.lista_evolucao_ia import ListaEvolucaoIA
    classes_disponiveis['ListaEvolucaoIA'] = ListaEvolucaoIA
    logger.debug("✓ ListaEvolucaoIA importado")
except ImportError as e:
    logger.error(f"✗ Erro ao importar ListaEvolucaoIA: {e}")
    ListaEvolucaoIA = None

# 8. GestorCicloEvolucao
try:
    from src.engenharia.gestor_ciclo_evolucao import GestorCicloEvolucao
    classes_disponiveis['GestorCicloEvolucao'] = GestorCicloEvolucao
    logger.debug("✓ GestorCicloEvolucao importado")
except ImportError as e:
    logger.error(f"✗ Erro ao importar GestorCicloEvolucao: {e}")
    GestorCicloEvolucao = None

# 9. IntegracaoEvolucaoIA
try:
    from src.engenharia.integracao_evolucao_ia import IntegracaoEvolucaoIA
    classes_disponiveis['IntegracaoEvolucaoIA'] = IntegracaoEvolucaoIA
    logger.debug("✓ IntegracaoEvolucaoIA importado")
except ImportError as e:
    logger.error(f"✗ Erro ao importar IntegracaoEvolucaoIA: {e}")
    IntegracaoEvolucaoIA = None

# ============================================================================
# BLOCO 3: Funções utilitárias
# ============================================================================

def verificar_disponibilidade():
    """Retorna dicionário com status de disponibilidade das classes"""
    return {nome: cls is not None for nome, cls in classes_disponiveis.items()}

def obter_classe(nome_classe):
    """Retorna a classe se disponível, None caso contrário"""
    return classes_disponiveis.get(nome_classe)

def diagnosticar():
    """Executa diagnóstico completo do módulo de engenharia"""
    print("\n" + "="*60)
    print("🔧 DIAGNÓSTICO DO MÓDULO DE ENGENHARIA")
    print("="*60)
    
    print(f"\n📦 ChromaDB: {'✅ Disponível' if CHROMA_AVAILABLE else '❌ Indisponível'}")
    
    print("\n📋 Classes esperadas vs disponíveis:")
    classes_esperadas = [
        'GerenciadorPropostas',
        'ConstrutorFerramentasIncremental',
        'SolicitadorArquivos',
        'IntegracaoProptas',  # Esta é a crítica!
        'BotAnalisadorSeguranca',
        'ScannerSistema',
        'ListaEvolucaoIA',
        'GestorCicloEvolucao',
        'IntegracaoEvolucaoIA'
    ]
    
    for classe in classes_esperadas:
        status = classes_disponiveis.get(classe)
        if status is not None:
            print(f"  ✅ {classe:<30} → Disponível")
        else:
            print(f"  ❌ {classe:<30} → Indisponível")
    
    print("\n📁 Verificando arquivos fisicamente:")
    import os
    pasta_atual = os.path.dirname(__file__)
    print(f"  📂 Pasta: {pasta_atual}")
    
    if os.path.exists(pasta_atual):
        arquivos = [f for f in os.listdir(pasta_atual) if f.endswith('.py') and f != '__init__.py']
        for arquivo in sorted(arquivos):
            print(f"     📄 {arquivo}")
    
    print("\n🔍 Verificando IntegracaoProptas especificamente:")
    caminho_arquivo = os.path.join(pasta_atual, 'integracao_proptas.py')
    if os.path.exists(caminho_arquivo):
        print(f"  ✅ Arquivo encontrado: {caminho_arquivo}")
        try:
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                conteudo = f.read()
                if 'class IntegracaoProptas' in conteudo:
                    print('  ✅ Classe "IntegracaoProptas" encontrada (com P maiúsculo)')
                elif 'class IntegracaoProptas' in conteudo:
                    print('  ⚠️ Classe "IntegracaoProptas" encontrada (com p minúsculo) - PRECISA CORRIGIR!')
                else:
                    print('  ❌ Nenhuma classe chamada IntegracaoProptas encontrada no arquivo')
        except Exception as e:
            print(f"  ❌ Erro ao ler arquivo: {e}")
    else:
        print(f"  ❌ Arquivo NÃO encontrado: {caminho_arquivo}")
    
    print("="*60 + "\n")

# ============================================================================
# BLOCO 4: Diagnóstico automático se executado diretamente
# ============================================================================

if __name__ == "__main__":
    diagnosticar()