#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

./scripts/install_grpc_deps.sh
PYTHONPATH="${ROOT_DIR}/src:${PYTHONPATH:-}" python - <<'PY'
from zorn.grpc_api.contract import assert_lattice_grpc_contract
from zorn.grpc_api.proto_modules import load_lattice_proto_modules

modules = load_lattice_proto_modules()
assert_lattice_grpc_contract(modules)
print("Loaded official Buf-generated Lattice gRPC artifacts:")
for key, value in modules.module_names().items():
    print(f"  {key}: {value}")
####
PY
