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

## Out of Scope

- Full PCAP parsing.
- FastDIS dependency wiring.
- Fire/Detonation events.
- Electromagnetic emission mapping.
- Scenario clock/replay controls.

## Follow-On

After this mapping is stable, add a concrete reader backed by Packet-Stoat or
FastDIS and wire `zorn replay dis fixtures/demo.pcap` into the scenario engine.
