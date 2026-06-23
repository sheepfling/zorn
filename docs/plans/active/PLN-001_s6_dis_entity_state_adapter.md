# PLN-001: S6 DIS Entity State Adapter

## Objective

Document and validate the first evaluation-only adapter helper: DIS Entity State
JSONL to Zorn Entity. This helper exercises the public surface without turning
DIS into a core runtime concept.

## Scope

- Define a local adapter helper under `eval_dis/`.
- Add a small internal neutral representation for DIS Entity State data.
- Map DIS Entity State fields to Zorn entity payloads.
- Add fixture-driven tests for deterministic mappings.
- Keep replay helpers outside the runtime CLI.

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
- The helper publishes the fixture through the existing public Entity API and
  writes a pass/fail report.

## Out of Scope

- Full PCAP parsing.
- External adapter dependency wiring.
- Fire/Detonation events.
- Electromagnetic emission mapping.
- Scenario clock/replay controls.

## Follow-On

After this mapping is stable, keep any concrete reader or adapter wiring
outside the core runtime and feed the same neutral model through the public
Entity API.

## Current Status

Initial JSONL replay is implemented under `eval_dis/`. It is a
neutral fixture path, not full PCAP parsing. The helper emits a report with
passed, failed, missing, entities, and events fields. Normal replay uses the
existing `/api/v1/entities` and `/api/v1/entities/events` routes; private store
access is limited to internal tests/helpers.
