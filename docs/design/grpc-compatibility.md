# gRPC compatibility

Zorn's gRPC layer is intentionally built around the official public Lattice protobuf artifacts rather than local, hand-written `.proto` copies.

The compatibility rule is:

```text
Buf-generated Lattice protos are the contract.
Zorn implements server behavior behind those generated service classes.
```

This keeps the mock from drifting away from the public SDK contract. Package upgrades are explicit: update the Buf-generated dependency pins, run the proto contract report, then update compatibility notes and tests.

## Pinned generated artifacts

The gRPC optional dependencies are pinned in `pyproject.toml` and sourced from Buf's generated Python package index:

```bash
uv sync --extra test --extra grpc
```

The exact current pins are:

```text
anduril-lattice-sdk-grpc-python==1.80.0.1.20260515215502+ed34febdefc1
anduril-lattice-sdk-protocolbuffers-python==34.1.0.1.20260515215502+ed34febdefc1
anduril-lattice-sdk-protocolbuffers-pyi==34.1.0.1.20260515215502+ed34febdefc1
grpcio==1.80.0
protobuf==7.34.1
```

The package source is:

```text
https://buf.build/gen/python
```

Do not install similarly named third-party packages from random indexes. The official generated packages should come from Buf.

## Proto contract verification

Run the contract reporter before starting a gRPC server or after bumping any generated package:

```bash
python scripts/proto_contract_report.py --assert --pretty
```

The reporter checks:

- installed generated package versions;
- loaded Python module names;
- service full names;
- method names;
- request and response message full names;
- unary/client-stream/server-stream cardinality;
- descriptor fingerprints.

The server also runs the service/method/cardinality assertion at startup. Strict startup auditing is enabled by default and can be temporarily disabled for local debugging with:

```bash
C2_COMPAT_GRPC_STRICT_PROTO_AUDIT=false
```

That flag should stay enabled for contract tests and sample-app compatibility runs.

## Service proto files

The public Buf module separates request/response API files from service files. The loader imports both groups and does not assume service descriptors live in the request/response module.

```text
anduril/entitymanager/v1/entity_manager_api.pub.proto
anduril/entitymanager/v1/entity_manager_grpcapi.pub.proto
anduril/taskmanager/v1/task_manager_api.pub.proto
anduril/taskmanager/v1/task_manager_grpcapi.pub.proto
```

To export the official `.proto` files for local inspection without committing them:

```bash
./scripts/sync_official_lattice_protos.sh
```

The export defaults to:

```text
buf.build/anduril/lattice-sdk:ed34febdefc1
```

## Start the REST and gRPC processes

Use one database URL for both processes if you want REST and gRPC to share state.

```bash
C2_COMPAT_PRODUCT_NAME=Zorn \
C2_COMPAT_AUTH_MODE=none \
C2_COMPAT_DATABASE_URL=sqlite:///./var/zorn.db \
uv run uvicorn zorn.main:app --reload --port 8080
```

In another terminal:

```bash
C2_COMPAT_PRODUCT_NAME=Zorn \
C2_COMPAT_DATABASE_URL=sqlite:///./var/zorn.db \
uv run zorn-grpc
```

Then run:

```bash
uv run python scripts/grpc_smoke.py --target 127.0.0.1:50051
```

## TLS for local tests

Most local SDK smoke tests can use an insecure channel. For TLS behavior:

```bash
./scripts/make_dev_tls.sh

C2_COMPAT_GRPC_USE_TLS=true \
C2_COMPAT_GRPC_TLS_CERT_PATH=var/certs/server.pem \
C2_COMPAT_GRPC_TLS_KEY_PATH=var/certs/server-key.pem \
uv run zorn-grpc

uv run python scripts/grpc_smoke.py \
  --target localhost:50051 \
  --tls \
  --ca-file var/certs/dev-ca.pem
```

## Implemented services

Zorn registers these generated service names from the official Buf artifacts:

```text
anduril.entitymanager.v1.EntityManagerAPI
anduril.taskmanager.v1.TaskManagerAPI
```

Implemented method skeletons:

```text
EntityManagerAPI
  PublishEntity
  PublishEntities
  GetEntity
  OverrideEntity
  RemoveEntityOverride
  StreamEntityComponents

TaskManagerAPI
  CreateTask
  GetTask
  QueryTasks
  UpdateStatus
  CancelTask
  ListenAsAgent
  ListenForManualControlFrames
  StreamTasks
```

## Current limits

The gRPC layer is a compatibility facade over the current REST/domain stores. It does not yet implement every filter, selector, task specification, or stream envelope exactly. The response bridge now strips local/private fields before strict protobuf JSON parsing and only falls back to lenient parsing if strict parsing fails.

The current hardening suite also includes descriptor-audit unit tests that simulate missing public RPCs and verify that the contract checker rejects them.

The next hardening step is to run official public gRPC sample apps against the local endpoint and patch differences as contract failures, not guesses.
