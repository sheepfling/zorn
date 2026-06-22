from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from google.protobuf.any_pb2 import Any as AnyMessage
from google.protobuf.message import Message
from google.protobuf.wrappers_pb2 import StringValue

from ..grpc_api.proto_modules import LatticeProtoModules


@dataclass(frozen=True, slots=True)
class GoldenGrpcFixture:
    path: str
    rpc: str
    request: Message
#####


def request_message_type(proto_modules: LatticeProtoModules, rpc: str) -> type[Message]:
    mapping: dict[str, type[Message]] = {
        "anduril.entitymanager.v1.EntityManagerAPI.PublishEntity": proto_modules.entity_api.PublishEntityRequest,
        "anduril.entitymanager.v1.EntityManagerAPI.GetEntity": proto_modules.entity_api.GetEntityRequest,
        "anduril.entitymanager.v1.EntityManagerAPI.StreamEntityComponents": proto_modules.entity_api.StreamEntityComponentsRequest,
        "anduril.taskmanager.v1.TaskManagerAPI.CreateTask": proto_modules.task_api.CreateTaskRequest,
        "anduril.taskmanager.v1.TaskManagerAPI.UpdateStatus": proto_modules.task_api.UpdateStatusRequest,
        "anduril.taskmanager.v1.TaskManagerAPI.CancelTask": proto_modules.task_api.CancelTaskRequest,
        "anduril.taskmanager.v1.TaskManagerAPI.ListenAsAgent": proto_modules.task_api.ListenAsAgentRequest,
    }
    try:
        return mapping[rpc]
    except KeyError as exc:  # pragma: no cover - manifest contract violation
        raise KeyError(f"unsupported gRPC wire fixture rpc: {rpc}") from exc
    ####
#####


def build_golden_grpc_requests(proto_modules: LatticeProtoModules) -> dict[str, GoldenGrpcFixture]:
    if proto_modules.task is None:  # pragma: no cover - protected by pinned Buf package contract
        raise RuntimeError("Task protobuf module is required for golden gRPC wire fixtures")
    ####
    entity_message = proto_modules.entity.Entity(
        entity_id="grpc-wire-entity-publish",
        description="gRPC wire fixture entity",
        is_live=True,
        no_expiry=True,
    )
    publish_request = proto_modules.entity_api.PublishEntityRequest(entity=entity_message)
    get_request = proto_modules.entity_api.GetEntityRequest(entity_id="grpc-wire-entity-get")
    stream_request = proto_modules.entity_api.StreamEntityComponentsRequest(
        components_to_include=["description"],
        preexisting_only=True,
    )

    specification = AnyMessage()
    specification.Pack(StringValue(value="grpc-wire-create-spec"))
    create_request = proto_modules.task_api.CreateTaskRequest(
        task_id="grpc-wire-task-create",
        display_name="gRPC wire task create",
        description="Created from golden wire fixture",
        specification=specification,
    )
    create_request.relations.assignee.system.entity_id = "grpc-wire-agent-1"

    progress = AnyMessage()
    progress.Pack(StringValue(value="grpc-wire-progress"))
    update_request = proto_modules.task_api.UpdateStatusRequest()
    update_request.status_update.version.task_id = "grpc-wire-task-update"
    update_request.status_update.version.status_version = 1
    update_request.status_update.status.status = proto_modules.task.STATUS_EXECUTING
    update_request.status_update.status.progress.CopyFrom(progress)

    cancel_request = proto_modules.task_api.CancelTaskRequest(task_id="grpc-wire-task-cancel")
    cancel_request.author.system.service_name = "grpc-wire-fixtures"

    listen_request = proto_modules.task_api.ListenAsAgentRequest(heartbeat_interval_ms=0)
    listen_request.entity_ids.entity_ids.append("grpc-wire-agent-listen")

    fixtures = {
        "entity_publish_request.binpb": GoldenGrpcFixture(
            path="entity_publish_request.binpb",
            rpc="anduril.entitymanager.v1.EntityManagerAPI.PublishEntity",
            request=publish_request,
        ),
        "entity_get_request.binpb": GoldenGrpcFixture(
            path="entity_get_request.binpb",
            rpc="anduril.entitymanager.v1.EntityManagerAPI.GetEntity",
            request=get_request,
        ),
        "entity_stream_request.binpb": GoldenGrpcFixture(
            path="entity_stream_request.binpb",
            rpc="anduril.entitymanager.v1.EntityManagerAPI.StreamEntityComponents",
            request=stream_request,
        ),
        "task_create_request.binpb": GoldenGrpcFixture(
            path="task_create_request.binpb",
            rpc="anduril.taskmanager.v1.TaskManagerAPI.CreateTask",
            request=create_request,
        ),
        "task_update_status_request.binpb": GoldenGrpcFixture(
            path="task_update_status_request.binpb",
            rpc="anduril.taskmanager.v1.TaskManagerAPI.UpdateStatus",
            request=update_request,
        ),
        "task_cancel_request.binpb": GoldenGrpcFixture(
            path="task_cancel_request.binpb",
            rpc="anduril.taskmanager.v1.TaskManagerAPI.CancelTask",
            request=cancel_request,
        ),
        "task_listen_as_agent_request.binpb": GoldenGrpcFixture(
            path="task_listen_as_agent_request.binpb",
            rpc="anduril.taskmanager.v1.TaskManagerAPI.ListenAsAgent",
            request=listen_request,
        ),
    }
    return fixtures
#####


def request_metadata(message: Message) -> dict[str, Any]:
    descriptor = message.DESCRIPTOR
    metadata: dict[str, Any] = {
        "message_type": descriptor.full_name,
        "serialized_size": len(message.SerializeToString()),
        "fields": sorted(field.name for field, _value in message.ListFields()),
    }
    if descriptor.full_name.endswith("PublishEntityRequest") and hasattr(message, "entity"):
        metadata["entity_id"] = getattr(message.entity, "entity_id", "")
    elif descriptor.full_name.endswith("GetEntityRequest"):
        metadata["entity_id"] = getattr(message, "entity_id", "")
    elif descriptor.full_name.endswith("CreateTaskRequest"):
        metadata["task_id"] = getattr(message, "task_id", "")
    elif descriptor.full_name.endswith("CancelTaskRequest"):
        metadata["task_id"] = getattr(message, "task_id", "")
    elif descriptor.full_name.endswith("ListenAsAgentRequest") and hasattr(message, "entity_ids"):
        metadata["entity_ids"] = list(getattr(message.entity_ids, "entity_ids", []))
    elif descriptor.full_name.endswith("UpdateStatusRequest") and hasattr(message, "status_update"):
        metadata["task_id"] = getattr(message.status_update.version, "task_id", "")
        metadata["status_version"] = getattr(message.status_update.version, "status_version", 0)
    ####
    return metadata
#####
