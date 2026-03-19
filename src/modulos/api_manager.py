from __future__ import annotations
# src/core/api_manager.py
# -*- coding: utf-8 -*-
"""
Gerencia interações com APIs externas delegando execução e segurana ação Consulado Soberano.
Implementao defensiva e real:
 - usa o Consulado quando disponível para todas as chamadas HTTP
 - válida ações via validador tico quando disponível
 - registra eventos relevantes na memória quando possível
 - caching local com TTL
 - implementaes reais de provedores de clima e de consultas (NewsAPI, GitHub, Wikipedia, Reqres)
"""
from pathlib import Path
from typing import Dict, Any, Optional, List
import asyncio
import json
import logging
import time

from src.config.config import get_config, ConfigError  # assume existir no projeto

logger = logging.getLogger("APIManager")


class APIManager:
    def __init__(self, coracao_ref: Any, config_instance: Any = None):
        self.coracao = coracao_ref
        self.config = config_instance or get_config()
        self.logger = logging.getLogger("APIManager")

        # Cache local com TTL (dicionrio: {key: {"data": ..., "timestamp": ..., "ttl": ...}})
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl_segundos = int(getattr(self.config, "CACHE_API_TTL_SEGUNDOS", 600))

        # Verificaes bsicas
        if not hasattr(self.coracao, "secrets_manager") or not self.coracao.secrets_manager:
            self.logger.critical("[API_MANAGER] Secrets Manager no disponível no Corao.")
            raise ConfigError("Secrets Manager no disponível para APIManager.")

        # Carregar chaves (podem ser listas ou valores nicos)
        self.OPENWEATHERMAP_API_KEYS: List[str] = self.coracao.secrets_manager.get_secret_or_none(
            "OPENWEATHERMAP_API_KEYS", default=[]
        ) or []
        self.OPENWEATHERMAP_CIDADE = getattr(self.config, "OPENWEATHERMAP_CIDADE", None) \
            or (self.config.get("OPENWEATHERMAP_CIDADE") if hasattr(self.config, "get") else None)
        self.OPENWEATHERMAP_PAIS = getattr(self.config, "OPENWEATHERMAP_PAIS", None) \
            or (self.config.get("OPENWEATHERMAP_PAIS") if hasattr(self.config, "get") else None)

        self.WEATHERAPI_COM_API_KEY = self.coracao.secrets_manager.get_secret_or_none("WEATHERAPI_COM_API_KEY")
        self.ACCUWEATHER_API_KEY = self.coracao.secrets_manager.get_secret_or_none("ACCUWEATHER_API_KEY")
        self.TOMORROW_IO_API_KEY = self.coracao.secrets_manager.get_secret_or_none("TOMORROW_IO_API_KEY")
        self.NEWSAPI_API_KEY = self.coracao.secrets_manager.get_secret_or_none("NEWSAPI_API_KEY")
        self.REQRES_API_KEY = self.coracao.secrets_manager.get_secret_or_none("REQRES_API_KEY")
        self.GITHUB_TOKEN = self.coracao.secrets_manager.get_secret_or_none("GITHUB_TOKEN")

        self.logger.info("[API_MANAGER] Inicializado. Cache TTL: %ds", self.cache_ttl_segundos)

    # ----------------------
    # Cache helpers
    # ----------------------
    def _cache_get(self, key: str) -> Optional[Any]:
        entry = self.cache.get(key)
        if not entry:
            return None
        agora = time.time()
        if agora - entry["timestamp"] < entry.get("ttl", self.cache_ttl_segundos):
            self.logger.debug("[API_MANAGER] Cache hit: %s", key)
            return entry["data"]
        # expirado
        try:
            del self.cache[key]
        except KeyError:
            pass
        return None

    def _cache_set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl or self.cache_ttl_segundos
        self.cache[key] = {"data": data, "timestamp": time.time(), "ttl": ttl}
        self.logger.debug("[API_MANAGER] Cache set: %s (ttl=%ds)", key, ttl)

    # ----------------------
    # Helpers internos
    # ----------------------
    def _validar_acao_externa(self, acao: str, detalhes: str) -> bool:
        validador = getattr(self.coracao, "validador_etico", None)
        if callable(getattr(validador, "validar_acao", None)):
            try:
                aprovado, motivo = validador.validar_acao(nome_acao=acao, descricao_acao=detalhes, autor="APIManager")
                if not aprovado:
                    self.logger.warning("[API_MANAGER] Validador tico bloqueou a ação: %s -> %s", acao, motivo)
                return bool(aprovado)
            except Exception:
                self.logger.exception("[API_MANAGER] Erro ao chamar ValidadorEtico; permitindo por fallback.")
                return True
        self.logger.warning("[API_MANAGER] Validador tico no disponível  prosseguindo sem validao.")
        return True

    def _registrar_na_memoria(self, evento: str, categoria: str = "api_externa") -> None:
        gm = getattr(self.coracao, "gerenciador_memoria", None)
        try:
            if callable(getattr(gm, "registrar_evento_na_historia", None)):
                gm.registrar_evento_na_historia(autor="APIManager", evento=evento, categoria=categoria)
            else:
                self.logger.debug("[API_MANAGER] Gerenciador de Memória no expe registrar_evento_na_historia.")
        except Exception:
            self.logger.debug("[API_MANAGER] Falha ao registrar evento na memória (silenciado).", exc_info=True)

    # ----------------------
    # Consulado wrappers (sync/async)
    # ----------------------
    async def _call_consulado_async(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        consulado = getattr(self.coracao, "consulado", None)
        if not consulado:
            return {"status": "falha", "motivo": "Consulado indisponível."}
        fn = getattr(consulado, "solicitar_missao", None)
        if not callable(fn):
            return {"status": "falha", "motivo": "Consulado no expe solicitar_missao."}
        try:
            resultado = fn(**payload)
            if asyncio.iscoroutine(resultado):
                # aguardamos de forma segura se inserido em loop
                if asyncio.get_event_loop().is_running():
                    resultado = await resultado
                else:
                    resultado = asyncio.run(resultado)
            return resultado
        except Exception as e:
            self.logger.exception("[API_MANAGER] Erro ao chamar Consulado (async): %s", e)
            return {"status": "falha", "motivo": str(e)}

    def _call_consulado(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        consulado = getattr(self.coracao, "consulado", None)
        if not consulado:
            return {"status": "falha", "motivo": "Consulado indisponível."}
        fn = getattr(consulado, "solicitar_missao", None)
        if not callable(fn):
            return {"status": "falha", "motivo": "Consulado no expe solicitar_missao."}
        try:
            resultado = fn(**payload)
            if asyncio.iscoroutine(resultado):
                try:
                    if asyncio.get_event_loop().is_running():
                        self.logger.error("[API_MANAGER] Consulado retornou coroutine, loop j em execução.")
                        return {"status": "falha", "motivo": "Consulado assncrono no suportado neste contexto."}
                    else:
                        resultado = asyncio.run(resultado)
                except Exception as e:
                    self.logger.exception("[API_MANAGER] Erro ao aguardar coroutine do Consulado: %s", e)
                    return {"status": "falha", "motivo": str(e)}
            return resultado
        except Exception as e:
            self.logger.exception("[API_MANAGER] Erro ao chamar Consulado: %s", e)
            return {"status": "falha", "motivo": str(e)}

    def _chamar_via_consulado(self,
                              url: str,
                              metodo: str = "GET",
                              headers: Optional[Dict[str, str]] = None,
                              params: Optional[Dict[str, Any]] = None,
                              timeout: int = 10,
                              nivel_acesso: str = "leitura",
                              descricao_extra: Optional[str] = None) -> Dict[str, Any]:
        if not hasattr(self.coracao, "consulado") or not self.coracao.consulado:
            self.logger.error("[API_MANAGER] Consulado Soberano no disponível.")
            return {"status": "falha", "motivo": "Consulado indisponível."}

        payload = {
            "acao": "requisicao_http",
            "descricao": descricao_extra or f"Requisio segura para {url}",
            "autor": "APIManager",
            "nivel_acesso": nivel_acesso,
            "url": url,
            "metodo": metodo,
            "headers": headers or {},
            "params": params or {},
            "timeout": timeout,
            "retornar_conteudo": True
        }
        return self._call_consulado(payload)

    # ----------------------
    # funções pblicas (async)
    # ----------------------
    async def obter_clima_atual(self, cidade: Optional[str] = None, pais: Optional[str] = None) -> Dict[str, Any]:
        cache_key = f"clima:{cidade or self.OPENWEATHERMAP_CIDADE}:{pais or self.OPENWEATHERMAP_PAIS}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        cidade_final = cidade or self.OPENWEATHERMAP_CIDADE or "So Paulo"
        pais_final = pais or self.OPENWEATHERMAP_PAIS or "BR"

        if not self._validar_acao_externa("OBTER_CLIMA", f"Obter clima para {cidade_final}, {pais_final}"):
            return {"sucesso": False, "mensagem": "Ao bloqueada por validador tico."}

        self.logger.info("[API_MANAGER] Solicitando clima para %s, %s", cidade_final, pais_final)

        # 1) OpenWeatherMap (lista de chaves)
        for chave in (self.OPENWEATHERMAP_API_KEYS or []):
            if not chave or "SUA_CHAVE" in str(chave).upper():
                continue
            res = await self._obter_clima_openweathermap_async(cidade_final, pais_final, chave)
            if res.get("sucesso"):
                self._registrar_na_memoria(f"Clima obtido via OpenWeatherMap para {cidade_final}")
                self._cache_set(cache_key, res)
                return res

        # 2) WeatherAPI.com
        if self.WEATHERAPI_COM_API_KEY and "SUA_CHAVE" not in str(self.WEATHERAPI_COM_API_KEY).upper():
            res = await self._obter_clima_weatherapi_com_async(cidade_final, pais_final, self.WEATHERAPI_COM_API_KEY)
            if res.get("sucesso"):
                self._registrar_na_memoria(f"Clima obtido via WeatherAPI.com para {cidade_final}")
                self._cache_set(cache_key, res)
                return res

        # 3) AccuWeather
        if self.ACCUWEATHER_API_KEY and "SUA_CHAVE" not in str(self.ACCUWEATHER_API_KEY).upper():
            res = await self._obter_clima_accuweather_completo_async(cidade_final, pais_final, self.ACCUWEATHER_API_KEY)
            if res.get("sucesso"):
                self._registrar_na_memoria(f"Clima obtido via AccuWeather para {cidade_final}")
                self._cache_set(cache_key, res)
                return res

        # 4) Tomorrow.io (usa coordenadas; tentamos geocoding via OpenWeatherMap se necessário)
        if self.TOMORROW_IO_API_KEY and "SUA_CHAVE" not in str(self.TOMORROW_IO_API_KEY).upper():
            res = await self._obter_clima_tomorrow_io_completo_async(cidade_final, pais_final, self.TOMORROW_IO_API_KEY)
            if res.get("sucesso"):
                self._registrar_na_memoria(f"Clima obtido via Tomorrow.io para {cidade_final}")
                self._cache_set(cache_key, res)
                return res

        self.logger.error("[API_MANAGER] Todos provedores de clima falharam para %s, %s", cidade_final, pais_final)
        return {"sucesso": False, "mensagem": "No foi possível obter clima de nenhum provedor."}

    async def _obter_clima_openweathermap_async(self, cidade: str, pais: str, api_key: str) -> Dict[str, Any]:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": f"{cidade},{pais}", "appid": api_key, "units": "metric", "lang": "pt_br"}
        payload = {
            "acao": "requisicao_http",
            "autor": "APIManager",
            "nivel_acesso": "leitura",
            "url": url,
            "metodo": "GET",
            "params": params,
            "timeout": 12,
            "retornar_conteudo": True
        }
        resultado = await self._call_consulado_async(payload)
        if resultado and resultado.get("status") == "executado":
            try:
                data = resultado.get("resultado", {}).get("dados", {}) or {}
                main = data.get("main", {})
                weather = (data.get("weather") or [{}])[0]
                temp = main.get("temp")
                desc = weather.get("description", "")
                if temp is None:
                    raise ValueError("campo 'temp' ausente")
                return {"sucesso": True,
                        "temperatura": f"{float(temp):.1f}C",
                        "sensacao_termica": f"{float(main.get('feels_like', temp)):.1f}C",
                        "descricao": str(desc).capitalize(),
                        "fonte": "OpenWeatherMap"}
            except Exception as e:
                self.logger.exception("[API_MANAGER] Erro processando OpenWeatherMap: %s", e)
                return {"sucesso": False, "mensagem": f"Erro ao processar resposta OpenWeatherMap: {e}"}
        return {"sucesso": False, "mensagem": f"Falha OpenWeatherMap: {resultado.get('motivo', 'Desconhecido') if resultado else 'sem resultado'}"}

    async def _obter_clima_weatherapi_com_async(self, cidade: str, pais: str, api_key: str) -> Dict[str, Any]:
        url = "https://api.weatherapi.com/v1/current.json"
        params = {"key": api_key, "q": f"{cidade},{pais}", "lang": "pt"}
        payload = {
            "acao": "requisicao_http",
            "autor": "APIManager",
            "nivel_acesso": "leitura",
            "url": url,
            "metodo": "GET",
            "params": params,
            "timeout": 12,
            "retornar_conteudo": True
        }
        resultado = await self._call_consulado_async(payload)
        if resultado and resultado.get("status") == "executado":
            try:
                data = resultado.get("resultado", {}).get("dados", {}) or {}
                current = data.get("current", {})
                temp = current.get("temp_c")
                condition = current.get("condition", {}).get("text", "")
                if temp is None:
                    raise ValueError("campo 'temp_c' ausente")
                return {"sucesso": True,
                        "temperatura": f"{temp}C",
                        "sensacao_termica": f"{current.get('feelslike_c', temp)}C",
                        "descricao": str(condition).capitalize(),
                        "fonte": "WeatherAPI.com"}
            except Exception as e:
                self.logger.exception("[API_MANAGER] Erro processando WeatherAPI: %s", e)
                return {"sucesso": False, "mensagem": f"Erro ao processar WeatherAPI: {e}"}
        return {"sucesso": False, "mensagem": f"Falha WeatherAPI: {resultado.get('motivo', 'Desconhecido') if resultado else 'sem resultado'}"}

    async def _obter_clima_accuweather_completo_async(self, cidade: str, pais: str, api_key: str) -> Dict[str, Any]:
        search_url = "https://dataservice.accuweather.com/locations/v1/cities/search"
        search_params = {"apikey": api_key, "q": f"{cidade},{pais}"}
        search_payload = {
            "acao": "requisicao_http",
            "autor": "APIManager",
            "nivel_acesso": "leitura",
            "url": search_url,
            "metodo": "GET",
            "params": search_params,
            "timeout": 12,
            "retornar_conteudo": True
        }
        res_search = await self._call_consulado_async(search_payload)
        if not res_search or res_search.get("status") != "executado":
            return {"sucesso": False, "mensagem": f"Falha ao buscar location key: {res_search.get('motivo', 'Desconhecido') if res_search else 'sem resultado'}"}
        try:
            locations = res_search.get("resultado", {}).get("dados", []) or []
            if not locations:
                return {"sucesso": False, "mensagem": "Cidade no encontrada no AccuWeather."}
            location_key = locations[0].get("Key")
            if not location_key:
                raise ValueError("Location Key ausente")
        except Exception as e:
            self.logger.exception("[API_MANAGER] Erro obtendo location key AccuWeather: %s", e)
            return {"sucesso": False, "mensagem": f"Erro obtendo location key: {e}"}

        weather_url = f"https://dataservice.accuweather.com/currentconditions/v1/{location_key}"
        weather_params = {"apikey": api_key, "language": "pt-br"}
        weather_payload = {
            "acao": "requisicao_http",
            "autor": "APIManager",
            "nivel_acesso": "leitura",
            "url": weather_url,
            "metodo": "GET",
            "params": weather_params,
            "timeout": 12,
            "retornar_conteudo": True
        }
        res_weather = await self._call_consulado_async(weather_payload)
        if res_weather and res_weather.get("status") == "executado":
            try:
                data = res_weather.get("resultado", {}).get("dados", []) or []
                if not data or not isinstance(data, list):
                    raise ValueError("Formato inesperado no response")
                item = data[0]
                temp = item.get("Temperature", {}).get("Metric", {}).get("Value")
                text = item.get("WeatherText")
                return {"sucesso": True, "temperatura": f"{temp}C", "descricao": text, "fonte": "AccuWeather"}
            except Exception as e:
                self.logger.exception("[API_MANAGER] Erro processando AccuWeather: %s", e)
                return {"sucesso": False, "mensagem": f"Erro ao processar AccuWeather: {e}"}
        return {"sucesso": False, "mensagem": f"Falha AccuWeather: {res_weather.get('motivo', 'Desconhecido') if res_weather else 'sem resultado'}"}

    async def _obter_clima_tomorrow_io_completo_async(self, cidade: str, pais: str, api_key: str) -> Dict[str, Any]:
        # coordenadas conhecidas como fallback inicial
        coordenadas = {
            "So Paulo": (-23.5505, -46.6333),
            "Rio de Janeiro": (-22.9068, -43.1729),
            "London": (51.5074, -0.1278),
            "Lisbon": (38.7223, -9.1393)
        }
        coords = coordenadas.get(cidade)
        # se no temos coords, tentamos geocoding via OpenWeatherMap (se chave disponível)
        if not coords:
            if self.OPENWEATHERMAP_API_KEYS:
                chave = self.OPENWEATHERMAP_API_KEYS[0]
                try:
                    geocode_url = "http://api.openweathermap.org/geo/1.0/direct"
                    params = {"q": f"{cidade},{pais}", "limit": 1, "appid": chave}
                    payload = {
                        "acao": "requisicao_http",
                        "autor": "APIManager",
                        "nivel_acesso": "leitura",
                        "url": geocode_url,
                        "metodo": "GET",
                        "params": params,
                        "timeout": 8,
                        "retornar_conteudo": True
                    }
                    res = await self._call_consulado_async(payload)
                    if res and res.get("status") == "executado":
                        data = res.get("resultado", {}).get("dados", [])
                        if data and isinstance(data, list) and data[0].get("lat") and data[0].get("lon"):
                            coords = (float(data[0]["lat"]), float(data[0]["lon"]))
                except Exception:
                    self.logger.debug("[API_MANAGER] Geocoding OpenWeatherMap falhou (fallback).", exc_info=True)
        if not coords:
            self.logger.warning("[API_MANAGER] Coordenadas no encontradas para %s", cidade)
            return {"sucesso": False, "mensagem": f"Coordenadas no encontradas para {cidade}"}

        url = "https://api.tomorrow.io/v4/weather/realtime"
        params = {"location": f"{coords[0]},{coords[1]}", "apikey": api_key, "units": "metric"}
        payload = {
            "acao": "requisicao_http",
            "autor": "APIManager",
            "nivel_acesso": "leitura",
            "url": url,
            "metodo": "GET",
            "params": params,
            "timeout": 12,
            "retornar_conteudo": True
        }
        res = await self._call_consulado_async(payload)
        if res and res.get("status") == "executado":
            try:
                data = res.get("resultado", {}).get("dados", {}) or {}
                temp = None
                humidity = None
                # estrutura esperada: data -> values
                if isinstance(data, dict):
                    temp = data.get("data", {}).get("values", {}).get("temperature")
                    humidity = data.get("data", {}).get("values", {}).get("humidity")
                if temp is None:
                    raise ValueError("campo 'temperature' ausente")
                return {"sucesso": True, "temperatura": f"{temp}C", "descricao": f"Umidade: {humidity}%", "fonte": "Tomorrow.io"}
            except Exception as e:
                self.logger.exception("[API_MANAGER] Erro processando Tomorrow.io: %s", e)
                return {"sucesso": False, "mensagem": f"Erro ao processar Tomorrow.io: {e}"}
        return {"sucesso": False, "mensagem": f"Falha Tomorrow.io: {res.get('motivo', 'Desconhecido') if res else 'sem resultado'}"}

    # ----------------------
    # Notcias (NewsAPI)
    # ----------------------
    async def obter_noticias_newsapi(self, query: str = "IA", language: str = "pt") -> Dict[str, Any]:
        cache_key = f"noticias:{query}:{language}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        if not self._validar_acao_externa("OBTER_NOTICIAS", f"Obter notcias sobre {query}"):
            return {"sucesso": False, "mensagem": "Ao bloqueada por validador tico."}

        if not self.NEWSAPI_API_KEY or "SUA_CHAVE" in str(self.NEWSAPI_API_KEY).upper():
            self.logger.warning("[API_MANAGER] NewsAPI key ausente.")
            return {"sucesso": False, "mensagem": "Chave da NewsAPI no configurada."}

        url = "https://newsapi.org/v2/everything"
        params = {"q": query, "language": language, "sortBy": "relevancy", "pageSize": 3, "apiKey": self.NEWSAPI_API_KEY}
        payload = {
            "acao": "requisicao_http",
            "autor": "APIManager",
            "nivel_acesso": "leitura",
            "url": url,
            "metodo": "GET",
            "params": params,
            "timeout": 15,
            "retornar_conteudo": True
        }
        res = await self._call_consulado_async(payload)
        if res and res.get("status") == "executado":
            try:
                data = res.get("resultado", {}).get("dados", {}) or {}
                articles = data.get("articles", [])
                noticias = []
                for a in articles[:3]:
                    noticias.append({
                        "titulo": a.get("title", "Sem ttulo"),
                        "descricao": a.get("description", ""),
                        "url": a.get("url", "#")
                    })
                self._registrar_na_memoria(f"Notcias obtidas: {query}")
                resultado = {"sucesso": True, "noticias": noticias, "fonte": "NewsAPI"}
                self._cache_set(cache_key, resultado)
                return resultado
            except Exception as e:
                self.logger.exception("[API_MANAGER] Erro processando NewsAPI: %s", e)
                return {"sucesso": False, "mensagem": f"Erro processando NewsAPI: {e}"}
        return {"sucesso": False, "mensagem": f"Falha NewsAPI: {res.get('motivo', 'Desconhecido') if res else 'sem resultado'}"}

    # ----------------------
    # GitHub search (usa api_consultor se disponível, seno Consulado)
    # ----------------------
    async def consultar_github(self, query: str, sort: str = "updated") -> Dict[str, Any]:
        cache_key = f"github:{query}:{sort}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        if not self._validar_acao_externa("CONSULTAR_GITHUB", f"Consultar repositrios sobre {query}"):
            return {"sucesso": False, "mensagem": "Bloqueado por validador tico."}

        api_consultor = getattr(self.coracao, "api_consultor", None)
        if api_consultor and hasattr(api_consultor, "consultar_github"):
            try:
                res = await api_consultor.consultar_github(query, sort)
                if res.get("sucesso"):
                    self._registrar_na_memoria(f"GitHub consultado: {query}")
                    self._cache_set(cache_key, res)
                    return res
            except Exception:
                self.logger.debug("api_consultor falhou; usando fallback via Consulado.")

        url = "https://api.github.com/search/repositories"
        params = {"q": query, "sort": sort, "order": "desc", "per_page": 5}
        headers = {"Authorization": f"token {self.GITHUB_TOKEN}"} if self.GITHUB_TOKEN else {}
        payload = {
            "acao": "requisicao_http",
            "autor": "APIManager",
            "nivel_acesso": "leitura",
            "url": url,
            "metodo": "GET",
            "params": params,
            "headers": headers,
            "timeout": 10,
            "retornar_conteudo": True
        }
        res = await self._call_consulado_async(payload)
        if res and res.get("status") == "executado":
            try:
                data = res.get("resultado", {}).get("dados", {}) or {}
                repos = []
                for repo in data.get("items", []):
                    repos.append({
                        "nome": repo.get("name", ""),
                        "descricao": repo.get("description", ""),
                        "url": repo.get("html_url", "")
                    })
                resultado = {"sucesso": True, "repositorios": repos, "fonte": "GitHub"}
                self._cache_set(cache_key, resultado)
                return resultado
            except Exception as e:
                self.logger.exception("[API_MANAGER] Erro processando GitHub: %s", e)
                return {"sucesso": False, "mensagem": f"Erro processando GitHub: {e}"}
        return {"sucesso": False, "mensagem": f"Falha GitHub: {res.get('motivo', 'Desconhecido') if res else 'sem resultado'}"}

    # ----------------------
    # Wikipedia
    # ----------------------
    async def consultar_wikipedia(self, query: str, language: str = "pt") -> Dict[str, Any]:
        cache_key = f"wikipedia:{query}:{language}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        if not self._validar_acao_externa("CONSULTAR_WIKIPEDIA", f"Consultar Wikipedia sobre {query}"):
            return {"sucesso": False, "mensagem": "Bloqueado por validador tico."}

        api_consultor = getattr(self.coracao, "api_consultor", None)
        if api_consultor and hasattr(api_consultor, "consultar_wikipedia"):
            try:
                res = await api_consultor.consultar_wikipedia(query, language)
                if res.get("sucesso"):
                    self._registrar_na_memoria(f"Wikipedia consultada: {query}")
                    self._cache_set(cache_key, res)
                    return res
            except Exception:
                self.logger.debug("api_consultor falhou; usando fallback via Consulado.")

        params = {"action": "query", "format": "json", "prop": "extracts", "exintro": True, "explaintext": True, "titles": query}
        url = f"https://{language}.wikipedia.org/w/api.php"
        payload = {
            "acao": "requisicao_http",
            "autor": "APIManager",
            "nivel_acesso": "leitura",
            "url": url,
            "metodo": "GET",
            "params": params,
            "timeout": 10,
            "retornar_conteudo": True
        }
        res = await self._call_consulado_async(payload)
        if res and res.get("status") == "executado":
            try:
                data = res.get("resultado", {}).get("dados", {}) or {}
                pages = data.get("query", {}).get("pages", {})
                resultados = []
                for page_id, page in pages.items():
                    if page_id != "-1":
                        resultados.append({
                            "titulo": page.get("title", ""),
                            "extrato": page.get("extract", "")[:300]
                        })
                resultado = {"sucesso": True, "resultados": resultados, "fonte": "Wikipedia"}
                self._cache_set(cache_key, resultado)
                return resultado
            except Exception as e:
                self.logger.exception("[API_MANAGER] Erro processando Wikipedia: %s", e)
                return {"sucesso": False, "mensagem": f"Erro processando Wikipedia: {e}"}
        return {"sucesso": False, "mensagem": f"Falha Wikipedia: {res.get('motivo', 'Desconhecido') if res else 'sem resultado'}"}

    # ----------------------
    # Reqres (exemplo)
    # ----------------------
    async def consultar_reqres_api(self, endpoint: str = "users", item_id: Optional[int] = None) -> Dict[str, Any]:
        cache_key = f"reqres:{endpoint}:{item_id}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        if not self._validar_acao_externa("CONSULTAR_REQRES", f"Consultar Reqres endpoint {endpoint}"):
            return {"sucesso": False, "mensagem": "Bloqueado por validador tico."}

        url = f"https://reqres.in/api/{endpoint}" + (f"/{item_id}" if item_id else "")
        payload = {
            "acao": "requisicao_http",
            "autor": "APIManager",
            "nivel_acesso": "leitura",
            "url": url,
            "metodo": "GET",
            "timeout": 10,
            "retornar_conteudo": True
        }
        res = await self._call_consulado_async(payload)
        if res and res.get("status") == "executado":
            try:
                dados = res.get("resultado", {}).get("dados", {})
                self._registrar_na_memoria(f"Consulta Reqres: {endpoint}")
                resultado = {"sucesso": True, "dados": dados, "fonte": "Reqres.in"}
                self._cache_set(cache_key, resultado)
                return resultado
            except Exception as e:
                self.logger.exception("[API_MANAGER] Erro processando Reqres: %s", e)
                return {"sucesso": False, "mensagem": f"Erro processando Reqres: {e}"}
        return {"sucesso": False, "mensagem": f"Falha Reqres: {res.get('motivo', 'Desconhecido') if res else 'sem resultado'}"}

    # ----------------------
    # Shutdown / housekeeping
    # ----------------------
    def desligar(self) -> None:
        self.logger.info("APIManager desligado (cache limpo).")
        self.cache.clear()
