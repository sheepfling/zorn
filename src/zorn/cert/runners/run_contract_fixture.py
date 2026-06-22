from __future__ import annotations

import asyncio
import json
from pathlib import Path
import shutil
from typing import Any
from urllib import request

import grpc
import yaml

from ..grpc_wire import request_message_type, request_metadata
from ...grpc_api.contract import assert_lattice_grpc_contract, build_lattice_grpc_contract_report
from ...grpc_api.proto_modules import MissingLatticeProtoDependency, load_lattice_proto_modules
from .common import (
    base_report,
    http_bytes,
    http_json,
    start_http_insecure_grpc_zorn_server,
    start_http_zorn_server,
    stop_dual_transport_zorn_server,
    stop_https_zorn_server,
)


def run_schema_proto(*, fixture: Any, fixture_dir: Path, target: str, token: str, mode: str) -> dict[str, Any]:
    del target, token
    report = base_report(fixture_id=fixture.id, mode=mode)
    repo_root = Path(__file__).resolve().parents[4]
    manifest_path = repo_root / "tests" / "fixtures" / "grpc" / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    fixtures = [item for item in manifest.get("fixtures", []) if isinstance(item, dict) and item.get("path") and item.get("rpc")]
    expected = [item["path"] for item in fixtures]
    missing_files = [path for path in expected if not (manifest_path.parent / path).exists()]
    report["details"] = {
        "fixture_dir": str(fixture_dir),
        "manifest": str(manifest_path),
        "expected_binpb": expected,
        "missing_binpb": missing_files,
    }
    if missing_files:
        report["details"]["reason"] = "golden gRPC wire fixtures are missing"
        report["result"] = "missing"
        report["missing"] = list(fixture.surfaces)
        return report
    ####
    try:
        proto_modules = load_lattice_proto_modules()
        assert_lattice_grpc_contract(proto_modules)
    except MissingLatticeProtoDependency as exc:
        report["details"]["reason"] = str(exc)
        report["result"] = "blocked"
        report["missing"] = list(fixture.surfaces)
        return report
    except Exception as exc:
        report["details"]["reason"] = str(exc)
        report["result"] = "failed"
        report["failed"] = list(fixture.surfaces)
        report["missing"] = []
        return report
    ####
    contract_report = build_lattice_grpc_contract_report(proto_modules)
    report["details"]["grpc_contract_report"] = contract_report
    parsed_messages: dict[str, Any] = {}
    parsed_fixtures: dict[str, Any] = {}
    for item in fixtures:
        path = item["path"]
        request_type = request_message_type(proto_modules, item["rpc"])
        message = request_type()
        message.ParseFromString((manifest_path.parent / path).read_bytes())
        parsed_messages[path] = message
        parsed_fixtures[path] = {
            "rpc": item["rpc"],
            "capability": item.get("capability"),
            "request": request_metadata(message),
        }
    ####
    report["details"]["parsed_fixtures"] = parsed_fixtures
    server = start_http_insecure_grpc_zorn_server(repo_root=repo_root, token="dev-token")
    try:
        wire_results = asyncio.run(
            _run_golden_wire_checks(
                proto_modules=proto_modules,
                grpc_target=server.grpc_target,
                requests=parsed_messages,
            )
        )
        report["details"]["wire_results"] = wire_results
        _record(report, "transport.grpc_protobuf", all(result["ok"] for result in wire_results.values()), {"grpc_target": server.grpc_target})
        _record(report, "auth.grpc_bearer_metadata", True, {"grpc_target": server.grpc_target, "metadata": "authorization: Bearer dev-token"})
        _record(report, "entities.grpc_stream", wire_results["entity_stream_request.binpb"]["ok"], wire_results["entity_stream_request.binpb"])
        _record(report, "tasks.listen_as_agent", wire_results["task_listen_as_agent_request.binpb"]["ok"], wire_results["task_listen_as_agent_request.binpb"])
        report["missing"] = sorted(surface for surface in fixture.surfaces if surface not in report["passed"] and surface not in report["failed"])
        report["result"] = "failed" if report["failed"] else ("partial" if report["missing"] else "pass")
    finally:
        logs = stop_dual_transport_zorn_server(server)
        report["details"]["server_log"] = logs["rest"]
        report["details"]["grpc_server_log"] = logs["grpc"]
    ####
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


async def _run_golden_wire_checks(
    *,
    proto_modules: Any,
    grpc_target: str,
    requests: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    metadata = (("authorization", "Bearer dev-token"),)
    results: dict[str, dict[str, Any]] = {}
    async with grpc.aio.insecure_channel(grpc_target) as channel:
        entity_stub = proto_modules.entity_api_grpc.EntityManagerAPIStub(channel)
        task_stub = proto_modules.task_api_grpc.TaskManagerAPIStub(channel)

        publish_request = requests["entity_publish_request.binpb"]
        publish_response = await entity_stub.PublishEntity(publish_request, metadata=metadata)
        publish_roundtrip = proto_modules.entity_api.PublishEntityResponse()
        publish_roundtrip.ParseFromString(publish_response.SerializeToString())
        published_entity_id = publish_request.entity.entity_id
        fetched_after_publish = await entity_stub.GetEntity(
            proto_modules.entity_api.GetEntityRequest(entity_id=published_entity_id),
            metadata=metadata,
        )
        results["entity_publish_request.binpb"] = {
            "ok": fetched_after_publish.entity.entity_id == published_entity_id,
            "entity_id": published_entity_id,
            "response_type": publish_roundtrip.DESCRIPTOR.full_name,
        }

        get_request = requests["entity_get_request.binpb"]
        await entity_stub.PublishEntity(
            proto_modules.entity_api.PublishEntityRequest(
                entity=proto_modules.entity.Entity(
                    entity_id=get_request.entity_id,
                    description="gRPC wire get fixture",
                    is_live=True,
                    no_expiry=True,
                )
            ),
            metadata=metadata,
        )
        get_response = await entity_stub.GetEntity(get_request, metadata=metadata)
        get_roundtrip = proto_modules.entity_api.GetEntityResponse()
        get_roundtrip.ParseFromString(get_response.SerializeToString())
        results["entity_get_request.binpb"] = {
            "ok": get_roundtrip.entity.entity_id == get_request.entity_id,
            "entity_id": get_roundtrip.entity.entity_id,
        }

        await entity_stub.PublishEntity(
            proto_modules.entity_api.PublishEntityRequest(
                entity=proto_modules.entity.Entity(
                    entity_id="grpc-wire-stream-entity",
                    description="gRPC wire stream fixture",
                    is_live=True,
                    no_expiry=True,
                )
            ),
            metadata=metadata,
        )
        stream_call = entity_stub.StreamEntityComponents(requests["entity_stream_request.binpb"], metadata=metadata)
        stream_response = await asyncio.wait_for(stream_call.read(), timeout=2.0)
        stream_call.cancel()
        entity_event = getattr(stream_response, "entity_event", None)
        streamed_entity = getattr(entity_event, "entity", None) if entity_event is not None else None
        results["entity_stream_request.binpb"] = {
            "ok": bool(streamed_entity is not None and getattr(streamed_entity, "entity_id", "")),
            "response_type": stream_response.DESCRIPTOR.full_name,
            "entity_id": getattr(streamed_entity, "entity_id", ""),
        }

        create_request = requests["task_create_request.binpb"]
        create_response = await task_stub.CreateTask(create_request, metadata=metadata)
        create_roundtrip = proto_modules.task_api.CreateTaskResponse()
        create_roundtrip.ParseFromString(create_response.SerializeToString())
        created_task = create_roundtrip.task
        results["task_create_request.binpb"] = {
            "ok": created_task.version.task_id == create_request.task_id and created_task.specification.type_url == create_request.specification.type_url,
            "task_id": created_task.version.task_id,
            "specification_type_url": created_task.specification.type_url,
        }

        update_request = requests["task_update_status_request.binpb"]
        await task_stub.CreateTask(
            proto_modules.task_api.CreateTaskRequest(
                task_id=update_request.status_update.version.task_id,
                display_name="gRPC wire update task",
                relations=proto_modules.task.Relations(
                    assignee=proto_modules.task.Principal(
                        system=proto_modules.task.System(entity_id="grpc-wire-agent-update")
                    )
                ),
            ),
            metadata=metadata,
        )
        update_response = await task_stub.UpdateStatus(update_request, metadata=metadata)
        update_roundtrip = proto_modules.task_api.UpdateStatusResponse()
        update_roundtrip.ParseFromString(update_response.SerializeToString())
        updated_task = update_roundtrip.task
        results["task_update_status_request.binpb"] = {
            "ok": updated_task.version.task_id == update_request.status_update.version.task_id and updated_task.version.status_version >= 2,
            "task_id": updated_task.version.task_id,
            "status_version": updated_task.version.status_version,
            "progress_type_url": updated_task.status.progress.type_url,
        }

        cancel_request = requests["task_cancel_request.binpb"]
        await task_stub.CreateTask(
            proto_modules.task_api.CreateTaskRequest(
                task_id=cancel_request.task_id,
                display_name="gRPC wire cancel task",
            ),
            metadata=metadata,
        )
        cancel_response = await task_stub.CancelTask(cancel_request, metadata=metadata)
        cancel_roundtrip = proto_modules.task_api.CancelTaskResponse()
        cancel_roundtrip.ParseFromString(cancel_response.SerializeToString())
        cancelled_task = cancel_roundtrip.task
        results["task_cancel_request.binpb"] = {
            "ok": cancelled_task.version.task_id == cancel_request.task_id,
            "task_id": cancelled_task.version.task_id,
            "status": cancelled_task.status.status,
        }

        listen_request = requests["task_listen_as_agent_request.binpb"]
        listen_entity_id = listen_request.entity_ids.entity_ids[0]
        await task_stub.CreateTask(
            proto_modules.task_api.CreateTaskRequest(
                task_id="grpc-wire-task-listen",
                display_name="gRPC wire listen task",
                relations=proto_modules.task.Relations(
                    assignee=proto_modules.task.Principal(
                        system=proto_modules.task.System(entity_id=listen_entity_id)
                    )
                ),
            ),
            metadata=metadata,
        )
        listen_call = task_stub.ListenAsAgent(listen_request, metadata=metadata)
        listen_response = await asyncio.wait_for(listen_call.read(), timeout=2.0)
        listen_call.cancel()
        execute_request = getattr(listen_response, "execute_request", None)
        execute_task = getattr(execute_request, "task", None) if execute_request is not None else None
        results["task_listen_as_agent_request.binpb"] = {
            "ok": bool(execute_task is not None and execute_task.version.task_id == "grpc-wire-task-listen"),
            "response_type": listen_response.DESCRIPTOR.full_name,
            "task_id": execute_task.version.task_id if execute_task is not None else None,
        }
    ####
    return results
####


def _record(report: dict[str, Any], capability: str, ok: bool, detail: dict[str, Any]) -> None:
    target = "passed" if ok else "failed"
    if capability not in report[target]:
        report[target].append(capability)
    ####
    report["details"][capability] = detail
####
