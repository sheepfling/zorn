# Zorn Rich Environment Architecture

Zorn is organized as a compatibility kernel plus local showcase modules.

```text
official-compatible layer
  Entities
  Tasks
  Objects
  OAuth-dev/static/no-auth modes
  REST streams
  gRPC EntityManagerAPI
  gRPC TaskManagerAPI
  official Buf-generated proto audit

local showcase layer
  Developer Console
  Operator C2
  scenario engine
  mission graph
  mock agents
  mesh simulation
  partner package registry
  domain packs
  UI state
  local extension metadata
```

The showcase layer can store local state and generate local reports, but it must
drive integration behavior through the compatibility kernel. A DIS plugin, AIS
runner, SDK client, or sample app should not need a Zorn-specific endpoint.

## Local Module Boundaries

- Developer Console: reads entity/task/object state, streams, reports, and
  fixture output for debugging.
- Operator C2: renders map-first COP, tasks, media, provenance, and scenario
  controls from the same kernel state.
- Scenario engine: seeds, resets, replays, exports, and compares deterministic
  runs.
- Mission autonomy: provides mock agents and task-catalog behavior through the
  task/entity surfaces.
- Mesh simulator: models degraded distribution locally while preserving the
  visible Entity/Task/Object behavior.
- Partner system: stores package manifests and capability scorecards.
- Domain packs: package safe synthetic scenarios and expected timelines.
