from __future__ import annotations

import grpc

from zorn.grpc_api.health import _message_classes as health_message_classes
from zorn.grpc_api.reflection import _message_classes as reflection_message_classes

from .conftest import GrpcCompatServer


async def test_grpc_reflection_lists_lattice_services(grpc_compat_server: GrpcCompatServer) -> None:
    request_type, response_type = reflection_message_classes()
    async with grpc.aio.insecure_channel(grpc_compat_server.address) as channel:
        call = channel.stream_stream(
            "/grpc.reflection.v1alpha.ServerReflection/ServerReflectionInfo",
            request_serializer=lambda request: request.SerializeToString(),
            response_deserializer=response_type.FromString,
        )
        responses = call(iter([request_type(list_services="")]))
        response = await responses.read()
    ####

    service_names = {service.name for service in response.list_services_response.service}
    assert "anduril.entitymanager.v1.EntityManagerAPI" in service_names
    assert "anduril.taskmanager.v1.TaskManagerAPI" in service_names
    assert "grpc.health.v1.Health" in service_names


async def test_grpc_reflection_describes_entity_manager(grpc_compat_server: GrpcCompatServer) -> None:
    request_type, response_type = reflection_message_classes()
    async with grpc.aio.insecure_channel(grpc_compat_server.address) as channel:
        call = channel.stream_stream(
            "/grpc.reflection.v1alpha.ServerReflection/ServerReflectionInfo",
            request_serializer=lambda request: request.SerializeToString(),
            response_deserializer=response_type.FromString,
        )
        responses = call(
            iter(
                [
                    request_type(
                        file_containing_symbol="anduril.entitymanager.v1.EntityManagerAPI",
                    )
                ]
            )
        )
        response = await responses.read()
    ####

    assert response.file_descriptor_response.file_descriptor_proto


async def test_grpc_health_check_serving(grpc_compat_server: GrpcCompatServer) -> None:
    request_type, response_type = health_message_classes()
    async with grpc.aio.insecure_channel(grpc_compat_server.address) as channel:
        check = channel.unary_unary(
            "/grpc.health.v1.Health/Check",
            request_serializer=lambda request: request.SerializeToString(),
            response_deserializer=response_type.FromString,
        )
        response = await check(request_type(service=""))
    ####

    assert response.status == 1
