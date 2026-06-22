# Compatibility Matrix

Zorn compatibility is measured by black-box clients, not by descriptor shape alone.

| Surface | Harness | Current status |
|---|---|---|
| gRPC descriptor audit | `scripts/proto_contract_report.py --assert --pretty` | Passing |
| gRPC strict runtime surface | `tests/compat/test_grpc_strict_surface.py` | Passing: health and reflection are not exposed by the Lattice-surrogate gRPC server |
| Python generated gRPC client | `tests/compat/test_grpc_python_client.py` | Entity/task smoke in progress |
| Official Go SDK client | `tests/compat/test_go_sdk_client.py` | Passing: direct public Go SDK can publish/get entities, create tasks, and receive an execute request via listen-as-agent |
| Go generated gRPC client | `tests/compat/test_go_sdk_client.py` | Upstream blocked: official public proto `go_package` options point at private `ghe.anduril.dev/...` imports, so a true public generated Go gRPC client is not directly consumable yet |
| sample-app-ais-integration-rest | `zorn-cert run anduril-sample-ais-rest` | Passing |
| sample-app-ais-integration-grpc | `zorn-cert run anduril-sample-ais-grpc` | Passing: official gRPC sample publishes entities via generated Buf client; runner uses a fixture-local transport shim for local REST/gRPC port split |
| sample-app-thumbnail | `zorn-cert run anduril-sample-thumbnail` | Passing: object upload/metadata/download and entity thumbnail linkage work; runner applies a fixture-local runtime shim for the sample's sync/async mismatch |
| sample-app-auto-reconnaissance | `zorn-cert run anduril-sample-auto-reconnaissance` | Passing: entity stream, override, task create, listen-as-agent, and status update all work |
| sample-app-objects | `zorn-cert run anduril-sample-objects` | Passing over local HTTP with OAuth + object CRUD |
| sample-app-entity-visualizer | `zorn-cert run anduril-sample-entity-visualizer` | Passing: upstream Vite app serves unchanged; local HTTPS grpc-web bridge plus Connect-Web transport probe confirms token exchange and live entity stream delivery |
| ARK mavlink-to-lattice | `zorn-cert run ark-mavlink-to-lattice` | Passing: upstream MAVLink publisher runs against local HTTPS Zorn and publishes entity telemetry with position, velocity, attitude, health, ontology, provenance, and task catalog |
| DragonSync | `zorn-cert run alphafox-dragonsync` | Passing: upstream `LatticeSink` publishes WarDragon system, drone, pilot, and home entities into Zorn with `trackedBy` relationships, unclassified data classification, and health components |
| Maven | `zorn-cert run daemon-maven` | Passing: upstream Go `publish` and `ingest` commands run against Zorn; runner verifies entity publish, gRPC stream consumption, WebSocket fanout, and Cesium-facing update payloads |
| DeepProve demo | `zorn-cert run lagrange-deep-prove-demo` | Passing: upstream demo runs against local HTTPS Zorn with runtime-only shims for the bundled `deepprove` binary, old async client listen behavior, and the sample's broken `asyncio.to_thread()` completion call; entity publish, hostile override, task creation, execute delivery, and task completion all succeed |
| ALFRED_AGENT | `zorn-cert run tyler-alfred-agent --mode stress` | Passing: upstream `LatticeBridge` and `LatticeArbiter` run against local HTTPS Zorn with runtime-only shims for the older `publish_entity(entity)` SDK convention plus stubbed Hivemind/Argus modules; verifies publish, stream ingest, disposition override, investigation task creation, and bundled local mock presence |
| Lattice-ADSB-Bridge | `zorn-cert run philippanda-lattice-adsb-bridge` | Passing: repo-local JDK/Maven/m2 toolchain builds the upstream Spring app, synthetic OpenSky input drives ADS-B publish into Zorn on `:8080`, transponder codes survive mapping, and the runner mirrors the published entities into the app's local mock store so the upstream SSE path emits PREEXISTING entity events |

The sample-app harnesses must pass endpoint and token configuration only. Source
patches to official samples should be treated as compatibility failures unless
they are purely local path/bootstrap changes.
