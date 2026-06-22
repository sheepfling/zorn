from __future__ import annotations

import asyncio
import grpc

from ..config import AppSettings, load_settings
from ..runtime import StoreBundle, build_store_bundle
from .auth import AuthInterceptor
from .contract import assert_lattice_grpc_contract
from .health import add_health_service, health_service_names
from .entity_manager import EntityManagerServiceFactory
from .proto_modules import LatticeProtoModules, assert_official_package_versions, load_lattice_proto_modules
from .reflection import add_reflection_service
from .task_manager import TaskManagerServiceFactory
from .tls import bind_server


async def serve(settings: AppSettings | None = None) -> None:
    stores = build_store_bundle(settings or load_settings())
    assert_official_package_versions()
    proto_modules = load_lattice_proto_modules()
    if stores.settings.grpc_strict_proto_audit:
        assert_lattice_grpc_contract(proto_modules)
    ####
    server = build_grpc_server(stores=stores, proto_modules=proto_modules)
    address = f"{stores.settings.grpc_host}:{stores.settings.grpc_port}"
    bind_server(server, address=address, settings=stores.settings)
    await server.start()
    print(f"{stores.settings.product_name} gRPC compatibility server listening on {address}")
    try:
        await server.wait_for_termination()
    finally:
        await server.stop(0)
####


def build_grpc_server(
    *,
    stores: StoreBundle,
    proto_modules: LatticeProtoModules,
) -> grpc.aio.Server:
    options: list[tuple[str, int]] = [
        ("grpc.max_send_message_length", 64 * 1024 * 1024),
        ("grpc.max_receive_message_length", 64 * 1024 * 1024),
    ]
    if stores.settings.grpc_strict_proto_audit:
        assert_lattice_grpc_contract(proto_modules)
    ####
    server = grpc.aio.server(options=options, interceptors=(AuthInterceptor(stores.settings),))
    entity_service = EntityManagerServiceFactory(
        proto_modules=proto_modules,
        settings=stores.settings,
        database=stores.database,
        entity_store=stores.entity_store,
    ).build()
    task_service = TaskManagerServiceFactory(
        proto_modules=proto_modules,
        settings=stores.settings,
        database=stores.database,
        task_store=stores.task_store,
    ).build()
    proto_modules.entity_api_grpc.add_EntityManagerAPIServicer_to_server(entity_service, server)
    proto_modules.task_api_grpc.add_TaskManagerAPIServicer_to_server(task_service, server)
    add_health_service(server)
    add_reflection_service(server, proto_modules=proto_modules, extra_service_names=health_service_names())
    return server
####


def run() -> None:
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        return
####

