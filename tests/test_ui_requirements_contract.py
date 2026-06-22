from __future__ import annotations

from pathlib import Path

from zorn.cert.harness import load_contract


ROOT = Path(__file__).resolve().parents[1]


def test_ui_reference_registry_files_are_committed() -> None:
    reference_dir = ROOT / "docs" / "reference" / "ui"

    assert (reference_dir / "README.md").is_file()
    assert (reference_dir / "zorn_lattice_ui_reference_registry.md").is_file()
    assert (reference_dir / "zorn_lattice_ui_reference_registry.json").is_file()
    assert (reference_dir / "zorn_lattice_ui_resource_registry.md").is_file()


def test_zorn_ui_projection_proto_is_local_contract_not_lattice_vendor_copy() -> None:
    proto_path = ROOT / "proto" / "zorn" / "ui" / "v1" / "ui.proto"
    proto = proto_path.read_text()

    assert 'package zorn.ui.v1;' in proto
    assert "should not be confused with" in proto
    assert "message CopViewState" in proto
    assert "message EntitySummary" in proto
    assert "message EntityDetail" in proto
    assert "message TaskSummary" in proto
    assert "message TaskDetail" in proto
    assert "message MapOverlay" in proto
    assert "message OperatorActionLog" in proto


def test_ui_requirements_contract_tracks_p0_p1_p2_and_proof_paths() -> None:
    contract = load_contract(ROOT, "ui_requirements")["ui_requirements"]
    priorities = contract["priorities"]

    assert set(priorities) == {"P0", "P1", "P2"}

    p0_ids = {requirement["id"] for requirement in priorities["P0"]["requirements"]}
    assert {
        "REQ-COP-001",
        "REQ-ENT-DETAIL-001",
        "REQ-MAP-CURSOR-001",
        "REQ-STATUSBAR-001",
        "REQ-TASK-CATALOG-001",
        "REQ-TASK-DETAILS-001",
        "REQ-THREAT-001",
    }.issubset(p0_ids)

    proof_paths = contract["proof_paths"]
    assert "anduril-sample-ais-rest" in proof_paths["fixture_driven"]
    assert "anduril-sample-entity-visualizer" in proof_paths["fixture_driven"]
    assert {"BA-001", "BA-007", "ADS-002", "ADS-003", "ADS-004"}.issubset(
        proof_paths["scenario_driven"]
    )
    assert proof_paths["browser_proof"]["required"] is True


def test_ui_plan_points_to_lattice_boundary_and_visual_certification() -> None:
    plan = (ROOT / "docs" / "design" / "zorn-cop-debug-ui.md").read_text()

    assert "without expanding the\nLattice-compatible API" in plan
    assert "UI-2: `/developer-console`" in plan
    assert "UI-3: `/c2` operator COP" in plan
    assert "UI-4: visual certification" in plan
    assert "Playwright" in plan
