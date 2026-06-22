# Lattice Ecosystem Requirements

Zorn should grow beyond a narrow REST mock, but the compatibility boundary is
strict: third-party integrations must only see validated Lattice-shaped
surfaces. Ecosystem modules can add local scenario files, manifests, reports,
UI state, adapter configs, and internal tooling. They must not create new
surrogate API contracts.

## Lanes

- `zorn-sdk`: official SDK conformance, Buf proto audit, sample-app harnesses,
  and developer diagnostics.
- `zorn-c2`: COP and operator workflows backed by existing Entity/Task/Object
  state.
- `zorn-autonomy`: TaskCatalog routing, mission graphs, mock agents, and
  human-supervision gates through task surfaces.
- `zorn-mesh`: node/link/offline simulation as local scenario behavior over
  existing state.
- `zorn-partner`: package manifests, scorecards, reference data, and
  compatibility reports.
- `zorn-adapters`: AIS, DIS, HLA, CoT/TAK, and synthetic source adapters that
  publish through Lattice-shaped APIs.
- `zorn-domain`: radar, EO/IR, C-UAS, autonomy, maritime, tactical compute, and
  space-domain scenario packs.

## Boundary

Allowed integration surfaces are Entities, Tasks, Objects, Auth, REST streams,
gRPC Entities, and gRPC Tasks. Local product apps and scenario modules may use
internal read models, files, manifests, and reports, but those artifacts are not
third-party API.
