from __future__ import annotations

from datetime import timedelta
import time

from fastapi.testclient import TestClient

from zorn.time_utils import to_iso, utc_now


def test_live_entity_rejects_past_expiry(client: TestClient) -> None:
    response = client.put(
        "/api/v1/entities",
        json={
            "entityId": "expired-live-entity",
            "isLive": True,
            "expiryTime": "2020-01-01T00:00:00Z",
        },
    )

    assert response.status_code == 400
    assert "expiryTime must be in the future" in response.json()["detail"]
####


def test_entity_publish_with_is_live_false_emits_deleted_event_and_final_state(client: TestClient) -> None:
    created = client.put(
        "/api/v1/entities",
        json={"entityId": "entity-delete-contract", "isLive": True},
    )
    assert created.status_code == 200

    deleted = client.put(
        "/api/v1/entities",
        json={"entityId": "entity-delete-contract", "isLive": False},
    )
    assert deleted.status_code == 200
    assert deleted.json()["isLive"] is False
    assert deleted.json()["_compat"]["eventType"] == "DELETED"

    fetched = client.get("/api/v1/entities/entity-delete-contract")
    assert fetched.status_code == 200
    assert fetched.json()["isLive"] is False

    events = client.post("/api/v1/entities/events", json={"afterSequence": 0}).json()["events"]
    assert [event["eventType"] for event in events] == ["CREATE", "DELETED"]
####


def test_entity_expiry_emits_deleted_event_and_marks_entity_non_live(client: TestClient) -> None:
    expiry_time = to_iso(utc_now() + timedelta(milliseconds=250))
    created = client.put(
        "/api/v1/entities",
        json={
            "entityId": "entity-expiry-contract",
            "isLive": True,
            "expiryTime": expiry_time,
        },
    )
    assert created.status_code == 200

    time.sleep(0.3)

    fetched = client.get("/api/v1/entities/entity-expiry-contract")
    assert fetched.status_code == 200
    assert fetched.json()["isLive"] is False

    events = client.post("/api/v1/entities/events", json={"afterSequence": 0}).json()["events"]
    assert [event["eventType"] for event in events] == ["CREATE", "DELETED"]
    assert events[-1]["entity"]["entityId"] == "entity-expiry-contract"
    assert events[-1]["entity"]["isLive"] is False
####
