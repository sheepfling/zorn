from __future__ import annotations

import asyncio
import time
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from ..compat import heartbeat_seconds_from_payload, int_from_payload, select_entity_components, sequence_token
from ..config import AppSettings
from ..db import Database
from ..dependencies import get_entity_store, get_settings, require_auth
from ..events import (
    entity_stream_event_payload,
    entity_stream_heartbeat_payload,
    event_to_payload,
    format_sse,
    get_max_event_id,
    poll_events,
)
from ..stores import EntityStore

router = APIRouter(prefix="/entities", tags=["entities"], dependencies=[Depends(require_auth)])


async def _json_body(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return {}
    ####
    return body if isinstance(body, dict) else {}
####


@router.put("")
def publish_entity(
    store: Annotated[EntityStore, Depends(get_entity_store)],
    payload: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    try:
        return store.publish(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    ####
####


@router.get("/{entity_id}")
def get_entity(
    entity_id: str,
    store: Annotated[EntityStore, Depends(get_entity_store)],
) -> dict[str, Any]:
    entity = store.get(entity_id)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="entity not found")
    ####
    return entity
####


@router.post("/events")
async def poll_entity_events(
    request: Request,
    store: Annotated[EntityStore, Depends(get_entity_store)],
) -> dict[str, Any]:
    body = await _json_body(request)
    session_token = body.get("sessionToken")
    after_sequence = sequence_token(session_token, default=int_from_payload(body, "afterSequence", "fromSequence", default=0))
    limit = int_from_payload(body, "limit", "maxEvents", default=100)
    components = body.get("componentsToInclude")
    components_to_include = components if isinstance(components, list) else None
    events = [_filter_entity_event(event, components_to_include) for event in store.poll(after_sequence=after_sequence, limit=limit)]
    next_token = str(max([after_sequence, *[int(event.get("sequence") or 0) for event in events]]))
    return {"sessionToken": next_token, "entityEvents": events, "events": events}
####


@router.post("/events/poll")
async def poll_entity_events_alias(
    request: Request,
    store: Annotated[EntityStore, Depends(get_entity_store)],
) -> dict[str, Any]:
    return await poll_entity_events(request=request, store=store)
####


@router.post("/stream")
async def stream_entity_events(
    request: Request,
    settings: Annotated[AppSettings, Depends(get_settings)],
    store: Annotated[EntityStore, Depends(get_entity_store)],
) -> StreamingResponse:
    body = await _json_body(request)
    heartbeat_seconds = heartbeat_seconds_from_payload(
        body,
        default_seconds=settings.heartbeat_seconds,
        millisecond_keys=("heartbeatIntervalMS", "heartbeatIntervalMs"),
    )
    preexisting_only = bool(body.get("preExistingOnly", False))
    components = body.get("componentsToInclude")
    components_to_include = components if isinstance(components, list) else None
    database: Database = request.app.state.database

    async def generate() -> Any:
        for entity in store.list_live():
            filtered_entity = select_entity_components(entity, components_to_include)
            payload = entity_stream_event_payload(event_type="PREEXISTING", entity=filtered_entity)
            yield format_sse("entity", payload)
        ####
        if preexisting_only:
            return
        ####
        with database.session() as session:
            cursor = get_max_event_id(session, stream="entity")
        ####
        next_heartbeat = time.monotonic() + heartbeat_seconds
        while not await request.is_disconnected():
            with database.session() as session:
                rows = poll_events(session, stream="entity", after_sequence=cursor, limit=100)
            ####
            for row in rows:
                cursor = max(cursor, row.id)
                event_payload = _filter_entity_event(event_to_payload(row), components_to_include)
                entity_payload = event_payload.get("entity")
                if not isinstance(entity_payload, dict):
                    continue
                ####
                payload = entity_stream_event_payload(
                    event_type=str(event_payload.get("eventType", row.event_type)),
                    entity=entity_payload,
                    occurred_time=event_payload.get("occurredTime") if isinstance(event_payload.get("occurredTime"), str) else None,
                )
                yield format_sse("entity", payload)
            ####
            if time.monotonic() >= next_heartbeat:
                yield format_sse("heartbeat", entity_stream_heartbeat_payload())
                next_heartbeat = time.monotonic() + heartbeat_seconds
            ####
            await asyncio.sleep(settings.poll_interval_seconds)
        ####
    ####

    return StreamingResponse(generate(), media_type="text/event-stream")
####


@router.put("/{entity_id}/override/{field_path:path}")
def override_entity(
    entity_id: str,
    field_path: str,
    store: Annotated[EntityStore, Depends(get_entity_store)],
    payload: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    override_payload = payload.get("entity") if isinstance(payload.get("entity"), dict) else payload
    entity = store.override_field(entity_id, field_path, override_payload)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="entity not found")
    ####
    return entity
####


@router.delete("/{entity_id}/override/{field_path:path}")
def delete_entity_override(
    entity_id: str,
    field_path: str,
    store: Annotated[EntityStore, Depends(get_entity_store)],
) -> dict[str, Any]:
    entity = store.remove_override(entity_id, field_path)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="entity not found")
    ####
    return entity
####


def _filter_entity_event(event: dict[str, Any], components_to_include: list[str] | None) -> dict[str, Any]:
    event = dict(event)
    entity = event.get("entity")
    if isinstance(entity, dict):
        event["entity"] = select_entity_components(entity, components_to_include)
    ####
    return event
####
