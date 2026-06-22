# Zorn Lattice Ecosystem Architecture

Zorn should be a modular tactical ecosystem simulator while remaining a strict
Lattice surrogate at its integration boundary.

```text
Zorn-compatible environment
  zorn-core      -> Entities, Tasks, Objects, auth-dev, streams, event log
  zorn-sdk       -> SDK conformance, Buf audits, sample-app harnesses
  zorn-c2        -> local COP/developer-console applications
  zorn-autonomy  -> taskable agents, TaskCatalog routing, mission graphs
  zorn-mesh      -> local node/link/offline distribution simulation
  zorn-partner   -> package manifests, scorecards, reference data
  zorn-adapters  -> AIS, DIS, HLA, CoT/TAK, synthetic feeds
  zorn-domain    -> radar, EO/IR, C-UAS, autonomy, maritime, space scenarios
```

## Compatibility Boundary

The compatibility data plane is limited to validated Lattice-shaped surfaces:

- Entities
- Tasks
- Objects
- Auth
- REST streams
- gRPC EntityManager
- gRPC TaskManager

Modules may consume those surfaces, generate data for them, and verify behavior
with tests and reports. They must not add third-party-facing routes or local
replacement Lattice protos.

## Local Extension Model

Zorn-only features belong in local artifacts:

- scenario files,
- plugin manifests,
- adapter configs,
- local UI state,
- certification reports,
- reference datasets,
- in-process read models.

These artifacts can support demos and development, but they are not Lattice API.
