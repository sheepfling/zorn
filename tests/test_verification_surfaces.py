from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_details_and_backend_metadata_are_machine_readable(client: TestClient) -> None:
    health = client.get("/healthz/details")
    assert health.status_code == 200
    health_payload = health.json()
    assert health_payload["schemaVersion"] == "zorn.health.details.v1"
    assert health_payload["backendMode"] == "sqlite"
    assert health_payload["authMode"] == "none"
    assert health_payload["enabledSurfaces"]["rest"]["entities"] is True

    capabilities = client.get("/api/v1/backend/capabilities")
    assert capabilities.status_code == 200
    capabilities_payload = capabilities.json()
    assert capabilities_payload["schemaVersion"] == "zorn.backend.capabilities.v1"
    assert "entities.events.snapshot" in capabilities_payload["supported"]
    assert "verification.state" in capabilities_payload["supported"]

    compatibility = client.get("/api/v1/backend/compatibility")
    assert compatibility.status_code == 200
    compatibility_payload = compatibility.json()
    assert compatibility_payload["schemaVersion"] == "zorn.backend.compatibility.v1"
    assert compatibility_payload["streamGuarantees"]["ordering"]


def test_entity_lifecycle_snapshot_and_verification_state_use_public_api(client: TestClient) -> None:
    create = client.put(
        "/api/v1/entities",
        json={
            "entityId": "fastdis-alpha",
            "description": "FastDIS alpha",
            "isLive": True,
            "location": {"position": {"latitudeDegrees": 35.0, "longitudeDegrees": -117.0}},
            "provenance": {"sourceId": "fastdis-test", "sourceUpdateTime": "2026-06-22T00:00:00Z"},
        },
    )
    assert create.status_code == 200

    update = client.put(
        "/api/v1/entities",
        json={
            "entityId": "fastdis-alpha",
            "description": "FastDIS alpha moved",
            "isLive": True,
            "location": {"position": {"latitudeDegrees": 35.1, "longitudeDegrees": -117.2}},
            "provenance": {"sourceId": "fastdis-test", "sourceUpdateTime": "2026-06-22T00:00:01Z"},
        },
    )
    assert update.status_code == 200

    delete = client.request("DELETE", "/api/v1/entities/fastdis-alpha", json={"deleteReason": "test complete"})
    assert delete.status_code == 200
    assert delete.json()["isLive"] is False
    assert delete.json()["_compat"]["eventType"] == "DELETED"

    snapshot = client.get("/api/v1/entities/events/snapshot")
    assert snapshot.status_code == 200
    snapshot_payload = snapshot.json()
    assert snapshot_payload["schemaVersion"] == "zorn.events.snapshot.v1"
    assert snapshot_payload["stream"] == "entity"
    assert [event["eventType"] for event in snapshot_payload["events"]] == ["CREATE", "UPDATE", "DELETED"]
    assert [event["sequence"] for event in snapshot_payload["events"]] == [1, 2, 3]

    verification = client.get("/api/v1/verification/state")
    assert verification.status_code == 200
    verification_payload = verification.json()
    assert verification_payload["schemaVersion"] == "zorn.verification.state.v1"
    assert verification_payload["entities"][0]["entityId"] == "fastdis-alpha"
    assert verification_payload["entities"][0]["isLive"] is False
    assert verification_payload["events"]["entities"]["count"] == 3


def test_task_event_snapshot_is_stable(client: TestClient) -> None:
    create = client.post(
        "/api/v1/tasks",
        json={"taskId": "task-snapshot", "displayName": "Snapshot task", "assigneeId": "fastdis-alpha"},
    )
    assert create.status_code == 201
    update = client.put("/api/v1/tasks/task-snapshot/status", json={"status": "EXECUTING"})
    assert update.status_code == 200
    cancel = client.put("/api/v1/tasks/task-snapshot/cancel", json={"reason": "done"})
    assert cancel.status_code == 200

    snapshot = client.get("/api/v1/tasks/events/snapshot")
    assert snapshot.status_code == 200
    payload = snapshot.json()
    assert payload["schemaVersion"] == "zorn.events.snapshot.v1"
    assert payload["stream"] == "task"
    assert [event["eventType"] for event in payload["events"]] == ["CREATE", "UPDATE", "CANCELED"]
    assert payload["sequenceStart"] == 1
    assert payload["sequenceEnd"] == 4


def test_verification_routes_are_declared_in_openapi(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]

    assert "/healthz/details" in paths
    assert "/api/v1/entities/events/snapshot" in paths
    assert "/api/v1/tasks/events/snapshot" in paths
    assert "/api/v1/verification/state" in paths
    assert "/api/v1/backend/capabilities" in paths
    assert "/api/v1/backend/compatibility" in paths
