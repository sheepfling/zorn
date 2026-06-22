# Zorn

Local Zorn compatibility sandbox for Lattice-oriented REST, gRPC, proto, task,
entity, and object workflow experiments.

## Alpha 1 Status

Alpha 1 is the DIS-app readiness baseline. It is meant to be cloned elsewhere
and used as the source of truth while testing an external FastDIS/DIS plugin.

Alpha 1 does **not** introduce a new server API for DIS. DIS-style adapters
publish through the existing public Zorn/Lattice-compatible surfaces:

- `PUT /api/v1/entities`
- `POST /api/v1/entities/events`
- `POST /api/v1/tasks`
- `PUT /api/v1/tasks/{task_id}/status`
- `PUT /api/v1/tasks/{task_id}/cancel`
- `POST /api/v1/objects/{object_path}`
- `DELETE /api/v1/objects/{object_path}`

The repo includes replay tooling and fixtures that exercise those public routes:

- DIS Entity State JSONL -> Entity publish/events.
- Entity/Task/Object JSONL replay logs.
- Pass/fail/missing reports for replay runs.

FastDIS and other plugins should prefer API verification over CLI report files:

- `GET /healthz/details`
- `GET /api/v1/entities/events/snapshot`
- `GET /api/v1/tasks/events/snapshot`
- `GET /api/v1/verification/state`
- `GET /api/v1/backend/capabilities`
- `GET /api/v1/backend/compatibility`

## Start Here

- `src/zorn/` contains the reusable surrogate logic.
- `scripts/` contains repo workflow entrypoints.
- `docs/` contains repo notes and backlog plans.
- `tests/` contains the verification suite.
- `artifacts/` is the repo-local output surface and stays out of git.
- `INTAKE/` is the holding area for raw inputs and notes.

## Quick Start

1. Install `uv` and Python 3.12+.
2. Run `uv sync --extra dev --extra grpc`.
3. Run `.venv/bin/python -m pytest tests/test_public_api_replay.py tests/test_dis_entity_state_adapter.py tests/test_entities.py tests/test_tasks.py tests/test_objects.py`.
4. Start the REST API:

   ```bash
   C2_COMPAT_AUTH_MODE=none .venv/bin/uvicorn zorn.main:app --host 127.0.0.1 --port 8080
   ```

5. In another shell, run the Alpha 1 replay checks:

   ```bash
   .venv/bin/zorn replay dis tests/fixtures/dis/entity_state_replay.jsonl \
     --target http://127.0.0.1:8080 \
     --report /tmp/zorn-alpha1-dis-report.json

   .venv/bin/zorn replay api tests/fixtures/replay/entity_task_object_api.jsonl \
     --target http://127.0.0.1:8080 \
     --report /tmp/zorn-alpha1-api-report.json
   ```

For gRPC work, run `make grpc-run` in a separate shell after installing the grpc
extra.

## Validation

- `.venv/bin/python -m pytest`
- `.venv/bin/ruff check .`
- `.venv/bin/mypy src tests scripts`
- `.venv/bin/python scripts/proto_contract_report.py --assert --pretty`

The proto contract uses the official Buf-generated Lattice Python packages. Zorn
does not maintain hand-written replacement protobuf files.

## Layout

- `src/zorn/` keeps the Python package and REST/gRPC implementations.
- `proto/` documents the official Buf proto source of truth.
- `docs/manifests/` contains REST, gRPC, proto, and integration registry manifests.
- `docs/design/alpha-readiness-roadmap.md` defines Alpha 1/2/3 readiness gates.
- `docs/plans/active/` tracks active work packets.
- `tests/fixtures/dis/` contains the Alpha 1 DIS Entity State replay fixture.
- `tests/fixtures/replay/` contains public Entity/Task/Object API replay logs.
- `scripts/workflow_bootstrap.py` owns the repo root and cache-root setup.
- `.venv`, `.cache`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `cache`, and
  `archive` are expected to be symlinked to the local cache tree.

## Initial Scope

The repo now includes a local compatibility surface for:

- entity publish/read/stream behavior,
- task create/status/listen/stream behavior,
- object upload/download/list/delete behavior,
- OAuth-dev/static/no-auth REST modes,
- official Lattice EntityManagerAPI and TaskManagerAPI gRPC/proto contract checks.

## External DIS Plugin Contract

An external DIS/FastDIS plugin should treat Zorn as an HTTP API target:

1. Parse DIS/PCAP/FastDIS input outside this repo.
2. Map Entity State PDUs into normal entity payloads.
3. Publish through `PUT /api/v1/entities`.
4. Verify stream behavior through `POST /api/v1/entities/events` or
   `POST /api/v1/entities/stream`.
5. Use existing Task and Object routes for task lifecycle and media/object replay.
6. Verify backend state through `GET /api/v1/verification/state` and event
   snapshots rather than treating replay reports as the source of truth.

The in-repo JSONL fixtures are examples of the expected payload shape and report
format; they are not a new public DIS API.
