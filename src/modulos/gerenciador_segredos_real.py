# -*- coding: utf-8 -*-
"""
Arquivo: src/modules/gerenciador_segredos_real.py
Funo: Gerenciar acesso seguro a credenciais e chaves de API
Autor: Arquitetura Arca Celestial

Melhorias aplicadas:
 - Import defensivo de python-dotenv (fallback silencioso se ausente)
 - Cache thread-safe com lock
 - Validaes bsicas de formato mais robustas
 - Logs informativos sem exposio de valores sensveis
 - Tipagem e pequenas correes de comportamento
"""
from __future__ import annotations


import os
import logging
from typing import Optional, Dict, List
import secrets

# load_dotenv  opcional  tentar importar de forma defensiva
try:
    from dotenv import load_dotenv  # type: ignore
    _HAVE_DOTENV = True
except Exception:
    _HAVE_DOTENV = False


class GerenciadorSegredos:
    """
    Gerenciador centralizado de credenciais e chaves de API.Princpio: falha segura  se um segredo no existir, retorna None (ou loga se for obrigatrio).
    Mantm um cache local (no persistente) e fornece validaes bsicas de formato.
    """

    def __init__(self, caminho_env: Optional[str] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._cache: Dict[str, str] = {}
        self._cache_lock = __import__("threading").RLock()

        # Carregar.env se possível / desejado
        try:
            if caminho_env and os.path.exists(caminho_env):
                if _HAVE_DOTENV:
                    load_dotenv(caminho_env)
                    self.logger.info("Arquivo.env carregado de: %s", caminho_env)
                else:
                    self.logger.warning(".env especificado mas python-dotenv no est instalado.")
            else:
                if _HAVE_DOTENV:
                    load_dotenv()
                    self.logger.debug("Tentativa de carregar.env da raiz do projeto")
        except Exception:
            self.logger.exception("Falha ao tentar carregar.env (ignorado)")

    def obter_segredo(self, chave: str, obrigatorio: bool = False) -> Optional[str]:
        """
        Obtm um segredo das variveis de ambiente.Retorna None se no existir.Se obrigatorio=True, registra erro.
        """
        if not chave:
            return None

        chave = chave.strip()
        with self._cache_lock:
            if chave in self._cache:
                return self._cache[chave]

        valor = os.getenv(chave)
        if valor:
            # armazenar no cache (no expor valor em logs)
            with self._cache_lock:
                self._cache[chave] = valor
            self.logger.info("Segredo carregado: %s [tamanho=%d]", chave, len(valor))
            return valor

        if obrigatorio:
            self.logger.error("Segredo obrigatrio '%s' no encontrado em variveis de ambiente", chave)
        else:
            self.logger.debug("Segredo opcional '%s' no encontrado", chave)
        return None

    def obter_api_key(self, servico: str) -> Optional[str]:
        """
        Obtm chave de API para um servio específico.Tenta vrios nomes comuns.válida o formato basicamente antes de retornar.
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
                self.logger.info("API key vlida encontrada para %s (varivel=%s)", servico_upper, chave)
                return valor

        self.logger.debug("Nenhuma API key vlida encontrada para %s", servico_upper)
        return None

    def _validar_formato_basico(self, chave: str, servico: str) -> bool:
        """
        Validao simples e especfica por servio para filtrar formatos obviamente invlidos.No substitui validao do provedor (teste de autenticao).
        """
        if not chave or not servico:
            return False

        # Normalizar
        serv = servico.upper()
        k = chave.strip()

        # Regras especficas
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

        # Regras genricas
        if len(k) < 20:
            self.logger.warning("API key muito curta para %s", serv)
            return False

        # Sem caracteres de quebra bvios
        if any(c in k for c in ['\n', '\r', ' ']):
            self.logger.warning("API key com caracteres invlidos para %s", serv)
            return False

        # Passou as checagens simples
        return True

    def obter_configuracao_bd(self) -> Dict[str, Optional[str]]:
        """Obtm configurações de banco de dados a partir das variveis de ambiente."""
        return {
            "host": self.obter_segredo("DB_HOST", obrigatorio=False),
            "port": self.obter_segredo("DB_PORT", obrigatorio=False),
            "user": self.obter_segredo("DB_USER", obrigatorio=False),
            "password": self.obter_segredo("DB_PASSWORD", obrigatorio=False),
            "database": self.obter_segredo("DB_NAME", obrigatorio=False)
        }

    def validar_segredos_minimos(self) -> Dict[str, bool]:
        """Verifica presena/validao básica das principais API keys."""
        servios = ["ANTHROPIC", "OPENAI", "GROQ", "GEMINI"]
        resultados = {s.lower(): (self.obter_api_key(s) is not None) for s in servios}
        presentes = sum(resultados.values())
        total = len(resultados)
        self.logger.info("Validao de segredos: %d/%d APIs configuradas", presentes, total)
        return resultados

    def listar_segredos_disponiveis(self) -> List[str]:
        """
        Lista nomes de variveis de ambiente relevantes sem expor valores.
        """
        relevantes = []
        for k in os.environ.keys():
            ku = k.upper()
            if any(p in ku for p in ("API", "KEY", "TOKEN", "SECRET", "PASSWORD", "DB", "HOST")):
                relevantes.append(k)
        return sorted(relevantes)

    def definir_segredo_temporario(self, chave: str, valor: str) -> None:
        """
        Define um segredo temporrio apenas na sessão atual (no persiste em.env).
        """
        if not chave:
            return
        os.environ[chave] = valor
        with self._cache_lock:
            self._cache[chave] = valor
        self.logger.info("Segredo temporrio definido: %s [tamanho=%d]", chave, len(valor) if valor else 0)

    def limpar_cache(self) -> None:
        """Limpa o cache de segredos carregados."""
        with self._cache_lock:
            self._cache.clear()
        self.logger.debug("Cache de segredos limpo")


# Singleton auxiliar e funções utilitrias
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


