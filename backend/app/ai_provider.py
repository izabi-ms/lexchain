"""AI provider boundary for LexChain.

The current implementation supports NVIDIA NIM's OpenAI-compatible chat-completions
API. Local Ollama code is deliberately not imported or initialized by the application.
"""
from __future__ import annotations

import json
import os
from typing import AsyncIterator

import httpx
from dotenv import load_dotenv

from app.db import BACKEND_DIR

load_dotenv(BACKEND_DIR / ".env", override=False)


class AIProviderError(RuntimeError):
    """A safe, user-presentable AI provider error."""


class NvidiaNimProvider:
    def __init__(self) -> None:
        self.base_url = os.getenv(
            "NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"
        ).rstrip("/")
        self.api_key = os.getenv("NVIDIA_NIM_API_KEY", "").strip()
        self.model = os.getenv("NVIDIA_NIM_MODEL", "").strip()
        try:
            self.timeout_seconds = float(os.getenv("NVIDIA_NIM_TIMEOUT_SECONDS", "180"))
        except ValueError:
            self.timeout_seconds = 180.0

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.model and self.base_url)

    async def open_stream(self, prompt: str) -> tuple[httpx.AsyncClient, httpx.Response]:
        if not self.api_key:
            raise AIProviderError("NVIDIA NIM is not configured. Set NVIDIA_NIM_API_KEY in backend/.env.")
        if not self.model:
            raise AIProviderError("NVIDIA NIM model is not configured. Set NVIDIA_NIM_MODEL in backend/.env.")

        client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout_seconds, connect=20.0),
        )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You assist with drafting business documents. Produce a clear English-language draft "
                        "based only on the information supplied. Do not invent facts, legal citations, "
                        "statutory requirements, or claims that a document is legally valid. Where important "
                        "information is missing, use a visible placeholder rather than guessing. The output is "
                        "a draft for human review, not a substitute for advice from a qualified lawyer."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "stream": True,
        }
        try:
            request = client.build_request(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "text/event-stream",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response = await client.send(request, stream=True)
            if response.is_error:
                body = (await response.aread()).decode("utf-8", errors="replace")
                status = response.status_code
                await response.aclose()
                await client.aclose()
                # Do not expose request headers or API credentials in errors.
                safe_body = body[:500] if body else "No provider error details returned."
                raise AIProviderError(f"NVIDIA NIM returned HTTP {status}: {safe_body}")
            return client, response
        except AIProviderError:
            raise
        except httpx.HTTPError as exc:
            await client.aclose()
            raise AIProviderError(f"Could not connect to NVIDIA NIM: {exc.__class__.__name__}.") from exc

    async def stream_text(self, response: httpx.Response) -> AsyncIterator[str]:
        async for line in response.aiter_lines():
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = payload.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            content = delta.get("content")
            if isinstance(content, str) and content:
                yield content


def get_ai_provider() -> NvidiaNimProvider:
    """Return the configured provider without making a network request."""
    provider_name = os.getenv("AI_PROVIDER", "nvidia_nim").strip().lower()
    if provider_name != "nvidia_nim":
        if provider_name == "ollama":
            raise AIProviderError(
                "Ollama is intentionally disabled in this MVP phase. Use AI_PROVIDER=nvidia_nim."
            )
        raise AIProviderError(f"Unsupported AI_PROVIDER '{provider_name}'.")
    return NvidiaNimProvider()
