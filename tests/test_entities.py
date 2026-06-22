from __future__ import annotations

from fastapi.testclient import TestClient


def test_publish_get_and_poll_entity_events(client: TestClient) -> None:
    entity = {
        "entityId": "asset-alpha",
        "description": "Example entity",
        "isLive": True,
        "location": {"position": {"latitudeDegrees": 34.0, "longitudeDegrees": -118.0}},
        "unknownComponent": {"preserveMe": True},
    }

    publish_response = client.put("/api/v1/entities", json=entity)
    assert publish_response.status_code == 200
    assert publish_response.json()["entityId"] == "asset-alpha"

    get_response = client.get("/api/v1/entities/asset-alpha")
    assert get_response.status_code == 200
    assert get_response.json()["unknownComponent"] == {"preserveMe": True}

    poll_response = client.post("/api/v1/entities/events", json={"afterSequence": 0})
    assert poll_response.status_code == 200
    events = poll_response.json()["events"]
    assert events[0]["eventType"] == "CREATE"
    assert events[0]["entity"]["entityId"] == "asset-alpha"
####


def test_entity_override_round_trip(client: TestClient) -> None:
    client.put("/api/v1/entities", json={"entityId": "asset-bravo", "isLive": True})

    override_response = client.put(
        "/api/v1/entities/asset-bravo/override/location.position",
        json={"latitudeDegrees": 35.0, "longitudeDegrees": -117.0},
    )
    assert override_response.status_code == 200
    assert override_response.json()["overrides"]["location.position"]["latitudeDegrees"] == 35.0

    remove_response = client.delete("/api/v1/entities/asset-bravo/override/location.position")
    assert remove_response.status_code == 200
    assert "location.position" not in remove_response.json()["overrides"]
####
