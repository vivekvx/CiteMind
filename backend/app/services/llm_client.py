import json
import logging
import re
from typing import Optional

import httpx

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

TIMEOUT = 120.0


class LLMClient:
    """Provider chain: Ollama → Groq → OpenAI → OpenRouter."""

    def complete(self, prompt: str, system: str = "", json_mode: bool = False) -> str:
        settings = get_settings()
        provider = settings.llm_provider

        if provider == "auto":
            for fn in (self._try_ollama, self._try_groq, self._try_openai, self._try_openrouter):
                result = fn(prompt, system, json_mode, settings)
                if result is not None:
                    return result
            raise RuntimeError(
                "No LLM available. Start Ollama or set GROQ_API_KEY / OPENAI_API_KEY / OPENROUTER_API_KEY."
            )

        fn_map = {
            "ollama": self._try_ollama,
            "groq": self._try_groq,
            "openai": self._try_openai,
            "openrouter": self._try_openrouter,
        }
        fn = fn_map.get(provider)
        if fn is None:
            raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")
        result = fn(prompt, system, json_mode, settings)
        if result is None:
            raise RuntimeError(f"LLM provider {provider!r} failed or is not configured.")
        return result

    def _try_ollama(self, prompt: str, system: str, json_mode: bool, settings) -> Optional[str]:
        url = f"{settings.ollama_base_url}/api/chat"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body: dict = {"model": settings.ollama_model, "messages": messages, "stream": False}
        if json_mode:
            body["format"] = "json"
        try:
            resp = httpx.post(url, json=body, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()["message"]["content"]
        except Exception as exc:
            logger.debug("Ollama unavailable: %s", exc)
            return None

    def _try_groq(self, prompt: str, system: str, json_mode: bool, settings) -> Optional[str]:
        if not settings.groq_api_key:
            return None
        return self._openai_compat(
            url="https://api.groq.com/openai/v1/chat/completions",
            api_key=settings.groq_api_key,
            model=settings.groq_chat_model,
            prompt=prompt,
            system=system,
            json_mode=json_mode,
        )

    def _try_openai(self, prompt: str, system: str, json_mode: bool, settings) -> Optional[str]:
        if not settings.openai_api_key:
            return None
        return self._openai_compat(
            url="https://api.openai.com/v1/chat/completions",
            api_key=settings.openai_api_key,
            model=settings.openai_chat_model,
            prompt=prompt,
            system=system,
            json_mode=json_mode,
        )

    def _try_openrouter(self, prompt: str, system: str, json_mode: bool, settings) -> Optional[str]:
        if not settings.openrouter_api_key:
            return None
        return self._openai_compat(
            url="https://openrouter.ai/api/v1/chat/completions",
            api_key=settings.openrouter_api_key,
            model=settings.llm_chat_model or "openai/gpt-4o-mini",
            prompt=prompt,
            system=system,
            json_mode=json_mode,
        )

    def _openai_compat(
        self,
        url: str,
        api_key: str,
        model: str,
        prompt: str,
        system: str,
        json_mode: bool,
    ) -> Optional[str]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body: dict = {"model": model, "messages": messages}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        try:
            resp = httpx.post(
                url,
                json=body,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.debug("OpenAI-compat call failed (%s): %s", url, exc)
            return None


def parse_json_response(text: str) -> dict:
    """Extract JSON from LLM response that may wrap JSON in prose or code fences."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError(f"No valid JSON in LLM response: {text[:200]}")
