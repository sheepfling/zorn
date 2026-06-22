# Zorn Lattice UI Reference Registry

Generated: 2026-06-21T23:27:43.120969+00:00

This registry converts public Lattice UI evidence into preliminary Zorn UI and state-model requirements. It separates source reliability from requirement priority so we can use official documentation as hard evidence and public screenshots/design portfolios as supporting evidence.

## Confidence scale

- **High**: official Anduril docs or screenshots tied directly to official developer workflows.
- **Medium-high**: official company news/exercise imagery with visible UI but limited documentation context.
- **Medium**: partner articles or sanitized portfolio material. Useful for UX behavior; not a complete production spec.
- **Low**: public social screenshots. Use only as supporting evidence.

## Source catalog

| ID | Title | Type | Reliability | Key images | Notes |
|---|---|---|---|---|---|
| `SRC-001` | Anduril developer docs — Watch entities | official_docs | high | `IMG-001`, `IMG-002` | Official docs page for getting an entity from the UI and streaming entity events. Includes Lattice UI asset details imagery. |
| `SRC-002` | Anduril developer docs — Sample apps | official_docs | high | `IMG-003` | Official sample app overview. Includes entity visualizer, objects CLI, AIS integration, entity thumbnail, and task-an-asset samples. |
| `SRC-003` | Anduril developer docs — Entities overview | official_docs | high | — | Official data-model source for entities, templates, lifecycle, assets, tracks, and geo-entities. |
| `SRC-004` | Anduril developer docs — Tasks overview | official_docs | high | — | Official source for task model, task catalog, task status, and task lifecycle semantics. |
| `SRC-005` | Anduril developer docs — Update tasks | official_docs | high | `IMG-004`, `IMG-005` | Official task status update guide with screenshot evidence of task selection/execution UI. |
| `SRC-006` | Anduril developer docs — Objects overview | official_docs | high | — | Official object-store source for file/data storage, object lifecycle, CDN/mesh behavior, and entity/object use cases. |
| `SRC-007` | Lauren Park portfolio — Anduril Lattice UI | designer_portfolio | medium | `IMG-006`, `IMG-007` | Sanitized designer portfolio describing Lattice Live COP, object multi-selection, grouping, bulk editing, and starring. |
| `SRC-008` | Wind River blog — Lattice Sandbox integration | partner_blog | medium | `IMG-008`, `IMG-009` | Partner blog about early Lattice Sandbox access and integration with Lattice SDK. Includes sandbox UI screenshots with simulated assets and tasks. |
| `SRC-009` | Anduril news — Desert Guardian 1.0 | company_news | medium_high | `IMG-010` | Public exercise screenshot showing satellite map, hostile air vehicle tracks, loiter/engagement regions, and Roadrunner task cards. |
| `SRC-010` | Hartpunkt article — Anduril Lattice selected for U.S. Army IBCS-M | media_article | medium | `IMG-011` | German article with Anduril-attributed C-UAS/fire-control UI screenshot. Use as supporting visual evidence only. |
| `SRC-011` | Public social screenshot — Lattice Live drone tracking | social_media | low | `IMG-012` | Unverified public screenshot of Lattice Live showing wardragon-detection track details. Keep as low-confidence supporting evidence. |

## Image / resource analysis

| ID | Source | Title | Priority | Confidence | Observed UI | Proto requirements |
|---|---|---|---:|---|---|---|
| `IMG-001` | `SRC-001` | Entity details panel with asset actions | P0 | high | Dark-theme map-first shell; Left entity detail panel; Online badge; Entity template/platform label; Disposition dropdown-like label; … | `REQ-ENT-DETAIL-001`, `REQ-ENT-ACTIONS-001`, `REQ-ENT-COPY-001`, `REQ-STAR-001` |
| `IMG-002` | `SRC-001` | Entity Explorer / get entity context | P0 | high | Entity Explorer table/list implied by official docs; Entity ID column for copy/use in SDK calls | `REQ-EXPLORER-001`, `REQ-EXPLORER-002` |
| `IMG-003` | `SRC-002` | Tasking interface with bearing/range line | P0 | high | Selected asset detail panel; Central map with bearing/range geometry; Target/asset connection line; Task details panel for Investigate; Edit / complete / cancel task controls; … | `REQ-TASK-PANEL-001`, `REQ-TASK-GEOMETRY-001`, `REQ-MAP-CURSOR-001` |
| `IMG-004` | `SRC-005` | Task assignment workflow on satellite map | P0 | high | Satellite basemap; Anchored-to-asset banner; Selected asset/track popup; Right-side Task Details panel; Select track from map prompt; … | `REQ-TASK-CREATE-001`, `REQ-TASK-EXECUTE-001`, `REQ-MAP-PROMPT-001` |
| `IMG-005` | `SRC-005` | Task dropdown from asset panel | P0 | high | Asset detail panel task dropdown; Task list includes BDA, Follow, Investigate, Manual, Smack, Target; Task menu items include info/help icons; Payloads / Task Catalog / Tags sections visible | `REQ-TASK-CATALOG-001`, `REQ-TASK-LAUNCHER-001`, `REQ-ENT-SECTIONS-001` |
| `IMG-006` | `SRC-007` | Object map visualization and object list | P1 | medium | Interactive map with clustered/numbered markers; Left Objects panel; Search and sort controls; Object cards with metadata/creator-like fields; Object map visualization empty/intro state | `REQ-OBJECT-LIST-001`, `REQ-MAP-CLUSTER-001`, `REQ-SEARCH-SORT-001` |
| `IMG-007` | `SRC-007` | Multi-selection, bulk action, grouping, ungroup confirmation | P1 | medium | Multi-selection panel; Selected count; Search and sort selected objects; Bulk Action button; Group/Ungroup controls; … | `REQ-SELECT-001`, `REQ-SELECT-002`, `REQ-BULK-001`, `REQ-GROUP-001`, `REQ-GROUP-UNGROUP-001`, `REQ-FEEDBACK-001` |
| `IMG-008` | `SRC-008` | Sandbox UAV task details interface | P1 | medium | Blue bounded task/selection frame on map; Task Details panel for BDA-like mission; Target selection prompt; Conflict resolution prompt; Discard and Execute Task buttons; … | `REQ-TASK-DETAILS-001`, `REQ-TASK-CONFLICT-001`, `REQ-ENT-HOVER-001` |
| `IMG-009` | `SRC-008` | Sandbox simulated asset with payloads and data overrides | P1 | medium | Left panel with SPI/asset data; Payloads section with operational status and count; Add Payload action; Data Overrides section with validation/check state; Task dropdown; … | `REQ-PAYLOAD-001`, `REQ-OVERRIDE-001`, `REQ-STATUSBAR-001` |
| `IMG-010` | `SRC-009` | Desert Guardian operational C2 screenshot | P1 | medium_high | Satellite map with hostile air tracks; Layers/Search/Analytics/Map Options controls; Left track list/detail panel; Right mission/task cards; Loiter zone polygon/circle; … | `REQ-TOOLBAR-001`, `REQ-THREAT-001`, `REQ-ZONE-001`, `REQ-TASK-CARDS-001` |
| `IMG-011` | `SRC-010` | C-UAS/fire-control screenshot | P2 | medium | 3D/satellite tactical map; Multiple track categories/colors; Sensor cones/coverage sectors; Defended area polygon; Triage/status categories such as pending/current/complete; … | `REQ-CUAS-QUEUE-001`, `REQ-SENSOR-COVERAGE-001`, `REQ-SAFETY-STOP-001` |
| `IMG-012` | `SRC-011` | Public social Lattice Live drone tracking screenshot | P2 | low | Dark map with multiple drone/track markers; Inline selected-track popup; Left panel/details implied by selected route URL; Bottom UTC timestamp/live status bar | `REQ-ENT-HOVER-001`, `REQ-REMOTEID-001`, `REQ-STATUSBAR-001` |

## Proto requirement catalog

| ID | Priority | Requirement | Evidence |
|---|---:|---|---|
| `REQ-COP-001` | P0 | Map-first Live COP shell — Zorn shall provide a map-first, dark-theme Live COP shell with live status, map toolbar, entity layers, and selected-object panels. | IMG-001, IMG-003, IMG-004, IMG-010 |
| `REQ-TOOLBAR-001` | P1 | Global toolbar — Zorn should expose global map controls for layers, search, analytics, and map options. | IMG-010 |
| `REQ-EXPLORER-001` | P0 | Entity Explorer — Zorn shall provide an Entity Explorer/Object list that supports browsing, selecting, searching, and sorting entities. | IMG-002, IMG-006 |
| `REQ-EXPLORER-002` | P0 | Copy entity ID — Zorn shall allow operators/developers to copy an entity ID from the Entity Explorer or detail panel. | SRC-001, IMG-002 |
| `REQ-ENT-DETAIL-001` | P0 | Entity detail panel — Zorn shall show a detail panel for selected entities containing status, template/platform, disposition, data type, ID, simulation/live state, kinematics, location, timestamps, provenance, and health where present. | IMG-001, IMG-003, IMG-004, IMG-009, IMG-012 |
| `REQ-ENT-SECTIONS-001` | P1 | Expandable entity component sections — Zorn should group selected entity details into expandable sections such as Asset Data, Payloads, Data Overrides, Task Catalog, Tags, and Media. | IMG-005, IMG-009 |
| `REQ-ENT-ACTIONS-001` | P0 | Entity action menu — Zorn shall provide an entity action menu with Follow, Manual/control placeholder, Anchor to Map Center, Copy Content, and Manage Asset actions. | IMG-001 |
| `REQ-ENT-COPY-001` | P1 | Copy asset URL/location/content — Zorn should support copy actions for asset URL, asset location, and serialized content. | IMG-001 |
| `REQ-ENT-HOVER-001` | P1 | Inline map entity popup — Zorn should show a compact inline popup when hovering or selecting a map entity, repeating key details from the side panel. | IMG-008, IMG-012 |
| `REQ-MAP-CLUSTER-001` | P1 | Entity clustering — Zorn should cluster high-density entities and show count markers on the map. | IMG-006 |
| `REQ-MAP-CURSOR-001` | P0 | Cursor coordinates and scale — Zorn shall show map scale and cursor coordinate/readout status. | IMG-003, IMG-009, IMG-012 |
| `REQ-STATUSBAR-001` | P0 | Live status bar — Zorn shall show a bottom or persistent status bar indicating live state, current/UTC time, and last event timing. | IMG-009, IMG-012 |
| `REQ-TASK-CATALOG-001` | P0 | Task catalog-derived task menu — Zorn shall derive available task actions from the selected asset's task catalog where available, with fallbacks for sample fixtures. | IMG-005, SRC-004 |
| `REQ-TASK-LAUNCHER-001` | P0 | Task launcher dropdown — Zorn shall provide a task dropdown/action launcher from the selected asset detail panel. | IMG-005, IMG-009 |
| `REQ-TASK-DETAILS-001` | P0 | Task details panel — Zorn shall provide a Task Details panel with task type, assigned asset(s), objective/target, parameters, conflict state, and execute/discard controls. | IMG-003, IMG-004, IMG-008 |
| `REQ-TASK-CREATE-001` | P0 | Create task from map selection — Zorn shall allow operators to create a task from an asset and a map-selected target or point. | IMG-003, IMG-004, SRC-004 |
| `REQ-TASK-EXECUTE-001` | P0 | Execute/discard task workflow — Zorn shall support task draft, execute, discard, status update, complete, and cancel workflows. | IMG-003, IMG-004, IMG-008, SRC-004, SRC-005 |
| `REQ-TASK-GEOMETRY-001` | P0 | Task geometry overlays — Zorn shall render bearing/range lines and task-related geometry between assigned assets and objectives. | IMG-003, IMG-004, IMG-010 |
| `REQ-TASK-CONFLICT-001` | P1 | Task conflict prompt — Zorn should expose task conflict state and prompt operators to resolve conflicts before execution. | IMG-008 |
| `REQ-TASK-CARDS-001` | P1 | Mission/task cards — Zorn should show active/pending/current/completed task cards with progress/readiness and context actions. | IMG-010, IMG-011 |
| `REQ-ZONE-001` | P1 | Geo-zone overlays — Zorn should render geo-entity shapes and task/mission zones such as loiter zones, corridors, defended areas, and polygons. | IMG-010, IMG-011, SRC-003 |
| `REQ-SENSOR-COVERAGE-001` | P2 | Sensor coverage overlays — Zorn may render sensor cones/coverage sectors as map overlays. | IMG-011 |
| `REQ-THREAT-001` | P0 | Threat/disposition visualization — Zorn shall visualize disposition/threat using distinct map marker styles and detail-panel labels. | IMG-003, IMG-010, IMG-011, SRC-003 |
| `REQ-PAYLOAD-001` | P1 | Payload panel — Zorn should display payload components/statuses for assets when available. | IMG-009 |
| `REQ-OVERRIDE-001` | P1 | Data overrides panel — Zorn should show and eventually manage field-level data overrides, including override status/validity. | IMG-009 |
| `REQ-OBJECT-LIST-001` | P1 | Objects panel — Zorn should provide an Objects panel for object/media records and entity-associated object references. | IMG-006, SRC-006 |
| `REQ-MEDIA-001` | P1 | Track thumbnails and manifests — Zorn should support rendering media/object references such as track thumbnails and vessel manifests through the entity media component. | SRC-006 |
| `REQ-SELECT-001` | P1 | Multi-select entrypoints — Zorn should allow multi-selection through shift-click on object/entity cards and map-area selection. | IMG-007, SRC-007 |
| `REQ-SELECT-002` | P1 | Multi-selection panel — Zorn should provide a multi-selection panel with selected count, search, sort, filters, and clear/remove actions. | IMG-007, SRC-007 |
| `REQ-BULK-001` | P1 | Bulk metadata edit — Zorn should support bulk metadata edit actions over a selection set. | IMG-007, SRC-007 |
| `REQ-GROUP-001` | P1 | Create and manage entity groups — Zorn should allow creating groups from selected entities and adding entities to existing groups. | IMG-007, SRC-007, SRC-004 |
| `REQ-GROUP-UNGROUP-001` | P1 | Ungroup confirmation — Zorn should require confirmation before ungrouping/removing a group. | IMG-007, SRC-007 |
| `REQ-STAR-001` | P1 | Starred entities — Zorn should let operators star objects/entities from cards, details panels, and map context menus, then access them from a Starred panel. | IMG-001, SRC-007 |
| `REQ-FEEDBACK-001` | P1 | Operator feedback snackbar — Zorn should show confirmation/error snackbars after bulk edit, group add/remove, star, and task actions. | SRC-007 |
| `REQ-CUAS-QUEUE-001` | P2 | Threat engagement queue — Zorn may provide a pending/current/complete queue for C-UAS or fire-control workflows. | IMG-011 |
| `REQ-SAFETY-STOP-001` | P2 | Emergency stop / abort action affordance — Zorn may expose high-salience abort/emergency-stop controls for simulated engagements only. | IMG-011 |
| `REQ-REMOTEID-001` | P2 | Remote ID / drone detection track fields — Zorn may provide specific rendering for Remote ID / small UAS detection fields such as serial number, ANSI/CTA ID, operator/home point, and wardragon-detection provenance. | IMG-012 |

## Requirement groups

### P0: build first

- Live COP map shell with toolbar/status.
- Entity Explorer and selected-entity detail panel.
- Robust entity component rendering: handle missing location, milView, ontology, health, payloads, taskCatalog, media, and provenance.
- Entity action menu: follow, anchor, copy, star, task launcher.
- Task catalog-derived task launcher.
- Task Details panel with draft/execute/discard/status workflow.
- Bearing/range and task geometry overlays.
- Disposition/threat coloring.
- Bottom status bar with live state, cursor, and last event.

### P1: add after fixture-driven P0

- Multi-selection panel and map/card selection entrypoints.
- Bulk metadata edit.
- Group creation, add-to-group, ungroup confirmation.
- Starred panel.
- Payloads, data overrides, object/media panel.
- Geo-zone overlays, clusters, task cards, conflict prompts.

### P2: later / specialized

- C-UAS engagement queue.
- Sensor coverage overlays.
- Emergency-stop/abort UI for simulated control paths only.
- Remote ID / wardragon-specific metadata cards.

## Draft data model

The sibling file `zorn_lattice_ui_proto_requirements.proto` defines a first-pass UI-state contract for:

- `CopViewState`
- `EntitySummary`
- `EntityDetail`
- `TaskSummary`
- `TaskDetail`
- `SelectionSet`
- `EntityGroup`
- `StarredEntity`
- `ObjectRef`
- `MapOverlay`
- `OperatorActionLog`

This is intentionally **not** an Anduril API proto. It is a Zorn UI-facing projection model that can be populated from the Lattice surrogate state store.

## Traceability notes

- Requirements linked only to `SRC-*` and `IMG-*` IDs should be treated as traceable but not yet executable.
- Requirements should become executable once a fixture or mocked event stream can produce the data path.
- Any requirement supported only by `SRC-010` or `SRC-011` should remain P2 unless confirmed by official docs or a sample app.

## Next actions

1. Capture screenshots directly from official docs pages into a local evidence folder if licensing/use permits.
2. Add each `REQ-*` item to the Zorn issue tracker with source IDs and acceptance criteria.
3. Implement a minimal `CopViewState` projection from Zorn entity stream events.
4. Build the first P0 UI shell against generated fixtures: AIS REST/gRPC + entity visualizer + Maven stream model.
5. Convert P0 acceptance criteria into Playwright visual/interaction tests.
