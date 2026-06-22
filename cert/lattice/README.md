# Zorn Lattice Certification

This directory turns the research registry into an executable certification corpus.

- `fixtures.yaml` pins external repositories by immutable commit SHA.
- `adaptation-tiers.yaml` defines how much adaptation each fixture required.
- `assertions.yaml` records the next stronger proof obligations for passing, weak, negative/stress, gRPC, and scenario tracks.
- `capabilities.yaml` defines pass conditions before fixture execution.
- `domains.yaml` defines the big Zorn systems as capability contracts.
- `coverage.yaml` is the master truth table across official samples, third-party fixtures, and synthetic scenarios.
- `levels.yaml` defines certification levels from SDK smoke through Air Dominance & Strike surrogate behavior.
- `artifacts.yaml` defines the self-checking run outputs expected from scenario certification.
- `runners/` contains language-specific and fixture-specific runners.
- `reports/` stores JSON certification artifacts.

The corpus is cloned into ignored repo-local `cert/lattice/.fixtures` by default.
Upstream sample code is not vendored into this repository.

## Registry Tracks

The registry separates compatibility evidence from broader scenario references:

- `official`: public sample apps that should think Zorn is Lattice.
- `third_party`: public integrations that exercise messier real-world client behavior.
- `official_sdk_conformance`: direct SDK smoke fixtures for Python, Go, Java, JavaScript, C++, and Rust.
- `spec_derived_rest_conformance`: OpenAPI/Postman-derived REST checks from public API reference artifacts.
- `schema_proto_conformance`: Buf/protobuf descriptor and raw generated-client compatibility checks.
- `lattice_style_scenario_references`: Lattice-inspired UI/simulation projects used to shape synthetic BA/ADS scenarios, not to prove Anduril SDK compatibility.
- `scenarios`: deterministic Zorn-native scenario certifications.

Only the first two tracks are currently fully executable. The SDK/spec/schema
tracks are pinned now so runners can be added deliberately without counting
them as independent app compatibility evidence.

## Adaptation Tiers

Every fixture reports one adaptation tier:

- `endpoint_token_only`: only endpoint, token, sandbox, or OAuth credential changes.
- `runtime_env_translation`: config/env names or local runtime setup are translated by the runner.
- `transport_proxy`: a local proxy or bridge adapts transport without changing fixture code.
- `runtime_shim`: generated smoke code, SDK wrapper setup, or injected runtime behavior is required.
- `local_overlay`: fixture depends on local mocked/overlay behavior beyond endpoint/config changes.

The certification bar is highest when public apps pass at `endpoint_token_only`.
Higher tiers are still useful, but they are reported separately so compatibility
evidence is not overstated.

## Assertion Tracks

The current green corpus is now backed by stronger planned assertions:

- AIS fixtures must prove identity stability, provenance preservation, and update ordering.
- Objects and thumbnail fixtures must prove byte fidelity and persistent entity media links.
- Tasking fixtures must prove lifecycle ordering and no duplicate agent delivery.
- Maven, DragonSync, ADS-B, and MAVLink fixtures must prove richer component fidelity.
- Entity Visualizer must move from transport proof to browser-visible map/entity proof.
- Negative/stress certification covers bad auth, stale updates, bad task transitions, reconnect/heartbeat, and concurrent publish-stream behavior.
- Golden gRPC wire certification is pinned in `tests/fixtures/grpc/manifest.yaml`.
- Scenario certification starts with `BA-001`, `BA-007`, `ADS-002`, `ADS-003`, and `ADS-004`.
UI certification is tracked separately under `cert/ui` so UI requirements do not
become part of the Lattice-compatible data-plane contract.

## Commands

```bash
zorn-cert list
zorn-cert clone --all
zorn-cert clone anduril-sample-ais-rest
zorn-cert inspect anduril-sample-ais-rest
zorn-cert install anduril-sample-ais-rest
zorn-cert run anduril-sample-ais-rest --target http://localhost:8080
zorn-cert report
zorn-cert domains
zorn-cert coverage
zorn-cert levels
zorn-cert validate-contracts
```

`inspect` reports what Zorn currently knows about a fixture workspace: language,
manifest-pinned or inferred install commands, one or more native run commands,
config files, and environment hints.
`install` runs the resolved dependency setup inside the ignored clone workspace
without modifying upstream source.

The first executable milestone is AIS REST entity ingestion: publish a normalized
AIS-style entity to Zorn, verify canonical readback, and verify the REST stream
surface emits an entity event.

## Architecture Target

Zorn is not only a mock endpoint. The certification target is a simulated
battlespace kernel:

```text
SDK/API facade
  -> command/event log
  -> entity/task/object stores
  -> scenario engine
  -> fusion/rules/effects plugins
  -> streaming fanout
  -> UI/replay/export
```

An unmodified public Lattice sample should think Zorn is Lattice, and synthetic
Battlespace Awareness or Air Dominance & Strike scenarios should produce
believable entities, tasks, streams, media, and outcomes.
