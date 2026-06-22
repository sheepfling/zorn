# Faithful Lattice Surrogate Plan

Zorn has crossed the first compatibility threshold: the current pinned public
sample and third-party fixture corpus runs green under `zorn-cert`.

That is necessary, but it is not the same thing as being a faithful Lattice
surrogate.

The next planning rule is:

```text
Do not treat "sample passed" as the end state.
Treat each passing fixture as evidence, then harden the gap between
"evidence with shims" and "behaviorally faithful surrogate".
```

## Current state

What is already proven:

- official sample corpus runs end to end;
- major REST surfaces for entities, tasks, and objects work;
- gRPC descriptors, reflection, health, and public Python generated-client smoke work;
- several third-party integrations publish or consume data against Zorn.

What is not yet proven strongly enough:

- every passing sample can run with only endpoint/token changes and no runtime shims;
- stream/event semantics are faithful under longer-running or concurrent flows;
- scenario-level behavior is deterministic and certifiable;
- fusion, alerts, replay, and effects behavior exist as executable contracts;
- UI consumers are visually validated, not only transport-probed.

## New registry tracks

The current 12 app/integration fixtures are probably close to the useful public
ceiling for real Lattice-compatible apps. The next coverage jump should come
from conformance tracks:

1. `official_sdk_conformance`
   Direct SDK smoke fixtures for Python, Go, Java, JavaScript, C++, and Rust.
   These isolate SDK behavior from app-specific assumptions and should exercise
   auth, entities, streams, tasks, and objects through each public SDK surface.

2. `spec_derived_rest_conformance`
   OpenAPI/Postman-derived checks from public API reference artifacts. These
   should test endpoint coverage, pagination, long-polling, task streams, manual
   control frames, object deletion/list-deleted behavior, and OAuth flows.

3. `schema_proto_conformance`
   Buf/protobuf descriptor and raw generated-client compatibility checks. This
   track should distinguish official SDK compatibility from raw generated-client
   issues such as the current public Go `go_package` metadata limitation.

4. `lattice_style_scenario_references`
   Lattice-inspired UI/simulation projects used as scenario design references,
   not as Anduril SDK compatibility evidence.

## Planning principle

The plan should drive Zorn toward four stricter certification tiers:

1. Fixture executes
2. Fixture executes without source patching
3. Fixture executes without runtime shims
4. Fixture executes and produces faithful state, event, and UI outcomes

Today, most fixtures are at tier 2. Some are partly at tier 3. Very few are at
tier 4.

## Phase F1: Remove compatibility crutches

Goal: reduce the gap between "passes under harness" and "acts like Lattice".

Priority work:

1. Classify every fixture runner by adaptation type:
   - endpoint/token only
   - runtime env translation
   - transport proxy
   - Python `sitecustomize` or language shim
   - local service overlay

2. Emit this classification in every report.

3. For each official fixture, define a target tier:
   - AIS REST: tier 3
   - AIS gRPC: tier 3
   - Objects: tier 3
   - Thumbnail: tier 3
   - Entity Visualizer: tier 3
   - Auto Recon: tier 3

4. Burn down shims in this order:
   - SSE entity stream payload compatibility
   - OAuth/base-url split assumptions
   - gRPC/gRPC-web transport topology
   - old SDK snake_case/camelCase tolerance
   - sync/async client mismatches

Acceptance criteria:

- every official fixture report states its adaptation tier;
- no official fixture depends on source edits;
- official fixtures move toward endpoint/token/config-only execution;
- shim count trends downward across releases.

## Phase F2: Deepen assertions per fixture

Goal: stop certifying only "the app ran" and certify "the app observed the
right behavior".

Required upgrades:

1. AIS REST / AIS gRPC
   - assert stable entity identity across updates;
   - assert provenance and ontology survive multiple publishes;
   - assert stream emits update ordering, not just final state.

2. Objects / Thumbnail
   - assert downloaded bytes match uploaded bytes;
   - assert metadata survives list/get/head;
   - assert entity media linkage survives a follow-up entity read and stream event.

3. Entity Visualizer
   - add browser-visible assertion, not only grpc-web transport probe;
   - confirm at least one rendered entity marker/list row appears from live data.

4. Auto Recon / DeepProve / ALFRED
   - assert task lifecycle ordering:
     `CREATED -> EXECUTING -> terminal`;
   - assert correct agent selection and no duplicate execute delivery;
   - assert override causes downstream re-evaluation where expected.

5. Maven / DragonSync / ADS-B / MAVLink
   - assert richer component fidelity:
     relationships, classification, health, velocity, attitude, transponder codes.

Acceptance criteria:

- each fixture report contains explicit state assertions, event assertions, and
  when relevant UI assertions;
- reports explain exactly what was proven, not just pass/fail totals.

## Phase F3: Add negative and stress certification

Goal: make Zorn fail like a real system when inputs are wrong, and remain stable
when clients are messy.

Add negative-path checks for:

- invalid bearer token;
- missing auth metadata;
- malformed object path;
- stale entity update rejection;
- invalid task status transition;
- unsupported selector/filter shapes;
- bad `Any` payloads;
- stream reconnect after disconnect.

Add stress-path checks for:

- repeated long-poll `listen_as_agent`;
- concurrent publish + stream consumers;
- duplicate entity publishes from multiple sources;
- preexisting-only stream exhaustion;
- heartbeat disabled vs heartbeat enabled.

Acceptance criteria:

- every major surface has at least one negative-path cert;
- stress runs emit compatibility reports, not raw stack traces.

## Phase F4: Wire-level and schema-fidelity hardening

Goal: move from API-shape compatibility to message fidelity.

Required work:

1. Expand golden protobuf fixtures per RPC:
   - publish entity
   - get entity
   - stream entity request
   - create task
   - update status
   - cancel task
   - listen as agent

2. For each RPC, verify:
   - official generated request serializes;
   - Zorn accepts it unchanged;
   - response round-trips via official generated client;
   - unknown fields are preserved where expected;
   - `google.protobuf.Any` survives;
   - enums/timestamps/durations remain valid.

3. Tighten descriptor/startup audit to fail loudly if public services drift.

Acceptance criteria:

- wire fixtures are part of CI;
- schema-preserving behavior is demonstrated, not assumed.

## Phase F5: Scenario-level certification

Goal: certify Zorn as a battlespace kernel, not only a sample-app target.

First required scenarios:

### Battlespace Awareness

- `BA-001`: AIS vessel appears, moves, disappears
- `BA-005`: operator marks track suspicious/hostile
- `BA-006`: thumbnail/media attaches to entity
- `BA-007`: UI consumer receives live stream update
- `BA-008`: stale track expires

### Air Dominance & Strike

- `ADS-002`: operator creates investigate task
- `ADS-003`: agent accepts task
- `ADS-004`: asset reports en route / executing / complete
- `ADS-010`: human override cancels or retasks mission

Each scenario should emit:

- `run.json`
- `events.jsonl`
- `entities.final.json`
- `tasks.final.json`
- `objects.final.json`
- `coverage.json`

Acceptance criteria:

- scenarios are deterministic in CI;
- scenario reports fill the current level-5 and level-6 coverage gaps.

## Phase F6: Faithfulness scorecard

Goal: make progress visible and hard to hand-wave.

Add a scorecard per fixture and release:

- adaptation tier
- surfaces exercised
- positive-path assertions count
- negative-path assertions count
- UI assertions present/absent
- scenario coverage linked/unlinked
- known deviations from public Lattice behavior

This should produce a simple summary:

```text
official fixtures passing: 6/6
third-party fixtures passing: 6/6
official fixtures tier-3 or better: X/6
official fixtures tier-4 or better: Y/6
level-5 capabilities covered: A/B
level-6 capabilities covered: C/D
```

## Recommended execution order

1. Add adaptation-tier reporting to every existing app fixture report.
2. Add direct SDK smoke runners in this order:
   Python, Go, JavaScript, Java, Rust, C++.
3. Upgrade entity-visualizer from transport proof to browser-visible proof.
4. Deepen AIS and Auto Recon assertions.
5. Add spec-derived REST checks from OpenAPI/Postman artifacts.
6. Add negative/stress certification for auth, streams, and task lifecycle.
7. Add golden gRPC wire fixtures and raw proto generation matrix checks.
8. Implement `BA-001`, `BA-007`, `ADS-002`, `ADS-003`, `ADS-004`.
9. Use those scenario results to close level-5 and level-6 gaps.

## Definition of the next deliverable

The next meaningful deliverable should be:

`S5.3 - Faithful Surrogate Hardening`

It is done when:

- every official fixture report includes adaptation tier and stronger state/event assertions;
- entity-visualizer has a browser-visible proof path;
- negative/stress auth and stream checks exist;
- golden gRPC wire fixtures cover the core RPC set;
- at least `BA-001` and `ADS-002/003/004` are executable and deterministic.

That is the point where Zorn stops merely passing a corpus and starts becoming a
defensible public Lattice surrogate.
