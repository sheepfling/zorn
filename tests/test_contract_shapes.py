from __future__ import annotations

from fastapi.testclient import TestClient

from zorn.compat import heartbeat_seconds_from_payload
from zorn.routes.tasks import _task_matches_stream_request


def test_entity_poll_shape_and_component_filter(client: TestClient) -> None:
    client.put(
        "/api/v1/entities",
        json={
            "entityId": "track-1",
            "isLive": True,
            "description": "Preserved but filtered",
            "location": {"position": {"latitudeDegrees": 1.0, "longitudeDegrees": 2.0}},
            "provenance": {"sourceUpdateTime": "2026-06-21T00:00:00Z"},
        },
    )

    response = client.post(
        "/api/v1/entities/events",
        json={"sessionToken": "0", "componentsToInclude": ["location"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sessionToken"] == "1"
    assert payload["entityEvents"][0]["entity"]["entityId"] == "track-1"
    assert "location" in payload["entityEvents"][0]["entity"]
    assert "description" not in payload["entityEvents"][0]["entity"]
####


def test_entity_stream_preexisting_only(client: TestClient) -> None:
    client.put("/api/v1/entities", json={"entityId": "preexisting-track", "isLive": True})

    with client.stream(
        "POST",
        "/api/v1/entities/stream",
        json={"preExistingOnly": True, "heartbeatIntervalMS": 50},
    ) as response:
        text = response.read().decode("utf-8")
    ####

    assert response.status_code == 200
    assert "event: entity" in text
    assert '"event":"entity"' in text
    assert '"eventType":"EVENT_TYPE_PREEXISTING"' in text
    assert '"data":"{' in text
    assert "preexisting-track" in text
####


def test_entity_stale_source_update_time_is_ignored(client: TestClient) -> None:
    newer = {
        "entityId": "ordered-track",
        "description": "newer",
        "provenance": {"sourceUpdateTime": "2026-06-21T01:00:00Z"},
    }
    older = {
        "entityId": "ordered-track",
        "description": "older",
        "provenance": {"sourceUpdateTime": "2026-06-21T00:00:00Z"},
    }

    client.put("/api/v1/entities", json=newer)
    ignored = client.put("/api/v1/entities", json=older)
    fetched = client.get("/api/v1/entities/ordered-track")

    assert ignored.json()["_compat"]["ignoredStaleUpdate"] is True
    assert fetched.json()["description"] == "newer"
####


def test_task_contract_defaults_and_agent_listen(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tasks",
        json={
            "taskId": "task-contract-1",
            "displayName": "Investigate Contract",
            "relations": {"assignee": {"system": {"entityId": "agent-1"}}},
            "specification": {"@type": "type.googleapis.com/example.Investigate"},
        },
    )

    assert response.status_code == 201
    task = response.json()
    assert task["version"]["taskId"] == "task-contract-1"
    assert task["status"]["status"] == "STATUS_CREATED"

    listen = client.post("/api/v1/agent/listen", json={"agentSelector": {"entityIds": ["agent-1"]}})
    assert listen.status_code == 200
    assert listen.json()["executeRequest"]["task"]["version"]["taskId"] == "task-contract-1"
    assert listen.json()["execute_request"]["task"]["version"]["task_id"] == "task-contract-1"
    assert listen.json()["execute_request"]["task"]["display_name"] == "Investigate Contract"
    assert listen.json()["execute_request"]["task"]["specification"]["type"] == "type.googleapis.com/example.Investigate"
    assert listen.json()["execute_request"]["task"]["relations"]["assignee"]["system"]["entity_id"] == "agent-1"

    second_listen = client.post("/api/v1/agent/listen", json={"agentSelector": {"entityIds": ["agent-1"]}})
    assert second_listen.status_code == 200
    assert "executeRequest" not in second_listen.json()
    assert "execute_request" not in second_listen.json()
####


def test_task_status_update_accepts_next_status_version(client: TestClient) -> None:
    create = client.post(
        "/api/v1/tasks",
        json={"taskId": "task-contract-2", "relations": {"assignee": {"system": {"entityId": "agent-2"}}}},
    )

    assert create.status_code == 201
    update = client.put(
        "/api/v1/tasks/task-contract-2/status",
        json={"statusVersion": 2, "newStatus": {"status": "STATUS_EXECUTING"}},
    )

    assert update.status_code == 200
    assert update.json()["version"]["statusVersion"] == 2
    assert update.json()["status"]["status"] == "STATUS_EXECUTING"
####


def test_task_query_supports_statuses_assignee_and_next_page_token_shape(client: TestClient) -> None:
    created = client.post(
        "/api/v1/tasks",
        json={
            "taskId": "task-query-filter-1",
            "displayName": "Task query filter",
            "relations": {"assignee": {"system": {"entityId": "agent-query"}}},
            "specification": {"@type": "type.googleapis.com/example.Investigate"},
        },
    )
    assert created.status_code == 201

    updated = client.put(
        "/api/v1/tasks/task-query-filter-1/status",
        json={"statusVersion": 1, "newStatus": {"status": "STATUS_EXECUTING"}},
    )
    assert updated.status_code == 200

    query = client.post(
        "/api/v1/tasks/query",
        json={
            "statuses": ["STATUS_EXECUTING"],
            "assignee": {"system": {"entityId": "agent-query"}},
            "task_type": "type.googleapis.com/example.Investigate",
        },
    )
    assert query.status_code == 200
    payload = query.json()
    assert payload["next_page_token"] is None
    assert [task["taskId"] for task in payload["tasks"]] == ["task-query-filter-1"]
####


def test_task_query_supports_nested_status_filter_and_type_url_shape(client: TestClient) -> None:
    created = client.post(
        "/api/v1/tasks",
        json={
            "taskId": "task-query-filter-2",
            "displayName": "Task query nested filter",
            "relations": {"assignee": {"system": {"entityId": "agent-query-2"}}},
            "specification": {"typeUrl": "type.googleapis.com/example.VisualId"},
        },
    )
    assert created.status_code == 201

    updated = client.put(
        "/api/v1/tasks/task-query-filter-2/status",
        json={"statusVersion": 1, "newStatus": {"status": "STATUS_EXECUTING"}},
    )
    assert updated.status_code == 200

    query = client.post(
        "/api/v1/tasks/query",
        json={
            "statusFilter": {"status": "STATUS_EXECUTING"},
            "assignee": {"system": {"entityId": "agent-query-2"}},
            "taskType": {"typeUrl": "type.googleapis.com/example.VisualId"},
        },
    )
    assert query.status_code == 200
    payload = query.json()
    assert [task["taskId"] for task in payload["tasks"]] == ["task-query-filter-2"]
####


def test_entity_override_updates_effective_value(client: TestClient) -> None:
    client.put(
        "/api/v1/entities",
        json={
            "entityId": "track-override-1",
            "milView": {"disposition": "DISPOSITION_UNKNOWN"},
            "provenance": {"sourceUpdateTime": "2026-06-21T00:00:00Z"},
        },
    )

    override = client.put(
        "/api/v1/entities/track-override-1/override/mil_view.disposition",
        json={"entity": {"milView": {"disposition": "DISPOSITION_SUSPICIOUS"}}},
    )

    assert override.status_code == 200
    assert override.json()["milView"]["disposition"] == "DISPOSITION_SUSPICIOUS"
    assert override.json()["overrides"]["mil_view.disposition"] == "DISPOSITION_SUSPICIOUS"
####


def test_object_contract_metadata_shape(client: TestClient) -> None:
    upload = client.post(
        "/api/v1/objects/captures/one.bin",
        content=b"abc",
        headers={"Content-Type": "application/octet-stream", "Time-To-Live": "1000000000"},
    )

    assert upload.status_code == 200
    assert upload.json()["content_identifier"]["path"] == "captures/one.bin"
    assert upload.json()["size_bytes"] == 3

    listing = client.get("/api/v1/objects", params={"prefix": "captures", "maxPageSize": 10})
    assert listing.status_code == 200
    assert listing.json()["path_metadatas"][0]["content_identifier"]["path"] == "captures/one.bin"
    assert listing.json()["next_page_token"] is None
####


def test_zero_heartbeat_is_preserved_for_rest_entity_streams() -> None:
    assert heartbeat_seconds_from_payload(
        {"heartbeatIntervalMS": 0},
        default_seconds=15.0,
        millisecond_keys=("heartbeatIntervalMS", "heartbeatIntervalMs"),
    ) == 0.0


def test_zero_heartbeat_is_preserved_for_rest_task_streams() -> None:
    assert heartbeat_seconds_from_payload(
        {"heartbeatIntervalMs": 0},
        default_seconds=15.0,
        millisecond_keys=("heartbeatIntervalMs", "heartbeatIntervalMS"),
    ) == 0.0


def test_zero_heartbeat_is_preserved_for_second_based_stream_inputs() -> None:
    assert heartbeat_seconds_from_payload(
        {"heartbeatSeconds": 0},
        default_seconds=15.0,
        millisecond_keys=("heartbeatIntervalMs", "heartbeatIntervalMS"),
    ) == 0.0
####


def test_task_stream_filter_helper_matches_status_assignee_and_type() -> None:
    matching_task = {
        "taskId": "task-stream-match",
        "status": {"status": "STATUS_EXECUTING"},
        "relations": {"assignee": {"system": {"entityId": "agent-stream-filter"}}},
        "specification": {"@type": "type.googleapis.com/example.Investigate"},
    }
    other_task = {
        "taskId": "task-stream-other",
        "status": {"status": "STATUS_CREATED"},
        "relations": {"assignee": {"system": {"entityId": "other-agent"}}},
        "specification": {"@type": "type.googleapis.com/example.Other"},
    }
    request = {
        "assignee": {"system": {"entityId": "agent-stream-filter"}},
        "statusFilter": {"statuses": ["STATUS_EXECUTING"]},
        "taskType": {"type": "type.googleapis.com/example.Investigate"},
    }

    assert _task_matches_stream_request(matching_task, request) is True
    assert _task_matches_stream_request(other_task, request) is False
####
