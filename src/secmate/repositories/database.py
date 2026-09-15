"""SQLite connection, migration, repositories, cleanup, and online backup."""

from __future__ import annotations

import sqlite3
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

from secmate.utils.ids import public_id
from secmate.utils.time import utc_text


@dataclass(frozen=True, slots=True)
class Memory:
    id: str
    guild_id: str
    content: str
    created_at_utc: str
    expires_at_utc: str


@dataclass(frozen=True, slots=True)
class Deadline:
    id: str
    guild_id: str
    title: str
    due_at_utc: str
    status: str
    created_at_utc: str
    completed_at_utc: str | None


@dataclass(frozen=True, slots=True)
class ChunkRecord:
    id: str
    document_id: str
    display_name: str
    chunk_index: int
    page_start: int | None
    page_end: int | None
    content: str
    embedding: bytes
    embedding_dimensions: int
    embed_model: str


class Database:
    def __init__(self, path: Path, migrations_path: Path | None = None) -> None:
        self.path = path
        self.migrations_path = migrations_path or Path(__file__).parents[3] / "migrations"

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[aiosqlite.Connection]:
        connection = await aiosqlite.connect(self.path)
        connection.row_factory = aiosqlite.Row
        await connection.execute("PRAGMA foreign_keys=ON")
        await connection.execute("PRAGMA busy_timeout=5000")
        await connection.execute("PRAGMA journal_mode=WAL")
        try:
            yield connection
        finally:
            await connection.close()

    async def migrate(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with self.connect() as db:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at_utc TEXT NOT NULL)"
            )
            await db.commit()
            applied = {
                row[0]
                for row in await (
                    await db.execute("SELECT version FROM schema_migrations")
                ).fetchall()
            }
            for migration in sorted(self.migrations_path.glob("[0-9][0-9][0-9]_*.sql")):
                version = int(migration.name.split("_", 1)[0])
                if version in applied:
                    continue
                script = migration.read_text(encoding="utf-8")
                timestamp = utc_text(datetime.now(UTC))
                wrapped = (
                    "BEGIN IMMEDIATE;\n"
                    + script
                    + "\n"
                    + "INSERT INTO schema_migrations(version,name,applied_at_utc) VALUES("
                    + f"{version},'{migration.name.replace(chr(39), chr(39) * 2)}','{timestamp}');\nCOMMIT;"
                )
                try:
                    await db.executescript(wrapped)
                except Exception:
                    await db.rollback()
                    raise

    async def integrity_check(self) -> bool:
        async with self.connect() as db:
            row = await (await db.execute("PRAGMA integrity_check")).fetchone()
            return bool(row and row[0] == "ok")


class MemoryRepository:
    def __init__(self, database: Database, now: Callable[[], datetime] | None = None) -> None:
        self.database = database
        self.now = now or (lambda: datetime.now(UTC))

    async def add(self, guild_id: str, content: str, retention_days: int) -> Memory:
        now = self.now()
        item = Memory(
            public_id("mem"),
            guild_id,
            content,
            utc_text(now),
            utc_text(now + timedelta(days=retention_days)),
        )
        async with self.database.connect() as db:
            await db.execute(
                "INSERT INTO memories VALUES(?,?,?,?,?)",
                (item.id, item.guild_id, item.content, item.created_at_utc, item.expires_at_utc),
            )
            await db.commit()
        return item

    async def list_active(self, guild_id: str, limit: int = 50) -> list[Memory]:
        async with self.database.connect() as db:
            rows = await (
                await db.execute(
                    "SELECT * FROM memories WHERE guild_id=? AND expires_at_utc>=? ORDER BY created_at_utc DESC LIMIT ?",
                    (guild_id, utc_text(self.now()), limit),
                )
            ).fetchall()
        return [Memory(**dict(row)) for row in rows]

    async def delete(self, guild_id: str, memory_id: str) -> bool:
        async with self.database.connect() as db:
            cursor = await db.execute(
                "DELETE FROM memories WHERE guild_id=? AND id=?", (guild_id, memory_id)
            )
            await db.commit()
            return cursor.rowcount == 1


class DeadlineRepository:
    def __init__(self, database: Database, now: Callable[[], datetime] | None = None) -> None:
        self.database = database
        self.now = now or (lambda: datetime.now(UTC))

    async def add(self, guild_id: str, title: str, due_at: datetime) -> Deadline:
        item = Deadline(
            public_id("due"),
            guild_id,
            title,
            utc_text(due_at),
            "pending",
            utc_text(self.now()),
            None,
        )
        async with self.database.connect() as db:
            await db.execute(
                "INSERT INTO deadlines VALUES(?,?,?,?,?,?,?)",
                (
                    item.id,
                    item.guild_id,
                    item.title,
                    item.due_at_utc,
                    item.status,
                    item.created_at_utc,
                    item.completed_at_utc,
                ),
            )
            await db.commit()
        return item

    async def list_pending(
        self, guild_id: str, limit: int = 50, until: datetime | None = None
    ) -> list[Deadline]:
        sql = "SELECT * FROM deadlines WHERE guild_id=? AND status='pending'"
        args: list[Any] = [guild_id]
        if until is not None:
            sql += " AND due_at_utc<=?"
            args.append(utc_text(until))
        sql += " ORDER BY due_at_utc LIMIT ?"
        args.append(limit)
        async with self.database.connect() as db:
            rows = await (await db.execute(sql, args)).fetchall()
        return [Deadline(**dict(row)) for row in rows]

    async def complete(self, guild_id: str, deadline_id: str) -> bool:
        async with self.database.connect() as db:
            cursor = await db.execute(
                "UPDATE deadlines SET status='completed',completed_at_utc=? WHERE guild_id=? AND id=? AND status='pending'",
                (utc_text(self.now()), guild_id, deadline_id),
            )
            await db.commit()
            return cursor.rowcount == 1

    async def delete(self, guild_id: str, deadline_id: str) -> bool:
        async with self.database.connect() as db:
            cursor = await db.execute(
                "DELETE FROM deadlines WHERE guild_id=? AND id=?", (guild_id, deadline_id)
            )
            await db.commit()
            return cursor.rowcount == 1


class JobRepository:
    def __init__(self, database: Database, now: Callable[[], datetime] | None = None) -> None:
        self.database = database
        self.now = now or (lambda: datetime.now(UTC))

    async def claim(self, job_name: str, guild_id: str, local_date: str) -> str | None:
        job_id = public_id("job")
        try:
            async with self.database.connect() as db:
                await db.execute(
                    "INSERT INTO job_runs(id,job_name,guild_id,local_date,status,attempts,claimed_at_utc) VALUES(?,?,?,?, 'claimed',1,?)",
                    (job_id, job_name, guild_id, local_date, utc_text(self.now())),
                )
                await db.commit()
            return job_id
        except sqlite3.IntegrityError:
            return None

    async def finish(self, job_id: str, succeeded: bool, error_code: str | None = None) -> None:
        status = "succeeded" if succeeded else "failed"
        async with self.database.connect() as db:
            await db.execute(
                "UPDATE job_runs SET status=?,finished_at_utc=?,last_error_code=? WHERE id=?",
                (status, utc_text(self.now()), error_code, job_id),
            )
            await db.commit()


class DocumentRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def current_signature(self, relative_path: str) -> tuple[str, str] | None:
        async with self.database.connect() as db:
            row = await (
                await db.execute(
                    "SELECT sha256,embed_model FROM documents WHERE relative_path=?",
                    (relative_path,),
                )
            ).fetchone()
        return (row[0], row[1]) if row else None

    async def replace(
        self,
        *,
        display_name: str,
        relative_path: str,
        sha256: str,
        file_type: str,
        page_count: int | None,
        embed_model: str,
        chunks: Sequence[dict[str, Any]],
        indexed_at: datetime,
    ) -> None:
        document_id = public_id("doc")
        async with self.database.connect() as db:
            await db.execute("BEGIN IMMEDIATE")
            old = await (
                await db.execute("SELECT id FROM documents WHERE relative_path=?", (relative_path,))
            ).fetchone()
            if old:
                await db.execute("DELETE FROM documents WHERE id=?", (old[0],))
            await db.execute(
                "INSERT INTO documents VALUES(?,?,?,?,?,?,?,?)",
                (
                    document_id,
                    display_name,
                    relative_path,
                    sha256,
                    file_type,
                    page_count,
                    embed_model,
                    utc_text(indexed_at),
                ),
            )
            for index, chunk in enumerate(chunks):
                await db.execute(
                    "INSERT INTO document_chunks VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        public_id("chk"),
                        document_id,
                        index,
                        chunk.get("page_start"),
                        chunk.get("page_end"),
                        chunk["content"],
                        chunk["embedding"],
                        chunk["embedding_dimensions"],
                        embed_model,
                    ),
                )
            await db.commit()

    async def all_chunks(self, embed_model: str) -> list[ChunkRecord]:
        async with self.database.connect() as db:
            rows = await (
                await db.execute(
                    "SELECT c.id,c.document_id,d.display_name,c.chunk_index,c.page_start,c.page_end,c.content,c.embedding,c.embedding_dimensions,c.embed_model FROM document_chunks c JOIN documents d ON d.id=c.document_id WHERE c.embed_model=?",
                    (embed_model,),
                )
            ).fetchall()
        return [ChunkRecord(**dict(row)) for row in rows]

    async def counts(self) -> tuple[int, int]:
        async with self.database.connect() as db:
            document_row = await (await db.execute("SELECT count(*) FROM documents")).fetchone()
            chunk_row = await (await db.execute("SELECT count(*) FROM document_chunks")).fetchone()
            if document_row is None or chunk_row is None:
                raise RuntimeError("Kunne ikke tælle dokumentindekset")
            documents = document_row[0]
            chunks = chunk_row[0]
        return int(documents), int(chunks)

    async def sample_chunks(self, limit: int = 1) -> list[ChunkRecord]:
        async with self.database.connect() as db:
            rows = await (
                await db.execute(
                    "SELECT c.id,c.document_id,d.display_name,c.chunk_index,c.page_start,"
                    "c.page_end,c.content,c.embedding,c.embedding_dimensions,c.embed_model "
                    "FROM document_chunks c JOIN documents d ON d.id=c.document_id "
                    "ORDER BY RANDOM() LIMIT ?",
                    (limit,),
                )
            ).fetchall()
        return [ChunkRecord(**dict(row)) for row in rows]


class NewsRepository:
    def __init__(self, database: Database, now: Callable[[], datetime] | None = None) -> None:
        self.database = database
        self.now = now or (lambda: datetime.now(UTC))

    async def insert(self, item: dict[str, Any]) -> bool:
        try:
            async with self.database.connect() as db:
                await db.execute(
                    "INSERT INTO news_items VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        item["id"],
                        item["dedupe_key"],
                        item["source_name"],
                        item["title"],
                        item["url"],
                        item.get("published_at_utc"),
                        item["fetched_at_utc"],
                        item["category"],
                        item["summary_da"],
                        item["study_relevance_da"],
                        item.get("confidence"),
                        None,
                        item["expires_at_utc"],
                    ),
                )
                await db.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    async def exists(self, dedupe_key: str) -> bool:
        async with self.database.connect() as db:
            row = await (
                await db.execute("SELECT 1 FROM news_items WHERE dedupe_key=?", (dedupe_key,))
            ).fetchone()
        return row is not None

    async def latest(self, category: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        sql = "SELECT * FROM news_items"
        args: list[Any] = []
        if category and category != "alle":
            sql += " WHERE category=?"
            args.append(category)
        sql += " ORDER BY COALESCE(published_at_utc,fetched_at_utc) DESC LIMIT ?"
        args.append(limit)
        async with self.database.connect() as db:
            rows = await (await db.execute(sql, args)).fetchall()
        return [dict(row) for row in rows]

    async def mark_posted(self, item_id: str) -> None:
        async with self.database.connect() as db:
            await db.execute(
                "UPDATE news_items SET posted_at_utc=? WHERE id=?", (utc_text(self.now()), item_id)
            )
            await db.commit()


async def cleanup(
    database: Database, now: datetime, completed_deadline_days: int
) -> dict[str, int]:
    cutoff_completed = utc_text(now - timedelta(days=completed_deadline_days))
    cutoff_jobs = utc_text(now - timedelta(days=90))
    counts: dict[str, int] = {}
    async with database.connect() as db:
        for name, sql, args in (
            ("memories", "DELETE FROM memories WHERE expires_at_utc<?", (utc_text(now),)),
            (
                "deadlines",
                "DELETE FROM deadlines WHERE status='completed' AND completed_at_utc<?",
                (cutoff_completed,),
            ),
            ("news", "DELETE FROM news_items WHERE expires_at_utc<?", (utc_text(now),)),
            ("jobs", "DELETE FROM job_runs WHERE claimed_at_utc<?", (cutoff_jobs,)),
        ):
            cursor = await db.execute(sql, args)
            counts[name] = cursor.rowcount
        await db.execute("PRAGMA optimize")
        await db.commit()
    return counts


async def backup_database(
    database: Database, backup_dir: Path, keep: int = 7, now: datetime | None = None
) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%d-%H%M%S")
    destination = backup_dir / f"secmate-{stamp}.db"
    source = sqlite3.connect(database.path)
    target = sqlite3.connect(destination)
    try:
        source.backup(target)
        result = target.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise RuntimeError("Backup integrity check fejlede")
    finally:
        target.close()
        source.close()
    backups = sorted(backup_dir.glob("secmate-*.db"), reverse=True)
    for old in backups[keep:]:
        old.unlink()
    return destination
