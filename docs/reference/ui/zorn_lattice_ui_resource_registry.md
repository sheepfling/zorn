# Zorn Lattice UI Resource Registry

Generated: 2026-06-21

Purpose: catalog public UI references for Anduril Lattice/Lattice Sandbox and translate observed operator-facing features into Zorn proto/API requirements.

Confidence levels:
- Observed: directly visible in a public image/screenshot/video frame.
- Public-text: stated in public docs/article text, not necessarily visible in UI.
- Inferred: reasonable requirement inferred from repeated UI patterns; do not claim as exact Lattice behavior.

## Resource registry

| ID | Source / resource | Resource type | Confidence | Observed UI features | Zorn implications |
|---|---|---|---|---|---|
| UI-001 | Lauren Park Anduril portfolio: multi-selection/grouping UI | Portfolio screenshots | Observed, but portfolio context needs caution | Dark map, clustered entity markers, multi-selection drawer, search, sort, refine selection, selected objects list, live status, bulk action button, warning modal for ungrouping, snack/toast feedback | Need bulk selection model, group/ungroup operations, query/sort/filter state, entity live/stale state, UI confirmation/action audit events |
| UI-002 | WIRED ABMS Lattice demo imagery | Photo/article | Observed + article context | Large wall display, Lattice-branded map, grid overlay, track/vehicle labels, curved engagement/coverage arcs, left asset/details panel, ownership prompt before issuing commands, operator workstations | Need authority/ownership/lease primitive before commands; map overlays; panelized entity detail; command gating; multi-operator session awareness |
| UI-003 | Anduril Desert Guardian 1.0 article imagery | Company article screenshots | Observed | Satellite map, red hostile air vehicles, dashed flight paths, sensor/engagement zones, Roadrunner task cards, engagement progress percentages, armed/warhead status, RTB/Loiter/Scuttle controls | Need task cards, task progress, task control actions, effector readiness/safety status, hostile track rendering, zones/corridors, engagement lifecycle |
| UI-004 | Anduril IBCS-M article imagery | Company article screenshot | Observed | Satellite map, many air tracks, friendly/hostile/unknown icons, sensor cones, defended area polygon, right engagement queue, pending/current/complete task sections, asset launch countdowns, E-stop controls, classify/engage actions | Need engagement queue proto, effector assignment, launch/countdown state, emergency stop command, track classification workflow, defended-area overlays, sensor coverage overlays |
| UI-005 | Developer sample apps overview / tasking sample screenshot | Official developer docs | Observed + public docs | Map tasking interface, selected asset details, speed/heading/location/altitude, objective target, investigate task, edit/complete/cancel controls | Need generic Task, TaskObjective, TaskTarget, TaskStatus, asset state, command controls, selected entity detail drawer |
| UI-006 | Wind River Lattice Sandbox screenshots | Partner blog screenshots | Observed | Sandbox header, live mode, left SPI/entity data panel, simulated generated data, payloads, data overrides, task dropdown, dark map, 3D toggle, cursor coordinates, task form with BDA, standoff distance, target selection prompt, discard/execute | Need sandbox/dev mode, simulation flag, payload component, data overrides, task parameter schema, 3D mode flag, cursor coordinates, target point selection |
| UI-007 | Anduril SDK sample apps and docs | Official developer docs | Public-text | Entities, Tasks, Objects, thumbnails, simulated AIS/asset workflows, entity visualizer map | Need SDK-compatible endpoints plus UI backed by entity stream, task lifecycle, object/media attachment |

## Derived operator feature taxonomy

### Map and overlays
- Base map: satellite/dark/vector modes.
- Grid/coordinate overlay.
- 2D/3D toggle.
- Cursor coordinate readout.
- Entity markers, icons, headings, trails, dashed paths.
- Cluster markers / count bubbles.
- Sensor cones, coverage zones, defended areas, loiter zones, engagement corridors.

### Entity browsing and detail
- Left entity/SPI panel.
- Entity list with search, sort, refine selection, live status.
- Multi-select and bulk action.
- Entity details: domain, type, disposition, speed, heading, altitude, position, created/last-updated, source/sensor, provenance, payloads, data overrides.

### Tasking and autonomy
- Right task panel / task cards.
- Task states: pending, current, complete.
- Task progress percentage.
- Task target selection from map.
- Task parameters such as standoff distance.
- Commands: execute, edit, complete, cancel, RTB, loiter, scuttle.
- Agent/asset readiness and payload/warhead/armed state.

### Engagement / effects
- Classify/engage workflow.
- Launch countdown or time-to-target.
- Effector assignment.
- Emergency stop.
- Hostile/unknown/friendly visual distinction.
- Safety/readiness gates.

### Collaboration and authority
- Ownership prompt before issuing commands.
- Likely multi-operator session state.
- Command authorization and audit trail.
- Confirmation modals and action feedback.

## Proto/API requirement draft

These are Zorn requirements, not claims of exact Anduril protobuf names.

### zorn.ui.v1.ViewState
- session_id: string
- operator_id: string
- mode: LIVE | REPLAY | SANDBOX
- map_mode: SATELLITE | DARK | VECTOR
- dimension_mode: MAP_2D | MAP_3D
- camera: MapCamera
- selected_entity_ids: repeated string
- selected_task_ids: repeated string
- active_panel: enum
- cursor_position: GeoPoint optional

### zorn.entity.v1.EntitySummary
- entity_id: string
- display_name: string
- domain: AIR | SURFACE | SUBSURFACE | LAND | SPACE | UNKNOWN
- entity_type: string
- disposition: FRIENDLY | ASSUMED_FRIENDLY | NEUTRAL | UNKNOWN | SUSPECT | HOSTILE
- live_state: LIVE | STALE | EXPIRED | SIMULATED
- position: GeoPoint
- kinematics: Kinematics
- created_at: Timestamp
- last_updated_at: Timestamp
- source_refs: repeated SourceRef
- provenance: Provenance
- visual: EntityVisual

### zorn.entity.v1.EntitySelection
- selection_id: string
- entity_ids: repeated string
- query: string
- sort: SortSpec
- filters: repeated FilterSpec
- group_id: string optional
- count: int32

### zorn.entity.v1.EntityGroup
- group_id: string
- display_name: string
- entity_ids: repeated string
- created_by: string
- created_at: Timestamp
- membership_rule: string optional

### zorn.task.v1.Task
- task_id: string
- task_type: INVESTIGATE | BDA | LOITER | RETURN_TO_BASE | SCUTTLE | ENGAGE | TRACK | CUSTOM
- status: DRAFT | PENDING | ASSIGNED | ACCEPTED | EXECUTING | COMPLETED | CANCELLED | FAILED
- assignee_entity_id: string optional
- target_entity_id: string optional
- target_point: GeoPoint optional
- objective: string
- parameters: google.protobuf.Struct
- progress: double
- created_by: string
- created_at: Timestamp
- updated_at: Timestamp

### zorn.effects.v1.Engagement
- engagement_id: string
- target_entity_id: string
- effector_entity_id: string
- status: PENDING | QUEUED | LAUNCHING | IN_FLIGHT | INTERCEPTING | COMPLETE | ABORTED | FAILED
- readiness: NOT_READY | READY | ARMED | SAFE | UNKNOWN
- time_to_launch: Duration optional
- time_to_target: Duration optional
- progress: double
- safety_state: NORMAL | HOLD | ESTOP_REQUESTED | ESTOPPED
- command_refs: repeated string

### zorn.overlay.v1.Overlay
- overlay_id: string
- overlay_type: SENSOR_CONE | DEFENDED_AREA | LOITER_ZONE | ENGAGEMENT_CORRIDOR | ROUTE | GEOFENCE | GRID
- geometry: Geometry
- owner_entity_id: string optional
- style: OverlayStyle
- validity_interval: TimeInterval optional

### zorn.command.v1.CommandLease
- lease_id: string
- resource_id: string
- resource_type: ENTITY | TASK | ENGAGEMENT | GROUP | OVERLAY
- operator_id: string
- expires_at: Timestamp
- permissions: repeated string

### zorn.command.v1.Command
- command_id: string
- command_type: TAKE_OWNERSHIP | RELEASE_OWNERSHIP | CREATE_TASK | UPDATE_TASK | CANCEL_TASK | COMPLETE_TASK | CLASSIFY | OVERRIDE_ENTITY | ENGAGE | ESTOP | BULK_UPDATE | GROUP | UNGROUP
- actor_operator_id: string
- target_ids: repeated string
- lease_id: string optional
- parameters: google.protobuf.Struct
- requires_confirmation: bool
- created_at: Timestamp

### zorn.stream.v1.UiEvent
- event_id: string
- event_type: ENTITY_CREATED | ENTITY_UPDATED | ENTITY_DELETED | TASK_UPDATED | ENGAGEMENT_UPDATED | OBJECT_ATTACHED | OVERLAY_UPDATED | SELECTION_UPDATED | COMMAND_ACK | COMMAND_REJECTED | ALERT_RAISED | TOAST
- entity: EntitySummary optional
- task: Task optional
- engagement: Engagement optional
- overlay: Overlay optional
- command_result: CommandResult optional
- occurred_at: Timestamp

## Implementation priorities from UI registry

P0:
- Entity detail panel backing model.
- Live entity stream to UI.
- Task card model and lifecycle.
- Command lease/ownership before commands.
- Basic overlays: routes, zones, sensor cones.

P1:
- Multi-selection, groups, bulk actions.
- Engagement queue and effector state.
- Data overrides and provenance display.
- Payload/media attachment.

P2:
- 3D camera mode.
- Timeline/replay scrubbing.
- Multi-operator collaborative UI state.
- Advanced styling and tactical-symbol renderer.
