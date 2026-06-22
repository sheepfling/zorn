from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_SURFACES = {
    "entities",
    "tasks",
    "objects",
    "auth",
    "rest_streams",
    "grpc_entities",
    "grpc_tasks",
}
FORBIDDEN_TEXT = (
    "/api/zorn",
    "/api/v1/backend",
    "/api/v1/verification",
    "events/snapshot",
    "healthz/details",
    "read-only debug endpoint",
)


def test_ecosystem_registry_declares_required_lanes_and_boundary() -> None:
    registry = json.loads((ROOT / "docs" / "reference" / "lattice-ecosystem-registry.json").read_text())

    assert registry["schema_version"] == "zorn.lattice_ecosystem.registry.v1"
    assert set(registry["boundary"]["allowed_surfaces"]) == ALLOWED_SURFACES
    assert "zorn_specific_public_routes" in registry["boundary"]["forbidden"]
    assert {lane["module"] for lane in registry["lanes"]} == {
        "zorn-core",
        "zorn-sdk",
        "zorn-c2",
        "zorn-autonomy",
        "zorn-mesh",
        "zorn-partner",
        "zorn-adapters",
        "zorn-domain",
    }
    for lane in registry["lanes"]:
        assert set(lane["lattice_surfaces"]) <= ALLOWED_SURFACES
        assert lane["local_artifacts"]
    ####


def test_ecosystem_requirements_pin_boundary_as_p0() -> None:
    requirements = json.loads((ROOT / "docs" / "reference" / "lattice-ecosystem-requirements.json").read_text())
    by_id = {item["id"]: item for item in requirements["requirements"]}

    assert by_id["ECO-BOUNDARY-001"]["priority"] == "P0"
    assert "must not add third-party-facing API" in by_id["ECO-BOUNDARY-001"]["text"]
    assert "ECO-ADAPTER-001" in by_id
    assert "ECO-C2-001" in by_id


def test_module_manifest_uses_only_lattice_surfaces_for_integration() -> None:
    manifest = yaml.safe_load((ROOT / "docs" / "manifests" / "zorn-modules.yaml").read_text())

    assert manifest["schema_version"] == "zorn.modules.v1"
    assert set(manifest["boundary"]["allowed_lattice_surfaces"]) == ALLOWED_SURFACES
    for module in manifest["modules"].values():
        assert set(module["consumes_lattice_surfaces"]) <= ALLOWED_SURFACES
        assert set(module["provides_lattice_surfaces"]) <= ALLOWED_SURFACES
        assert "local_artifacts" in module
    ####


def test_ecosystem_docs_do_not_reintroduce_zorn_specific_public_api() -> None:
    paths = [
        ROOT / "docs" / "design" / "zorn-product-boundaries.md",
        ROOT / "docs" / "design" / "zorn-cop-debug-ui.md",
        ROOT / "docs" / "design" / "alpha-readiness-roadmap.md",
        ROOT / "docs" / "design" / "zorn-lattice-ecosystem-architecture.md",
        ROOT / "docs" / "design" / "zorn-expansion-milestones.md",
        ROOT / "docs" / "reference" / "lattice-ecosystem-report.md",
    ]
    combined = "\n".join(path.read_text() for path in paths)

    for forbidden in FORBIDDEN_TEXT:
        assert forbidden not in combined
    ####
