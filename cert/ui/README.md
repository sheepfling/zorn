# Zorn UI Certification

This directory tracks Zorn product-app requirements separately from the
Lattice-compatible data plane under `cert/lattice`.

The UI certification target is browser-visible proof that Zorn's data plane is
useful:

- `/developer-console` for entity, task, object, stream, schema, and compatibility debugging.
- `/c2` for map-first operator COP workflows.
- Playwright screenshots and interaction tests for fixture and scenario output.

UI requirements may reference Lattice-like product behavior as research evidence,
but they must not redefine the official Entity, Task, Object, REST, gRPC, or auth
compatibility contracts.
