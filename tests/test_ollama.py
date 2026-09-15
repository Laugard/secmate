from __future__ import annotations

import asyncio
from typing import Any

import pytest

from secmate.errors import ModelResponseError, OllamaUnavailable
from secmate.services.ollama_service import OllamaService


class FakeClient:
    def __init__(self) -> None:
        self.chat_responses: list[Any] = []

    async def list(self) -> dict[str, Any]:
        return {"models": [{"model": "qwen3:4b"}, {"model": "embeddinggemma"}]}

    async def chat(self, **kwargs: Any) -> Any:
        return self.chat_responses.pop(0) if self.chat_responses else {"message": {"content": "ok"}}

    async def embed(self, **kwargs: Any) -> Any:
        values = kwargs["input"]
        return {"embeddings": [[1.0, float(index)] for index, _ in enumerate(values)]}


async def test_health_and_embed() -> None:
    service = OllamaService(
        "http://127.0.0.1:11434", "qwen3:4b", "embeddinggemma", client=FakeClient()
    )
    assert all((await service.health()).values())
    assert len(await service.embed(["a", "b"])) == 2


async def test_structured_retries_then_fallback() -> None:
    client = FakeClient()
    client.chat_responses = [{"message": {"content": "bad"}}, {"message": {"content": "still bad"}}]
    service = OllamaService("http://127.0.0.1:11434", "qwen3:4b", "embeddinggemma", client=client)
    assert await service.structured("s", "u", {"safe": True}) == {"safe": True}


async def test_bad_embedding_dimensions() -> None:
    class Bad(FakeClient):
        async def embed(self, **kwargs: Any) -> Any:
            return {"embeddings": [[1.0], [1.0, 2.0]]}

    service = OllamaService("http://127.0.0.1:11434", "q", "e", client=Bad())
    with pytest.raises(ModelResponseError):
        await service.embed(["a", "b"])


async def test_timeout_releases_semaphore() -> None:
    class Slow(FakeClient):
        async def chat(self, **kwargs: Any) -> Any:
            await asyncio.sleep(0.05)

    service = OllamaService("http://127.0.0.1:11434", "q", "e", timeout=0.001, client=Slow())
    for _ in range(2):
        with pytest.raises(OllamaUnavailable):
            await service.chat("s", "u")
