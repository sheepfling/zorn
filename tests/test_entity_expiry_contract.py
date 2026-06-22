from __future__ import annotations

from fastapi.testclient import TestClient


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
