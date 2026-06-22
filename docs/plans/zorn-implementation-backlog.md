# Zorn implementation backlog

| Story ID | Milestone | Epic | Lane | Priority | Title |
|---|---|---|---|---|---|
| Z3-E1-S01 | Z3 | Z3-E1 | LANE-SANDBOX | P0 | Create/list/get/delete local environment records |
| Z3-E1-S02 | Z3 | Z3-E1 | LANE-SANDBOX | P0 | Attach environment_id to entities, tasks, objects, and event log rows without breaking existing default behavior |
| Z3-E1-S03 | Z3 | Z3-E1 | LANE-SANDBOX | P0 | Expose active environment selection through startup configuration and UI-local files |
| Z3-E2-S01 | Z3 | Z3-E2 | LANE-SANDBOX | P0 | Add seed packs for empty, AIS demo, DIS demo, C-UAS surveillance demo, and autonomy patrol demo |
| Z3-E2-S02 | Z3 | Z3-E2 | LANE-SANDBOX | P0 | Implement deterministic reset that clears current state and replays seed data |
| Z3-E2-S03 | Z3 | Z3-E2 | LANE-SANDBOX | P0 | Export environment state as jsonl plus object metadata manifest |
| Z3-E3-S01 | Z3 | Z3-E3 | LANE-SANDBOX | P0 | Add real-time and simulated-time modes |
| Z3-E3-S02 | Z3 | Z3-E3 | LANE-SANDBOX | P0 | Allow pause/resume/speed multiplier for scenarios |
| Z3-E3-S03 | Z3 | Z3-E3 | LANE-SANDBOX | P0 | Ensure TTL/expiry, task status timestamps, and event ordering can use simulated time |
| Z3-E4-S01 | Z3 | Z3-E4 | LANE-SANDBOX | P0 | Register fixture packs with metadata, source, safety classification, and supported scenarios |
| Z3-E4-S02 | Z3 | Z3-E4 | LANE-SANDBOX | P0 | Validate fixture packs before loading |
| Z3-E4-S03 | Z3 | Z3-E4 | LANE-SANDBOX | P0 | Expose fixture pack status in Developer Console |
| Z4-E1-S01 | Z4 | Z4-E1 | LANE-DEVELOPER-CONSOLE | P0 | Browse/filter/search entities by template, disposition, environment, source, liveness, and last update |
| Z4-E1-S02 | Z4 | Z4-E1 | LANE-DEVELOPER-CONSOLE | P0 | Open entity detail with component cards, raw JSON, provenance, and event history |
| Z4-E1-S03 | Z4 | Z4-E1 | LANE-DEVELOPER-CONSOLE | P0 | Validate selected entity against known public-compatible schema checks and local lint rules |
| Z4-E2-S01 | Z4 | Z4-E2 | LANE-DEVELOPER-CONSOLE | P0 | Browse tasks by status, assignee, task type URL, creator, and terminal/non-terminal state |
| Z4-E2-S02 | Z4 | Z4-E2 | LANE-DEVELOPER-CONSOLE | P0 | Show task lifecycle timeline, status payloads, errors, progress, result, and relation graph |
| Z4-E2-S03 | Z4 | Z4-E2 | LANE-DEVELOPER-CONSOLE | P0 | Expose manual create/status/cancel actions in dev mode |
| Z4-E3-S01 | Z4 | Z4-E3 | LANE-DEVELOPER-CONSOLE | P0 | Browse objects by path prefix, size, checksum, expiry, and linked entity |
| Z4-E3-S02 | Z4 | Z4-E3 | LANE-DEVELOPER-CONSOLE | P0 | Preview supported images/text/json and download raw objects |
| Z4-E3-S03 | Z4 | Z4-E3 | LANE-DEVELOPER-CONSOLE | P0 | Show object upload/delete events and TTL status |
| Z4-E4-S01 | Z4 | Z4-E4 | LANE-DEVELOPER-CONSOLE | P0 | Display active SSE/gRPC streams, heartbeat cadence, event counts, reconnects, and last error |
| Z4-E4-S02 | Z4 | Z4-E4 | LANE-DEVELOPER-CONSOLE | P0 | Render descriptor audit and sample-app compatibility status |
| Z4-E4-S03 | Z4 | Z4-E4 | LANE-DEVELOPER-CONSOLE | P0 | Export debug bundle with state snapshot, event log tail, and compatibility report |
| Z5-E1-S01 | Z5 | Z5-E1 | LANE-C2 | P0 | Render entities with location on a map using template/disposition/environment-derived symbology |
| Z5-E1-S02 | Z5 | Z5-E1 | LANE-C2 | P0 | Display trails, headings, speed, altitude/depth, and stale/live/deleted state |
| Z5-E1-S03 | Z5 | Z5-E1 | LANE-C2 | P0 | Support layer toggles for assets, tracks, geo-entities, trails, coverage, labels, and tasks |
| Z5-E2-S01 | Z5 | Z5-E2 | LANE-C2 | P0 | List assets, tracks, geo-entities, alerts, and active tasks in side rail |
| Z5-E2-S02 | Z5 | Z5-E2 | LANE-C2 | P0 | Support search and filters aligned with Entity Explorer |
| Z5-E2-S03 | Z5 | Z5-E2 | LANE-C2 | P0 | Show selected entity detail with core telemetry, provenance, media, and task actions |
| Z5-E3-S01 | Z5 | Z5-E3 | LANE-C2 | P0 | Show pending/assigned/in-progress/completed/failed/canceled task lanes |
| Z5-E3-S02 | Z5 | Z5-E3 | LANE-C2 | P0 | Create allowed mock tasks against selected assets/tracks/areas |
| Z5-E3-S03 | Z5 | Z5-E3 | LANE-C2 | P0 | Cancel tasks and show status timeline updates in the side panel |
| Z5-E4-S01 | Z5 | Z5-E4 | LANE-C2 | P0 | Create local watchlist rules for stale asset, unknown track near zone, task failure, and object expiry |
| Z5-E4-S02 | Z5 | Z5-E4 | LANE-C2 | P0 | Render non-kinetic alerts in map/list panels |
| Z5-E4-S03 | Z5 | Z5-E4 | LANE-C2 | P0 | Allow operator acknowledgement as local UI state |
| Z6-E1-S01 | Z6 | Z6-E1 | LANE-ADAPTERS | P1 | Define adapter lifecycle: configure, validate, start, pause, stop, health, metrics |
| Z6-E1-S02 | Z6 | Z6-E1 | LANE-ADAPTERS | P1 | Add adapter-to-entity mapping registry with source/provenance rules |
| Z6-E1-S03 | Z6 | Z6-E1 | LANE-ADAPTERS | P1 | Expose adapter health and throughput in Developer Console |
| Z6-E2-S01 | Z6 | Z6-E2 | LANE-ADAPTERS | P1 | Convert AIS vessel fixtures into surface track/entity updates |
| Z6-E2-S02 | Z6 | Z6-E2 | LANE-ADAPTERS | P1 | Map MMSI/callsign/name into aliases and provenance |
| Z6-E2-S03 | Z6 | Z6-E2 | LANE-ADAPTERS | P1 | Support replay speed and deterministic event order |
| Z6-E3-S01 | Z6 | Z6-E3 | LANE-ADAPTERS | P1 | Map DIS entity identifiers to stable entityId/aliases |
| Z6-E3-S02 | Z6 | Z6-E3 | LANE-ADAPTERS | P1 | Map DIS location, velocity, orientation, force ID, domain, and entity type into compatible entity components |
| Z6-E3-S03 | Z6 | Z6-E3 | LANE-ADAPTERS | P1 | Add namespace policy for exercise ID and site/application/entity IDs |
| Z6-E4-S01 | Z6 | Z6-E4 | LANE-ADAPTERS | P1 | Represent generic sensor coverage as geo shapes and sensor components |
| Z6-E4-S02 | Z6 | Z6-E4 | LANE-ADAPTERS | P1 | Represent detections as tracks or source-linked entity updates |
| Z6-E4-S03 | Z6 | Z6-E4 | LANE-ADAPTERS | P1 | Preserve source confidence/quality as tracked/provenance metadata when available |
| Z7-E1-S01 | Z7 | Z7-E1 | LANE-OBJECTS-MEDIA | P1 | Add checksum/size/content-type/expiry/path-prefix query behavior to tests |
| Z7-E1-S02 | Z7 | Z7-E1 | LANE-OBJECTS-MEDIA | P1 | Support object lifecycle events for upload/delete/expiry |
| Z7-E1-S03 | Z7 | Z7-E1 | LANE-OBJECTS-MEDIA | P1 | Represent object-to-entity linkage in local indexes without altering public object API |
| Z7-E2-S01 | Z7 | Z7-E2 | LANE-OBJECTS-MEDIA | P1 | Upload image object and attach it to selected entity media component/override where compatible |
| Z7-E2-S02 | Z7 | Z7-E2 | LANE-OBJECTS-MEDIA | P1 | Preview image and basic text/json content in entity detail and object browser |
| Z7-E2-S03 | Z7 | Z7-E2 | LANE-OBJECTS-MEDIA | P1 | Generate synthetic thumbnails for seeded tracks/assets |
| Z7-E3-S01 | Z7 | Z7-E3 | LANE-OBJECTS-MEDIA | P1 | Generate scenario report object with entity/task/event summaries |
| Z7-E3-S02 | Z7 | Z7-E3 | LANE-OBJECTS-MEDIA | P1 | Export evidence bundle with objects, event log, task timeline, and compatibility report |
| Z7-E3-S03 | Z7 | Z7-E3 | LANE-OBJECTS-MEDIA | P1 | Add redaction hooks for sensitive/local-only fields |
| Z7-E4-S01 | Z7 | Z7-E4 | LANE-OBJECTS-MEDIA | P1 | Add local object availability metadata to support later mesh simulation |
| Z7-E4-S02 | Z7 | Z7-E4 | LANE-OBJECTS-MEDIA | P1 | Track which simulated nodes have each object |
| Z7-E4-S03 | Z7 | Z7-E4 | LANE-OBJECTS-MEDIA | P1 | Expose object distribution state as Zorn-only metadata in UI |
| Z8-E1-S01 | Z8 | Z8-E1 | LANE-AUTONOMY | P1 | Register mock agents as entities with TaskCatalog components |
| Z8-E1-S02 | Z8 | Z8-E1 | LANE-AUTONOMY | P1 | Match task specification type URLs to capable agents |
| Z8-E1-S03 | Z8 | Z8-E1 | LANE-AUTONOMY | P1 | Render agent capability and last heartbeat in Developer Console and /c2 |
| Z8-E2-S01 | Z8 | Z8-E2 | LANE-AUTONOMY | P1 | Implement agent loop: listen, accept, update progress, complete/fail/cancel |
| Z8-E2-S02 | Z8 | Z8-E2 | LANE-AUTONOMY | P1 | Support deterministic behavior under sandbox clock |
| Z8-E2-S03 | Z8 | Z8-E2 | LANE-AUTONOMY | P1 | Publish agent telemetry and status entities while executing tasks |
| Z8-E3-S01 | Z8 | Z8-E3 | LANE-AUTONOMY | P1 | Define local YAML/JSON mission graph with tasks, dependencies, gates, and rollback/cancel behavior |
| Z8-E3-S02 | Z8 | Z8-E3 | LANE-AUTONOMY | P1 | Add human approval gates before simulated task execution where appropriate |
| Z8-E3-S03 | Z8 | Z8-E3 | LANE-AUTONOMY | P1 | Render mission graph timeline in UI |
| Z8-E4-S01 | Z8 | Z8-E4 | LANE-AUTONOMY | P1 | Agents can publish new entity observations, task status, and object attachments |
| Z8-E4-S02 | Z8 | Z8-E4 | LANE-AUTONOMY | P1 | Camera-like agent can attach synthetic thumbnail/report objects |
| Z8-E4-S03 | Z8 | Z8-E4 | LANE-AUTONOMY | P1 | Failure modes generate errors visible in task timeline |
| Z9-E1-S01 | Z9 | Z9-E1 | LANE-MESH | P1 | Define simulated nodes with roles, location, storage, and connectivity profile |
| Z9-E1-S02 | Z9 | Z9-E1 | LANE-MESH | P1 | Render topology graph in Developer Console |
| Z9-E1-S03 | Z9 | Z9-E1 | LANE-MESH | P1 | Allow scenario packs to declare node topology |
| Z9-E2-S01 | Z9 | Z9-E2 | LANE-MESH | P1 | Replicate entity/task/object events between nodes according to link profiles |
| Z9-E2-S02 | Z9 | Z9-E2 | LANE-MESH | P1 | Queue events during partitions and replay on reconnect |
| Z9-E2-S03 | Z9 | Z9-E2 | LANE-MESH | P1 | Expose replication lag and conflict resolution trace |
| Z9-E3-S01 | Z9 | Z9-E3 | LANE-MESH | P1 | Track object availability per node |
| Z9-E3-S02 | Z9 | Z9-E3 | LANE-MESH | P1 | Simulate object fetch failures when partitioned or unavailable |
| Z9-E3-S03 | Z9 | Z9-E3 | LANE-MESH | P1 | Surface object distribution state in Object Explorer and C2 media panel |
| Z9-E4-S01 | Z9 | Z9-E4 | LANE-MESH | P1 | Support latency, bandwidth, packet loss, and offline profiles |
| Z9-E4-S02 | Z9 | Z9-E4 | LANE-MESH | P1 | Apply link profiles to streams and object transfers in simulated mode |
| Z9-E4-S03 | Z9 | Z9-E4 | LANE-MESH | P1 | Add UI controls to toggle network impairment during demos |
| Z10-E1-S01 | Z10 | Z10-E1 | LANE-PARTNER | P1 | Define package types: app, adapter, agent, data-service, scenario-pack, domain-pack |
| Z10-E1-S02 | Z10 | Z10-E1 | LANE-PARTNER | P1 | Declare inputs, outputs, API dependencies, task definitions, objects, permissions, and safety notes |
| Z10-E1-S03 | Z10 | Z10-E1 | LANE-PARTNER | P1 | Validate manifests and show errors before installation |
| Z10-E2-S01 | Z10 | Z10-E2 | LANE-PARTNER | P1 | Index installed integrations by capabilities and supported scenarios |
| Z10-E2-S02 | Z10 | Z10-E2 | LANE-PARTNER | P1 | Show compatibility status with REST, gRPC, sample apps, and scenario packs |
| Z10-E2-S03 | Z10 | Z10-E2 | LANE-PARTNER | P1 | Render integration health and recent events |
| Z10-E3-S01 | Z10 | Z10-E3 | LANE-PARTNER | P1 | Run package-specific tests against a clean sandbox |
| Z10-E3-S02 | Z10 | Z10-E3 | LANE-PARTNER | P1 | Generate scorecard: API calls exercised, events emitted, objects created, tasks routed |
| Z10-E3-S03 | Z10 | Z10-E3 | LANE-PARTNER | P1 | Export scorecard as JSON and human-readable report |
| Z10-E4-S01 | Z10 | Z10-E4 | LANE-PARTNER | P1 | Bundle known-good fixtures for AIS, DIS, media, tasks, and mesh partitions |
| Z10-E4-S02 | Z10 | Z10-E4 | LANE-PARTNER | P1 | Declare data provenance and safety boundaries |
| Z10-E4-S03 | Z10 | Z10-E4 | LANE-PARTNER | P1 | Use reference packs in CI and showcase mode |
| Z11-E1-S01 | Z11 | Z11-E1 | LANE-DOMAINS | P1 | Replay AIS tracks with vessel identities and routes |
| Z11-E1-S02 | Z11 | Z11-E1 | LANE-DOMAINS | P1 | Attach synthetic manifest/thumbnail objects |
| Z11-E1-S03 | Z11 | Z11-E1 | LANE-DOMAINS | P1 | Trigger watchlist alerts for training-only rule examples |
| Z11-E2-S01 | Z11 | Z11-E2 | LANE-DOMAINS | P1 | Replay air/surface/ground/subsurface simulated entities |
| Z11-E2-S02 | Z11 | Z11-E2 | LANE-DOMAINS | P1 | Show adapter mapping from raw sim identifiers to public-compatible components |
| Z11-E2-S03 | Z11 | Z11-E2 | LANE-DOMAINS | P1 | Exercise stream and UI performance with dense tracks |
| Z11-E3-S01 | Z11 | Z11-E3 | LANE-DOMAINS | P1 | Represent sensors, surveillance zones, unknown tracks, and investigation tasks safely |
| Z11-E3-S02 | Z11 | Z11-E3 | LANE-DOMAINS | P1 | Route non-kinetic investigation task to mock sensor/camera agent |
| Z11-E3-S03 | Z11 | Z11-E3 | LANE-DOMAINS | P1 | Generate synthetic report object after task completion |
| Z11-E4-S01 | Z11 | Z11-E4 | LANE-DOMAINS | P1 | Create high-altitude/space-track mock entities with uncertainty and sparse updates |
| Z11-E4-S02 | Z11 | Z11-E4 | LANE-DOMAINS | P1 | Create undersea sparse-comms scenario with delayed entity updates and mesh partition behavior |
| Z11-E4-S03 | Z11 | Z11-E4 | LANE-DOMAINS | P1 | Create asset readiness checklist workflow with automated/mock readings and human signoff |
| Z12-E1-S01 | Z12 | Z12-E1 | LANE-SHOWCASE | P1 | Start REST, gRPC, UI, agents, adapters, mesh sim, and selected scenario pack |
| Z12-E1-S02 | Z12 | Z12-E1 | LANE-SHOWCASE | P1 | Check dependency health before scenario starts |
| Z12-E1-S03 | Z12 | Z12-E1 | LANE-SHOWCASE | P1 | Provide deterministic cleanup/reset between runs |
| Z12-E2-S01 | Z12 | Z12-E2 | LANE-SHOWCASE | P1 | Record entities published, tasks created/routed/completed, objects created, stream reconnects, mesh lag, and compatibility results |
| Z12-E2-S02 | Z12 | Z12-E2 | LANE-SHOWCASE | P1 | Emit machine-readable metrics JSON |
| Z12-E2-S03 | Z12 | Z12-E2 | LANE-SHOWCASE | P1 | Render human-readable evaluation report |
| Z12-E3-S01 | Z12 | Z12-E3 | LANE-SHOWCASE | P1 | Capture API transcripts and UI state snapshots during scenario execution |
| Z12-E3-S02 | Z12 | Z12-E3 | LANE-SHOWCASE | P1 | Create operator, developer, partner, and evaluator runbooks |
| Z12-E3-S03 | Z12 | Z12-E3 | LANE-SHOWCASE | P1 | Document expected observations and success signals for each demo |
| Z12-E4-S01 | Z12 | Z12-E4 | LANE-SHOWCASE | P1 | Package docker-compose local stack |
| Z12-E4-S02 | Z12 | Z12-E4 | LANE-SHOWCASE | P1 | Add versioned fixture/data bundles |
| Z12-E4-S03 | Z12 | Z12-E4 | LANE-SHOWCASE | P1 | Generate compatibility matrix and limitation list for each release |
