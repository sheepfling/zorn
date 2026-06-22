from __future__ import annotations

import asyncio

import grpc

from .conftest import DualTransportCompat


async def test_rest_entity_publish_is_visible_via_grpc_get_and_stream(
    dual_transport_compat: DualTransportCompat,
    dual_transport_grpc_channel: grpc.aio.Channel,
) -> None:
    client = dual_transport_compat.rest_client
    proto_modules = dual_transport_compat.proto_modules
    entity_stub = proto_modules.entity_api_grpc.EntityManagerAPIStub(dual_transport_grpc_channel)

    publish = client.put(
        "/api/v1/entities",
        json={
            "entityId": "parity-rest-entity",
            "description": "REST-published parity entity",
            "isLive": True,
            "noExpiry": True,
            "ontology": {"template": "TEMPLATE_TRACK", "platformType": "UAS"},
            "provenance": {"sourceId": "parity-rest", "integrationName": "parity-rest"},
        },
    )
    assert publish.status_code == 200, publish.text

    fetched = await entity_stub.GetEntity(
        proto_modules.entity_api.GetEntityRequest(entity_id="parity-rest-entity")
    )
    assert fetched.entity.entity_id == "parity-rest-entity"

    stream = entity_stub.StreamEntityComponents(
        proto_modules.entity_api.StreamEntityComponentsRequest(
            preexisting_only=True,
            heartbeat_period_millis=0,
        )
    )
    event = await asyncio.wait_for(stream.read(), timeout=2)
    stream.cancel()

    assert event.entity_event.entity.entity_id == "parity-rest-entity"


async def test_grpc_entity_publish_is_visible_via_rest_get(
    dual_transport_compat: DualTransportCompat,
    dual_transport_grpc_channel: grpc.aio.Channel,
) -> None:
    client = dual_transport_compat.rest_client
    proto_modules = dual_transport_compat.proto_modules
    entity_stub = proto_modules.entity_api_grpc.EntityManagerAPIStub(dual_transport_grpc_channel)

    await entity_stub.PublishEntity(
        proto_modules.entity_api.PublishEntityRequest(
            entity=proto_modules.entity.Entity(
                entity_id="parity-grpc-entity",
                description="gRPC-published parity entity",
                is_live=True,
                no_expiry=True,
            )
        )
    )

    response = client.get("/api/v1/entities/parity-grpc-entity")
    assert response.status_code == 200, response.text
    assert response.json()["entityId"] == "parity-grpc-entity"


async def test_rest_and_grpc_task_lifecycle_share_state(
    dual_transport_compat: DualTransportCompat,
    dual_transport_grpc_channel: grpc.aio.Channel,
) -> None:
    client = dual_transport_compat.rest_client
    proto_modules = dual_transport_compat.proto_modules
    task_module = proto_modules.task
    assert task_module is not None
    task_stub = proto_modules.task_api_grpc.TaskManagerAPIStub(dual_transport_grpc_channel)

    create_rest = client.post(
        "/api/v1/tasks",
        json={
            "taskId": "parity-rest-task",
            "displayName": "REST parity task",
            "relations": {
                "assignee": {
                    "system": {
                        "entityId": "parity-agent-rest",
                    }
                }
            },
        },
    )
    assert create_rest.status_code == 201, create_rest.text

    grpc_get_rest_task = await task_stub.GetTask(
        proto_modules.task_api.GetTaskRequest(task_id="parity-rest-task")
    )
    assert grpc_get_rest_task.task.version.task_id == "parity-rest-task"

    listen_call = task_stub.ListenAsAgent(
        proto_modules.task_api.ListenAsAgentRequest(
            entity_ids=proto_modules.task_api.EntityIds(entity_ids=["parity-agent-rest"])
        )
    )
    listen_response = await asyncio.wait_for(listen_call.read(), timeout=2)
    listen_call.cancel()
    assert listen_response.execute_request.task.version.task_id == "parity-rest-task"

    updated = await task_stub.UpdateStatus(
        proto_modules.task_api.UpdateStatusRequest(
            status_update=task_module.StatusUpdate(
                version=task_module.TaskVersion(
                    task_id="parity-rest-task",
                    status_version=1,
                ),
                status=task_module.TaskStatus(status=task_module.STATUS_EXECUTING),
            )
        )
    )
    assert updated.task.version.status_version >= 2

    rest_get_after_grpc_update = client.get("/api/v1/tasks/parity-rest-task")
    assert rest_get_after_grpc_update.status_code == 200, rest_get_after_grpc_update.text
    assert rest_get_after_grpc_update.json()["status"]["status"] == "STATUS_EXECUTING"

    grpc_created = await task_stub.CreateTask(
        proto_modules.task_api.CreateTaskRequest(
            task_id="parity-grpc-task",
            display_name="gRPC parity task",
            relations=task_module.Relations(
                assignee=task_module.Principal(
                    system=task_module.System(entity_id="parity-agent-grpc")
                )
            ),
        )
    )
    assert grpc_created.task.version.task_id == "parity-grpc-task"

    rest_get_grpc_task = client.get("/api/v1/tasks/parity-grpc-task")
    assert rest_get_grpc_task.status_code == 200, rest_get_grpc_task.text
    assert rest_get_grpc_task.json()["taskId"] == "parity-grpc-task"

    rest_update = client.put(
        "/api/v1/tasks/parity-grpc-task/status",
        json={"statusVersion": 1, "newStatus": {"status": "STATUS_EXECUTING"}},
    )
    assert rest_update.status_code == 200, rest_update.text

    grpc_get_after_rest_update = await task_stub.GetTask(
        proto_modules.task_api.GetTaskRequest(task_id="parity-grpc-task")
    )
    assert grpc_get_after_rest_update.task.version.task_id == "parity-grpc-task"
    assert grpc_get_after_rest_update.task.version.status_version >= 2
    assert grpc_get_after_rest_update.task.status.status == task_module.STATUS_EXECUTING
####


async def test_rest_cancel_is_delivered_as_grpc_cancel_request(
    dual_transport_compat: DualTransportCompat,
    dual_transport_grpc_channel: grpc.aio.Channel,
) -> None:
    client = dual_transport_compat.rest_client
    proto_modules = dual_transport_compat.proto_modules
    task_stub = proto_modules.task_api_grpc.TaskManagerAPIStub(dual_transport_grpc_channel)

    created = client.post(
        "/api/v1/tasks",
        json={
            "taskId": "parity-rest-cancel-task",
            "displayName": "REST cancel parity task",
            "relations": {
                "assignee": {
                    "system": {
                        "entityId": "parity-agent-cancel-rest",
                    }
                }
            },
        },
    )
    assert created.status_code == 201, created.text

    listen_call = task_stub.ListenAsAgent(
        proto_modules.task_api.ListenAsAgentRequest(
            entity_ids=proto_modules.task_api.EntityIds(entity_ids=["parity-agent-cancel-rest"])
        )
    )
    first = await asyncio.wait_for(listen_call.read(), timeout=2)
    assert first.execute_request.task.version.task_id == "parity-rest-cancel-task"

    canceled = client.put(
        "/api/v1/tasks/parity-rest-cancel-task/cancel",
        json={"reason": "operator cancel"},
    )
    assert canceled.status_code == 200, canceled.text

    second = await asyncio.wait_for(listen_call.read(), timeout=2)
    listen_call.cancel()

    assert second.cancel_request.task_id == "parity-rest-cancel-task"
    assert second.cancel_request.assignee.system.entity_id == "parity-agent-cancel-rest"


async def test_grpc_cancel_is_delivered_as_rest_cancel_request(
    dual_transport_compat: DualTransportCompat,
    dual_transport_grpc_channel: grpc.aio.Channel,
) -> None:
    client = dual_transport_compat.rest_client
    proto_modules = dual_transport_compat.proto_modules
    task_module = proto_modules.task
    assert task_module is not None
    task_stub = proto_modules.task_api_grpc.TaskManagerAPIStub(dual_transport_grpc_channel)

    created = await task_stub.CreateTask(
        proto_modules.task_api.CreateTaskRequest(
            task_id="parity-grpc-cancel-task",
            display_name="gRPC cancel parity task",
            relations=task_module.Relations(
                assignee=task_module.Principal(
                    system=task_module.System(entity_id="parity-agent-cancel-grpc")
                )
            ),
        )
    )
    assert created.task.version.task_id == "parity-grpc-cancel-task"

    first = client.post("/api/v1/agent/listen", json={"agentSelector": {"entityIds": ["parity-agent-cancel-grpc"]}})
    assert first.status_code == 200, first.text
    assert first.json()["executeRequest"]["task"]["taskId"] == "parity-grpc-cancel-task"

    canceled = await task_stub.CancelTask(
        proto_modules.task_api.CancelTaskRequest(
            task_id="parity-grpc-cancel-task",
        )
    )
    assert canceled.task.version.task_id == "parity-grpc-cancel-task"

    second = client.post("/api/v1/agent/listen", json={"agentSelector": {"entityIds": ["parity-agent-cancel-grpc"]}})
    assert second.status_code == 200, second.text
    assert second.json()["cancelRequest"]["task"]["taskId"] == "parity-grpc-cancel-task"


async def test_rest_task_stream_and_grpc_task_stream_observe_same_cancelled_task_state(
    dual_transport_compat: DualTransportCompat,
    dual_transport_grpc_channel: grpc.aio.Channel,
) -> None:
    client = dual_transport_compat.rest_client
    proto_modules = dual_transport_compat.proto_modules
    task_module = proto_modules.task
    assert task_module is not None
    task_stub = proto_modules.task_api_grpc.TaskManagerAPIStub(dual_transport_grpc_channel)

    created = client.post(
        "/api/v1/tasks",
        json={
            "taskId": "parity-stream-task",
            "displayName": "Task stream parity task",
            "relations": {
                "assignee": {
                    "system": {
                        "entityId": "parity-agent-stream",
                    }
                }
            },
        },
    )
    assert created.status_code == 201, created.text

    grpc_stream = task_stub.StreamTasks(
        proto_modules.task_api.StreamTasksRequest(
            heartbeat_interval_ms=0,
        )
    )
    first = await asyncio.wait_for(grpc_stream.read(), timeout=2)
    assert first.task_event.task.version.task_id == "parity-stream-task"

    canceled = client.put(
        "/api/v1/tasks/parity-stream-task/cancel",
        json={"reason": "parity stream cancel"},
    )
    assert canceled.status_code == 200, canceled.text

    second = await asyncio.wait_for(grpc_stream.read(), timeout=2)
    grpc_stream.cancel()

    assert second.task_event.task.version.task_id == "parity-stream-task"
    assert second.task_event.task.status.status == task_module.STATUS_DONE_NOT_OK
