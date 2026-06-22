#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/docs/upstream/anduril"
mkdir -p "${OUT_DIR}"

fetch() {
  local url="$1"
  local out="$2"
  curl -fsSL "$url" -o "${OUT_DIR}/${out}"
}

fetch "https://developer.anduril.com/guides/concepts/overview.md" "concepts-overview.md"
fetch "https://developer.anduril.com/reference/rest/entities/publish-entity.md" "rest-entities-publish.md"
fetch "https://developer.anduril.com/reference/rest/entities/stream-entities.md" "rest-entities-stream.md"
fetch "https://developer.anduril.com/reference/rest/entities/long-poll-entity-events.md" "rest-entities-events.md"
fetch "https://developer.anduril.com/reference/rest/tasks/create-task.md" "rest-tasks-create.md"
fetch "https://developer.anduril.com/reference/rest/tasks/query-tasks.md" "rest-tasks-query.md"
fetch "https://developer.anduril.com/reference/rest/tasks/stream-tasks.md" "rest-tasks-stream.md"
fetch "https://developer.anduril.com/reference/rest/tasks/listen-as-agent.md" "rest-tasks-listen-as-agent.md"
fetch "https://developer.anduril.com/reference/rest/tasks/stream-as-agent.md" "rest-tasks-stream-as-agent.md"
fetch "https://developer.anduril.com/reference/rest/objects/list-objects.md" "rest-objects-list.md"
fetch "https://developer.anduril.com/reference/rest/objects/upload-object.md" "rest-objects-upload.md"
fetch "https://developer.anduril.com/reference/rest/objects/get-object-metadata.md" "rest-objects-metadata.md"

printf 'Fetched upstream docs into %s\n' "${OUT_DIR}"
