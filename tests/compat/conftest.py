from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path

import grpc
import pytest

from zorn.config import AppSettings
from zorn.grpc_api.proto_modules import LatticeProtoModules, load_lattice_proto_modules
from zorn.grpc_api.server import build_grpc_server
from zorn.runtime import build_store_bundle


@dataclass(frozen=True, slots=True)
class GrpcCompatServer:
    address: str
    settings: AppSettings
    proto_modules: LatticeProtoModules


@pytest.fixture()
def proto_modules() -> LatticeProtoModules:
    return load_lattice_proto_modules()


@pytest.fixture()
async def grpc_compat_server(tmp_path: Path, proto_modules: LatticeProtoModules) -> AsyncGenerator[GrpcCompatServer]:
    settings = AppSettings(
        auth_mode="none",
        database_url=f"sqlite:///{tmp_path / 'grpc_compat.db'}",
        object_root=tmp_path / "objects",
        grpc_port=0,
        poll_interval_seconds=0.01,
    )
    stores = build_store_bundle(settings)
    server = build_grpc_server(stores=stores, proto_modules=proto_modules)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        yield GrpcCompatServer(
            address=f"127.0.0.1:{port}",
            settings=settings,
            proto_modules=proto_modules,
        )
    finally:
        await server.stop(0)
    ####
####


@pytest.fixture()
async def grpc_auth_server(tmp_path: Path, proto_modules: LatticeProtoModules) -> AsyncGenerator[GrpcCompatServer]:
    settings = AppSettings(
        auth_mode="static",
        static_tokens=["dev-token"],
        database_url=f"sqlite:///{tmp_path / 'grpc_auth.db'}",
        object_root=tmp_path / "objects",
        grpc_port=0,
        poll_interval_seconds=0.01,
    )
    stores = build_store_bundle(settings)
    server = build_grpc_server(stores=stores, proto_modules=proto_modules)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        yield GrpcCompatServer(
            address=f"127.0.0.1:{port}",
            settings=settings,
            proto_modules=proto_modules,
        )
    finally:
        await server.stop(0)
    ####
####


@pytest.fixture()
async def grpc_channel(grpc_compat_server: GrpcCompatServer) -> AsyncGenerator[grpc.aio.Channel]:
    channel = grpc.aio.insecure_channel(grpc_compat_server.address)
    try:
        yield channel
    finally:
        await channel.close()
    ####
####
