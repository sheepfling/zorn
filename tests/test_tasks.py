from __future__ import annotations

from fastapi.testclient import TestClient


def test_task_lifecycle(client: TestClient) -> None:
    task = {
        "taskId": "task-alpha",
        "displayName": "Investigate point",
        "assigneeId": "asset-alpha",
        "specification": {"@type": "type.example/Investigate", "point": {"lat": 34.0, "lon": -118.0}},
    }

    create_response = client.post("/api/v1/tasks", json=task)
    assert create_response.status_code == 201
    assert create_response.json()["taskId"] == "task-alpha"

    get_response = client.get("/api/v1/tasks/task-alpha")
    assert get_response.status_code == 200
    assert get_response.json()["displayName"] == "Investigate point"

    status_response = client.put("/api/v1/tasks/task-alpha/status", json={"status": "EXECUTING"})
    assert status_response.status_code == 200
    assert status_response.json()["status"]["status"] == "EXECUTING"

    query_response = client.post("/api/v1/tasks/query", json={"assigneeId": "asset-alpha"})
    assert query_response.status_code == 200
    assert query_response.json()["tasks"][0]["taskId"] == "task-alpha"

    cancel_response = client.put("/api/v1/tasks/task-alpha/cancel", json={"reason": "operator request"})
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"]["status"] == "STATUS_CANCELED"
####
