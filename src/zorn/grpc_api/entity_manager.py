from __future__ import annotations

import asyncio
import time
from typing import Any

import grpc

from ..config import AppSettings
from ..db import Database
from ..events import event_to_payload, get_max_event_id, poll_events
from ..stores import EntityStore
from .json_bridge import (
    get_repeated_strings,
    get_string_attr,
    make_entity_event_response,
    make_heartbeat_response,
    message_to_dict,
    parse_dict_or_empty,
)
from .proto_modules import LatticeProtoModules


class EntityManagerServiceFactory:
    def __init__(
        self,
        *,
        proto_modules: LatticeProtoModules,
        settings: AppSettings,
        database: Database,
        entity_store: EntityStore,
    ) -> None:
        self.proto_modules = proto_modules
        self.settings = settings
        self.database = database
        self.entity_store = entity_store
    ####

    def build(self) -> Any:
        proto_modules = self.proto_modules
        settings = self.settings
        database = self.database
        entity_store = self.entity_store

        class EntityManagerService(proto_modules.entity_api_grpc.EntityManagerAPIServicer):  # type: ignore[misc, valid-type, name-defined]
            async def PublishEntity(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
                entity_payload = _entity_payload_from_request(request)
                if entity_payload is None:
                    await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "PublishEntityRequest.entity is required")
                    raise AssertionError("unreachable after gRPC abort")
                ####
                try:
                    entity_store.publish(entity_payload)
                except ValueError as exc:
                    await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
                    raise AssertionError("unreachable after gRPC abort")
                ####
                return proto_modules.entity_api.PublishEntityResponse()
            ####

            async def PublishEntities(self, request_iterator: Any, context: grpc.aio.ServicerContext) -> Any:
                async for request in request_iterator:
                    entity_payload = _entity_payload_from_request(request)
                    if entity_payload is not None:
                        try:
                            entity_store.publish(entity_payload)
                        except ValueError:
                            # PublishEntities trades validation feedback for throughput.
                            continue
                        ####
                    ####
                ####
                return proto_modules.entity_api.PublishEntitiesResponse()
            ####

            async def GetEntity(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
                entity_id = get_string_attr(request, "entity_id", "entityId")
                if entity_id is None:
                    await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "GetEntityRequest.entity_id is required")
                    raise AssertionError("unreachable after gRPC abort")
                ####
                entity = entity_store.get(entity_id)
                if entity is None:
                    await context.abort(grpc.StatusCode.NOT_FOUND, f"entity not found: {entity_id}")
                    raise AssertionError("unreachable after gRPC abort")
                ####
                return parse_dict_or_empty(proto_modules.entity_api.GetEntityResponse, {"entity": entity})
            ####

            async def OverrideEntity(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
                payload = message_to_dict(request)
                entity_payload = _entity_payload_from_request(request)
                entity_id = (
                    _first_string(payload, "entityId", "entity_id")
                    or (
                        entity_payload.get("entityId")
                        if isinstance(entity_payload, dict) and isinstance(entity_payload.get("entityId"), str)
                        else None
                    )
                    or (
                        entity_payload.get("entity_id")
                        if isinstance(entity_payload, dict) and isinstance(entity_payload.get("entity_id"), str)
                        else None
                    )
                )
                field_path = _field_path_from_request(payload, request)
                if entity_id is None or field_path is None:
                    await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "entity_id and field_path are required")
                    raise AssertionError("unreachable after gRPC abort")
                ####
                value = entity_payload or payload.get("value") or payload.get("fieldValue") or payload.get("maskedFieldValue") or payload
                entity = entity_store.override_field(entity_id, field_path, value)
                if entity is None:
                    await context.abort(grpc.StatusCode.NOT_FOUND, f"entity not found: {entity_id}")
                    raise AssertionError("unreachable after gRPC abort")
                ####
                response_type = getattr(proto_modules.entity_api, "OverrideEntityResponse")
                return parse_dict_or_empty(response_type, {"entity": entity})
            ####

            async def RemoveEntityOverride(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
                payload = message_to_dict(request)
                entity_id = _first_string(payload, "entityId", "entity_id") or get_string_attr(request, "entity_id", "entityId")
                field_path = _field_path_from_request(payload, request)
                if entity_id is None or field_path is None:
                    await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "entity_id and field_path are required")
                    raise AssertionError("unreachable after gRPC abort")
                ####
                entity = entity_store.remove_override(entity_id, field_path)
                if entity is None:
                    await context.abort(grpc.StatusCode.NOT_FOUND, f"entity not found: {entity_id}")
                    raise AssertionError("unreachable after gRPC abort")
                ####
                response_type = getattr(proto_modules.entity_api, "RemoveEntityOverrideResponse")
                return parse_dict_or_empty(response_type, {"entity": entity})
            ####

            async def StreamEntityComponents(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
                payload = message_to_dict(request)
                components = get_repeated_strings(request, "components_to_include")
                include_all_components = bool(payload.get("includeAllComponents", False))
                if components and include_all_components:
                    await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "include_all_components cannot be combined with components_to_include")
                    raise AssertionError("unreachable after gRPC abort")
                ####
                preexisting_only = bool(getattr(request, "preexisting_only", False))
                heartbeat_period_millis = int(getattr(request, "heartbeat_period_millis", 0) or 0)
                heartbeat_seconds = heartbeat_period_millis / 1000.0 if heartbeat_period_millis > 0 else 0.0

                for entity in entity_store.list_live():
                    if _entity_matches_stream_request(entity, payload):
                        selected = entity if include_all_components else _select_components(entity, components)
                        yield make_entity_event_response(
                            response_type=proto_modules.entity_api.StreamEntityComponentsResponse,
                            entity_type=proto_modules.entity.Entity,
                            event_type="PREEXISTING",
                            entity=selected,
                        )
                    ####
                ####
                if preexisting_only:
                    return
                ####
                with database.session() as session:
                    cursor = get_max_event_id(session, stream="entity")
                ####
                next_heartbeat = time.monotonic() + heartbeat_seconds if heartbeat_seconds > 0 else 0.0
                while True:
                    if context.cancelled():
                        return
                    ####
                    with database.session() as session:
                        rows = poll_events(session, stream="entity", after_sequence=cursor, limit=100)
                    ####
                    for row in rows:
                        cursor = max(cursor, row.id)
                        event = event_to_payload(row)
                        event_entity = event.get("entity")
                        if isinstance(event_entity, dict) and _entity_matches_stream_request(event_entity, payload):
                            selected = event_entity if include_all_components else _select_components(event_entity, components)
                            yield make_entity_event_response(
                                response_type=proto_modules.entity_api.StreamEntityComponentsResponse,
                                entity_type=proto_modules.entity.Entity,
                                event_type=_entity_event_type(row.event_type),
                                entity=selected,
                            )
                        ####
                    ####
                    if heartbeat_seconds > 0 and time.monotonic() >= next_heartbeat:
                        yield make_heartbeat_response(proto_modules.entity_api.StreamEntityComponentsResponse)
                        next_heartbeat = time.monotonic() + heartbeat_seconds
                    ####
                    await asyncio.sleep(settings.poll_interval_seconds)
                ####
            ####
        ####

        return EntityManagerService()
    ####
####


def _entity_payload_from_request(request: Any) -> dict[str, Any] | None:
    entity = getattr(request, "entity", None)
    if entity is None:
        return None
    ####
    payload = message_to_dict(entity)
    for raw_name, wire_name in (("entity_id", "entityId"), ("is_live", "isLive"), ("no_expiry", "noExpiry")):
        value = getattr(entity, raw_name, None)
        if isinstance(value, bool):
            payload[wire_name] = value
            payload.setdefault(raw_name, value)
        elif isinstance(value, str) and value:
            payload[wire_name] = value
            payload.setdefault(raw_name, value)
        ####
    ####
    return payload if payload else None
####


def _first_string(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
        ####
    ####
    return None
####


def _field_path_from_request(payload: dict[str, Any], request: Any) -> str | None:
    direct = _first_string(payload, "fieldPath", "field_path")
    if direct is not None:
        return direct
    ####
    for field_name in ("field_path", "fieldPath"):
        repeated = get_repeated_strings(request, field_name)
        if repeated:
            return "".join(repeated) if len(repeated) > 1 and all(len(item) == 1 for item in repeated) else ".".join(repeated)
        ####
    ####
    return get_string_attr(request, "field_path", "fieldPath")
####


def _select_components(entity: dict[str, Any], components: list[str]) -> dict[str, Any]:
    if not components:
        return entity
    ####
    selected: dict[str, Any] = {}
    for key in {"entityId", "entity_id", *components, *[_snake_to_camel(component) for component in components]}:
        if key in entity:
            selected[key] = entity[key]
        ####
    ####
    return selected
####


def _entity_matches_stream_request(entity: dict[str, Any], payload: dict[str, Any]) -> bool:
    entity_ids = _entity_ids_filter(payload)
    if entity_ids and _entity_id(entity) not in entity_ids:
        return False
    ####
    return True
####


def _entity_ids_filter(payload: dict[str, Any]) -> set[str]:
    filter_payload = payload.get("filter")
    if not isinstance(filter_payload, dict):
        return set()
    ####
    candidates = [
        filter_payload.get("entityIds"),
        filter_payload.get("entity_ids"),
        _nested_value(filter_payload, ["ids", "entityIds"]),
        _nested_value(filter_payload, ["ids", "entity_ids"]),
    ]
    entity_ids: set[str] = set()
    for candidate in candidates:
        if isinstance(candidate, list):
            entity_ids.update(value for value in candidate if isinstance(value, str))
        elif isinstance(candidate, dict):
            values = candidate.get("entityIds") or candidate.get("entity_ids") or []
            if isinstance(values, list):
                entity_ids.update(value for value in values if isinstance(value, str))
            ####
        ####
    ####
    return entity_ids
####


def _nested_value(payload: dict[str, Any], keys: list[str]) -> Any:
    value: object = payload
    for key in keys:
        if not isinstance(value, dict):
            return None
        ####
        value = value.get(key)
    ####
    return value
####


def _entity_id(entity: dict[str, Any]) -> str | None:
    value = entity.get("entityId") or entity.get("entity_id")
    return value if isinstance(value, str) else None
####


def _snake_to_camel(value: str) -> str:
    parts = value.split("_")
    if not parts:
        return value
    ####
    return parts[0] + "".join(part.capitalize() for part in parts[1:])
####


def _entity_event_type(raw_event_type: str) -> str:
    normalized = raw_event_type.upper()
    if normalized in {"CREATE", "CREATED"}:
        return "CREATE"
    ####
    if normalized in {"DELETE", "DELETED", "REMOVE", "REMOVED"}:
        return "DELETED"
    ####
    if normalized == "PREEXISTING":
        return "PREEXISTING"
    ####
    return "UPDATE"
####
