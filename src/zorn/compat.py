from __future__ import annotations

import re
from typing import Any

from .time_utils import to_iso

OBJECT_PATH_PATTERN = re.compile(r"^[a-zA-Z0-9/_=\-.]+$")


ENTITY_ALWAYS_INCLUDED_COMPONENTS: set[str] = {"entityId"}


def first_present(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
        ####
    ####
    return None
####


def bool_from_payload(payload: dict[str, Any], key: str, default: bool = False) -> bool:
    value = payload.get(key)
    if isinstance(value, bool):
        return value
    ####
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        ####
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
        ####
    ####
    return default
####


def int_from_payload(payload: dict[str, Any], *keys: str, default: int = 0) -> int:
    raw = first_present(payload, *keys)
    if raw is None:
        return default
    ####
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default
    ####
####


def milliseconds_to_seconds(value: int | float | None, default_seconds: float) -> float:
    if value is None:
        return default_seconds
    ####
    return max(float(value) / 1000.0, 0.001)
####


def heartbeat_seconds_from_payload(
    payload: dict[str, Any],
    *,
    default_seconds: float,
    millisecond_keys: tuple[str, ...],
    second_keys: tuple[str, ...] = ("heartbeatSeconds",),
) -> float:
    for key in millisecond_keys:
        if key in payload:
            return milliseconds_to_seconds(int_from_payload(payload, key, default=int(default_seconds * 1000)), default_seconds)
        ####
    ####
    for key in second_keys:
        if key in payload:
            try:
                return max(float(payload[key]), 0.001)
            except (TypeError, ValueError):
                return default_seconds
            ####
        ####
    ####
    return default_seconds
####


def sequence_token(value: object, default: int = 0) -> int:
    if value is None:
        return default
    ####
    if isinstance(value, int):
        return max(value, 0)
    ####
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return default
        ####
        try:
            return max(int(cleaned), 0)
        except ValueError:
            return default
        ####
    ####
    return default
####


def select_entity_components(entity: dict[str, Any], components: list[str] | None) -> dict[str, Any]:
    if not components:
        return dict(entity)
    ####
    selected: dict[str, Any] = {}
    for key in ENTITY_ALWAYS_INCLUDED_COMPONENTS | set(components):
        if key in entity:
            selected[key] = entity[key]
        ####
    ####
    return selected
####


def object_metadata_wire(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "content_identifier": {
            "path": metadata["objectPath"],
            "checksum": metadata["checksumSha256"],
        },
        "size_bytes": metadata["sizeBytes"],
        "last_updated_at": metadata["updatedTime"],
        "expiry_time": metadata.get("expiryTime"),
        "objectPath": metadata["objectPath"],
        "checksumSha256": metadata["checksumSha256"],
        "sizeBytes": metadata["sizeBytes"],
        "contentType": metadata["contentType"],
        "createdTime": metadata["createdTime"],
        "updatedTime": metadata["updatedTime"],
        "metadata": metadata.get("metadata") or {},
    }
####


def object_metadata_headers(metadata: dict[str, Any]) -> dict[str, str]:
    headers = {
        "Content-Length": str(metadata["sizeBytes"]),
        "Content-Type": str(metadata["contentType"]),
        "ETag": str(metadata["checksumSha256"]),
        "Path": str(metadata["objectPath"]),
        "Checksum": str(metadata["checksumSha256"]),
        "Last-Modified": str(metadata["updatedTime"]),
        "X-Checksum-Sha256": str(metadata["checksumSha256"]),
        "X-Object-Path": str(metadata["objectPath"]),
    }
    expiry_time = metadata.get("expiryTime")
    if isinstance(expiry_time, str) and expiry_time:
        headers["Expires"] = expiry_time
    ####
    return headers
####


def validate_object_path(object_path: str) -> str:
    cleaned = object_path.strip().lstrip("/")
    if not cleaned:
        raise ValueError("object path cannot be empty")
    ####
    if ".." in cleaned.split("/"):
        raise ValueError("object path must be relative and cannot include '..'")
    ####
    if not OBJECT_PATH_PATTERN.fullmatch(cleaned):
        raise ValueError("object path must match ^[a-zA-Z0-9/_=\\-.]+$")
    ####
    return cleaned
####


def ttl_header_to_seconds(raw_ttl: str | None) -> int | None:
    if raw_ttl is None or not raw_ttl.strip():
        return None
    ####
    try:
        ttl_value = int(raw_ttl)
    except ValueError as exc:
        raise ValueError("Time-To-Live must be an integer") from exc
    ####
    if ttl_value < 0:
        raise ValueError("Time-To-Live must be non-negative")
    ####
    if ttl_value >= 1_000_000_000:
        return max(ttl_value // 1_000_000_000, 1)
    ####
    return ttl_value
####


def datetime_dict_value(value: object) -> str | None:
    if hasattr(value, "tzinfo"):
        return to_iso(value)  # type: ignore[arg-type]
    ####
    return value if isinstance(value, str) and value else None
####
