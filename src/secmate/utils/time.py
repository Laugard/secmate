from __future__ import annotations

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from secmate.errors import ValidationError


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def local_deadline_to_utc(date_text: str, time_text: str | None, timezone: ZoneInfo) -> datetime:
    try:
        day = date.fromisoformat(date_text)
        clock = time.fromisoformat(time_text or "23:59")
    except ValueError as exc:
        raise ValidationError("Dato/tid skal have formatet YYYY-MM-DD og HH:MM") from exc
    local = datetime.combine(day, clock, timezone)
    roundtrip = local.astimezone(UTC).astimezone(timezone)
    if roundtrip.replace(fold=local.fold) != local:
        raise ValidationError("Tidspunktet findes ikke på grund af skift til sommertid")
    return local.astimezone(UTC)
