# PLN-001: S6 DIS Entity State Adapter

## Objective

Implement the first tactical data adapter: DIS Entity State PDU to Zorn Entity.
This is the milestone where Zorn becomes a tactical simulation integration
platform instead of only a Lattice-compatible API sandbox.

## Scope

- Define a local adapter package under `src/zorn/adapters/dis/`.
- Add a small internal neutral representation for DIS Entity State data.
- Map DIS Entity State fields to Zorn entity payloads.
- Add fixture-driven tests for deterministic mappings.
- Add a replay command stub that can later consume PCAP/FastDIS input.

## Mapping

| DIS input | Zorn output |
|---|---|
| exercise ID + entity ID | namespaced `entityId` |
| entity ID | aliases / alternate IDs |
| marking | description |
| force ID | `milView.disposition` |
| entity type | ontology |
| world location | `location.position` |
| velocity | `location.velocityEnu` |
| orientation | `location.attitudeEnu` |
| source timestamp | provenance source update time |

## Acceptance Criteria

- A fixture Entity State PDU maps to a canonical Zorn entity payload.
- Repeated updates preserve stable `entityId`.
- Namespacing supports multiple DIS exercise IDs.
- Source identity is present in provenance.
- Tests cover force/disposition mapping and location/velocity/attitude fields.
- `zorn replay dis tests/fixtures/dis/entity_state_replay.jsonl --target http://127.0.0.1:8080`
  publishes the fixture through the existing public Entity API and writes a
  pass/fail report.

## Out of Scope

- Full PCAP parsing.
- FastDIS dependency wiring.
- Fire/Detonation events.
- Electromagnetic emission mapping.
- Scenario clock/replay controls.

## Follow-On

After this mapping is stable, add a concrete reader backed by Packet-Stoat or
FastDIS and wire `zorn replay dis fixtures/demo.pcap` into the scenario engine.

## Current Status

Initial JSONL replay is implemented under `src/zorn/adapters/dis/`. It is a
neutral fixture path, not full PCAP parsing. The command emits an Alpha 1 report
with passed, failed, missing, entities, and events fields. Normal replay uses
the existing `/api/v1/entities` and `/api/v1/entities/events` routes; private
store access is limited to internal tests/helpers.

FastDIS should verify Zorn through API state surfaces instead of treating replay
reports as authoritative:

- `GET /healthz/details`
- `GET /api/v1/entities/events/snapshot`
- `GET /api/v1/tasks/events/snapshot`
- `GET /api/v1/verification/state`
- `GET /api/v1/backend/capabilities`
- `GET /api/v1/backend/compatibility`

Explicit entity deletion/tombstoning is available through
`DELETE /api/v1/entities/{entity_id}` and emits a `DELETED` entity event.
