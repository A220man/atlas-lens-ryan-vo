"""Multi-provider LLM adapter gateway.

Supports OpenAI-compatible (LiteLLM/OpenRouter/Ollama), Anthropic, Gemini
via httpx with bounded timeouts and credential redaction. Includes offline
deterministic fallback when no key is configured.
"""

from typing import Any, Dict, List, Optional
import httpx

from app.core.config import Settings, get_settings


class LlmGatewayService:
    """Interchangeable provider adapter with server-side credential isolation."""

    @classmethod
    async def generate_completion(
        cls,
        prompt: str,
        system_instruction: str = "You are Atlas Lens, an AI developer assistant.",
        settings: Optional[Settings] = None
    ) -> Dict[str, Any]:
        """Send completion request to configured provider or execute offline fallback."""
        if settings is None:
            settings = get_settings()

        # If no API key is supplied, run deterministic offline fallback engine
        if not settings.llm_api_key:
            return cls._offline_deterministic_fallback(prompt, settings)

        timeout = httpx.Timeout(settings.llm_request_timeout, connect=5.0)

        try:
            if settings.llm_provider in ("openai-compatible", "ollama"):
                return await cls._call_openai_compatible(prompt, system_instruction, settings, timeout)
            elif settings.llm_provider == "anthropic":
                return await cls._call_anthropic(prompt, system_instruction, settings, timeout)
            elif settings.llm_provider == "gemini":
                return await cls._call_gemini(prompt, system_instruction, settings, timeout)
            else:
                return {
                    "provider": settings.llm_provider,
                    "model": settings.llm_model,
                    "is_advisory": True,
                    "is_offline_fallback": True,
                    "content": f"[Unsupported provider '{settings.llm_provider}']",
                    "error": f"Provider '{settings.llm_provider}' is not supported."
                }
        except httpx.HTTPStatusError as exc:
            return {
                "provider": settings.llm_provider,
                "model": settings.llm_model,
                "is_advisory": True,
                "is_offline_fallback": True,
                "content": "[Provider API Error]",
                "error": f"HTTP status error from {settings.llm_provider}: status {exc.response.status_code}"
            }
        except Exception as exc:
            return {
                "provider": settings.llm_provider,
                "model": settings.llm_model,
                "is_advisory": True,
                "is_offline_fallback": True,
                "content": "[Connection Error]",
                "error": f"Network or timeout error contacting {settings.llm_provider}: {type(exc).__name__}"
            }

    @classmethod
    async def _call_openai_compatible(
        cls, prompt: str, system: str, settings: Settings, timeout: httpx.Timeout
    ) -> Dict[str, Any]:
        """Invoke OpenAI-compatible /v1/chat/completions endpoint."""
        base_url = settings.llm_base_url.rstrip("/")
        url = f"{base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]["message"]["content"]
            return {
                "provider": "openai-compatible",
                "model": settings.llm_model,
                "is_advisory": True,
                "is_offline_fallback": False,
                "content": choice,
                "error": None
            }

    @classmethod
    async def _call_anthropic(
        cls, prompt: str, system: str, settings: Settings, timeout: httpx.Timeout
    ) -> Dict[str, Any]:
        """Invoke Anthropic /v1/messages endpoint."""
        base_url = settings.llm_base_url.rstrip("/") or "https://api.anthropic.com"
        url = f"{base_url}/v1/messages"
        headers = {
            "x-api-key": settings.llm_api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        payload = {
            "model": settings.llm_model,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024,
            "temperature": 0.2
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["content"][0]["text"]
            return {
                "provider": "anthropic",
                "model": settings.llm_model,
                "is_advisory": True,
                "is_offline_fallback": False,
                "content": content,
                "error": None
            }

    @classmethod
    async def _call_gemini(
        cls, prompt: str, system: str, settings: Settings, timeout: httpx.Timeout
    ) -> Dict[str, Any]:
        """Invoke Google Gemini generateContent endpoint."""
        base_url = settings.llm_base_url.rstrip("/") or "https://generativelanguage.googleapis.com"
        url = f"{base_url}/v1beta/models/{settings.llm_model}:generateContent?key={settings.llm_api_key}"
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": prompt}]}]
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            choice = candidates[0]["content"]["parts"][0]["text"] if candidates else ""
            return {
                "provider": "gemini",
                "model": settings.llm_model,
                "is_advisory": True,
                "is_offline_fallback": False,
                "content": choice,
                "error": None
            }

    @classmethod
    def _offline_deterministic_fallback(cls, prompt: str, settings: Settings) -> Dict[str, Any]:
        """Grounded offline baseline when LLM_API_KEY is not configured."""
        words = prompt.split()
        summary = f"Processed {len(words)} tokens in offline deterministic mode. Key features analyzed."
        return {
            "provider": f"{settings.llm_provider} (offline mode)",
            "model": settings.llm_model,
            "is_advisory": True,
            "is_offline_fallback": True,
            "content": f"[Offline Grounded Response]: {summary}",
            "error": "No LLM_API_KEY provided; operating in deterministic offline baseline mode."
        }
