import asyncio

import pytest

from app.ai_provider import AIProviderError, NvidiaNimProvider, get_ai_provider


class FakeStreamResponse:
    async def aiter_lines(self):
        yield 'data: {"choices":[{"delta":{"content":"Draft "}}]}'
        yield 'data: {"choices":[{"delta":{"content":"text"}}]}'
        yield "data: [DONE]"


def test_nim_provider_requires_key_and_model(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "nvidia_nim")
    monkeypatch.delenv("NVIDIA_NIM_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_NIM_MODEL", raising=False)
    provider = get_ai_provider()
    assert not provider.is_configured

    with pytest.raises(AIProviderError, match="NVIDIA_NIM_API_KEY"):
        asyncio.run(provider.open_stream("test prompt"))


def test_ollama_is_disabled(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    with pytest.raises(AIProviderError, match="intentionally disabled"):
        get_ai_provider()


def test_nim_sse_stream_parsing():
    provider = NvidiaNimProvider()

    async def collect():
        return "".join([chunk async for chunk in provider.stream_text(FakeStreamResponse())])

    assert asyncio.run(collect()) == "Draft text"
