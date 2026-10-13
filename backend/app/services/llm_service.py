"""Thin client for any OpenAI-compatible /chat/completions API (Groq, Gemini-compat, OpenAI, Ollama)."""
from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class LLMUnavailable(Exception):
    pass


def chat(messages: list[dict], tools: list[dict] | None = None, temperature: float = 0.3) -> dict:
    """Returns the assistant `message` dict (may contain `tool_calls`)."""
    if not settings.llm_enabled:
        raise LLMUnavailable("LLM_API_KEY is not configured")
    payload: dict = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": settings.LLM_MAX_TOKENS,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    try:
        r = httpx.post(
            f"{settings.LLM_API_BASE_URL.rstrip('/')}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
        if r.status_code >= 400:
            logger.warning("LLM error %s: %s", r.status_code, r.text[:300])
            raise LLMUnavailable(f"LLM provider returned {r.status_code}")
        return r.json()["choices"][0]["message"]
    except httpx.HTTPError as exc:
        raise LLMUnavailable(str(exc)) from exc
