# -*- coding: utf-8 -*-
"""
API CONSULTOR - Cliente modular para APIs externas (assíncrono, robusto)
Local: servicos/api_consultor.py

Melhorias (atualizadas):
- Sessão aiohttp gerenciada corretamente (reuso / fechamento).
- Retries com backoff exponencial para chamadas HTTP.
- Timeout configurável via config.
- Tratamento defensivo de JSON / respostas não-200.
- Cache com TTL (time-to-live) para evitar requests repetidos.
- Rate limiting básico via semaphore.
- Detecção de rate limit (headers X-RateLimit-Remaining).
- Logging consistente.
"""
from __future__ import annotations
import json
import os
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, List, Optional, Any
import datetime
import logging
import math
import time

logger = logging.getLogger(__name__)


class ApiConsultor:
    """
    Cliente REAL para consultar APIs externas.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = Path(config_path) if config_path else None
        self.config = self._carregar_config()
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache: Dict[str, Dict[str, Any]] = {}  # {key: {"data": ..., "timestamp": ..., "ttl": ...}}
        # políticas
        politicas = self.config.get("politicas", {}) if isinstance(self.config, dict) else {}
        self.timeout_segundos = int(politicas.get("timeout_segundos", 10))
        self.max_tentativas = int(politicas.get("max_tentativas", 3))
        self.cache_ttl_segundos = int(politicas.get("cache_ttl_segundos", 300))  # 5 min default
        # rate limiting
        self.rate_limit_semaphore = asyncio.Semaphore(int(politicas.get("max_requests_simultaneas", 5)))
        # connector limits
        self._connector_limit = int(self.config.get("http", {}).get("connector_limit", 10))
        logger.info("ApiConsultor inicializado (timeout=%ss, max_tentativas=%d, cache_ttl=%ds, rate_limit=%d)",
                    self.timeout_segundos, self.max_tentativas, self.cache_ttl_segundos, self.rate_limit_semaphore._value)

    def _carregar_config(self) -> Dict[str, Any]:
        default = {
            "apis": {
                "newsapi": {
                    "nome": "NewsAPI",
                    "endpoint": "https://newsapi.org/v2/everything",
                    "ativo": True,
                    "parametros_default": {"language": "pt", "sortBy": "publishedAt", "pageSize": 5}
                },
                "github": {
                    "nome": "GitHub API",
                    "endpoint": "https://api.github.com/search/repositories",
                    "ativo": True,
                    "parametros_default": {"sort": "updated", "order": "desc"}
                }
            },
            "politicas": {"timeout_segundos": 10, "max_tentativas": 3, "cache_ttl_segundos": 300, "max_requests_simultaneas": 5},
            "http": {"connector_limit": 10}
        }
        if not self.config_path:
            return default
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # shallow merge
                merged = default.copy()
                merged.update(loaded)
                return merged
        except Exception as e:
            logger.warning("Falha ao carregar config %s: %s - usando padrão", self.config_path, e, exc_info=True)
        return default

    def _obter_chave_api(self, nome_api: str) -> Optional[str]:
        mapa = {"newsapi": "NEWS_API_KEY", "github": "GITHUB_TOKEN"}
        key = mapa.get(nome_api)
        return os.getenv(key) if key else None

    def _cache_get(self, key: str) -> Optional[Any]:
        entry = self.cache.get(key)
        if entry:
            agora = time.time()
            if agora - entry["timestamp"] < entry.get("ttl", self.cache_ttl_segundos):
                logger.debug("Cache hit for %s", key)
                return entry["data"]
            else:
                del self.cache[key]  # expirado
        return None

    def _cache_set(self, key: str, data: Any, ttl: Optional[int] = None):
        ttl = ttl or self.cache_ttl_segundos
        self.cache[key] = {"data": data, "timestamp": time.time(), "ttl": ttl}
        logger.debug("Cache set for %s (ttl=%ds)", key, ttl)

    async def _criar_sessao(self):
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout_segundos)
            connector = aiohttp.TCPConnector(limit=self._connector_limit)
            self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
            logger.debug("Sessão aiohttp criada (limit=%d)", self._connector_limit)

    async def _request_with_retries(self, method: str, url: str, *, params: Optional[Dict] = None,
                                    headers: Optional[Dict] = None, json_body: Optional[Any] = None) -> Dict[str, Any]:
        """Faz request com retries exponenciais, rate limiting e tratamento de rate limit; retorna dict."""
        async with self.rate_limit_semaphore:  # rate limiting
            await self._criar_sessao()
            attempt = 0
            last_exc = None
            while attempt < max(1, self.max_tentativas):
                try:
                    attempt += 1
                    logger.debug("HTTP %s %s (attempt %d)", method, url, attempt)
                    async with self.session.request(method, url, params=params, headers=headers, json=json_body) as resp:
                        status = resp.status
                        text = await resp.text()
                        # rate limit check
                        remaining = resp.headers.get("X-RateLimit-Remaining")
                        if remaining and int(remaining) == 0:
                            reset_time = resp.headers.get("X-RateLimit-Reset")
                            if reset_time:
                                wait_time = max(1, int(reset_time) - int(time.time()))
                                logger.warning("Rate limit atingido; aguardando %ds", wait_time)
                                await asyncio.sleep(wait_time)
                                continue  # retry após wait
                        # tentar parse JSON
                        body = None
                        try:
                            body = json.loads(text)
                        except Exception:
                            body = text
                        return {"status": status, "body": body, "text": text}
                except asyncio.TimeoutError as e:
                    last_exc = e
                    logger.warning("Timeout em request %s %s (attempt %d)", method, url, attempt)
                except aiohttp.ClientError as e:
                    last_exc = e
                    logger.warning("ClientError em request %s %s (attempt %d): %s", method, url, attempt, e)
                except Exception as e:
                    last_exc = e
                    logger.exception("Erro inesperado em request %s %s (attempt %d)", method, url, attempt, exc_info=True)

                # backoff exponencial
                if attempt < self.max_tentativas:
                    backoff = min(10, (2 ** (attempt - 1)) + (0.1 * (attempt)))
                    await asyncio.sleep(backoff)

            # exauriu tentativas
            err_msg = str(last_exc) if last_exc is not None else "Falha desconhecida"
            return {"status": None, "body": None, "text": None, "error": err_msg}

    async def consultar_newsapi(self, query: str, language: str = "pt", page_size: int = 5) -> Dict[str, Any]:
        cache_key = f"newsapi:{query}:{language}:{page_size}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        api_key = self._obter_chave_api("newsapi")
        if not api_key:
            return {"sucesso": False, "erro": "NEWS_API_KEY não configurada no ambiente"}
        params = {"q": query, "apiKey": api_key, "language": language, "pageSize": page_size, "sortBy": "publishedAt"}
        url = self.config.get("apis", {}).get("newsapi", {}).get("endpoint", "https://newsapi.org/v2/everything")
        resp = await self._request_with_retries("GET", url, params=params)
        if resp.get("status") == 200 and resp.get("body"):
            dados = resp["body"]
            artigos = []
            for artigo in dados.get("articles", []):
                artigos.append({
                    "titulo": artigo.get("title", ""),
                    "descricao": artigo.get("description", ""),
                    "url": artigo.get("url", ""),
                    "fonte": artigo.get("source", {}).get("name", ""),
                    "data": artigo.get("publishedAt", ""),
                    "autor": artigo.get("author", "")
                })
            resultado = {"sucesso": True, "query": query, "total_resultados": dados.get("totalResults", 0), "artigos": artigos, "timestamp": datetime.datetime.now().isoformat()}
            self._cache_set(cache_key, resultado)
            return resultado
        else:
            return {"sucesso": False, "erro": resp.get("error") or f"Status {resp.get('status')}", "detalhes": str(resp.get("text"))[:400]}

    async def consultar_github(self, query: str, sort: str = "updated", order: str = "desc") -> Dict[str, Any]:
        cache_key = f"github:{query}:{sort}:{order}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        params = {"q": query, "sort": sort, "order": order, "per_page": 5}
        url = self.config.get("apis", {}).get("github", {}).get("endpoint", "https://api.github.com/search/repositories")
        headers = {}
        token = self._obter_chave_api("github")
        if token:
            headers["Authorization"] = f"token {token}"
        resp = await self._request_with_retries("GET", url, params=params, headers=headers)
        if resp.get("status") == 200 and resp.get("body"):
            dados = resp["body"]
            repos = []
            for repo in dados.get("items", []):
                repos.append({
                    "nome": repo.get("name", ""),
                    "descricao": repo.get("description", ""),
                    "linguagem": repo.get("language", ""),
                    "estrelas": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                    "url": repo.get("html_url", ""),
                    "ultima_atualizacao": repo.get("updated_at", "")
                })
            resultado = {"sucesso": True, "query": query, "total_resultados": dados.get("total_count", 0), "repositorios": repos, "timestamp": datetime.datetime.now().isoformat()}
            self._cache_set(cache_key, resultado)
            return resultado
        else:
            return {"sucesso": False, "erro": resp.get("error") or f"Status {resp.get('status')}", "detalhes": str(resp.get("text"))[:400]}

    async def consultar_wikipedia(self, query: str, language: str = "pt") -> Dict[str, Any]:
        cache_key = f"wikipedia:{query}:{language}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        params = {"action": "query", "format": "json", "prop": "extracts|info", "exintro": True, "explaintext": True, "inprop": "url", "titles": query}
        endpoint = f"https://{language}.wikipedia.org/w/api.php"
        resp = await self._request_with_retries("GET", endpoint, params=params)
        if resp.get("status") == 200 and resp.get("body"):
            dados = resp["body"]
            paginas = dados.get("query", {}).get("pages", {})
            resultados = []
            for page_id, pagina in paginas.items():
                if page_id != "-1":
                    resultados.append({
                        "titulo": pagina.get("title", ""),
                        "extrato": (pagina.get("extract") or "")[:500],
                        "url": pagina.get("fullurl", ""),
                        "tamanho": pagina.get("length", 0)
                    })
            resultado = {"sucesso": True, "query": query, "resultados": resultados, "timestamp": datetime.datetime.now().isoformat()}
            self._cache_set(cache_key, resultado)
            return resultado
        else:
            return {"sucesso": False, "erro": resp.get("error") or f"Status {resp.get('status')}", "detalhes": str(resp.get("text"))[:400]}

    async def consultar_inteligente(self, query: str, preferencia: Optional[str] = None) -> Dict[str, Any]:
        ql = query.lower()
        tipo_api = preferencia or "wikipedia"
        if not preferencia:
            if any(w in ql for w in ["noticia", "notícia", "jornal", "novidade", "hoje"]):
                tipo_api = "noticias"
            elif any(w in ql for w in ["github", "repositório", "código", "programa", "software"]):
                tipo_api = "github"
            else:
                tipo_api = "wikipedia"
        logger.info("Consulta inteligente -> %s for '%s'", tipo_api, query)
        if tipo_api in ("noticias", "news", "newsapi"):
            return await self.consultar_newsapi(query)
        if tipo_api in ("github",):
            return await self.consultar_github(query)
        return await self.consultar_wikipedia(query)

    def obter_apis_disponiveis(self) -> List[Dict[str, Any]]:
        apis = []
        apis.append({"nome": "NewsAPI", "tipo": "noticias", "disponivel": bool(self._obter_chave_api("newsapi")), "requer_chave": True, "descricao": "Notícias atualizadas"})
        apis.append({"nome": "GitHub API", "tipo": "github", "disponivel": True, "requer_chave": False, "descricao": "Repositórios de código"})
        apis.append({"nome": "Wikipedia API", "tipo": "wikipedia", "disponivel": True, "requer_chave": False, "descricao": "Conhecimento geral"})
        return apis

    async def testar_conexoes(self) -> Dict[str, bool]:
        resultados: Dict[str, bool] = {}
        try:
            r = await self.consultar_wikipedia("teste")
            resultados["wikipedia"] = bool(r.get("sucesso"))
        except Exception:
            resultados["wikipedia"] = False
        if self._obter_chave_api("newsapi"):
            try:
                r = await self.consultar_newsapi("tecnologia")
                resultados["newsapi"] = bool(r.get("sucesso"))
            except Exception:
                resultados["newsapi"] = False
        else:
            resultados["newsapi"] = False
        try:
            r = await self.consultar_github("python")
            resultados["github"] = bool(r.get("sucesso"))
        except Exception:
            resultados["github"] = False
        return resultados

    async def fechar(self):
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("Sessão HTTP fechada")
        self.session = None


# ---------- Helpers síncronos ----------

def consultar_noticias_sincrono(query: str, **kwargs) -> Dict[str, Any]:
    consultor = ApiConsultor()
    async def _c():
        return await consultor.consultar_newsapi(query, **kwargs)
    resultado = asyncio.run(_c())
    asyncio.run(consultor.fechar())
    return resultado

def consultar_inteligente_sincrono(query: str, **kwargs) -> Dict[str, Any]:
    consultor = ApiConsultor()
    async def _c():
        return await consultor.consultar_inteligente(query, **kwargs)
    resultado = asyncio.run(_c())
    asyncio.run(consultor.fechar())
    return resultado


# ===== EXEMPLO (executar como script) =====
if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    async def teste_completo():
        consultor = ApiConsultor()
        print("APIs disponíveis:", consultor.obter_apis_disponiveis())
        conex = await consultor.testar_conexoes()
        print("Conexões:", conex)
        r = await consultor.consultar_inteligente("últimas notícias de IA")
        print("Consulta inteligente:", r.get("sucesso"), r.get("total_resultados"))
        await consultor.fechar()

    asyncio.run(teste_completo())

