from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from importlib import metadata
from typing import Any


BUF_PYTHON_INDEX_URL = "https://buf.build/gen/python"
LATTICE_BSR_MODULE = "buf.build/anduril/lattice-sdk"

OFFICIAL_BUF_PACKAGES: dict[str, str] = {
    "anduril-lattice-sdk-grpc-python": "1.80.0.1.20260515215502+ed34febdefc1",
    "anduril-lattice-sdk-protocolbuffers-python": "34.1.0.1.20260515215502+ed34febdefc1",
    "anduril-lattice-sdk-protocolbuffers-pyi": "34.1.0.1.20260515215502+ed34febdefc1",
}


class MissingLatticeProtoDependency(RuntimeError):
    pass
####


@dataclass(slots=True)
class LatticeProtoModules:
    entity_api: Any
    entity_grpcapi: Any
    entity_api_grpc: Any
    entity: Any
    task_api: Any
    task_grpcapi: Any
    task_api_grpc: Any
    task: Any | None = None

    def module_names(self) -> dict[str, str | None]:
        return {
            "entity_api": self.entity_api.__name__,
            "entity_grpcapi": self.entity_grpcapi.__name__,
            "entity_api_grpc": self.entity_api_grpc.__name__,
            "entity": self.entity.__name__,
            "task_api": self.task_api.__name__,
            "task_grpcapi": self.task_grpcapi.__name__,
            "task_api_grpc": self.task_api_grpc.__name__,
            "task": self.task.__name__ if self.task is not None else None,
        }
    ####
####


def load_lattice_proto_modules() -> LatticeProtoModules:
    assert_official_package_versions()
    entity_api = _import_first(
        "EntityManager request/response protobuf module",
        [
            "anduril.entitymanager.v1.entity_manager_api.pub_pb2",
            "anduril.entitymanager.v1.entity_manager_api_dot_pub_pb2",
            "anduril.entitymanager.v1.entity_manager_api_pb2",
            "anduril.entitymanager.v1.entity_manager_grpcapi_dot_pub_pb2",
            "anduril.entitymanager.v1.entity_manager_grpcapi_pb2",
        ],
    )
    entity_grpcapi = _import_first(
        "EntityManager service protobuf module",
        [
            "anduril.entitymanager.v1.entity_manager_api.pub_pb2",
            "anduril.entitymanager.v1.entity_manager_grpcapi_dot_pub_pb2",
            "anduril.entitymanager.v1.entity_manager_grpcapi_pb2",
            "anduril.entitymanager.v1.entity_manager_grpcapi.pub_pb2",
        ],
    )
    entity_api_grpc = _import_first(
        "EntityManager generated gRPC module",
        [
            "anduril.entitymanager.v1.entity_manager_api.pub_pb2_grpc",
            "anduril.entitymanager.v1.entity_manager_grpcapi_dot_pub_pb2_grpc",
            "anduril.entitymanager.v1.entity_manager_grpcapi_pb2_grpc",
            "anduril.entitymanager.v1.entity_manager_grpcapi.pub_pb2_grpc",
        ],
    )
    entity = _import_first(
        "Entity protobuf module",
        [
            "anduril.entitymanager.v1.entity.pub_pb2",
            "anduril.entitymanager.v1.entity_dot_pub_pb2",
            "anduril.entitymanager.v1.entity_pb2",
            "anduril.entitymanager.v1.entity.pub_pb2",
        ],
    )
    task_api = _import_first(
        "TaskManager request/response protobuf module",
        [
            "anduril.taskmanager.v1.task_manager_api.pub_pb2",
            "anduril.taskmanager.v1.task_manager_api_dot_pub_pb2",
            "anduril.taskmanager.v1.task_manager_api_pb2",
            "anduril.taskmanager.v1.task_manager_grpcapi_dot_pub_pb2",
            "anduril.taskmanager.v1.task_manager_grpcapi_pb2",
        ],
    )
    task_grpcapi = _import_first(
        "TaskManager service protobuf module",
        [
            "anduril.taskmanager.v1.task_manager_api.pub_pb2",
            "anduril.taskmanager.v1.task_manager_grpcapi_dot_pub_pb2",
            "anduril.taskmanager.v1.task_manager_grpcapi_pb2",
            "anduril.taskmanager.v1.task_manager_grpcapi.pub_pb2",
        ],
    )
    task_api_grpc = _import_first(
        "TaskManager generated gRPC module",
        [
            "anduril.taskmanager.v1.task_manager_api.pub_pb2_grpc",
            "anduril.taskmanager.v1.task_manager_grpcapi_dot_pub_pb2_grpc",
            "anduril.taskmanager.v1.task_manager_grpcapi_pb2_grpc",
            "anduril.taskmanager.v1.task_manager_grpcapi.pub_pb2_grpc",
        ],
    )
    task = _import_optional(
        [
            "anduril.taskmanager.v1.task.pub_pb2",
            "anduril.taskmanager.v1.task_dot_pub_pb2",
            "anduril.taskmanager.v1.task_pb2",
            "anduril.taskmanager.v1.task.pub_pb2",
        ],
    )
    return LatticeProtoModules(
        entity_api=entity_api,
        entity_grpcapi=entity_grpcapi,
        entity_api_grpc=entity_api_grpc,
        entity=entity,
        task_api=task_api,
        task_grpcapi=task_grpcapi,
        task_api_grpc=task_api_grpc,
        task=task,
    )
####


def installed_official_package_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for package_name in OFFICIAL_BUF_PACKAGES:
        try:
            versions[package_name] = metadata.version(package_name)
        except metadata.PackageNotFoundError:
            versions[package_name] = None
        ####
    ####
    return versions
####


def official_package_version_mismatches() -> dict[str, tuple[str, str | None]]:
    mismatches: dict[str, tuple[str, str | None]] = {}
    installed_versions = installed_official_package_versions()
    for package_name, expected_version in OFFICIAL_BUF_PACKAGES.items():
        installed_version = installed_versions.get(package_name)
        if installed_version != expected_version:
            mismatches[package_name] = (expected_version, installed_version)
        ####
    ####
    return mismatches
####


def assert_official_package_versions() -> None:
    mismatches = official_package_version_mismatches()
    if not mismatches:
        return
    ####
    details = "\n".join(
        f"  - {package_name}: expected {expected}, installed {installed or 'not installed'}"
        for package_name, (expected, installed) in mismatches.items()
    )
    raise MissingLatticeProtoDependency(
        "Installed official Buf-generated Python packages for Lattice do not match the pinned compatibility contract.\n"
        f"Expected packages from {BUF_PYTHON_INDEX_URL}:\n{details}\n"
        "Run `uv sync --extra grpc` or `./scripts/install_grpc_deps.sh`."
    )
####


def _import_optional(paths: list[str]) -> Any | None:
    try:
        return _import_first("optional Task protobuf module", paths)
    except MissingLatticeProtoDependency:
        return None
    ####
####


def _import_first(label: str, paths: list[str]) -> Any:
    failures: list[str] = []
    for path in paths:
        try:
            return import_module(path)
        except ModuleNotFoundError as exc:
            failures.append(f"{path}: {exc}")
        ####
    ####
    joined_failures = "\n  - ".join(failures)
    raise MissingLatticeProtoDependency(
        "Lattice gRPC compatibility requires the official Buf-generated Python packages. "
        "Install with `uv sync --extra grpc`, or use `./scripts/install_grpc_deps.sh`. "
        "Do not use hand-written replacement protos or fallback PyPI lookalikes. "
        f"Missing import: {label}; attempted imports:\n  - {joined_failures}"
    )
####
