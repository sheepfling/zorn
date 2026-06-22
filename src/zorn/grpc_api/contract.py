from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from google.protobuf.descriptor import FileDescriptor, MethodDescriptor, ServiceDescriptor

from .proto_modules import LatticeProtoModules, installed_official_package_versions


@dataclass(frozen=True, slots=True)
class ExpectedGrpcMethod:
    name: str
    input_type: str
    output_type: str
    client_streaming: bool
    server_streaming: bool
####


@dataclass(frozen=True, slots=True)
class ExpectedGrpcService:
    package: str
    service_name: str
    methods: tuple[ExpectedGrpcMethod, ...]
####


@dataclass(frozen=True, slots=True)
class GrpcMethodReport:
    name: str
    input_type: str
    output_type: str
    client_streaming: bool
    server_streaming: bool
####


@dataclass(frozen=True, slots=True)
class GrpcServiceReport:
    full_name: str
    file_name: str
    file_sha256: str
    methods: list[GrpcMethodReport]
####


def _method(
    package: str,
    name: str,
    *,
    client_streaming: bool = False,
    server_streaming: bool = False,
) -> ExpectedGrpcMethod:
    return ExpectedGrpcMethod(
        name=name,
        input_type=f"{package}.{name}Request",
        output_type=f"{package}.{name}Response",
        client_streaming=client_streaming,
        server_streaming=server_streaming,
    )
####


ENTITY_MANAGER_PACKAGE = "anduril.entitymanager.v1"
TASK_MANAGER_PACKAGE = "anduril.taskmanager.v1"

EXPECTED_ENTITY_MANAGER_SERVICE = ExpectedGrpcService(
    package=ENTITY_MANAGER_PACKAGE,
    service_name="EntityManagerAPI",
    methods=(
        _method(ENTITY_MANAGER_PACKAGE, "PublishEntity"),
        _method(ENTITY_MANAGER_PACKAGE, "PublishEntities", client_streaming=True),
        _method(ENTITY_MANAGER_PACKAGE, "GetEntity"),
        _method(ENTITY_MANAGER_PACKAGE, "OverrideEntity"),
        _method(ENTITY_MANAGER_PACKAGE, "RemoveEntityOverride"),
        _method(ENTITY_MANAGER_PACKAGE, "StreamEntityComponents", server_streaming=True),
    ),
)

EXPECTED_TASK_MANAGER_SERVICE = ExpectedGrpcService(
    package=TASK_MANAGER_PACKAGE,
    service_name="TaskManagerAPI",
    methods=(
        _method(TASK_MANAGER_PACKAGE, "CreateTask"),
        _method(TASK_MANAGER_PACKAGE, "GetTask"),
        _method(TASK_MANAGER_PACKAGE, "QueryTasks"),
        _method(TASK_MANAGER_PACKAGE, "UpdateStatus"),
        _method(TASK_MANAGER_PACKAGE, "CancelTask"),
        _method(TASK_MANAGER_PACKAGE, "ListenAsAgent", server_streaming=True),
        _method(TASK_MANAGER_PACKAGE, "ListenForManualControlFrames", server_streaming=True),
        _method(TASK_MANAGER_PACKAGE, "StreamTasks", server_streaming=True),
    ),
)

EXPECTED_SERVICES: tuple[ExpectedGrpcService, ...] = (
    EXPECTED_ENTITY_MANAGER_SERVICE,
    EXPECTED_TASK_MANAGER_SERVICE,
)


class GrpcContractMismatch(RuntimeError):
    pass
####


def assert_lattice_grpc_contract(proto_modules: LatticeProtoModules) -> None:
    mismatches = lattice_grpc_contract_mismatches(proto_modules)
    if not mismatches:
        return
    ####
    raise GrpcContractMismatch("Lattice gRPC proto contract mismatch:\n" + "\n".join(f"  - {item}" for item in mismatches))
####


def lattice_grpc_contract_mismatches(proto_modules: LatticeProtoModules) -> list[str]:
    service_pairs = (
        (EXPECTED_ENTITY_MANAGER_SERVICE, proto_modules.entity_grpcapi.DESCRIPTOR),
        (EXPECTED_TASK_MANAGER_SERVICE, proto_modules.task_grpcapi.DESCRIPTOR),
    )
    mismatches: list[str] = []
    for expected_service, file_descriptor in service_pairs:
        service = file_descriptor.services_by_name.get(expected_service.service_name)
        if service is None:
            mismatches.append(f"missing service {expected_service.package}.{expected_service.service_name}")
            continue
        ####
        if service.full_name != f"{expected_service.package}.{expected_service.service_name}":
            mismatches.append(
                f"service {expected_service.service_name} full name was {service.full_name}, "
                f"expected {expected_service.package}.{expected_service.service_name}"
            )
        ####
        actual_methods = {method.name: method for method in service.methods}
        expected_method_names = {method.name for method in expected_service.methods}
        extra_methods = sorted(set(actual_methods) - expected_method_names)
        missing_methods = sorted(expected_method_names - set(actual_methods))
        for name in missing_methods:
            mismatches.append(f"{service.full_name} missing method {name}")
        ####
        for name in extra_methods:
            mismatches.append(f"{service.full_name} has unexpected method {name}")
        ####
        for expected_method in expected_service.methods:
            actual_method = actual_methods.get(expected_method.name)
            if actual_method is None:
                continue
            ####
            if actual_method.input_type.full_name != expected_method.input_type:
                mismatches.append(
                    f"{service.full_name}.{expected_method.name} input_type was "
                    f"{actual_method.input_type.full_name}, expected {expected_method.input_type}"
                )
            ####
            if actual_method.output_type.full_name != expected_method.output_type:
                mismatches.append(
                    f"{service.full_name}.{expected_method.name} output_type was "
                    f"{actual_method.output_type.full_name}, expected {expected_method.output_type}"
                )
            ####
            if actual_method.client_streaming != expected_method.client_streaming:
                mismatches.append(
                    f"{service.full_name}.{expected_method.name} client_streaming was "
                    f"{actual_method.client_streaming}, expected {expected_method.client_streaming}"
                )
            ####
            if actual_method.server_streaming != expected_method.server_streaming:
                mismatches.append(
                    f"{service.full_name}.{expected_method.name} server_streaming was "
                    f"{actual_method.server_streaming}, expected {expected_method.server_streaming}"
                )
            ####
        ####
    ####
    return mismatches
####


def build_lattice_grpc_contract_report(proto_modules: LatticeProtoModules) -> dict[str, Any]:
    service_descriptors = [
        proto_modules.entity_grpcapi.DESCRIPTOR.services_by_name[EXPECTED_ENTITY_MANAGER_SERVICE.service_name],
        proto_modules.task_grpcapi.DESCRIPTOR.services_by_name[EXPECTED_TASK_MANAGER_SERVICE.service_name],
    ]
    return {
        "officialPackageVersions": installed_official_package_versions(),
        "moduleNames": proto_modules.module_names(),
        "services": [asdict(service_report_from_descriptor(service_descriptor)) for service_descriptor in service_descriptors],
        "mismatches": lattice_grpc_contract_mismatches(proto_modules),
    }
####


def service_report_from_descriptor(service: ServiceDescriptor) -> GrpcServiceReport:
    return GrpcServiceReport(
        full_name=service.full_name,
        file_name=service.file.name,
        file_sha256=file_descriptor_sha256(service.file),
        methods=[method_report_from_descriptor(method) for method in service.methods],
    )
####


def method_report_from_descriptor(method: MethodDescriptor) -> GrpcMethodReport:
    return GrpcMethodReport(
        name=method.name,
        input_type=method.input_type.full_name,
        output_type=method.output_type.full_name,
        client_streaming=method.client_streaming,
        server_streaming=method.server_streaming,
    )
####


def file_descriptor_sha256(file_descriptor: FileDescriptor) -> str:
    return hashlib.sha256(file_descriptor.serialized_pb).hexdigest()
####
