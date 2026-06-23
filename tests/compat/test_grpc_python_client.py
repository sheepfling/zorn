from __future__ import annotations

import asyncio

import grpc
import pytest
from fastapi.testclient import TestClient

from zorn import build_app

from .conftest import GrpcCompatServer


async def test_official_python_generated_client_entity_and_task_calls(
    grpc_compat_server: GrpcCompatServer,
    grpc_channel: grpc.aio.Channel,
) -> None:
    proto_modules = grpc_compat_server.proto_modules
    entity_stub = proto_modules.entity_api_grpc.EntityManagerAPIStub(grpc_channel)
    task_stub = proto_modules.task_api_grpc.TaskManagerAPIStub(grpc_channel)

    entity = proto_modules.entity.Entity(
        entity_id="compat-python-entity",
        description="generated Python client entity",
        is_live=True,
        no_expiry=True,
    )
    await entity_stub.PublishEntity(proto_modules.entity_api.PublishEntityRequest(entity=entity))
    get_entity_response = await entity_stub.GetEntity(
        proto_modules.entity_api.GetEntityRequest(entity_id="compat-python-entity")
    )
    assert get_entity_response.entity.entity_id == "compat-python-entity"

    create_task_response = await task_stub.CreateTask(
        proto_modules.task_api.CreateTaskRequest(
            task_id="compat-python-task",
            display_name="Generated Python task",
            description="created by compatibility harness",
        )
    )
    assert create_task_response.task.version.task_id == "compat-python-task"

    listen_call = task_stub.ListenAsAgent(proto_modules.task_api.ListenAsAgentRequest())
    listen_response = await asyncio.wait_for(listen_call.read(), timeout=2)
    assert any(
        listen_response.HasField(field_name)
        for field_name in ("execute_request", "cancel_request", "complete_request", "heartbeat")
    )
    listen_call.cancel()


async def test_grpc_update_status_preserves_status_version_context(
    grpc_compat_server: GrpcCompatServer,
    grpc_channel: grpc.aio.Channel,
) -> None:
    proto_modules = grpc_compat_server.proto_modules
    task_module = proto_modules.task
    assert task_module is not None
    task_stub = proto_modules.task_api_grpc.TaskManagerAPIStub(grpc_channel)

    await task_stub.CreateTask(
        proto_modules.task_api.CreateTaskRequest(
            task_id="compat-python-status-task",
            display_name="Generated Python status task",
        )
    )
    response = await task_stub.UpdateStatus(
        proto_modules.task_api.UpdateStatusRequest(
            status_update=task_module.StatusUpdate(
                version=task_module.TaskVersion(
                    task_id="compat-python-status-task",
                    status_version=1,
                ),
                status=task_module.TaskStatus(
                    status=task_module.STATUS_EXECUTING,
                ),
            )
        )
    )

    assert response.task.version.task_id == "compat-python-status-task"
    assert response.task.version.status_version >= 2
    assert response.task.status.status == task_module.STATUS_EXECUTING


async def test_grpc_listen_as_agent_honors_entity_ids_selector(
    grpc_compat_server: GrpcCompatServer,
    grpc_channel: grpc.aio.Channel,
) -> None:
    proto_modules = grpc_compat_server.proto_modules
    task_module = proto_modules.task
    assert task_module is not None
    task_stub = proto_modules.task_api_grpc.TaskManagerAPIStub(grpc_channel)

    await task_stub.CreateTask(
        proto_modules.task_api.CreateTaskRequest(
            task_id="compat-python-listen-a",
            display_name="Task A",
            relations=task_module.Relations(
                assignee=task_module.Principal(
                    system=task_module.System(entity_id="agent-a"),
                )
            ),
        )
    )
    await task_stub.CreateTask(
        proto_modules.task_api.CreateTaskRequest(
            task_id="compat-python-listen-b",
            display_name="Task B",
            relations=task_module.Relations(
                assignee=task_module.Principal(
                    system=task_module.System(entity_id="agent-b"),
                )
            ),
        )
    )

    listen_call = task_stub.ListenAsAgent(
        proto_modules.task_api.ListenAsAgentRequest(
            entity_ids=proto_modules.task_api.EntityIds(entity_ids=["agent-b"])
        )
    )
    response = await asyncio.wait_for(listen_call.read(), timeout=2)
    listen_call.cancel()

    assert response.execute_request.task.version.task_id == "compat-python-listen-b"


async def test_grpc_static_auth_accepts_bearer_metadata(grpc_auth_server: GrpcCompatServer) -> None:
    proto_modules = grpc_auth_server.proto_modules
    async with grpc.aio.insecure_channel(grpc_auth_server.address) as channel:
        stub = proto_modules.entity_api_grpc.EntityManagerAPIStub(channel)
        entity = proto_modules.entity.Entity(
            entity_id="auth-entity",
            description="authorized",
            is_live=True,
            no_expiry=True,
        )
        await stub.PublishEntity(
            proto_modules.entity_api.PublishEntityRequest(entity=entity),
            metadata=(("authorization", "Bearer dev-token"),),
        )
        response = await stub.GetEntity(
            proto_modules.entity_api.GetEntityRequest(entity_id="auth-entity"),
            metadata=(("x-api-key", "dev-token"),),
        )
    ####
    assert response.entity.entity_id == "auth-entity"


async def test_grpc_static_auth_rejects_invalid_token(grpc_auth_server: GrpcCompatServer) -> None:
    proto_modules = grpc_auth_server.proto_modules
    async with grpc.aio.insecure_channel(grpc_auth_server.address) as channel:
        stub = proto_modules.entity_api_grpc.EntityManagerAPIStub(channel)
        with pytest.raises(grpc.aio.AioRpcError) as exc_info:
            await stub.GetEntity(
                proto_modules.entity_api.GetEntityRequest(entity_id="missing"),
                metadata=(("authorization", "Bearer wrong-token"),),
            )
    ####
    assert exc_info.value.code() == grpc.StatusCode.UNAUTHENTICATED


async def test_grpc_oauth_issued_token_is_accepted_and_then_expires(grpc_oauth_server: GrpcCompatServer) -> None:
    proto_modules = grpc_oauth_server.proto_modules
    app = build_app(grpc_oauth_server.settings)
    with TestClient(app) as client:
        token_response = client.post("/api/v1/oauth/token", json={"client_id": "dev", "client_secret": "dev"})
        assert token_response.status_code == 200
        token = token_response.json()["access_token"]
        assert token != "dev-token"
    ####

    async with grpc.aio.insecure_channel(grpc_oauth_server.address) as channel:
        stub = proto_modules.entity_api_grpc.EntityManagerAPIStub(channel)
        entity = proto_modules.entity.Entity(
            entity_id="grpc-oauth-issued-token-entity",
            description="oauth issued token",
            is_live=True,
            no_expiry=True,
        )
        await stub.PublishEntity(
            proto_modules.entity_api.PublishEntityRequest(entity=entity),
            metadata=(("authorization", f"Bearer {token}"),),
        )

        await asyncio.sleep(1.1)

        with pytest.raises(grpc.aio.AioRpcError) as exc_info:
            await stub.GetEntity(
                proto_modules.entity_api.GetEntityRequest(entity_id="grpc-oauth-issued-token-entity"),
                metadata=(("authorization", f"Bearer {token}"),),
            )
    ####
    assert exc_info.value.code() == grpc.StatusCode.UNAUTHENTICATED


async def test_grpc_static_auth_requires_sandbox_metadata_when_enabled(grpc_sandbox_auth_server: GrpcCompatServer) -> None:
    proto_modules = grpc_sandbox_auth_server.proto_modules
    async with grpc.aio.insecure_channel(grpc_sandbox_auth_server.address) as channel:
        stub = proto_modules.entity_api_grpc.EntityManagerAPIStub(channel)
        entity = proto_modules.entity.Entity(
            entity_id="grpc-sandbox-auth-entity",
            description="sandbox metadata required",
            is_live=True,
            no_expiry=True,
        )
        with pytest.raises(grpc.aio.AioRpcError) as exc_info:
            await stub.PublishEntity(
                proto_modules.entity_api.PublishEntityRequest(entity=entity),
                metadata=(("authorization", "Bearer dev-token"),),
            )
        await stub.PublishEntity(
            proto_modules.entity_api.PublishEntityRequest(entity=entity),
            metadata=(
                ("authorization", "Bearer dev-token"),
                ("anduril-sandbox-authorization", "Bearer dev-token"),
            ),
        )
    ####
    assert exc_info.value.code() == grpc.StatusCode.PERMISSION_DENIED


async def test_grpc_strict_auth_requires_separate_bearer_and_sandbox_metadata(
    grpc_strict_sandbox_auth_server: GrpcCompatServer,
) -> None:
    proto_modules = grpc_strict_sandbox_auth_server.proto_modules
    async with grpc.aio.insecure_channel(grpc_strict_sandbox_auth_server.address) as channel:
        stub = proto_modules.entity_api_grpc.EntityManagerAPIStub(channel)
        entity = proto_modules.entity.Entity(
            entity_id="grpc-strict-sandbox-auth-entity",
            description="strict sandbox metadata required",
            is_live=True,
            no_expiry=True,
        )
        with pytest.raises(grpc.aio.AioRpcError) as legacy_exc_info:
            await stub.PublishEntity(
                proto_modules.entity_api.PublishEntityRequest(entity=entity),
                metadata=(("anduril-sandbox-authorization", "Bearer dev-token"),),
            )

        await stub.PublishEntity(
            proto_modules.entity_api.PublishEntityRequest(entity=entity),
            metadata=(
                ("authorization", "Bearer dev-token"),
                ("x-anduril-sandbox", "zorn-cert"),
            ),
        )

    assert legacy_exc_info.value.code() == grpc.StatusCode.UNAUTHENTICATED


async def test_grpc_cancel_rejects_already_terminal_task(
    grpc_compat_server: GrpcCompatServer,
    grpc_channel: grpc.aio.Channel,
) -> None:
    proto_modules = grpc_compat_server.proto_modules
    task_stub = proto_modules.task_api_grpc.TaskManagerAPIStub(grpc_channel)

    await task_stub.CreateTask(
        proto_modules.task_api.CreateTaskRequest(
            task_id="compat-python-cancel-terminal-task",
            display_name="Cancel terminal task",
        )
    )
    await task_stub.CancelTask(
        proto_modules.task_api.CancelTaskRequest(
            task_id="compat-python-cancel-terminal-task",
        )
    )

    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await task_stub.CancelTask(
            proto_modules.task_api.CancelTaskRequest(
                task_id="compat-python-cancel-terminal-task",
            )
        )

    assert exc_info.value.code() == grpc.StatusCode.FAILED_PRECONDITION


async def test_grpc_manual_control_stream_closes_when_task_becomes_terminal(
    grpc_compat_server: GrpcCompatServer,
    grpc_channel: grpc.aio.Channel,
) -> None:
    proto_modules = grpc_compat_server.proto_modules
    task_stub = proto_modules.task_api_grpc.TaskManagerAPIStub(grpc_channel)

    await task_stub.CreateTask(
        proto_modules.task_api.CreateTaskRequest(
            task_id="compat-python-manual-control-task",
            display_name="Manual control terminal close",
        )
    )

    frame_call = task_stub.ListenForManualControlFrames(
        proto_modules.task_api.ListenForManualControlFramesRequest(
            task_id="compat-python-manual-control-task",
        )
    )
    await task_stub.CancelTask(
        proto_modules.task_api.CancelTaskRequest(
            task_id="compat-python-manual-control-task",
        )
    )

    response = await asyncio.wait_for(frame_call.read(), timeout=2)
    assert response is grpc.aio.EOF


async def test_grpc_stream_tasks_excludes_terminal_preexisting_tasks(
    grpc_compat_server: GrpcCompatServer,
    grpc_channel: grpc.aio.Channel,
) -> None:
    proto_modules = grpc_compat_server.proto_modules
    task_stub = proto_modules.task_api_grpc.TaskManagerAPIStub(grpc_channel)

    await task_stub.CreateTask(
        proto_modules.task_api.CreateTaskRequest(
            task_id="compat-python-terminal-preexisting",
            display_name="Terminal preexisting",
        )
    )
    await task_stub.CancelTask(
        proto_modules.task_api.CancelTaskRequest(
            task_id="compat-python-terminal-preexisting",
        )
    )
    await task_stub.CreateTask(
        proto_modules.task_api.CreateTaskRequest(
            task_id="compat-python-open-preexisting",
            display_name="Open preexisting",
        )
    )

    stream = task_stub.StreamTasks(
        proto_modules.task_api.StreamTasksRequest(
            heartbeat_interval_ms=0,
        )
    )
    response = await asyncio.wait_for(stream.read(), timeout=2)
    stream.cancel()

    assert response.task_event.task.version.task_id == "compat-python-open-preexisting"


async def test_grpc_manual_control_missing_task_is_not_found(
    grpc_compat_server: GrpcCompatServer,
    grpc_channel: grpc.aio.Channel,
) -> None:
    proto_modules = grpc_compat_server.proto_modules
    task_stub = proto_modules.task_api_grpc.TaskManagerAPIStub(grpc_channel)

    frame_call = task_stub.ListenForManualControlFrames(
        proto_modules.task_api.ListenForManualControlFramesRequest(
            task_id="compat-python-missing-manual-control-task",
        )
    )

    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await asyncio.wait_for(frame_call.read(), timeout=2)

    assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND


async def test_grpc_manual_control_terminal_task_closes_immediately(
    grpc_compat_server: GrpcCompatServer,
    grpc_channel: grpc.aio.Channel,
) -> None:
    proto_modules = grpc_compat_server.proto_modules
    task_stub = proto_modules.task_api_grpc.TaskManagerAPIStub(grpc_channel)

    await task_stub.CreateTask(
        proto_modules.task_api.CreateTaskRequest(
            task_id="compat-python-terminal-manual-control-task",
            display_name="Terminal manual control",
        )
    )
    await task_stub.CancelTask(
        proto_modules.task_api.CancelTaskRequest(
            task_id="compat-python-terminal-manual-control-task",
        )
    )

    frame_call = task_stub.ListenForManualControlFrames(
        proto_modules.task_api.ListenForManualControlFramesRequest(
            task_id="compat-python-terminal-manual-control-task",
        )
    )

    response = await asyncio.wait_for(frame_call.read(), timeout=2)
    assert response is grpc.aio.EOF
