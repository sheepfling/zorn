# Strict Startup Contract

Strict startup is the fail-fast configuration profile for Zorn when the goal is
to emulate the public Lattice endpoint as tightly as the current surface
allows.

It does not add any new runtime API. It only constrains startup configuration so
the process refuses to boot unless the existing compatibility layer is enabled
in the right shape.

## Purpose

The strict startup profile exists to keep the surrogate honest:

- auth must be enabled
- sandbox header enforcement must be enabled
- gRPC descriptor auditing must remain enabled
- OAuth-dev tokens must be issued and validated as real lifecycle tokens
- OAuth-dev token issuance must stay in strict mode for the faithful profile
- OAuth scope handling should stay informational in strict mode
- gRPC sandbox metadata should remain separate from bearer credentials in the
  faithful profile
- the startup config must not silently drift into a convenience mode

## Required Settings

When `C2_COMPAT_STRICT_STARTUP=true`, the process must validate:

- `C2_COMPAT_AUTH_MODE` is not `none`
- `C2_COMPAT_STATIC_TOKENS` is not empty
- `C2_COMPAT_REQUIRE_SANDBOX_HEADER=true`
- `C2_COMPAT_GRPC_STRICT_PROTO_AUDIT=true`
- `C2_COMPAT_OAUTH_DEV_TOKEN_TTL_SECONDS` is positive when `oauth-dev` is used
- `C2_COMPAT_OAUTH_DEV_TOKEN_MODE=strict`
- `C2_COMPAT_OAUTH_DEV_SIGNING_SECRET` or `C2_COMPAT_OAUTH_DEV_SIGNING_SECRET_FILE` is set when `oauth-dev` is used
- `C2_COMPAT_OAUTH_SCOPE_MODE=informational`
- `C2_COMPAT_GRPC_SANDBOX_AUTH_MODE=strict_separate`

## Recommended Strict Profile

The most faithful current profile is:

```bash
C2_COMPAT_STRICT_STARTUP=true
C2_COMPAT_AUTH_MODE=oauth-dev
C2_COMPAT_REQUIRE_SANDBOX_HEADER=true
C2_COMPAT_GRPC_STRICT_PROTO_AUDIT=true
C2_COMPAT_OAUTH_DEV_TOKEN_MODE=strict
C2_COMPAT_OAUTH_DEV_TOKEN_TTL_SECONDS=3600
C2_COMPAT_OAUTH_DEV_SIGNING_SECRET=replace-with-real-seed
C2_COMPAT_OAUTH_SCOPE_MODE=informational
C2_COMPAT_GRPC_SANDBOX_AUTH_MODE=strict_separate
```

TLS can still be configured separately using the existing gRPC TLS settings.
Strict startup does not invent a new transport mode.

## Failure Behavior

If a required strict setting is missing or invalid, Zorn should fail at startup
with a single error that lists the violated startup constraints.

That is preferable to booting a permissive surrogate that looks healthy but is
actually running in a weaker auth mode.

## Non-Goals

- refresh-token endpoints
- new diagnostics endpoints
- new startup API routes
- startup-time replacement of the public Lattice contract

The non-strict compatibility profile may keep `C2_COMPAT_GRPC_SANDBOX_AUTH_MODE=legacy_bearer`,
`C2_COMPAT_OAUTH_SCOPE_MODE=locked`, and `C2_COMPAT_OAUTH_DEV_TOKEN_MODE=compat_static`
for fault injection or adapter testing, but those settings are not part of the
strict surrogate claim.

## Relationship To Alpha 1

Strict startup is a guardrail for Alpha 1 and later profiles. It helps ensure
that the process used by FastDIS, sample apps, and cert fixtures is the same
shape the surrogate intends to support, without widening the public API surface.

The same startup contract can be expressed either through `C2_COMPAT_*`
environment variables or an optional `zorn.toml` profile. Env vars override the
TOML file. See `design/zorn-configuration.md` for the full configuration map.
