# Alpha 1 Gap Closure Plan

This plan takes the Alpha1.1 external evaluator gap evidence and turns it into a
correction tranche for a stricter, more usable Alpha 1.

Checkpoint commit for this plan:

- `d5169e8` `Harden strict Lattice surrogate core`

Primary evidence source:

- `zorn_gap_bundle_alpha1_1.zip`

The goal is not to broaden Zorn. The goal is to remove the places where Alpha
1 still behaves unlike a public Lattice-shaped environment, while staying
inside the existing public contract:

- REST Entities / Tasks / Objects
- OAuth-dev token route
- public Buf-generated gRPC Entities / Tasks
- no new runtime endpoints
- no Zorn-only transport shortcuts for external apps

## Current Gaps

The external evaluator gap bundle identifies three real weak areas:

1. Entity parity across REST and gRPC is incomplete.
2. OAuth/auth lifecycle behavior is still too static.
3. Some external evaluator flows still need Zorn-shaped handling instead of
   relying only on the public-surrogate behavior.

These are the concrete failures called out by the gap bundle:

- gRPC override is not accepted through the official request shape.
- REST remove-override does not restore the expected shared state across
  transports.
- gRPC remove-override is not accepted through the expected request shape.
- gRPC `is_live=false` does not surface as non-live on REST `GET`.
- OAuth tokens are effectively aliases of the static bearer token state.
- OAuth expiry is announced but not enforced.
- OAuth scope is echoed but not meaningfully modeled.
- gRPC auth does not accept the sandbox-header style metadata path that some
  external flows use on REST.

## Hard Boundary

The corrective work must stay inside these rules:

- Do not add diagnostic or verification endpoints.
- Do not add Zorn-only runtime APIs for state inspection.
- Do not invent vendor-only auth semantics that are not evidenced by the public
  routes or public SDK behavior.
- Do not push UI, replay controls, or adapter-local shortcuts into the data
  plane.

If a behavior is unknown on real Lattice, Alpha 1 should either:

- match the public SDK/proto/request shape exactly, or
- keep the behavior minimal and document the unknown, rather than inventing a
  larger model.

## Workstream A: Entity Parity Closure

This is the highest-value Alpha 1 corrective work because it directly affects
external evaluator entity publication, stream verification, and cross-transport
trust.

### A1. Fix gRPC override request parsing

Current problem:

- `OverrideEntityRequest` is being treated as if it contains top-level
  `entity_id`.
- The official request shape instead carries:
  - `entity`
  - `field_path`
  - `provenance`

Correction:

- Derive `entity_id` from `request.entity.entity_id`.
- Read `field_path` from the real request field.
- Extract the override value from the entity payload at the requested field
  path, not from a guessed top-level object shape.

Acceptance:

- gRPC override followed by REST `GET` shows the overridden value.
- gRPC override followed by gRPC `GetEntity` shows the same state.
- Direct SDK smoke and parity tests cover this path.

### A2. Fix gRPC remove-override request handling

Current problem:

- The gap evidence reports `RemoveEntityOverride` fails with
  `entity_id and field_path are required`.

Correction:

- Verify the generated request shape against the pinned official proto modules.
- Accept the actual official request fields without fallback assumptions.
- Add a dedicated parity test using the official Python gRPC types.

Acceptance:

- gRPC remove-override succeeds against the official generated request type.
- REST `GET` after gRPC remove-override shows the cleared state.

### A3. Restore base entity state after override removal

Current problem:

- REST remove-override clears the `overrides` map but leaves the effective field
  value in place.

Correction:

- Preserve pre-override field state in internal storage that never leaks through
  REST or gRPC payloads.
- On override removal, restore the base value or remove the field if no base
  value existed.
- Re-emit the corrected entity state through the normal event log path.

Implementation note:

- This is internal store bookkeeping, not a public surface change.
- Private compatibility metadata must be stripped before any entity leaves the
  server.

Acceptance:

- REST override -> gRPC get -> REST remove-override -> gRPC get returns the same
  post-clear state as REST `GET`.
- gRPC override -> REST get -> gRPC remove-override -> REST get returns the same
  post-clear state.

### A4. Preserve explicit gRPC `is_live=false`

Current problem:

- gRPC-originated non-live entities become live on the REST side.

Likely cause:

- default proto scalar `false` is lost during message-to-dict conversion, so the
  store falls back to `isLive=true`.

Correction:

- Preserve explicit proto scalar booleans when translating public gRPC entity
  messages into the store payload.
- Add a direct parity test for gRPC publish with `is_live=false`.

Acceptance:

- gRPC publish with `is_live=false` is visible as non-live on REST `GET`.
- Matching entity event semantics remain `DELETED`/non-live, not `CREATE`.

## Workstream B: Auth Lifecycle Realism Within Boundary

Alpha 1 should become less static, but it should not invent a large auth model.

### B1. Separate issued OAuth tokens from static bearer tokens

Current problem:

- `/oauth/token` returns the same practical auth state as the static dev token.

Correction:

- Introduce an internal issued-token store behind the existing `/oauth/token`
  route and the existing auth middleware.
- Issued tokens should be distinct from configured static tokens.
- Bearer validation should accept:
  - configured static dev tokens
  - issued OAuth-dev tokens that are still valid

Acceptance:

- issued token != static bootstrap token
- REST and gRPC both accept issued tokens
- invalid issued token is rejected cleanly

### B2. Enforce token expiry

Current problem:

- `expires_in` is reported but not enforced.

Correction:

- Track issue time and expiry for OAuth-dev tokens.
- Reject expired tokens on REST with the existing auth response path.
- Reject expired tokens on gRPC with `UNAUTHENTICATED`.

Acceptance:

- token works before expiry
- token fails after expiry
- static dev tokens remain valid only if configured as static tokens

### B3. Accept sandbox-header style metadata on gRPC when enabled

Current problem:

- REST can enforce sandbox-header style auth; gRPC only accepts bearer metadata.

Correction:

- Accept `anduril-sandbox-authorization` and equivalent metadata in the gRPC
  auth interceptor when sandbox-header mode is enabled.
- Do not require a second invented handshake or new endpoint.

Acceptance:

- same startup auth mode can be exercised consistently over REST and gRPC
- missing required sandbox metadata fails cleanly

### B4. Explicitly defer refresh and rich scope enforcement

These remain out of Alpha 1 unless evidenced by public client requirements:

- refresh-token flow
- arbitrary scope authorization matrix
- vendor-like OAuth policy modeling

Reason:

- adding them speculatively would be invented behavior, not compatibility
  hardening.

Alpha 1 should keep `scope` informational unless a public SDK/sample/app
actually depends on enforcement behavior that can be observed and tested.

## Workstream C: Remove Remaining External Evaluator Cheat Pressure

The server and the adapter lane need to meet in the public contract, not in
special-case glue.

### C1. Use the same public transport abstraction in replay/adapter lanes

Correction:

- External evaluator and replay paths should drive Zorn through the same public API
  transport abstraction used by certification.
- No direct internal store access.
- No adapter-only runtime route calls.

### C2. Stop synthesizing extra lifecycle rows

Correction:

- rely on real publish/update/non-live semantics from the entity store and event
  log
- keep stream ordering and non-live transitions deterministic enough that
  external evaluators do not need to fabricate additional rows to satisfy checks

### C3. Keep task/object pressure honest

Correction:

- Continue proving tasks and objects only through the existing public routes and
  official SDK/sample lanes.
- Do not add Alpha 1-only helper behavior to make the underlying surrogate
  appear healthier than it actually is.

## Definition of Done for Alpha 1

Alpha 1 is ready when these are true:

1. Entity parity probe is green for:
   - REST publish -> gRPC read/stream
   - gRPC publish -> REST read/events
   - REST override -> gRPC read
   - gRPC override -> REST read
   - REST remove-override -> gRPC read
   - gRPC remove-override -> REST read
   - REST non-live -> gRPC read
   - gRPC non-live -> REST read
2. OAuth-dev uses distinct issued tokens with real expiry enforcement.
3. REST and gRPC auth both honor the configured bearer/sandbox startup modes.
4. External evaluators no longer need synthetic entity lifecycle rows to satisfy stream
   verification.
5. All of the above are proven by current tests and certification artifacts, not
   by prose or a Zorn-only diagnostics route.

## Recommended Implementation Order

1. Fix gRPC `OverrideEntityRequest` parsing.
2. Fix gRPC `is_live=false` scalar preservation.
3. Implement internal base-state restoration for override removal.
4. Add issued-token store with expiry enforcement behind existing OAuth-dev
   flow.
5. Accept sandbox-header metadata on gRPC when required by startup config.
6. Re-run external evaluator gap probes and promote the remaining unknowns to explicit
   documented defer items.

## Explicit Defer Items

These should not block Alpha 1 unless a public client proves they are required:

- refresh-token support
- rich scope authorization policy
- vendor-only auth/session claims
- any new verification or backend self-description endpoint
- UI or scenario features in the compatibility layer
