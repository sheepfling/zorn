from __future__ import annotations

from pathlib import Path

import yaml

from zorn.cert.harness import load_contract, load_fixtures, validate_contracts


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


def test_registry_tracks_sdk_spec_schema_and_reference_fixtures() -> None:
    fixtures = {fixture.id: fixture for fixture in load_fixtures(ROOT)}

    assert fixtures["sdk-python-smoke"].category == "official_sdk_conformance"
    assert fixtures["sdk-go-smoke"].category == "official_sdk_conformance"
    assert fixtures["sdk-java-smoke"].category == "official_sdk_conformance"
    assert fixtures["sdk-javascript-smoke"].category == "official_sdk_conformance"
    assert fixtures["sdk-cpp-grpc-smoke"].category == "official_sdk_conformance"
    assert fixtures["sdk-rust-grpc-smoke"].category == "official_sdk_conformance"
    assert fixtures["api-evangelist-openapi-rest"].category == "spec_derived_rest_conformance"
    assert fixtures["buf-schema-registry-descriptor-check"].category == "schema_proto_conformance"
    assert fixtures["sargvision-swarm-replay-reference"].category == "lattice_style_scenario_reference"


def test_adaptation_tiers_are_declared_for_compatibility_reporting() -> None:
    tiers = load_contract(ROOT, "adaptation_tiers")["adaptation_tiers"]
    fixtures = {fixture.id: fixture for fixture in load_fixtures(ROOT)}

    assert set(tiers) == {
        "endpoint_token_only",
        "runtime_env_translation",
        "transport_proxy",
        "runtime_shim",
        "local_overlay",
    }
    assert fixtures["anduril-sample-ais-rest"].adaptation_tier == "endpoint_token_only"
    assert fixtures["anduril-sample-entity-visualizer"].adaptation_tier == "transport_proxy"
    assert fixtures["sdk-python-smoke"].adaptation_tier == "runtime_shim"
    assert fixtures["tyler-alfred-agent"].adaptation_tier == "local_overlay"


def test_assertion_contracts_cover_next_certification_targets() -> None:
    assertions = load_contract(ROOT, "assertions")["assertion_groups"]

    assert "current_passing_corpus" in assertions
    assert "weak_proof_upgrades" in assertions
    assert "negative_and_stress" in assertions
    assert "golden_grpc_wire" in assertions
    assert "scenario_certification" in assertions

    current_fixtures = assertions["current_passing_corpus"]["fixtures"]
    assert "anduril-sample-ais-rest" in current_fixtures
    assert "anduril-sample-thumbnail" in current_fixtures
    assert "ark-mavlink-to-lattice" in current_fixtures

    grpc_fixtures = assertions["golden_grpc_wire"]["fixtures"]
    assert "grpc-wire-entity-publish" in grpc_fixtures
    assert "grpc-wire-task-listen" in grpc_fixtures

    scenarios = assertions["scenario_certification"]["scenarios"]
    assert {"BA-001", "BA-007", "ADS-002", "ADS-003", "ADS-004"}.issubset(scenarios)


def test_golden_grpc_manifest_is_pinned_to_known_capabilities() -> None:
    manifest_path = ROOT / "tests" / "fixtures" / "grpc" / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    known_capabilities = set(load_contract(ROOT, "capabilities")["capabilities"])
    fixtures = {fixture["path"]: fixture for fixture in manifest["fixtures"]}

    assert {
        "entity_publish_request.binpb",
        "entity_get_request.binpb",
        "entity_stream_request.binpb",
        "task_create_request.binpb",
        "task_update_status_request.binpb",
        "task_cancel_request.binpb",
        "task_listen_as_agent_request.binpb",
    } == set(fixtures)
    assert {fixture["capability"] for fixture in fixtures.values()} <= known_capabilities
