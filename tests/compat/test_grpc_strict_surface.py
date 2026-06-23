from __future__ import annotations

from pathlib import Path

import grpc
from zorn.config import AppSettings
from zorn.grpc_api.proto_modules import load_lattice_proto_modules
from zorn.grpc_api.server import build_grpc_server
from zorn.runtime import build_store_bundle
import pytest

@pytest.mark.asyncio
async def test_grpc_runtime_does_not_expose_health_or_reflection(tmp_path: Path) -> None:
    proto_modules = load_lattice_proto_modules()
    settings = AppSettings(
        auth_mode="none",
        database_url=f"sqlite:///{tmp_path / 'grpc_strict_surface.db'}",
        object_root=tmp_path / "objects",
        grpc_port=0,
        poll_interval_seconds=0.01,
    )
    stores = build_store_bundle(settings)
    server = build_grpc_server(stores=stores, proto_modules=proto_modules)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
            health = channel.unary_unary(
                "/grpc.health.v1.Health/Check",
                request_serializer=bytes,
                response_deserializer=bytes,
            )
            with pytest.raises(grpc.aio.AioRpcError) as health_error:
                await health(b"")
            ####
            assert health_error.value.code() == grpc.StatusCode.UNIMPLEMENTED

            reflection = channel.stream_stream(
                "/grpc.reflection.v1alpha.ServerReflection/ServerReflectionInfo",
                request_serializer=bytes,
                response_deserializer=bytes,
            )
            with pytest.raises(grpc.aio.AioRpcError) as reflection_error:
                await reflection(iter([b""])).read()
            ####
            assert reflection_error.value.code() == grpc.StatusCode.UNIMPLEMENTED
    finally:
        await server.stop(0)
