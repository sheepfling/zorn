# Zorn acceptance test matrix

| Test ID | Milestone | Lane | Level | Description |
|---|---|---|---|---|
| Z3-AT01 | Z3 | LANE-SANDBOX | integration | Resetting the same seed twice yields the same entity/task/object/event counts and ordered event hashes. |
| Z3-AT02 | Z3 | LANE-SANDBOX | integration | Two environments can contain the same entityId without state collision. |
| Z3-AT03 | Z3 | LANE-SANDBOX | integration | Simulated time pause prevents expiry and task timeline advancement. |
| Z3-AT04 | Z3 | LANE-SANDBOX | integration | Exported environment can be imported into a clean database and pass equality checks. |
| Z4-AT01 | Z4 | LANE-DEVELOPER-CONSOLE | integration | Entity Explorer displays seeded asset, track, and geo-entity examples. |
| Z4-AT02 | Z4 | LANE-DEVELOPER-CONSOLE | integration | Task Explorer displays Create → Update → Cancel/Complete timeline. |
| Z4-AT03 | Z4 | LANE-DEVELOPER-CONSOLE | integration | Object Explorer previews a thumbnail object and shows metadata. |
| Z4-AT04 | Z4 | LANE-DEVELOPER-CONSOLE | integration | Stream Inspector shows entity stream heartbeats and live create/update/delete events. |
| Z5-AT01 | Z5 | LANE-C2 | integration | AIS or synthetic entity replay moves icons on the map through entity stream updates. |
| Z5-AT02 | Z5 | LANE-C2 | integration | Selecting an entity highlights it in the map, list, and detail panel. |
| Z5-AT03 | Z5 | LANE-C2 | integration | Creating a mock investigation task shows it on the task board and routes it to a mock agent. |
| Z5-AT04 | Z5 | LANE-C2 | integration | Alert rule triggers on a seeded unknown track near a configured training zone. |
| Z6-AT01 | Z6 | LANE-ADAPTERS | integration | AIS replay creates moving surface tracks visible in /c2 and /developer-console. |
| Z6-AT02 | Z6 | LANE-ADAPTERS | integration | DIS fixture creates asset/track entities with stable IDs and deterministic provenance. |
| Z6-AT03 | Z6 | LANE-ADAPTERS | integration | Adapter failure is surfaced as health status without crashing the server. |
| Z6-AT04 | Z6 | LANE-ADAPTERS | integration | Replay can pause/resume through the sandbox clock. |
| Z7-AT01 | Z7 | LANE-OBJECTS-MEDIA | scenario | Uploading a thumbnail object makes it visible on selected entity detail. |
| Z7-AT02 | Z7 | LANE-OBJECTS-MEDIA | scenario | Deleting an object updates browser state and event log. |
| Z7-AT03 | Z7 | LANE-OBJECTS-MEDIA | scenario | Evidence export contains manifest, events, tasks, objects, and checksums. |
| Z7-AT04 | Z7 | LANE-OBJECTS-MEDIA | scenario | Object metadata remains REST-compatible while local distribution metadata remains namespaced. |
| Z8-AT01 | Z8 | LANE-AUTONOMY | scenario | A task created in /c2 routes to a matching mock agent via ListenAsAgent. |
| Z8-AT02 | Z8 | LANE-AUTONOMY | scenario | Agent status progresses through sent/accepted/in-progress/complete or failed. |
| Z8-AT03 | Z8 | LANE-AUTONOMY | scenario | Cancel request interrupts task and records terminal status. |
| Z8-AT04 | Z8 | LANE-AUTONOMY | scenario | Mission graph pauses at human approval gate and resumes only after operator approval. |
| Z9-AT01 | Z9 | LANE-MESH | scenario | Partitioning a node stops remote event visibility while local state continues. |
| Z9-AT02 | Z9 | LANE-MESH | scenario | Reconnect replays queued events in deterministic order. |
| Z9-AT03 | Z9 | LANE-MESH | scenario | Object unavailable on a node shows a clear simulated fetch failure. |
| Z9-AT04 | Z9 | LANE-MESH | scenario | Replication trace explains how a final entity state was chosen after conflict. |
| Z10-AT01 | Z10 | LANE-PARTNER | scenario | A sample AIS adapter package installs and declares entity-publishing capability. |
| Z10-AT02 | Z10 | LANE-PARTNER | scenario | A mock agent package installs and declares TaskCatalog support. |
| Z10-AT03 | Z10 | LANE-PARTNER | scenario | Conformance runner executes package tests in a reset sandbox. |
| Z10-AT04 | Z10 | LANE-PARTNER | scenario | Scorecard accurately reports pass/fail and exercised capabilities. |
| Z11-AT01 | Z11 | LANE-DOMAINS | scenario | Each domain pack can be reset, run, paused, exported, and replayed. |
| Z11-AT02 | Z11 | LANE-DOMAINS | scenario | Each pack exercises at least three of: Entities, Tasks, Objects, UI, adapters, agents, mesh. |
| Z11-AT03 | Z11 | LANE-DOMAINS | scenario | C-UAS pack contains no engagement recommendation, targeting, weapon-release, or fire-control workflow. |
| Z11-AT04 | Z11 | LANE-DOMAINS | scenario | All packs generate a scenario report object and event summary. |
| Z12-AT01 | Z12 | LANE-SHOWCASE | scenario | A fresh clone can run the showcase bundle and produce a report without manual data setup. |
| Z12-AT02 | Z12 | LANE-SHOWCASE | scenario | Evaluation report includes compatibility, scenario, UI, adapter, agent, object, and mesh sections. |
| Z12-AT03 | Z12 | LANE-SHOWCASE | scenario | Each demo has a runbook with expected operator/developer observations. |
| Z12-AT04 | Z12 | LANE-SHOWCASE | scenario | Release matrix lists supported, partial, and intentionally unsupported features. |
