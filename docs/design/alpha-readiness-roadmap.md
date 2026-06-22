# Alpha Readiness Roadmap

This roadmap translates the technical S5-S12 plan into product-readiness gates.
It is intentionally honest about maturity: Alpha 1 should be useful for a DIS
app, Alpha 2 should be a much more faithful Lattice-compatible data plane, and
Alpha 3 should add browser-visible product apps without polluting the data plane.

## Alpha 1: DIS App Ready

Goal: make Zorn a practical local surrogate target for a DIS integration app.

Alpha 1 is not full Lattice compatibility. It is the smallest useful tactical
integration harness: replay DIS Entity State PDUs, publish normalized entities,
stream them back, and prove the data is inspectable.

Primary scope:

- DIS Entity State PDU -> Zorn Entity adapter.
- Entity publish/update/read/stream over the REST-compatible surface.
- Stable entity IDs derived from DIS exercise/site/application/entity identity.
- DIS source identity and exercise ID preserved in aliases/provenance.
- Location, velocity, orientation, force/disposition, entity type, and marking mapped into entity components.
- Entity create/update/delete or stale behavior visible in event streams.
- Minimal scenario/replay command for a recorded DIS sample.
- Compatibility report showing pass/fail/missing for the DIS readiness contract.

Acceptance criteria:

- `zorn replay dis <pcap-or-fixture>` publishes moving entities into Zorn.
- `GET` entity returns canonical state for a replayed DIS entity.
- REST stream emits ordered create/update/delete or stale events.
- Multiple DIS exercise IDs namespace cleanly without entity ID collisions.
- AIS REST sample and direct SDK smoke fixtures still pass after DIS adapter work.
- A certification report can show the final entity set and event log without adding a Zorn-specific integration endpoint.

Non-goals:

- Complete gRPC parity.
- Full task lifecycle parity.
- Operator `/c2` UI.
- Full object/media workflows.
- Fusion/correlation beyond stable DIS identity mapping.

Exit label:

`Alpha 1 DIS App Ready`: suitable for local DIS app integration and demos, with
known gaps documented in reports.

## Alpha 2: Vetted Data Plane

Goal: make Zorn a materially more faithful Lattice-compatible data plane across
Entities, Tasks, Objects, auth, streams, and gRPC.

Alpha 2 is where Zorn moves from "useful DIS harness" to "credible public
Lattice surrogate for SDK/sample app behavior." The UI remains separate and is
not allowed to define data-plane behavior.

Primary scope:

- Official SDK smoke coverage for Python, Go, JavaScript, Java, C++, and Rust where tooling is available.
- Official sample apps exercised with adaptation-tier reporting.
- REST Entities, Tasks, and Objects behavior hardened against sample and SDK expectations.
- gRPC EntityManager and TaskManager auth metadata, TLS modes, descriptor audits, and generated-client calls.
- Golden gRPC wire fixtures for entity publish/get/stream and task create/update/cancel/listen.
- Negative and stress certification: bad auth, stale updates, bad task transitions, reconnects, heartbeats, concurrent publish-stream.
- Object byte fidelity, metadata, list, download, delete, and thumbnail/entity linkage.
- Task lifecycle ordering, status versions, agent delivery, cancellation, and no duplicate agent delivery.
- Protobuf `Any`, enums, timestamps, durations, and unknown fields round-trip where expected.
- Scenario certification starts for BA-001, BA-007, ADS-002, ADS-003, and ADS-004.

Acceptance criteria:

- `zorn-cert validate-contracts` passes.
- SDK Python, Go, and JavaScript direct smokes pass full-surface contracts.
- Java/C++/Rust tracks either pass or report explicit environment/schema blockers.
- Official AIS REST and AIS gRPC publish moving entities.
- Official Objects and Thumbnail workflows pass with byte/link fidelity.
- Entity visualizer has browser-visible proof, not only transport proof.
- Auto Recon-style task creation and agent listening work through the expected lifecycle.
- Golden gRPC fixtures pass or produce compatibility reports with actionable failures.
- Compatibility reports distinguish `endpoint_token_only`, `runtime_env_translation`, `transport_proxy`, `runtime_shim`, and `local_overlay`.

Non-goals:

- Production security posture.
- Proprietary mesh behavior.
- Full operator UI.
- General-purpose plugin marketplace.

Exit label:

`Alpha 2 Vetted Data Plane`: suitable for broad local compatibility testing
against public SDKs, sample apps, and tactical protocol adapters.

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
- A DIS replay is visible as moving tracks in the browser.
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

Alpha 1 feeds Alpha 2 with real tactical data pressure. Alpha 2 feeds Alpha 3
with trustworthy data-plane behavior. Alpha 3 proves behavior visually, but does
not define the behavior.

```text
Alpha 1 DIS App Ready
  -> DIS adapter, replay, entity streams, reports

Alpha 2 Vetted Data Plane
  -> SDK/sample/gRPC/object/task lifecycle parity

Alpha 3 Product UI
  -> /developer-console, /c2, visual certification
```

## Current Priority

The immediate implementation priority is now Alpha 1 corrective hardening:

1. Close the FastDIS entity parity gaps:
   - gRPC override request parsing
   - gRPC non-live parity
   - override removal restoring shared state across transports
2. Make OAuth-dev tokens distinct and expiring without inventing new auth
   surfaces.
3. Keep FastDIS and replay lanes on the same public Entity/Task/Object
   interfaces used by SDK/sample certification.
4. After the above is green, resume the DIS Entity State adapter and replay
   tranche.

The detailed corrective plan is in:

- `design/alpha1-gap-closure-plan.md`

## Alpha 1 Evidence

The first Alpha 1 implementation slice is fixture-driven:

- Adapter package: `src/zorn/adapters/dis/`.
- Replay fixture: `tests/fixtures/dis/entity_state_replay.jsonl`.
- Fixture notes: `tests/fixtures/dis/README.md`.
- Command: `zorn replay dis tests/fixtures/dis/entity_state_replay.jsonl --target http://127.0.0.1:8080 --report /tmp/zorn-alpha1-dis-report.json`.
- Tests: `tests/test_dis_entity_state_adapter.py`.
- Public API replay log: `tests/fixtures/replay/entity_task_object_api.jsonl`.
- Public API replay tests: `tests/test_public_api_replay.py`.

This proves the JSONL Entity State replay path through the existing public
Entity API. It also proves Entity/Task/Object replay logs can be applied through
the existing public routes without adding a new server surface. It does not yet
prove PCAP or FastDIS ingestion; those should feed the same neutral adapter
model next.
