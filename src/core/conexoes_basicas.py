# -*- coding: utf-8 -*-
"""
Local: src/conexoes/conexoes_basicas.py
Função: Carregar credenciais e fornecer clientes para APIs usadas pelo sistema.Observações:
 - Carrega.env de forma tolerante.
 - Leitura de chaves suporta listas (CSV) quando apropriado.
 - Imports de bibliotecas externas são feitos de forma lazy dentro das funções.
 - Cache de conexões inicializadas para evitar reinit.
 - Integração com secrets_manager do coração (fallback).
 - Logs com exc_info para facilitar diagnóstico.
Sugestão aplicada: Usar cfg_get para ler chaves API.
Integrações aplicadas: Coração (carregamento init), analisador (fallback LLM), encarnacao (inferência 3D).
"""
from __future__ import annotations
import os
import logging
from typing import Optional, Any, List, Dict
from pathlib import Path

try:
    from dotenv import load_dotenv
except:
    logging.getLogger(__name__).warning("âš ï¸ load_dotenv não disponível")
    load_dotenv = None  # Se dotenv não estiver instalado, não falhar no import do módulo

logger = logging.getLogger(__name__)

# Sugestão aplicada: Import cfg_utils
try:
    from cfg_utils import cfg_get
    CFG_UTILS_DISPONIVEL = True
except ImportError:
    CFG_UTILS_DISPONIVEL = False

# Integrações aplicadas
try:
    from src.consulado.analisador_intencao import AnalisadorIntencao  # Para fallback LLM
    ANALISADOR_DISPONIVEL = True
except ImportError:
    ANALISADOR_DISPONIVEL = False

try:
    from src.encarnacao import EncarnacaoAPI  # Para inferência 3D
    ENCARNACAO_DISPONIVEL = True
except ImportError:
    ENCARNACAO_DISPONIVEL = False

try:
    from src.coracao import Coracao  # Para carregamento no init
    CORACAO_DISPONIVEL = True
except ImportError:
    CORACAO_DISPONIVEL = False

# Tentar carregar.env (procura arquivo no diretório do projeto ou caminho explícito)
def _load_dotenv_optional():
    if load_dotenv is None:
        logger.debug("python-dotenv não instalado; pulando carregamento de.env")
        return
    # Caminhos prováveis: repositório raiz (duas pastas acima deste arquivo)
    candidate = Path(__file__).resolve().parents[2] / ".env"
    if candidate.exists():
        try:
            load_dotenv(dotenv_path=str(candidate))
            logger.debug(".env carregado de %s", candidate)
        except Exception:
            logger.exception("Falha ao carregar.env de %s", candidate)
    else:
        logger.debug(".env não encontrado em %s; usando variáveis de ambiente do sistema", candidate)


_load_dotenv_optional()

# Cache global para conexões inicializadas (evita reinit desnecessária)
_CACHE_CONEXOES: Dict[str, Any] = {}

# -------------- Helpers de leitura de variáveis de ambiente --------------
def _get_env_str(name: str, default: Optional[str] = None, secrets_manager: Optional[Any] = None) -> Optional[str]:
    # Sugestão aplicada: Usar cfg_get para ler chaves API (fallback para env)
    if CFG_UTILS_DISPONIVEL and secrets_manager:
        try:
            val = cfg_get(secrets_manager, "API_KEYS", name, fallback=None)
            if val:
                return val
        except Exception:
            pass
    # Fallback para env
    val = os.getenv(name)
    if val is None:
        return default
    val = val.strip()
    return val if val != "" else default


def _get_env_list(name: str, default: Optional[List[str]] = None, sep: str = ",", secrets_manager: Optional[Any] = None) -> List[str]:
    raw = _get_env_str(name, "", secrets_manager)
    if not raw:
        return default or []
    # separar por vírgula e limpar espaços
    parts = [p.strip() for p in raw.split(sep) if p.strip()]
    return parts


def _path_exists_env(name: str, secrets_manager: Optional[Any] = None) -> Optional[Path]:
    raw = _get_env_str(name, secrets_manager=secrets_manager)
    if not raw:
        return None
    p = Path(raw).expanduser()
    if p.exists():
        return p
    logger.warning("Caminho de ambiente %s definido mas não existe: %s", name, p)
    return None


def _log_missing_key(name: str) -> None:
    logger.warning("Chave de ambiente '%s' não encontrada ou vazia.", name)


def _cache_conexao(key: str, conexao: Any):
    _CACHE_CONEXOES[key] = conexao
    logger.debug("Conexão %s cacheada", key)


def _get_cached_conexao(key: str) -> Optional[Any]:
    return _CACHE_CONEXOES.get(key)


# -------------- Conexões LLM --------------
def conectar_geminipro(secrets_manager: Optional[Any] = None) -> Optional[Any]:
    """Conecta ao Gemini Pro (google.generativeai)."""
    cached = _get_cached_conexao("geminipro")
    if cached:
        return cached

    key = _get_env_str("GEMINI_API_KEY", secrets_manager=secrets_manager)
    if not key:
        _log_missing_key("GEMINI_API_KEY")
        return None
    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=key)
        _cache_conexao("geminipro", genai)
        logger.info("Conexão ao Gemini Pro configurada")
        return genai
    except ImportError:
        logger.error("Biblioteca 'google-generativeai' não instalada.pip install google-generativeai", exc_info=True)
        return None
    except Exception:
        logger.exception("Erro ao inicializar Gemini Pro")
        return None


def conectar_openai(secrets_manager: Optional[Any] = None) -> Optional[Any]:
    """Conecta ao OpenAI (openai-python)."""
    cached = _get_cached_conexao("openai")
    if cached:
        return cached

    key = _get_env_str("OPENAI_API_KEY", secrets_manager=secrets_manager)
    if not key:
        _log_missing_key("OPENAI_API_KEY")
        return None
    try:
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=key)
        _cache_conexao("openai", client)
        logger.info("Conectado ao OpenAI")
        return client
    except ImportError:
        logger.error("Biblioteca 'openai' não instalada.pip install openai", exc_info=True)
        return None
    except Exception:
        logger.exception("Erro ao conectar ao OpenAI")
        return None


def conectar_anthropic(secrets_manager: Optional[Any] = None) -> Optional[Any]:
    """Conecta ao Anthropic (nova API)."""
    cached = _get_cached_conexao("anthropic")
    if cached:
        return cached

    key = _get_env_str("ANTHROPIC_API_KEY", secrets_manager=secrets_manager)
    if not key:
        _log_missing_key("ANTHROPIC_API_KEY")
        return None
    try:
        from anthropic import Anthropic  # type: ignore
        client = Anthropic(api_key=key)
        _cache_conexao("anthropic", client)
        logger.info("Conectado ao Anthropic")
        return client
    except ImportError:
        logger.error("Biblioteca 'anthropic' não instalada.", exc_info=True)
        return None
    except Exception:
        logger.exception("Erro ao conectar ao Anthropic")
        return None


def conectar_mistral(secrets_manager: Optional[Any] = None) -> Optional[Any]:
    """Conecta ao Mistral via OpenAI-compatible."""
    cached = _get_cached_conexao("mistral")
    if cached:
        return cached

    key = _get_env_str("MISTRAL_API_KEY", secrets_manager=secrets_manager)
    if not key:
        _log_missing_key("MISTRAL_API_KEY")
        return None
    try:
        from openai import OpenAI  # type: ignore
        base_url = _get_env_str("MISTRAL_BASE_URL", "https://api.mistral.ai/v1", secrets_manager)
        client = OpenAI(api_key=key, base_url=base_url)
        _cache_conexao("mistral", client)
        logger.info("Conectado ao Mistral")
        return client
    except ImportError:
        logger.error("Biblioteca 'openai' não instalada.", exc_info=True)
        return None
    except Exception:
        logger.exception("Erro ao conectar ao Mistral")
        return None


def conectar_ollama(secrets_manager: Optional[Any] = None) -> Optional[Any]:
    """Conecta ao Ollama (local LLM)."""
    cached = _get_cached_conexao("ollama")
    if cached:
        return cached

    host = _get_env_str("OLLAMA_HOST", "http://localhost:11434", secrets_manager)
    try:
        from ollama import Client  # type: ignore
        client = Client(host=host)
        _cache_conexao("ollama", client)
        logger.info("Conectado ao Ollama em %s", host)
        return client
    except ImportError:
        logger.error("Biblioteca 'ollama' não instalada.", exc_info=True)
        return None
    except Exception:
        logger.exception("Erro ao conectar ao Ollama")
        return None


def conectar_huggingface(secrets_manager: Optional[Any] = None) -> Optional[Any]:
    """Conecta ao Hugging Face (transformers)."""
    cached = _get_cached_conexao("huggingface")
    if cached:
        return cached

    key = _get_env_str("HUGGINGFACE_API_KEY", secrets_manager=secrets_manager)
    if not key:
        _log_missing_key("HUGGINGFACE_API_KEY")
        return None
    try:
        from huggingface_hub import HfApi  # type: ignore
        api = HfApi(token=key)
        _cache_conexao("huggingface", api)
        logger.info("Conectado ao Hugging Face")
        return api
    except ImportError:
        logger.error("Biblioteca 'huggingface_hub' não instalada.", exc_info=True)
        return None
    except Exception:
        logger.exception("Erro ao conectar ao Hugging Face")
        return None


# -------------- Agregador com Integrações --------------
def carregar_todas_conexoes(secrets_manager: Optional[Any] = None) -> Dict[str, Any]:
    """Carrega todas as conexões e integra com módulos."""
    logger.info("Carregando conexões básicas com integrações...")
    conexoes = {
        "geminipro": conectar_geminipro(secrets_manager),
        "openai": conectar_openai(secrets_manager),
        "anthropic": conectar_anthropic(secrets_manager),
        "mistral": conectar_mistral(secrets_manager),
        "ollama": conectar_ollama(secrets_manager),
        "huggingface": conectar_huggingface(secrets_manager),
    }
    total = len(conexoes)
    succ = sum(1 for v in conexoes.values() if v)
    logger.info("Conexões carregadas: %d/%d", succ, total)

    # Integração coração (carregamento no init)
    if CORACAO_DISPONIVEL:
        try:
            coracao = Coracao()  # Assumindo instância
            coracao.conexoes = conexoes  # Armazenar no coração
            logger.info("Conexões integradas ao coração.")
        except Exception:
            logger.exception("Erro ao integrar conexões ao coração.")

    # Integração analisador (fallback LLM)
    if ANALISADOR_DISPONIVEL:
        try:
            analisador = AnalisadorIntencao(config=None)  # Assumindo config
            analisador.conexoes_openai = conexoes.get("openai")  # Para fallback
            logger.info("Conexões integradas ao analisador (fallback LLM).")
        except Exception:
            logger.exception("Erro ao integrar conexões ao analisador.")

    # Integração encarnacao (inferência 3D)
    if ENCARNACAO_DISPONIVEL:
        try:
            encarnacao = EncarnacaoAPI(coracao=None)  # Assumindo coração
            encarnacao.conexoes_llm = conexoes  # Para inferência
            logger.info("Conexões integradas Í  encarnacao (inferência 3D).")
        except Exception:
            logger.exception("Erro ao integrar conexões Í  encarnacao.")

    return conexoes


# --- Exemplo de uso em linha de comando ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    conexoes = carregar_todas_conexoes()
    logger.info("Resumo de conexões (mostrando chaves e existência):")
    for k, v in conexoes.items():
        logger.info("  %s: %s", k, "OK" if v else "N/A")

# --- FIM DO ARQUIVO conexoes_basicas.py ---
