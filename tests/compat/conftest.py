from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path

import grpc
import pytest
from fastapi.testclient import TestClient

from zorn import build_app
from zorn.config import AppSettings
from zorn.grpc_api.proto_modules import LatticeProtoModules, load_lattice_proto_modules
from zorn.grpc_api.server import build_grpc_server
from zorn.runtime import build_store_bundle


@dataclass(frozen=True, slots=True)
class GrpcCompatServer:
    address: str
    settings: AppSettings
    proto_modules: LatticeProtoModules


@dataclass(frozen=True, slots=True)
class DualTransportCompat:
    address: str
    settings: AppSettings
    proto_modules: LatticeProtoModules
    rest_client: TestClient


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
async def grpc_oauth_server(tmp_path: Path, proto_modules: LatticeProtoModules) -> AsyncGenerator[GrpcCompatServer]:
    settings = AppSettings(
        auth_mode="oauth-dev",
        static_tokens=["dev-token"],
        oauth_dev_token_ttl_seconds=1,
        database_url=f"sqlite:///{tmp_path / 'grpc_oauth.db'}",
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
async def grpc_sandbox_auth_server(tmp_path: Path, proto_modules: LatticeProtoModules) -> AsyncGenerator[GrpcCompatServer]:
    settings = AppSettings(
        auth_mode="static",
        static_tokens=["dev-token"],
        require_sandbox_header=True,
        database_url=f"sqlite:///{tmp_path / 'grpc_sandbox_auth.db'}",
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
async def grpc_strict_sandbox_auth_server(tmp_path: Path, proto_modules: LatticeProtoModules) -> AsyncGenerator[GrpcCompatServer]:
    settings = AppSettings(
        auth_mode="oauth-dev",
        static_tokens=["dev-token"],
        oauth_dev_token_ttl_seconds=3600,
        oauth_dev_signing_secret="grpc-strict-sandbox-secret",
        oauth_scope_mode="informational",
        require_sandbox_header=True,
        grpc_sandbox_auth_mode="strict_separate",
        strict_startup=True,
        grpc_strict_proto_audit=True,
        database_url=f"sqlite:///{tmp_path / 'grpc_strict_sandbox_auth.db'}",
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


@pytest.fixture()
async def dual_transport_compat(
    tmp_path: Path,
    proto_modules: LatticeProtoModules,
) -> AsyncGenerator[DualTransportCompat]:
    settings = AppSettings(
        auth_mode="none",
        database_url=f"sqlite:///{tmp_path / 'dual_transport.db'}",
        object_root=tmp_path / "objects",
        grpc_port=0,
        heartbeat_seconds=0.1,
        poll_interval_seconds=0.01,
    )
    app = build_app(settings)
    stores = build_store_bundle(settings)
    server = build_grpc_server(stores=stores, proto_modules=proto_modules)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        with TestClient(app) as rest_client:
            yield DualTransportCompat(
                address=f"127.0.0.1:{port}",
                settings=settings,
                proto_modules=proto_modules,
                rest_client=rest_client,
            )
    finally:
        await server.stop(0)
    ####
####


@pytest.fixture()
async def dual_transport_grpc_channel(
    dual_transport_compat: DualTransportCompat,
) -> AsyncGenerator[grpc.aio.Channel]:
    channel = grpc.aio.insecure_channel(dual_transport_compat.address)
    try:
        yield channel
    finally:
        await channel.close()
    ####
####
