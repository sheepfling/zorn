# Lattice Certification Goal

## Objective

Build a non-vendored Lattice compatibility certification pipeline for Zorn.
The pipeline should automatically clone pinned public sample and integration
repositories, install their dependencies in isolated fixture workspaces,
configure them only through endpoints, tokens, environment variables, or config
files, run their native workflows against Zorn, and emit reproducible
capability reports.

The purpose is to prove that Zorn behaves like a credible public
Lattice-compatible sandbox, not only that it exposes similarly shaped endpoints.

## Priority Order

1. Official AIS REST
   - Proves REST auth, entity publish/upsert, location, ontology, provenance, and stream readback.
2. Official Objects
   - Proves object upload, metadata, list, download, and delete.
3. Official Thumbnail
   - Proves Objects plus Entities together, especially media/entity linkage.
4. Official AIS gRPC
   - Proves official Buf/gRPC entity publish behavior with generated clients.
5. Official Entity Visualizer
   - Proves live entity stream semantics for UI consumers.
6. Official Auto Reconnaissance
   - Proves entity stream, overrides, task creation, task catalog, agent listen, and task status lifecycle.
7. ARK MAVLink to Lattice
   - Proves telemetry-style entity publishing: position, velocity, attitude, health, ontology, and provenance.
8. DragonSync
   - Proves richer real-world entity modeling: relationships, classification, health, ADS-B/RID/TAK-style fields.
9. Maven
   - Proves gRPC stream consumer behavior, persistence/UI-style downstream use, and OAuth-like client flow.
10. DeepProve, ALFRED, and Java ADS-B
   - Stress and edge fixtures after official and cleaner third-party paths pass.

## Definition of Done

- `zorn-cert clone --all` clones pinned repos into ignored local fixture directories.
- `zorn-cert inspect <fixture>` reports language, install command, run command, and config expectations.
- `zorn-cert install <fixture>` installs dependencies without modifying upstream source.
- `zorn-cert run <fixture> --target ...` runs the fixture against Zorn with endpoint/token/config injection only.
- `zorn-cert report` shows pass, fail, or partial status per fixture and capability.
- CI can run at least the official fixtures, with third-party fixtures available as optional or stress jobs.
- No upstream code is vendored into Zorn; only pinned refs, runner metadata, generated reports, and compatibility findings are kept.

## Strategic Outcome

Zorn becomes a measured Lattice compatibility target. Every new feature or bug
fix should be driven by a public client, sample app, integration fixture, or
synthetic scenario that exposes a concrete compatibility gap.
