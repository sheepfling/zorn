from __future__ import annotations

from pathlib import Path

from zorn.cert.harness import load_contract, validate_contracts


ROOT = Path(__file__).resolve().parents[1]


def test_cert_contracts_reference_defined_capabilities() -> None:
    assert validate_contracts(ROOT) == []


def test_cert_contracts_include_required_domains_and_levels() -> None:
    domains = load_contract(ROOT, "domains")["domains"]
    levels = load_contract(ROOT, "levels")["levels"]

    assert "entity_track_model" in domains
    assert "tasks_missions" in domains
    assert "effects_intercepts" in domains
    assert "replay_simulation" in domains
    assert {level["level"] for level in levels} == set(range(7))


def test_coverage_matrix_tracks_hero_suites() -> None:
    coverage = load_contract(ROOT, "coverage")["coverage"]
    scenarios = {row["synthetic_scenario"] for row in coverage}

    assert "BA-001" in scenarios
    assert "BA-007" in scenarios
    assert "ADS-006/ADS-007" in scenarios
