from __future__ import annotations

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
import grpc
from typing import Any


HEALTH_SERVICE_NAME = "grpc.health.v1.Health"


def add_health_service(server: grpc.aio.Server) -> None:
    server.add_generic_rpc_handlers((_HealthHandler(),))
####


def health_service_names() -> tuple[str, ...]:
    return (HEALTH_SERVICE_NAME,)
####


def _message_classes() -> tuple[Any, Any]:
    pool = descriptor_pool.Default()
    try:
        request_descriptor = pool.FindMessageTypeByName("grpc.health.v1.HealthCheckRequest")
        response_descriptor = pool.FindMessageTypeByName("grpc.health.v1.HealthCheckResponse")
    except KeyError:
        pool.Add(_health_file_descriptor())
        request_descriptor = pool.FindMessageTypeByName("grpc.health.v1.HealthCheckRequest")
        response_descriptor = pool.FindMessageTypeByName("grpc.health.v1.HealthCheckResponse")
    ####
    return (
        message_factory.GetMessageClass(request_descriptor),
        message_factory.GetMessageClass(response_descriptor),
    )
####


class _HealthHandler(grpc.GenericRpcHandler):
    def service(self, handler_call_details: grpc.HandlerCallDetails) -> grpc.RpcMethodHandler | None:
        if handler_call_details.method == "/grpc.health.v1.Health/Check":
            request_type, response_type = _message_classes()
            return grpc.unary_unary_rpc_method_handler(
                _check,
                request_deserializer=request_type.FromString,
                response_serializer=lambda response: response.SerializeToString(),
            )
        ####
        return None
    ####
####


async def _check(request, context: grpc.aio.ServicerContext):
    _, response_type = _message_classes()
    response = response_type()
    response.status = 1
    return response
####


def _health_file_descriptor() -> descriptor_pb2.FileDescriptorProto:
    descriptor = descriptor_pb2.FileDescriptorProto()
    descriptor.name = "grpc/health/v1/health.proto"
    descriptor.package = "grpc.health.v1"
    descriptor.syntax = "proto3"

    request = descriptor.message_type.add()
    request.name = "HealthCheckRequest"
    service = request.field.add()
    service.name = "service"
    service.number = 1
    service.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    service.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING

    response = descriptor.message_type.add()
    response.name = "HealthCheckResponse"
    serving_status = response.enum_type.add()
    serving_status.name = "ServingStatus"
    for name, number in (
        ("UNKNOWN", 0),
        ("SERVING", 1),
        ("NOT_SERVING", 2),
        ("SERVICE_UNKNOWN", 3),
    ):
        value = serving_status.value.add()
        value.name = name
        value.number = number
    ####
    status = response.field.add()
    status.name = "status"
    status.number = 1
    status.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    status.type = descriptor_pb2.FieldDescriptorProto.TYPE_ENUM
    status.type_name = ".grpc.health.v1.HealthCheckResponse.ServingStatus"

    service_descriptor = descriptor.service.add()
    service_descriptor.name = "Health"
    check = service_descriptor.method.add()
    check.name = "Check"
    check.input_type = ".grpc.health.v1.HealthCheckRequest"
    check.output_type = ".grpc.health.v1.HealthCheckResponse"
    watch = service_descriptor.method.add()
    watch.name = "Watch"
    watch.input_type = ".grpc.health.v1.HealthCheckRequest"
    watch.output_type = ".grpc.health.v1.HealthCheckResponse"
    watch.server_streaming = True
    return descriptor
####
