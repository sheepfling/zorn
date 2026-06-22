from __future__ import annotations

import asyncio
import time
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from ..compat import bool_from_payload, heartbeat_seconds_from_payload, int_from_payload
from ..config import AppSettings
from ..db import Database
from ..dependencies import get_settings, get_task_store, require_auth
from ..events import event_snapshot, event_to_payload, format_sse, get_max_event_id, heartbeat_payload, poll_events
from ..stores import TaskStatusConflict, TaskStore, TerminalTaskUpdateError

router = APIRouter(tags=["tasks"], dependencies=[Depends(require_auth)])


async def _json_body(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return {}
    ####
    return body if isinstance(body, dict) else {}
####


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(
    store: Annotated[TaskStore, Depends(get_task_store)],
    payload: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    try:
        return store.create(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    ####
####


@router.get("/tasks/{task_id}")
def get_task(
    task_id: str,
    store: Annotated[TaskStore, Depends(get_task_store)],
) -> dict[str, Any]:
    task = store.get(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
    ####
    return task
####


@router.put("/tasks/{task_id}/status")
def update_task_status(
    task_id: str,
    store: Annotated[TaskStore, Depends(get_task_store)],
    payload: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    try:
        task = store.update_status(task_id, payload)
    except TaskStatusConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except TerminalTaskUpdateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    ####
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
    ####
    return task
####


@router.post("/tasks/{task_id}/status")
def update_task_status_post_alias(
    task_id: str,
    store: Annotated[TaskStore, Depends(get_task_store)],
    payload: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    return update_task_status(task_id=task_id, store=store, payload=payload)
####


@router.put("/tasks/{task_id}/cancel")
def cancel_task(
    task_id: str,
    store: Annotated[TaskStore, Depends(get_task_store)],
    payload: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    task = store.cancel(task_id, payload)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
    ####
    return task
####


@router.post("/tasks/{task_id}/cancel")
def cancel_task_post_alias(
    task_id: str,
    store: Annotated[TaskStore, Depends(get_task_store)],
    payload: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    return cancel_task(task_id=task_id, store=store, payload=payload)
####


@router.post("/tasks/query")
def query_tasks(
    store: Annotated[TaskStore, Depends(get_task_store)],
    payload: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    return {"tasks": store.query(payload)}
####


@router.post("/tasks/events")
async def poll_task_events(
    request: Request,
    store: Annotated[TaskStore, Depends(get_task_store)],
) -> dict[str, Any]:
    body = await _json_body(request)
    after_sequence = int_from_payload(body, "afterSequence", "fromSequence", default=0)
    limit = int_from_payload(body, "limit", default=100)
    return {"events": store.poll_tasks(after_sequence=after_sequence, limit=limit)}
####


@router.get("/tasks/events/snapshot")
def task_events_snapshot(request: Request) -> dict[str, Any]:
    return event_snapshot(request.app.state.database, stream="task")
####


@router.post("/tasks/stream")
async def stream_tasks(
    request: Request,
    settings: Annotated[AppSettings, Depends(get_settings)],
    store: Annotated[TaskStore, Depends(get_task_store)],
) -> StreamingResponse:
    body = await _json_body(request)
    heartbeat_seconds = heartbeat_seconds_from_payload(
        body,
        default_seconds=settings.heartbeat_seconds,
        millisecond_keys=("heartbeatIntervalMs", "heartbeatIntervalMS"),
    )
    exclude_preexisting = bool_from_payload(body, "excludePreexistingTasks", default=False)
    include_preexisting = bool_from_payload(body, "includePreexisting", default=not exclude_preexisting)
    database: Database = request.app.state.database

    async def generate() -> Any:
        if include_preexisting:
            for task in store.list_open():
                yield format_sse("PREEXISTING", {"eventType": "PREEXISTING", "task": task})
            ####
        ####
        with database.session() as session:
            cursor = get_max_event_id(session, stream="task")
        ####
        next_heartbeat = time.monotonic() + heartbeat_seconds
        while not await request.is_disconnected():
            with database.session() as session:
                rows = poll_events(session, stream="task", after_sequence=cursor, limit=100)
            ####
            for row in rows:
                cursor = max(cursor, row.id)
                yield format_sse(row.event_type, event_to_payload(row))
            ####
            if time.monotonic() >= next_heartbeat:
                yield format_sse("HEARTBEAT", {"heartbeat": heartbeat_payload(), **heartbeat_payload()})
                next_heartbeat = time.monotonic() + heartbeat_seconds
            ####
            await asyncio.sleep(settings.poll_interval_seconds)
        ####
    ####

    return StreamingResponse(generate(), media_type="text/event-stream")
####


@router.post("/agent/listen")
async def listen_as_agent(
    request: Request,
    store: Annotated[TaskStore, Depends(get_task_store)],
) -> dict[str, Any]:
    body = await _json_body(request)
    assignee_id = _assignee_id_from_body(body)
    event = store.claim_agent_request(assignee_id=assignee_id)
    if event:
        return event
    ####
    return {"heartbeat": heartbeat_payload()}
####


@router.post("/agent/stream")
async def stream_as_agent(
    request: Request,
    settings: Annotated[AppSettings, Depends(get_settings)],
    store: Annotated[TaskStore, Depends(get_task_store)],
) -> StreamingResponse:
    body = await _json_body(request)
    assignee_id = _assignee_id_from_body(body)
    heartbeat_seconds = heartbeat_seconds_from_payload(
        body,
        default_seconds=settings.heartbeat_seconds,
        millisecond_keys=("heartbeatIntervalMs", "heartbeatIntervalMS"),
    )
    database: Database = request.app.state.database

    async def generate() -> Any:
        for task in store.list_open(assignee_id=assignee_id):
            yield format_sse(
                "ExecuteRequest",
                {
                    "executeRequest": {"task": task},
                    "execute_request": {"task": task},
                    "requestType": "ExecuteRequest",
                    "request_type": "ExecuteRequest",
                    "task": task,
                    "assigneeId": assignee_id,
                    "assignee_id": assignee_id,
                },
            )
        ####
        with database.session() as session:
            cursor = get_max_event_id(session, stream="agent")
        ####
        next_heartbeat = time.monotonic() + heartbeat_seconds
        while not await request.is_disconnected():
            subject_ids = [assignee_id, "*"] if assignee_id is not None else None
            with database.session() as session:
                rows = poll_events(session, stream="agent", after_sequence=cursor, limit=100, subject_ids=subject_ids)
            ####
            for row in rows:
                cursor = max(cursor, row.id)
                yield format_sse(row.event_type, event_to_payload(row))
            ####
            if time.monotonic() >= next_heartbeat:
                yield format_sse("HEARTBEAT", {"heartbeat": heartbeat_payload(), **heartbeat_payload()})
                next_heartbeat = time.monotonic() + heartbeat_seconds
            ####
            await asyncio.sleep(settings.poll_interval_seconds)
        ####
    ####

    return StreamingResponse(generate(), media_type="text/event-stream")
####


@router.post("/tasks/{task_id}/manual-control/stream")
async def manual_control_stream(
    task_id: str,
    request: Request,
    settings: Annotated[AppSettings, Depends(get_settings)],
) -> StreamingResponse:
    body = await _json_body(request)
    heartbeat_seconds = heartbeat_seconds_from_payload(
        body,
        default_seconds=settings.heartbeat_seconds,
        millisecond_keys=("heartbeatIntervalMs", "heartbeatIntervalMS"),
    )
    _ = task_id

    async def generate() -> Any:
        while not await request.is_disconnected():
            yield format_sse("HEARTBEAT", {"heartbeat": heartbeat_payload(), **heartbeat_payload()})
            await asyncio.sleep(heartbeat_seconds)
        ####
    ####

    return StreamingResponse(generate(), media_type="text/event-stream")
####


def _assignee_id_from_body(body: dict[str, Any]) -> str | None:
    raw = body.get("assigneeId") or body.get("agentId") or body.get("entityId")
    if isinstance(raw, str) and raw:
        return raw
    ####
    selector = body.get("agentSelector") or body.get("agent_selector")
    if isinstance(selector, dict):
        entity_ids = selector.get("entityIds") or selector.get("entity_ids")
        if isinstance(entity_ids, list) and entity_ids:
            first = entity_ids[0]
            if isinstance(first, str) and first:
                return first
            ####
        ####
    ####
    agent = body.get("agent") or body.get("assignee")
    if isinstance(agent, dict):
        nested = agent.get("entityId")
        if isinstance(nested, str) and nested:
            return nested
        ####
        system = agent.get("system")
        if isinstance(system, dict):
            entity_id = system.get("entityId")
            return entity_id if isinstance(entity_id, str) and entity_id else None
        ####
    ####
    return None
####
