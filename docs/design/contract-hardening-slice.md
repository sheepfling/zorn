# Contract hardening slice

This slice moves the local mock from "plausible local REST server" toward an SDK-contract target.
The codename remains runtime-configurable through `C2_COMPAT_PRODUCT_NAME`; route paths, environment prefixes, package names, and table names do not depend on the codename.

## Implemented compatibility improvements

### Entities

- `POST /api/v1/entities/events` now returns both the public-style `sessionToken`/`entityEvents` envelope and the previous helper `events` alias.
- Entity event polling accepts `sessionToken`, `afterSequence`, or `fromSequence`.
- Entity event polling and streaming support `componentsToInclude`.
- `POST /api/v1/entities/stream` supports `heartbeatIntervalMS`, `heartbeatIntervalMs`, and `preExistingOnly`.
- Entity publishing preserves unknown fields.
- Entity publishing optionally ignores stale updates when both existing and incoming payloads provide `provenance.sourceUpdateTime`.

### Tasks

- `POST /api/v1/tasks` now returns `201 Created`.
- Created tasks receive a public-style `version.taskId`, `version.definitionVersion`, `version.statusVersion`, `createTime`, `lastUpdateTime`, and default `status.status = STATUS_CREATED`.
- `relations.assignee.system.entityId` and related assignee shapes are used for task routing.
- `POST /api/v1/agent/listen` now returns a single JSON task request or heartbeat instead of acting as an SSE alias.
- `POST /api/v1/agent/stream` remains the SSE task-request stream.
- Task streams support `heartbeatIntervalMs` and `excludePreexistingTasks`.

### Objects

- `GET /api/v1/objects` now returns `path_metadatas` and `next_page_token`, plus a backward-compatible `objects` alias.
- `POST /api/v1/objects/{objectPath}` now returns public-style `content_identifier`, `size_bytes`, `last_updated_at`, and `expiry_time`, plus local helper aliases.
- Object paths are checked against the public path-character pattern.
- `Time-To-Live` supports nanosecond-style values while still accepting small second-style local-test values.
- `HEAD /api/v1/objects/{objectPath}` returns `Path`, `Checksum`, `Last-Modified`, `Expires`, `Content-Length`, and local helper headers.

## Still intentionally simplified

- The server is schema-preserving, not schema-complete.
- Unknown entity/task fields are accepted and round-tripped instead of exhaustively modeled.
- Manual-control streaming currently emits heartbeats only.
- Object pagination accepts page tokens but does not yet implement cursors.
- gRPC is represented in manifests only; service implementations are a later slice.

## New contract tests

`tests/test_contract_shapes.py` covers:

- Entity polling envelope and component filtering.
- Entity stream `preExistingOnly` behavior.
- `provenance.sourceUpdateTime` stale-update rejection.
- Task default shape and agent-listen routing.
- Object upload/list metadata envelopes.
