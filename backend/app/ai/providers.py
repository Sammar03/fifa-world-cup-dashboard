"""Multi-provider LLM client (owner decision 2026-06-12: free-tier providers
first — groq default — with anthropic/openai/gemini/openrouter selectable via
AI_PROVIDER + AI_MODEL + AI_API_KEY; switching providers is an env change only).

Plain httpx, no provider SDKs: groq and openrouter speak the OpenAI
chat-completions dialect, so there are exactly three wire formats here
(OpenAI-compatible, Anthropic, Gemini). Called ONLY from the ingestion job —
never on the request path (CLAUDE.md §5.1).
"""

import logging
import time
from dataclasses import dataclass

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_OPENAI_COMPATIBLE_BASE = {
    "openai": "https://api.openai.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}

_TIMEOUT_SECONDS = 30


@dataclass
class AIResult:
    text: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int
    model: str


class AIProviderError(Exception):
    pass


def ai_available() -> bool:
    key = get_settings().AI_API_KEY
    return bool(key) and key != "your_key_here"


async def complete(prompt: str) -> AIResult:
    """One-shot completion via the configured provider. Raises AIProviderError
    on any failure — callers log and skip, never crash the ingestion run."""
    settings = get_settings()
    if not ai_available():
        raise AIProviderError("AI_API_KEY is not configured")

    started = time.monotonic()
    try:
        if settings.AI_PROVIDER in _OPENAI_COMPATIBLE_BASE:
            result = await _openai_compatible(
                _OPENAI_COMPATIBLE_BASE[settings.AI_PROVIDER], prompt
            )
        elif settings.AI_PROVIDER == "anthropic":
            result = await _anthropic(prompt)
        elif settings.AI_PROVIDER == "gemini":
            result = await _gemini(prompt)
        else:  # unreachable — config validates the literal
            raise AIProviderError(f"unknown provider {settings.AI_PROVIDER}")
    except httpx.HTTPError as exc:
        raise AIProviderError(f"{settings.AI_PROVIDER} call failed: {exc}") from exc

    result.latency_ms = int((time.monotonic() - started) * 1000)
    return result


async def _openai_compatible(base_url: str, prompt: str) -> AIResult:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.AI_API_KEY}"},
            json={
                "model": settings.AI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": settings.AI_MAX_TOKENS,
                "temperature": 0.4,
            },
        )
        response.raise_for_status()
        payload = response.json()
    try:
        text = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIProviderError(f"unexpected response shape: {exc}") from exc
    usage = payload.get("usage") or {}
    return AIResult(
        text=text,
        input_tokens=usage.get("prompt_tokens"),
        output_tokens=usage.get("completion_tokens"),
        latency_ms=0,
        model=settings.AI_MODEL,
    )


async def _anthropic(prompt: str) -> AIResult:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.AI_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": settings.AI_MODEL,
                "max_tokens": settings.AI_MAX_TOKENS,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
            },
        )
        response.raise_for_status()
        payload = response.json()
    try:
        text = payload["content"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIProviderError(f"unexpected response shape: {exc}") from exc
    usage = payload.get("usage") or {}
    return AIResult(
        text=text,
        input_tokens=usage.get("input_tokens"),
        output_tokens=usage.get("output_tokens"),
        latency_ms=0,
        model=settings.AI_MODEL,
    )


async def _gemini(prompt: str) -> AIResult:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL}:generateContent",
            # Key in a header, NOT a query param: httpx logs full request URLs at
            # INFO and embeds them in HTTP exceptions, so a ?key= would leak the
            # secret into logs (security baseline, CLAUDE.md §11).
            headers={"x-goog-api-key": settings.AI_API_KEY},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": settings.AI_MAX_TOKENS,
                    "temperature": 0.4,
                },
            },
        )
        response.raise_for_status()
        payload = response.json()
    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIProviderError(f"unexpected response shape: {exc}") from exc
    usage = payload.get("usageMetadata") or {}
    return AIResult(
        text=text,
        input_tokens=usage.get("promptTokenCount"),
        output_tokens=usage.get("candidatesTokenCount"),
        latency_ms=0,
        model=settings.AI_MODEL,
    )
