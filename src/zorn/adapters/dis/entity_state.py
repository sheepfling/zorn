from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
import json
import math
from pathlib import Path
from typing import Any, cast

from ...time_utils import to_iso, utc_now


@dataclass(frozen=True, slots=True)
class DisEntityState:
    exercise_id: int
    site_id: int
    application_id: int
    entity_id: int
    force_id: str
    marking: str
    entity_type: dict[str, Any]
    latitude_degrees: float
    longitude_degrees: float
    altitude_hae_meters: float | None
    velocity_east_mps: float | None
    velocity_north_mps: float | None
    velocity_up_mps: float | None
    psi_radians: float | None
    theta_radians: float | None
    phi_radians: float | None
    source_update_time: str
    is_live: bool = True
####


def load_entity_state_jsonl(path: Path) -> list[DisEntityState]:
    states: list[DisEntityState] = []
    for line_number, raw_line in enumerate(path.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        ####
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
        ####
        if not isinstance(payload, dict):
            raise ValueError(f"{path}:{line_number}: expected JSON object")
        ####
        states.append(entity_state_from_payload(payload))
    ####
    return states
####


def entity_state_from_payload(payload: dict[str, Any]) -> DisEntityState:
    entity_identity = _dict(payload, "entity_id", "entityId", "entity")
    world_location = _dict(payload, "world_location", "worldLocation", "location")
    velocity = _dict(payload, "velocity", "linear_velocity", "linearVelocity")
    orientation = _dict(payload, "orientation", "euler")

    return DisEntityState(
        exercise_id=_required_int(payload, "exercise_id", "exerciseId"),
        site_id=_required_int(entity_identity, "site_id", "siteId"),
        application_id=_required_int(entity_identity, "application_id", "applicationId"),
        entity_id=_required_int(entity_identity, "entity_id", "entityId"),
        force_id=str(payload.get("force_id") or payload.get("forceId") or "unknown"),
        marking=str(payload.get("marking") or payload.get("description") or ""),
        entity_type=dict(payload.get("entity_type") or payload.get("entityType") or {}),
        latitude_degrees=_required_float(world_location, "latitude_degrees", "latitudeDegrees", "lat"),
        longitude_degrees=_required_float(world_location, "longitude_degrees", "longitudeDegrees", "lon"),
        altitude_hae_meters=_optional_float(world_location, "altitude_hae_meters", "altitudeHaeMeters", "altitude_meters"),
        velocity_east_mps=_optional_float(velocity, "east_mps", "eastMps", "x_mps", "x"),
        velocity_north_mps=_optional_float(velocity, "north_mps", "northMps", "y_mps", "y"),
        velocity_up_mps=_optional_float(velocity, "up_mps", "upMps", "z_mps", "z"),
        psi_radians=_optional_angle_radians(orientation, "psi"),
        theta_radians=_optional_angle_radians(orientation, "theta"),
        phi_radians=_optional_angle_radians(orientation, "phi"),
        source_update_time=str(payload.get("timestamp") or payload.get("source_update_time") or to_iso(utc_now())),
        is_live=bool(payload.get("is_live") if "is_live" in payload else payload.get("isLive", True)),
    )
####


def entity_state_to_zorn_entity(state: DisEntityState) -> dict[str, Any]:
    entity_id = dis_entity_id(state)
    entity_type = _entity_type_payload(state.entity_type)
    attitude = _attitude_quaternion(state.psi_radians, state.theta_radians, state.phi_radians)

    location: dict[str, Any] = {
        "position": {
            "latitudeDegrees": state.latitude_degrees,
            "longitudeDegrees": state.longitude_degrees,
        },
    }
    if state.altitude_hae_meters is not None:
        location["position"]["altitudeHaeMeters"] = state.altitude_hae_meters
    ####
    if any(value is not None for value in (state.velocity_east_mps, state.velocity_north_mps, state.velocity_up_mps)):
        location["velocityEnu"] = {
            "e": state.velocity_east_mps or 0.0,
            "n": state.velocity_north_mps or 0.0,
            "u": state.velocity_up_mps or 0.0,
        }
    ####
    if attitude is not None:
        location["attitudeEnu"] = attitude
    ####

    return {
        "entityId": entity_id,
        "entity_id": entity_id,
        "description": state.marking or entity_id,
        "isLive": state.is_live,
        "is_live": state.is_live,
        "noExpiry": True,
        "aliases": {
            "dis": {
                "exerciseId": state.exercise_id,
                "siteId": state.site_id,
                "applicationId": state.application_id,
                "entityId": state.entity_id,
                "uid": f"{state.exercise_id}:{state.site_id}:{state.application_id}:{state.entity_id}",
            }
        },
        "location": location,
        "milView": {
            "disposition": _force_to_disposition(state.force_id),
            "environment": _domain_to_environment(entity_type.get("domain")),
        },
        "ontology": entity_type,
        "provenance": {
            "integrationName": "zorn-dis-entity-state-replay",
            "sourceId": f"dis-ex{state.exercise_id}-site{state.site_id}-app{state.application_id}",
            "sourceDescription": "DIS Entity State PDU replay",
            "sourceUpdateTime": state.source_update_time,
        },
    }
####


def dis_entity_id(state: DisEntityState) -> str:
    return f"dis-ex{state.exercise_id}-site{state.site_id}-app{state.application_id}-entity{state.entity_id}"
####


def _entity_type_payload(entity_type: dict[str, Any]) -> dict[str, Any]:
    domain = str(entity_type.get("domain") or "unknown").lower()
    platform_type = str(entity_type.get("platform_type") or entity_type.get("platformType") or entity_type.get("kind") or "UNKNOWN")
    payload = {
        "template": "TEMPLATE_TRACK",
        "platformType": platform_type.upper(),
        "domain": domain.upper(),
    }
    for key in ("country", "category", "subcategory", "specific", "extra"):
        if key in entity_type:
            payload[key] = entity_type[key]
        ####
    ####
    return payload
####


def _force_to_disposition(force_id: str) -> str:
    normalized = force_id.strip().lower().replace("-", "_").replace(" ", "_")
    return {
        "1": "DISPOSITION_FRIENDLY",
        "friendly": "DISPOSITION_FRIENDLY",
        "2": "DISPOSITION_HOSTILE",
        "opposing": "DISPOSITION_HOSTILE",
        "hostile": "DISPOSITION_HOSTILE",
        "3": "DISPOSITION_NEUTRAL",
        "neutral": "DISPOSITION_NEUTRAL",
    }.get(normalized, "DISPOSITION_UNKNOWN")
####


def _domain_to_environment(domain: object) -> str:
    normalized = str(domain or "").strip().lower()
    return {
        "air": "ENVIRONMENT_AIR",
        "surface": "ENVIRONMENT_SURFACE",
        "subsurface": "ENVIRONMENT_SUBSURFACE",
        "land": "ENVIRONMENT_LAND",
        "ground": "ENVIRONMENT_LAND",
        "space": "ENVIRONMENT_SPACE",
    }.get(normalized, "ENVIRONMENT_UNKNOWN")
####


def _attitude_quaternion(psi: float | None, theta: float | None, phi: float | None) -> dict[str, float] | None:
    if psi is None and theta is None and phi is None:
        return None
    ####
    yaw = psi or 0.0
    pitch = theta or 0.0
    roll = phi or 0.0
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)
    return {
        "w": cr * cp * cy + sr * sp * sy,
        "x": sr * cp * cy - cr * sp * sy,
        "y": cr * sp * cy + sr * cp * sy,
        "z": cr * cp * sy - sr * sp * cy,
    }
####


def _dict(payload: dict[str, Any], *keys: str) -> dict[str, Any]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, dict):
            return value
        ####
    ####
    return {}
####


def _required_int(payload: dict[str, Any], *keys: str) -> int:
    value = _first(payload, keys)
    if value is None:
        raise ValueError(f"missing required integer field: {keys[0]}")
    ####
    return int(cast(str | bytes | bytearray | int | float, value))
####


def _required_float(payload: dict[str, Any], *keys: str) -> float:
    value = _first(payload, keys)
    if value is None:
        raise ValueError(f"missing required float field: {keys[0]}")
    ####
    return float(cast(str | bytes | bytearray | int | float, value))
####


def _optional_float(payload: dict[str, Any], *keys: str) -> float | None:
    value = _first(payload, keys)
    return None if value is None else float(cast(str | bytes | bytearray | int | float, value))
####


def _optional_angle_radians(payload: dict[str, Any], basename: str) -> float | None:
    radians = _first(payload, (f"{basename}_radians", f"{basename}Radians", basename))
    if radians is not None:
        return float(cast(str | bytes | bytearray | int | float, radians))
    ####
    degrees = _first(payload, (f"{basename}_degrees", f"{basename}Degrees"))
    return None if degrees is None else math.radians(float(cast(str | bytes | bytearray | int | float, degrees)))
####


def _first(payload: dict[str, Any], keys: Iterable[str]) -> object | None:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
        ####
    ####
    return None
####


def _validate_iso(value: str) -> str:
    datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value
####
