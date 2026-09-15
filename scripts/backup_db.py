#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from secmate.config import Settings  # noqa: E402
from secmate.repositories.database import Database, backup_database  # noqa: E402


async def run() -> None:
    settings = Settings.from_env(require_discord=False)
    database = Database(settings.database_path)
    await database.migrate()
    path = await backup_database(database, settings.backup_path)
    print(f"Verificeret backup oprettet: {path.name}")


if __name__ == "__main__":
    asyncio.run(run())
