from __future__ import annotations

from .config import AppSettings


class StrictStartupError(RuntimeError):
    pass
####


def validate_strict_startup(settings: AppSettings) -> None:
    if not settings.strict_startup:
        return
    ####
    errors: list[str] = []
    if settings.auth_mode == "none":
        errors.append("C2_COMPAT_AUTH_MODE must not be none in strict startup mode")
    ####
    if not settings.static_tokens:
        errors.append("C2_COMPAT_STATIC_TOKENS must contain at least one token in strict startup mode")
    ####
    if not settings.require_sandbox_header:
        errors.append("C2_COMPAT_REQUIRE_SANDBOX_HEADER must be true in strict startup mode")
    ####
    if not settings.grpc_strict_proto_audit:
        errors.append("C2_COMPAT_GRPC_STRICT_PROTO_AUDIT must be true in strict startup mode")
    ####
    if settings.auth_mode == "oauth-dev" and settings.oauth_dev_token_ttl_seconds <= 0:
        errors.append("C2_COMPAT_OAUTH_DEV_TOKEN_TTL_SECONDS must be positive in oauth-dev strict startup mode")
    ####
    if errors:
        raise StrictStartupError("Strict startup validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    ####
####
