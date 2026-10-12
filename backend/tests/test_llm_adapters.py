"""Tests for LLM multi-provider gateway and offline deterministic fallback."""

import pytest
import httpx
from app.core.config import Settings
from app.services.llm_adapters import LlmGatewayService


@pytest.mark.asyncio
async def test_offline_deterministic_fallback():
    """Ensure offline deterministic fallback runs when LLM_API_KEY is empty."""
    settings = Settings(llm_api_key="", llm_provider="ollama", llm_model="llama3.1")
    res = await LlmGatewayService.generate_completion(
        prompt="Explain token bloat in conversation history",
        settings=settings
    )
    assert res["is_offline_fallback"] is True
    assert res["is_advisory"] is True
    assert "offline" in res["provider"].lower()
    assert "No LLM_API_KEY provided" in res["error"]
    assert "[Offline Grounded Response]" in res["content"]


@pytest.mark.asyncio
async def test_openai_compatible_mocked_success(monkeypatch):
    """Test OpenAI-compatible adapter with mocked httpx response."""
    synthetic_key = "synthetic-openai-key-" + ("0" * 8)
    settings = Settings(
        llm_api_key=synthetic_key,
        llm_provider="openai-compatible",
        llm_model="gpt-4o-mini",
        llm_base_url="http://127.0.0.1:11434"
    )

    async def mock_post(self, url, *args, **kwargs):
        req = httpx.Request("POST", url)
        return httpx.Response(
            status_code=200,
            json={"choices": [{"message": {"content": "Mocked completion result"}}]},
            request=req
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    res = await LlmGatewayService.generate_completion(prompt="Hello", settings=settings)
    assert res["content"] == "Mocked completion result"
    assert res["provider"] == "openai-compatible"
    assert res["is_offline_fallback"] is False


@pytest.mark.asyncio
async def test_anthropic_mocked_success(monkeypatch):
    """Test Anthropic adapter with mocked response."""
    synthetic_key = "synthetic-anthropic-key-" + ("0" * 8)
    settings = Settings(
        llm_api_key=synthetic_key,
        llm_provider="anthropic",
        llm_model="claude-3-5-sonnet",
        llm_base_url="http://127.0.0.1:8000"
    )

    async def mock_post(self, url, *args, **kwargs):
        req = httpx.Request("POST", url)
        return httpx.Response(
            status_code=200,
            json={"content": [{"text": "Anthropic response text"}]},
            request=req
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    res = await LlmGatewayService.generate_completion(prompt="Hello", settings=settings)
    assert res["content"] == "Anthropic response text"
    assert res["provider"] == "anthropic"


@pytest.mark.asyncio
async def test_gemini_mocked_success(monkeypatch):
    """Test Gemini adapter with mocked response."""
    synthetic_key = "synthetic-gemini-key-" + ("0" * 8)
    settings = Settings(
        llm_api_key=synthetic_key,
        llm_provider="gemini",
        llm_model="gemini-1.5-flash",
        llm_base_url="http://127.0.0.1:8000"
    )

    async def mock_post(self, url, *args, **kwargs):
        req = httpx.Request("POST", url)
        return httpx.Response(
            status_code=200,
            json={"candidates": [{"content": {"parts": [{"text": "Gemini response text"}]}}]},
            request=req
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    res = await LlmGatewayService.generate_completion(prompt="Hello", settings=settings)
    assert res["content"] == "Gemini response text"
    assert res["provider"] == "gemini"


@pytest.mark.asyncio
async def test_provider_http_error_handling(monkeypatch):
    """Ensure HTTP errors from providers are gracefully captured without crashing."""
    synthetic_key = "synthetic-key-" + ("0" * 8)
    settings = Settings(
        llm_api_key=synthetic_key,
        llm_provider="openai-compatible",
        llm_model="gpt-4o",
        llm_base_url="http://127.0.0.1:11434"
    )

    async def mock_post(self, url, *args, **kwargs):
        req = httpx.Request("POST", url)
        return httpx.Response(status_code=500, request=req)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    res = await LlmGatewayService.generate_completion(prompt="Hello", settings=settings)
    assert res["is_offline_fallback"] is True
    assert "status 500" in res["error"]
