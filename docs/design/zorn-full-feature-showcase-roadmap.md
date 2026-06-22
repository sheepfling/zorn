# Zorn Full-Feature Showcase Roadmap

Zorn should mature from a Lattice-compatible local surrogate into a richer
showcase environment without changing the third-party integration boundary.

## Compatibility Kernel

The kernel is the only surface third-party apps should target:

- Entity REST behavior and EntityManager gRPC behavior.
- Task REST behavior and TaskManager gRPC behavior.
- Object REST behavior.
- Auth modes used by public samples and SDKs.
- REST stream behavior and generated-client conformance.

## Showcase Expansion

The showcase layer can add local product modules:

- Developer Console.
- Operator C2.
- Scenario engine.
- Mission graph and mock agents.
- Mesh/edge simulator.
- Partner-style package manifests and capability reports.
- Domain scenario packs.

These modules consume the kernel and local scenario artifacts. They must not
create a fake Lattice API, a replacement Lattice proto namespace, or a new
third-party contract.

## Milestone Order

1. Z0: keep guardrail tests green.
2. Z1: harden Entity/Task/Object lifecycle behavior.
3. Z2: make SDK and sample-app harnesses the main compatibility proof.
4. Z3: add deterministic sandbox environment management.
5. Z4: build the developer console first.
6. Z5: build the operator C2 view on the same data.
7. Z6-Z12: layer adapters, media workflows, agents, mesh simulation, partner
   packaging, domain scenarios, and evaluation bundles.
