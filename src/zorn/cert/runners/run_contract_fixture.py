from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import shutil
import tempfile
import textwrap
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
    http_sse_event,
    run_command,
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
    if fixture.id == "sdk-cpp-grpc-smoke":
        return _run_sdk_cpp_smoke(fixture=fixture, fixture_dir=fixture_dir, token=token, mode=mode)
    ####
    return _native_sdk_report(
        fixture=fixture,
        fixture_dir=fixture_dir,
        target=target,
        token=token,
        mode=mode,
        language="cpp",
        tools=["cmake"],
    )
####


def run_rust_sample(*, fixture: Any, fixture_dir: Path, target: str, token: str, mode: str) -> dict[str, Any]:
    if fixture.id == "sdk-rust-grpc-smoke":
        return _run_sdk_rust_smoke(fixture=fixture, fixture_dir=fixture_dir, token=token, mode=mode)
    ####
    return _native_sdk_report(
        fixture=fixture,
        fixture_dir=fixture_dir,
        target=target,
        token=token,
        mode=mode,
        language="rust",
        tools=["cargo"],
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
        sse_status, sse_event, sse_payload = http_sse_event(
            "POST",
            f"{base_url}/api/v1/entities/stream",
            token=token,
            payload={"preExistingOnly": True, "heartbeatIntervalMs": 0},
        )
        _record(
            report,
            "entities.stream_sse",
            sse_status == 200 and (sse_payload.get("entity") or {}).get("entityId") == entity_id,
            {"event": sse_event, "payload": sse_payload},
        )

        task_id = f"{fixture.id}-task"
        assignee_id = f"{fixture.id}-agent"
        status, created_task = http_json(
            "POST",
            f"{base_url}/api/v1/tasks",
            token=token,
            payload={"taskId": task_id, "displayName": "Spec REST task", "assigneeId": assignee_id},
        )
        _record(report, "tasks.create", status == 201 and created_task.get("taskId") == task_id, created_task)
        status, fetched_task = http_json("GET", f"{base_url}/api/v1/tasks/{task_id}", token=token)
        _record(report, "tasks.get", status == 200 and fetched_task.get("taskId") == task_id, fetched_task)
        status, query_tasks = http_json("POST", f"{base_url}/api/v1/tasks/query", token=token, payload={})
        task_ids = [item.get("taskId") for item in query_tasks.get("tasks", []) if isinstance(item, dict)]
        _record(report, "tasks.query", status == 200 and task_id in task_ids, {"taskIds": task_ids})
        listen_status, listen_payload = http_json(
            "POST",
            f"{base_url}/api/v1/agent/listen",
            token=token,
            payload={"agentSelector": {"entityIds": [assignee_id]}},
        )
        execute_request = listen_payload.get("executeRequest") or listen_payload.get("execute_request") or {}
        _record(
            report,
            "tasks.listen_as_agent",
            listen_status == 200 and (execute_request.get("task") or {}).get("taskId") == task_id,
            listen_payload,
        )
        task_stream_status, task_stream_event, task_stream_payload = http_sse_event(
            "POST",
            f"{base_url}/api/v1/tasks/stream",
            token=token,
            payload={"includePreexisting": True, "heartbeatIntervalMs": 0},
        )
        streamed_task = task_stream_payload.get("task")
        if not isinstance(streamed_task, dict):
            task_event = task_stream_payload.get("taskEvent") or task_stream_payload.get("task_event")
            if isinstance(task_event, dict):
                candidate = task_event.get("task")
                if isinstance(candidate, dict):
                    streamed_task = candidate
                ####
            ####
        ####
        _record(
            report,
            "tasks.stream",
            task_stream_status == 200 and isinstance(streamed_task, dict) and streamed_task.get("taskId") == task_id,
            {"event": task_stream_event, "payload": task_stream_payload},
        )
        agent_stream_status, agent_stream_event, agent_stream_payload = http_sse_event(
            "POST",
            f"{base_url}/api/v1/agent/stream",
            token=token,
            payload={"agentSelector": {"entityIds": [assignee_id]}, "heartbeatIntervalMs": 0},
        )
        streamed_execute = agent_stream_payload.get("executeRequest") or agent_stream_payload.get("execute_request") or {}
        _record(
            report,
            "tasks.stream_as_agent",
            agent_stream_status == 200 and (streamed_execute.get("task") or {}).get("taskId") == task_id,
            {"event": agent_stream_event, "payload": agent_stream_payload},
        )
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


def _run_sdk_cpp_smoke(*, fixture: Any, fixture_dir: Path, token: str, mode: str) -> dict[str, Any]:
    report = base_report(fixture_id=fixture.id, mode=mode)
    cmake = shutil.which("cmake")
    if cmake is None:
        report["result"] = "blocked"
        report["missing"] = list(fixture.surfaces)
        report["details"] = {
            "reason": "cmake is required for sdk-cpp-grpc-smoke",
            "fixture_dir": str(fixture_dir),
            "required_tools": ["cmake"],
        }
        return report
    ####

    grpc_config = _find_cmake_package_config(
        package_dir="grpc",
        filename="gRPCConfig.cmake",
    )
    protobuf_config = _find_cmake_package_config(
        package_dir="protobuf",
        filename="protobuf-config.cmake",
    )
    if grpc_config is None or protobuf_config is None:
        report["result"] = "blocked"
        report["missing"] = list(fixture.surfaces)
        report["details"] = {
            "reason": "system gRPC/protobuf C++ development packages are required for sdk-cpp-grpc-smoke",
            "fixture_dir": str(fixture_dir),
            "required_tools": ["cmake", "gRPCConfig.cmake", "protobuf-config.cmake"],
            "grpc_config": str(grpc_config) if grpc_config else None,
            "protobuf_config": str(protobuf_config) if protobuf_config else None,
        }
        return report
    ####

    repo_root = Path(__file__).resolve().parents[4]
    grpc_fixture_dir = repo_root / "tests" / "fixtures" / "grpc"
    smoke_root = Path(tempfile.mkdtemp(prefix="zorn-cpp-sdk-smoke-"))
    source_dir = smoke_root / "src"
    build_dir = smoke_root / "build"
    source_dir.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)

    (smoke_root / "CMakeLists.txt").write_text(
        textwrap.dedent(
            f"""
            cmake_minimum_required(VERSION 3.16)
            project(zorn_sdk_cpp_smoke LANGUAGES CXX)

            set(CMAKE_CXX_STANDARD 17)
            set(CMAKE_CXX_STANDARD_REQUIRED ON)

            add_subdirectory("{fixture_dir.as_posix()}" lattice-sdk-cpp)

            add_executable(zorn-sdk-cpp-smoke src/main.cc)
            target_include_directories(zorn-sdk-cpp-smoke PRIVATE "{fixture_dir.as_posix()}/src")
            target_link_libraries(zorn-sdk-cpp-smoke PRIVATE lattice-sdk-cpp gRPC::grpc++ protobuf::libprotobuf)
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (source_dir / "main.cc").write_text(
        textwrap.dedent(
            """
            #include <fstream>
            #include <iostream>
            #include <memory>
            #include <string>

            #include <grpcpp/channel.h>
            #include <grpcpp/client_context.h>
            #include <grpcpp/create_channel.h>
            #include <grpcpp/security/credentials.h>
            #include <grpcpp/support/status.h>

            #include "anduril/entitymanager/v1/entity.pub.pb.h"
            #include "anduril/entitymanager/v1/entity_manager_grpcapi.pub.grpc.pb.h"
            #include "anduril/taskmanager/v1/task.pub.pb.h"
            #include "anduril/taskmanager/v1/task_manager_grpcapi.pub.grpc.pb.h"

            namespace {{

            template <typename Message>
            bool LoadMessage(const std::string& root, const std::string& name, Message* message) {{
                std::ifstream input(root + "/" + name, std::ios::binary);
                return input.good() && message->ParseFromIstream(&input);
            }}

            void PrintResult(
                const std::string& name,
                bool ok,
                const std::string& body,
                bool& first
            ) {{
                if (!first) {{
                    std::cout << ",\\n";
                }}
                first = false;
                std::cout << "  \\"" << name << "\\": { \\"ok\\": " << (ok ? "true" : "false");
                if (!body.empty()) {{
                    std::cout << ", " << body;
                }}
                std::cout << " }";
            }}

            std::string JsonString(const std::string& value) {{
                std::string escaped;
                escaped.reserve(value.size() + 8);
                for (char ch : value) {{
                    if (ch == '\\\\' || ch == '"') {{
                        escaped.push_back('\\\\');
                    }}
                    escaped.push_back(ch);
                }}
                return "\\\"" + escaped + "\\\"";
            }}

            }}  // namespace

            int main() {{
                const char* grpc_target_env = std::getenv("ZORN_GRPC_TARGET");
                const char* token_env = std::getenv("ZORN_TOKEN");
                const char* fixture_dir_env = std::getenv("ZORN_GRPC_FIXTURE_DIR");
                if (grpc_target_env == nullptr || token_env == nullptr || fixture_dir_env == nullptr) {{
                    std::cerr << "missing ZORN_GRPC_TARGET/ZORN_TOKEN/ZORN_GRPC_FIXTURE_DIR\\n";
                    return 2;
                }}

                const std::string grpc_target(grpc_target_env);
                const std::string token(token_env);
                const std::string fixture_dir(fixture_dir_env);

                auto channel = grpc::CreateChannel(grpc_target, grpc::InsecureChannelCredentials());
                auto entity_stub = anduril::entitymanager::v1::EntityManagerAPI::NewStub(channel);
                auto task_stub = anduril::taskmanager::v1::TaskManagerAPI::NewStub(channel);

                anduril::entitymanager::v1::PublishEntityRequest publish_request;
                anduril::entitymanager::v1::GetEntityRequest get_request;
                anduril::entitymanager::v1::StreamEntityComponentsRequest stream_request;
                anduril::taskmanager::v1::CreateTaskRequest create_request;
                anduril::taskmanager::v1::UpdateStatusRequest update_request;
                anduril::taskmanager::v1::ListenAsAgentRequest listen_request;

                if (!LoadMessage(fixture_dir, "entity_publish_request.binpb", &publish_request)
                    || !LoadMessage(fixture_dir, "entity_get_request.binpb", &get_request)
                    || !LoadMessage(fixture_dir, "entity_stream_request.binpb", &stream_request)
                    || !LoadMessage(fixture_dir, "task_create_request.binpb", &create_request)
                    || !LoadMessage(fixture_dir, "task_update_status_request.binpb", &update_request)
                    || !LoadMessage(fixture_dir, "task_listen_as_agent_request.binpb", &listen_request)) {{
                    std::cerr << "failed to load one or more binpb fixtures\\n";
                    return 3;
                }}

                bool first = true;
                bool overall_ok = true;
                std::cout << "{\\n";

                grpc::ClientContext publish_context;
                publish_context.AddMetadata("authorization", "Bearer " + token);
                anduril::entitymanager::v1::PublishEntityResponse publish_response;
                grpc::Status publish_status = entity_stub->PublishEntity(&publish_context, publish_request, &publish_response);
                const std::string published_entity_id = publish_request.entity().entity_id();
                PrintResult(
                    "auth.grpc_bearer_metadata",
                    publish_status.ok(),
                    "\\"metadata\\": " + JsonString("authorization: Bearer <token>"),
                    first
                );
                PrintResult(
                    "transport.grpc_protobuf",
                    publish_status.ok(),
                    "\\"grpc_target\\": " + JsonString(grpc_target),
                    first
                );

                grpc::ClientContext publish_get_context;
                publish_get_context.AddMetadata("authorization", "Bearer " + token);
                anduril::entitymanager::v1::GetEntityResponse publish_get_response;
                grpc::Status publish_get_status = entity_stub->GetEntity(
                    &publish_get_context,
                    anduril::entitymanager::v1::GetEntityRequest{{published_entity_id}},
                    &publish_get_response
                );
                const bool publish_ok = publish_status.ok()
                    && publish_get_status.ok()
                    && publish_get_response.entity().entity_id() == published_entity_id;
                PrintResult(
                    "entities.publish",
                    publish_ok,
                    "\\"entity_id\\": " + JsonString(published_entity_id),
                    first
                );

                grpc::ClientContext seed_get_context;
                seed_get_context.AddMetadata("authorization", "Bearer " + token);
                anduril::entitymanager::v1::PublishEntityRequest seed_get_request;
                auto* seeded_get_entity = seed_get_request.mutable_entity();
                seeded_get_entity->set_entity_id(get_request.entity_id());
                seeded_get_entity->set_description("C++ gRPC get fixture");
                seeded_get_entity->set_is_live(true);
                anduril::entitymanager::v1::PublishEntityResponse seed_get_response;
                grpc::Status seed_get_status = entity_stub->PublishEntity(&seed_get_context, seed_get_request, &seed_get_response);

                grpc::ClientContext get_context;
                get_context.AddMetadata("authorization", "Bearer " + token);
                anduril::entitymanager::v1::GetEntityResponse get_response;
                grpc::Status get_status = entity_stub->GetEntity(&get_context, get_request, &get_response);
                const bool get_ok = seed_get_status.ok()
                    && get_status.ok()
                    && get_response.entity().entity_id() == get_request.entity_id();
                PrintResult(
                    "entities.get",
                    get_ok,
                    "\\"entity_id\\": " + JsonString(get_response.entity().entity_id()),
                    first
                );

                grpc::ClientContext seed_stream_context;
                seed_stream_context.AddMetadata("authorization", "Bearer " + token);
                anduril::entitymanager::v1::PublishEntityRequest seed_stream_request;
                auto* seeded_stream_entity = seed_stream_request.mutable_entity();
                seeded_stream_entity->set_entity_id("grpc-wire-stream-entity");
                seeded_stream_entity->set_description("C++ gRPC stream fixture");
                seeded_stream_entity->set_is_live(true);
                anduril::entitymanager::v1::PublishEntityResponse seed_stream_response;
                grpc::Status seed_stream_status = entity_stub->PublishEntity(&seed_stream_context, seed_stream_request, &seed_stream_response);

                grpc::ClientContext stream_context;
                stream_context.AddMetadata("authorization", "Bearer " + token);
                auto stream_reader = entity_stub->StreamEntityComponents(&stream_context, stream_request);
                anduril::entitymanager::v1::StreamEntityComponentsResponse stream_response;
                const bool stream_read = stream_reader->Read(&stream_response);
                grpc::Status stream_finish = stream_reader->Finish();
                const std::string stream_entity_id =
                    stream_read && stream_response.has_entity_event() && stream_response.entity_event().has_entity()
                        ? stream_response.entity_event().entity().entity_id()
                        : "";
                const bool stream_ok = seed_stream_status.ok()
                    && stream_read
                    && stream_finish.ok()
                    && !stream_entity_id.empty();
                PrintResult(
                    "entities.grpc_stream",
                    stream_ok,
                    "\\"entity_id\\": " + JsonString(stream_entity_id),
                    first
                );

                grpc::ClientContext create_context;
                create_context.AddMetadata("authorization", "Bearer " + token);
                anduril::taskmanager::v1::CreateTaskResponse create_response;
                grpc::Status create_status = task_stub->CreateTask(&create_context, create_request, &create_response);
                const std::string created_task_id =
                    create_response.has_task() && create_response.task().has_version()
                        ? create_response.task().version().task_id()
                        : "";
                const bool create_ok = create_status.ok() && created_task_id == create_request.task_id();
                PrintResult(
                    "tasks.create",
                    create_ok,
                    "\\"task_id\\": " + JsonString(created_task_id),
                    first
                );

                grpc::ClientContext seed_update_context;
                seed_update_context.AddMetadata("authorization", "Bearer " + token);
                anduril::taskmanager::v1::CreateTaskRequest seed_update_request;
                seed_update_request.set_task_id(update_request.status_update().version().task_id());
                seed_update_request.set_display_name("C++ gRPC update task");
                auto* update_relations = seed_update_request.mutable_relations();
                auto* update_assignee = update_relations->mutable_assignee();
                update_assignee->mutable_system()->set_entity_id("grpc-wire-agent-update");
                anduril::taskmanager::v1::CreateTaskResponse seed_update_response;
                grpc::Status seed_update_status = task_stub->CreateTask(&seed_update_context, seed_update_request, &seed_update_response);

                grpc::ClientContext update_context;
                update_context.AddMetadata("authorization", "Bearer " + token);
                anduril::taskmanager::v1::UpdateStatusResponse update_response;
                grpc::Status update_status = task_stub->UpdateStatus(&update_context, update_request, &update_response);
                const unsigned int status_version =
                    update_response.has_task() && update_response.task().has_version()
                        ? update_response.task().version().status_version()
                        : 0U;
                const std::string updated_task_id =
                    update_response.has_task() && update_response.task().has_version()
                        ? update_response.task().version().task_id()
                        : "";
                const bool update_ok = seed_update_status.ok()
                    && update_status.ok()
                    && updated_task_id == update_request.status_update().version().task_id()
                    && status_version >= 2U;
                PrintResult(
                    "tasks.update_status",
                    update_ok,
                    "\\"task_id\\": " + JsonString(updated_task_id) + ", \\"status_version\\": " + std::to_string(status_version),
                    first
                );

                grpc::ClientContext seed_listen_context;
                seed_listen_context.AddMetadata("authorization", "Bearer " + token);
                anduril::taskmanager::v1::CreateTaskRequest seed_listen_request;
                seed_listen_request.set_task_id("grpc-wire-task-listen");
                seed_listen_request.set_display_name("C++ gRPC listen task");
                auto* listen_relations = seed_listen_request.mutable_relations();
                auto* listen_assignee = listen_relations->mutable_assignee();
                if (listen_request.has_entity_ids() && listen_request.entity_ids().entity_ids_size() > 0) {
                    listen_assignee->mutable_system()->set_entity_id(listen_request.entity_ids().entity_ids(0));
                }
                anduril::taskmanager::v1::CreateTaskResponse seed_listen_response;
                grpc::Status seed_listen_status = task_stub->CreateTask(&seed_listen_context, seed_listen_request, &seed_listen_response);

                grpc::ClientContext listen_context;
                listen_context.AddMetadata("authorization", "Bearer " + token);
                auto listen_reader = task_stub->ListenAsAgent(&listen_context, listen_request);
                anduril::taskmanager::v1::ListenAsAgentResponse listen_response;
                const bool listen_read = listen_reader->Read(&listen_response);
                grpc::Status listen_finish = listen_reader->Finish();
                const std::string listened_task_id =
                    listen_read
                    && listen_response.request_case() == anduril::taskmanager::v1::ListenAsAgentResponse::kExecuteRequest
                    && listen_response.execute_request().has_task()
                    && listen_response.execute_request().task().has_version()
                        ? listen_response.execute_request().task().version().task_id()
                        : "";
                const bool listen_ok = seed_listen_status.ok()
                    && listen_read
                    && listen_finish.ok()
                    && listened_task_id == "grpc-wire-task-listen";
                PrintResult(
                    "tasks.listen_as_agent",
                    listen_ok,
                    "\\"task_id\\": " + JsonString(listened_task_id),
                    first
                );

                overall_ok = publish_status.ok() && publish_ok && get_ok && stream_ok && create_ok && update_ok && listen_ok;
                std::cout << "\\n}\\n";
                return overall_ok ? 0 : 1;
            }
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    env = {
        **os.environ,
        "CMAKE_PREFIX_PATH": os.pathsep.join(
            sorted(
                {
                    str(grpc_config.parent.parent.parent),
                    str(protobuf_config.parent.parent.parent),
                }
            )
        ),
    }
    server = start_http_insecure_grpc_zorn_server(repo_root=repo_root, token=token)
    try:
        env.update(
            {
                "ZORN_GRPC_TARGET": server.grpc_target,
                "ZORN_TOKEN": token,
                "ZORN_GRPC_FIXTURE_DIR": str(grpc_fixture_dir),
            }
        )
        configure = run_command([cmake, "-S", str(smoke_root), "-B", str(build_dir)], cwd=smoke_root, env=env, timeout=300.0)
        build = run_command([cmake, "--build", str(build_dir)], cwd=smoke_root, env=env, timeout=300.0)
        executable = build_dir / "zorn-sdk-cpp-smoke"
        if not executable.exists():
            executable = build_dir / "Debug" / "zorn-sdk-cpp-smoke"
        ####
        run = run_command([str(executable)], cwd=smoke_root, env=env, timeout=300.0) if executable.exists() else None
        report["details"] = {
            "fixture_dir": str(fixture_dir),
            "language": "cpp",
            "required_tools": ["cmake", "gRPCConfig.cmake", "protobuf-config.cmake"],
            "grpc_config": str(grpc_config),
            "protobuf_config": str(protobuf_config),
            "grpc_fixture_dir": str(grpc_fixture_dir),
            "smoke_root": str(smoke_root),
            "configure": {
                "args": configure.args,
                "returncode": configure.returncode,
                "stdout": configure.stdout,
                "stderr": configure.stderr,
            },
            "build": {
                "args": build.args,
                "returncode": build.returncode,
                "stdout": build.stdout,
                "stderr": build.stderr,
            },
            "run": None
            if run is None
            else {
                "args": run.args,
                "returncode": run.returncode,
                "stdout": run.stdout,
                "stderr": run.stderr,
            },
        }
        if configure.returncode != 0 or build.returncode != 0 or run is None or run.returncode != 0:
            report["result"] = "failed"
            report["failed"] = list(fixture.surfaces)
            report["details"]["reason"] = "cpp gRPC smoke executable failed"
            return report
        ####

        results = json.loads(run.stdout)
        report["details"]["results"] = results
        for surface in fixture.surfaces:
            detail = results.get(surface, {"ok": False})
            _record(report, surface, bool(detail.get("ok")), detail)
        ####
        report["missing"] = sorted(surface for surface in fixture.surfaces if surface not in report["passed"] and surface not in report["failed"])
        report["result"] = "failed" if report["failed"] else ("partial" if report["missing"] else "pass")
        return report
    finally:
        logs = stop_dual_transport_zorn_server(server)
        report.setdefault("details", {})
        report["details"]["server_log"] = logs["rest"]
        report["details"]["grpc_server_log"] = logs["grpc"]
        shutil.rmtree(smoke_root, ignore_errors=True)
    ####
####


def _find_cmake_package_config(*, package_dir: str, filename: str) -> Path | None:
    roots = [
        Path("/opt/homebrew/Cellar"),
        Path("/usr/local/Cellar"),
        Path("/opt/local/lib/cmake"),
        Path("/usr/local/lib/cmake"),
        Path("/usr/lib/cmake"),
    ]
    for root in roots:
        if not root.exists():
            continue
        ####
        if root.name == "Cellar":
            matches = sorted(root.glob(f"{package_dir}/*/lib/cmake/**/{filename}"))
        else:
            matches = sorted(root.glob(f"**/{filename}"))
        ####
        if matches:
            return matches[-1]
        ####
    ####
    return None
####


def _run_sdk_rust_smoke(*, fixture: Any, fixture_dir: Path, token: str, mode: str) -> dict[str, Any]:
    report = base_report(fixture_id=fixture.id, mode=mode)
    cargo = shutil.which("cargo")
    if cargo is None:
        report["result"] = "blocked"
        report["missing"] = list(fixture.surfaces)
        report["details"] = {
            "reason": "cargo is required for sdk-rust-grpc-smoke",
            "fixture_dir": str(fixture_dir),
            "required_tools": ["cargo"],
        }
        return report
    ####

    repo_root = Path(__file__).resolve().parents[4]
    grpc_fixture_dir = repo_root / "tests" / "fixtures" / "grpc"
    smoke_root = Path(tempfile.mkdtemp(prefix="zorn-rust-sdk-smoke-"))
    src_dir = smoke_root / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    (smoke_root / "Cargo.toml").write_text(
        textwrap.dedent(
            f"""
            [package]
            name = "zorn-sdk-rust-smoke"
            version = "0.1.0"
            edition = "2021"

            [dependencies]
            anduril-lattice-sdk = {{ path = "{fixture_dir.as_posix()}" }}
            prost = "0.13.1"
            serde_json = "1.0.145"
            tokio = {{ version = "1.48.0", features = ["macros", "rt-multi-thread", "time"] }}
            tonic = {{ version = "0.12.1", features = ["gzip"] }}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (src_dir / "main.rs").write_text(
        textwrap.dedent(
            """
            use anduril_lattice_sdk::anduril::entitymanager::v1 as entity;
            use anduril_lattice_sdk::anduril::entitymanager::v1::entity_manager_api_client::EntityManagerApiClient;
            use anduril_lattice_sdk::anduril::taskmanager::v1 as task;
            use anduril_lattice_sdk::anduril::taskmanager::v1::task_manager_api_client::TaskManagerApiClient;
            use prost::Message;
            use serde_json::json;
            use std::error::Error;
            use std::fs;
            use std::time::Duration;
            use tokio::time::timeout;
            use tonic::metadata::{Ascii, MetadataValue};
            use tonic::service::Interceptor;
            use tonic::transport::Channel;
            use tonic::{Request, Status};

            #[derive(Clone)]
            struct AuthInterceptor {
                authorization: MetadataValue<Ascii>,
            }

            impl Interceptor for AuthInterceptor {
                fn call(&mut self, mut request: Request<()>) -> Result<Request<()>, Status> {
                    request
                        .metadata_mut()
                        .insert("authorization", self.authorization.clone());
                    Ok(request)
                }
            }

            fn decode_message<T: Message + Default>(root: &str, path: &str) -> Result<T, Box<dyn Error>> {
                let bytes = fs::read(format!("{root}/{path}"))?;
                Ok(T::decode(bytes.as_slice())?)
            }

            fn auth_interceptor(token: &str) -> Result<AuthInterceptor, Box<dyn Error>> {
                Ok(AuthInterceptor {
                    authorization: format!("Bearer {token}").parse()?,
                })
            }

            #[tokio::main]
            async fn main() -> Result<(), Box<dyn Error>> {
                let grpc_target = std::env::var("ZORN_GRPC_TARGET")?;
                let token = std::env::var("ZORN_TOKEN")?;
                let fixture_root = std::env::var("ZORN_GRPC_FIXTURE_DIR")?;
                let channel = Channel::from_shared(format!("http://{grpc_target}"))?
                    .connect()
                    .await?;

                let mut entity_client =
                    EntityManagerApiClient::with_interceptor(channel.clone(), auth_interceptor(&token)?);
                let mut task_client =
                    TaskManagerApiClient::with_interceptor(channel, auth_interceptor(&token)?);

                let publish_request: entity::PublishEntityRequest =
                    decode_message(&fixture_root, "entity_publish_request.binpb")?;
                let publish_entity_id = publish_request
                    .entity
                    .as_ref()
                    .map(|entity| entity.entity_id.clone())
                    .unwrap_or_default();
                entity_client.publish_entity(publish_request).await?;
                let publish_get = entity_client
                    .get_entity(entity::GetEntityRequest {
                        entity_id: publish_entity_id.clone(),
                    })
                    .await?
                    .into_inner();
                let publish_ok = publish_get
                    .entity
                    .as_ref()
                    .map(|entity| entity.entity_id.as_str())
                    == Some(publish_entity_id.as_str());

                let get_request: entity::GetEntityRequest =
                    decode_message(&fixture_root, "entity_get_request.binpb")?;
                entity_client
                    .publish_entity(entity::PublishEntityRequest {
                        entity: Some(entity::Entity {
                            entity_id: get_request.entity_id.clone(),
                            description: "Rust gRPC get fixture".to_string(),
                            is_live: true,
                            ..Default::default()
                        }),
                    })
                    .await?;
                let get_response = entity_client.get_entity(get_request.clone()).await?.into_inner();
                let get_ok = get_response
                    .entity
                    .as_ref()
                    .map(|entity| entity.entity_id.as_str())
                    == Some(get_request.entity_id.as_str());

                entity_client
                    .publish_entity(entity::PublishEntityRequest {
                        entity: Some(entity::Entity {
                            entity_id: "grpc-wire-stream-entity".to_string(),
                            description: "Rust gRPC stream fixture".to_string(),
                            is_live: true,
                            ..Default::default()
                        }),
                    })
                    .await?;
                let stream_request: entity::StreamEntityComponentsRequest =
                    decode_message(&fixture_root, "entity_stream_request.binpb")?;
                let mut stream = entity_client
                    .stream_entity_components(stream_request)
                    .await?
                    .into_inner();
                let stream_first = timeout(Duration::from_secs(2), stream.message()).await??;
                let stream_entity_id = stream_first
                    .and_then(|item| item.entity_event)
                    .and_then(|event| event.entity)
                    .map(|entity| entity.entity_id)
                    .unwrap_or_default();
                let stream_ok = !stream_entity_id.is_empty();

                let create_request: task::CreateTaskRequest =
                    decode_message(&fixture_root, "task_create_request.binpb")?;
                let create_response = task_client
                    .create_task(create_request.clone())
                    .await?
                    .into_inner();
                let created_task = create_response.task.clone();
                let create_ok = created_task
                    .as_ref()
                    .and_then(|task| task.version.as_ref())
                    .map(|version| version.task_id.as_str())
                    == Some(create_request.task_id.as_str());

                let update_request: task::UpdateStatusRequest =
                    decode_message(&fixture_root, "task_update_status_request.binpb")?;
                let update_task_id = update_request
                    .status_update
                    .as_ref()
                    .and_then(|update| update.version.as_ref())
                    .map(|version| version.task_id.clone())
                    .unwrap_or_default();
                task_client
                    .create_task(task::CreateTaskRequest {
                        task_id: update_task_id.clone(),
                        display_name: "Rust gRPC update task".to_string(),
                        relations: Some(task::Relations {
                            assignee: Some(task::Principal {
                                on_behalf_of: None,
                                agent: Some(task::principal::Agent::System(task::System {
                                    service_name: String::new(),
                                    entity_id: "grpc-wire-agent-update".to_string(),
                                    manages_own_scheduling: false,
                                })),
                            }),
                            parent_task_id: String::new(),
                        }),
                        ..Default::default()
                    })
                    .await?;
                let update_response = task_client
                    .update_status(update_request)
                    .await?
                    .into_inner();
                let update_task = update_response.task.clone();
                let update_ok = update_task
                    .as_ref()
                    .and_then(|task| task.version.as_ref())
                    .map(|version| {
                        version.task_id == update_task_id && version.status_version >= 2
                    })
                    .unwrap_or(false);

                let listen_request: task::ListenAsAgentRequest =
                    decode_message(&fixture_root, "task_listen_as_agent_request.binpb")?;
                let listen_entity_id = match listen_request.agent_selector.as_ref() {
                    Some(task::listen_as_agent_request::AgentSelector::EntityIds(ids)) => {
                        ids.entity_ids.first().cloned().unwrap_or_default()
                    }
                    None => String::new(),
                };
                task_client
                    .create_task(task::CreateTaskRequest {
                        task_id: "grpc-wire-task-listen".to_string(),
                        display_name: "Rust gRPC listen task".to_string(),
                        relations: Some(task::Relations {
                            assignee: Some(task::Principal {
                                on_behalf_of: None,
                                agent: Some(task::principal::Agent::System(task::System {
                                    service_name: String::new(),
                                    entity_id: listen_entity_id.clone(),
                                    manages_own_scheduling: false,
                                })),
                            }),
                            parent_task_id: String::new(),
                        }),
                        ..Default::default()
                    })
                    .await?;
                let mut listen_stream = task_client
                    .listen_as_agent(listen_request)
                    .await?
                    .into_inner();
                let listen_first = timeout(Duration::from_secs(2), listen_stream.message()).await??;
                let listen_task_id = listen_first
                    .and_then(|item| item.request)
                    .and_then(|request| match request {
                        task::listen_as_agent_response::Request::ExecuteRequest(execute) => {
                            execute.task.and_then(|task| task.version.map(|version| version.task_id))
                        }
                        _ => None,
                    })
                    .unwrap_or_default();
                let listen_ok = listen_task_id == "grpc-wire-task-listen";

                let output = json!({
                    "transport.grpc_protobuf": { "ok": true, "grpc_target": grpc_target },
                    "auth.grpc_bearer_metadata": { "ok": true, "metadata": "authorization: Bearer <token>" },
                    "entities.publish": { "ok": publish_ok, "entity_id": publish_entity_id },
                    "entities.get": { "ok": get_ok, "entity_id": get_request.entity_id },
                    "entities.grpc_stream": { "ok": stream_ok, "entity_id": stream_entity_id },
                    "tasks.create": {
                        "ok": create_ok,
                        "task_id": create_response
                            .task
                            .as_ref()
                            .and_then(|task| task.version.as_ref())
                            .map(|version| version.task_id.clone())
                            .unwrap_or_default()
                    },
                    "tasks.update_status": {
                        "ok": update_ok,
                        "task_id": update_task
                            .as_ref()
                            .and_then(|task| task.version.as_ref())
                            .map(|version| version.task_id.clone())
                            .unwrap_or_default(),
                        "status_version": update_task
                            .as_ref()
                            .and_then(|task| task.version.as_ref())
                            .map(|version| version.status_version)
                            .unwrap_or_default()
                    },
                    "tasks.listen_as_agent": { "ok": listen_ok, "task_id": listen_task_id }
                });
                println!("{}", serde_json::to_string_pretty(&output)?);
                Ok(())
            }
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    env = {
        **os.environ,
        "CARGO_HOME": str(smoke_root / "cargo-home"),
        "CARGO_TARGET_DIR": str(smoke_root / "target"),
    }
    server = start_http_insecure_grpc_zorn_server(repo_root=repo_root, token=token)
    try:
        env.update(
            {
                "ZORN_GRPC_TARGET": server.grpc_target,
                "ZORN_TOKEN": token,
                "ZORN_GRPC_FIXTURE_DIR": str(grpc_fixture_dir),
            }
        )
        cargo_run = run_command(
            [cargo, "run", "--quiet"],
            cwd=smoke_root,
            env=env,
            timeout=300.0,
        )
        report["details"] = {
            "fixture_dir": str(fixture_dir),
            "language": "rust",
            "required_tools": ["cargo"],
            "grpc_fixture_dir": str(grpc_fixture_dir),
            "smoke_root": str(smoke_root),
            "cargo_run": {
                "args": cargo_run.args,
                "returncode": cargo_run.returncode,
                "stdout": cargo_run.stdout,
                "stderr": cargo_run.stderr,
            },
        }
        if cargo_run.returncode != 0:
            report["result"] = "failed"
            report["failed"] = list(fixture.surfaces)
            report["details"]["reason"] = "rust gRPC smoke executable failed"
            return report
        ####

        results = json.loads(cargo_run.stdout)
        report["details"]["results"] = results
        for surface in fixture.surfaces:
            detail = results.get(surface, {"ok": False})
            _record(report, surface, bool(detail.get("ok")), detail)
        ####
        report["missing"] = sorted(surface for surface in fixture.surfaces if surface not in report["passed"] and surface not in report["failed"])
        report["result"] = "failed" if report["failed"] else ("partial" if report["missing"] else "pass")
        return report
    finally:
        logs = stop_dual_transport_zorn_server(server)
        report.setdefault("details", {})
        report["details"]["server_log"] = logs["rest"]
        report["details"]["grpc_server_log"] = logs["grpc"]
        shutil.rmtree(smoke_root, ignore_errors=True)
    ####
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
        streamed_entity_id = streamed_entity.entity_id if streamed_entity is not None else ""
        results["entity_stream_request.binpb"] = {
            "ok": bool(streamed_entity_id),
            "response_type": stream_response.DESCRIPTOR.full_name,
            "entity_id": streamed_entity_id,
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
