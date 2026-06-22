# Proto-compliance development slice

This slice tightens the gRPC layer around the official public Buf-generated Lattice artifacts instead of local replacement schemas.

## Added guarantees

```text
- The server imports the public Buf-generated EntityManager and TaskManager service modules.
- Startup verifies the pinned generated package versions.
- Startup verifies service full names, RPC names, request/response message full names, and stream cardinality.
- The request/response message modules are loaded separately from the service descriptor modules.
- A JSON contract report can be emitted for CI and release artifacts.
- Local proto snapshots can be exported for inspection, but are not used as runtime source of truth.
```

## Behavioral tightening

```text
- gRPC PublishEntity maps entity validation failures to INVALID_ARGUMENT.
- gRPC PublishEntities accepts streaming writes and suppresses per-entity validation feedback.
- gRPC CreateTask defaults to STATUS_SENT.
- Task status updates support optimistic status-version enforcement.
- StreamTasks and ListenAsAgent include basic filtering and heartbeat support.
- StreamEntityComponents supports preexisting state, component filtering, heartbeat control, and entity ID filters.
- JSON-to-protobuf bridging is descriptor-aware and preserves unknown Any payloads as opaque JSON bytes.
```

## Still not complete

```text
- Official sample-app gRPC runners still need to be executed against localhost.
- Advanced filter semantics are partial.
- Manual-control frame payloads need contract tests against real generated message shapes.
- The local store is compatibility-oriented and does not implement proprietary Lattice internals.
```
