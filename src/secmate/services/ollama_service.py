"""Bounded async access to the host-local Ollama API."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, cast

from secmate.errors import ModelResponseError, OllamaUnavailable

_JSON_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


class OllamaClient(Protocol):
    async def list(self) -> Any: ...
    async def chat(self, **kwargs: Any) -> Any: ...
    async def embed(self, **kwargs: Any) -> Any: ...


def field(response: Any, key: str, default: Any = None) -> Any:
    """Read a key from either a mapping or an attribute-style SDK response object."""
    if isinstance(response, Mapping):
        return response.get(key, default)
    return getattr(response, key, default)


def message_text(message: Any) -> str:
    """The assistant text of a chat message, stripped; empty when the model returned none."""
    return str(field(message, "content", "") or "").strip()


def model_tag(name: str) -> str:
    """Ollama reports an untagged pull as `name:latest`; compare both sides without the default tag."""
    return name.removesuffix(":latest")


def parse_json_object(content: str) -> dict[str, Any] | None:
    """Parse a JSON object from model output, tolerating a Markdown code fence around it."""
    fenced = _JSON_FENCE.match(content)
    candidate = fenced.group(1) if fenced else content
    try:
        result = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return result if isinstance(result, dict) else None


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
        raw_models = field(response, "models", [])
        names = {
            model_tag(str(field(model, "model", field(model, "name", "")))) for model in raw_models
        }
        return {
            "api": True,
            "chat_model": model_tag(self.chat_model) in names,
            "embed_model": model_tag(self.embed_model) in names,
        }

    async def chat(
        self,
        system: str,
        user: str,
        *,
        tools: Sequence[dict[str, Any]] | None = None,
        messages: list[dict[str, Any]] | None = None,
        json_only: bool = False,
    ) -> Any:
        payload = messages or [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        # Reasoning models (qwen3) otherwise spend the whole timeout budget on a hidden
        # thinking pass before the first answer token; every SecMate task is extractive.
        kwargs: dict[str, Any] = {"model": self.chat_model, "messages": payload, "think": False}
        if tools:
            kwargs["tools"] = list(tools)
        if json_only:
            kwargs["format"] = "json"
        response = await self._bounded(self.client.chat(**kwargs))
        return field(response, "message", {})

    async def structured(self, system: str, user: str, fallback: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(2):
            prompt = (
                user if attempt == 0 else user + "\nReturnér KUN gyldig JSON i det krævede format."
            )
            message = await self.chat(system, prompt, json_only=True)
            result = parse_json_object(message_text(message))
            if result is not None:
                return result
        return fallback

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await self._bounded(self.client.embed(model=self.embed_model, input=list(texts)))
        vectors = field(response, "embeddings", [])
        if len(vectors) != len(texts) or not vectors:
            raise ModelResponseError("Embeddingmodellen returnerede et forkert antal vektorer")
        dimensions = len(vectors[0])
        if dimensions == 0 or any(len(vector) != dimensions for vector in vectors):
            raise ModelResponseError("Embeddingdimensionerne er inkonsistente")
        return [[float(value) for value in vector] for vector in vectors]
