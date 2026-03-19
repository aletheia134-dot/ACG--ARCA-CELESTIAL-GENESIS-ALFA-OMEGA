"""Engenharia de ferramentas e evolução"""

try:
    from src.engenharia.sistema_propostas_ferramentas import GerenciadorPropostas
except Exception:
    GerenciadorPropostas = None

try:
    from src.engenharia.construtor_ferramentas_incremental import ConstrutorFerramentasIncremental
except Exception:
    ConstrutorFerramentasIncremental = None

try:
    from src.engenharia.solicitador_arquivos import SolicitadorArquivos
except Exception:
    SolicitadorArquivos = None

try:
    from src.engenharia.integracao_proptas import IntegracaoProptas
except Exception:
    IntegracaoProptas = None

try:
    from src.seguranca.bot_analise_seguranca import BotAnalisadorSeguranca
except Exception:
    BotAnalisadorSeguranca = None

try:
    from src.engenharia.scanner_sistema import ScannerSistema
except Exception:
    ScannerSistema = None

try:
    from src.engenharia.lista_evolucao_ia import ListaEvolucaoIA
except Exception:
    ListaEvolucaoIA = None

try:
    from src.engenharia.gestor_ciclo_evolucao import GestorCicloEvolucao
except Exception:
    GestorCicloEvolucao = None

try:
    from src.engenharia.integracao_evolucao_ia import IntegracaoEvolucaoIA
except Exception:
    IntegracaoEvolucaoIA = None