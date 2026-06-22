from __future__ import annotations

from typing import Any
from uuid import uuid4


def first_string(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
        ####
    ####
    return None
####


def get_nested_value(payload: dict[str, Any], path: list[str]) -> object | None:
    value: object = payload
    for key in path:
        if not isinstance(value, dict):
            return None
        ####
        value = value.get(key)
    ####
    return value
####


def get_nested_string(payload: dict[str, Any], path: list[str]) -> str | None:
    value = get_nested_value(payload, path)
    return value if isinstance(value, str) and value.strip() else None
####


def entity_id_from_payload(payload: dict[str, Any], *, allow_generated: bool = True) -> str:
    entity_id = first_string(
        payload.get("entityId"),
        payload.get("entity_id"),
        get_nested_string(payload, ["entity", "entityId"]),
        get_nested_string(payload, ["entity", "entity_id"]),
    )
    if entity_id is not None:
        return entity_id
    ####
    if not allow_generated:
        raise ValueError("entityId is required")
    ####
    return f"entity-{uuid4()}"
####


def task_id_from_payload(payload: dict[str, Any]) -> str:
    return first_string(
        payload.get("taskId"),
        payload.get("task_id"),
        get_nested_string(payload, ["task", "taskId"]),
        get_nested_string(payload, ["task", "task_id"]),
        get_nested_string(payload, ["version", "taskId"]),
        get_nested_string(payload, ["version", "task_id"]),
    ) or f"task-{uuid4()}"
####


def assignee_id_from_task(payload: dict[str, Any]) -> str | None:
    return first_string(
        payload.get("assigneeId"),
        payload.get("assignee_id"),
        get_nested_string(payload, ["assignee", "entityId"]),
        get_nested_string(payload, ["assignee", "entity_id"]),
        get_nested_string(payload, ["relations", "assignee", "entityId"]),
        get_nested_string(payload, ["relations", "assignee", "entity_id"]),
        get_nested_string(payload, ["relations", "assignee", "system", "entityId"]),
        get_nested_string(payload, ["relations", "assignee", "system", "entity_id"]),
        get_nested_string(payload, ["relations", "assignee", "agent", "system", "entityId"]),
        get_nested_string(payload, ["relations", "assignee", "agent", "system", "entity_id"]),
        get_nested_string(payload, ["relations", "assignee", "team", "entityId"]),
        get_nested_string(payload, ["relations", "assignee", "team", "entity_id"]),
        get_nested_string(payload, ["relations", "assigneeId"]),
        get_nested_string(payload, ["relations", "assignee_id"]),
    )
####


def source_update_time_from_entity(payload: dict[str, Any]) -> str | None:
    return first_string(
        get_nested_string(payload, ["provenance", "sourceUpdateTime"]),
        get_nested_string(payload, ["provenance", "source_update_time"]),
        get_nested_string(payload, ["metadata", "provenance", "sourceUpdateTime"]),
        get_nested_string(payload, ["metadata", "provenance", "source_update_time"]),
    )
####
