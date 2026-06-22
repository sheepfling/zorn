from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from zorn.db import EventRow
from zorn.replay import replay_api_log
from tests.api_transport import ApiTestClientTransport


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "replay" / "entity_task_object_api.jsonl"


def test_entity_task_object_api_log_replays_through_existing_public_routes(client: TestClient) -> None:
    result = replay_api_log(FIXTURE, ApiTestClientTransport(client))
    report = result.to_report()

    assert report["result"] == "passed"
    assert report["failed"] == []
    assert report["missing"] == []
    assert {
        "entities.publish",
        "tasks.create",
        "tasks.update_status",
        "tasks.cancel",
        "objects.upload",
        "objects.delete",
    } == set(report["passed"])

    entity_response = client.get("/api/v1/entities/replay-asset-01")
    assert entity_response.status_code == 200
    assert entity_response.json()["provenance"]["sourceId"] == "api-replay"

    task_response = client.get("/api/v1/tasks/replay-task-01")
    assert task_response.status_code == 200
    assert task_response.json()["status"]["status"] == "STATUS_CANCELED"

    object_response = client.get("/api/v1/objects/replay/report.txt")
    assert object_response.status_code == 404


def test_task_and_object_operations_are_logged_for_replay_auditing(client: TestClient) -> None:
    replay_api_log(FIXTURE, ApiTestClientTransport(client))

    app = cast(Any, client.app)
    with app.state.database.session() as session:
        rows = session.query(EventRow).order_by(EventRow.id.asc()).all()
    ####
    streams = [(row.stream, row.event_type, row.subject_id) for row in rows]

    assert ("entity", "CREATE", "replay-asset-01") in streams
    assert ("task", "CREATE", "replay-task-01") in streams
    assert ("task", "UPDATE", "replay-task-01") in streams
    assert ("task", "CANCELED", "replay-task-01") in streams
    assert ("object", "CREATE", "replay/report.txt") in streams
    assert ("object", "DELETED", "replay/report.txt") in streams
