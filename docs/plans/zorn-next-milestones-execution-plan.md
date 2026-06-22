# Zorn next milestone execution plan

This plan expands the Z3–Z12 roadmap into execution-ready lanes, epics, acceptance tests, and demo signals.

## Contract boundary

- Lattice-compatible scope: Entities, Tasks, Objects, OAuth-dev, REST/gRPC gateway, and official public Buf-generated gRPC descriptors.
- Compatibility kernel: public-compatible Entities, Tasks, Objects, OAuth-dev, REST Entity/Task/Object routes, and public Buf-generated gRPC EntityManagerAPI/TaskManagerAPI only.
- Zorn-only scope: sandbox manager, developer console, operator C2, scenario engine, adapter framework, mesh simulator, partner package system, domain packs, local UI state.
- Rule: do not create local replacement Lattice protos. Zorn extensions must live in sidecar tables, local files, package manifests, scenario files, reports, or UI-internal read models.

## Sources used by this planning slice

- **SRC-LATTICE-CONCEPTS** — Building with Lattice: https://developer.anduril.com/guides/concepts/overview — Defines apps, integrations, data services; Entities, Tasks, Objects; REST/gRPC protocol split.
- **SRC-LATTICE-ENTITIES** — Entities overview: https://developer.anduril.com/guides/entities/overview — Defines entities as component bags powering the COP; asset/track/geo-entity shapes and lifecycle.
- **SRC-LATTICE-TASKS** — Tasks overview: https://developer.anduril.com/guides/tasks/overview — Defines deliberate sequential tasks, TaskCatalog, lifecycle, routing, status updates.
- **SRC-LATTICE-DEV-CONSOLE** — Lattice Developer Console changelog: https://developer.anduril.com/changelog — Lists Developer Console features: Entity Explorer, Task Explorer, Object Explorer, schemas, /developer-console and /c2.
- **SRC-LATTICE-MIGRATION** — Migrate to v2: https://developer.anduril.com/reference/overview/versioning/migrating-to-v2 — Confirms REST/gRPC availability and Buf-generated gRPC artifacts.
- **SRC-LATTICE-C2** — Lattice Command & Control: https://www.anduril.com/lattice/command-and-control — Public lane for C2/common operating picture and battle-management positioning.
- **SRC-LATTICE-AUTONOMY** — Lattice Mission Autonomy: https://www.anduril.com/lattice/mission-autonomy — Public lane for mission autonomy and human-supervised multi-asset autonomy.
- **SRC-LATTICE-MESH** — Lattice Mesh: https://www.anduril.com/lattice/lattice-mesh — Public lane for tactical-edge data distribution and mesh-like workflows.
- **SRC-LATTICE-SDK** — Lattice SDK: https://www.anduril.com/lattice/lattice-sdk — Public lane for SDK apps, data services, and hardware integrations.
- **SRC-LATTICE-PARTNER** — Lattice Partner Program: https://www.anduril.com/lattice/lattice-partner-program — Public lane for partner resources, sandboxes, validation, and reference applications.

## Milestone detail

## Z3 — Sandbox Environment Manager

**Lane:** LANE-SANDBOX

**Objective:** Introduce first-class local environments with isolation, deterministic time, seed/reset/export, fixture packs, and scenario bootstrap files and commands.

**Why now:** Every rich showcase needs repeatability. Environment management prevents the C2 UI, sample app tests, adapters, and mesh simulation from fighting over shared state.

**Depends on:** Z0, Z1, Z2

**Modules:**
- c2_compat_sandbox.environments
- c2_compat_sandbox.fixtures
- c2_compat_sandbox.clock
- c2_compat_sandbox.local_inspection

**Epics and stories:**

### Z3-E1 — Environment registry
- Create/list/get/delete local environment records.
- Attach environment_id to entities, tasks, objects, and event log rows without breaking existing default behavior.
- Expose active environment selection through startup configuration and UI-local files.

### Z3-E2 — Seed, reset, export, and import
- Add seed packs for empty, AIS demo, DIS demo, C-UAS surveillance demo, and autonomy patrol demo.
- Implement deterministic reset that clears current state and replays seed data.
- Export environment state as jsonl plus object metadata manifest.

### Z3-E3 — Deterministic clock
- Add real-time and simulated-time modes.
- Allow pause/resume/speed multiplier for scenarios.
- Ensure TTL/expiry, task status timestamps, and event ordering can use simulated time.

### Z3-E4 — Fixture and schema pack manager
- Register fixture packs with metadata, source, safety classification, and supported scenarios.
- Validate fixture packs before loading.
- Expose fixture pack status in Developer Console.

**Deliverables:**
- Environment manifests and CLI inspection commands.
- Seed/reset/export/import commands.
- Scenario clock service.
- Fixture pack manifest schema.
- CI seed smoke test.

**Acceptance tests:**
- Resetting the same seed twice yields the same entity/task/object/event counts and ordered event hashes.
- Two environments can contain the same entityId without state collision.
- Simulated time pause prevents expiry and task timeline advancement.
- Exported environment can be imported into a clean database and pass equality checks.

**Showcase signal:** A user can pick a scenario pack, reset it, run it, pause time, and export the resulting state for debugging.

**Non-goals / boundaries:**
- No cloud multi-tenant security claims.
- No production-grade identity provider integration.

## Z4 — Developer Console MVP

**Lane:** LANE-DEVELOPER-CONSOLE

**Objective:** Build the first web console for inspecting, filtering, validating, and debugging entities, tasks, objects, streams, schemas, and compatibility results.

**Why now:** The console becomes the workspace for contract hardening, sample-app debugging, adapter development, and scenario authoring.

**Depends on:** Z1, Z2, Z3

**Modules:**
- zorn-ui/developer-console
- c2_compat_sandbox.local_inspection
- zorn-ui/shared

**Epics and stories:**

### Z4-E1 — Entity Explorer
- Browse/filter/search entities by template, disposition, environment, source, liveness, and last update.
- Open entity detail with component cards, raw JSON, provenance, and event history.
- Validate selected entity against known public-compatible schema checks and local lint rules.

### Z4-E2 — Task Explorer
- Browse tasks by status, assignee, task type URL, creator, and terminal/non-terminal state.
- Show task lifecycle timeline, status payloads, errors, progress, result, and relation graph.
- Expose manual create/status/cancel actions in dev mode.

### Z4-E3 — Object Explorer
- Browse objects by path prefix, size, checksum, expiry, and linked entity.
- Preview supported images/text/json and download raw objects.
- Show object upload/delete events and TTL status.

### Z4-E4 — Stream and compatibility inspector
- Display active SSE/gRPC streams, heartbeat cadence, event counts, reconnects, and last error.
- Render descriptor audit and sample-app compatibility status.
- Export debug bundle with state snapshot, event log tail, and compatibility report.

**Deliverables:**
- /developer-console web app shell.
- Entity, Task, Object Explorer pages.
- Stream Inspector page.
- Compatibility Matrix page.
- Debug bundle export.

**Acceptance tests:**
- Entity Explorer displays seeded asset, track, and geo-entity examples.
- Task Explorer displays Create → Update → Cancel/Complete timeline.
- Object Explorer previews a thumbnail object and shows metadata.
- Stream Inspector shows entity stream heartbeats and live create/update/delete events.

**Showcase signal:** A developer can explain exactly why the COP looks the way it does by drilling from UI object to entity component to event to source integration.

**Non-goals / boundaries:**
- No pixel clone of any proprietary UI.
- No operator-grade authorization model yet.

## Z5 — Operator C2 MVP

**Lane:** LANE-C2

**Objective:** Create a map-first operator view that turns live entities, tasks, objects, and streams into a believable common operational picture.

**Why now:** This is the first milestone that makes Zorn feel like a rich environment rather than a backend test server.

**Depends on:** Z3, Z4

**Modules:**
- zorn-ui/c2
- zorn-ui/map
- zorn-ui/task-board
- zorn-ui/media-panel

**Epics and stories:**

### Z5-E1 — Map-first COP shell
- Render entities with location on a map using template/disposition/environment-derived symbology.
- Display trails, headings, speed, altitude/depth, and stale/live/deleted state.
- Support layer toggles for assets, tracks, geo-entities, trails, coverage, labels, and tasks.

### Z5-E2 — Object list and selection
- List assets, tracks, geo-entities, alerts, and active tasks in side rail.
- Support search and filters aligned with Entity Explorer.
- Show selected entity detail with core telemetry, provenance, media, and task actions.

### Z5-E3 — Task board and operator actions
- Show pending/assigned/in-progress/completed/failed/canceled task lanes.
- Create allowed mock tasks against selected assets/tracks/areas.
- Cancel tasks and show status timeline updates in the side panel.

### Z5-E4 — Alerts and watchlists
- Create local watchlist rules for stale asset, unknown track near zone, task failure, and object expiry.
- Render non-kinetic alerts in map/list panels.
- Allow operator acknowledgement as local UI state.

**Deliverables:**
- /c2 web app shell.
- Map renderer with live entity stream.
- Layer manager and object list.
- Selected entity details with task/media panels.
- Task board and basic alert drawer.

**Acceptance tests:**
- AIS or synthetic entity replay moves icons on the map through entity stream updates.
- Selecting an entity highlights it in the map, list, and detail panel.
- Creating a mock investigation task shows it on the task board and routes it to a mock agent.
- Alert rule triggers on a seeded unknown track near a configured training zone.

**Showcase signal:** An observer sees a live, explainable COP with moving tracks, selected details, tasking, alerts, and media attachments.

**Non-goals / boundaries:**
- No real-world targeting, engagement recommendation, or weapon-release workflow.
- No copying proprietary Anduril visual identity.

## Z6 — Sensor, Track, and Protocol Adapters

**Lane:** LANE-ADAPTERS

**Objective:** Build adapter infrastructure and initial AIS/DIS/HLA/CoT-style ingest paths that feed public-compatible entities/events into Zorn.

**Why now:** Adapters make the environment look alive and prove Zorn can serve as a simulation integration platform.

**Depends on:** Z3, Z4, Z5

**Modules:**
- zorn-adapter-framework
- zorn-adapter-ais
- zorn-adapter-dis
- zorn-adapter-hla
- zorn-adapter-cot

**Epics and stories:**

### Z6-E1 — Adapter framework
- Define adapter lifecycle: configure, validate, start, pause, stop, health, metrics.
- Add adapter-to-entity mapping registry with source/provenance rules.
- Expose adapter health and throughput in Developer Console.

### Z6-E2 — AIS adapter
- Convert AIS vessel fixtures into surface track/entity updates.
- Map MMSI/callsign/name into aliases and provenance.
- Support replay speed and deterministic event order.

### Z6-E3 — DIS Entity State adapter
- Map DIS entity identifiers to stable entityId/aliases.
- Map DIS location, velocity, orientation, force ID, domain, and entity type into compatible entity components.
- Add namespace policy for exercise ID and site/application/entity IDs.

### Z6-E4 — Sensor and detection modeling
- Represent generic sensor coverage as geo shapes and sensor components.
- Represent detections as tracks or source-linked entity updates.
- Preserve source confidence/quality as tracked/provenance metadata when available.

**Deliverables:**
- Adapter plugin base classes and manifests.
- AIS fixture replay.
- DIS Entity State PDU mapping skeleton.
- Adapter health/metrics page.
- Mapping registry docs.

**Acceptance tests:**
- AIS replay creates moving surface tracks visible in /c2 and /developer-console.
- DIS fixture creates asset/track entities with stable IDs and deterministic provenance.
- Adapter failure is surfaced as health status without crashing the server.
- Replay can pause/resume through the sandbox clock.

**Showcase signal:** External/simulated data feeds become live COP objects with traceable mappings and health telemetry.

**Non-goals / boundaries:**
- No operational sensor-fusion claims.
- No classified protocol support.
- No live unapproved network ingest by default.

## Z7 — Objects, Media, Reports, and Evidence Workflows

**Lane:** LANE-OBJECTS-MEDIA

**Objective:** Turn object storage into visible workflows for thumbnails, reports, manifests, sensor captures, replay artifacts, and exportable evidence bundles.

**Why now:** Media and reports make demos richer and exercise the full Entities + Objects relationship rather than entity telemetry alone.

**Depends on:** Z3, Z4, Z5

**Modules:**
- c2_compat_sandbox.objects
- zorn-ui/object-browser
- zorn-evidence
- zorn-reporting

**Epics and stories:**

### Z7-E1 — Object metadata hardening
- Add checksum/size/content-type/expiry/path-prefix query behavior to tests.
- Support object lifecycle events for upload/delete/expiry.
- Represent object-to-entity linkage in local indexes without altering public object API.

### Z7-E2 — Thumbnail and media flow
- Upload image object and attach it to selected entity media component/override where compatible.
- Preview image and basic text/json content in entity detail and object browser.
- Generate synthetic thumbnails for seeded tracks/assets.

### Z7-E3 — Reports and evidence bundles
- Generate scenario report object with entity/task/event summaries.
- Export evidence bundle with objects, event log, task timeline, and compatibility report.
- Add redaction hooks for sensitive/local-only fields.

### Z7-E4 — Object distribution simulation hooks
- Add local object availability metadata to support later mesh simulation.
- Track which simulated nodes have each object.
- Expose object distribution state as Zorn-only metadata in UI.

**Deliverables:**
- Object lifecycle events.
- Object/entity linkage index.
- Thumbnail demo workflow.
- Scenario report generator.
- Evidence bundle exporter.

**Acceptance tests:**
- Uploading a thumbnail object makes it visible on selected entity detail.
- Deleting an object updates browser state and event log.
- Evidence export contains manifest, events, tasks, objects, and checksums.
- Object metadata remains REST-compatible while local distribution metadata remains namespaced.

**Showcase signal:** A demo can show track thumbnails, generated reports, downloadable object artifacts, and a complete scenario evidence package.

**Non-goals / boundaries:**
- No evidentiary chain-of-custody certification.
- No sensitive media processing by default.

## Z8 — Mission Autonomy and Taskable Agents

**Lane:** LANE-AUTONOMY

**Objective:** Build mock agents and mission graph execution to exercise task catalogs, task routing, status updates, cancellation, and human-supervised autonomy.

**Why now:** Taskable agents make the task API meaningful and enable richer multi-asset demos without needing real robotics.

**Depends on:** Z3, Z4, Z5, Z6

**Modules:**
- zorn-agent-runtime
- zorn-mission-graph
- zorn-agents/mock_uav
- zorn-agents/mock_camera
- zorn-agents/mock_radar

**Epics and stories:**

### Z8-E1 — Agent registry and TaskCatalog matching
- Register mock agents as entities with TaskCatalog components.
- Match task specification type URLs to capable agents.
- Render agent capability and last heartbeat in Developer Console and /c2.

### Z8-E2 — Mock agent runtime
- Implement agent loop: listen, accept, update progress, complete/fail/cancel.
- Support deterministic behavior under sandbox clock.
- Publish agent telemetry and status entities while executing tasks.

### Z8-E3 — Mission graph DSL
- Define local YAML/JSON mission graph with tasks, dependencies, gates, and rollback/cancel behavior.
- Add human approval gates before simulated task execution where appropriate.
- Render mission graph timeline in UI.

### Z8-E4 — Agent outputs
- Agents can publish new entity observations, task status, and object attachments.
- Camera-like agent can attach synthetic thumbnail/report objects.
- Failure modes generate errors visible in task timeline.

**Deliverables:**
- Agent registry.
- Mock agent runtime.
- TaskCatalog matcher.
- Mission graph runner.
- Human approval gate UI.

**Acceptance tests:**
- A task created in /c2 routes to a matching mock agent via ListenAsAgent.
- Agent status progresses through sent/accepted/in-progress/complete or failed.
- Cancel request interrupts task and records terminal status.
- Mission graph pauses at human approval gate and resumes only after operator approval.

**Showcase signal:** The environment demonstrates human-supervised multi-agent task execution with visible task lifecycles and agent-generated outputs.

**Non-goals / boundaries:**
- No autonomous weapon behavior.
- No real asset control.
- No engagement or targeting recommendations.

## Z9 — Mesh and Edge Simulation

**Lane:** LANE-MESH

**Objective:** Simulate distributed edge behavior: node-local event logs, constrained links, partitions, reconnect, object availability, and deterministic reconciliation.

**Why now:** Mesh-like behavior distinguishes Zorn from a single-node mock and lets demos show tactical-edge constraints safely.

**Depends on:** Z3, Z7

**Modules:**
- zorn-mesh-sim
- zorn-node
- zorn-replication
- zorn-ui/mesh-panel

**Epics and stories:**

### Z9-E1 — Node registry and topology
- Define simulated nodes with roles, location, storage, and connectivity profile.
- Render topology graph in Developer Console.
- Allow scenario packs to declare node topology.

### Z9-E2 — Event replication simulator
- Replicate entity/task/object events between nodes according to link profiles.
- Queue events during partitions and replay on reconnect.
- Expose replication lag and conflict resolution trace.

### Z9-E3 — Object distribution simulator
- Track object availability per node.
- Simulate object fetch failures when partitioned or unavailable.
- Surface object distribution state in Object Explorer and C2 media panel.

### Z9-E4 — Degraded-link profiles
- Support latency, bandwidth, packet loss, and offline profiles.
- Apply link profiles to streams and object transfers in simulated mode.
- Add UI controls to toggle network impairment during demos.

**Deliverables:**
- Mesh node/topology manifest.
- Partition/reconnect simulator.
- Replication trace viewer.
- Object availability model.
- Degraded-link controls.

**Acceptance tests:**
- Partitioning a node stops remote event visibility while local state continues.
- Reconnect replays queued events in deterministic order.
- Object unavailable on a node shows a clear simulated fetch failure.
- Replication trace explains how a final entity state was chosen after conflict.

**Showcase signal:** A demo can disconnect an edge node, continue local operations, then reconnect and show deterministic reconciliation.

**Non-goals / boundaries:**
- No proprietary Lattice Mesh implementation claim.
- No production networking stack.
- No covert communications features.

## Z10 — Partner-Style Integration System

**Lane:** LANE-PARTNER

**Objective:** Create local partner-style integration workflows: package manifests, capability catalogs, conformance suites, reference datasets, and scorecards.

**Why now:** The partner lane turns Zorn into a showcase platform where adapters/apps/agents can be installed, evaluated, and compared.

**Depends on:** Z2, Z3, Z4, Z6

**Modules:**
- zorn-partner-registry
- zorn-plugin-runner
- zorn-conformance
- zorn-ui/partner-console

**Epics and stories:**

### Z10-E1 — Integration package manifest
- Define package types: app, adapter, agent, data-service, scenario-pack, domain-pack.
- Declare inputs, outputs, API dependencies, task definitions, objects, permissions, and safety notes.
- Validate manifests and show errors before installation.

### Z10-E2 — Capability catalog
- Index installed integrations by capabilities and supported scenarios.
- Show compatibility status with REST, gRPC, sample apps, and scenario packs.
- Render integration health and recent events.

### Z10-E3 — Conformance runner
- Run package-specific tests against a clean sandbox.
- Generate scorecard: API calls exercised, events emitted, objects created, tasks routed.
- Export scorecard as JSON and human-readable report.

### Z10-E4 — Reference data packs
- Bundle known-good fixtures for AIS, DIS, media, tasks, and mesh partitions.
- Declare data provenance and safety boundaries.
- Use reference packs in CI and showcase mode.

**Deliverables:**
- zorn-package.json schema.
- Plugin registry and installer skeleton.
- Capability catalog UI.
- Conformance test runner.
- Scorecard export.

**Acceptance tests:**
- A sample AIS adapter package installs and declares entity-publishing capability.
- A mock agent package installs and declares TaskCatalog support.
- Conformance runner executes package tests in a reset sandbox.
- Scorecard accurately reports pass/fail and exercised capabilities.

**Showcase signal:** Zorn can act as a local partner sandbox where integrations are discovered, installed, tested, and scored.

**Non-goals / boundaries:**
- No claim of official Anduril partner validation.
- No execution of untrusted plugin code without explicit local opt-in.

## Z11 — Domain Scenario Packs

**Lane:** LANE-DOMAINS

**Objective:** Package rich, safe, repeatable domain showcases that exercise C2, adapters, autonomy, objects, and mesh behavior.

**Why now:** Domain packs are the showcase surface: they demonstrate why the platform exists and provide regression scenarios for development.

**Depends on:** Z5, Z6, Z7, Z8, Z9, Z10

**Modules:**
- zorn-domain-maritime
- zorn-domain-dis
- zorn-domain-cuas
- zorn-domain-space
- zorn-domain-undersea
- zorn-domain-readiness

**Epics and stories:**

### Z11-E1 — Maritime AIS + media pack
- Replay AIS tracks with vessel identities and routes.
- Attach synthetic manifest/thumbnail objects.
- Trigger watchlist alerts for training-only rule examples.

### Z11-E2 — DIS multi-domain replay pack
- Replay air/surface/ground/subsurface simulated entities.
- Show adapter mapping from raw sim identifiers to public-compatible components.
- Exercise stream and UI performance with dense tracks.

### Z11-E3 — C-UAS surveillance and investigation pack
- Represent sensors, surveillance zones, unknown tracks, and investigation tasks safely.
- Route non-kinetic investigation task to mock sensor/camera agent.
- Generate synthetic report object after task completion.

### Z11-E4 — Space, undersea, and readiness packs
- Create high-altitude/space-track mock entities with uncertainty and sparse updates.
- Create undersea sparse-comms scenario with delayed entity updates and mesh partition behavior.
- Create asset readiness checklist workflow with automated/mock readings and human signoff.

**Deliverables:**
- Maritime scenario pack.
- DIS multi-domain scenario pack.
- C-UAS surveillance scenario pack with safety constraints.
- Space-track mock pack.
- Undersea sparse-comms pack.
- Readiness checklist pack.

**Acceptance tests:**
- Each domain pack can be reset, run, paused, exported, and replayed.
- Each pack exercises at least three of: Entities, Tasks, Objects, UI, adapters, agents, mesh.
- C-UAS pack contains no engagement recommendation, targeting, weapon-release, or fire-control workflow.
- All packs generate a scenario report object and event summary.

**Showcase signal:** A reviewer can choose from multiple realistic-looking but safe scenarios that show the breadth of the ecosystem.

**Non-goals / boundaries:**
- No real operational tactics.
- No live weapons/effectors.
- No classified data or controlled datasets.

## Z12 — Rich Showcase Bundle and Evaluation Mode

**Lane:** LANE-SHOWCASE

**Objective:** Create a polished, repeatable demo/evaluation experience that launches Zorn, runs scenarios, records evidence, and produces reports.

**Why now:** Once features exist, the project needs a clean story that proves the ecosystem in one command and generates artifacts for review.

**Depends on:** Z3, Z4, Z5, Z6, Z7, Z8, Z9, Z10, Z11

**Modules:**
- zorn-showcase-runner
- zorn-eval
- zorn-recording
- zorn-docs

**Epics and stories:**

### Z12-E1 — One-command showcase runner
- Start REST, gRPC, UI, agents, adapters, mesh sim, and selected scenario pack.
- Check dependency health before scenario starts.
- Provide deterministic cleanup/reset between runs.

### Z12-E2 — Evaluation metrics
- Record entities published, tasks created/routed/completed, objects created, stream reconnects, mesh lag, and compatibility results.
- Emit machine-readable metrics JSON.
- Render human-readable evaluation report.

### Z12-E3 — Demo recordings and narrative runbooks
- Capture API transcripts and UI state snapshots during scenario execution.
- Create operator, developer, partner, and evaluator runbooks.
- Document expected observations and success signals for each demo.

### Z12-E4 — Release readiness and packaging
- Package docker-compose local stack.
- Add versioned fixture/data bundles.
- Generate compatibility matrix and limitation list for each release.

**Deliverables:**
- Showcase runner CLI.
- Evaluation metrics/report generator.
- Scenario runbooks.
- Docker compose stack.
- Release compatibility matrix.

**Acceptance tests:**
- A fresh clone can run the showcase bundle and produce a report without manual data setup.
- Evaluation report includes compatibility, scenario, UI, adapter, agent, object, and mesh sections.
- Each demo has a runbook with expected operator/developer observations.
- Release matrix lists supported, partial, and intentionally unsupported features.

**Showcase signal:** Zorn can be demonstrated as a complete local environment with API compatibility, COP UI, adapters, agents, mesh simulation, partner integration, and scenario reports.

**Non-goals / boundaries:**
- No claim of official Lattice certification.
- No production deployment guarantee.
