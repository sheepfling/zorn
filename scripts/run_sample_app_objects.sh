#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SAMPLE_DIR="${ZORN_SAMPLE_APP_OBJECTS_DIR:-${ROOT_DIR}/cache/sample-app-objects}"
TARGET_URL="${ZORN_REST_BASE_URL:-http://127.0.0.1:8080}"
TOKEN="${ZORN_DEV_TOKEN:-dev-token}"

if [[ ! -d "${SAMPLE_DIR}" ]]; then
  cat >&2 <<EOF
sample-app-objects is not present at:
  ${SAMPLE_DIR}

Clone or unpack the official sample app there, or set ZORN_SAMPLE_APP_OBJECTS_DIR.
The harness will pass endpoint/token environment variables only; it will not patch sample source.
EOF
  exit 2
fi

cd "${SAMPLE_DIR}"
export LATTICE_BASE_URL="${TARGET_URL}"
export LATTICE_API_URL="${TARGET_URL}"
export LATTICE_TOKEN="${TOKEN}"
export AUTH_TOKEN="${TOKEN}"

if [[ -x ./smoke.sh ]]; then
  ./smoke.sh
elif [[ -f Makefile ]]; then
  make smoke
else
  echo "No known sample-app-objects smoke entrypoint found." >&2
  exit 2
fi
