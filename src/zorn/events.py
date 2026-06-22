from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Sequence
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from .db import EventRow
from .time_utils import to_iso, utc_now
from .db import Database


def add_event(
    session: Session,
    *,
    stream: str,
    subject_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> EventRow:
    row = EventRow(
        stream=stream,
        subject_id=subject_id,
        event_type=event_type,
        occurred_at=utc_now(),
        payload=payload,
    )
    session.add(row)
    session.flush()
    return row
####


def get_max_event_id(session: Session, stream: str | None = None) -> int:
    statement: Select[tuple[int | None]] = select(func.max(EventRow.id))
    if stream is not None:
        statement = statement.where(EventRow.stream == stream)
    ####
    return int(session.execute(statement).scalar_one() or 0)
####


def poll_events(
    session: Session,
    *,
    stream: str,
    after_sequence: int = 0,
    limit: int = 100,
    subject_id: str | None = None,
    subject_ids: list[str] | None = None,
) -> list[EventRow]:
    statement = (
        select(EventRow)
        .where(EventRow.stream == stream)
        .where(EventRow.id > after_sequence)
        .order_by(EventRow.id.asc())
        .limit(max(1, min(limit, 1000)))
    )
    if subject_ids is not None:
        statement = statement.where(EventRow.subject_id.in_(subject_ids))
    elif subject_id is not None:
        statement = statement.where(EventRow.subject_id == subject_id)
    ####
    return list(session.scalars(statement).all())
####


def event_to_payload(row: EventRow) -> dict[str, Any]:
    payload = dict(row.payload)
    payload.setdefault("eventType", row.event_type)
    payload.setdefault("sequence", row.id)
    payload.setdefault("occurredTime", to_iso(row.occurred_at))
    return payload
####


def event_snapshot(database: Database, *, stream: str, limit: int = 1000) -> dict[str, Any]:
    with database.session() as session:
        rows = poll_events(session, stream=stream, after_sequence=0, limit=limit)
    ####
    events = [event_to_payload(row) for row in rows]
    sequences = [int(event.get("sequence") or 0) for event in events]
    return {
        "schemaVersion": "zorn.events.snapshot.v1",
        "stream": stream,
        "sequenceStart": min(sequences, default=0),
        "sequenceEnd": max(sequences, default=0),
        "count": len(events),
        "events": events,
    }
####


def format_sse(event_name: str, payload: dict[str, Any]) -> str:
    data = json.dumps(payload, separators=(",", ":"), sort_keys=False)
    return f"event: {event_name}\ndata: {data}\n\n"
####


def heartbeat_payload() -> dict[str, Any]:
    return {"eventType": "HEARTBEAT", "occurredTime": to_iso(utc_now())}
####


def entity_stream_event_payload(
    *,
    event_type: str,
    entity: dict[str, Any],
    occurred_time: str | None = None,
) -> dict[str, Any]:
    payload = {
        "event": "entity",
        "eventType": _entity_stream_event_type(event_type),
        "time": occurred_time or to_iso(utc_now()),
        "entity": entity,
    }
    # Some public sample apps incorrectly inspect a typed SSE model's `data`
    # attribute instead of using the parsed fields. Preserve compatibility by
    # embedding the same event body as a JSON string.
    payload["data"] = json.dumps(payload, separators=(",", ":"), sort_keys=False)
    return payload
####


def entity_stream_heartbeat_payload() -> dict[str, Any]:
    payload = {"event": "heartbeat", "timestamp": to_iso(utc_now())}
    payload["data"] = json.dumps(payload, separators=(",", ":"), sort_keys=False)
    return payload
####


def _entity_stream_event_type(event_type: str) -> str:
    return {
        "CREATE": "EVENT_TYPE_CREATED",
        "UPDATE": "EVENT_TYPE_UPDATE",
        "DELETE": "EVENT_TYPE_DELETED",
        "DELETED": "EVENT_TYPE_DELETED",
        "PREEXISTING": "EVENT_TYPE_PREEXISTING",
        "POST_EXPIRY_OVERRIDE": "EVENT_TYPE_POST_EXPIRY_OVERRIDE",
    }.get(event_type, "EVENT_TYPE_INVALID")
####


async def rows_to_sse(rows: Sequence[EventRow]) -> AsyncGenerator[str, None]:
    for row in rows:
        yield format_sse(row.event_type, event_to_payload(row))
    ####
####
