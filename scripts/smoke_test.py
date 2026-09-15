#!/usr/bin/env python3
"""Network-free smoke test for config, database, persistence, and backup."""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from secmate.repositories.database import Database, MemoryRepository, backup_database  # noqa: E402


async def run() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        database = Database(root / "secmate.db", ROOT / "migrations")
        await database.migrate()
        item = await MemoryRepository(database).add("smoke-guild", "ufølsom smoke-note", 1)
        assert any(
            memory.id == item.id
            for memory in await MemoryRepository(database).list_active("smoke-guild")
        )
        backup = await backup_database(database, root / "backups")
        assert backup.exists() and await Database(backup, ROOT / "migrations").integrity_check()
    print("Smoke test: OK")


if __name__ == "__main__":
    asyncio.run(run())
