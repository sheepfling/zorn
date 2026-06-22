#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

python -m pip install -r requirements/grpc-runtime.txt
python -m pip install -r requirements/lattice-buf-generated.txt
PYTHONPATH="${ROOT_DIR}/src:${PYTHONPATH:-}" python scripts/proto_contract_report.py --assert --pretty
