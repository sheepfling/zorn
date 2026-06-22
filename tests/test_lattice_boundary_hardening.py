from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from zorn import AppSettings, build_app


ROOT = Path(__file__).resolve().parents[1]


def _client(tmp_path: Path, *, auth_mode: str = "none", require_sandbox_header: bool = False) -> TestClient:
    settings = AppSettings(
        auth_mode=auth_mode,  # type: ignore[arg-type]
        static_tokens=["dev-token"],
        require_sandbox_header=require_sandbox_header,
        database_url=f"sqlite:///{tmp_path / 'boundary.db'}",
        object_root=tmp_path / "objects",
        heartbeat_seconds=0.1,
        poll_interval_seconds=0.01,
    )
    return TestClient(build_app(settings))


def test_healthz_is_not_used_as_bearer_token_compatibility_proof() -> None:
    runner = (ROOT / "src" / "zorn" / "cert" / "runners" / "run_contract_fixture.py").read_text()

    assert 'f"{base_url}/healthz"' not in runner
    assert '"auth.bearer_token"' in runner
    assert '"endpoint": "PUT /api/v1/entities"' in runner


def test_default_app_mounts_only_strict_runtime_surface(tmp_path: Path) -> None:
    settings = AppSettings(
        auth_mode="none",
        database_url=f"sqlite:///{tmp_path / 'strict.db'}",
        object_root=tmp_path / "objects",
    )
    app = build_app(settings)
    mounted_methods = {
        (str(getattr(route, "path", "")), method)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }
    assert ("/healthz", "GET") not in mounted_methods
    assert ("/api/v1/entities/events/poll", "POST") not in mounted_methods
    assert ("/api/v1/tasks/{task_id}/status", "POST") not in mounted_methods
    assert ("/api/v1/tasks/{task_id}/cancel", "POST") not in mounted_methods
    assert ("/api/v1/tasks/events", "POST") not in mounted_methods
    assert ("/api/v1/tasks/{task_id}/manual-control/stream", "POST") not in mounted_methods

    with TestClient(app) as client:
        healthz = client.get("/healthz")
        assert healthz.status_code == 404

        entity_poll_alias = client.post("/api/v1/entities/events/poll", json={})
        assert entity_poll_alias.status_code == 404

        task_status_post_alias = client.post("/api/v1/tasks/task-a/status", json={})
        assert task_status_post_alias.status_code == 405

        task_cancel_post_alias = client.post("/api/v1/tasks/task-a/cancel", json={})
        assert task_cancel_post_alias.status_code == 405

        task_events_helper = client.post("/api/v1/tasks/events", json={})
        assert task_events_helper.status_code == 405

        manual_control_placeholder = client.post("/api/v1/tasks/task-a/manual-control/stream", json={})
        assert manual_control_placeholder.status_code == 404


def test_static_auth_distinguishes_missing_invalid_valid_and_sandbox_headers(tmp_path: Path) -> None:
    with _client(tmp_path, auth_mode="static") as client:
        missing = client.get("/api/v1/entities/missing")
        assert missing.status_code == 401

        invalid = client.get("/api/v1/entities/missing", headers={"Authorization": "Bearer wrong-token"})
        assert invalid.status_code == 403

        valid = client.put(
            "/api/v1/entities",
            json={"entityId": "auth-entity", "isLive": True},
            headers={"Authorization": "Bearer dev-token"},
        )
        assert valid.status_code == 200

        api_key = client.get("/api/v1/entities/auth-entity", headers={"x-api-key": "dev-token"})
        assert api_key.status_code == 200

    with _client(tmp_path, auth_mode="static", require_sandbox_header=True) as client:
        no_sandbox = client.get("/api/v1/entities/auth-entity", headers={"Authorization": "Bearer dev-token"})
        assert no_sandbox.status_code == 403
        assert no_sandbox.json()["detail"] == "Missing sandbox header"

        with_sandbox = client.put(
            "/api/v1/entities",
            json={"entityId": "sandbox-entity", "isLive": True},
            headers={"Authorization": "Bearer dev-token", "Anduril-Sandbox-Authorization": "Bearer dev-token"},
        )
        assert with_sandbox.status_code == 200


def test_oauth_dev_token_is_proven_through_entity_surface(tmp_path: Path) -> None:
    with _client(tmp_path, auth_mode="oauth-dev") as client:
        token_response = client.post("/api/v1/oauth/token", json={"client_id": "dev", "client_secret": "dev"})
        assert token_response.status_code == 200
        token = token_response.json()["access_token"]

        publish = client.put(
            "/api/v1/entities",
            json={"entityId": "oauth-entity", "isLive": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert publish.status_code == 200
        assert publish.json()["entityId"] == "oauth-entity"


def test_stale_entity_update_does_not_emit_extra_lifecycle_event(client: TestClient) -> None:
    first = client.put(
        "/api/v1/entities",
        json={
            "entityId": "stale-entity",
            "isLive": True,
            "description": "newer",
            "provenance": {"sourceUpdateTime": "2026-01-01T00:00:00Z"},
        },
    )
    assert first.status_code == 200

    stale = client.put(
        "/api/v1/entities",
        json={
            "entityId": "stale-entity",
            "isLive": True,
            "description": "older",
            "provenance": {"sourceUpdateTime": "2025-01-01T00:00:00Z"},
        },
    )
    assert stale.status_code == 200
    assert stale.json()["_compat"]["ignoredStaleUpdate"] is True

    events = client.post("/api/v1/entities/events", json={"afterSequence": 0}).json()["events"]
    assert [event["eventType"] for event in events] == ["CREATE"]
    assert events[0]["entity"]["description"] == "newer"


def test_task_lifecycle_rejects_duplicates_stale_status_and_terminal_updates(client: TestClient) -> None:
    task = {
        "taskId": "lifecycle-task",
        "displayName": "Lifecycle task",
        "assigneeId": "agent-1",
    }
    created = client.post("/api/v1/tasks", json=task)
    assert created.status_code == 201

    duplicate = client.post("/api/v1/tasks", json=task)
    assert duplicate.status_code == 409

    executing = client.put(
        "/api/v1/tasks/lifecycle-task/status",
        json={"statusVersion": 1, "newStatus": {"status": "STATUS_EXECUTING"}},
    )
    assert executing.status_code == 200
    assert executing.json()["version"]["statusVersion"] == 2

    stale_status = client.put(
        "/api/v1/tasks/lifecycle-task/status",
        json={"statusVersion": 1, "newStatus": {"status": "STATUS_DONE_OK"}},
    )
    assert stale_status.status_code == 409

    cancelled = client.put("/api/v1/tasks/lifecycle-task/cancel", json={"reason": "operator"})
    assert cancelled.status_code == 200

    terminal_update = client.put(
        "/api/v1/tasks/lifecycle-task/status",
        json={"statusVersion": 3, "newStatus": {"status": "STATUS_EXECUTING"}},
    )
    assert terminal_update.status_code == 409


def test_agent_listen_delivers_each_request_once(client: TestClient) -> None:
    created = client.post(
        "/api/v1/tasks",
        json={"taskId": "agent-task", "displayName": "Agent task", "assigneeId": "agent-2"},
    )
    assert created.status_code == 201

    first = client.post("/api/v1/agent/listen", json={"assigneeId": "agent-2"})
    assert first.status_code == 200
    assert first.json()["requestType"] == "ExecuteRequest"

    second = client.post("/api/v1/agent/listen", json={"assigneeId": "agent-2"})
    assert second.status_code == 200
    assert "heartbeat" in second.json()


def test_object_missing_and_deleted_paths_fail_cleanly(client: TestClient) -> None:
    missing_get = client.get("/api/v1/objects/missing/object.bin")
    assert missing_get.status_code == 404

    missing_head = client.head("/api/v1/objects/missing/object.bin")
    assert missing_head.status_code == 404

    upload = client.post("/api/v1/objects/tmp/object.bin", content=b"bytes")
    assert upload.status_code == 200

    delete = client.delete("/api/v1/objects/tmp/object.bin")
    assert delete.status_code == 200

    deleted_get = client.get("/api/v1/objects/tmp/object.bin")
    assert deleted_get.status_code == 404
