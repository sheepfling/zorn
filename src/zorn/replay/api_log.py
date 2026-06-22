from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import base64
import json
from pathlib import Path
from typing import Any, Protocol
from urllib import error, parse, request


class PublicApiTransport(Protocol):
    def request_json(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        ...
    ####
####


@dataclass(frozen=True, slots=True)
class ApiReplayResult:
    fixture: str
    result: str
    passed: tuple[str, ...]
    failed: tuple[str, ...]
    missing: tuple[str, ...]
    operations: tuple[dict[str, Any], ...]

    def to_report(self) -> dict[str, Any]:
        return {
            "fixture": self.fixture,
            "result": self.result,
            "passed": list(self.passed),
            "failed": list(self.failed),
            "missing": list(self.missing),
            "operations": list(self.operations),
        }
    ####
####


class UrlLibPublicApiTransport:
    def __init__(self, target: str, *, token: str | None = None, timeout_seconds: float = 10.0) -> None:
        self.target = target.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds
    ####

    def request_json(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        request_headers = dict(headers or {})
        request_body = body
        if json_payload is not None:
            request_body = json.dumps(json_payload).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        ####
        if self.token:
            request_headers.setdefault("Authorization", f"Bearer {self.token}")
        ####
        url = self.target + path
        api_request = request.Request(url, data=request_body, headers=request_headers, method=method.upper())
        try:
            with request.urlopen(api_request, timeout=self.timeout_seconds) as response:
                raw = response.read()
        except error.HTTPError as exc:
            raw_error = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {path} failed with HTTP {exc.code}: {raw_error}") from exc
        ####
        if not raw:
            return {}
        ####
        decoded = json.loads(raw.decode("utf-8"))
        return decoded if isinstance(decoded, dict) else {"value": decoded}
    ####
####


def load_api_replay_jsonl(path: Path) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(path.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        ####
        try:
            operation = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
        ####
        if not isinstance(operation, dict):
            raise ValueError(f"{path}:{line_number}: expected JSON object")
        ####
        operations.append(operation)
    ####
    return operations
####


def replay_api_log(path: Path, transport: PublicApiTransport) -> ApiReplayResult:
    operations = load_api_replay_jsonl(path)
    return replay_api_operations(str(path), operations, transport)
####


def replay_api_operations(
    fixture: str,
    operations: list[dict[str, Any]],
    transport: PublicApiTransport,
) -> ApiReplayResult:
    passed: list[str] = []
    failed: list[str] = []
    observed: list[dict[str, Any]] = []
    for index, operation in enumerate(operations, start=1):
        try:
            response = _apply_operation(operation, transport)
        except Exception as exc:
            failed.append(f"{_operation_name(operation)}:{index}:{exc}")
            continue
        ####
        observed.append({"index": index, "operation": _operation_name(operation), "response": response})
        passed.append(_capability_for_operation(operation))
    ####
    unique_passed = tuple(dict.fromkeys(passed))
    result = "passed" if not failed else "partial"
    return ApiReplayResult(
        fixture=fixture,
        result=result,
        passed=unique_passed,
        failed=tuple(failed),
        missing=tuple(_missing_capabilities(unique_passed)),
        operations=tuple(observed),
    )
####


def operations_for_entities(entities: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"surface": "entity", "operation": "publish", "payload": entity} for entity in entities]
####


def _apply_operation(operation: dict[str, Any], transport: PublicApiTransport) -> dict[str, Any]:
    surface = str(operation.get("surface") or "")
    action = str(operation.get("operation") or "")
    if surface == "entity" and action == "publish":
        return transport.request_json("PUT", "/api/v1/entities", json_payload=_payload(operation))
    ####
    if surface == "task" and action == "create":
        return transport.request_json("POST", "/api/v1/tasks", json_payload=_payload(operation))
    ####
    if surface == "task" and action == "update_status":
        task_id = _required_string(operation, "task_id", "taskId")
        return transport.request_json("PUT", f"/api/v1/tasks/{parse.quote(task_id)}/status", json_payload=_payload(operation))
    ####
    if surface == "task" and action == "cancel":
        task_id = _required_string(operation, "task_id", "taskId")
        return transport.request_json("PUT", f"/api/v1/tasks/{parse.quote(task_id)}/cancel", json_payload=_payload(operation))
    ####
    if surface == "object" and action == "put":
        object_path = _required_string(operation, "object_path", "objectPath")
        content = _content_bytes(operation)
        content_type = str(operation.get("content_type") or operation.get("contentType") or "application/octet-stream")
        return transport.request_json(
            "POST",
            f"/api/v1/objects/{parse.quote(object_path)}",
            body=content,
            headers={"Content-Type": content_type},
        )
    ####
    if surface == "object" and action == "delete":
        object_path = _required_string(operation, "object_path", "objectPath")
        return transport.request_json("DELETE", f"/api/v1/objects/{parse.quote(object_path)}")
    ####
    raise ValueError(f"unsupported replay operation: {surface}.{action}")
####


def _payload(operation: dict[str, Any]) -> dict[str, Any]:
    payload = operation.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("operation payload must be an object")
    ####
    return payload
####


def _required_string(operation: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = operation.get(key)
        if isinstance(value, str) and value:
            return value
        ####
    ####
    raise ValueError(f"missing required string field: {keys[0]}")
####


def _content_bytes(operation: dict[str, Any]) -> bytes:
    raw_base64 = operation.get("content_base64") or operation.get("contentBase64")
    if isinstance(raw_base64, str):
        return base64.b64decode(raw_base64)
    ####
    raw_text = operation.get("content_text") or operation.get("contentText")
    if isinstance(raw_text, str):
        return raw_text.encode("utf-8")
    ####
    raise ValueError("object put operation requires content_base64 or content_text")
####


def _operation_name(operation: dict[str, Any]) -> str:
    return f"{operation.get('surface')}.{operation.get('operation')}"
####


def _capability_for_operation(operation: dict[str, Any]) -> str:
    surface = str(operation.get("surface") or "")
    action = str(operation.get("operation") or "")
    return {
        ("entity", "publish"): "entities.publish",
        ("task", "create"): "tasks.create",
        ("task", "update_status"): "tasks.update_status",
        ("task", "cancel"): "tasks.cancel",
        ("object", "put"): "objects.upload",
        ("object", "delete"): "objects.delete",
    }.get((surface, action), f"{surface}.{action}")
####


def _missing_capabilities(passed: tuple[str, ...]) -> list[str]:
    required = {"entities.publish", "tasks.create", "tasks.update_status", "tasks.cancel", "objects.upload", "objects.delete"}
    return sorted(required - set(passed))
####
