from __future__ import annotations

import hashlib
import shutil
from datetime import timedelta
from pathlib import Path
from typing import Any, List

from sqlalchemy import delete, select

from .compat import ENTITY_INTERNAL_STATE_KEY, entity_public_payload, object_metadata_wire, validate_object_path
from .db import Database, EntityRow, ObjectRow, TaskRow
from .events import add_event, event_to_payload, poll_events
from .identity import assignee_id_from_task, entity_id_from_payload, source_update_time_from_entity, task_id_from_payload
from .time_utils import expiry_from_ttl_seconds, parse_iso_datetime, to_iso, utc_now

TERMINAL_TASK_STATUSES: set[str] = {
    "SUCCEEDED",
    "FAILED",
    "CANCELED",
    "CANCELLED",
    "DONE_OK",
    "DONE_NOT_OK",
    "STATUS_DONE_OK",
    "STATUS_DONE_NOT_OK",
    "STATUS_CANCELED",
    "STATUS_CANCELLED",
}


class TaskStatusConflict(RuntimeError):
    pass
####


class TerminalTaskUpdateError(RuntimeError):
    pass
####


class EntityStore:
    def __init__(
        self,
        database: Database,
        *,
        allow_generated_ids: bool = True,
        enforce_source_update_time: bool = True,
    ) -> None:
        self.database = database
        self.allow_generated_ids = allow_generated_ids
        self.enforce_source_update_time = enforce_source_update_time
    ####

    def publish(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = dict(payload)
        entity_id = entity_id_from_payload(payload, allow_generated=self.allow_generated_ids)
        payload.setdefault("entityId", entity_id)
        payload.setdefault("entity_id", entity_id)
        now = utc_now()
        expiry_time = parse_iso_datetime(payload.get("expiryTime") or payload.get("expiry_time"))
        explicit_live = payload.get("isLive") if "isLive" in payload else payload.get("is_live")
        is_live = bool(explicit_live) if explicit_live is not None else True
        no_expiry = bool(payload.get("noExpiry") if "noExpiry" in payload else payload.get("no_expiry", False))
        if expiry_time is not None and expiry_time <= now and is_live:
            raise ValueError("expiryTime must be in the future for live entity publishes")
        ####
        if expiry_time is not None and expiry_time > now + timedelta(days=30) and not no_expiry:
            raise ValueError("expiryTime must be less than 30 days in the future unless noExpiry is true")
        ####
        payload["isLive"] = is_live
        payload.setdefault("is_live", is_live)
        event_type = "UPDATE"
        with self.database.session() as session:
            existing = session.get(EntityRow, entity_id)
            if existing is not None and self._is_stale_update(payload, dict(existing.payload)):
                existing_payload = dict(existing.payload)
                existing_payload.setdefault("_compat", {})
                existing_payload["_compat"].update({"ignoredStaleUpdate": True, "sequence": existing.sequence})
                return existing_payload
            ####
            if existing is None:
                event_type = "CREATE" if is_live else "DELETED"
                row = EntityRow(
                    entity_id=entity_id,
                    payload=payload,
                    is_live=is_live,
                    created_at=now,
                    updated_at=now,
                    expiry_time=expiry_time,
                    sequence=0,
                )
                session.add(row)
            else:
                event_type = "DELETED" if existing.is_live and not is_live else "UPDATE"
                existing.payload = payload
                existing.is_live = is_live
                existing.updated_at = now
                existing.expiry_time = expiry_time
                row = existing
            ####
            event_payload = {"eventType": event_type, "entity": payload, "time": to_iso(now)}
            event = add_event(
                session,
                stream="entity",
                subject_id=entity_id,
                event_type=event_type,
                payload=event_payload,
            )
            row.sequence = event.id
            session.commit()
            payload["_compat"] = {"sequence": event.id, "eventType": event_type}
            return payload
        ####
    ####

    def get(self, entity_id: str) -> dict[str, Any] | None:
        with self.database.session() as session:
            self._expire_due_entities(session, entity_ids=[entity_id])
            row = session.get(EntityRow, entity_id)
            return self._public_entity(row.payload) if row is not None else None
        ####
    ####

    def list_live(self) -> list[dict[str, Any]]:
        with self.database.session() as session:
            self._expire_due_entities(session)
            now = utc_now()
            rows = session.scalars(
                select(EntityRow)
                .where(EntityRow.is_live.is_(True))
                .where((EntityRow.expiry_time.is_(None)) | (EntityRow.expiry_time > now))
                .order_by(EntityRow.sequence.asc())
            ).all()
            return [self._public_entity(row.payload) for row in rows]
        ####
    ####

    def poll(self, after_sequence: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        with self.database.session() as session:
            self._expire_due_entities(session)
            return [event_to_payload(row) for row in poll_events(
                session,
                stream="entity",
                after_sequence=after_sequence,
                limit=limit,
            )]
        ####
    ####

    def override_field(self, entity_id: str, field_path: str, value: Any) -> dict[str, Any] | None:
        with self.database.session() as session:
            row = session.get(EntityRow, entity_id)
            if row is None:
                return None
            ####
            payload = dict(row.payload)
            overrides = dict(payload.get("overrides") or {})
            self._capture_override_base(payload, field_path)
            override_value = self._extract_override_value(field_path, value)
            overrides[field_path] = override_value
            payload["overrides"] = overrides
            self._set_field_path(payload, field_path, override_value)
            row.payload = payload
            row.updated_at = utc_now()
            event = add_event(
                session,
                stream="entity",
                subject_id=entity_id,
                event_type="UPDATE",
                payload={"eventType": "UPDATE", "entity": payload, "overrideFieldPath": field_path},
            )
            row.sequence = event.id
            session.commit()
            return self._public_entity(payload)
        ####
    ####

    def remove_override(self, entity_id: str, field_path: str) -> dict[str, Any] | None:
        with self.database.session() as session:
            row = session.get(EntityRow, entity_id)
            if row is None:
                return None
            ####
            payload = dict(row.payload)
            overrides = dict(payload.get("overrides") or {})
            overrides.pop(field_path, None)
            payload["overrides"] = overrides
            self._restore_override_base(payload, field_path)
            row.payload = payload
            row.updated_at = utc_now()
            event = add_event(
                session,
                stream="entity",
                subject_id=entity_id,
                event_type="UPDATE",
                payload={"eventType": "UPDATE", "entity": payload, "removedOverrideFieldPath": field_path},
            )
            row.sequence = event.id
            session.commit()
            return self._public_entity(payload)
        ####
    ####

    def _is_stale_update(self, incoming: dict[str, Any], existing: dict[str, Any]) -> bool:
        if not self.enforce_source_update_time:
            return False
        ####
        incoming_time = parse_iso_datetime(source_update_time_from_entity(incoming))
        existing_time = parse_iso_datetime(source_update_time_from_entity(existing))
        if incoming_time is None or existing_time is None:
            return False
        ####
        return incoming_time <= existing_time
    ####

    def _expire_due_entities(self, session: Any, *, entity_ids: list[str] | None = None) -> None:
        now = utc_now()
        statement = select(EntityRow).where(EntityRow.is_live.is_(True)).where(EntityRow.expiry_time.is_not(None))
        if entity_ids:
            statement = statement.where(EntityRow.entity_id.in_(entity_ids))
        ####
        rows = session.scalars(statement).all()
        expired = False
        for row in rows:
            expiry_time = parse_iso_datetime(row.expiry_time)
            if expiry_time is None or expiry_time > now:
                continue
            ####
            payload = dict(row.payload)
            payload["isLive"] = False
            payload["is_live"] = False
            row.payload = payload
            row.is_live = False
            row.updated_at = now
            event = add_event(
                session,
                stream="entity",
                subject_id=row.entity_id,
                event_type="DELETED",
                payload={"eventType": "DELETED", "entity": payload, "time": to_iso(now)},
            )
            row.sequence = event.id
            expired = True
        ####
        if expired:
            session.commit()
        ####
    ####

    @staticmethod
    def _extract_override_value(field_path: str, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        ####
        resolved = EntityStore._get_field_path(value, field_path)
        return value if resolved is None else resolved
    ####

    @staticmethod
    def _public_entity(payload: dict[str, Any]) -> dict[str, Any]:
        return entity_public_payload(dict(payload))
    ####

    @staticmethod
    def _capture_override_base(payload: dict[str, Any], field_path: str) -> None:
        internal = EntityStore._internal_state(payload)
        override_bases = dict(internal.get("overrideBaseValues") or {})
        if field_path in override_bases:
            return
        ####
        exists = EntityStore._has_field_path(payload, field_path)
        override_bases[field_path] = {
            "exists": exists,
            "value": EntityStore._get_field_path(payload, field_path) if exists else None,
        }
        internal["overrideBaseValues"] = override_bases
        payload[ENTITY_INTERNAL_STATE_KEY] = internal
    ####

    @staticmethod
    def _restore_override_base(payload: dict[str, Any], field_path: str) -> None:
        internal = EntityStore._internal_state(payload)
        override_bases = dict(internal.get("overrideBaseValues") or {})
        base = override_bases.pop(field_path, None)
        if base is None:
            EntityStore._delete_field_path(payload, field_path)
        else:
            if bool(base.get("exists")):
                EntityStore._set_field_path(payload, field_path, base.get("value"))
            else:
                EntityStore._delete_field_path(payload, field_path)
            ####
        ####
        if override_bases:
            internal["overrideBaseValues"] = override_bases
            payload[ENTITY_INTERNAL_STATE_KEY] = internal
        else:
            internal.pop("overrideBaseValues", None)
            if internal:
                payload[ENTITY_INTERNAL_STATE_KEY] = internal
            else:
                payload.pop(ENTITY_INTERNAL_STATE_KEY, None)
            ####
        ####
    ####

    @staticmethod
    def _internal_state(payload: dict[str, Any]) -> dict[str, Any]:
        raw = payload.get(ENTITY_INTERNAL_STATE_KEY)
        return dict(raw) if isinstance(raw, dict) else {}
    ####

    @staticmethod
    def _get_field_path(payload: dict[str, Any], field_path: str) -> Any:
        current: Any = payload
        for segment in field_path.split("."):
            if not isinstance(current, dict):
                return None
            ####
            key = EntityStore._resolve_key(current, segment)
            if key is None:
                return None
            ####
            current = current.get(key)
        ####
        return current
    ####

    @staticmethod
    def _has_field_path(payload: dict[str, Any], field_path: str) -> bool:
        current: Any = payload
        for segment in field_path.split("."):
            if not isinstance(current, dict):
                return False
            ####
            key = EntityStore._resolve_key(current, segment)
            if key is None:
                return False
            ####
            current = current.get(key)
        ####
        return True
    ####

    @staticmethod
    def _set_field_path(payload: dict[str, Any], field_path: str, value: Any) -> None:
        current: dict[str, Any] = payload
        segments = field_path.split(".")
        for segment in segments[:-1]:
            key = EntityStore._resolve_key(current, segment) or segment
            nested = current.get(key)
            if not isinstance(nested, dict):
                nested = {}
                current[key] = nested
            ####
            current = nested
        ####
        leaf = EntityStore._resolve_key(current, segments[-1]) or segments[-1]
        current[leaf] = value
    ####

    @staticmethod
    def _delete_field_path(payload: dict[str, Any], field_path: str) -> None:
        current: dict[str, Any] | None = payload
        segments = field_path.split(".")
        for segment in segments[:-1]:
            if current is None:
                return
            ####
            key = EntityStore._resolve_key(current, segment)
            if key is None:
                return
            ####
            nested = current.get(key)
            if not isinstance(nested, dict):
                return
            ####
            current = nested
        ####
        if current is None:
            return
        ####
        leaf = EntityStore._resolve_key(current, segments[-1])
        if leaf is not None:
            current.pop(leaf, None)
        ####
    ####

    @staticmethod
    def _resolve_key(payload: dict[str, Any], segment: str) -> str | None:
        candidates = [segment, _snake_to_camel(segment), _camel_to_snake(segment)]
        for candidate in candidates:
            if candidate in payload:
                return candidate
            ####
        ####
        return None
    ####
####


def _snake_to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])
####


def _camel_to_snake(value: str) -> str:
    result: list[str] = []
    for char in value:
        if char.isupper():
            result.extend(["_", char.lower()])
        else:
            result.append(char)
        ####
    ####
    return "".join(result).lstrip("_")
####


class TaskStore:
    def __init__(self, database: Database) -> None:
        self.database = database
        self._agent_delivery_sequences: dict[str, int] = {}
    ####

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = self._normalize_new_task(dict(payload))
        task_id = task_id_from_payload(payload)
        status = self._status_from_payload(payload, default="STATUS_CREATED")
        assignee_id = assignee_id_from_task(payload)
        now = utc_now()
        with self.database.session() as session:
            existing = session.get(TaskRow, task_id)
            if existing is not None:
                raise ValueError(f"Task already exists: {task_id}")
            ####
            row = TaskRow(
                task_id=task_id,
                payload=payload,
                status=status,
                assignee_id=assignee_id,
                created_at=now,
                updated_at=now,
                is_terminal=status in TERMINAL_TASK_STATUSES,
                sequence=0,
            )
            session.add(row)
            event = add_event(
                session,
                stream="task",
                subject_id=task_id,
                event_type="CREATE",
                payload={"eventType": "CREATE", "task": payload},
            )
            row.sequence = event.id
            if not bool(payload.get("isExecutedElsewhere", payload.get("is_executed_elsewhere", False))):
                add_event(
                    session,
                    stream="agent",
                    subject_id=assignee_id or "*",
                    event_type="ExecuteRequest",
                    payload={
                        "executeRequest": {"task": payload},
                        "execute_request": {"task": payload},
                        "requestType": "ExecuteRequest",
                        "request_type": "ExecuteRequest",
                        "task": payload,
                        "assigneeId": assignee_id,
                        "assignee_id": assignee_id,
                    },
                )
            ####
            session.commit()
            payload["_compat"] = {"sequence": event.id, "eventType": "CREATE"}
            return payload
        ####
    ####

    def get(self, task_id: str) -> dict[str, Any] | None:
        with self.database.session() as session:
            row = session.get(TaskRow, task_id)
            return dict(row.payload) if row is not None else None
        ####
    ####

    def query(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        filters = filters or {}
        status_filters = self._query_status_values(filters)
        assignee_filter = (
            self._query_scalar(filters, "assigneeId")
            or self._query_scalar(filters, "assignee_id")
            or self._query_assignee_id(filters)
        )
        task_type_filter = self._task_type_filter(filters)
        with self.database.session() as session:
            statement = select(TaskRow).order_by(TaskRow.sequence.asc())
            if status_filters:
                statement = statement.where(TaskRow.status.in_(status_filters))
            ####
            if isinstance(assignee_filter, str) and assignee_filter:
                statement = statement.where(TaskRow.assignee_id == assignee_filter)
            ####
            rows = session.scalars(statement).all()
            tasks = [dict(row.payload) for row in rows]
            if task_type_filter is not None:
                tasks = [task for task in tasks if self._task_type(task) == task_type_filter]
            ####
            return tasks
        ####
    ####

    def update_status(
        self,
        task_id: str,
        payload: dict[str, Any],
        *,
        enforce_version: bool = False,
    ) -> dict[str, Any] | None:
        status_payload = self._normalize_status_payload(dict(payload))
        with self.database.session() as session:
            row = session.get(TaskRow, task_id)
            if row is None:
                return None
            ####
            if row.is_terminal:
                raise TerminalTaskUpdateError(f"Task is already terminal: {task_id}")
            ####
            task_payload = dict(row.payload)
            version = dict(task_payload.get("version") or {})
            current_status_version = int(version.get("statusVersion") or version.get("status_version") or 1)
            expected_status_version = self._expected_status_version(payload)
            if enforce_version and expected_status_version is None:
                raise TaskStatusConflict("status update requires current statusVersion")
            ####
            if expected_status_version is not None and expected_status_version < current_status_version:
                raise TaskStatusConflict(
                    f"statusVersion mismatch for {task_id}: expected {current_status_version}, got {expected_status_version}"
                )
            ####
            task_payload["status"] = status_payload
            last_update_time = to_iso(utc_now())
            task_payload["lastUpdateTime"] = last_update_time
            task_payload["last_update_time"] = last_update_time
            version["taskId"] = task_id
            version["task_id"] = task_id
            version["statusVersion"] = (
                max(current_status_version + 1, expected_status_version)
                if isinstance(expected_status_version, int)
                else current_status_version + 1
            )
            version["status_version"] = version["statusVersion"]
            version.setdefault("definitionVersion", 1)
            version.setdefault("definition_version", version["definitionVersion"])
            task_payload["version"] = version
            status = self._status_from_payload(status_payload, default=row.status)
            row.payload = task_payload
            row.status = status
            row.updated_at = utc_now()
            row.is_terminal = status in TERMINAL_TASK_STATUSES
            event = add_event(
                session,
                stream="task",
                subject_id=task_id,
                event_type="UPDATE",
                payload={"eventType": "UPDATE", "task": task_payload, "status": status_payload},
            )
            row.sequence = event.id
            session.commit()
            return task_payload
        ####
    ####

    def cancel(
        self,
        task_id: str,
        payload: dict[str, Any] | None = None,
        *,
        terminal_status: str = "STATUS_CANCELED",
        error_code: str | None = None,
    ) -> dict[str, Any] | None:
        cancel_payload = dict(payload or {})
        with self.database.session() as session:
            row = session.get(TaskRow, task_id)
            if row is None:
                return None
            ####
            if row.is_terminal:
                raise TerminalTaskUpdateError(f"Task is already terminal: {task_id}")
            ####
            task_payload = dict(row.payload)
            status_value = str(cancel_payload.get("status") or terminal_status)
            status_payload: dict[str, Any] = {"status": status_value, "cancel": cancel_payload}
            if error_code is not None:
                status_payload["taskError"] = {"code": error_code, "message": cancel_payload.get("reason") or "cancelled"}
                status_payload["task_error"] = status_payload["taskError"]
            ####
            task_payload["status"] = status_payload
            last_update_time = to_iso(utc_now())
            task_payload["lastUpdateTime"] = last_update_time
            task_payload["last_update_time"] = last_update_time
            version = dict(task_payload.get("version") or {})
            version["taskId"] = task_id
            version["task_id"] = task_id
            version["statusVersion"] = int(version.get("statusVersion") or version.get("status_version") or 1) + 1
            version["status_version"] = version["statusVersion"]
            version.setdefault("definitionVersion", 1)
            version.setdefault("definition_version", version["definitionVersion"])
            task_payload["version"] = version
            row.payload = task_payload
            row.status = status_value
            row.updated_at = utc_now()
            row.is_terminal = True
            event = add_event(
                session,
                stream="task",
                subject_id=task_id,
                event_type="CANCELED",
                payload={"eventType": "CANCELED", "task": task_payload, "cancel": cancel_payload},
            )
            row.sequence = event.id
            add_event(
                session,
                stream="agent",
                subject_id=row.assignee_id or "*",
                event_type="CancelRequest",
                payload={
                    "cancelRequest": {"task": task_payload, "cancel": cancel_payload},
                    "cancel_request": {"task": task_payload, "cancel": cancel_payload},
                    "requestType": "CancelRequest",
                    "request_type": "CancelRequest",
                    "task": task_payload,
                },
            )
            session.commit()
            return task_payload
        ####
    ####

    def list_open(self, assignee_id: str | None = None) -> list[dict[str, Any]]:
        with self.database.session() as session:
            statement = select(TaskRow).where(TaskRow.is_terminal.is_(False)).order_by(TaskRow.sequence.asc())
            if assignee_id is not None:
                statement = statement.where((TaskRow.assignee_id == assignee_id) | (TaskRow.assignee_id.is_(None)))
            ####
            rows = session.scalars(statement).all()
            return [dict(row.payload) for row in rows]
        ####
    ####

    def poll_tasks(self, after_sequence: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        with self.database.session() as session:
            return [event_to_payload(row) for row in poll_events(
                session,
                stream="task",
                after_sequence=after_sequence,
                limit=limit,
            )]
        ####
    ####

    def poll_agent(self, after_sequence: int = 0, limit: int = 100, assignee_id: str | None = None) -> list[dict[str, Any]]:
        with self.database.session() as session:
            subject_ids = [assignee_id, "*"] if assignee_id is not None else None
            return [event_to_payload(row) for row in poll_events(
                session,
                stream="agent",
                after_sequence=after_sequence,
                limit=limit,
                subject_ids=subject_ids,
            )]
        ####
    ####

    def claim_agent_request(self, assignee_id: str | None = None) -> dict[str, Any] | None:
        delivery_key = assignee_id or "*"
        after_sequence = self._agent_delivery_sequences.get(delivery_key, 0)
        events = self.poll_agent(after_sequence=after_sequence, limit=100, assignee_id=assignee_id)
        for event in events:
            sequence = int(event.get("sequence") or after_sequence)
            self._agent_delivery_sequences[delivery_key] = max(after_sequence, sequence)
            if any(
                key in event
                for key in (
                    "executeRequest",
                    "execute_request",
                    "cancelRequest",
                    "cancel_request",
                    "completeRequest",
                    "complete_request",
                )
            ):
                return event
            ####
        ####
        return None
    ####

    @staticmethod
    def _normalize_new_task(payload: dict[str, Any]) -> dict[str, Any]:
        task_id = task_id_from_payload(payload)
        now = to_iso(utc_now())
        version = dict(payload.get("version") or {})
        version.setdefault("taskId", task_id)
        version.setdefault("task_id", task_id)
        version.setdefault("definitionVersion", 1)
        version.setdefault("definition_version", 1)
        version.setdefault("statusVersion", 1)
        version.setdefault("status_version", 1)
        payload["version"] = version
        payload.setdefault("taskId", task_id)
        payload.setdefault("task_id", task_id)
        payload.setdefault("createTime", now)
        payload.setdefault("create_time", now)
        payload.setdefault("lastUpdateTime", now)
        payload.setdefault("last_update_time", now)
        payload["status"] = TaskStore._normalize_status_payload(payload.get("status") if isinstance(payload.get("status"), dict) else {"status": payload.get("status") or "STATUS_CREATED"})
        display_name = payload.get("displayName")
        if isinstance(display_name, str) and display_name and "display_name" not in payload:
            payload["display_name"] = display_name
        ####
        if isinstance(payload.get("specification"), dict):
            specification = dict(payload["specification"])
            if isinstance(specification.get("@type"), str) and "type" not in specification:
                specification["type"] = specification["@type"]
            elif isinstance(specification.get("type"), str) and "@type" not in specification:
                specification["@type"] = specification["type"]
            ####
            payload["specification"] = specification
        ####
        relations = payload.get("relations")
        if isinstance(relations, dict):
            normalized_relations = dict(relations)
            assignee = normalized_relations.get("assignee")
            if isinstance(assignee, dict):
                normalized_assignee = dict(assignee)
                system = normalized_assignee.get("system")
                if isinstance(system, dict):
                    normalized_system = dict(system)
                    entity_id = normalized_system.get("entityId")
                    if isinstance(entity_id, str) and entity_id and "entity_id" not in normalized_system:
                        normalized_system["entity_id"] = entity_id
                    ####
                    service_name = normalized_system.get("serviceName")
                    if isinstance(service_name, str) and service_name and "service_name" not in normalized_system:
                        normalized_system["service_name"] = service_name
                    ####
                    normalized_assignee["system"] = normalized_system
                ####
                normalized_relations["assignee"] = normalized_assignee
            ####
            payload["relations"] = normalized_relations
        ####
        if "author" in payload and "createdBy" not in payload and "created_by" not in payload:
            payload["createdBy"] = payload["author"]
            payload["created_by"] = payload["author"]
        ####
        payload.setdefault("createdBy", {"system": {"serviceName": "local-compat-sandbox", "service_name": "local-compat-sandbox"}})
        payload.setdefault("created_by", payload["createdBy"])
        payload.setdefault("lastUpdatedBy", payload["createdBy"])
        payload.setdefault("last_updated_by", payload["createdBy"])
        return payload
    ####

    @staticmethod
    def _normalize_status_payload(payload: dict[str, Any] | object) -> dict[str, Any]:
        if isinstance(payload, dict):
            nested_status = payload.get("newStatus") if isinstance(payload.get("newStatus"), dict) else payload.get("new_status")
            if not isinstance(nested_status, dict):
                candidate_status = payload.get("status")
                if isinstance(candidate_status, dict):
                    nested_status = candidate_status
                ####
            ####
            result = dict(nested_status) if isinstance(nested_status, dict) else dict(payload)
            status = (
                result.get("status")
                or result.get("state")
                or result.get("taskStatus")
                or payload.get("status")
                or payload.get("state")
                or payload.get("taskStatus")
                or "STATUS_CREATED"
            )
            result["status"] = str(status)
            return result
        ####
        return {"status": str(payload or "STATUS_CREATED")}
    ####


    @staticmethod
    def _expected_status_version(payload: dict[str, Any]) -> int | None:
        for key in ("statusVersion", "status_version"):
            value = payload.get(key)
            if isinstance(value, int):
                return value
            ####
        ####
        version = payload.get("version")
        if isinstance(version, dict):
            for key in ("statusVersion", "status_version"):
                value = version.get(key)
                if isinstance(value, int):
                    return value
                ####
            ####
        ####
        return None
    ####

    @staticmethod
    def _status_from_payload(payload: dict[str, Any], default: str) -> str:
        raw = payload.get("status") or payload.get("state") or payload.get("taskStatus")
        if isinstance(raw, dict):
            raw = raw.get("status") or raw.get("state")
        ####
        return raw if isinstance(raw, str) and raw else default
    ####

    @staticmethod
    def _query_scalar(filters: dict[str, Any], key: str) -> str | None:
        value = filters.get(key)
        if isinstance(value, str):
            return value
        ####
        if isinstance(value, dict):
            nested = value.get("value") or value.get("eq")
            return nested if isinstance(nested, str) else None
        ####
        return None
    ####

    @staticmethod
    def _query_status_values(filters: dict[str, Any]) -> list[str]:
        scalar = TaskStore._query_scalar(filters, "status")
        if isinstance(scalar, str) and scalar:
            return [scalar]
        ####
        raw = filters.get("statuses")
        if isinstance(raw, list):
            return [value for value in raw if isinstance(value, str) and value]
        ####
        status_filter = filters.get("statusFilter") or filters.get("status_filter")
        if not isinstance(raw, dict) and isinstance(status_filter, dict):
            raw = status_filter
        ####
        if isinstance(raw, dict):
            nested = raw.get("statuses") or raw.get("values") or raw.get("status") or []
            if isinstance(nested, str):
                return [nested] if nested else []
            ####
            if isinstance(nested, list):
                return [value for value in nested if isinstance(value, str) and value]
            ####
        ####
        return []
    ####

    @staticmethod
    def _query_assignee_id(filters: dict[str, Any]) -> str | None:
        raw = filters.get("assignee")
        if isinstance(raw, str):
            return raw
        ####
        if isinstance(raw, dict):
            system = raw.get("system")
            if isinstance(system, dict):
                entity_id = system.get("entityId") or system.get("entity_id")
                return entity_id if isinstance(entity_id, str) and entity_id else None
            ####
            entity_id = raw.get("entityId") or raw.get("entity_id")
            return entity_id if isinstance(entity_id, str) and entity_id else None
        ####
        return None
    ####

    @staticmethod
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

    @staticmethod
    def _task_type(task: dict[str, Any]) -> str | None:
        specification = task.get("specification")
        if isinstance(specification, dict):
            raw = specification.get("@type") or specification.get("type") or specification.get("typeUrl") or specification.get("type_url")
            return raw if isinstance(raw, str) else None
        ####
        return None
    ####
####


class ObjectStore:
    def __init__(self, database: Database, root: Path, max_object_bytes: int) -> None:
        self.database = database
        self.root = root
        self.max_object_bytes = max_object_bytes
        self.root.mkdir(parents=True, exist_ok=True)
    ####

    def put(
        self,
        *,
        object_path: str,
        content: bytes,
        content_type: str,
        ttl_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if len(content) > self.max_object_bytes:
            raise ValueError(f"Object is too large: {len(content)} bytes")
        ####
        normalized_path = self._normalize_path(object_path)
        file_path = self._file_path(normalized_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        checksum = hashlib.sha256(content).hexdigest()
        file_path.write_bytes(content)
        now = utc_now()
        expiry_time = expiry_from_ttl_seconds(ttl_seconds)
        metadata_json = dict(metadata or {})
        with self.database.session() as session:
            row = session.get(ObjectRow, normalized_path)
            event_type = "CREATE"
            if row is None:
                row = ObjectRow(
                    object_path=normalized_path,
                    checksum_sha256=checksum,
                    size_bytes=len(content),
                    content_type=content_type,
                    created_at=now,
                    updated_at=now,
                    expiry_time=expiry_time,
                    metadata_json=metadata_json,
                )
                session.add(row)
            else:
                event_type = "UPDATE"
                row.checksum_sha256 = checksum
                row.size_bytes = len(content)
                row.content_type = content_type
                row.updated_at = now
                row.expiry_time = expiry_time
                row.metadata_json = metadata_json
            ####
            add_event(
                session,
                stream="object",
                subject_id=normalized_path,
                event_type=event_type,
                payload={
                    "eventType": event_type,
                    "object": self._row_to_payload(row),
                },
            )
            session.commit()
            return self._row_to_payload(row)
        ####
    ####

    def get(self, object_path: str) -> tuple[dict[str, Any], bytes] | None:
        normalized_path = self._normalize_path(object_path)
        with self.database.session() as session:
            row = session.get(ObjectRow, normalized_path)
            if row is None:
                return None
            ####
            if self._prune_if_expired(session, row):
                return None
            ####
            file_path = self._file_path(normalized_path)
            if not file_path.exists():
                return None
            ####
            return self._row_to_payload(row), file_path.read_bytes()
        ####
    ####

    def metadata(self, object_path: str) -> dict[str, Any] | None:
        normalized_path = self._normalize_path(object_path)
        with self.database.session() as session:
            row = session.get(ObjectRow, normalized_path)
            if row is not None and self._prune_if_expired(session, row):
                return None
            ####
            return self._row_to_payload(row) if row is not None else None
        ####
    ####

    def delete(self, object_path: str) -> bool:
        normalized_path = self._normalize_path(object_path)
        file_path = self._file_path(normalized_path)
        with self.database.session() as session:
            row = session.get(ObjectRow, normalized_path)
            existed = row is not None
            if row is not None:
                add_event(
                    session,
                    stream="object",
                    subject_id=normalized_path,
                    event_type="DELETED",
                    payload={"eventType": "DELETED", "object": self._row_to_payload(row)},
                )
            ####
            session.execute(delete(ObjectRow).where(ObjectRow.object_path == normalized_path))
            session.commit()
        ####
        if file_path.exists():
            if file_path.is_dir():
                shutil.rmtree(file_path)
            else:
                file_path.unlink()
            ####
        ####
        return existed
    ####

    def list(self, prefix: str | None = None, limit: int = 100) -> List[dict[str, Any]]:
        normalized_prefix = self._normalize_prefix(prefix)
        with self.database.session() as session:
            statement = select(ObjectRow).order_by(ObjectRow.object_path.asc()).limit(max(1, min(limit, 1000)))
            if normalized_prefix:
                statement = statement.where(ObjectRow.object_path.startswith(normalized_prefix))
            ####
            rows = session.scalars(statement).all()
            active_rows: list[ObjectRow] = []
            for row in rows:
                if self._prune_if_expired(session, row):
                    continue
                ####
                active_rows.append(row)
            ####
            return [self._row_to_payload(row) for row in active_rows]
        ####
    ####

    def list_wire(self, prefix: str | None = None, limit: int = 100) -> List[dict[str, Any]]:
        return [object_metadata_wire(metadata) for metadata in self.list(prefix=prefix, limit=limit)]
    ####

    def _file_path(self, object_path: str) -> Path:
        return self.root / object_path
    ####

    def _prune_if_expired(self, session: Any, row: ObjectRow) -> bool:
        expiry_time = parse_iso_datetime(row.expiry_time)
        if expiry_time is None or expiry_time > utc_now():
            return False
        ####
        add_event(
            session,
            stream="object",
            subject_id=row.object_path,
            event_type="DELETED",
            payload={"eventType": "DELETED", "object": self._row_to_payload(row)},
        )
        session.execute(delete(ObjectRow).where(ObjectRow.object_path == row.object_path))
        session.commit()
        file_path = self._file_path(row.object_path)
        if file_path.exists():
            if file_path.is_dir():
                shutil.rmtree(file_path)
            else:
                file_path.unlink()
            ####
        ####
        return True
    ####

    @staticmethod
    def _normalize_prefix(prefix: str | None) -> str | None:
        if prefix is None or not prefix.strip():
            return None
        ####
        return ObjectStore._normalize_path(prefix)
    ####

    @staticmethod
    def _normalize_path(object_path: str) -> str:
        return validate_object_path(object_path)
    ####

    @staticmethod
    def _row_to_payload(row: ObjectRow) -> dict[str, Any]:
        return {
            "objectPath": row.object_path,
            "checksumSha256": row.checksum_sha256,
            "sizeBytes": row.size_bytes,
            "contentType": row.content_type,
            "createdTime": to_iso(row.created_at),
            "updatedTime": to_iso(row.updated_at),
            "expiryTime": to_iso(row.expiry_time) if row.expiry_time is not None else None,
            "metadata": dict(row.metadata_json),
        }
    ####
####
