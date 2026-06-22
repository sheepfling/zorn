from __future__ import annotations

from zorn.grpc_api.contract import EXPECTED_SERVICES


def test_expected_lattice_grpc_services_are_tracked() -> None:
    services = {f"{service.package}.{service.service_name}": service for service in EXPECTED_SERVICES}

    assert set(services) == {
        "anduril.entitymanager.v1.EntityManagerAPI",
        "anduril.taskmanager.v1.TaskManagerAPI",
    }
    entity_methods = {method.name: method for method in services["anduril.entitymanager.v1.EntityManagerAPI"].methods}
    task_methods = {method.name: method for method in services["anduril.taskmanager.v1.TaskManagerAPI"].methods}
    assert entity_methods["PublishEntities"].client_streaming is True
    assert entity_methods["StreamEntityComponents"].server_streaming is True
    assert task_methods["ListenAsAgent"].server_streaming is True
    assert task_methods["StreamTasks"].server_streaming is True
####
