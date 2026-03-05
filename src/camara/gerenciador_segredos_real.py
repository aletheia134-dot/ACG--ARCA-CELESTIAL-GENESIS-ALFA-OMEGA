# -*- coding: utf-8 -*-
"""
Arquivo: src/modules/gerenciador_segredos_real.py
FunÃ§Ã£o: Gerenciar acesso seguro a credenciais e chaves de API
Autor: Arquitetura Arca Celestial

Melhorias aplicadas:
 - Import defensivo de python-dotenv (fallback silencioso se ausente)
 - Cache thread-safe com lock
 - ValidaÃ§Ãµes básicas de formato mais robustas
 - Logs informativos sem exposiÃ§Ã£o de valores sensÃ­veis
 - Tipagem e pequenas correÃ§Ãµes de comportamento
"""
from __future__ import annotations


import os
import logging
from typing import Optional, Dict, List
import secrets

# load_dotenv Ã© opcional â€” tentar importar de forma defensiva
try:
    from dotenv import load_dotenv  # type: ignore
    _HAVE_DOTENV = True
except Exception:
    _HAVE_DOTENV = False


class GerenciadorSegredos:
    """
    Gerenciador centralizado de credenciais e chaves de API.PrincÃ­pio: falha segura â€” se um segredo nÃ£o existir, retorna None (ou loga se for obrigatÃ³rio).
    MantÃ©m um cache local (nÃ£o persistente) e fornece validaÃ§Ãµes básicas de formato.
    """

    def __init__(self, caminho_env: Optional[str] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._cache: Dict[str, str] = {}
        self._cache_lock = __import__("threading").RLock()

        # Carregar.env se possÃ­vel / desejado
        try:
            if caminho_env and os.path.exists(caminho_env):
                if _HAVE_DOTENV:
                    load_dotenv(caminho_env)
                    self.logger.info("Arquivo.env carregado de: %s", caminho_env)
                else:
                    self.logger.warning(".env especificado mas python-dotenv nÃ£o estÃ¡ instalado.")
            else:
                if _HAVE_DOTENV:
                    load_dotenv()
                    self.logger.debug("Tentativa de carregar.env da raiz do projeto")
        except Exception:
            self.logger.exception("Falha ao tentar carregar.env (ignorado)")

    def obter_segredo(self, chave: str, obrigatorio: bool = False) -> Optional[str]:
        """
        ObtÃ©m um segredo das variÃ¡veis de ambiente.Retorna None se nÃ£o existir.Se obrigatorio=True, registra erro.
        """
        if not chave:
            return None

        chave = chave.strip()
        with self._cache_lock:
            if chave in self._cache:
                return self._cache[chave]

        valor = os.getenv(chave)
        if valor:
            # armazenar no cache (nÃ£o expor valor em logs)
            with self._cache_lock:
                self._cache[chave] = valor
            self.logger.info("Segredo carregado: %s [tamanho=%d]", chave, len(valor))
            return valor

        if obrigatorio:
            self.logger.error("Segredo obrigatÃ³rio '%s' nÃ£o encontrado em variÃ¡veis de ambiente", chave)
        else:
            self.logger.debug("Segredo opcional '%s' nÃ£o encontrado", chave)
        return None

    def obter_api_key(self, servico: str) -> Optional[str]:
        """
        ObtÃ©m chave de API para um serviÃ§o especÃ­fico.Tenta vÃ¡rios nomes comuns.Valida o formato basicamente antes de retornar.
        """
        if not servico:
            return None

        servico_upper = servico.strip().upper()
        possiveis_chaves = [
            f"{servico_upper}_API_KEY",
            f"{servico_upper}_KEY",
            f"API_KEY_{servico_upper}",
            f"{servico_upper}KEY",
            f"{servico_upper}_TOKEN",
            f"TOKEN_{servico_upper}"
        ]

        for chave in possiveis_chaves:
            valor = self.obter_segredo(chave)
            if valor and self._validar_formato_basico(valor, servico_upper):
                self.logger.info("API key vÃ¡lida encontrada para %s (variÃ¡vel=%s)", servico_upper, chave)
                return valor

        self.logger.debug("Nenhuma API key vÃ¡lida encontrada para %s", servico_upper)
        return None

    def _validar_formato_basico(self, chave: str, servico: str) -> bool:
        """
        ValidaÃ§Ã£o simples e especÃ­fica por serviÃ§o para filtrar formatos obviamente invÃ¡lidos.NÃ£o substitui validação do provedor (teste de autenticaÃ§Ã£o).
        """
        if not chave or not servico:
            return False

        # Normalizar
        serv = servico.upper()
        k = chave.strip()

        # Regras especÃ­ficas
        if serv == "ANTHROPIC":
            if not k.startswith("sk-ant-") and len(k) < 30:
                self.logger.warning("Anthropic key com formato suspeito")
                return False

        if serv == "OPENAI":
            # Aceita sk- e fk- (inclui chaves de org/funcionais)
            if not (k.startswith("sk-") or k.startswith("fk-")):
                self.logger.warning("OpenAI key com formato suspeito")
                return False

        if serv == "GROQ":
            if not k.startswith("gsk_"):
                self.logger.warning("Groq key com formato suspeito")
                return False

        # Regras genÃ©ricas
        if len(k) < 20:
            self.logger.warning("API key muito curta para %s", serv)
            return False

        # Sem caracteres de quebra Ã³bvios
        if any(c in k for c in ['\n', '\r', ' ']):
            self.logger.warning("API key com caracteres invÃ¡lidos para %s", serv)
            return False

        # Passou as checagens simples
        return True

    def obter_configuracao_bd(self) -> Dict[str, Optional[str]]:
        """ObtÃ©m configuraÃ§Ãµes de banco de dados a partir das variÃ¡veis de ambiente."""
        return {
            "host": self.obter_segredo("DB_HOST", obrigatorio=False),
            "port": self.obter_segredo("DB_PORT", obrigatorio=False),
            "user": self.obter_segredo("DB_USER", obrigatorio=False),
            "password": self.obter_segredo("DB_PASSWORD", obrigatorio=False),
            "database": self.obter_segredo("DB_NAME", obrigatorio=False)
        }

    def validar_segredos_minimos(self) -> Dict[str, bool]:
        """Verifica presença/validação básica das principais API keys."""
        serviços = ["ANTHROPIC", "OPENAI", "GROQ", "GEMINI"]
        resultados = {s.lower(): (self.obter_api_key(s) is not None) for s in serviços}
        presentes = sum(resultados.values())
        total = len(resultados)
        self.logger.info("ValidaÃ§Ã£o de segredos: %d/%d APIs configuradas", presentes, total)
        return resultados

    def listar_segredos_disponiveis(self) -> List[str]:
        """
        Lista nomes de variÃ¡veis de ambiente relevantes sem expor valores.
        """
        relevantes = []
        for k in os.environ.keys():
            ku = k.upper()
            if any(p in ku for p in ("API", "KEY", "TOKEN", "SECRET", "PASSWORD", "DB", "HOST")):
                relevantes.append(k)
        return sorted(relevantes)

    def definir_segredo_temporario(self, chave: str, valor: str) -> None:
        """
        Define um segredo temporÃ¡rio apenas na sessÃ£o atual (nÃ£o persiste em.env).
        """
        if not chave:
            return
        os.environ[chave] = valor
        with self._cache_lock:
            self._cache[chave] = valor
        self.logger.info("Segredo temporÃ¡rio definido: %s [tamanho=%d]", chave, len(valor) if valor else 0)

    def limpar_cache(self) -> None:
        """Limpa o cache de segredos carregados."""
        with self._cache_lock:
            self._cache.clear()
        self.logger.debug("Cache de segredos limpo")


# Singleton auxiliar e funÃ§Ãµes utilitÃ¡rias
_instancia_global: Optional[GerenciadorSegredos] = None

def obter_gerenciador_segredos() -> GerenciadorSegredos:
    global _instancia_global
    if _instancia_global is None:
        _instancia_global = GerenciadorSegredos()
    return _instancia_global

def obter_api_key(servico: str) -> Optional[str]:
    return obter_gerenciador_segredos().obter_api_key(servico)

def obter_segredo(chave: str, obrigatorio: bool = False) -> Optional[str]:
    return obter_gerenciador_segredos().obter_segredo(chave, obrigatorio)


