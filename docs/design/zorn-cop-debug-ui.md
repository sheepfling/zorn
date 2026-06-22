# Zorn COP/Debug UI Plan

Zorn needs working product apps, not a landing page. The UI layer is parallel to
the Lattice-compatible data plane: it consumes Entities, Tasks, Objects, auth,
and streams, but it does not define or modify those contracts.

The first UI should be a dense developer console because it directly supports
compatibility work. A `/c2` operator view follows once the debug surfaces are
useful enough to make entity/task/object behavior visible.

## Contract First

The UI contract is Zorn-owned and separate from public Lattice API protos:

- Reference evidence lives in `docs/reference/ui/`.
- The projection proto lives in `proto/zorn/ui/v1/ui.proto`.
- The implementation backlog lives in `cert/ui/requirements.yaml`.

The proto is a UI projection model. It should be generated from Zorn state and
event logs, never treated as a replacement for official SDK compatibility. UI
state such as selected entity, pinned panels, map viewport, layer set, saved
views, debug bookmarks, and scenario timeline position stays in the UI/app
layer.

## Milestones

### UI-0: registry and projection contract

Preserve the UI registry and pin the first projection model. This is the current
slice and gives the repo a concrete UI requirements artifact.

Acceptance:

- UI reference registries are committed under `docs/reference/ui`.
- `zorn.ui.v1` projection proto is present under `proto/zorn`.
- Tests prove the contract files and P0 requirements exist.

### UI-1: developer console read model

Expose a UI-facing read model for `/developer-console` without expanding the
Lattice-compatible API. The UI can use in-process adapters, local app state,
scenario files, certification reports, and existing Entity/Task/Object/Auth
surfaces. It must not create a new third-party integration contract.

### UI-2: `/developer-console`

Build the first usable browser UI for debugging and validation:

- Entity explorer/table with search, sort, and copy ID.
- Entity detail panel with raw JSON/proto projection.
- Task explorer with lifecycle, payload, assignee, and status history.
- Object explorer with metadata, links, download/delete, and thumbnail preview.
- Stream event log for debugging fixture behavior.
- Schema/shape validation for SDK sample payloads.
- Live status bar with event timing and reconnect state.

This should be fixture-driven by AIS REST/gRPC and the entity visualizer proof
path.

### UI-3: `/c2` operator COP

Build the map-first operator view from the same data plane:

- Map canvas with entity markers and disposition styling.
- Selected entity panel with location, provenance, health, media, and relations.
- Task catalog actions from selected assets.
- Task draft, execute, discard, cancel, complete, and status update views.
- Task geometry overlays between asset and objective.
- Object browser with metadata, thumbnails, download/delete, and entity linkage.

### UI-4: visual certification

Add Playwright tests and screenshots for browser-visible proof:

- Entity markers render for fixture-published entities.
- Selection opens the correct detail panel.
- Taskable assets expose task actions.
- Object media links survive refresh.
- BA/ADS scenario snapshots are deterministic.

### UI-5: plugin panels

Once the core shell works, add plugin registration for adapters, scenarios, and
agents. A plugin should declare panel id, data dependencies, optional overlays,
and failure isolation behavior.

## Design Constraints

- Build the actual tool as the first screen.
- Keep the interface operational and information-dense.
- Avoid decorative marketing layouts.
- Use stable panel dimensions and predictable controls.
- Prioritize scanability over visual drama.
- Treat Playwright screenshots as certification artifacts, not just frontend QA.
