from __future__ import annotations

from pathlib import Path

import pytest

from secmate.config import Settings, validate_ollama_host
from secmate.errors import ConfigurationError, ValidationError
from secmate.logging_config import redact
from secmate.utils.discord_text import split_message
from secmate.utils.time import local_deadline_to_utc
from secmate.utils.validation import bounded_text, reject_likely_secret


def base_env(tmp_path: Path) -> dict[str, str]:
    return {
        "DISCORD_TOKEN": "fake-for-tests",
        "DISCORD_TEST_GUILD_ID": "123",
        "DATABASE_PATH": str(tmp_path / "data" / "db.sqlite"),
        "DOCUMENTS_PATH": str(tmp_path / "docs"),
        "BACKUP_PATH": str(tmp_path / "backups"),
        "LOG_PATH": str(tmp_path / "logs" / "app.log"),
    }


def test_missing_token_fails_fast(tmp_path: Path) -> None:
    env = base_env(tmp_path)
    del env["DISCORD_TOKEN"]
    with pytest.raises(ConfigurationError, match="DISCORD_TOKEN"):
        Settings.from_env(env)


@pytest.mark.parametrize(
    "host", ["http://0.0.0.0:11434", "https://example.com", "http://192.168.1.2:11434"]
)
def test_remote_ollama_rejected(host: str) -> None:
    with pytest.raises(ConfigurationError):
        validate_ollama_host(host)


@pytest.mark.parametrize(
    "host", ["http://127.0.0.1:11434", "http://localhost:11434", "http://[::1]:11434"]
)
def test_loopback_ollama_allowed(host: str) -> None:
    assert validate_ollama_host(host) == host


def test_directories_are_created(tmp_path: Path) -> None:
    settings = Settings.from_env(base_env(tmp_path))
    settings.ensure_directories()
    assert settings.documents_path.is_dir()
    assert settings.backup_path.is_dir()


def test_optional_channels_are_disabled(tmp_path: Path) -> None:
    settings = Settings.from_env(base_env(tmp_path))
    assert settings.digest_channel_id is None
    assert not any(settings.news_channel_ids.values())


def test_cloud_model_tag_is_rejected(tmp_path: Path) -> None:
    env = base_env(tmp_path)
    env["OLLAMA_CHAT_MODEL"] = "qwen3:cloud"
    with pytest.raises(ConfigurationError):
        Settings.from_env(env)


def test_secret_redaction_does_not_log_value() -> None:
    secret = "M" + "a" * 25 + ".abcdef." + "b" * 25
    assert secret not in redact(f"token={secret}")
    assert "[REDACTED]" in redact(f"token={secret}")


def test_input_limits_and_secret_rejection() -> None:
    with pytest.raises(ValidationError):
        bounded_text("x" * 11, 10, "Tekst")
    with pytest.raises(ValidationError):
        reject_likely_secret("api_key=abcdefghijk")


def test_discord_split_never_exceeds_limit() -> None:
    parts = split_message("word " * 1000, 100)
    assert len(parts) > 1
    assert all(len(part) <= 100 for part in parts)


def test_date_conversion_and_dst_gap(tmp_path: Path) -> None:
    timezone = Settings.from_env(base_env(tmp_path)).timezone
    value = local_deadline_to_utc("2026-01-15", "10:00", timezone)
    assert value.hour == 9
    with pytest.raises(ValidationError):
        local_deadline_to_utc("2026-03-29", "02:30", timezone)
