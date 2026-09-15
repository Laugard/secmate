"""Logging that avoids retaining command/document content and masks secrets."""

from __future__ import annotations

import logging
import re
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

TOKEN_PATTERNS = (
    re.compile(r"(?i)(discord_token|token|api[_-]?key|authorization)(\s*[=:]\s*)([^\s,;]+)"),
    re.compile(r"[MN][A-Za-z\d_-]{20,}\.[A-Za-z\d_-]{6,}\.[A-Za-z\d_-]{20,}"),
)


def redact(text: str) -> str:
    result = text
    for pattern in TOKEN_PATTERNS:
        if pattern.groups >= 3:
            result = pattern.sub(r"\1\2[REDACTED]", result)
        else:
            result = pattern.sub("[REDACTED]", result)
    return result


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(str(record.msg))
        record.args = ()
        return True


def configure_logging(path: Path, level: str = "INFO", retention_days: int = 14) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = TimedRotatingFileHandler(
        path, when="midnight", backupCount=retention_days, encoding="utf-8"
    )
    handler.addFilter(RedactingFilter())
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level, logging.INFO))
