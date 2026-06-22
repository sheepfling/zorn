from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from zorn.cert.runners import run_contract_fixture


def test_spec_report_marks_missing_when_no_artifacts_exist(tmp_path: Path) -> None:
    fixture = SimpleNamespace(id="openapi-fixture", surfaces=("transport.rest_json",))

    report = run_contract_fixture._spec_report(
        fixture=fixture,
        fixture_dir=tmp_path,
        target="http://localhost:8080",
        token="dev-token",
        mode="cert",
        artifact_kind="openapi",
        patterns=("openapi.yaml",),
    )

    assert report["result"] == "missing"
    assert report["details"]["reason"] == "no openapi artifacts found"
    assert report["details"]["artifact_count"] == 0


def test_spec_rest_flow_prefers_public_entity_events_envelope(monkeypatch, tmp_path: Path) -> None:
    artifact = tmp_path / "openapi.yaml"
    artifact.write_text("openapi: 3.0.0\n", encoding="utf-8")
    fixture = SimpleNamespace(
        id="openapi-fixture",
        surfaces=(
            "auth.oauth_client_credentials",
            "auth.bearer_token",
            "transport.rest_json",
            "entities.publish",
            "entities.get",
            "entities.overrides.apply",
            "entities.overrides.clear",
            "entities.long_poll",
            "tasks.create",
            "tasks.get",
            "tasks.query",
            "tasks.update_status",
            "tasks.cancel",
            "objects.upload",
            "objects.metadata",
            "objects.list",
            "objects.download",
            "objects.delete",
        ),
    )

    monkeypatch.setattr(
        run_contract_fixture,
        "start_http_zorn_server",
        lambda **_: SimpleNamespace(base_url="http://zorn.test"),
    )
    monkeypatch.setattr(run_contract_fixture, "stop_https_zorn_server", lambda _server: "server log")
    monkeypatch.setattr(
        run_contract_fixture,
        "_http_upload",
        lambda *_args, **_kwargs: (200, {"objectPath": "openapi-fixture/object.txt"}),
    )
    monkeypatch.setattr(
        run_contract_fixture,
        "http_bytes",
        lambda method, url, **_kwargs: (
            (200, b"", {"Content-Length": "21"})
            if method == "HEAD"
            else (200, b"zorn spec rest smoke\n", {})
        ),
    )

    def fake_http_json(method: str, url: str, **_kwargs):
        if url.endswith("/api/v1/oauth/token"):
            return 200, {"access_token": "dev-token"}
        if url.endswith("/api/v1/entities") and method == "PUT":
            return 200, {"entityId": "openapi-fixture-entity"}
        if url.endswith("/api/v1/entities/openapi-fixture-entity"):
            return 200, {"entityId": "openapi-fixture-entity"}
        if url.endswith("/override/mil_view.disposition") and method == "PUT":
            return 200, {"entityId": "openapi-fixture-entity", "milView": {"disposition": "DISPOSITION_HOSTILE"}}
        if url.endswith("/override/mil_view.disposition") and method == "DELETE":
            return 200, {"entityId": "openapi-fixture-entity"}
        if url.endswith("/api/v1/entities/events"):
            return 200, {"sessionToken": "1", "entityEvents": [{"entity": {"entityId": "openapi-fixture-entity"}}]}
        if url.endswith("/api/v1/tasks") and method == "POST":
            return 201, {"taskId": "openapi-fixture-task", "version": {"statusVersion": 1}}
        if url.endswith("/api/v1/tasks/openapi-fixture-task") and method == "GET":
            return 200, {"taskId": "openapi-fixture-task"}
        if url.endswith("/api/v1/tasks/query"):
            return 200, {"tasks": [{"taskId": "openapi-fixture-task"}]}
        if url.endswith("/api/v1/tasks/openapi-fixture-task/status"):
            return 200, {"taskId": "openapi-fixture-task"}
        if url.endswith("/api/v1/tasks/openapi-fixture-task/cancel"):
            return 200, {"taskId": "openapi-fixture-task"}
        if "/api/v1/objects?prefix=openapi-fixture" in url:
            return 200, {"objects": [{"objectPath": "openapi-fixture/object.txt"}]}
        if url.endswith("/api/v1/objects/openapi-fixture/object.txt") and method == "DELETE":
            return 200, {"deleted": True}
        raise AssertionError(f"unexpected request: {method} {url}")

    monkeypatch.setattr(run_contract_fixture, "http_json", fake_http_json)

    report = run_contract_fixture._run_spec_rest_flow(
        fixture=fixture,
        fixture_dir=tmp_path,
        target="http://localhost:8080",
        token="dev-token",
        mode="cert",
        artifact_kind="openapi",
        patterns=("openapi.yaml",),
    )

    assert report["result"] == "pass"
    assert report["details"]["artifact_count"] == 1
    assert report["details"]["executor"] == "openapi_rest_flow"
    assert report["details"]["executed"] is True
    assert "reason" not in report["details"]
    assert report["details"]["entities.long_poll"]["entityEvents"][0]["entity"]["entityId"] == "openapi-fixture-entity"
