#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

BSR_MODULE="${C2_COMPAT_LATTICE_BSR_MODULE:-buf.build/anduril/lattice-sdk}"
BSR_REF="${C2_COMPAT_LATTICE_BSR_REF:-ed34febdefc1}"
OUT_DIR="${C2_COMPAT_LATTICE_PROTO_OUT:-vendor/lattice-sdk-protos}"
MODULE_REF="${BSR_MODULE}:${BSR_REF}"

if ! command -v buf >/dev/null 2>&1; then
  echo "buf CLI is required. Install it from https://buf.build/docs/installation/" >&2
  exit 127
fi

rm -rf "${OUT_DIR}"
mkdir -p "${OUT_DIR}"

buf export "${MODULE_REF}" \
  --path anduril/entitymanager/v1 \
  --path anduril/taskmanager/v1 \
  --path anduril/tasks \
  -o "${OUT_DIR}"

cat > "${OUT_DIR}/SOURCE.txt" <<EOF
source=${MODULE_REF}
exported_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)

These files are exported for local inspection only. Do not edit them by hand;
use the Buf-generated packages as the runtime/server contract.
EOF

echo "Exported official Lattice protos to ${OUT_DIR} from ${MODULE_REF}"
