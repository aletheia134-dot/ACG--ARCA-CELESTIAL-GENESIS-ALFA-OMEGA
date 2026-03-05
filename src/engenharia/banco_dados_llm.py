#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLMService - Endurecido

Gerencia carregamento e interação com LLMs locais (via llama_cpp) e um serviço RAG.Projetado para degradar graciosamente quando dependências não estão presentes
(e.g., em ambientes de desenvolvimento/test) e para aplicar timeouts nas chamadas
de inferência.Principais endurecimentos:
 - Imports defensivos (llama_cpp opcional)
 - Injeção de dependência para RAGService (ou tentativa de import fallback)
 - Verificações de existência de arquivos de modelo
 - Execução de inferência com ThreadPoolExecutor + timeout configurável
 - Logging em vez de prints
 - Estado consultável (is_phi3_loaded, is_vikhr_loaded)
 - Métodos de shutdown para liberar recursos do executor
 - Parâmetros configuráveis via construtor
"""
from __future__ import annotations


import concurrent.futures
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Attempt to import llama_cpp lazily/defensively
try:
    from llama_cpp import Llama  # type: ignore
    _LLAMA_AVAILABLE = True
except:
    logging.getLogger(__name__).warning("âš ï¸ Llama não disponível")
    Llama = None  # type: ignore
    _LLAMA_AVAILABLE = False
    logger.warning("llama_cpp não disponível; LLMService entrará em modo degradado (modelos locais desativados).")

# RAGService: allow injection, otherwise try a safe import
try:
    from memoria.rag_service import RAGService  # type: ignore
    _RAG_AVAILABLE = True
except:
    logging.getLogger(__name__).warning("âš ï¸ Llama não disponível")
    Llama = None  # type: ignore
    _RAG_AVAILABLE = False
    logger.info("RAGService não encontrado via import; aceitar injeção via construtor se necessário.")


class LLMService:
    """
    Serviço de LLM + RAG endurecido.Args:
        model_dir: diretório base onde ficam os modelos.phi3_model_path / vikhr_model_path: caminhos relativos ou absolutos para os modelos GGUF.rag_service: instância existente de RAGService (opcional). Se não fornecido, tentamos importar.n_gpu_layers: número de camadas na GPU (pass-through para llama_cpp).
        inference_timeout: tempo máximo (segundos) para cada chamada de inferência.executor_workers: número de workers para executar inferências em threads.
    """

    def __init__(
        self,
        model_dir: Optional[str] = None,
        phi3_model_path: Optional[str] = None,
        vikhr_model_path: Optional[str] = None,
        rag_service: Optional[Any] = None,
        n_gpu_layers: int = -1,
        inference_timeout: float = 30.0,
        executor_workers: int = 2,
    ):
        self.model_dir = Path(model_dir) if model_dir else Path("infraestrutura/LLM_Models")
        self.phi3_path = Path(phi3_model_path) if phi3_model_path else (self.model_dir / "PHI3.gguf")
        self.vikhr_path = Path(vikhr_model_path) if vikhr_model_path else (self.model_dir / "VIKHR.gguf")

        self.n_gpu_layers = int(n_gpu_layers)
        self.inference_timeout = float(inference_timeout)

        # Instances (may be None if unavailable)
        self.llm_phi3: Optional[Any] = None
        self.llm_vikhr: Optional[Any] = None

        # RAG service (injetável)
        if rag_service:
            self.rag_service = rag_service
        else:
            self.rag_service = RAGService() if _RAG_AVAILABLE and RAGService is not None else None

        # executor para executar inferência com timeout
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=int(executor_workers))
        self._shutdown = False

        # chat history simple
        self.chat_history = []

        logger.info("LLMService inicializado (LLama disponível=%s, RAG disponível=%s)", _LLAMA_AVAILABLE, self.rag_service is not None)

    # -------------------------
    # Model loading
    # -------------------------
    def _model_file_ok(self, p: Path) -> bool:
        try:
            return p.exists() and p.is_file()
        except Exception:
            return False

    def _load_model_instance(self, model_path: Path) -> Optional[Any]:
        """Tenta instanciar um Llama (defensivo)."""
        if not _LLAMA_AVAILABLE or Llama is None:
            logger.debug("llama_cpp não disponível; não é possível carregar: %s", model_path)
            return None
        if not self._model_file_ok(model_path):
            logger.warning("Arquivo de modelo não encontrado: %s", model_path)
            return None
        try:
            llm = Llama(
                model_path=str(model_path),
                n_gpu_layers=self.n_gpu_layers,
                n_ctx=4096,
                verbose=False,
            )
            logger.info("Modelo carregado: %s", model_path)
            return llm
        except Exception as e:
            logger.exception("Falha ao carregar modelo %s: %s", model_path, e)
            return None

    def initialize(self, load_phi3: bool = True, load_vikhr: bool = True) -> None:
        """
        Carrega modelos solicitados e inicializa RAG se necessário.Esta função é segura para chamadas repetidas (fará reload se já houver instâncias).
        """
        if self._shutdown:
            logger.warning("LLMService foi shutdown; initialize() ignorado.")
            return

        logger.info("LLMService: inicializando modelos (phi3=%s, vikhr=%s)", load_phi3, load_vikhr)

        if load_phi3:
            self.llm_phi3 = self._load_model_instance(self.phi3_path) or self.llm_phi3

        if load_vikhr:
            self.llm_vikhr = self._load_model_instance(self.vikhr_path) or self.llm_vikhr

        # Ensure RAG service initialized if possible
        if self.rag_service is None and _RAG_AVAILABLE and RAGService is not None:
            try:
                self.rag_service = RAGService()
                if hasattr(self.rag_service, "initialize"):
                    try:
                        self.rag_service.initialize()
                    except Exception:
                        logger.debug("RAGService.initialize() falhou (ignorando).")
                logger.info("RAGService inicializado via import fallback.")
            except Exception:
                logger.exception("Falha ao instanciar RAGService via fallback import.")

    # -------------------------
    # Inference helpers
    # -------------------------
    def _invoke_llm_sync(self, llm_instance: Any, messages: list, max_tokens: int, temperature: float):
        """
        Invoca a API do LLM de forma defensiva.Retorna string de conteúdo ou eleva Exception.Suporta create_chat_completion e create_completion (fallback).
        """
        if llm_instance is None:
            raise RuntimeError("LLM instance is None")

        # Try chat API first
        try:
            if hasattr(llm_instance, "create_chat_completion"):
                resp = llm_instance.create_chat_completion(messages=messages, max_tokens=max_tokens, temperature=temperature, stream=False)
                # Response may be dict-like or an object; handle both
                if isinstance(resp, dict):
                    choices = resp.get("choices") or []
                    if choices:
                        # support nested structures
                        first = choices[0]
                        # try various keys
                        if isinstance(first, dict):
                            msg = first.get("message") or first.get("text") or first.get("content")
                            if isinstance(msg, dict):
                                return msg.get("content", "") or ""
                            return msg or ""
                        return str(first)
                # fallback to trying repr
                return str(resp)
            elif hasattr(llm_instance, "create_completion"):
                # older API
                resp = llm_instance.create_completion(prompt=messages[-1]["content"], max_tokens=max_tokens, temperature=temperature)
                if isinstance(resp, dict):
                    return resp.get("choices", [{}])[0].get("text", "")
                return str(resp)
            else:
                # last resort: try calling as function if supported
                try:
                    resp = llm_instance(messages=messages, max_tokens=max_tokens, temperature=temperature)
                    return str(resp)
                except Exception as e:
                    raise RuntimeError(f"LLM instance does not expose known completion APIs: {e}")
        except Exception:
            logger.exception("Erro na chamada síncrona do LLM.")
            raise

    def _run_inference_with_timeout(self, llm_instance: Any, messages: list, max_tokens: int, temperature: float, timeout: Optional[float] = None) -> str:
        """
        Executa a inferência em thread separada com timeout.Se a chamada exceder o timeout, retorna mensagem de erro e cancela (não mata thread).
        """
        if timeout is None:
            timeout = self.inference_timeout

        future = self._executor.submit(self._invoke_llm_sync, llm_instance, messages, max_tokens, temperature)
        try:
            result = future.result(timeout=float(timeout))
            return result if result is not None else ""
        except concurrent.futures.TimeoutError:
            logger.error("Inferência ultrapassou timeout de %.1f segundos.", timeout)
            return f"Erro: inferência excedeu o timeout de {timeout} segundos."
        except Exception as e:
            logger.exception("Erro durante inferência: %s", e)
            return f"Erro na inferência: {e}"

    # -------------------------
    # High-level utilities
    # -------------------------
    def _build_messages(self, system_prompt: str, user_prompt: str):
        """Constroi lista de mensagens em formato compatível com chat APIs."""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    def _safe_query_rag(self, user_input: str) -> str:
        """Query na RAG; devolve string vazia se RAG ausente ou falhar."""
        if not self.rag_service:
            logger.debug("RAGService não configurado; retornando contexto vazio.")
            return ""
        try:
            # prefer a API 'query' or 'retrieve' if available
            if hasattr(self.rag_service, "query"):
                return str(self.rag_service.query(user_input) or "")
            if hasattr(self.rag_service, "retrieve"):
                return str(self.rag_service.retrieve(user_input) or "")
            logger.debug("RAGService presente mas sem método query/retrieve conhecido.")
        except Exception:
            logger.exception("Erro ao consultar RAGService (ignorando).")
        return ""

    # -------------------------
    # Public API
    # -------------------------
    def is_phi3_loaded(self) -> bool:
        return self.llm_phi3 is not None

    def is_vikhr_loaded(self) -> bool:
        return self.llm_vikhr is not None

    def _generate_response(self, llm_instance: Any, prompt: str, *, mode: str = "phi3", max_tokens: int = 1024) -> str:
        """
        Gera resposta usando um LLM carregado, aplicando timeout e controle.mode: 'phi3' or 'vikhr' (controls system prompt and temperature)
        """
        if llm_instance is None:
            return f"Erro: modelo {mode.upper()} indisponível."

        system_prompt = PHI3_SYSTEM_PROMPT if mode == "phi3" else VIKHR_SYSTEM_PROMPT
        temperature = 0.2 if mode == "phi3" else 0.7

        messages = self._build_messages(system_prompt, prompt)

        return self._run_inference_with_timeout(llm_instance, messages, max_tokens, temperature, timeout=self.inference_timeout)

    def process_request(self, user_input: str, mode: str = "phi3") -> Dict[str, str]:
        """
        Processa uma requisição do usuário.mode in {'phi3','vikhr','collective'}
        Retorna dict com chaves de modelos e seus textos.
        """
        if self._shutdown:
            return {"error": "LLMService está desligado."}

        results: Dict[str, str] = {}
        try:
            if mode == "phi3":
                context = self._safe_query_rag(user_input)
                augmented = f"CONTEXTO FORNECIDO:\n{context}\n\nPERGUNTA DO USUÍRIO:\n{user_input}"
                results["PHI-3"] = self._generate_response(self.llm_phi3, augmented, mode="phi3")

            elif mode == "vikhr":
                results["VIKHR"] = self._generate_response(self.llm_vikhr, user_input, mode="vikhr")

            elif mode == "collective":
                context = self._safe_query_rag(user_input)
                augmented = f"CONTEXTO FORNECIDO:\n{context}\n\nPERGUNTA DO USUÍRIO:\n{user_input}"
                results["PHI-3"] = self._generate_response(self.llm_phi3, augmented, mode="phi3", max_tokens=512)
                if self.llm_vikhr:
                    results["VIKHR"] = self._generate_response(self.llm_vikhr, user_input, mode="vikhr", max_tokens=512)
                else:
                    results["VIKHR"] = "Modelo criativo (VIKHR) indisponível."
            else:
                return {"error": f"Modo desconhecido: {mode}"}

            # Append simple history (bounded)
            try:
                self.chat_history.append({"user": user_input, "result": results})
                if len(self.chat_history) > 200:
                    self.chat_history.pop(0)
            except Exception:
                logger.debug("Falha ao atualizar chat_history (ignorando).")

            return results
        except Exception as e:
            logger.exception("Erro ao processar request: %s", e)
            return {"error": f"Erro interno: {e}"}

    def shutdown(self, wait: bool = True, timeout: float = 5.0) -> None:
        """Encerramento limpo do serviço (executor)."""
        self._shutdown = True
        try:
            self._executor.shutdown(wait=wait, timeout=timeout)
            logger.info("LLMService executor finalizado.")
        except Exception:
            logger.exception("Erro ao encerrar executor do LLMService.")


