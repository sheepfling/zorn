# Zorn

Local Zorn compatibility sandbox for Lattice-oriented REST, gRPC, proto, task,
entity, and object workflow experiments.

## Start Here

- `src/zorn/` contains the reusable surrogate logic.
- `scripts/` contains repo workflow entrypoints.
- `docs/` contains repo notes and backlog plans.
- `tests/` contains the verification suite.
- `artifacts/` is the repo-local output surface and stays out of git.
- `INTAKE/` is the holding area for raw inputs and notes.

## Quick Start

1. Run `uv sync --extra grpc --extra dev`.
2. Run `.venv/bin/python scripts/all.py`.
3. Run `.venv/bin/python scripts/proto_contract_report.py --assert --pretty`.
4. Run `make run` for the REST API or `make grpc-run` for the gRPC API.

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
- `docs/plans/active/` tracks active work packets.
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
