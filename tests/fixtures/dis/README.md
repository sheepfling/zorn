# DIS Fixtures

`entity_state_replay.jsonl` is the first Alpha 1 DIS readiness fixture. Each
line is a neutral JSON representation of a DIS Entity State update that can later
be produced by a PCAP/FastDIS reader.

The fixture covers:

- stable entity ID derivation from exercise/site/application/entity identity,
- two updates for one entity,
- a second exercise namespace with the same site/application/entity tuple,
- force/disposition mapping,
- location, velocity, and orientation mapping,
- provenance/source update time preservation,
- non-live/delete stream behavior.

Run it with:

```bash
zorn replay dis tests/fixtures/dis/entity_state_replay.jsonl \
  --target http://127.0.0.1:8080 \
  --report /tmp/zorn-alpha1-dis-report.json
```

The replay command publishes through the existing `/api/v1/entities` and
`/api/v1/entities/events` routes. It does not use private store access in the
normal plugin path.
