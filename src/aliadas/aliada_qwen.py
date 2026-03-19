from __future__ import annotations
# src/aliadas/aliada_qwen.py
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


class AliadaQwen:
    """
    Cliente robusto para o servio Qwen.

    - Usa requests.Session para pooling de conexões.
    - Retry exponencial com jitter para timeouts/erros transitrios.
    - Extrao de campos comuns de resposta (output, response, text, result, choices, data).
    - Public API:
      - processar(comando, contexto) -> (ok: bool, texto_or_none: Optional[str], status: str)
      - health_check() -> bool
      - shutdown()
    """

    def __init__(self, cfg: Optional[Dict[str, Any]] = None):
        self.cfg = cfg or {}
        self.endpoint = self.cfg.get("endpoint") or os.environ.get("QWEN_API_URL")
        self.api_key = self.cfg.get("api_key") or os.environ.get("QWEN_API_KEY")
        try:
            self.timeout = float(self.cfg.get("timeout_sec", os.environ.get("QWEN_TIMEOUT_SEC", DEFAULT_TIMEOUT)))
        except Exception:
            self.timeout = DEFAULT_TIMEOUT
        try:
            self.retries = int(self.cfg.get("retries", self.cfg.get("retry", DEFAULT_RETRIES)))
        except Exception:
            self.retries = DEFAULT_RETRIES

        if not self.endpoint:
            raise LLMUnavailableError(
                "AliadaQwen: endpoint no configurado (cfg['endpoint'] or QWEN_API_URL)"
            )

        self.session: Session = requests.Session()
        self._closed = False
        logger.info("AliadaQwen initialized endpoint=%s retries=%s timeout=%s", self.endpoint, self.retries, self.timeout)

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            # DashScope exige SSE desabilitado para respostas síncronas
            "X-DashScope-SSE": "disable",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _build_payload(self, comando: str, contexto: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Payload real da API Qwen (Alibaba DashScope).
        Doc: https://help.aliyun.com/zh/dashscope/developer-reference/api-details
        """
        messages = []
        if contexto and isinstance(contexto, dict):
            system_prompt = contexto.get("system_prompt") or contexto.get("system")
            if system_prompt:
                messages.append({"role": "system", "content": str(system_prompt)})
        messages.append({"role": "user", "content": comando})

        return {
            "model": self.cfg.get("model", "qwen-turbo"),
            "input": {
                "messages": messages
            },
            "parameters": {
                "max_tokens": int(self.cfg.get("max_tokens", 1024)),
                "temperature": float(self.cfg.get("temperature", 0.7)),
                "result_format": "message",
            }
        }

    def _extract_text(self, data: Any) -> Optional[str]:
        """
        Extrai texto da resposta real da DashScope.
        Estrutura: data.output.choices[0].message.content  OU  data.output.text
        """
        if data is None:
            return None
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            # Estrutura DashScope com result_format=message
            output = data.get("output", {})
            if isinstance(output, dict):
                choices = output.get("choices")
                if isinstance(choices, list) and choices:
                    msg = choices[0].get("message", {})
                    content = msg.get("content")
                    if isinstance(content, str) and content.strip():
                        return content.strip()
                # Estrutura DashScope legada (result_format=text)
                text = output.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()
            # Fallback genérico: choices estilo OpenAI
            choices = data.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0]
                if isinstance(first, dict):
                    msg = first.get("message", {})
                    content = msg.get("content") or first.get("text")
                    if isinstance(content, str) and content.strip():
                        return content.strip()
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
                logger.warning("AliadaQwen timeout (attempt %d/%d): %s", attempt, self.retries + 1, e)
                if attempt > self.retries:
                    raise LLMTimeoutError("Qwen timeout") from e
            except RequestException as e:
                last_exc = e
                status = getattr(e.response, "status_code", None) if hasattr(e, "response") else None
                logger.warning("AliadaQwen request error (attempt %d/%d) status=%s: %s", attempt, self.retries + 1, status, e)
                if attempt > self.retries:
                    raise LLMExecutionError(f"Qwen request failed: {e}") from e
            # backoff com jitter
            sleep_for = min(MAX_BACKOFF, backoff) * (0.8 + random.random() * 0.4)
            time.sleep(sleep_for)
            backoff *= 2

        if last_exc:
            raise LLMExecutionError("Qwen request failed (exceeded retries)") from last_exc
        raise LLMExecutionError("Qwen request failed (unknown reason)")

    def processar(self, comando: str, contexto: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str], str]:
        """
        Interface principal.
        Retorna (ok, texto|None, status) onde status é "ok" ou "timeout" / "unavailable" / "error".
        """
        if self._closed:
            logger.error("AliadaQwen chamada após shutdown")
            return False, None, "error:shutdown"

        payload = self._build_payload(comando, contexto)

        try:
            data = self._call_api(payload)
            texto = self._extract_text(data)
            if texto is not None:
                return True, texto, "ok"
            return True, str(data), "ok"
        except LLMTimeoutError as e:
            logger.warning("Qwen timeout: %s", e)
            return False, None, "timeout"
        except LLMUnavailableError as e:
            logger.error("Qwen unavailable: %s", e)
            return False, None, "unavailable"
        except LLMExecutionError as e:
            logger.exception("Qwen execution error: %s", e)
            return False, None, "error"
        except Exception as e:
            logger.exception("Qwen unexpected error: %s", e)
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
            logger.info("AliadaQwen.shutdown() called")
        except Exception:
            pass
