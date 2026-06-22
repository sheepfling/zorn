#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8080}"

curl -s -X PUT "$BASE_URL/api/v1/entities" \
  -H 'Content-Type: application/json' \
  -d '{"entityId":"asset-alpha","isLive":true,"description":"demo asset"}'

echo
curl -s "$BASE_URL/api/v1/entities/asset-alpha"
echo
