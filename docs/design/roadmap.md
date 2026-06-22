# Roadmap

This roadmap starts from the current compatibility-harness baseline and keeps the
project name as Zorn. Older notes may refer to Stratum; treat that as the former
working name.

For product-readiness gates, see `alpha-readiness-roadmap.md`:

- Alpha 1: DIS App Ready.
- Alpha 2: Vetted Data Plane.
- Alpha 3: Product UI.

## S5.1: Compatibility harness

Status: implemented baseline.

- Pinned certification fixtures live in `cert/lattice/fixtures.yaml`.
- Capability pass conditions live in `cert/lattice/capabilities.yaml`.
- `zorn-cert list`, `clone`, `run`, and `report` provide the executable corpus surface.
- gRPC descriptor audit, generated Python client calls, and AIS REST certification are covered.

## S5.2: Behavioral compliance hardening

Goal: make official SDK clients and sample apps behave against Zorn as they would
against public Lattice-compatible endpoints.

Work loop:

- run official client,
- capture mismatch,
- patch Zorn behavior,
- add regression test,
- repeat.

Primary APIs:

- `EntityManagerAPI.PublishEntity`
- `EntityManagerAPI.PublishEntities`
- `EntityManagerAPI.GetEntity`
- `EntityManagerAPI.StreamEntityComponents`
- `EntityManagerAPI.OverrideEntity`
- `EntityManagerAPI.RemoveEntityOverride`
- `TaskManagerAPI.CreateTask`
- `TaskManagerAPI.GetTask`
- `TaskManagerAPI.QueryTasks`
- `TaskManagerAPI.UpdateStatus`
- `TaskManagerAPI.CancelTask`
- `TaskManagerAPI.ListenAsAgent`
- `TaskManagerAPI.StreamTasks`
- `TaskManagerAPI.ListenForManualControlFrames`

Acceptance criteria:

- Official REST object sample works.
- Official AIS REST sample works.
- Official AIS gRPC sample works.
- Entity visualizer can consume Zorn streams.
- Auto-reconnaissance sample can create tasks.
- gRPC descriptor audit passes.
- Golden wire fixtures pass.
- Unknown fields and protobuf `Any` payloads survive round trips.

## S6: Tactical data adapters

Goal: connect real or simulated tactical protocols into Zorn.

Priority order:

1. DIS Entity State PDU -> Zorn Entity
2. AIS -> Zorn Entity
3. DIS Fire / Detonation -> event/task/object model
4. DIS Electromagnetic Emission -> sensors / detections
5. HLA object updates -> entity components
6. TAK / Cursor-on-Target adapter

Initial DIS Entity State mapping:

| DIS field | Zorn target |
|---|---|
| entity ID | `entityId` plus aliases |
| marking | description / display name |
| force ID | `milView.disposition` |
| entity type | ontology |
| world location | `location.position` |
| velocity | `location.velocityEnu` |
| orientation | `location.attitudeEnu` |
| timestamp/source | provenance |

Acceptance criteria:

- Replay DIS packets into Zorn.
- Entity stream shows create, update, and delete events.
- Entity positions move in real time.
- DIS source identity is preserved.
- Multiple DIS exercise IDs can be namespaced cleanly.

## S6.5: Scenario and replay engine

Goal: make tactical runs deterministic and repeatable.

Features:

- scenario files,
- replay clocks,
- deterministic time,
- pause/resume/seek,
- speed multiplier,
- synthetic entities,
- event recording,
- event replay.

Acceptance criteria:

- One command starts a whole tactical scenario.
- The same scenario produces the same event sequence every run.
- Scenarios can run in CI.
- Scenarios can drive REST, gRPC, and UI clients.

## S7: Taskable mock agents

Goal: add agents that publish themselves, advertise task catalogs, accept tasks,
update status, and produce follow-on objects/entities.

Examples:

- mock UAV agent,
- mock camera agent,
- mock radar agent,
- mock CUAS effector agent,
- mock human observer agent,
- mock investigation agent.

Acceptance criteria:

- Agent stream receives matching tasks.
- Task catalog matching works.
- Cancel requests are delivered.
- Manual-control frame stream works.
- Agents can attach thumbnails, reports, or detections via Objects.

## S8: COP/debug UI

Goal: build a developer UI for inspecting Zorn state and event history.

Views:

- entities map/table, raw JSON/proto, component diff, provenance, event log,
- tasks list, lifecycle timeline, assignment, status, cancel/complete controls,
- object browser with thumbnails, metadata, download, and delete,
- stream inspector for SSE/gRPC events, heartbeats, and reconnect behavior.

Acceptance criteria:

- Watch a DIS replay live.
- Click an entity and inspect raw Lattice-style component data.
- Create a task manually.
- See which mock agent accepted it.
- Inspect every event that led to current state.

## S9: Edge/degraded-network simulation

Goal: approximate tactical-edge behavior locally without claiming proprietary
mesh semantics.

Features:

- multiple Zorn nodes,
- node IDs,
- environment IDs,
- object availability by node,
- replication delay,
- offline queue,
- network partitions,
- packet loss,
- bandwidth limits,
- stale entity behavior,
- deterministic reconciliation.

Acceptance criteria:

- Same API surface works during degraded mode.
- Streams recover after reconnect.
- Object metadata can show simulated distribution state.
- Entity expiry/staleness behavior is visible.
- Conflicts are deterministic and explainable.

## S10: Plugin/developer platform

Goal: keep protocol adapters, task agents, object processors, event subscribers,
scenario sources, and UI panels out of the core monolith.

Acceptance criteria:

- New adapter can be installed without modifying core.
- Plugin declares supported inputs and outputs.
- Plugin can run in-process or as an external service.
- Plugin can be tested against recorded fixtures.

## S11: Packaging and deployment

Goal: make Zorn easy to run locally, offline, and in CI.

Targets:

- Docker Compose,
- single-node local dev,
- offline laptop bundle,
- CI service mode,
- optional Kubernetes deployment,
- Python package,
- container image,
- demo scenario image.

Stable commands should include:

- `zorn serve`
- `zorn grpc`
- `zorn scenario run cuas-demo-01`
- `zorn replay dis fixtures/demo.pcap`
- `zorn compat run`
- `zorn export events run-001.jsonl`

A future neutral CLI alias can be added if the public name changes.

## S12: Credibility/demo package

Goal: explain why Zorn exists with polished, reproducible demonstrations.

Demos:

1. AIS vessel tracking into Zorn
2. DIS battlefield replay into live COP
3. Suspicious entity triggers investigation task
4. Mock UAV accepts task and publishes object thumbnail
5. Edge node goes offline, reconnects, and reconciles
6. Official SDK sample app talks to Zorn

Each demo should include one command, a short video or GIF, an architecture
diagram, API transcript, test results, and known limitations.
