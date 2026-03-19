from __future__ import annotations
import os
import time
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
import threading
import requests

# tente ler .env sem sobrescrever o ambiente
try:
    from dotenv import load_dotenv, dotenv_values
    load_dotenv()
    _DOTENV_VALUES = dotenv_values('.env') or {}
except Exception:
    _DOTENV_VALUES = {}

from src.diagnostico.erros import ErroConfiguracao, ErroTempoEsgotado, ErroExecucaoServico

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def _get_from_env_or_dotenv(key: str) -> Optional[str]:
    return os.environ.get(key) or _DOTENV_VALUES.get(key)


def _collect_keys_for(names: List[str]) -> List[str]:
    """
    Coleta chaves/ tokens a partir de vrias possíveis variveis de ambiente
    Example usage:
      _collect_keys_for(["OPENAI_API_KEY","OPENAI_API_KEYS","OPENAI"])
    Retorna lista sem vazios e sem duplicatas (preserva ordem).
    """
    vals: List[str] = []
    # 1) explicit comma-separated variants
    for n in names:
        v = os.environ.get(n) or _DOTENV_VALUES.get(n)
        if v and ',' in v:
            for part in str(v).split(','):
                p = part.strip()
                if p:
                    vals.append(p)
    # 2) singular and enumerated forms
    for n in names:
        v = os.environ.get(n) or _DOTENV_VALUES.get(n)
        if v and ',' not in str(v):
            vals.append(v.strip())
    # enumerated suffix _1, _2 ...
    base = names[0]  # use first name as base for enumerated pattern
    i = 1
    while True:
        name_try = f"{base}_{i}"
        v = os.environ.get(name_try) or _DOTENV_VALUES.get(name_try)
        if not v:
            break
        vals.append(v.strip())
        i += 1
    # also accept suffix KEY_1 style
    i = 1
    while True:
        name_try = f"{base}_KEY_{i}"
        v = os.environ.get(name_try) or _DOTENV_VALUES.get(name_try)
        if not v:
            break
        vals.append(v.strip())
        i += 1
    # dedupe preserving order
    seen = set()
    out = []
    for v in vals:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


class KeyRotationState:
    def __init__(self, keys: Optional[List[str]] = None):
        self.keys = keys[:] if keys else []
        self.lock = threading.Lock()
        self.index = 0
        self.disabled_until: Dict[str, float] = {}

    def next_key(self, now: Optional[float] = None) -> Optional[str]:
        now = now if now is not None else time.time()
        with self.lock:
            n = len(self.keys)
            if n == 0:
                return None
            for _ in range(n):
                k = self.keys[self.index % n]
                self.index = (self.index + 1) % n
                du = self.disabled_until.get(k)
                if not du or du <= now:
                    return k
            return None

    def disable_key(self, key: str, cooldown_seconds: int = 60):
        with self.lock:
            self.disabled_until[key] = time.time() + cooldown_seconds

    def has_any_key_available(self) -> bool:
        now = time.time()
        with self.lock:
            for k in self.keys:
                if not self.disabled_until.get(k) or self.disabled_until[k] <= now:
                    return True
            return False


class LLMClient:
    def __init__(self, cfg: Optional[Dict[str, Any]] = None):
        self.cfg = cfg or {}
        self.timeout = float(self.cfg.get("timeout", _get_from_env_or_dotenv("LLM_TIMEOUT") or os.environ.get("LLM_TIMEOUT") or 30))
        self.retries = int(self.cfg.get("retries", _get_from_env_or_dotenv("LLM_RETRIES") or os.environ.get("LLM_RETRIES") or 2))

        # collect keys/tokens
        openai_keys = _collect_keys_for(["OPENAI_API_KEYS", "OPENAI_API_KEY", "OPENAI"])
        hf_tokens = _collect_keys_for(["HF_TOKENS", "HF_TOKEN", "HF"])
        # generic endpoints keys
        gemini_keys = _collect_keys_for(["GEMINI_API_KEYS", "GEMINI_API_KEY", "GEMINI"])
        deepseek_keys = _collect_keys_for(["DEEPSEEK_API_KEYS", "DEEPSEEK_API_KEY", "DEEPSEEK"])
        qwen_keys = _collect_keys_for(["QWEN_API_KEYS", "QWEN_API_KEY", "QWEN"])
        http_keys = _collect_keys_for(["HTTP_LLM_API_KEYS", "HTTP_LLM_API_KEY", "HTTP_LLM_API"])

        self.openai_keys = KeyRotationState(openai_keys)
        self.hf_tokens = KeyRotationState(hf_tokens)

        def _env(n): return os.environ.get(n) or _DOTENV_VALUES.get(n)

        self.endpoints: Dict[str, Tuple[Optional[str], KeyRotationState]] = {
            "gemini": (_env("GEMINI_API_URL"), KeyRotationState(gemini_keys)),
            "deepseek": (_env("DEEPSEEK_API_URL"), KeyRotationState(deepseek_keys)),
            "qwen": (_env("QWEN_API_URL"), KeyRotationState(qwen_keys)),
            "qwen_cloud": (_env("QWEN_CLOUD_API_URL"), KeyRotationState(qwen_keys)),
            "http": (_env("HTTP_LLM_API_URL"), KeyRotationState(http_keys)),
        }

        self.openai_model = self.cfg.get("openai_model") or _env("OPENAI_MODEL") or "gpt-3.5-turbo"
        self.hf_model = self.cfg.get("hf_model") or _env("HF_MODEL") or "gpt2"

        # Support a local model path/name for on-device inference (uses transformers + bitsandbytes)
        # Configure via cfg["local_model"] or env LOCAL_MODEL / HF_LOCAL_MODEL
        self.local_model = self.cfg.get("local_model") or _env("LOCAL_MODEL") or _env("HF_LOCAL_MODEL") or None
        self._local_model_obj: Optional[Tuple[Any, Any]] = None  # (model, tokenizer) lazy loaded
        self._local_model_lock = threading.Lock()

        # concurrency control for local model inference (to protect GPU VRAM and control parallel generate calls)
        try:
            conc_cfg = int(self.cfg.get("llm_call_concurrency", _get_from_env_or_dotenv("LLM_CALL_CONCURRENCY") or os.environ.get("LLM_CALL_CONCURRENCY") or 2))
        except Exception:
            conc_cfg = 2
        self._max_llm_concurrency = max(1, conc_cfg)
        self._generate_semaphore = threading.BoundedSemaphore(self._max_llm_concurrency)

        prov = (self.cfg.get("provider") or _env("LLM_PROVIDER") or os.environ.get("LLM_PROVIDER") or "").lower()
        if not prov:
            if self.openai_keys.keys:
                prov = "openai"
            elif self.hf_tokens.keys:
                prov = "huggingface"
            elif self.local_model:
                prov = "local"
            else:
                for p, (ep, ks) in self.endpoints.items():
                    if ep:
                        prov = p
                        break
        self.provider = prov or ""
        self.provider_order: List[str] = []
        if self.provider:
            self.provider_order.append(self.provider)
        # prefer local/huggingface/openai then endpoints
        for p in ("local", "openai", "huggingface") + tuple(self.endpoints.keys()):
            if p not in self.provider_order:
                self.provider_order.append(p)

        logger.info("LLMClient initialized provider=%s order=%s timeout=%s retries=%s local_model=%s llm_call_concurrency=%d",
                    self.provider, self.provider_order, self.timeout, self.retries, bool(self.local_model), self._max_llm_concurrency)

    def _post(self, url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> requests.Response:
        attempt = 0
        backoff = 0.5
        while True:
            attempt += 1
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
                return resp
            except requests.Timeout as e:
                logger.warning("Request timeout attempt %d to %s: %s", attempt, url, e)
                if attempt > self.retries:
                    raise ErroTempoEsgotado("Timeout ação chamar servio LLM") from e
            except Exception as e:
                logger.warning("Request exception attempt %d to %s: %s", attempt, url, e)
                if attempt > self.retries:
                    raise ErroExecucaoServico(f"Erro ao chamar servio LLM: {e}") from e
            time.sleep(backoff)
            backoff = min(backoff * 2, 60.0)

    def _request_with_rotation(self, url: str, payload: Dict[str, Any], header_builder, key_state: KeyRotationState, provider_name: str) -> Any:
        attempts = 0
        while True:
            key = key_state.next_key()
            if key is None:
                raise ErroExecucaoServico(f"Nenhuma chave disponível para provedor {provider_name} (todas em cooldown)")
            headers = header_builder(key)
            attempts += 1
            try:
                resp = self._post(url, headers, payload)
            except Exception as e:
                logger.warning("Erro de rede para %s com key=%s: %s", provider_name, "<masked>", e)
                key_state.disable_key(key, cooldown_seconds=30)
                if attempts > max(1, self.retries):
                    raise
                continue

            if resp.status_code == 429:
                ra = resp.headers.get("Retry-After")
                wait = 2
                if ra:
                    try:
                        wait = int(ra)
                    except Exception:
                        wait = 5
                logger.warning("Provider %s returned 429; disabling key for %s s", provider_name, wait)
                key_state.disable_key(key, cooldown_seconds=wait)
                time.sleep(wait)
                if attempts > max(1, self.retries):
                    resp.raise_for_status()
                continue

            if resp.status_code in (401, 403):
                logger.warning("Provider %s returned %s; disabling key longer", provider_name, resp.status_code)
                key_state.disable_key(key, cooldown_seconds=300)
                if attempts > max(1, self.retries):
                    resp.raise_for_status()
                continue

            if 500 <= resp.status_code < 600:
                logger.warning("Provider %s server error %s; disabling key shortly", provider_name, resp.status_code)
                key_state.disable_key(key, cooldown_seconds=10)
                if attempts > max(1, self.retries):
                    resp.raise_for_status()
                continue

            try:
                return resp.json()
            except ValueError:
                return {"raw_text": resp.text}

    def generate(self, prompt: str, max_tokens: int = 512, metadata: Optional[Dict[str, Any]] = None) -> str:
        last_exc: Optional[Exception] = None
        for prov in self.provider_order:
            try:
                if prov == "local" and self.local_model:
                    return self._call_local_model(prompt, max_tokens, metadata)
                if prov == "openai" and self.openai_keys.keys:
                    return self._call_openai_chat(prompt, max_tokens, metadata)
                if prov == "huggingface" and self.hf_tokens.keys:
                    return self._call_huggingface(prompt, max_tokens, metadata)
                ep, ks = self.endpoints.get(prov, (None, None))
                if ep and ks and ks.keys:
                    return self._call_generic_http(ep, ks, prompt, max_tokens, metadata)
            except Exception as e:
                logger.warning("Provider '%s' failed: %s (trying next)", prov, e)
                last_exc = e
                continue
        if last_exc:
            raise last_exc
        raise ErroConfiguracao("Nenhum provedor LLM configurado com chaves/endpoints vlidos")

    def _call_openai_chat(self, prompt: str, max_tokens: int, metadata: Optional[Dict[str, Any]] = None) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": self.openai_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }
        if metadata:
            payload["metadata"] = metadata

        def headers_for(key: str):
            return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

        data = self._request_with_rotation(url, payload, headers_for, self.openai_keys, "openai")
        if isinstance(data, dict):
            choices = data.get("choices")
            if choices and isinstance(choices, list) and choices:
                text = choices[0].get("message", {}).get("content") or choices[0].get("text")
                if text is not None:
                    return str(text)
            for k in ("output", "response", "text", "result"):
                if k in data:
                    return str(data[k])
        return json.dumps(data, ensure_ascii=False)

    def _call_huggingface(self, prompt: str, max_tokens: int, metadata: Optional[Dict[str, Any]] = None) -> str:
        # usar router.huggingface.co (novo host)
        model = self.hf_model
        url = f"https://router.huggingface.co/models/{model}"
        payload = {"inputs": prompt, "options": {"wait_for_model": True}}
        def headers_for(key: str):
            return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        data = self._request_with_rotation(url, payload, headers_for, self.hf_tokens, "huggingface")
        if isinstance(data, list) and data:
            if isinstance(data[0], dict) and "generated_text" in data[0]:
                return str(data[0]["generated_text"])
            return str(data[0])
        if isinstance(data, dict):
            for k in ("generated_text", "outputs", "output", "response", "text", "result"):
                if k in data:
                    v = data[k]
                    if isinstance(v, list) and v:
                        return str(v[0])
                    return str(v)
        return json.dumps(data, ensure_ascii=False)

    def _call_generic_http(self, endpoint: str, key_state: KeyRotationState, prompt: str, max_tokens: int, metadata: Optional[Dict[str, Any]] = None) -> str:
        payload = {"input": prompt, "max_tokens": max_tokens}
        if metadata:
            payload["metadata"] = metadata
        def headers_for(key: str):
            return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        data = self._request_with_rotation(endpoint, payload, headers_for, key_state, endpoint)
        if isinstance(data, dict):
            for k in ("output", "response", "text", "result", "generation"):
                if k in data:
                    return str(data[k])
        return json.dumps(data, ensure_ascii=False)

    # -------------------------
    # Local model support (transformers + bitsandbytes)
    # -------------------------
    def _load_local_model(self):
        """
        Lazy-load a local HF model for on-device inference.
        Uses bitsandbytes quantization (4-bit) and device_map='auto' when possible.
        """
        if self._local_model_obj is not None:
            return

        with self._local_model_lock:
            if self._local_model_obj is not None:
                return
            if not self.local_model:
                raise ErroConfiguracao("local_model no configurado para provedor 'local'")

            try:
                import torch
                from transformers import AutoTokenizer, AutoModelForCausalLM
                # BitsAndBytesConfig exists in transformers 4.30+ / huggingface; import lazily
                try:
                    from transformers import BitsAndBytesConfig
                except:
                    logging.getLogger(__name__).warning("[AVISO] BitsAndBytesConfig no disponível")
                    BitsAndBytesConfig = None

                model_name = self.local_model
                logger.info("Carregando modelo local '%s' (pode demorar)...", model_name)
                tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)

                use_cuda = False
                try:
                    use_cuda = torch.cuda.is_available()
                except Exception:
                    use_cuda = False

                model = None
                if use_cuda and BitsAndBytesConfig is not None:
                    try:
                        bnb_config = BitsAndBytesConfig(
                            load_in_4bit=True,
                            bnb_4bit_compute_dtype=torch.float16,
                            bnb_4bit_use_double_quant=True,
                        )
                        model = AutoModelForCausalLM.from_pretrained(
                            model_name,
                            device_map="auto",
                            quantization_config=bnb_config,
                            torch_dtype=torch.float16,
                            trust_remote_code=True,
                        )
                        logger.info("Modelo local carregado quantizado 4-bit com device_map=auto.")
                    except Exception as e:
                        logger.warning("Falha ao carregar quantizado com bitsandbytes: %s", e)
                        model = None

                if model is None:
                    # fallback: try to load with device_map auto in fp16 if possible
                    try:
                        model = AutoModelForCausalLM.from_pretrained(
                            model_name,
                            device_map="auto" if use_cuda else None,
                            torch_dtype=torch.float16 if use_cuda else None,
                            trust_remote_code=True,
                        )
                        logger.info("Modelo local carregado (fallback) com device_map=%s.", "auto" if use_cuda else "None")
                    except Exception as e:
                        logger.warning("Falha no fallback device_map load: %s. Tentar load padrão CPU.", e)
                        model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True)

                # store
                self._local_model_obj = (model, tokenizer)
            except Exception as e:
                logger.exception("Erro carregando local_model '%s': %s", self.local_model, e)
                raise ErroExecucaoServico(f"Erro ao carregar modelo local: {e}") from e

    def _call_local_model(self, prompt: str, max_tokens: int, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate using a local (on-device) model. This method assumes _load_local_model()
        was able to load the model (possibly sharded with device_map='auto').
        """
        try:
            import torch
        except Exception as e:
            raise ErroExecucaoServico("torch no disponível no ambiente para executar modelo local") from e

        self._load_local_model()
        model, tokenizer = self._local_model_obj  # type: ignore

        # Prepare inputs
        try:
            inputs = tokenizer(prompt, return_tensors="pt")
        except Exception:
            # fallback simpler encode
            input_ids = tokenizer.encode(prompt, return_tensors="pt")
            inputs = {"input_ids": input_ids}

        # Determine device for inputs: prefer CUDA if available, otherwise cpu.
        device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        # Move tensors to device
        try:
            if isinstance(inputs, dict):
                for k, v in list(inputs.items()):
                    if hasattr(v, "to"):
                        inputs[k] = v.to(device)
            else:
                inputs = {k: v.to(device) for k, v in inputs.items()}
        except Exception:
            # if moving fails, continue; model.generate may handle cpu tensors for sharded models
            logger.debug("No conseguiu mover inputs para %s; continuando (o generate pode fazer offload).", device)

        # Generation - use modest defaults; the caller sets max_tokens
        gen_kwargs = dict(max_new_tokens=max_tokens, do_sample=False)

        # Respect concurrency semaphore to avoid OOM and protect GPU usage
        acquired = False
        try:
            # Acquire with timeout to avoid indefinite blocking; timeout can be tuned
            acquired = self._generate_semaphore.acquire(timeout=60)
            if not acquired:
                raise ErroExecucaoServico("Timeout aguardando permisso para executar inferncia local (concurrency limit)")

            # Use inference_mode if available (more efficient than no_grad for inference)
            try:
                inference_ctx = torch.inference_mode
            except AttributeError:
                inference_ctx = torch.no_grad

            with inference_ctx():
                outputs = model.generate(**inputs, **gen_kwargs)
            text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            return text
        except ErroExecucaoServico:
            raise
        except Exception as e:
            logger.exception("Erro durante gerao local do modelo: %s", e)
            raise ErroExecucaoServico(f"Erro durante inferncia local: {e}") from e
        finally:
            if acquired:
                try:
                    self._generate_semaphore.release()
                except Exception:
                    pass
