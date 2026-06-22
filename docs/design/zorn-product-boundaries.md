# Zorn Product Boundaries

Zorn has three parallel layers. Keeping them separate prevents UI convenience
from leaking into the Lattice-compatible data plane.

## Compatibility Data Plane

This is the official compatibility surface:

- REST entities, tasks, objects, OAuth/dev auth, and streams.
- gRPC EntityManager and TaskManager services.
- Official public Buf-generated protobuf types.
- Descriptor audits, SDK smoke tests, sample apps, and wire fixtures.

This layer should remain shaped by public SDK/API behavior. It should not include
local UI state such as selected entity, panel layout, map viewport, layer toggles,
saved filters, debug bookmarks, or timeline cursor position.

## Zorn Product Apps

These are local apps deployed with Zorn:

- `/developer-console`: entity explorer, task explorer, object explorer, stream
  inspector, raw payload view, schema validation, and compatibility reports.
- `/c2`: map-first COP, selected entity panel, task board, object/media previews,
  and scenario controls.

The product apps consume the data plane. They can expose Zorn-only projection
endpoints under `/api/zorn/ui/v1/**`, but those endpoints are not part of the
Lattice compatibility contract.

## UI/Application State

UI state belongs in the UI/application layer:

- selected entity or task
- pinned panels
- active layer set
- map viewport
- user layout
- search history
- starred entities
- debug bookmarks
- scenario timeline position

Data-plane state remains in entity, task, object, auth, and stream stores.

## Scenario And Plugin Layer

Scenario replay, adapters, mock agents, and UI plugins sit beside the product
apps. They may publish entities, tasks, objects, and events through the data
plane, then visualize additional overlays through the UI projection layer.

The rule is simple: if an official SDK client should see it, it belongs in the
data plane. If only Zorn's local web app needs it, it belongs in the UI/app
layer.
