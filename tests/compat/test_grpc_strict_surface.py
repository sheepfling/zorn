from __future__ import annotations

import grpc
import pytest

from .conftest import GrpcCompatServer


async def test_grpc_runtime_does_not_expose_health_or_reflection(
    grpc_compat_server: GrpcCompatServer,
) -> None:
    async with grpc.aio.insecure_channel(grpc_compat_server.address) as channel:
        health = channel.unary_unary(
            "/grpc.health.v1.Health/Check",
            request_serializer=bytes,
            response_deserializer=bytes,
        )
        with pytest.raises(grpc.aio.AioRpcError) as health_error:
            await health(b"")
        ####
        assert health_error.value.code() is grpc.StatusCode.UNIMPLEMENTED

        reflection = channel.stream_stream(
            "/grpc.reflection.v1alpha.ServerReflection/ServerReflectionInfo",
            request_serializer=bytes,
            response_deserializer=bytes,
        )
        with pytest.raises(grpc.aio.AioRpcError) as reflection_error:
            await reflection(iter([b""])).read()
        ####
        assert reflection_error.value.code() is grpc.StatusCode.UNIMPLEMENTED
