from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any, cast

from google.protobuf import json_format
from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message
from google.protobuf.timestamp_pb2 import Timestamp


EVENT_HINTS: dict[str, tuple[str, ...]] = {
    "PREEXISTING": ("PREEXISTING",),
    "CREATE": ("CREATE", "CREATED"),
    "UPDATE": ("UPDATE", "UPDATED"),
    "DELETED": ("DELETE", "DELETED", "REMOVED"),
    "CANCELED": ("CANCEL", "CANCELED", "CANCELLED"),
    "HEARTBEAT": ("HEARTBEAT",),
    "EXECUTE_REQUEST": ("EXECUTE", "EXECUTE_REQUEST"),
    "CANCEL_REQUEST": ("CANCEL", "CANCEL_REQUEST"),
    "COMPLETE_REQUEST": ("COMPLETE", "COMPLETE_REQUEST"),
}


def message_to_dict(message: Message) -> dict[str, Any]:
    raw = json_format.MessageToDict(
        message,
        preserving_proto_field_name=False,
    )
    return raw if isinstance(raw, dict) else {}
####


def parse_dict(message_type: type[Message], payload: dict[str, Any]) -> Message:
    message = message_type()
    if message.DESCRIPTOR.full_name == "google.protobuf.Any":
        _assign_any(message, strip_private_fields(payload))
        return message
    ####
    try:
        json_format.ParseDict(strip_private_fields(payload), message, ignore_unknown_fields=True)
        return message
    except Exception:
        tolerant_message = message_type()
        merge_dict_tolerant(tolerant_message, strip_private_fields(payload))
        return tolerant_message
    ####
####


def parse_dict_or_empty(message_type: type[Message], *payloads: dict[str, Any]) -> Message:
    for payload in payloads:
        try:
            return parse_dict(message_type, strip_private_fields(payload))
        except Exception:
            continue
        ####
    ####
    return message_type()
####


def merge_dict_tolerant(message: Message, payload: dict[str, Any]) -> None:
    field_map = _field_lookup(message)
    for raw_name, raw_value in payload.items():
        field = field_map.get(raw_name)
        if field is None:
            continue
        ####
        _assign_field(message, field, raw_value)
    ####
####


def strip_private_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if not key.startswith("_")}
####


def get_string_attr(message: object, *names: str) -> str | None:
    for name in names:
        value = getattr(message, name, None)
        if isinstance(value, str) and value:
            return value
        ####
    ####
    return None
####


def has_field(message: Message, field_name: str) -> bool:
    return field_name in message.DESCRIPTOR.fields_by_name
####


def get_repeated_strings(message: Message, field_name: str) -> list[str]:
    if not has_field(message, field_name):
        return []
    ####
    raw = getattr(message, field_name)
    return [value for value in raw if isinstance(value, str)]
####


def copy_parsed_submessage(
    parent: Message,
    field_name: str,
    payload: dict[str, Any],
) -> bool:
    if not has_field(parent, field_name):
        return False
    ####
    submessage = getattr(parent, field_name)
    try:
        json_format.ParseDict(strip_private_fields(payload), submessage, ignore_unknown_fields=True)
        return True
    except Exception:
        try:
            merge_dict_tolerant(submessage, strip_private_fields(payload))
            return True
        except Exception:
            return False
        ####
    ####
####


def set_timestamp_now(message: Message, *field_names: str) -> None:
    timestamp = Timestamp()
    timestamp.GetCurrentTime()
    for field_name in field_names:
        if has_field(message, field_name):
            getattr(message, field_name).CopyFrom(timestamp)
            return
        ####
    ####
####


def set_enum_by_hint(message: Message, field_names: Iterable[str], event_type: str) -> None:
    hints = EVENT_HINTS.get(event_type, (event_type,))
    for field_name in field_names:
        field = message.DESCRIPTOR.fields_by_name.get(field_name)
        if field is None or field.enum_type is None:
            continue
        ####
        for enum_value in field.enum_type.values:
            enum_name = enum_value.name.upper()
            if any(hint.upper() in enum_name for hint in hints):
                setattr(message, field.name, enum_value.number)
                return
            ####
        ####
    ####
####


def make_heartbeat_response(response_type: type[Message]) -> Message:
    response = response_type()
    if copy_parsed_submessage(response, "heartbeat", {"timestamp": _timestamp_dict()}):
        return response
    ####
    if has_field(response, "heartbeat"):
        heartbeat = getattr(response, "heartbeat")
        set_timestamp_now(heartbeat, "timestamp", "time")
    ####
    return response
####


def make_entity_event_response(
    *,
    response_type: type[Message],
    entity_type: type[Message],
    event_type: str,
    entity: dict[str, Any],
) -> Message:
    response = response_type()
    entity_event_payload = {
        "eventType": _event_type_json(event_type),
        "entity": strip_private_fields(entity),
        "time": _timestamp_dict(),
    }
    for payload in (
        {"entityEvent": entity_event_payload},
        {"entity_event": entity_event_payload},
    ):
        try:
            return parse_dict(response_type, payload)
        except Exception:
            continue
        ####
    ####
    if has_field(response, "entity_event"):
        event = getattr(response, "entity_event")
        _fill_event_message(event, object_field="entity", object_payload=entity, object_type=entity_type, event_type=event_type)
    ####
    return response
####


def make_task_event_response(
    *,
    response_type: type[Message],
    task_type: type[Message] | None,
    event_type: str,
    task: dict[str, Any],
) -> Message:
    response = response_type()
    task_event_payload = {
        "eventType": _event_type_json(event_type),
        "task": strip_private_fields(task),
        "time": _timestamp_dict(),
    }
    for payload in (
        {"taskEvent": task_event_payload},
        {"task_event": task_event_payload},
    ):
        try:
            return parse_dict(response_type, payload)
        except Exception:
            continue
        ####
    ####
    if has_field(response, "task_event"):
        event = getattr(response, "task_event")
        _fill_event_message(event, object_field="task", object_payload=task, object_type=task_type, event_type=event_type)
    ####
    return response
####


def make_agent_response(
    *,
    response_type: type[Message],
    task_type: type[Message] | None,
    request_type: str,
    task: dict[str, Any] | None = None,
) -> Message:
    if task is None:
        return make_heartbeat_response(response_type)
    ####
    request_field = {
        "ExecuteRequest": "executeRequest",
        "CancelRequest": "cancelRequest",
        "CompleteRequest": "completeRequest",
    }.get(request_type, "executeRequest")
    response = response_type()
    snake_field = _camel_to_snake(request_field)
    if has_field(response, snake_field):
        submessage = getattr(response, snake_field)
        _fill_event_message(
            submessage,
            object_field="task",
            object_payload=task,
            object_type=task_type,
            event_type=request_type.upper(),
        )
        return response
    ####
    request_payload = {request_field: {"task": strip_private_fields(task)}}
    snake_request_payload = {_camel_to_snake(request_field): {"task": strip_private_fields(task)}}
    for payload in (
        {"request": request_payload},
        {"request": snake_request_payload},
        {request_field: {"task": strip_private_fields(task)}},
        {_camel_to_snake(request_field): {"task": strip_private_fields(task)}},
    ):
        try:
            return parse_dict(response_type, payload)
        except Exception:
            continue
        ####
    ####
    if has_field(response, "request"):
        wrapper = getattr(response, "request")
        if has_field(wrapper, snake_field):
            submessage = getattr(wrapper, snake_field)
            _fill_event_message(submessage, object_field="task", object_payload=task, object_type=task_type, event_type=request_type.upper())
        ####
    ####
    return response
####


def make_manual_control_frame_response(
    *,
    response_type: type[Message],
    frame: dict[str, Any],
) -> Message:
    for payload in ({"frame": strip_private_fields(frame)},):
        try:
            return parse_dict(response_type, payload)
        except Exception:
            continue
        ####
    ####
    response = response_type()
    if has_field(response, "frame"):
        copy_parsed_submessage(response, "frame", frame)
    ####
    return response
####


def _fill_event_message(
    event: Message,
    *,
    object_field: str,
    object_payload: dict[str, Any],
    object_type: type[Message] | None,
    event_type: str,
) -> None:
    set_enum_by_hint(event, ("event_type", "type", "request_type"), event_type)
    set_timestamp_now(event, "time", "timestamp", "event_time", "update_time")
    if object_type is not None and has_field(event, object_field):
        parsed = parse_dict_or_empty(object_type, object_payload)
        getattr(event, object_field).CopyFrom(parsed)
    elif has_field(event, object_field):
        copy_parsed_submessage(event, object_field, object_payload)
    ####
####


def _field_lookup(message: Message) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for field in message.DESCRIPTOR.fields:
        fields[field.name] = field
        if field.json_name:
            fields[field.json_name] = field
        ####
    ####
    return fields
####


def _assign_field(message: Message, field: Any, raw_value: Any) -> None:
    if field.label == FieldDescriptor.LABEL_REPEATED:
        _assign_repeated_field(message, field, raw_value)
        return
    ####
    if field.type == FieldDescriptor.TYPE_MESSAGE:
        submessage = getattr(message, field.name)
        _assign_message_value(submessage, raw_value)
        return
    ####
    value = _coerce_scalar(field, raw_value)
    if value is not None:
        setattr(message, field.name, value)
    ####
####


def _assign_repeated_field(message: Message, field: Any, raw_value: Any) -> None:
    repeated = getattr(message, field.name)
    if _is_map_field(field):
        if isinstance(raw_value, dict):
            for key, value in raw_value.items():
                repeated[key] = value
            ####
        ####
        return
    ####
    if not isinstance(raw_value, list):
        return
    ####
    if field.type == FieldDescriptor.TYPE_MESSAGE:
        for item in raw_value:
            submessage = repeated.add()
            _assign_message_value(submessage, item)
        ####
        return
    ####
    for item in raw_value:
        value = _coerce_scalar(field, item)
        if value is not None:
            repeated.append(value)
        ####
    ####
####


def _assign_message_value(message: Message, raw_value: Any) -> None:
    if message.DESCRIPTOR.full_name == "google.protobuf.Any":
        _assign_any(message, raw_value)
        return
    ####
    if message.DESCRIPTOR.full_name == "google.protobuf.Timestamp":
        _assign_timestamp(message, raw_value)
        return
    ####
    if isinstance(raw_value, dict):
        merge_dict_tolerant(message, raw_value)
    ####
####


def _assign_any(message: Message, raw_value: Any) -> None:
    if not isinstance(raw_value, dict):
        return
    ####
    type_url = raw_value.get("@type") or raw_value.get("typeUrl") or raw_value.get("type_url")
    if isinstance(type_url, str):
        setattr(message, "type_url", type_url)
    ####
    raw_bytes = raw_value.get("value")
    if isinstance(raw_bytes, bytes):
        setattr(message, "value", raw_bytes)
        return
    ####
    if isinstance(raw_bytes, str):
        setattr(message, "value", _decode_any_value(raw_bytes))
        return
    ####
    remainder = {key: value for key, value in raw_value.items() if key not in {"@type", "typeUrl", "type_url"}}
    if remainder:
        setattr(message, "value", json.dumps(remainder, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    ####
####


def _assign_timestamp(message: Message, raw_value: Any) -> None:
    timestamp = cast(Timestamp, message)
    if isinstance(raw_value, str):
        parsed = _parse_rfc3339(raw_value)
        if parsed is not None:
            timestamp.FromDatetime(parsed)
        ####
        return
    ####
    if isinstance(raw_value, dict):
        seconds = raw_value.get("seconds")
        nanos = raw_value.get("nanos")
        if isinstance(seconds, int):
            setattr(message, "seconds", seconds)
        ####
        if isinstance(nanos, int):
            setattr(message, "nanos", nanos)
        ####
    ####
####


def _coerce_scalar(field: FieldDescriptor, raw_value: Any) -> Any:
    if raw_value is None:
        return None
    ####
    if field.type == FieldDescriptor.TYPE_ENUM:
        if isinstance(raw_value, str) and field.enum_type is not None:
            enum_value = field.enum_type.values_by_name.get(raw_value)
            return enum_value.number if enum_value is not None else None
        ####
        return int(raw_value) if isinstance(raw_value, int) else None
    ####
    if field.type == FieldDescriptor.TYPE_BOOL:
        return bool(raw_value)
    ####
    if field.type in {
        FieldDescriptor.TYPE_DOUBLE,
        FieldDescriptor.TYPE_FLOAT,
    }:
        return float(raw_value) if isinstance(raw_value, int | float) else None
    ####
    if field.type in {
        FieldDescriptor.TYPE_INT32,
        FieldDescriptor.TYPE_INT64,
        FieldDescriptor.TYPE_UINT32,
        FieldDescriptor.TYPE_UINT64,
        FieldDescriptor.TYPE_SINT32,
        FieldDescriptor.TYPE_SINT64,
        FieldDescriptor.TYPE_FIXED32,
        FieldDescriptor.TYPE_FIXED64,
        FieldDescriptor.TYPE_SFIXED32,
        FieldDescriptor.TYPE_SFIXED64,
    }:
        return int(raw_value) if isinstance(raw_value, int | float) else None
    ####
    if field.type == FieldDescriptor.TYPE_BYTES:
        if isinstance(raw_value, bytes):
            return raw_value
        ####
        if isinstance(raw_value, str):
            return _decode_any_value(raw_value)
        ####
        return None
    ####
    if field.type == FieldDescriptor.TYPE_STRING:
        return str(raw_value)
    ####
    return raw_value
####


def _is_map_field(field: FieldDescriptor) -> bool:
    return bool(field.message_type is not None and field.message_type.GetOptions().map_entry)
####


def _decode_any_value(value: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        return value.encode("utf-8")
    ####
####


def _parse_rfc3339(value: str) -> datetime | None:
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    ####
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    ####
    return parsed.astimezone(UTC)
####


def _event_type_json(event_type: str) -> str:
    return f"EVENT_TYPE_{event_type.upper()}"
####


def _timestamp_dict() -> dict[str, int]:
    timestamp = Timestamp()
    timestamp.GetCurrentTime()
    return {"seconds": timestamp.seconds, "nanos": timestamp.nanos}
####


def _camel_to_snake(value: str) -> str:
    result: list[str] = []
    for char in value:
        if char.isupper() and result:
            result.append("_")
        ####
        result.append(char.lower())
    ####
    return "".join(result)
####
