"""Regressions pinned by the September 2026 code review."""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

from secmate.app import remaining_text
from secmate.logging_config import RedactingFilter
from secmate.repositories.database import Database, DocumentRepository, NewsRepository
from secmate.services.news_service import NewsService, published_at
from secmate.services.ollama_service import OllamaService, parse_json_object
from secmate.services.rag_service import NO_EVIDENCE_MESSAGE, NO_EVIDENCE_TOKEN, RagService

RSS = b"""<?xml version='1.0'?><rss version='2.0'><channel><title>Feed</title>
<item><title>First</title><link>https://example.com/1</link>
<pubDate>Mon, 14 Sep 2026 10:00:00 GMT</pubDate><description>a</description></item>
<item><title>Second</title><link>https://example.com/2</link><description>b</description></item>
</channel></rss>"""


class TaggedClient:
    async def list(self) -> dict[str, Any]:
        return {"models": [{"model": "qwen3:4b"}, {"model": "embeddinggemma:latest"}]}

    async def chat(self, **kwargs: Any) -> Any:
        return {"message": {"content": '```json\n{"category": "andet"}\n```'}}

    async def embed(self, **kwargs: Any) -> Any:
        return {"embeddings": [[1.0, 0.0] for _ in kwargs["input"]]}


async def test_health_matches_implicit_latest_tag() -> None:
    service = OllamaService(
        "http://127.0.0.1:11434", "qwen3:4b", "embeddinggemma", client=TaggedClient()
    )
    assert (await service.health())["embed_model"] is True


async def test_structured_accepts_fenced_json_and_requests_json_format() -> None:
    seen: dict[str, Any] = {}

    class Recording(TaggedClient):
        async def chat(self, **kwargs: Any) -> Any:
            seen.update(kwargs)
            return await super().chat(**kwargs)

    service = OllamaService("http://127.0.0.1:11434", "q", "e", client=Recording())
    assert await service.structured("s", "u", {}) == {"category": "andet"}
    assert seen["format"] == "json" and seen["think"] is False
    assert parse_json_object("[1]") is None and parse_json_object("nope") is None


class CountingOllama:
    embed_model = "e"

    def __init__(self) -> None:
        self.calls = 0

    async def structured(self, system: str, user: str, fallback: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        return {"category": "lovgivning", "summary_da": "s", "study_relevance_da": "r"}


class TwoItemFeed:
    urls = ("https://example.com/feed.xml",)

    async def fetch(self, url: str) -> bytes:
        return RSS


async def test_refresh_classifies_only_unseen_entries(tmp_path: Path) -> None:
    database = Database(tmp_path / "db.sqlite")
    await database.migrate()
    ollama = CountingOllama()
    service = NewsService(NewsRepository(database), ollama, TwoItemFeed())  # type: ignore[arg-type]
    first, errors = await service.refresh(5)
    assert not errors and len(first) == 2 and ollama.calls == 2
    assert first[0]["published_at_utc"] == "2026-09-14T10:00:00Z"
    assert first[1]["published_at_utc"] is None
    second, _ = await service.refresh(5)
    assert second == [] and ollama.calls == 2


def test_published_at_handles_missing_dates() -> None:
    assert published_at({}) is None


class NoEvidenceOllama:
    embed_model = "e"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]

    async def chat(self, system: str, user: str, **kwargs: Any) -> dict[str, str]:
        assert NO_EVIDENCE_TOKEN in system
        return {"content": NO_EVIDENCE_TOKEN}


async def test_no_evidence_token_suppresses_citation_claim(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from secmate.services.rag_service import pack_embedding

    database = Database(tmp_path / "db.sqlite")
    await database.migrate()
    repository = DocumentRepository(database)
    await repository.replace(
        display_name="a.txt",
        relative_path="a.txt",
        sha256="one",
        file_type="txt",
        page_count=None,
        embed_model="e",
        chunks=[
            {
                "content": "unrelated",
                "page_start": None,
                "page_end": None,
                "embedding": pack_embedding([1.0, 0.0]),
                "embedding_dimensions": 2,
            }
        ],
        indexed_at=datetime.now(UTC),
    )
    answer = await RagService(repository, NoEvidenceOllama()).answer("q")  # type: ignore[arg-type]
    assert answer.startswith(NO_EVIDENCE_MESSAGE) and "Nærmeste uddrag: [a.txt]" in answer
    assert "Kilder:" not in answer


def test_redacting_filter_renders_arguments_before_redacting() -> None:
    record = logging.LogRecord(
        "t", logging.INFO, __file__, 1, "job=%s token=%s", ("x", "abcdefgh12"), None
    )
    assert RedactingFilter().filter(record)
    assert record.getMessage() == "job=x token=[REDACTED]"


def test_remaining_text_is_never_negative() -> None:
    assert remaining_text(timedelta(hours=-5)) == "0 timer"
    assert remaining_text(timedelta(hours=386)) == "16 dage 2 timer"
