# Zorn Lattice Integration Registry

Generated: 2026-06-21

## Scope

This registry collects public GitHub projects that either use Anduril Lattice directly, are official Anduril samples, or are adjacent/pattern-only implementations that can inform Zorn behavior. It is triaged for certification/validation use, not for license clearance. Repos without an explicit license in inspected files should be treated as source-available only until reviewed.

## Surface legend

- Auth: bearer/environment token, OAuth client credentials, sandbox header, gRPC PerRPC credentials
- Entity Publish: publish/create/update entity
- Entity Stream: streaming/long-poll/SSE/gRPC entity updates
- Entity Override: field-specific overrides such as mil_view.disposition
- Entity Components: location, velocity, attitude, aliases, ontology, MilView, provenance, health, classification, relationships, tracked, transponder codes, task catalog
- Tasks: create_task, listen_as_agent, execute requests, update_task_status, task catalog
- Objects: upload/download/delete/list, metadata, thumbnail/object linkage
- UI/Storage: map visualization, Cesium/MapLibre, WebSocket/SSE, Neo4j/persistence

## Registry

| ID | Repository | Category | Language/runtime | License status | Zorn priority | Lattice surfaces exercised | Notes |
|---|---|---|---|---|---|---|---|
| A001 | anduril/sample-app-ais-integration-rest | Official sample | Python REST SDK | Anduril sample terms / review before vendoring | P0 | Auth, Entity Publish, Entity Components | Minimal REST entity publisher using simulated AIS vessel traffic. Best first smoke test. |
| A002 | anduril/sample-app-ais-integration-grpc | Official sample | Python gRPC SDK | Anduril sample terms / review before vendoring | P0 | Auth, Entity Publish, Entity Components | Same AIS lifecycle through gRPC SDK. Use beside A001 to compare protocol parity. |
| A003 | anduril/sample-app-entity-visualizer | Official sample | TypeScript/React | Anduril sample terms / review before vendoring | P0 | Auth, Entity Stream, UI | Entity stream consumer + real-time map UI. Good first read-side fixture. |
| A004 | anduril/sample-app-auto-reconnaissance | Official sample | Python | Anduril sample terms / review before vendoring | P0 | Entity Publish, Entity Stream, Entity Override, Tasks, Task Catalog | Core task lifecycle + override workflow. Essential for Zorn C2 behavior. |
| A005 | anduril/sample-app-objects | Official sample | Go CLI | Anduril sample terms / review before vendoring | P0 | Auth, Objects | Object API CRUD fixture: upload, download, delete, metadata, prefix listing. |
| A006 | anduril/sample-app-thumbnail | Official sample | Python | Anduril sample terms / review before vendoring | P0 | Objects, Entity Publish, object/entity linkage | Entity thumbnail workflow; crosses objects and entities. |
| T001 | ARK-Electronics/mavlink-to-lattice | Third-party real integration | Python + MAVSDK | BSD-3-Clause found | P0 | Auth, Entity Publish, Entity Components, Task Catalog | Real UAV telemetry at 1 Hz: position, velocity, attitude quaternion, health, ontology, MilView, provenance. |
| T002 | alphafox02/DragonSync | Third-party real integration | Python | Apache-2.0 found | P0 | Auth, Entity Publish, Entity Components, Relationships, Classification, Health | Rich WarDragon/RID/ADS-B/TAK bridge; publishes system, drone, pilot, home entities; rate limits and sandbox header handling. |
| T003 | daemon-blockint-tech/Maven | Third-party real integration | Go + React/Cesium + Neo4j | No license found in inspected files | P0/P1 | OAuth Auth, gRPC Entity Stream, Entity Publish, Entity Components, UI/Storage | Strong Zorn surrogate candidate: Go gRPC StreamEntityComponents, PublishEntity test command, Neo4j persistence, WebSocket/Cesium UI. |
| T004 | PhilipPanda/Lattice-ADSB-Bridge | Third-party real integration | Java/Spring | No license found in inspected files | P1 | Java Auth/client, Entity Publish, Entity Components, Transponder Codes, mock server, UI/SSE | Exercises Java SDK and ADS-B/OpenSky mapping. Useful once Java SDK endpoint compatibility matters. |
| T005 | Lagrange-Labs/anduril-deep-prove-demo | Third-party fork/enhancement | Python | No license found in inspected files | P1 | Entity Publish, Entity Stream, Entity Override, Tasks, listen_as_agent, update_task_status | Enhanced Auto Recon with ZK proof layer. Good task lifecycle stress fixture; license review needed. |
| T006 | tylerxmart32-afk/ALFRED_AGENT | Third-party real-ish integration | Python | License not verified | P2 | Entity Publish, Entity Stream, Entity Override, Tasks, local mock | Broad and messy ARGUS bridge. Useful stress/edge fixture after clean samples pass. |
| X001 | simplifaisoul/osiris | Adjacent/pattern-only | TypeScript/Next.js | README badge says MIT; verify | Research only | Simulated Lattice stream adapter, UI mapping | Not a confirmed SDK integration. Could inform UI shape tests only. |
| X002 | Enotrium/Vegard | Adjacent/pattern-only | Python | Not verified | Research only | Pattern-only tasks/entity state | Models ListenAsAgent/task patterns, but no live SDK client. |
| X003 | szl-holdings/platform | Adjacent/pattern-only | TypeScript | Not verified | Exclude from certification | Pattern-only architecture | Explicitly pattern-only, no Anduril code. |
| X004 | bgilbert1984/RF_SCYTHE | Adjacent/proprietary | Python/JS | Proprietary stated | Exclude from vendoring | Lattice-like SSE/provenance/session patterns | Mentions Lattice patterns, not a clean open-source integration. |

## Coverage matrix

| Surface | Primary fixtures | Secondary/stress fixtures | Gaps / notes |
|---|---|---|---|
| REST auth + sandbox header | A001, A005, A006, T001, T002 | T006 | Need assert header spelling/case acceptance and token failure modes. |
| OAuth client credentials | T003, T006 | T004 if adapted | Zorn should support OAuth token endpoint and sandbox header. |
| gRPC auth / PerRPC credentials | A002, T003 | SDK repos | Need gRPC TLS/insecure switch, token refresh, metadata propagation. |
| Publish entity basic | A001, A002, T001, T003 | T004, T005, T006 | Validate entity ID stability, upsert semantics, expiry, is_live. |
| Rich entity components | T001, T002, T004 | T006 | Components include health, classification, relationships, transponder codes, tracked, task catalog. |
| Entity stream read-side | A003, T003, T005, T006 | T004 mock/SSE | Need created/update/delete event types, pre-existing behavior, heartbeats, reconnect. |
| Overrides | A004, T005, T006 | — | Primary case is mil_view.disposition override. |
| Tasks create/assign/status | A004, T005, T006 | — | Need create_task, listen_as_agent, execute request, update_task_status, status versioning. |
| Objects API | A005, A006 | — | Only official samples cover this so far. Need object metadata, prefix list, binary payload, thumbnail link. |
| UI consumers | A003, T003, T004 | X001 | Test stream-to-map and stream-to-WebSocket adapters. |
| Persistence | T003 | T002 internal state | Neo4j persistence is a useful external-observer oracle for stream correctness. |

## Recommended integration order

1. Establish the Zorn core acceptance suite with A001, A002, A003, A005, A006, and A004.
2. Add T001 and T002 as real-world entity publishers for high-frequency telemetry, health, classification, relationships, and task catalog fields.
3. Add T003 as the first full surrogate/read-side stack: OAuth, gRPC stream, publish smoke command, persistence, WebSocket, and Cesium UI.
4. Add T004 to validate Java SDK compatibility and ADS-B/transponder mapping.
5. Add T005 to stress task lifecycle behavior beyond the base Auto Recon sample.
6. Use T006 only after the cleaner fixtures pass; it is valuable for messy integration behavior but not as a baseline.
7. Keep X001-X004 in research-only status unless we need UI patterns or conceptual task semantics.

## Immediate Zorn test objectives

- Implement a fixture runner that can clone a repo at a pinned commit and inject Zorn endpoint/auth env vars.
- Standardize observed outcomes as assertions: entities created/updated/deleted, stream events received, tasks created/statused, objects uploaded/listed/downloaded/deleted.
- Maintain license metadata separately from technical coverage; do not vendor unknown-license code.
- Add a small compatibility shim only where samples hard-code URLs or sandbox host conventions.
