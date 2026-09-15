#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from secmate.config import Settings  # noqa: E402
from secmate.repositories.database import Database, DocumentRepository  # noqa: E402
from secmate.services.ingestion_service import IngestionService  # noqa: E402
from secmate.services.ollama_service import OllamaService  # noqa: E402


async def run() -> None:
    settings = Settings.from_env(require_discord=False)
    settings.ensure_directories()
    database = Database(settings.database_path)
    await database.migrate()
    ollama = OllamaService(
        settings.ollama_host,
        settings.ollama_chat_model,
        settings.ollama_embed_model,
        settings.ollama_timeout,
    )
    service = IngestionService(
        DocumentRepository(database),
        ollama,
        settings.documents_path,
        max_bytes=settings.max_document_bytes,
        max_pages=settings.max_document_pages,
        chunk_chars=settings.rag_chunk_chars,
        overlap_chars=settings.rag_chunk_overlap_chars,
    )
    report = await service.ingest_all()
    print(
        f"Indekseret={report.indexed} uændret={report.unchanged} chunks={report.chunks} fejl={len(report.errors)}"
    )
    for error in report.errors:
        print(error)


if __name__ == "__main__":
    asyncio.run(run())
