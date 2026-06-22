from __future__ import annotations

from zorn.grpc_api.contract import EXPECTED_SERVICES


def test_expected_grpc_contract_covers_public_services() -> None:
    services = {service.service_name: service for service in EXPECTED_SERVICES}

    assert set(services) == {"EntityManagerAPI", "TaskManagerAPI"}
    assert {method.name for method in services["EntityManagerAPI"].methods} == {
        "PublishEntity",
        "PublishEntities",
        "GetEntity",
        "OverrideEntity",
        "RemoveEntityOverride",
        "StreamEntityComponents",
    }
    assert {method.name for method in services["TaskManagerAPI"].methods} == {
        "CreateTask",
        "GetTask",
        "QueryTasks",
        "UpdateStatus",
        "CancelTask",
        "ListenAsAgent",
        "ListenForManualControlFrames",
        "StreamTasks",
    }
####


def test_expected_streaming_cardinality() -> None:
    services = {service.service_name: service for service in EXPECTED_SERVICES}
    entity_methods = {method.name: method for method in services["EntityManagerAPI"].methods}
    task_methods = {method.name: method for method in services["TaskManagerAPI"].methods}

    assert entity_methods["PublishEntities"].client_streaming is True
    assert entity_methods["PublishEntities"].server_streaming is False
    assert entity_methods["StreamEntityComponents"].client_streaming is False
    assert entity_methods["StreamEntityComponents"].server_streaming is True
    assert task_methods["ListenAsAgent"].server_streaming is True
    assert task_methods["ListenForManualControlFrames"].server_streaming is True
    assert task_methods["StreamTasks"].server_streaming is True
####
