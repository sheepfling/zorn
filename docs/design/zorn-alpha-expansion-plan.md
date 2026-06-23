# Zorn Alpha Expansion Plan

## Goal

Build Zorn as a two-layer system:

- A strict Lattice-compatible core limited to public Entities, Tasks, Objects,
  OAuth-dev, REST, and public Buf-generated gRPC.
- A Zorn-native environment layer for C2, developer console, scenario control,
  mesh simulation, replay, adapters, and operator workflows that consumes the
  core through those same public interfaces rather than extending or replacing
  them.

The rule is firm:

- The core is the surrogate.
- The environment is the product layer.
- Product-layer features must not contaminate the surrogate contract.

## Phase Split

### Alpha 1

Finish Zorn as a strict Lattice surrogate with:

- faithful public API behavior
- replayable/loggable entity/task/object state
- no invented runtime surfaces
- official SDK, sample-app, and public gRPC evidence

### Alpha 2

Add a Zorn-native tactical sandbox layer with:

- environment manager
- deterministic replay/scenario control
- evaluation-only AIS and DIS adapters outside the Zorn package
- mock taskable agents
- degraded-network and mesh simulation

Every Alpha 2 feature must publish and observe through the Alpha 1 public core.

### Alpha 3

Build the UI layer as separate apps:

- `/developer-console` first
- `/c2` second

Both apps must be driven by the same entity/task/object streams and stores, and
UI-specific state must remain outside the compatibility layer.

## Architecture Guardrails

### Allowed In Core

- public REST routes
- public stream routes
- public OAuth-dev token route
- public Buf-generated gRPC EntityManager and TaskManager services
- compatibility reports and contract validation
- entity/task/object/auth/event persistence

### Not Allowed In Core

- adapter-specific runtime endpoints
- UI-specific state
- scenario-local control routes that masquerade as public API
- mesh-specific transport semantics in the compatibility contract
- proprietary or speculative Lattice behavior not evidenced by public material

### Allowed In Product Layer

- environment records
- scenario files
- replay clocks
- local read models
- adapter health
- node topology
- UI layout and filters
- showcase artifacts

## Recommended Build Sequence

1. Protect Alpha 1:
   keep the compatibility suite, SDK smokes, and contract validation green.
2. Build Z3 sandbox environment manager:
   environment IDs, seed/reset/export, deterministic clock, fixture packs.
3. Build evaluation-only adapters:
   AIS replay first, DIS replay second, both outside the Zorn package.
4. Build Alpha 2 mock agents:
   task catalog, listen/execute/status/complete loops, object attachments.
5. Build mesh simulation:
   nodes, partitions, lag, replay queues, object availability.
6. Build `/developer-console`:
   entity/task/object/stream inspectors and compatibility views.
7. Build `/c2`:
   map, task board, alerts, media, scenario controls.

## Alpha 2 Deliverables

- repeatable environment reset and seed
- deterministic replay clock
- evaluation-only adapters using only public routes
- mock agents using only public task/entity/object flows
- local mesh simulation with no API-surface expansion

## Alpha 3 Deliverables

- `/developer-console` for debugging and certification
- `/c2` for operator-style interaction
- Playwright proof that the UI reflects real core behavior

## Definition Of Success

Zorn succeeds as a product roadmap when:

- the strict public-Lattice surrogate remains credible on its own
- Alpha 2 adds tactical behavior without widening that contract
- Alpha 3 visualizes the same behavior without redefining it
