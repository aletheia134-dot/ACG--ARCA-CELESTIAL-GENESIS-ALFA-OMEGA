from __future__ import annotations
# src/aliadas/aliada_gemini.py
import os
import time
import logging
import random
from typing import Optional, Tuple, Any, Dict

import requests
from requests import Session, RequestException, Timeout

from src.diagnostico.erros import LLMUnavailableError, LLMExecutionError, LLMTimeoutError

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRIES = 2
DEFAULT_BACKOFF = 0.5
MAX_BACKOFF = 10.0


class AliadaGemini:
    """
    Cliente robusto para o servio Gemini.

    - Usa requests.Session para pooling de conexões.
    - Retry exponencial com jitter para timeouts/erros transitrios.
    - Extrao de campos comuns de resposta (output, result, text, generated_text, choices, data).
    - Métodos pblicos:
      - processar(comando, contexto) -> (ok: bool, texto_or_none: Optional[str], status: str)
      - health_check() -> bool
      - shutdown()
    """

    def __init__(self, cfg: Optional[Dict[str, Any]] = None):
        self.cfg = cfg or {}
        self.endpoint = self.cfg.get("endpoint") or os.environ.get("GEMINI_API_URL")
        self.api_key = self.cfg.get("api_key") or os.environ.get("GEMINI_API_KEY")
        try:
            self.timeout = float(self.cfg.get("timeout_sec", os.environ.get("GEMINI_TIMEOUT_SEC", DEFAULT_TIMEOUT)))
        except Exception:
            self.timeout = DEFAULT_TIMEOUT
        try:
            self.retries = int(self.cfg.get("retries", self.cfg.get("retry", DEFAULT_RETRIES)))
        except Exception:
            self.retries = DEFAULT_RETRIES

        if not self.endpoint:
            raise LLMUnavailableError(
                "AliadaGemini: endpoint no configurado (cfg['endpoint'] or GEMINI_API_URL)"
            )

        self.session: Session = requests.Session()
        self._closed = False
        logger.info("AliadaGemini initialized endpoint=%s retries=%s timeout=%s", self.endpoint, self.retries, self.timeout)

    def _build_headers(self) -> Dict[str, str]:
        # Gemini NÃO usa Authorization header — a chave vai como parâmetro de URL
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _build_url(self) -> str:
        """Monta URL real da Gemini com a API key como parâmetro."""
        base = self.endpoint or "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
        if self.api_key:
            sep = "&" if "?" in base else "?"
            return f"{base}{sep}key={self.api_key}"
        return base

    def _build_payload(self, comando: str, contexto: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Payload real da API Gemini (Google).
        Doc: https://ai.google.dev/api/generate-content
        """
        contents = []
        if contexto and isinstance(contexto, dict):
            historico = contexto.get("historico") or contexto.get("history", [])
            for turno in historico:
                if isinstance(turno, dict) and "role" in turno and "content" in turno:
                    contents.append({
                        "role": turno["role"],
                        "parts": [{"text": str(turno["content"])}]
                    })
        contents.append({
            "role": "user",
            "parts": [{"text": comando}]
        })

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": int(self.cfg.get("max_tokens", 1024)),
                "temperature": float(self.cfg.get("temperature", 0.7)),
            }
        }

        system_prompt = None
        if contexto and isinstance(contexto, dict):
            system_prompt = contexto.get("system_prompt") or contexto.get("system")
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": str(system_prompt)}]
            }

        return payload

    def _extract_text(self, data: Any) -> Optional[str]:
        """
        Extrai texto da resposta real da Gemini.
        Estrutura: data.candidates[0].content.parts[0].text
        """
        if data is None:
            return None
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            # Estrutura real Gemini
            candidates = data.get("candidates")
            if isinstance(candidates, list) and candidates:
                candidate = candidates[0]
                if isinstance(candidate, dict):
                    content = candidate.get("content", {})
                    parts = content.get("parts", [])
                    if isinstance(parts, list) and parts:
                        text = parts[0].get("text")
                        if isinstance(text, str) and text.strip():
                            return text.strip()
            # Fallback: error message da Gemini
            error = data.get("error", {})
            if isinstance(error, dict) and error.get("message"):
                logger.warning("Gemini retornou erro: %s", error["message"])
                return None
            # raw_text (resposta não-JSON)
            raw = data.get("raw_text")
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
        try:
            return str(data)
        except Exception:
            return None

    def _call_api(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Faz POST para o endpoint com retries/backoff.
        Lana LLMTimeoutError ou LLMExecutionError nas condies finais de falha.
        """
        headers = self._build_headers()
        attempt = 0
        backoff = DEFAULT_BACKOFF
        last_exc: Optional[Exception] = None

        while attempt <= self.retries:
            attempt += 1
            try:
                resp = self.session.post(self.endpoint, json=payload, headers=headers, timeout=self.timeout)
                resp.raise_for_status()
                try:
                    return resp.json()
                except ValueError:
                    return {"raw_text": resp.text}
            except Timeout as e:
                last_exc = e
                logger.warning("AliadaGemini timeout (attempt %d/%d): %s", attempt, self.retries + 1, e)
                if attempt > self.retries:
                    raise LLMTimeoutError("Gemini timeout") from e
            except RequestException as e:
                last_exc = e
                status = getattr(e.response, "status_code", None) if hasattr(e, "response") else None
                logger.warning("AliadaGemini request error (attempt %d/%d) status=%s: %s", attempt, self.retries + 1, status, e)
                if attempt > self.retries:
                    raise LLMExecutionError(f"Gemini request failed: {e}") from e
            # backoff com jitter
            sleep_for = min(MAX_BACKOFF, backoff) * (0.8 + random.random() * 0.4)
            time.sleep(sleep_for)
            backoff *= 2

        if last_exc:
            raise LLMExecutionError("Gemini request failed (exceeded retries)") from last_exc
        raise LLMExecutionError("Gemini request failed (unknown reason)")

    def processar(self, comando: str, contexto: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str], str]:
        """
        Interface principal.
        Retorna (ok, texto|None, status) onde status  "ok" ou "timeout" / "unavailable" / "error".
        """
        if self._closed:
            logger.error("AliadaGemini chamada aps shutdown")
            return False, None, "error:shutdown"

        payload: Dict[str, Any] = {"input": comando}
        if contexto:
            payload["context"] = contexto

        try:
            data = self._call_api(payload)
            texto = self._extract_text(data)
            if texto is not None:
                return True, texto, "ok"
            return True, str(data), "ok"
        except LLMTimeoutError as e:
            logger.warning("Gemini timeout: %s", e)
            return False, None, "timeout"
        except LLMUnavailableError as e:
            logger.error("Gemini unavailable: %s", e)
            return False, None, "unavailable"
        except LLMExecutionError as e:
            logger.exception("Gemini execution error: %s", e)
            return False, None, "error"
        except Exception as e:
            logger.exception("Gemini unexpected error: %s", e)
            return False, None, "error"

    def __call__(self, comando: str, contexto: Optional[Dict[str, Any]] = None):
        return self.processar(comando, contexto)

    def health_check(self) -> bool:
        """Verifica se o endpoint responde (HEAD ou GET)."""
        if self._closed:
            return False
        try:
            h = self._build_headers()
            resp = self.session.head(self.endpoint, headers=h, timeout=min(5.0, self.timeout))
            if resp.ok:
                return True
            resp = self.session.get(self.endpoint, headers=h, timeout=min(5.0, self.timeout))
            return resp.ok
        except Exception:
            return False

    def shutdown(self) -> None:
        try:
            self._closed = True
            try:
                self.session.close()
            except Exception:
                pass
            logger.info("AliadaGemini.shutdown() called")
        except Exception:
            pass
