# Alpha 1 Closeout Checklist

## Goal

Alpha 1 closes only when Zorn is a strict public-Lattice surrogate at the
data-plane layer:

- public Entities, Tasks, Objects, OAuth-dev, REST, and public Buf-generated
  gRPC for Entities and Tasks
- no invented runtime surfaces
- no adapter-specific runtime namespace in the Zorn package
- proof comes from tests, certification artifacts, and startup constraints

## Required Evidence

### 1. Public-surface validation is green

Required proof:

- full repo test suite passes
- lint passes
- type checking passes
- `zorn-cert validate-contracts` passes

Current evidence:

- `.venv/bin/python -m pytest`
- `.venv/bin/python -m ruff check .`
- `.venv/bin/python -m mypy src tests eval_dis`
- `.venv/bin/zorn-cert validate-contracts`

### 2. Entity parity is closed across REST and gRPC

Required proof:

- REST publish -> gRPC read/stream
- gRPC publish -> REST read/events
- REST override -> gRPC read
- gRPC override -> REST read
- REST remove-override -> gRPC read
- gRPC remove-override -> REST read
- REST non-live -> gRPC read
- gRPC non-live -> REST read

Current evidence:

- `tests/compat/test_transport_parity.py`

### 3. OAuth-dev lifecycle is real enough for Alpha 1

Required proof:

- issued tokens are distinct from configured static tokens in strict mode
- expiry is enforced
- strict startup requires trust seed, positive TTL, sandbox enforcement, proto
  audit, strict token mode, informational scope mode, and strict-separate gRPC
  sandbox auth mode
- REST and gRPC both validate issued tokens correctly

Current evidence:

- `tests/test_lattice_boundary_hardening.py`
- `tests/compat/test_grpc_python_client.py`
- `docs/design/strict-startup-contract.md`

### 4. Adapter and replay behavior stays outside the core runtime

Required proof:

- no adapter-specific runtime route
- no `zorn.adapters` namespace in the importable package
- evaluation helpers drive only the public API

Current evidence:

- `tests/test_zorn_package_boundary.py`
- `tests/test_public_api_replay.py`
- `tests/test_dis_entity_state_adapter.py`

### 5. Certification corpus is green except explicit environment blockers

Required proof:

- all generated cert reports are `pass` except documented environment/toolchain
  blockers

Current evidence:

- `cert/lattice/reports/`

## Accepted Environment Blocker

The only accepted non-pass Alpha 1 report is:

- `sdk-cpp-grpc-smoke`

Reason:

- it requires system C++ gRPC/protobuf development packages
- the current report must stay `blocked` only for missing local toolchain
  prerequisites, not for a Zorn protocol mismatch

## Accepted Defers

These do not block Alpha 1 closeout unless a public client proves they are
required:

- refresh-token support
- richer vendor-like OAuth policy beyond current coarse route-level scope
  enforcement for issued tokens
- vendor-only auth/session claims
- proprietary mesh behavior
- UI and scenario features inside the compatibility layer

## Exit Rule

Alpha 1 is closed when:

1. all required evidence above remains green
2. `sdk-cpp-grpc-smoke` is the only non-pass report
3. its `blocked` reason is toolchain-only
4. accepted defers remain documented and do not silently expand into runtime
   API surface
