from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient

from zorn import AppSettings
from zorn.adapters.dis import (
    dis_entity_id,
    entity_state_to_zorn_entity,
    load_entity_state_jsonl,
    replay_entity_state_jsonl_with_public_api,
    replay_entity_state_jsonl_with_store,
)
from zorn.events import entity_stream_event_payload
from zorn.runtime import build_store_bundle
from tests.api_transport import ApiTestClientTransport


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "dis" / "entity_state_replay.jsonl"


def test_dis_entity_state_maps_to_stable_zorn_entity() -> None:
    states = load_entity_state_jsonl(FIXTURE)
    entity = entity_state_to_zorn_entity(states[0])

    assert dis_entity_id(states[0]) == "dis-ex7-site10-app20-entity30"
    assert entity["entityId"] == "dis-ex7-site10-app20-entity30"
    assert entity["aliases"]["dis"]["uid"] == "7:10:20:30"
    assert entity["description"] == "ALPHA-UAV"
    assert entity["milView"]["disposition"] == "DISPOSITION_FRIENDLY"
    assert entity["milView"]["environment"] == "ENVIRONMENT_AIR"
    assert entity["ontology"]["platformType"] == "UAV"
    assert entity["location"]["position"]["latitudeDegrees"] == 35.0001
    assert entity["location"]["velocityEnu"] == {"e": 12.0, "n": 3.0, "u": 0.5}
    assert set(entity["location"]["attitudeEnu"]) == {"w", "x", "y", "z"}
    assert entity["provenance"]["sourceId"] == "dis-ex7-site10-app20"
    assert entity["provenance"]["sourceUpdateTime"] == "2026-06-22T00:00:00Z"


def test_dis_replay_publishes_ordered_events_and_report(tmp_path: Path) -> None:
    settings = AppSettings(
        database_url=f"sqlite:///{tmp_path / 'zorn.db'}",
        object_root=tmp_path / "objects",
    )
    bundle = build_store_bundle(settings)
    result = replay_entity_state_jsonl_with_store(FIXTURE, bundle.entity_store)
    report = result.to_report()

    assert report["result"] == "passed"
    assert report["entities"] == ["dis-ex7-site10-app20-entity30", "dis-ex8-site10-app20-entity30"]
    assert {
        "dis.entity_state.stable_ids",
        "entities.stream.create_update_order",
        "entities.stream.delete_or_non_live",
        "entities.location",
        "entities.velocity_enu",
        "entities.attitude",
        "entities.provenance",
    }.issubset(set(report["passed"]))

    events = report["events"]
    assert [event["eventType"] for event in events] == ["CREATE", "UPDATE", "CREATE", "DELETED"]
    assert [event["entity"]["entityId"] for event in events] == [
        "dis-ex7-site10-app20-entity30",
        "dis-ex7-site10-app20-entity30",
        "dis-ex8-site10-app20-entity30",
        "dis-ex7-site10-app20-entity30",
    ]
    alpha = bundle.entity_store.get("dis-ex7-site10-app20-entity30")
    bravo = bundle.entity_store.get("dis-ex8-site10-app20-entity30")
    assert alpha is not None
    assert bravo is not None
    assert alpha["isLive"] is False
    assert bravo["milView"]["disposition"] == "DISPOSITION_HOSTILE"


def test_dis_replay_events_are_visible_through_entity_event_api(client: TestClient) -> None:
    result = replay_entity_state_jsonl_with_public_api(FIXTURE, ApiTestClientTransport(client))
    assert result.result == "passed"

    response = client.post("/api/v1/entities/events", json={"afterSequence": 0})
    assert response.status_code == 200
    events = response.json()["events"]
    assert [event["eventType"] for event in events] == ["CREATE", "UPDATE", "CREATE", "DELETED"]
    assert events[0]["entity"]["aliases"]["dis"]["uid"] == "7:10:20:30"
    assert events[2]["entity"]["aliases"]["dis"]["uid"] == "8:10:20:30"
    assert events[3]["entity"]["isLive"] is False


def test_deleted_entity_stream_payload_uses_official_deleted_event_name() -> None:
    payload = entity_stream_event_payload(
        event_type="DELETED",
        entity={"entityId": "dis-ex7-site10-app20-entity30"},
        occurred_time="2026-06-22T00:00:03Z",
    )

    assert payload["eventType"] == "EVENT_TYPE_DELETED"
    assert json.loads(payload["data"])["eventType"] == "EVENT_TYPE_DELETED"


def test_dis_replay_command_help_points_to_public_api_target() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "zorn", "replay", "dis", "--help"],
        check=False,
        env={**os.environ},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--target" in result.stdout
