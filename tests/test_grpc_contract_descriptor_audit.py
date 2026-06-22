from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from zorn.grpc_api.contract import (
    EXPECTED_ENTITY_MANAGER_SERVICE,
    EXPECTED_TASK_MANAGER_SERVICE,
    GrpcContractMismatch,
    assert_lattice_grpc_contract,
    lattice_grpc_contract_mismatches,
)
from zorn.grpc_api.proto_modules import LatticeProtoModules


def test_descriptor_audit_accepts_matching_public_services() -> None:
    proto_modules = _fake_proto_modules()

    assert lattice_grpc_contract_mismatches(proto_modules) == []
    assert_lattice_grpc_contract(proto_modules)
####


def test_descriptor_audit_rejects_missing_rpc() -> None:
    proto_modules = _fake_proto_modules(drop_entity_method="PublishEntities")

    mismatches = lattice_grpc_contract_mismatches(proto_modules)

    assert any("PublishEntities" in mismatch for mismatch in mismatches)
    with pytest.raises(GrpcContractMismatch):
        assert_lattice_grpc_contract(proto_modules)
    ####
####


def test_descriptor_audit_rejects_wrong_request_type() -> None:
    proto_modules = _fake_proto_modules(input_type_override=("PublishEntity", "example.WrongRequest"))

    mismatches = lattice_grpc_contract_mismatches(proto_modules)

    assert any("PublishEntity input_type" in mismatch for mismatch in mismatches)
####


def _fake_proto_modules(
    drop_entity_method: str | None = None,
    input_type_override: tuple[str, str] | None = None,
) -> LatticeProtoModules:
    return LatticeProtoModules(
        entity_api=_fake_module("entity_api"),
        entity_grpcapi=_fake_descriptor_module(
            EXPECTED_ENTITY_MANAGER_SERVICE,
            drop_method=drop_entity_method,
            input_type_override=input_type_override,
        ),
        entity_api_grpc=_fake_module("entity_api_grpc"),
        entity=_fake_module("entity"),
        task_api=_fake_module("task_api"),
        task_grpcapi=_fake_descriptor_module(EXPECTED_TASK_MANAGER_SERVICE),
        task_api_grpc=_fake_module("task_api_grpc"),
        task=None,
    )
####


def _fake_module(name: str) -> Any:
    return SimpleNamespace(__name__=name)
####


def _fake_descriptor_module(
    expected_service: Any,
    *,
    drop_method: str | None = None,
    input_type_override: tuple[str, str] | None = None,
) -> Any:
    methods = []
    for expected_method in expected_service.methods:
        if expected_method.name == drop_method:
            continue
        ####
        input_type = expected_method.input_type
        if input_type_override is not None and input_type_override[0] == expected_method.name:
            input_type = input_type_override[1]
        ####
        methods.append(
            SimpleNamespace(
                name=expected_method.name,
                input_type=SimpleNamespace(full_name=input_type),
                output_type=SimpleNamespace(full_name=expected_method.output_type),
                client_streaming=expected_method.client_streaming,
                server_streaming=expected_method.server_streaming,
            )
        )
    ####
    service = SimpleNamespace(
        name=expected_service.service_name,
        full_name=f"{expected_service.package}.{expected_service.service_name}",
        methods=methods,
        file=SimpleNamespace(name=f"{expected_service.service_name}.proto", serialized_pb=b"fake"),
    )
    descriptor = SimpleNamespace(services_by_name={expected_service.service_name: service})
    return SimpleNamespace(__name__=f"{expected_service.service_name}_module", DESCRIPTOR=descriptor)
####
