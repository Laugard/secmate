"""Typed, fail-closed configuration sourced from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

from secmate.errors import ConfigurationError


def _integer(env: dict[str, str], key: str, default: int, *, minimum: int = 0) -> int:
    raw = env.get(key, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{key} skal være et heltal") from exc
    if value < minimum:
        raise ConfigurationError(f"{key} skal være mindst {minimum}")
    return value


def _floating(env: dict[str, str], key: str, default: float, *, minimum: float = 0) -> float:
    raw = env.get(key, str(default)).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{key} skal være et tal") from exc
    if value < minimum:
        raise ConfigurationError(f"{key} skal være mindst {minimum}")
    return value


def _optional_id(env: dict[str, str], key: str) -> int | None:
    raw = env.get(key, "").strip()
    if not raw:
        return None
    if not raw.isdecimal() or int(raw) <= 0:
        raise ConfigurationError(f"{key} skal være et positivt Discord-ID")
    return int(raw)


def _clock(value: str, key: str) -> str:
    parts = value.split(":")
    if len(parts) != 2 or not all(part.isdecimal() for part in parts):
        raise ConfigurationError(f"{key} skal have formatet HH:MM")
    hour, minute = map(int, parts)
    if hour > 23 or minute > 59:
        raise ConfigurationError(f"{key} skal være et gyldigt klokkeslæt")
    return f"{hour:02d}:{minute:02d}"


def validate_ollama_host(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ConfigurationError("OLLAMA_HOST skal være en lokal HTTP-loopback-adresse")
    if (
        parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ConfigurationError("OLLAMA_HOST må kun indeholde lokal host og port")
    return value.rstrip("/")


@dataclass(frozen=True, slots=True)
class Settings:
    discord_token: str
    discord_test_guild_id: int
    database_path: Path
    documents_path: Path
    backup_path: Path
    log_path: Path
    ollama_host: str
    ollama_chat_model: str
    ollama_embed_model: str
    timezone: ZoneInfo
    digest_time_local: str
    news_time_local: str
    digest_channel_id: int | None
    news_channel_ids: dict[str, int | None]
    admin_role_id: int | None
    ollama_timeout: float
    memory_retention_days: int
    completed_deadline_retention_days: int
    news_retention_days: int
    max_prompt_chars: int
    max_memory_chars: int
    max_document_bytes: int
    max_document_pages: int
    rag_chunk_chars: int
    rag_chunk_overlap_chars: int
    rag_top_k: int
    rag_min_similarity: float
    news_feed_urls: tuple[str, ...]
    news_max_items_per_run: int
    news_http_timeout: float
    news_max_response_bytes: int
    log_level: str

    @classmethod
    def from_env(
        cls, values: dict[str, str] | None = None, *, require_discord: bool = True
    ) -> Settings:
        if values is None:
            load_dotenv()
            env = dict(os.environ)
        else:
            env = values
        missing = [
            key
            for key in ("DISCORD_TOKEN", "DISCORD_TEST_GUILD_ID")
            if require_discord and not env.get(key, "").strip()
        ]
        if missing:
            raise ConfigurationError("Manglende indstilling(er): " + ", ".join(missing))
        token = env.get("DISCORD_TOKEN", "").strip()
        guild_raw = env.get("DISCORD_TEST_GUILD_ID", "1").strip()
        if not guild_raw.isdecimal() or int(guild_raw) <= 0:
            raise ConfigurationError("DISCORD_TEST_GUILD_ID skal være et positivt Discord-ID")
        timezone_name = env.get("APP_TIMEZONE", "Europe/Copenhagen")
        try:
            timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ConfigurationError("APP_TIMEZONE er ukendt") from exc
        feeds = tuple(
            item.strip() for item in env.get("NEWS_FEED_URLS", "").split(",") if item.strip()
        )
        if any(urlparse(url).scheme != "https" or not urlparse(url).hostname for url in feeds):
            raise ConfigurationError("NEWS_FEED_URLS må kun indeholde gyldige HTTPS-URL'er")
        chunk_chars = _integer(env, "RAG_CHUNK_CHARS", 1200, minimum=100)
        overlap = _integer(env, "RAG_CHUNK_OVERLAP_CHARS", 180)
        if overlap >= chunk_chars:
            raise ConfigurationError("RAG_CHUNK_OVERLAP_CHARS skal være mindre end RAG_CHUNK_CHARS")
        chat_model = env.get("OLLAMA_CHAT_MODEL", "qwen3:4b").strip()
        embed_model = env.get("OLLAMA_EMBED_MODEL", "embeddinggemma").strip()
        if (
            not chat_model
            or not embed_model
            or any("cloud" in model.lower() for model in (chat_model, embed_model))
        ):
            raise ConfigurationError("Ollama-modeller skal være eksplicitte lokale modeltags")
        return cls(
            discord_token=token,
            discord_test_guild_id=int(guild_raw),
            database_path=Path(env.get("DATABASE_PATH", "data/secmate.db")),
            documents_path=Path(env.get("DOCUMENTS_PATH", "data/documents")),
            backup_path=Path(env.get("BACKUP_PATH", "data/backups")),
            log_path=Path(env.get("LOG_PATH", "logs/secmate.log")),
            ollama_host=validate_ollama_host(env.get("OLLAMA_HOST", "http://127.0.0.1:11434")),
            ollama_chat_model=chat_model,
            ollama_embed_model=embed_model,
            timezone=timezone,
            digest_time_local=_clock(env.get("DAILY_DIGEST_TIME", "09:00"), "DAILY_DIGEST_TIME"),
            news_time_local=_clock(env.get("DAILY_NEWS_TIME", "09:15"), "DAILY_NEWS_TIME"),
            digest_channel_id=_optional_id(env, "DISCORD_DIGEST_CHANNEL_ID"),
            news_channel_ids={
                "sårbarheder": _optional_id(env, "DISCORD_NEWS_VULNERABILITIES_CHANNEL_ID"),
                "cyberangreb": _optional_id(env, "DISCORD_NEWS_ATTACKS_CHANNEL_ID"),
                "ai-security": _optional_id(env, "DISCORD_NEWS_AI_SECURITY_CHANNEL_ID"),
                "lovgivning": _optional_id(env, "DISCORD_NEWS_LAW_CHANNEL_ID"),
                "andet": _optional_id(env, "DISCORD_NEWS_OTHER_CHANNEL_ID"),
            },
            admin_role_id=_optional_id(env, "DISCORD_ADMIN_ROLE_ID"),
            ollama_timeout=_floating(env, "OLLAMA_REQUEST_TIMEOUT_SECONDS", 120, minimum=1),
            memory_retention_days=_integer(env, "MEMORY_RETENTION_DAYS", 90, minimum=1),
            completed_deadline_retention_days=_integer(
                env, "COMPLETED_DEADLINE_RETENTION_DAYS", 30, minimum=1
            ),
            news_retention_days=_integer(env, "NEWS_RETENTION_DAYS", 30, minimum=1),
            max_prompt_chars=_integer(env, "MAX_PROMPT_CHARS", 1500, minimum=1),
            max_memory_chars=_integer(env, "MAX_MEMORY_CHARS", 500, minimum=1),
            max_document_bytes=_integer(env, "MAX_DOCUMENT_MB", 20, minimum=1) * 1024 * 1024,
            max_document_pages=_integer(env, "MAX_DOCUMENT_PAGES", 200, minimum=1),
            rag_chunk_chars=chunk_chars,
            rag_chunk_overlap_chars=overlap,
            rag_top_k=_integer(env, "RAG_TOP_K", 5, minimum=1),
            rag_min_similarity=_floating(env, "RAG_MIN_SIMILARITY", 0.30),
            news_feed_urls=feeds,
            news_max_items_per_run=_integer(env, "NEWS_MAX_ITEMS_PER_RUN", 5, minimum=1),
            news_http_timeout=_floating(env, "NEWS_HTTP_TIMEOUT_SECONDS", 15, minimum=1),
            news_max_response_bytes=_integer(
                env, "NEWS_MAX_RESPONSE_BYTES", 2_000_000, minimum=1024
            ),
            log_level=env.get("LOG_LEVEL", "INFO").upper(),
        )

    def ensure_directories(self) -> None:
        for path in (
            self.database_path.parent,
            self.documents_path,
            self.backup_path,
            self.log_path.parent,
        ):
            path.mkdir(parents=True, exist_ok=True)
