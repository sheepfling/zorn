#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-127.0.0.1:50051}"

if ! command -v grpcurl >/dev/null 2>&1; then
  echo "grpcurl is required for this check." >&2
  exit 2
fi

grpcurl -plaintext "${TARGET}" list
grpcurl -plaintext "${TARGET}" list anduril.entitymanager.v1.EntityManagerAPI
grpcurl -plaintext "${TARGET}" describe anduril.taskmanager.v1.TaskManagerAPI
