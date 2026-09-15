from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from secmate.repositories.database import (
    Database,
    DeadlineRepository,
    JobRepository,
    MemoryRepository,
    backup_database,
    cleanup,
)


@pytest.fixture
async def database(tmp_path: Path) -> Database:
    db = Database(tmp_path / "secmate.db")
    await db.migrate()
    return db


async def test_migrations_are_idempotent(database: Database) -> None:
    await database.migrate()
    async with database.connect() as db:
        rows = await (await db.execute("SELECT version FROM schema_migrations")).fetchall()
    assert [row[0] for row in rows] == [1]


async def test_memory_persists_and_is_guild_isolated(database: Database) -> None:
    repo = MemoryRepository(database)
    item = await repo.add("guild-a", "Robert'); DROP TABLE memories;--", 90)
    assert [memory.id for memory in await MemoryRepository(database).list_active("guild-a")] == [
        item.id
    ]
    assert await repo.list_active("guild-b") == []
    async with database.connect() as db:
        assert (await (await db.execute("SELECT count(*) FROM memories")).fetchone())[0] == 1


async def test_cleanup_boundary(database: Database) -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    expired = MemoryRepository(database, lambda: now - timedelta(days=2))
    active = MemoryRepository(database, lambda: now)
    await expired.add("g", "old", 1)
    keep = await active.add("g", "new", 1)
    result = await cleanup(database, now, 30)
    assert result["memories"] == 1
    assert [item.id for item in await active.list_active("g")] == [keep.id]


async def test_deadline_crud_and_isolation(database: Database) -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    repo = DeadlineRepository(database, lambda: now)
    item = await repo.add("a", "Eksamen", now + timedelta(days=1))
    assert len(await repo.list_pending("a")) == 1
    assert await repo.list_pending("b") == []
    assert await repo.complete("b", item.id) is False
    assert await repo.complete("a", item.id) is True
    assert await repo.delete("a", item.id) is True


async def test_atomic_job_claim(database: Database) -> None:
    repo = JobRepository(database)
    results = await asyncio.gather(*(repo.claim("digest", "g", "2026-01-01") for _ in range(10)))
    assert sum(result is not None for result in results) == 1


async def test_online_backup_of_wal_database(database: Database, tmp_path: Path) -> None:
    await MemoryRepository(database).add("g", "persist", 30)
    backup = await backup_database(database, tmp_path / "backups")
    assert await Database(backup).integrity_check()
    assert len(await MemoryRepository(Database(backup)).list_active("g")) == 1


async def test_backup_rotation(database: Database, tmp_path: Path) -> None:
    directory = tmp_path / "backups"
    for index in range(9):
        await backup_database(
            database, directory, keep=7, now=datetime(2026, 1, 1, 0, 0, index, tzinfo=UTC)
        )
    assert len(list(directory.glob("secmate-*.db"))) == 7
