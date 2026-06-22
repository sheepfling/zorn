from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "docs" / "reference"
MANIFESTS_DIR = ROOT / "docs" / "manifests"
FORBIDDEN_RUNTIME_SURFACE_TEXT = (
    "/healthz",
    "grpc.health",
    "ServerReflection",
    "/api/zorn",
    "/api/v1/backend",
    "/api/v1/verification",
    "events/snapshot",
    "local API",
    "local APIs",
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    ####
    assert isinstance(data, dict)
    return data
####


def test_next_milestone_plan_is_well_linked() -> None:
    plan = load_json(REFERENCE_DIR / "zorn-next-milestone-plan.json")
    source_ids = {source["id"] for source in plan["sources"]}
    lane_ids = {lane["id"] for lane in plan["lanes"]}
    milestone_ids = {milestone["id"] for milestone in plan["milestones"]}

    assert len(source_ids) >= 10
    assert len(lane_ids) >= 10
    assert len(milestone_ids) == 10
    assert {f"Z{i}" for i in range(3, 13)} == milestone_ids

    for lane in plan["lanes"]:
        assert lane["mission"]
        assert lane["outputs"]
        for source_id in lane["sources"]:
            assert source_id in source_ids, (lane["id"], source_id)
        ####
        for milestone_id in lane["milestones"]:
            assert milestone_id.startswith("Z")
        ####
    ####

    for milestone in plan["milestones"]:
        assert milestone["lane"] in lane_ids
        assert milestone["objective"]
        assert milestone["why_now"]
        assert len(milestone["epics"]) >= 4
        assert milestone["deliverables"]
        assert milestone["acceptance_tests"]
        assert milestone["showcase_signal"]
        assert milestone["non_goals"]
        for dependency_id in milestone["depends_on"]:
            assert dependency_id in milestone_ids or dependency_id in {"Z0", "Z1", "Z2"}
        ####
    ####
####


def test_backlog_and_acceptance_matrix_cover_every_milestone() -> None:
    plan = load_json(REFERENCE_DIR / "zorn-next-milestone-plan.json")
    backlog_manifest = load_json(MANIFESTS_DIR / "zorn-implementation-backlog.json")
    acceptance_manifest = load_json(MANIFESTS_DIR / "zorn-acceptance-test-matrix.json")

    milestone_ids = {milestone["id"] for milestone in plan["milestones"]}
    backlog = backlog_manifest["backlog"]
    acceptance_tests = acceptance_manifest["acceptance_tests"]

    assert len(backlog) >= 100
    assert len(acceptance_tests) >= 35
    assert {story["milestone"] for story in backlog} == milestone_ids
    assert {test["milestone"] for test in acceptance_tests} == milestone_ids
    assert {story["id"] for story in backlog} == {story["id"] for story in plan["backlog"]}
    assert {test["id"] for test in acceptance_tests} == {test["id"] for test in plan["acceptance_tests"]}
####


def test_dependency_graph_and_risks_are_actionable() -> None:
    plan = load_json(REFERENCE_DIR / "zorn-next-milestone-plan.json")
    graph = load_json(MANIFESTS_DIR / "zorn-capability-dependency-graph.json")
    risk_register = load_json(REFERENCE_DIR / "zorn-risk-register.json")

    node_ids = {node["id"] for node in graph["nodes"]}
    assert node_ids == {milestone["id"] for milestone in plan["milestones"]}
    assert graph["edges"]

    for edge in graph["edges"]:
        assert edge["to"] in node_ids
        assert edge["from"] in node_ids or edge["from"] in {"Z0", "Z1", "Z2"}
        assert edge["reason"]
    ####

    risks = risk_register["risks"]
    assert len(risks) >= 7
    for risk in risks:
        assert risk["risk"]
        assert risk["impact"]
        assert risk["mitigation"]
        assert risk["owners"]
    ####
####


def test_next_milestone_plan_preserves_strict_lattice_boundary() -> None:
    paths = [
        REFERENCE_DIR / "zorn-next-milestone-plan.json",
        REFERENCE_DIR / "zorn-next-milestone-plan-report.md",
        REFERENCE_DIR / "zorn-work-lanes.json",
        REFERENCE_DIR / "zorn-risk-register.json",
        MANIFESTS_DIR / "zorn-implementation-backlog.json",
        MANIFESTS_DIR / "zorn-acceptance-test-matrix.json",
        MANIFESTS_DIR / "zorn-capability-dependency-graph.json",
        ROOT / "docs" / "plans" / "zorn-next-milestones-execution-plan.md",
        ROOT / "docs" / "plans" / "zorn-work-lanes.md",
        ROOT / "docs" / "plans" / "zorn-safety-and-boundaries.md",
        ROOT / "docs" / "plans" / "zorn-implementation-backlog.md",
        ROOT / "docs" / "plans" / "zorn-acceptance-test-matrix.md",
        ROOT / "docs" / "plans" / "zorn-showcase-runbook-index.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    for forbidden in FORBIDDEN_RUNTIME_SURFACE_TEXT:
        assert forbidden not in combined
    ####
    assert "Never create local replacement Lattice protos" in combined
    assert "public-compatible Entities, Tasks, Objects" in combined
    assert "UI-internal read models" in combined
####
