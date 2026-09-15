from __future__ import annotations

import re

from secmate.errors import ValidationError

SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)(?:password|passwd|api[_-]?key|token)\s*[:=]\s*\S{8,}"),
    re.compile(r"[MN][A-Za-z\d_-]{20,}\.[A-Za-z\d_-]{6,}\.[A-Za-z\d_-]{20,}"),
)


def bounded_text(value: str, maximum: int, label: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(f"{label} må ikke være tom")
    if len(cleaned) > maximum:
        raise ValidationError(f"{label} må højst være {maximum} tegn")
    return cleaned


def reject_likely_secret(value: str) -> None:
    if any(pattern.search(value) for pattern in SECRET_PATTERNS):
        raise ValidationError("Teksten ligner en adgangskode eller token og må ikke gemmes")
