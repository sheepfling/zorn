# Zorn risk, safety, and boundary register

This document keeps project risks visible while planning richer showcase features.

## RISK-001 — contract-drift

**Risk:** Official public SDK/proto behavior changes faster than the mock implementation.

**Impact:** Compatibility regressions in clients and sample apps.

**Mitigation:** Keep descriptor audit, sample-app harness, and compatibility matrix as release gates.

**Owning lanes:** LANE-CORE

## RISK-002 — legal-branding

**Risk:** Zorn could be mistaken for an official or affiliated product.

**Impact:** Brand/trademark and trust problems.

**Mitigation:** Use name-neutral internals, clear disclaimers, no Anduril marks or proprietary UI replication.

**Owning lanes:** LANE-SHOWCASE, LANE-PARTNER

## RISK-003 — safety

**Risk:** Domain scenarios drift toward operational targeting or weapon employment workflows.

**Impact:** Unsafe or inappropriate capabilities.

**Mitigation:** Keep C-UAS and defense scenarios limited to surveillance, investigation, reporting, readiness, and non-kinetic tasking.

**Owning lanes:** LANE-C2, LANE-AUTONOMY, LANE-DOMAINS

## RISK-004 — architecture

**Risk:** Zorn-only features leak into public-compatible proto/API layers.

**Impact:** Incompatibility and confusing boundaries.

**Mitigation:** Place local UI/plugin/scenario/mesh metadata in sidecar state, local manifests, reports, and UI-internal read models only.

**Owning lanes:** LANE-CORE, LANE-DEVELOPER-CONSOLE, LANE-MESH

## RISK-005 — scope

**Risk:** UI polish consumes effort before data/stream/task behavior is reliable.

**Impact:** Good-looking but brittle demos.

**Mitigation:** Build Developer Console and acceptance matrix before operator-grade COP polish.

**Owning lanes:** LANE-DEVELOPER-CONSOLE, LANE-C2

## RISK-006 — performance

**Risk:** Dense scenario packs overwhelm stream/event/UI performance.

**Impact:** Demos fail under realistic track counts.

**Mitigation:** Add performance budgets and synthetic load tests starting in Z5/Z6.

**Owning lanes:** LANE-C2, LANE-ADAPTERS, LANE-MESH

## RISK-007 — supply-chain

**Risk:** Generated proto packages or public SDK dependencies are unavailable or unexpectedly changed.

**Impact:** gRPC compatibility workflow breaks.

**Mitigation:** Pin versions, audit checksums/descriptors, and maintain documented export/snapshot steps.

**Owning lanes:** LANE-CORE
