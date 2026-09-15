"""Safe local document discovery, extraction, chunking, and atomic indexing."""

from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from secmate.errors import ValidationError
from secmate.repositories.database import DocumentRepository
from secmate.services.ollama_service import OllamaService
from secmate.services.rag_service import pack_embedding

SUPPORTED = {".pdf", ".md", ".txt"}


@dataclass(frozen=True, slots=True)
class SourcePage:
    text: str
    page: int | None


@dataclass(frozen=True, slots=True)
class IngestionReport:
    indexed: int = 0
    unchanged: int = 0
    chunks: int = 0
    ignored: int = 0
    errors: tuple[str, ...] = ()


def safe_files(root: Path, max_bytes: int) -> tuple[list[Path], list[str]]:
    root = root.resolve()
    files: list[Path] = []
    errors: list[str] = []
    for candidate in root.rglob("*"):
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(root)
            if candidate.is_symlink():
                raise ValidationError("symbolske links er ikke tilladt")
            if not resolved.is_file() or resolved.suffix.lower() not in SUPPORTED:
                continue
            if resolved.stat().st_size > max_bytes:
                raise ValidationError("filen er for stor")
            files.append(resolved)
        except (OSError, ValidationError, ValueError) as exc:
            errors.append(f"{candidate.name}: {exc}")
    return files, errors


def _extract(path: Path, max_pages: int) -> list[SourcePage]:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        if len(reader.pages) > max_pages:
            raise ValidationError("PDF'en har for mange sider")
        pages = [
            SourcePage((page.extract_text() or "").strip(), index + 1)
            for index, page in enumerate(reader.pages)
        ]
        if sum(len(page.text) for page in pages) < 20:
            raise ValidationError("PDF'en har ingen udtrækkelig tekst; OCR er ikke understøttet")
        return pages
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError("tekstfilen er ikke UTF-8") from exc
    if not text.strip():
        raise ValidationError("filen er tom")
    return [SourcePage(text, None)]


def chunk_pages(pages: list[SourcePage], size: int, overlap: int) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for page in pages:
        text = re.sub(r"\s+", " ", page.text).strip()
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                boundary = text.rfind(" ", start + size // 2, end)
                if boundary > start:
                    end = boundary
            content = text[start:end].strip()
            if content:
                chunks.append({"content": content, "page_start": page.page, "page_end": page.page})
            if end >= len(text):
                break
            start = max(start + 1, end - overlap)
    return chunks


class IngestionService:
    def __init__(
        self,
        repository: DocumentRepository,
        ollama: OllamaService,
        root: Path,
        *,
        max_bytes: int,
        max_pages: int,
        chunk_chars: int,
        overlap_chars: int,
    ) -> None:
        self.repository = repository
        self.ollama = ollama
        self.root = root
        self.max_bytes = max_bytes
        self.max_pages = max_pages
        self.chunk_chars = chunk_chars
        self.overlap_chars = overlap_chars

    async def ingest_all(self) -> IngestionReport:
        files, errors = await asyncio.to_thread(safe_files, self.root, self.max_bytes)
        indexed = unchanged = chunk_count = 0
        for path in files:
            relative = str(path.relative_to(self.root.resolve()))
            try:
                data = await asyncio.to_thread(path.read_bytes)
                digest = hashlib.sha256(data).hexdigest()
                if await self.repository.current_signature(relative) == (
                    digest,
                    self.ollama.embed_model,
                ):
                    unchanged += 1
                    continue
                pages = await asyncio.to_thread(_extract, path, self.max_pages)
                chunks = chunk_pages(pages, self.chunk_chars, self.overlap_chars)
                vectors = await self.ollama.embed([chunk["content"] for chunk in chunks])
                for chunk, vector in zip(chunks, vectors, strict=True):
                    chunk["embedding"] = pack_embedding(vector)
                    chunk["embedding_dimensions"] = len(vector)
                await self.repository.replace(
                    display_name=path.name,
                    relative_path=relative,
                    sha256=digest,
                    file_type=path.suffix.lower().lstrip("."),
                    page_count=len(pages) if path.suffix.lower() == ".pdf" else None,
                    embed_model=self.ollama.embed_model,
                    chunks=chunks,
                    indexed_at=datetime.now(UTC),
                )
                indexed += 1
                chunk_count += len(chunks)
            except Exception as exc:
                errors.append(f"{path.name}: {type(exc).__name__}: {exc}")
        return IngestionReport(indexed, unchanged, chunk_count, 0, tuple(errors))
