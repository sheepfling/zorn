# Alpha Readiness Roadmap

This roadmap translates the technical S5-S12 plan into product-readiness gates.
It is intentionally honest about maturity: Alpha 1 is the strict public
Lattice surrogate, Alpha 2 builds the tactical sandbox layer on top of it, and
Alpha 3 adds browser-visible product apps without polluting the data plane.

## Big Picture

Zorn should be built as a two-layer system:

- A strict Lattice-compatible core limited to public Entities, Tasks, Objects,
  OAuth-dev, REST, and public Buf-generated gRPC for Entities and Tasks.
- A Zorn-native environment layer for C2, developer console, scenario control,
  mesh simulation, replay, adapters, and operator workflows that consumes the
  core through those same public interfaces rather than extending or replacing
  them.

The architectural rule is simple:

- C2, mesh, replay, scenarios, and UI are product-layer capabilities, not
  Lattice-contract capabilities.
- They sit above the strict surrogate core, never inside it.

## Alpha 1: Strict Surrogate Ready

Goal: make Zorn a practical local surrogate target for public Lattice clients.

Alpha 1 is not full Lattice compatibility. It is the smallest useful public
integration harness: publish normalized entities, stream them back, and prove
the data is inspectable.

Primary scope:

- Entity publish/update/read/stream over the REST-compatible surface.
- Stable entity/task/object lifecycle behavior through the public APIs.
- Entity create/update/delete or stale behavior visible in event streams.
- Minimal scenario/replay command for a recorded public API sample.
- Compatibility report showing pass/fail/missing for the public surrogate
  contract.

Acceptance criteria:

- `GET` entity returns canonical state for a replayed DIS entity.
- REST stream emits ordered create/update/delete or stale events.
- Multiple entity identifiers namespace cleanly without collisions.
- AIS REST sample and direct SDK smoke fixtures still pass after strict
  surrogate work.
- A certification report can show the final entity set and event log without adding a Zorn-specific integration endpoint.

Non-goals:

- Complete gRPC parity.
- Full task lifecycle parity.
- Operator `/c2` UI.
- Full object/media workflows.
- Fusion/correlation beyond stable public identity mapping.

Exit label:

`Alpha 1 Strict Surrogate Ready`: suitable for local public client integration
and demos, with known gaps documented in reports.

## Alpha 2: Tactical Sandbox Layer

Goal: add a Zorn-native tactical sandbox layer for scenarios, adapters, replay,
mock agents, and degraded-network behavior while keeping all integration
behavior routed through the public Lattice-compatible core.

Alpha 2 starts only after the Alpha 1 surrogate is trustworthy. The purpose is
not to widen the public contract. The purpose is to exercise richer tactical
behavior by publishing and observing through the existing public core.

Primary scope:

- Sandbox environment manager:
  - environment selection
  - seed/reset/export
  - deterministic clock
  - fixture/scenario packs
- Tactical adapters outside the core package:
  - AIS replay
  - DIS replay
  - later protocol adapters using the same public publish/listen paths
- Scenario and replay controls:
  - deterministic time
  - pause/resume/seek/speed
  - recorded event/state replay through public routes
- Mock agents and taskable behavior:
  - TaskCatalog-style entities
  - listen/execute/status/complete/cancel loops
  - synthetic media/report publication through Objects
- Mesh/degraded-network simulation:
  - simulated nodes
  - replication delay/partition/reconnect
  - object availability and queue behavior
- Scenario certification starts for BA-001, BA-007, ADS-002, ADS-003, and
  ADS-004 using the Alpha 1 public core.

Acceptance criteria:

- Environment reset and seed produce repeatable entity/task/object/event state.
- AIS and DIS evaluation helpers can drive the same public entity/event
  surfaces without special-case runtime APIs.
- Mock agents receive tasks through the public task lifecycle and publish
  resulting entity/object updates through the same core routes.
- Scenario clock and replay affect expiry, event ordering, and task timing
  deterministically.
- Mesh simulation stays local to Zorn product behavior and does not redefine
  the compatibility contract.
- Alpha 1 compatibility evidence remains green while Alpha 2 features are
  enabled around it.

Non-goals:

- Inventing new public API surfaces.
- Proprietary mesh behavior.
- Full operator UI.
- Replacing SDK/sample certification with scenario-only proof.

Exit label:

`Alpha 2 Tactical Sandbox Layer`: suitable for local scenario, replay,
adapter, and mock-agent workflows built on top of the strict surrogate core.

## Alpha 3: Product UI

Goal: add separated Zorn product apps that consume the data plane and make
behavior visible in a browser.

Alpha 3 must not move UI requirements into the Lattice-compatible API/proto
contract. UI/application state lives under the Zorn product-app layer.

Primary scope:

- `/developer-console` first:
  - Entity Explorer.
  - Task Explorer.
  - Object Explorer.
  - Stream inspector.
  - Raw JSON/proto projection view.
  - Schema/shape validation view.
  - Compatibility report browser.
- `/c2` second:
  - Map-first COP.
  - Entity markers and disposition styling.
  - Selected entity panel.
  - Task board and task geometry overlays.
  - Object/media previews.
  - Scenario controls for replay, pause, resume, seek, and speed.
- Local UI read models backed by existing Lattice-shaped Entity/Task/Object/Auth surfaces.
- Playwright visual and interaction tests for fixture/scenario output.
- Screenshot artifacts for key certification runs.

Acceptance criteria:

- `/developer-console` can inspect entities, tasks, objects, streams, and compatibility reports from a live Zorn run.
- A replayed entity scenario is visible as moving tracks in the browser.
- Selecting an entity shows canonical component data and provenance.
- Taskable assets expose task catalog actions when available.
- Object thumbnails/media links remain visible after refresh.
- Playwright checks prove map markers, panels, stream status, and report views are browser-visible.
- UI state such as selected entity, active layers, layout, filters, and scenario timeline does not leak into the compatibility data plane.

Non-goals:

- UI as a replacement for SDK/sample app certification.
- UI-specific fields in official Lattice-compatible protos.
- Mission-polished production UX before the debug/developer workflows work.

Exit label:

`Alpha 3 Product UI`: suitable for demos, debugging, and visual certification of
Zorn runs.

## Dependency Order

Alpha 1 feeds Alpha 2 with a trustworthy compatibility core. Alpha 2 feeds
Alpha 3 with deterministic scenario, replay, agent, and mesh behavior. Alpha 3
proves behavior visually, but does not define the data plane.

```text
Alpha 1 Strict Surrogate Ready
  -> public API replay, entity streams, reports

Alpha 2 Tactical Sandbox Layer
  -> environments, replay, adapters, agents, mesh simulation

Alpha 3 Product UI
  -> /developer-console, /c2, visual certification
```

## Current Priority

The immediate downstream implementation priority after Alpha 1 is:

1. Freeze Alpha 1 compatibility evidence as the protected core gate.
2. Build Z3 sandbox environment manager:
   - environment_id
   - seed/reset/export
   - deterministic clock
3. Resume evaluation-only adapters outside the Zorn package:
   - AIS first
   - DIS second
4. Build Alpha 2 mock-agent/task routing on top of the public task core.
5. Add mesh/degraded-network simulation only after environment and replay state
   are deterministic.
6. Start Alpha 3 `/developer-console` before `/c2`.

The detailed boundary and corrective plans are in:

- `design/alpha1-gap-closure-plan.md`
- `design/alpha1-closeout-checklist.md`
- `design/strict-startup-contract.md`
- `design/zorn-product-boundaries.md`

## Alpha 1 Evidence

The first Alpha 1 implementation slice is fixture-driven:

- Evaluation helper package: `eval_dis/`.
- Replay fixture: `tests/fixtures/dis/entity_state_replay.jsonl`.
- Fixture notes: `tests/fixtures/dis/README.md`.
- Tests: `tests/test_dis_entity_state_adapter.py`.
- Public API replay log: `tests/fixtures/replay/entity_task_object_api.jsonl`.
- Public API replay tests: `tests/test_public_api_replay.py`.

This proves the JSONL replay helper can drive the existing public Entity API.
It also proves Entity/Task/Object replay logs can be applied through the
existing public routes without adding a new server surface. It does not yet
prove PCAP or any external adapter ingestion; those should feed the same
neutral adapter model outside the core runtime.
