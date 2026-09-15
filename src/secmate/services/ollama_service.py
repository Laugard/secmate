"""Bounded async access to the host-local Ollama API."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, cast

from secmate.errors import ModelResponseError, OllamaUnavailable


class OllamaClient(Protocol):
    async def list(self) -> Any: ...
    async def chat(self, **kwargs: Any) -> Any: ...
    async def embed(self, **kwargs: Any) -> Any: ...


def _value(response: Any, key: str, default: Any = None) -> Any:
    if isinstance(response, Mapping):
        return response.get(key, default)
    return getattr(response, key, default)


class OllamaService:
    def __init__(
        self,
        host: str,
        chat_model: str,
        embed_model: str,
        timeout: float = 120,
        client: OllamaClient | None = None,
    ) -> None:
        self.chat_model = chat_model
        self.embed_model = embed_model
        self.timeout = timeout
        if client is None:
            from ollama import AsyncClient

            client = cast(Any, AsyncClient(host=host))
        self.client = cast(OllamaClient, client)
        self._semaphore = asyncio.Semaphore(1)

    async def _bounded(self, awaitable: Any) -> Any:
        try:
            async with self._semaphore:
                return await asyncio.wait_for(awaitable, timeout=self.timeout)
        except TimeoutError as exc:
            raise OllamaUnavailable("Den lokale AI svarede ikke inden timeout") from exc
        except OllamaUnavailable:
            raise
        except Exception as exc:
            raise OllamaUnavailable("Den lokale AI er ikke tilgængelig") from exc

    async def health(self) -> dict[str, bool]:
        response = await self._bounded(self.client.list())
        raw_models = _value(response, "models", [])
        names = {str(_value(model, "model", _value(model, "name", ""))) for model in raw_models}
        return {
            "api": True,
            "chat_model": self.chat_model in names,
            "embed_model": self.embed_model in names,
        }

    async def chat(
        self,
        system: str,
        user: str,
        *,
        tools: Sequence[dict[str, Any]] | None = None,
        messages: list[dict[str, Any]] | None = None,
    ) -> Any:
        payload = messages or [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        kwargs: dict[str, Any] = {"model": self.chat_model, "messages": payload}
        if tools:
            kwargs["tools"] = list(tools)
        response = await self._bounded(self.client.chat(**kwargs))
        message = _value(response, "message", {})
        return message

    async def structured(self, system: str, user: str, fallback: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(2):
            prompt = (
                user if attempt == 0 else user + "\nReturnér KUN gyldig JSON i det krævede format."
            )
            message = await self.chat(system, prompt)
            content = str(_value(message, "content", ""))
            try:
                result = json.loads(content)
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                continue
        return fallback

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await self._bounded(self.client.embed(model=self.embed_model, input=list(texts)))
        vectors = _value(response, "embeddings", [])
        if len(vectors) != len(texts) or not vectors:
            raise ModelResponseError("Embeddingmodellen returnerede et forkert antal vektorer")
        dimensions = len(vectors[0])
        if dimensions == 0 or any(len(vector) != dimensions for vector in vectors):
            raise ModelResponseError("Embeddingdimensionerne er inkonsistente")
        return [[float(value) for value in vector] for vector in vectors]
