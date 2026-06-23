# DIS Fixtures

`entity_state_replay.jsonl` is an evaluation-only fixture. Each line is a
neutral JSON representation of a DIS Entity State update that can later be
produced by an external reader outside this repo.

The fixture covers:

- stable entity ID derivation from exercise/site/application/entity identity,
- two updates for one entity,
- a second exercise namespace with the same site/application/entity tuple,
- force/disposition mapping,
- location, velocity, and orientation mapping,
- provenance/source update time preservation,
- non-live/delete stream behavior.

Run it through the adapter helpers or the test suite, not through the core Zorn
CLI:

The replay helpers publish through the existing `/api/v1/entities` and
`/api/v1/entities/events` routes. They do not use private store access in the
normal adapter path.
