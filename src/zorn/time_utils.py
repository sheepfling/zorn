from __future__ import annotations

from datetime import UTC, datetime, timedelta


def utc_now() -> datetime:
    return datetime.now(tz=UTC)
####


def to_iso(value: datetime) -> str:
    resolved = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return resolved.astimezone(UTC).isoformat().replace("+00:00", "Z")
####


def parse_iso_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    ####
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    ####
    if not isinstance(value, str):
        return None
    ####
    cleaned = value.strip()
    if not cleaned:
        return None
    ####
    if cleaned.endswith("Z"):
        cleaned = f"{cleaned[:-1]}+00:00"
    ####
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    ####
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
####


def expiry_from_ttl_seconds(ttl_seconds: int | None) -> datetime | None:
    if ttl_seconds is None:
        return None
    ####
    return utc_now() + timedelta(seconds=ttl_seconds)
####
