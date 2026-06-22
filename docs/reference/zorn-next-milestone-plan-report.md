# Zorn next milestone planning report

Sources: 10
Work lanes: 11
Milestones detailed: 10
Epics: 40
Backlog stories: 120
Acceptance tests: 40
Dependency edges: 39
Risks: 7

## Milestone sequence

- **Z3** — Sandbox Environment Manager (LANE-SANDBOX)
- **Z4** — Developer Console MVP (LANE-DEVELOPER-CONSOLE)
- **Z5** — Operator C2 MVP (LANE-C2)
- **Z6** — Sensor, Track, and Protocol Adapters (LANE-ADAPTERS)
- **Z7** — Objects, Media, Reports, and Evidence Workflows (LANE-OBJECTS-MEDIA)
- **Z8** — Mission Autonomy and Taskable Agents (LANE-AUTONOMY)
- **Z9** — Mesh and Edge Simulation (LANE-MESH)
- **Z10** — Partner-Style Integration System (LANE-PARTNER)
- **Z11** — Domain Scenario Packs (LANE-DOMAINS)
- **Z12** — Rich Showcase Bundle and Evaluation Mode (LANE-SHOWCASE)

## Work lane coverage

- **LANE-CORE** — Compatibility Kernel: Z0, Z1, Z2
- **LANE-SANDBOX** — Sandbox Environment Manager: Z3
- **LANE-DEVELOPER-CONSOLE** — Developer Console: Z4
- **LANE-C2** — Operator C2: Z5
- **LANE-ADAPTERS** — Sensors, Tracks, and Protocol Adapters: Z6
- **LANE-OBJECTS-MEDIA** — Objects, Media, Reports, and Evidence: Z7
- **LANE-AUTONOMY** — Mission Autonomy and Taskable Agents: Z8
- **LANE-MESH** — Mesh and Edge Simulation: Z9
- **LANE-PARTNER** — Partner-Style Integration System: Z10
- **LANE-DOMAINS** — Domain Scenario Packs: Z11
- **LANE-SHOWCASE** — Showcase and Evaluation Mode: Z12

## Immediate recommended build sequence

1. Z3 environment manager basics: environment_id, reset/seed/export, deterministic clock.
2. Z4 Developer Console: Entity Explorer first, then Task/Object/Stream inspectors.
3. Z5 C2 shell: map/list/detail panels consuming existing entity stream.
4. Z6 adapter framework with AIS replay, then DIS Entity State mapping.
5. Z8 mock agents only after Task Explorer and C2 task board can show lifecycle clearly.
