"""Logging that avoids retaining command/document content and masks secrets."""

from __future__ import annotations

import logging
import re
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

TOKEN_PATTERNS = (
    re.compile(r"(?i)(discord_token|token|api[_-]?key|authorization)(\s*[=:]\s*)([^\s,;]+)"),
    re.compile(r"[MN][A-Za-z\d_-]{20,}\.[A-Za-z\d_-]{6,}\.[A-Za-z\d_-]{20,}"),
)
FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def redact(text: str) -> str:
    result = text
    for pattern in TOKEN_PATTERNS:
        if pattern.groups >= 3:
            result = pattern.sub(r"\1\2[REDACTED]", result)
        else:
            result = pattern.sub("[REDACTED]", result)
    return result


class RedactingFilter(logging.Filter):
    """Redact the fully formatted message: %-arguments are values too, so they are rendered first."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = ()
        return True


def configure_logging(path: Path, level: str = "INFO", retention_days: int = 14) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = TimedRotatingFileHandler(
        path, when="midnight", backupCount=retention_days, encoding="utf-8"
    )
    # The operator runs the bot in a terminal; warnings must be visible there, not only on disk.
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)
    root = logging.getLogger()
    root.handlers.clear()
    for handler in (file_handler, console_handler):
        handler.addFilter(RedactingFilter())
        handler.setFormatter(logging.Formatter(FORMAT))
        root.addHandler(handler)
    root.setLevel(getattr(logging, level, logging.INFO))
