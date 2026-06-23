# Zorn Configuration

Zorn is configured at startup. There is no runtime config API and no admin
route for changing surrogate behavior after boot.

The supported configuration sources are:

1. Environment variables with the `C2_COMPAT_` prefix.
2. An optional TOML profile file, usually `zorn.toml`.

Environment variables always override TOML values. The TOML file is a profile
layer for repeatable local runs, CI, and operator documentation.

TOML field names are allowed to use the more concise section aliases that show
up in the example profile:

- `auth.mode` as an alias for `auth_mode`
- `grpc.host` and `grpc.port` as aliases for the gRPC listener fields
- `grpc.tls_mode` as the canonical transport flag, with `grpc.use_tls` kept as
  a legacy alias

## Profile Discovery

Zorn looks for a TOML profile in this order:

1. An explicit path passed to `load_settings(...)`.
2. `C2_COMPAT_CONFIG_FILE`.
3. `./zorn.toml` in the current working directory.

If the configured TOML path does not exist, startup fails fast.

## Configuration Groups

The current startup surface is broader than auth. The main groups are:

### App Identity

- `product_name`
- `compatibility_target`
- `api_prefix`

These control the app title, description, and route prefixing. They do not
change the public Lattice contract.

### Auth

- `auth_mode`
- `static_tokens`
- `oauth_dev_token_ttl_seconds`
- `oauth_dev_token_mode`
- `oauth_dev_signing_secret`
- `oauth_dev_signing_secret_file`
- `oauth_scope_mode`
- `require_sandbox_header`
- `grpc_sandbox_auth_mode`
- `strict_startup`

These control bearer acceptance, OAuth-dev issuance, sandbox enforcement, and
the strict surrogate profile.

The important auth-only knobs are:

- `oauth_dev_signing_secret` or `oauth_dev_signing_secret_file` to seed issued
  OAuth-dev tokens at startup
- `oauth_dev_token_mode` to choose strict signed tokens or a static-bearer
  compatibility profile
- `oauth_dev_token_mode` to choose strict signed tokens or a looser
  compatibility profile that reuses startup bearer state
- `oauth_scope_mode` to keep scope informational or to lock the issuance path
- `grpc_sandbox_auth_mode` to separate or relax the sandbox metadata story for
  fault-injection profiles
- the existing `/api/v1/oauth/token` route behaves like a client-credentials
  issuance path in OAuth-dev mode; invalid grant types are rejected, and
  client_id/client_secret must be present

### Storage

- `database_url`
- `object_root`
- `max_object_bytes`

These control local persistence and object storage behavior.

### Behavior

- `allow_generated_entity_ids`
- `enforce_source_update_time`
- `heartbeat_seconds`
- `poll_interval_seconds`

These control lifecycle rules, stale-update handling, and stream timing.

### gRPC / Transport

- `grpc_host`
- `grpc_port`
- `grpc_tls_mode`
- `grpc_tls_cert_path`
- `grpc_tls_key_path`
- `grpc_strict_proto_audit`
- `grpc_enforce_task_status_version`

These control the gRPC listener and the stricter contract checks used by the
compatibility harness.

`grpc_tls_mode` is the canonical transport setting. `grpc_use_tls` is retained
as an alias so older startup profiles can still be translated cleanly into the
same gRPC behavior.

## Canonical Strict Profile

The faithful Alpha 1 / strict-surrogate profile is:

```toml
[app]
product_name = "Zorn"
compatibility_target = "Public SDK-style workflows"
api_prefix = "/api/v1"

[auth]
mode = "oauth-dev"
static_tokens = ["dev-token"]
oauth_dev_token_ttl_seconds = 3600
oauth_dev_token_mode = "strict"
oauth_dev_signing_secret_file = "./secrets/oauth-dev.seed"
oauth_scope_mode = "informational"
require_sandbox_header = true
grpc_sandbox_auth_mode = "strict_separate"
strict_startup = true

[storage]
database_url = "sqlite:///./var/zorn.db"
object_root = "./var/objects"
max_object_bytes = 67108864

[behavior]
allow_generated_entity_ids = true
enforce_source_update_time = true
heartbeat_seconds = 15.0
poll_interval_seconds = 0.25

[grpc]
host = "127.0.0.1"
port = 50051
tls_mode = "insecure"
strict_proto_audit = true
enforce_task_status_version = true
```

The strict startup contract still requires the same public Lattice-compatible
shape:

- auth must be enabled
- sandbox headers must be enforced
- gRPC proto auditing must stay on
- OAuth-dev must have a trust seed and positive TTL
- OAuth scope handling stays informational in strict mode
- gRPC sandbox metadata stays separate from bearer credentials in strict mode

## Startup Overrides

Use env vars when you want to override a local TOML profile temporarily. For
example:

```bash
C2_COMPAT_CONFIG_FILE=./zorn.toml \
C2_COMPAT_GRPC_PORT=50052 \
C2_COMPAT_AUTH_MODE=static \
.venv/bin/uvicorn zorn.main:app --host 127.0.0.1 --port 8080
```

The process still boots with the same strict validation rules. Overrides do not
create a new runtime API.

## Notes on Auth Realism

Auth realism is intentionally startup-driven:

- issued OAuth-dev tokens are signed at startup from a configured secret and
  rotate so only the most recently issued strict token remains active
- token issuance can be switched into a looser startup-only compatibility
  profile when required, but strict startup keeps the strict mode selected
- bearer and sandbox metadata are validated through the existing REST/gRPC
  paths
- refresh-token semantics remain a live-Lattice gap until a real route proves
  they belong
- richer scope policy remains a gap unless a public client or live vendor route
  proves otherwise

## Non-Goals

- runtime config mutation
- new diagnostics endpoints
- new auth control routes
- inventing Lattice surfaces that are not publicly validated
