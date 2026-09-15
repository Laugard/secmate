#!/usr/bin/env python3
"""Offline-first configuration and local dependency diagnostics."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from secmate.config import Settings  # noqa: E402
from secmate.errors import ConfigurationError  # noqa: E402
from secmate.services.ollama_service import OllamaService  # noqa: E402


async def run() -> int:
    print(f"Python: {'OK' if sys.version_info[:2] == (3, 12) else 'KRÆVER 3.12'}")
    try:
        settings = Settings.from_env()
    except ConfigurationError as exc:
        print(f"Konfiguration: FEJL — {exc}")
        print("Næste trin: kopiér .env.example til .env og udfyld de manglende nøgler lokalt.")
        return 1
    settings.ensure_directories()
    print("Konfiguration: OK (værdier vises ikke)")
    for label, path in (
        ("Database", settings.database_path.parent),
        ("Dokumenter", settings.documents_path),
        ("Backups", settings.backup_path),
        ("Logs", settings.log_path.parent),
    ):
        print(f"{label}: {'OK' if path.exists() and path.is_dir() else 'FEJL'}")
    try:
        health = await OllamaService(
            settings.ollama_host, settings.ollama_chat_model, settings.ollama_embed_model, 5
        ).health()
        print(f"Ollama API: {'OK' if health['api'] else 'FEJL'}")
        if not health["chat_model"]:
            print(f"Næste trin: ollama pull {settings.ollama_chat_model}")
        if not health["embed_model"]:
            print(f"Næste trin: ollama pull {settings.ollama_embed_model}")
    except Exception:
        print("Ollama: ikke tilgængelig. Næste trin: start Ollama lokalt og kør doctor igen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
