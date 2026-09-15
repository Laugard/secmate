from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, StreamObject

from secmate.repositories.database import Database, DocumentRepository
from secmate.services.ingestion_service import IngestionService, SourcePage, chunk_pages, safe_files
from secmate.services.rag_service import RagService, pack_embedding, similarity, unpack_embedding


class FakeOllama:
    embed_model = "embeddinggemma"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] if "NIS2" in text else [0.0, 1.0] for text in texts]

    async def chat(self, system: str, user: str, **kwargs: Any) -> dict[str, str]:
        assert "upålidelige data" in system
        return {"content": "NIS2 stiller krav til risikostyring."}


def write_text_pdf(path: Path) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    stream = StreamObject()
    stream.set_data(b"BT /F1 12 Tf 72 720 Td (NIS2 source page one) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)  # noqa: SLF001
    with path.open("wb") as output:
        writer.write(output)


async def test_md_ingestion_is_idempotent_and_retrievable(tmp_path: Path) -> None:
    root = tmp_path / "documents"
    root.mkdir()
    (root / "nis2.md").write_text(
        "NIS2 kræver passende cybersikkerheds-risikostyring.", encoding="utf-8"
    )
    database = Database(tmp_path / "db.sqlite")
    await database.migrate()
    repository = DocumentRepository(database)
    service = IngestionService(
        repository,
        FakeOllama(),
        root,
        max_bytes=10000,
        max_pages=10,
        chunk_chars=100,
        overlap_chars=10,
    )  # type: ignore[arg-type]
    first = await service.ingest_all()
    second = await service.ingest_all()
    assert (first.indexed, first.chunks, second.unchanged) == (1, 1, 1)
    rag = RagService(repository, FakeOllama(), top_k=2, minimum=0.5)  # type: ignore[arg-type]
    answer = await rag.answer("Hvad kræver NIS2?")
    assert "[nis2.md]" in answer


async def test_pdf_ingestion_preserves_human_page_number(tmp_path: Path) -> None:
    root = tmp_path / "documents"
    root.mkdir()
    write_text_pdf(root / "source.pdf")
    database = Database(tmp_path / "db.sqlite")
    await database.migrate()
    repository = DocumentRepository(database)
    service = IngestionService(
        repository,
        FakeOllama(),  # type: ignore[arg-type]
        root,
        max_bytes=10000,
        max_pages=10,
        chunk_chars=100,
        overlap_chars=10,
    )
    report = await service.ingest_all()
    chunks = await repository.all_chunks("embeddinggemma")
    assert report.indexed == 1 and chunks[0].page_start == 1
    assert "NIS2 source" in chunks[0].content


async def test_no_evidence_is_honest(tmp_path: Path) -> None:
    database = Database(tmp_path / "db.sqlite")
    await database.migrate()
    rag = RagService(DocumentRepository(database), FakeOllama(), minimum=0.9)  # type: ignore[arg-type]
    assert "ikke tilstrækkeligt belæg" in await rag.answer("ukendt")


async def test_failed_reindex_preserves_old_index(tmp_path: Path) -> None:
    root = tmp_path / "documents"
    root.mkdir()
    path = root / "a.txt"
    path.write_text("NIS2 gammel tekst som er lang nok.", encoding="utf-8")
    database = Database(tmp_path / "db.sqlite")
    await database.migrate()
    repository = DocumentRepository(database)
    good = IngestionService(
        repository,
        FakeOllama(),
        root,
        max_bytes=10000,
        max_pages=10,
        chunk_chars=100,
        overlap_chars=10,
    )  # type: ignore[arg-type]
    await good.ingest_all()
    path.write_text("NIS2 ny tekst som også er lang nok.", encoding="utf-8")

    class Failing(FakeOllama):
        async def embed(self, texts: list[str]) -> list[list[float]]:
            raise RuntimeError("fake embed failure")

    bad = IngestionService(
        repository,
        Failing(),
        root,
        max_bytes=10000,
        max_pages=10,
        chunk_chars=100,
        overlap_chars=10,
    )  # type: ignore[arg-type]
    report = await bad.ingest_all()
    chunks = await repository.all_chunks("embeddinggemma")
    assert report.errors and "gammel" in chunks[0].content


def test_chunking_preserves_page_and_overlap() -> None:
    chunks = chunk_pages([SourcePage("word " * 100, 7)], 100, 20)
    assert len(chunks) > 1
    assert all(chunk["page_start"] == 7 for chunk in chunks)


def test_embedding_roundtrip_and_similarity() -> None:
    packed = pack_embedding([0.1, 0.2, 0.3])
    unpacked = unpack_embedding(packed, 3)
    assert similarity(unpacked, unpacked) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        unpack_embedding(packed, 2)


def test_symlink_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    link = root / "escape.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Symlinks are unavailable")
    files, errors = safe_files(root, 1000)
    assert files == [] and errors


def test_oversized_file_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "large.txt").write_text("x" * 101, encoding="utf-8")
    files, errors = safe_files(root, 100)
    assert files == [] and errors


async def test_empty_pdf_reports_ocr_error(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with (root / "scan.pdf").open("wb") as stream:
        writer.write(stream)
    files, errors = safe_files(root, 10000)
    assert len(files) == 1 and not errors
    database = Database(tmp_path / "db.sqlite")
    await database.migrate()
    service = IngestionService(
        DocumentRepository(database),
        FakeOllama(),  # type: ignore[arg-type]
        root,
        max_bytes=10000,
        max_pages=10,
        chunk_chars=100,
        overlap_chars=10,
    )
    report = await service.ingest_all()
    assert report.indexed == 0 and "OCR" in report.errors[0]


async def test_document_cascade_delete(tmp_path: Path) -> None:
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
                "content": "x",
                "page_start": None,
                "page_end": None,
                "embedding": pack_embedding([1.0]),
                "embedding_dimensions": 1,
            }
        ],
        indexed_at=datetime.now(UTC),
    )
    await repository.replace(
        display_name="a.txt",
        relative_path="a.txt",
        sha256="two",
        file_type="txt",
        page_count=None,
        embed_model="e",
        chunks=[
            {
                "content": "y",
                "page_start": None,
                "page_end": None,
                "embedding": pack_embedding([1.0]),
                "embedding_dimensions": 1,
            }
        ],
        indexed_at=datetime.now(UTC),
    )
    chunks = await repository.all_chunks("e")
    assert len(chunks) == 1 and chunks[0].content == "y"
