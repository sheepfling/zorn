from __future__ import annotations

import json
from pathlib import Path


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
    "healthz/details",
    "events/snapshot",
    "local namespaced API",
)


def test_showcase_milestones_define_z0_through_z12_with_strict_boundary() -> None:
    data = json.loads((ROOT / "docs" / "reference" / "zorn-showcase-milestones.json").read_text())

    assert data["schema_version"] == "zorn.showcase.milestones.v1"
    assert set(data["boundary"]["compatibility_kernel"]) == ALLOWED_SURFACES
    assert "third-party integrations must only use validated Lattice-shaped surfaces" in data["boundary"]["rule"]
    assert [milestone["id"] for milestone in data["milestones"]] == [f"Z{index}" for index in range(13)]
    assert data["milestones"][0]["priority"] == "P0"
    assert data["milestones"][12]["name"] == "Rich Showcase Bundle and Evaluation Mode"


def test_showcase_scenarios_cover_major_lanes_and_use_only_lattice_surfaces() -> None:
    data = json.loads((ROOT / "docs" / "manifests" / "zorn-showcase-scenarios.json").read_text())

    assert data["schema_version"] == "zorn.showcase.scenarios.v1"
    assert set(data["boundary"]["allowed_surfaces"]) == ALLOWED_SURFACES
    assert len(data["scenarios"]) == 11

    by_id = {scenario["id"]: scenario for scenario in data["scenarios"]}
    assert {"Z4", "Z5", "Z8", "Z9", "Z10", "Z11", "Z12"} <= {
        milestone
        for scenario in data["scenarios"]
        for milestone in scenario["milestones"]
    }
    assert by_id["SCN-011"]["milestones"] == ["Z12"]
    assert by_id["SCN-004"]["surfaces"] == ["entities", "tasks", "objects", "rest_streams"]

    for scenario in data["scenarios"]:
        assert set(scenario["surfaces"]) <= ALLOWED_SURFACES


def test_showcase_example_files_match_manifest_entries() -> None:
    manifest = json.loads((ROOT / "docs" / "manifests" / "zorn-showcase-scenarios.json").read_text())

    for scenario in manifest["scenarios"]:
        example = scenario.get("example")
        if not example:
            continue
        path = ROOT / example
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["schema_version"] == "zorn.showcase.scenario.v1"
        assert data["id"] == scenario["id"]
        assert set(data["expected_surfaces"]) <= ALLOWED_SURFACES


def test_showcase_docs_do_not_reintroduce_zorn_specific_public_api() -> None:
    paths = [
        ROOT / "docs" / "reference" / "zorn-showcase-report.md",
        ROOT / "docs" / "design" / "zorn-full-feature-showcase-roadmap.md",
        ROOT / "docs" / "design" / "zorn-rich-environment-architecture.md",
        ROOT / "docs" / "design" / "zorn-showcase-scenario-catalog.md",
    ]
    combined = "\n".join(path.read_text() for path in paths)

    for forbidden in FORBIDDEN_TEXT:
        assert forbidden not in combined
