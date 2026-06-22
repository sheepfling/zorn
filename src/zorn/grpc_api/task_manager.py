from __future__ import annotations

import asyncio
import time
from typing import Any

import grpc

from ..config import AppSettings
from ..db import Database
from ..events import event_to_payload, get_max_event_id, poll_events
from ..stores import TaskStatusConflict, TaskStore, TerminalTaskUpdateError
from .json_bridge import (
    get_string_attr,
    make_agent_response,
    make_heartbeat_response,
    make_manual_control_frame_response,
    make_task_event_response,
    message_to_dict,
    parse_dict_or_empty,
)
from .proto_modules import LatticeProtoModules


class TaskManagerServiceFactory:
    def __init__(
        self,
        *,
        proto_modules: LatticeProtoModules,
        settings: AppSettings,
        database: Database,
        task_store: TaskStore,
    ) -> None:
        self.proto_modules = proto_modules
        self.settings = settings
        self.database = database
        self.task_store = task_store
    ####

    def build(self) -> Any:
        proto_modules = self.proto_modules
        settings = self.settings
        database = self.database
        task_store = self.task_store

        class TaskManagerService(proto_modules.task_api_grpc.TaskManagerAPIServicer):  # type: ignore[misc, valid-type, name-defined]
            async def CreateTask(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
                payload = _task_payload_from_create_request(message_to_dict(request))
                payload.setdefault("status", {"status": "STATUS_SENT"})
                try:
                    task = task_store.create(payload)
                except ValueError as exc:
                    await context.abort(grpc.StatusCode.ALREADY_EXISTS, str(exc))
                    raise AssertionError("unreachable after gRPC abort")
                ####
                return parse_dict_or_empty(proto_modules.task_api.CreateTaskResponse, {"task": task})
            ####

            async def GetTask(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
                task_id = get_string_attr(request, "task_id", "taskId")
                if task_id is None:
                    await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "GetTaskRequest.task_id is required")
                    raise AssertionError("unreachable after gRPC abort")
                ####
                task = task_store.get(task_id)
                if task is None:
                    await context.abort(grpc.StatusCode.NOT_FOUND, f"task not found: {task_id}")
                    raise AssertionError("unreachable after gRPC abort")
                ####
                return parse_dict_or_empty(proto_modules.task_api.GetTaskResponse, {"task": task})
            ####

            async def QueryTasks(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
                filters = message_to_dict(request)
                tasks = task_store.query(filters)
                return parse_dict_or_empty(proto_modules.task_api.QueryTasksResponse, {"tasks": tasks})
            ####

            async def UpdateStatus(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
                payload = message_to_dict(request)
                status_update = _status_update_from_payload(payload)
                task_id = _task_id_from_request(request, payload, status_update)
                if task_id is None:
                    await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "UpdateStatusRequest.status_update.version.task_id is required")
                    raise AssertionError("unreachable after gRPC abort")
                ####
                try:
                    task = task_store.update_status(
                        task_id,
                        status_update,
                        enforce_version=settings.grpc_enforce_task_status_version,
                    )
                except TaskStatusConflict as exc:
                    await context.abort(grpc.StatusCode.ABORTED, str(exc))
                    raise AssertionError("unreachable after gRPC abort")
                except TerminalTaskUpdateError as exc:
                    await context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(exc))
                    raise AssertionError("unreachable after gRPC abort")
                ####
                if task is None:
                    await context.abort(grpc.StatusCode.NOT_FOUND, f"task not found: {task_id}")
                    raise AssertionError("unreachable after gRPC abort")
                ####
                return parse_dict_or_empty(proto_modules.task_api.UpdateStatusResponse, {"task": task})
            ####

            async def CancelTask(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
                payload = message_to_dict(request)
                task_id = _task_id_from_request(request, payload, payload)
                if task_id is None:
                    await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "CancelTaskRequest.task_id is required")
                    raise AssertionError("unreachable after gRPC abort")
                ####
                task = task_store.cancel(
                    task_id,
                    payload,
                    terminal_status="STATUS_DONE_NOT_OK",
                    error_code="ERROR_CODE_CANCELLED",
                )
                if task is None:
                    await context.abort(grpc.StatusCode.NOT_FOUND, f"task not found: {task_id}")
                    raise AssertionError("unreachable after gRPC abort")
                ####
                return parse_dict_or_empty(proto_modules.task_api.CancelTaskResponse, {"task": task})
            ####

            async def ListenAsAgent(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
                payload = message_to_dict(request)
                assignee_id = _assignee_id_from_payload(payload) or get_string_attr(request, "assignee_id", "agent_id", "entity_id")
                heartbeat_seconds = _heartbeat_seconds(payload, default_seconds=0.0)
                for task in task_store.list_open(assignee_id=assignee_id):
                    yield make_agent_response(
                        response_type=proto_modules.task_api.ListenAsAgentResponse,
                        task_type=_task_message_type(proto_modules),
                        request_type="ExecuteRequest",
                        task=task,
                    )
                ####
                with database.session() as session:
                    cursor = get_max_event_id(session, stream="agent")
                ####
                next_heartbeat = time.monotonic() + heartbeat_seconds if heartbeat_seconds > 0 else 0.0
                while True:
                    if context.cancelled():
                        return
                    ####
                    subject_ids = [assignee_id, "*"] if assignee_id is not None else None
                    with database.session() as session:
                        rows = poll_events(session, stream="agent", after_sequence=cursor, limit=100, subject_ids=subject_ids)
                    ####
                    for row in rows:
                        cursor = max(cursor, row.id)
                        event = event_to_payload(row)
                        event_task = event.get("task")
                        if not isinstance(event_task, dict):
                            cancel = event.get("cancelRequest")
                            execute = event.get("executeRequest")
                            complete = event.get("completeRequest")
                            if isinstance(cancel, dict):
                                event_task = cancel.get("task")
                            elif isinstance(execute, dict):
                                event_task = execute.get("task")
                            elif isinstance(complete, dict):
                                event_task = complete.get("task")
                            ####
                        ####
                        yield make_agent_response(
                            response_type=proto_modules.task_api.ListenAsAgentResponse,
                            task_type=_task_message_type(proto_modules),
                            request_type=row.event_type,
                            task=event_task if isinstance(event_task, dict) else None,
                        )
                    ####
                    if heartbeat_seconds > 0 and time.monotonic() >= next_heartbeat:
                        yield make_heartbeat_response(proto_modules.task_api.ListenAsAgentResponse)
                        next_heartbeat = time.monotonic() + heartbeat_seconds
                    ####
                    await asyncio.sleep(settings.poll_interval_seconds)
                ####
            ####

            async def ListenForManualControlFrames(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
                response_type = proto_modules.task_api.ListenForManualControlFramesResponse
                task_id = get_string_attr(request, "task_id", "taskId")
                if task_id is None:
                    await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "ListenForManualControlFramesRequest.task_id is required")
                    raise AssertionError("unreachable after gRPC abort")
                ####
                with database.session() as session:
                    cursor = get_max_event_id(session, stream="manual_control")
                ####
                while True:
                    if context.cancelled():
                        return
                    ####
                    task = task_store.get(task_id)
                    if task is None:
                        await context.abort(grpc.StatusCode.NOT_FOUND, f"task not found: {task_id}")
                        raise AssertionError("unreachable after gRPC abort")
                    ####
                    if _is_terminal_task(task):
                        return
                    ####
                    with database.session() as session:
                        rows = poll_events(session, stream="manual_control", after_sequence=cursor, limit=100, subject_id=task_id)
                    ####
                    for row in rows:
                        cursor = max(cursor, row.id)
                        event = event_to_payload(row)
                        frame = event.get("frame")
                        if isinstance(frame, dict):
                            yield make_manual_control_frame_response(response_type=response_type, frame=frame)
                        ####
                    ####
                    await asyncio.sleep(settings.poll_interval_seconds)
                ####
            ####

            async def StreamTasks(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
                payload = message_to_dict(request)
                exclude_preexisting = bool(payload.get("excludePreexistingTasks", False))
                heartbeat_seconds = _heartbeat_seconds(payload, default_seconds=30.0)
                if not exclude_preexisting:
                    for task in task_store.list_open():
                        if _task_matches_stream_request(task, payload):
                            yield make_task_event_response(
                                response_type=proto_modules.task_api.StreamTasksResponse,
                                task_type=_task_message_type(proto_modules),
                                event_type="PREEXISTING",
                                task=task,
                            )
                        ####
                    ####
                ####
                with database.session() as session:
                    cursor = get_max_event_id(session, stream="task")
                ####
                next_heartbeat = time.monotonic() + heartbeat_seconds if heartbeat_seconds > 0 else 0.0
                while True:
                    if context.cancelled():
                        return
                    ####
                    with database.session() as session:
                        rows = poll_events(session, stream="task", after_sequence=cursor, limit=100)
                    ####
                    for row in rows:
                        cursor = max(cursor, row.id)
                        event = event_to_payload(row)
                        event_task = event.get("task")
                        if isinstance(event_task, dict) and _task_matches_stream_request(event_task, payload):
                            yield make_task_event_response(
                                response_type=proto_modules.task_api.StreamTasksResponse,
                                task_type=_task_message_type(proto_modules),
                                event_type=_task_event_type(row.event_type),
                                task=event_task,
                            )
                        ####
                    ####
                    if heartbeat_seconds > 0 and time.monotonic() >= next_heartbeat:
                        yield make_heartbeat_response(proto_modules.task_api.StreamTasksResponse)
                        next_heartbeat = time.monotonic() + heartbeat_seconds
                    ####
                    await asyncio.sleep(settings.poll_interval_seconds)
                ####
            ####
        ####

        return TaskManagerService()
    ####
####


def _task_payload_from_create_request(payload: dict[str, Any]) -> dict[str, Any]:
    task = payload.get("task")
    if isinstance(task, dict):
        merged = dict(task)
        for key in ("taskId", "task_id"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                merged.setdefault(key, value)
            ####
        ####
        return merged
    ####
    return payload
####


def _status_update_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    status_update = payload.get("statusUpdate") or payload.get("status_update")
    return status_update if isinstance(status_update, dict) else payload
####


def _task_message_type(proto_modules: LatticeProtoModules) -> type[Any] | None:
    if proto_modules.task is not None and hasattr(proto_modules.task, "Task"):
        return proto_modules.task.Task
    ####
    return None
####


def _task_id_from_request(request: Any, payload: dict[str, Any], status_update: dict[str, Any]) -> str | None:
    return (
        get_string_attr(request, "task_id", "taskId")
        or _first_string(payload, "taskId", "task_id")
        or _first_string(status_update, "taskId", "task_id")
        or _nested_string(payload, ["version", "taskId"])
        or _nested_string(payload, ["version", "task_id"])
        or _nested_string(payload, ["statusUpdate", "version", "taskId"])
        or _nested_string(payload, ["statusUpdate", "version", "task_id"])
        or _nested_string(payload, ["status_update", "version", "taskId"])
        or _nested_string(payload, ["status_update", "version", "task_id"])
        or _nested_string(status_update, ["version", "taskId"])
        or _nested_string(status_update, ["version", "task_id"])
    )
####


def _assignee_id_from_payload(payload: dict[str, Any]) -> str | None:
    return (
        _first_string(payload, "assigneeId", "assignee_id", "agentId", "agent_id", "entityId", "entity_id")
        or _nested_string(payload, ["entityIds", "entityIds", 0])
        or _nested_string(payload, ["entity_ids", "entity_ids", 0])
        or _nested_string(payload, ["agentSelector", "entityIds", "entityIds", 0])
        or _nested_string(payload, ["agent_selector", "entity_ids", "entity_ids", 0])
        or _nested_string(payload, ["agent", "entityId"])
        or _nested_string(payload, ["agent", "system", "entityId"])
        or _nested_string(payload, ["assignee", "entityId"])
        or _nested_string(payload, ["relations", "assignee", "entityId"])
        or _nested_string(payload, ["relations", "assignee", "system", "entityId"])
        or _nested_string(payload, ["relations", "assignee", "agent", "system", "entityId"])
    )
####


def _heartbeat_seconds(payload: dict[str, Any], *, default_seconds: float) -> float:
    raw = payload.get("heartbeatIntervalMs") or payload.get("heartbeatIntervalMS") or payload.get("heartbeat_interval_ms")
    if isinstance(raw, int | float):
        return max(0.0, float(raw) / 1000.0)
    ####
    return default_seconds
####


def _task_matches_stream_request(task: dict[str, Any], payload: dict[str, Any]) -> bool:
    parent_task_id = _first_string(payload, "parentTaskId", "parent_task_id")
    if parent_task_id is not None and _nested_string(task, ["relations", "parentTaskId"]) != parent_task_id:
        return False
    ####
    assignee_id = _assignee_id_from_payload(payload)
    if assignee_id is not None and _assignee_id_from_payload(task) != assignee_id:
        return False
    ####
    task_type = _task_type_filter(payload)
    if task_type is not None and _task_type(task) != task_type:
        return False
    ####
    statuses = _status_filter_values(payload)
    if statuses and _status_value(task) not in statuses:
        return False
    ####
    return True
####


def _status_filter_values(payload: dict[str, Any]) -> set[str]:
    status_filter = payload.get("statusFilter") or payload.get("status_filter")
    if not isinstance(status_filter, dict):
        return set()
    ####
    values = status_filter.get("statuses") or status_filter.get("status") or []
    if isinstance(values, str):
        return {values}
    ####
    if isinstance(values, list):
        return {value for value in values if isinstance(value, str)}
    ####
    return set()
####


def _status_value(task: dict[str, Any]) -> str | None:
    status = task.get("status")
    if isinstance(status, dict):
        raw = status.get("status")
        return raw if isinstance(raw, str) else None
    ####
    return status if isinstance(status, str) else None
####


def _is_terminal_task(task: dict[str, Any]) -> bool:
    return _status_value(task) in {"STATUS_DONE_OK", "STATUS_DONE_NOT_OK", "STATUS_CANCELED", "STATUS_CANCELLED"}
####


def _task_type_filter(filters: dict[str, Any]) -> str | None:
    raw = filters.get("taskType") or filters.get("task_type") or filters.get("type")
    if isinstance(raw, str):
        return raw
    ####
    if isinstance(raw, dict):
        candidate = raw.get("type") or raw.get("url") or raw.get("@type") or raw.get("typeUrl") or raw.get("type_url")
        return candidate if isinstance(candidate, str) else None
    ####
    return None
####


def _task_type(task: dict[str, Any]) -> str | None:
    specification = task.get("specification")
    if isinstance(specification, dict):
        raw = specification.get("@type") or specification.get("type") or specification.get("typeUrl") or specification.get("type_url")
        return raw if isinstance(raw, str) else None
    ####
    return None
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


def _nested_string(payload: dict[str, Any], keys: list[str | int]) -> str | None:
    value: object = payload
    for key in keys:
        if isinstance(key, int):
            if not isinstance(value, list) or key >= len(value):
                return None
            ####
            value = value[key]
            continue
        ####
        if not isinstance(value, dict):
            return None
        ####
        value = value.get(key)
    ####
    return value if isinstance(value, str) and value else None
####


def _task_event_type(raw_event_type: str) -> str:
    normalized = raw_event_type.upper()
    if normalized in {"CREATE", "CREATED"}:
        return "CREATE"
    ####
    if normalized in {"CANCELED", "CANCELLED", "CANCEL"}:
        return "CANCELED"
    ####
    if normalized == "PREEXISTING":
        return "PREEXISTING"
    ####
    return "UPDATE"
####
