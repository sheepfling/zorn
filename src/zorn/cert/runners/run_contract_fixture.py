from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any
from urllib import request

import yaml

from .common import base_report, http_bytes, http_json, start_http_zorn_server, stop_https_zorn_server


def run_schema_proto(*, fixture: Any, fixture_dir: Path, target: str, token: str, mode: str) -> dict[str, Any]:
    del target, token
    report = base_report(fixture_id=fixture.id, mode=mode)
    repo_root = Path(__file__).resolve().parents[4]
    manifest_path = repo_root / "tests" / "fixtures" / "grpc" / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    expected = [item["path"] for item in manifest.get("fixtures", []) if isinstance(item, dict) and item.get("path")]
    missing_files = [path for path in expected if not (manifest_path.parent / path).exists()]
    report["details"] = {
        "reason": "golden gRPC wire fixture generator is not implemented yet",
        "fixture_dir": str(fixture_dir),
        "manifest": str(manifest_path),
        "expected_binpb": expected,
        "missing_binpb": missing_files,
    }
    report["result"] = "missing" if missing_files else "blocked"
    report["missing"] = list(fixture.surfaces)
    return report
####


def run_spec_rest(*, fixture: Any, fixture_dir: Path, target: str, token: str, mode: str) -> dict[str, Any]:
    return _run_spec_rest_flow(
        fixture=fixture,
        fixture_dir=fixture_dir,
        target=target,
        token=token,
        mode=mode,
        artifact_kind="openapi",
        patterns=("*openapi*.yml", "*openapi*.yaml", "*openapi*.json", "openapi.yml", "openapi.yaml", "openapi.json"),
    )
####


def run_postman_rest(*, fixture: Any, fixture_dir: Path, target: str, token: str, mode: str) -> dict[str, Any]:
    return _run_spec_rest_flow(
        fixture=fixture,
        fixture_dir=fixture_dir,
        target=target,
        token=token,
        mode=mode,
        artifact_kind="postman",
        patterns=("*postman*.json", "*collection*.json"),
    )
####


def run_cpp_sample(*, fixture: Any, fixture_dir: Path, target: str, token: str, mode: str) -> dict[str, Any]:
    return _native_sdk_report(
        fixture=fixture,
        fixture_dir=fixture_dir,
        target=target,
        token=token,
        mode=mode,
        language="cpp",
        tools=["cmake", "protoc"],
    )
####


def run_rust_sample(*, fixture: Any, fixture_dir: Path, target: str, token: str, mode: str) -> dict[str, Any]:
    return _native_sdk_report(
        fixture=fixture,
        fixture_dir=fixture_dir,
        target=target,
        token=token,
        mode=mode,
        language="rust",
        tools=["cargo", "protoc"],
    )
####


def _spec_report(
    *,
    fixture: Any,
    fixture_dir: Path,
    target: str,
    token: str,
    mode: str,
    artifact_kind: str,
    patterns: tuple[str, ...],
) -> dict[str, Any]:
    report = base_report(fixture_id=fixture.id, mode=mode)
    artifacts = sorted({path.relative_to(fixture_dir).as_posix() for pattern in patterns for path in fixture_dir.rglob(pattern)})
    report["details"] = {
        "fixture_dir": str(fixture_dir),
        "target": target,
        "token_configured": bool(token),
        "artifact_kind": artifact_kind,
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
    }
    if artifacts:
        report["result"] = "blocked"
    else:
        report["details"]["reason"] = f"no {artifact_kind} artifacts found"
        report["result"] = "missing"
    report["missing"] = list(fixture.surfaces)
    return report
####


def _run_spec_rest_flow(
    *,
    fixture: Any,
    fixture_dir: Path,
    target: str,
    token: str,
    mode: str,
    artifact_kind: str,
    patterns: tuple[str, ...],
) -> dict[str, Any]:
    report = _spec_report(
        fixture=fixture,
        fixture_dir=fixture_dir,
        target=target,
        token=token,
        mode=mode,
        artifact_kind=artifact_kind,
        patterns=patterns,
    )
    if not report["details"]["artifacts"]:
        return report
    ####
    report["details"]["executor"] = f"{artifact_kind}_rest_flow"
    report["details"]["executed"] = True
    repo_root = Path(__file__).resolve().parents[4]
    server = start_http_zorn_server(repo_root=repo_root, token=token)
    try:
        base_url = server.base_url
        status, oauth = http_json(
            "POST",
            f"{base_url}/api/v1/oauth/token",
            token=token,
            payload={"client_id": "zorn-client", "client_secret": "zorn-secret"},
        )
        _record(report, "auth.oauth_client_credentials", status == 200 and bool(oauth.get("access_token")), oauth)
        _record(report, "transport.rest_json", True, {"artifact_kind": artifact_kind, "artifacts": report["details"]["artifacts"]})

        entity_id = f"{fixture.id}-entity"
        entity_payload = {
            "entityId": entity_id,
            "description": f"{fixture.id} REST conformance entity",
            "isLive": True,
            "noExpiry": True,
            "location": {"position": {"latitudeDegrees": 37.781, "longitudeDegrees": -122.422, "altitudeHaeMeters": 45}},
            "ontology": {"template": "TEMPLATE_TRACK", "platformType": "UAS"},
            "milView": {"disposition": "DISPOSITION_ASSUMED_FRIENDLY"},
            "provenance": {"sourceId": fixture.id, "integrationName": fixture.id},
        }
        status, published = http_json("PUT", f"{base_url}/api/v1/entities", token=token, payload=entity_payload)
        _record(report, "entities.publish", status == 200 and published.get("entityId") == entity_id, published)
        _record(report, "auth.bearer_token", status == 200 and published.get("entityId") == entity_id, {"endpoint": "PUT /api/v1/entities"})
        status, fetched = http_json("GET", f"{base_url}/api/v1/entities/{entity_id}", token=token)
        _record(report, "entities.get", status == 200 and fetched.get("entityId") == entity_id, fetched)
        status, overridden = http_json(
            "PUT",
            f"{base_url}/api/v1/entities/{entity_id}/override/mil_view.disposition",
            token=token,
            payload={"milView": {"disposition": "DISPOSITION_HOSTILE"}},
        )
        _record(report, "entities.overrides.apply", status == 200 and (overridden.get("milView") or {}).get("disposition") == "DISPOSITION_HOSTILE", overridden)
        status, cleared = http_json("DELETE", f"{base_url}/api/v1/entities/{entity_id}/override/mil_view.disposition", token=token)
        _record(report, "entities.overrides.clear", status == 200 and cleared.get("entityId") == entity_id, cleared)
        status, events = http_json("POST", f"{base_url}/api/v1/entities/events", token=token, payload={"sessionToken": ""})
        long_poll_events = events.get("entityEvents")
        if not isinstance(long_poll_events, list):
            long_poll_events = events.get("events")
        ####
        _record(report, "entities.long_poll", status == 200 and isinstance(long_poll_events, list) and bool(long_poll_events), events)

        task_id = f"{fixture.id}-task"
        status, created_task = http_json("POST", f"{base_url}/api/v1/tasks", token=token, payload={"taskId": task_id, "displayName": "Spec REST task"})
        _record(report, "tasks.create", status == 201 and created_task.get("taskId") == task_id, created_task)
        status, fetched_task = http_json("GET", f"{base_url}/api/v1/tasks/{task_id}", token=token)
        _record(report, "tasks.get", status == 200 and fetched_task.get("taskId") == task_id, fetched_task)
        status, query_tasks = http_json("POST", f"{base_url}/api/v1/tasks/query", token=token, payload={})
        task_ids = [item.get("taskId") for item in query_tasks.get("tasks", []) if isinstance(item, dict)]
        _record(report, "tasks.query", status == 200 and task_id in task_ids, {"taskIds": task_ids})
        status, updated_task = http_json(
            "PUT",
            f"{base_url}/api/v1/tasks/{task_id}/status",
            token=token,
            payload={"statusVersion": ((created_task.get("version") or {}).get("statusVersion") or 0), "newStatus": {"status": "STATUS_EXECUTING"}},
        )
        _record(report, "tasks.update_status", status == 200 and updated_task.get("taskId") == task_id, updated_task)
        status, cancelled_task = http_json("PUT", f"{base_url}/api/v1/tasks/{task_id}/cancel", token=token, payload={})
        _record(report, "tasks.cancel", status == 200 and cancelled_task.get("taskId") == task_id, cancelled_task)

        object_path = f"{fixture.id}/object.txt"
        upload_status, upload_payload = _http_upload(f"{base_url}/api/v1/objects/{object_path}", token=token, body=b"zorn spec rest smoke\n")
        _record(report, "objects.upload", upload_status == 200 and object_path in json.dumps(upload_payload), upload_payload)
        status, body, headers = http_bytes("HEAD", f"{base_url}/api/v1/objects/{object_path}", token=token)
        _record(report, "objects.metadata", status == 200 and int(headers.get("Content-Length", headers.get("content-length", "0"))) > 0, {"headers": headers})
        status, listed = http_json("GET", f"{base_url}/api/v1/objects?prefix={fixture.id}", token=token)
        _record(report, "objects.list", status == 200 and object_path in json.dumps(listed), listed)
        status, body, _headers = http_bytes("GET", f"{base_url}/api/v1/objects/{object_path}", token=token)
        _record(report, "objects.download", status == 200 and body == b"zorn spec rest smoke\n", {"bytes": len(body)})
        status, deleted = http_json("DELETE", f"{base_url}/api/v1/objects/{object_path}", token=token)
        _record(report, "objects.delete", status == 200 and deleted.get("deleted") is True, deleted)

        requested = set(fixture.surfaces)
        passed = set(report["passed"])
        failed = set(report["failed"])
        report["missing"] = sorted(surface for surface in requested if surface not in passed and surface not in failed)
        report["result"] = "failed" if report["failed"] else ("partial" if report["missing"] else "pass")
        return report
    finally:
        report["details"]["server_log"] = stop_https_zorn_server(server)
    ####
####


def _http_upload(url: str, *, token: str, body: bytes) -> tuple[int, dict[str, Any]]:
    req = request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
            "x-api-key": token,
            "x-anduril-sandbox": "zorn-cert",
        },
    )
    with request.urlopen(req, timeout=10.0) as response:
        text = response.read().decode("utf-8")
        return response.status, json.loads(text) if text else {}
    ####
####


def _native_sdk_report(
    *,
    fixture: Any,
    fixture_dir: Path,
    target: str,
    token: str,
    mode: str,
    language: str,
    tools: list[str],
) -> dict[str, Any]:
    report = base_report(fixture_id=fixture.id, mode=mode)
    missing_tools = [tool for tool in tools if shutil.which(tool) is None]
    source_files = sorted(
        path.relative_to(fixture_dir).as_posix()
        for path in fixture_dir.rglob("*")
        if path.is_file() and path.suffix in {".cc", ".cpp", ".cxx", ".h", ".hpp", ".rs", ".proto"}
    )
    report["details"] = {
        "reason": f"{language} direct gRPC SDK smoke runner is scaffolded but not implemented yet",
        "fixture_dir": str(fixture_dir),
        "target": target,
        "token_configured": bool(token),
        "language": language,
        "required_tools": tools,
        "missing_tools": missing_tools,
        "source_file_count": len(source_files),
        "sample_source_files": source_files[:20],
    }
    report["result"] = "blocked"
    report["missing"] = list(fixture.surfaces)
    return report
####


def _record(report: dict[str, Any], capability: str, ok: bool, detail: dict[str, Any]) -> None:
    target = "passed" if ok else "failed"
    if capability not in report[target]:
        report[target].append(capability)
    ####
    report["details"][capability] = detail
####
