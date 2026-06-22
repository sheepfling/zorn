# gRPC proto compliance checklist

The goal is strict public-proto compatibility, not a local approximation.
Every gRPC compatibility change should preserve these rules:

```text
1. Runtime message and service classes come from the official Buf-generated packages.
2. Local hand-written `.proto` files are never used as the server contract.
3. Service full names, RPC names, request/response message full names, and streaming cardinality are audited before server registration.
4. The pinned Buf package versions are explicit and reproducible.
5. Exported `.proto` files are inspection/vendor artifacts only; they are not edited.
6. Behavior differences between REST and gRPC are represented at the facade boundary.
```

## Required checks

Run these locally before packaging a gRPC change:

```bash
pytest
python -m compileall -q src tests scripts
python scripts/proto_contract_report.py --assert --pretty
```

The proto report requires the Buf-generated packages to be installed. Without those packages, it exits with an actionable dependency message rather than falling back to local stand-ins.

## Compatibility-sensitive behaviors already modeled

```text
EntityManagerAPI.PublishEntities
  Client-streaming request; no locally invented request batching schema.

EntityManagerAPI.StreamEntityComponents
  Server-streaming response; preexisting live entities first; optional heartbeat only when requested.

TaskManagerAPI.CreateTask
  gRPC facade initializes tasks as STATUS_SENT.

REST POST /api/v1/tasks
  REST facade keeps STATUS_CREATED behavior.

TaskManagerAPI.UpdateStatus
  Enforces statusVersion by default and rejects stale status updates.

TaskManagerAPI.CancelTask
  gRPC cancellation maps to STATUS_DONE_NOT_OK with ERROR_CODE_CANCELLED.

TaskManagerAPI.ListenAsAgent
  Server-streaming agent request wrapper with ExecuteRequest, CancelRequest, CompleteRequest, and optional heartbeat.

TaskManagerAPI.ListenForManualControlFrames
  Server-streaming manual-control frames; stream exits once the task is terminal.
```

## Rename safety

The compatibility layer intentionally avoids hardcoding the project codename in proto paths, Python packages, database tables, or service registration. Product naming remains runtime configuration through `C2_COMPAT_PRODUCT_NAME`.
