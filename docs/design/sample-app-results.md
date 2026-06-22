# Sample App Results

This file records black-box sample-app runs against Zorn.

## Current Slice

- `sample-app-ais-integration-rest`: `pass`
  commit: `311b6659662c1f3119ba517530a46e9bac5c4cb8`
  evidence: `cert/lattice/reports/anduril-sample-ais-rest.json`
- `sample-app-ais-integration-grpc`: `pass`
  commit: `6c304f093e445a1721951a647ca49a05e9bba6e2`
  evidence: `cert/lattice/reports/anduril-sample-ais-grpc.json`
  note: passes with a fixture-local runtime shim that routes OAuth HTTPS and gRPC traffic to separate local Zorn ports while leaving upstream source untouched.
- `sample-app-thumbnail`: `pass`
  commit: `b9faa7029c0caa3433f3c97ffed365aef6c37fcf`
  evidence: `cert/lattice/reports/anduril-sample-thumbnail.json`
  note: passes with a fixture-local `sitecustomize` runtime shim that makes the sample's sync `Lattice.entities.override_entity()` call awaitable, leaving upstream source untouched.
- `sample-app-auto-reconnaissance`: `pass`
  commit: `749f24b411a125926993c790935ac73811858320`
  evidence: `cert/lattice/reports/anduril-sample-auto-reconnaissance.json`
  note: passes after fixing SSE entity payload compatibility, agent selector parsing, task status-version handling, task delivery replay, and effective entity override application.
- `sample-app-objects`: `pass`
  commit: `3f205e169bf657985f719766be5b1cb074559767`
  evidence: `cert/lattice/reports/anduril-sample-objects.json`
  note: runs against local HTTP Zorn with OAuth token exchange and passes upload, metadata, list, download, and delete.
- `sample-app-entity-visualizer`: `pass`
  commit: `6836aa41ecf18939fc939726b8513aa1e80a3cf6`
  evidence: `cert/lattice/reports/anduril-sample-entity-visualizer.json`
  note: runs with a local HTTPS grpc-web bridge in front of Zorn gRPC/REST, serves the upstream Vite app unchanged, and verifies the visualizer transport path by fetching OAuth tokens and streaming live entities through the same Connect-Web dependency stack.
- `ARK mavlink-to-lattice`: `pass`
  commit: `6b80988217a4055aaad5377be3eda6c92fe277b4`
  evidence: `cert/lattice/reports/ark-mavlink-to-lattice.json`
  note: runs the upstream publisher unchanged against local HTTPS Zorn with a fixture-local `sitecustomize` shim that supplies synthetic MAVLink telemetry at runtime; verifies entity publish, position, velocity, attitude, ontology, health, provenance, and task catalog.
- `DragonSync`: `pass`
  commit: `2cf6fdcfe9dbe3bdebcbd728428ba50fb1974747`
  evidence: `cert/lattice/reports/alphafox-dragonsync.json`
  note: runs the upstream `sinks.lattice_sink.LatticeSink` against local HTTPS Zorn with synthetic system/drone/pilot/home inputs and verifies bearer auth, entity publish, `trackedBy` relationships, unclassified data classification, and WarDragon health components.
- `Maven`: `pass`
  commit: `39bc21752360cbaf9fb7b418da188daa2ecdeab7`
  evidence: `cert/lattice/reports/daemon-maven.json`
  note: runs the upstream Go `cmd/ingest` and `cmd/publish` paths against Zorn using runtime-only overlays for auth, gRPC target selection, and Neo4j persistence; verifies OAuth-shaped auth flow, entity publish, gRPC ingest, WebSocket fanout, and Cesium-facing entity update payloads.
- `DeepProve demo`: `pass`
  commit: `13ba53d7662d91a85a7060ecbead7c23495d8b71`
  evidence: `cert/lattice/reports/lagrange-deep-prove-demo.json`
  note: passes with runtime-only shims for the non-native `deepprove` binary, the older shared-client `listen_as_agent` behavior, and the sample's incorrect `asyncio.to_thread()` use on an async status-update method; upstream source remains untouched while entity publish, hostile override, task creation, execute-request delivery, and task completion all succeed against Zorn.
- `ALFRED_AGENT`: `pass`
  commit: `6162a37f12de7bbc0d38fb786311c13686ec75bc`
  evidence: `cert/lattice/reports/tyler-alfred-agent.json`
  note: runs the upstream `alfred.integrations.lattice_bridge` and `LatticeArbiter` path against local HTTPS Zorn with runtime-only compatibility shims for ALFRED's older `publish_entity(entity)` SDK convention plus stubbed Hivemind and Argus threat-scoring modules; verifies entity publish, entity stream consumption, disposition override, investigation task creation, and bundled `scripts/lattice_mock.py` presence without installing ALFRED's unrelated ML stack.
- `Lattice-ADSB-Bridge`: `pass`
  commit: `9b21ff869d0600b3bca872276c11d9a6b815fdf2`
  evidence: `cert/lattice/reports/philippanda-lattice-adsb-bridge.json`
  note: runs with repo-local JDK 17, Maven 3.9.9, and a repo-local Maven cache entry for `com.anduril:lattice-sdk:5.3.1`; the runner feeds a synthetic OpenSky payload, starts Zorn on `:8080` to satisfy the app's hardcoded SDK base URL, verifies ADS-B publish and transponder-code mapping in Zorn, then mirrors the published entities into the app's local mock store so the upstream SSE/UI path emits PREEXISTING events without patching upstream source.
- Direct generated Python gRPC client: covered by `tests/compat/test_grpc_python_client.py`.
- Official Go SDK client: covered by `tests/compat/test_go_sdk_client.py`.
- Direct generated Go gRPC client: upstream public Go import path is currently blocked by private `go_package` metadata in the official proto descriptors.

Future entries should include sample commit, Zorn commit, command, environment,
pass/fail status, and the first compatibility mismatch if failed.
