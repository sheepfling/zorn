from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from zorn.replay import PublicApiTransport, replay_api_operations
from eval_dis.entity_state import DisEntityState, dis_entity_id, entity_state_to_zorn_entity, load_entity_state_jsonl


class EntityPublisher(Protocol):
    def publish_entity(self, entity: dict[str, Any]) -> dict[str, Any]:
        ...
    ####
####


class PublicApiEntityPublisher:
    def __init__(self, transport: PublicApiTransport) -> None:
        self.transport = transport
    ####

    def publish_entity(self, entity: dict[str, Any]) -> dict[str, Any]:
        return self.transport.request_json("PUT", "/api/v1/entities", json_payload=entity)
    ####
####


class StoreEntityPublisher:
    """Internal test helper. Production adapters should use PublicApiEntityPublisher."""

    def __init__(self, store: Any) -> None:
        self.store = store
    ####

    def publish_entity(self, entity: dict[str, Any]) -> dict[str, Any]:
        return self.store.publish(entity)
    ####
####


@dataclass(frozen=True, slots=True)
class DisReplayResult:
    fixture: str
    result: str
    passed: tuple[str, ...]
    failed: tuple[str, ...]
    missing: tuple[str, ...]
    entities: tuple[str, ...]
    events: tuple[dict[str, Any], ...]

    def to_report(self) -> dict[str, Any]:
        return {
            "fixture": self.fixture,
            "result": self.result,
            "passed": list(self.passed),
            "failed": list(self.failed),
            "missing": list(self.missing),
            "entities": list(self.entities),
            "events": list(self.events),
        }
    ####
####


def replay_entity_state_jsonl_with_public_api(path: Path, transport: PublicApiTransport) -> DisReplayResult:
    states = load_entity_state_jsonl(path)
    operations = [
        {"surface": "entity", "operation": "publish", "payload": entity_state_to_zorn_entity(state)}
        for state in states
    ]
    api_result = replay_api_operations(str(path), operations, transport)
    events_response = transport.request_json(
        "POST",
        "/api/v1/entities/events",
        json_payload={"afterSequence": 0, "limit": 1000},
    )
    raw_events = events_response.get("events")
    event_list = [event for event in raw_events if isinstance(event, dict)] if isinstance(raw_events, list) else []
    passed, failed, missing = _evaluate_replay(states, event_list)
    failed.extend(api_result.failed)
    passed = list(dict.fromkeys([*api_result.passed, *passed]))
    return _result_from_parts(
        path=path,
        states=states,
        events=event_list,
        passed=passed,
        failed=failed,
        missing=missing,
    )
####


def replay_entity_state_jsonl(path: Path, publisher: EntityPublisher) -> DisReplayResult:
    states = load_entity_state_jsonl(path)
    events: list[dict[str, Any]] = []
    for state in states:
        entity = entity_state_to_zorn_entity(state)
        published = publisher.publish_entity(entity)
        compat = published.get("_compat")
        if isinstance(compat, dict):
            events.append(
                {
                    "eventType": compat.get("eventType"),
                    "entity": published,
                    "sequence": compat.get("sequence"),
                }
            )
        ####
    ####
    passed, failed, missing = _evaluate_replay(states, events)
    return _result_from_parts(
        path=path,
        states=states,
        events=events,
        passed=passed,
        failed=failed,
        missing=missing,
    )
####


def replay_entity_state_jsonl_with_store(path: Path, store: Any) -> DisReplayResult:
    return replay_entity_state_jsonl(path, StoreEntityPublisher(store))
####


def _result_from_parts(
    *,
    path: Path,
    states: list[DisEntityState],
    events: list[dict[str, Any]],
    passed: list[str],
    failed: list[str],
    missing: list[str],
) -> DisReplayResult:
    result = "passed" if not failed and not missing else "partial"
    return DisReplayResult(
        fixture=str(path),
        result=result,
        passed=tuple(dict.fromkeys(passed)),
        failed=tuple(failed),
        missing=tuple(missing),
        entities=tuple(dict.fromkeys(dis_entity_id(state) for state in states)),
        events=tuple(_events_for_states(states, events)),
    )
####


def _events_for_states(states: list[DisEntityState], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expected_ids = {dis_entity_id(state) for state in states}
    result: list[dict[str, Any]] = []
    for event in events:
        entity = event.get("entity")
        if isinstance(entity, dict) and entity.get("entityId") in expected_ids:
            result.append(event)
        ####
    ####
    return result
####


def _evaluate_replay(states: list[DisEntityState], events: list[dict[str, Any]]) -> tuple[list[str], list[str], list[str]]:
    passed: list[str] = []
    failed: list[str] = []
    missing: list[str] = []

    relevant_events = _events_for_states(states, events)
    expected_ids = {dis_entity_id(state) for state in states}
    event_entities: list[dict[str, Any]] = []
    for event in relevant_events:
        entity = event.get("entity")
        if isinstance(entity, dict):
            event_entities.append(entity)
        ####
    ####
    event_ids = {str(entity.get("entityId")) for entity in event_entities}
    if expected_ids and expected_ids <= event_ids:
        passed.append("dis.entity_state.stable_ids")
    else:
        missing.append("dis.entity_state.stable_ids")
    ####

    event_types = [str(event.get("eventType")) for event in relevant_events]
    if "CREATE" in event_types and "UPDATE" in event_types:
        passed.append("entities.stream.create_update_order")
    else:
        missing.append("entities.stream.create_update_order")
    ####
    if "DELETED" in event_types or any(entity.get("isLive") is False for entity in event_entities):
        passed.append("entities.stream.delete_or_non_live")
    else:
        missing.append("entities.stream.delete_or_non_live")
    ####

    if event_entities and all(_has_location(entity) for entity in event_entities):
        passed.append("entities.location")
    else:
        failed.append("entities.location")
    ####
    if any(_has_velocity(entity) for entity in event_entities):
        passed.append("entities.velocity_enu")
    else:
        missing.append("entities.velocity_enu")
    ####
    if any(_has_attitude(entity) for entity in event_entities):
        passed.append("entities.attitude")
    else:
        missing.append("entities.attitude")
    ####
    if event_entities and all(_has_provenance(entity) for entity in event_entities):
        passed.append("entities.provenance")
    else:
        failed.append("entities.provenance")
    ####

    return passed, failed, missing
####


def _has_location(entity: dict[str, Any]) -> bool:
    position = entity.get("location", {}).get("position") if isinstance(entity.get("location"), dict) else None
    return isinstance(position, dict) and "latitudeDegrees" in position and "longitudeDegrees" in position
####


def _has_velocity(entity: dict[str, Any]) -> bool:
    location = entity.get("location")
    return isinstance(location, dict) and isinstance(location.get("velocityEnu"), dict)
####


def _has_attitude(entity: dict[str, Any]) -> bool:
    location = entity.get("location")
    return isinstance(location, dict) and isinstance(location.get("attitudeEnu"), dict)
####


def _has_provenance(entity: dict[str, Any]) -> bool:
    provenance = entity.get("provenance")
    return isinstance(provenance, dict) and bool(provenance.get("sourceId")) and bool(provenance.get("sourceUpdateTime"))
####
