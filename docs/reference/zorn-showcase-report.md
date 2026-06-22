# Zorn Showcase Report

This report summarizes the planned full-feature showcase lane. It does not
expand the compatibility API.

The compatibility kernel remains:

- Entities
- Tasks
- Objects
- Auth
- REST streams
- gRPC EntityManagerAPI
- gRPC TaskManagerAPI

Zorn-only showcase modules may add local manifests, scenario files, UI state,
developer-console views, operator-COP views, mock agents, mesh simulation state,
and scorecards. Those artifacts are not third-party integration surfaces.

Current planned registry totals:

- Sources: 15
- Milestones: 13
- Capabilities: 56
- Scenarios: 11

The next implementation target is Z3 + Z4:

- Z3 Sandbox Environment Manager: `environment_id`, seed/reset/export,
  deterministic clock, fixture packs.
- Z4 Developer Console MVP: Entity Explorer, Task Explorer, Object Explorer,
  Stream Inspector, Compatibility Matrix.
