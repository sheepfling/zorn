from __future__ import annotations

import os
from pathlib import Path
from collections.abc import Mapping, Sequence
from typing import Any, Literal, cast

import tomllib

from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    product_name: str = "Zorn"
    compatibility_target: str = "Public SDK-style workflows"
    api_prefix: str = "/api/v1"
    auth_mode: Literal["none", "static", "oauth-dev"] = "none"
    static_tokens: list[str] = Field(default_factory=lambda: ["dev-token"])
    oauth_dev_token_mode: Literal["strict", "compat_static"] = "strict"
    oauth_dev_token_ttl_seconds: int = 3600
    oauth_dev_signing_secret: str | None = None
    oauth_scope_mode: Literal["informational", "locked"] = "informational"
    require_sandbox_header: bool = False
    grpc_sandbox_auth_mode: Literal["legacy_bearer", "strict_separate"] = "legacy_bearer"
    strict_startup: bool = False
    database_url: str = "sqlite:///./var/zorn.db"
    object_root: Path = Path("./var/objects")
    max_object_bytes: int = 64 * 1024 * 1024
    allow_generated_entity_ids: bool = True
    enforce_source_update_time: bool = True
    heartbeat_seconds: float = 15.0
    poll_interval_seconds: float = 0.25
    grpc_host: str = "127.0.0.1"
    grpc_port: int = 50051
    grpc_tls_mode: Literal["insecure", "self-signed", "provided"] = "insecure"
    grpc_use_tls: bool = False
    grpc_tls_cert_path: Path | None = None
    grpc_tls_key_path: Path | None = None
    grpc_strict_proto_audit: bool = True
    grpc_enforce_task_status_version: bool = True
####


_MISSING = object()


def _split_tokens(raw_tokens: str) -> list[str]:
    return [token.strip() for token in raw_tokens.split(",") if token.strip()]
####


def _is_truthy(raw_value: str) -> bool:
    return raw_value.lower() in {"1", "true", "yes", "on"}
####


def _optional_path_from_env(name: str) -> Path | None:
    value = os.getenv(name)
    return Path(value) if value else None
####


def _optional_secret_from_env(name: str) -> str | None:
    value = os.getenv(name)
    return value if value else None
####


def _optional_secret_from_file(name: str) -> str | None:
    value = os.getenv(name)
    if not value:
        return None
    return Path(value).read_text(encoding="utf-8").strip() or None
####


def _env_value(name: str) -> str | None:
    value = os.getenv(name)
    return value if value else None
####


def _source_value(env_name: str, toml_value: Any, default: Any) -> Any:
    env_value = _env_value(env_name)
    if env_value is not None:
        return env_value
    ####
    if toml_value is not _MISSING:
        return toml_value
    ####
    return default
####


def _resolve_config_path(explicit_path: str | Path | None) -> Path | None:
    if explicit_path is not None:
        return Path(explicit_path)
    ####
    env_path = os.getenv("C2_COMPAT_CONFIG_FILE")
    if env_path:
        return Path(env_path)
    ####
    default_path = Path("zorn.toml")
    if default_path.exists():
        return default_path
    ####
    return None
####


def _load_toml_config(config_path: Path | None) -> tuple[dict[str, Any], Path | None]:
    if config_path is None:
        return {}, None
    ####
    if not config_path.exists():
        raise FileNotFoundError(config_path)
    ####
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)
    ####
    if not isinstance(raw, dict):
        raise TypeError(f"{config_path} must contain a TOML table at the top level")
    ####
    return raw, config_path.parent
####


def _toml_section(raw: Mapping[str, Any], section: str) -> Mapping[str, Any]:
    value = raw.get(section)
    return value if isinstance(value, Mapping) else {}
####


def _toml_value(raw: Mapping[str, Any], section: str, *keys: str) -> Any:
    section_data = _toml_section(raw, section)
    for key in keys:
        if key in section_data:
            return section_data[key]
    ####
    for key in keys:
        if key in raw:
            return raw[key]
    ####
    return _MISSING
####


def _toml_string(raw: Mapping[str, Any], section: str, *keys: str) -> Any:
    value = _toml_value(raw, section, *keys)
    if value is _MISSING:
        return _MISSING
    ####
    return str(value)
####


def _toml_bool(raw: Mapping[str, Any], section: str, *keys: str) -> Any:
    value = _toml_value(raw, section, *keys)
    if value is _MISSING:
        return _MISSING
    ####
    if isinstance(value, bool):
        return value
    ####
    if isinstance(value, str):
        return _is_truthy(value)
    ####
    return bool(value)
####


def _toml_int(raw: Mapping[str, Any], section: str, *keys: str) -> Any:
    value = _toml_value(raw, section, *keys)
    if value is _MISSING:
        return _MISSING
    ####
    return int(value)
####


def _toml_float(raw: Mapping[str, Any], section: str, *keys: str) -> Any:
    value = _toml_value(raw, section, *keys)
    if value is _MISSING:
        return _MISSING
    ####
    return float(value)
####


def _toml_tokens(raw: Mapping[str, Any], section: str, *keys: str) -> Any:
    value = _toml_value(raw, section, *keys)
    if value is _MISSING:
        return _MISSING
    ####
    if isinstance(value, str):
        return _split_tokens(value)
    ####
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [str(token).strip() for token in value if str(token).strip()]
    ####
    raise TypeError(f"Expected a string or string array for {section}.{keys[0]}")
####


def _toml_path(raw: Mapping[str, Any], section: str, base_dir: Path | None, *keys: str) -> Any:
    value = _toml_value(raw, section, *keys)
    if value is _MISSING:
        return _MISSING
    ####
    path = Path(str(value))
    if path.is_absolute() or base_dir is None:
        return path
    ####
    return base_dir / path
####


def _oauth_secret_from_toml(raw: Mapping[str, Any], base_dir: Path | None) -> str | None:
    env_secret = _optional_secret_from_env("C2_COMPAT_OAUTH_DEV_SIGNING_SECRET")
    if env_secret:
        return env_secret
    ####
    env_secret_file = _optional_secret_from_file("C2_COMPAT_OAUTH_DEV_SIGNING_SECRET_FILE")
    if env_secret_file:
        return env_secret_file
    ####
    inline_secret = _toml_string(raw, "auth", "oauth_dev_signing_secret", "signing_secret")
    if inline_secret is not _MISSING and inline_secret:
        return inline_secret
    ####
    secret_file = _toml_path(raw, "auth", base_dir, "oauth_dev_signing_secret_file", "signing_secret_file")
    if secret_file is _MISSING:
        return None
    ####
    return Path(secret_file).read_text(encoding="utf-8").strip() or None
####


def _grpc_tls_mode_from_sources(raw: Mapping[str, Any]) -> Literal["insecure", "self-signed", "provided"]:
    raw_mode = os.getenv("C2_COMPAT_GRPC_TLS_MODE")
    if raw_mode in {"insecure", "self-signed", "provided"}:
        return cast(Literal["insecure", "self-signed", "provided"], raw_mode)
    ####
    raw_use_tls = os.getenv("C2_COMPAT_GRPC_USE_TLS")
    if raw_use_tls is not None:
        return "provided" if _is_truthy(raw_use_tls) else "insecure"
    ####
    toml_mode = _toml_string(raw, "grpc", "grpc_tls_mode", "tls_mode")
    if toml_mode is not _MISSING and toml_mode in {"insecure", "self-signed", "provided"}:
        return cast(Literal["insecure", "self-signed", "provided"], toml_mode)
    ####
    toml_use_tls = _toml_bool(raw, "grpc", "grpc_use_tls", "use_tls")
    if toml_use_tls is not _MISSING:
        return "provided" if toml_use_tls else "insecure"
    ####
    return "insecure"
####


def _grpc_tls_mode_from_env() -> Literal["insecure", "self-signed", "provided"]:
    raw_mode = os.getenv("C2_COMPAT_GRPC_TLS_MODE")
    if raw_mode in {"insecure", "self-signed", "provided"}:
        return cast(Literal["insecure", "self-signed", "provided"], raw_mode)
    ####
    if os.getenv("C2_COMPAT_GRPC_USE_TLS", "false").lower() in {"1", "true", "yes"}:
        return "provided"
    ####
    return "insecure"
####


def load_settings(config_path: Path | str | None = None) -> AppSettings:
    resolved_config_path = _resolve_config_path(config_path)
    toml_data, toml_dir = _load_toml_config(resolved_config_path)

    grpc_tls_mode = _grpc_tls_mode_from_sources(toml_data)
    grpc_use_tls = grpc_tls_mode != "insecure"
    product_name = _source_value("C2_COMPAT_PRODUCT_NAME", _toml_string(toml_data, "app", "product_name"), "Zorn")
    compatibility_target = _source_value(
        "C2_COMPAT_COMPATIBILITY_TARGET",
        _toml_string(toml_data, "app", "compatibility_target"),
        "Public SDK-style workflows",
    )
    api_prefix = _source_value("C2_COMPAT_API_PREFIX", _toml_string(toml_data, "app", "api_prefix"), "/api/v1")
    auth_mode = _source_value("C2_COMPAT_AUTH_MODE", _toml_string(toml_data, "auth", "auth_mode", "mode"), "none")
    static_tokens_source = _env_value("C2_COMPAT_STATIC_TOKENS")
    if static_tokens_source is not None:
        static_tokens = _split_tokens(static_tokens_source)
    else:
        toml_static_tokens = _toml_tokens(toml_data, "auth", "static_tokens")
        static_tokens = toml_static_tokens if toml_static_tokens is not _MISSING else ["dev-token"]
    ####
    oauth_dev_token_ttl_seconds_source = _env_value("C2_COMPAT_OAUTH_DEV_TOKEN_TTL_SECONDS")
    if oauth_dev_token_ttl_seconds_source is not None:
        oauth_dev_token_ttl_seconds = int(oauth_dev_token_ttl_seconds_source)
    else:
        toml_ttl = _toml_int(toml_data, "auth", "oauth_dev_token_ttl_seconds", "token_ttl_seconds")
        oauth_dev_token_ttl_seconds = int(toml_ttl) if toml_ttl is not _MISSING else 3600
    ####
    oauth_dev_signing_secret = (
        _optional_secret_from_env("C2_COMPAT_OAUTH_DEV_SIGNING_SECRET")
        or _optional_secret_from_file("C2_COMPAT_OAUTH_DEV_SIGNING_SECRET_FILE")
        or _oauth_secret_from_toml(toml_data, toml_dir)
    )
    oauth_dev_token_mode = _source_value(
        "C2_COMPAT_OAUTH_DEV_TOKEN_MODE",
        _toml_string(toml_data, "auth", "oauth_dev_token_mode", "token_mode"),
        "strict",
    )
    oauth_scope_mode = _source_value(
        "C2_COMPAT_OAUTH_SCOPE_MODE",
        _toml_string(toml_data, "auth", "oauth_scope_mode", "scope_mode"),
        "informational",
    )
    require_sandbox_header_source = _env_value("C2_COMPAT_REQUIRE_SANDBOX_HEADER")
    if require_sandbox_header_source is not None:
        require_sandbox_header = _is_truthy(require_sandbox_header_source)
    else:
        toml_require_sandbox_header = _toml_bool(toml_data, "auth", "require_sandbox_header", "sandbox_header_required")
        require_sandbox_header = bool(toml_require_sandbox_header) if toml_require_sandbox_header is not _MISSING else False
    ####
    grpc_sandbox_auth_mode = _source_value(
        "C2_COMPAT_GRPC_SANDBOX_AUTH_MODE",
        _toml_string(toml_data, "auth", "grpc_sandbox_auth_mode", "sandbox_auth_mode"),
        "legacy_bearer",
    )
    strict_startup_source = _env_value("C2_COMPAT_STRICT_STARTUP")
    if strict_startup_source is not None:
        strict_startup = _is_truthy(strict_startup_source)
    else:
        toml_strict_startup = _toml_bool(toml_data, "auth", "strict_startup")
        strict_startup = bool(toml_strict_startup) if toml_strict_startup is not _MISSING else False
    ####
    database_url = _source_value("C2_COMPAT_DATABASE_URL", _toml_string(toml_data, "storage", "database_url"), "sqlite:///./var/zorn.db")
    object_root_env = _optional_path_from_env("C2_COMPAT_OBJECT_ROOT")
    if object_root_env is not None:
        object_root = object_root_env
    else:
        toml_object_root = _toml_path(toml_data, "storage", toml_dir, "object_root")
        object_root = toml_object_root if toml_object_root is not _MISSING else Path("./var/objects")
    ####
    max_object_bytes_source = _env_value("C2_COMPAT_MAX_OBJECT_BYTES")
    if max_object_bytes_source is not None:
        max_object_bytes = int(max_object_bytes_source)
    else:
        toml_max_object_bytes = _toml_int(toml_data, "storage", "max_object_bytes")
        max_object_bytes = int(toml_max_object_bytes) if toml_max_object_bytes is not _MISSING else 64 * 1024 * 1024
    ####
    allow_generated_entity_ids_source = _env_value("C2_COMPAT_ALLOW_GENERATED_ENTITY_IDS")
    if allow_generated_entity_ids_source is not None:
        allow_generated_entity_ids = _is_truthy(allow_generated_entity_ids_source)
    else:
        toml_allow_generated_entity_ids = _toml_bool(toml_data, "behavior", "allow_generated_entity_ids")
        allow_generated_entity_ids = bool(toml_allow_generated_entity_ids) if toml_allow_generated_entity_ids is not _MISSING else True
    ####
    enforce_source_update_time_source = _env_value("C2_COMPAT_ENFORCE_SOURCE_UPDATE_TIME")
    if enforce_source_update_time_source is not None:
        enforce_source_update_time = _is_truthy(enforce_source_update_time_source)
    else:
        toml_enforce_source_update_time = _toml_bool(toml_data, "behavior", "enforce_source_update_time")
        enforce_source_update_time = bool(toml_enforce_source_update_time) if toml_enforce_source_update_time is not _MISSING else True
    ####
    heartbeat_seconds_source = _env_value("C2_COMPAT_HEARTBEAT_SECONDS")
    if heartbeat_seconds_source is not None:
        heartbeat_seconds = float(heartbeat_seconds_source)
    else:
        toml_heartbeat_seconds = _toml_float(toml_data, "behavior", "heartbeat_seconds")
        heartbeat_seconds = float(toml_heartbeat_seconds) if toml_heartbeat_seconds is not _MISSING else 15.0
    ####
    poll_interval_seconds_source = _env_value("C2_COMPAT_POLL_INTERVAL_SECONDS")
    if poll_interval_seconds_source is not None:
        poll_interval_seconds = float(poll_interval_seconds_source)
    else:
        toml_poll_interval_seconds = _toml_float(toml_data, "behavior", "poll_interval_seconds")
        poll_interval_seconds = float(toml_poll_interval_seconds) if toml_poll_interval_seconds is not _MISSING else 0.25
    ####
    grpc_host = _source_value("C2_COMPAT_GRPC_HOST", _toml_string(toml_data, "grpc", "grpc_host", "host"), "127.0.0.1")
    grpc_port_source = _env_value("C2_COMPAT_GRPC_PORT")
    if grpc_port_source is not None:
        grpc_port = int(grpc_port_source)
    else:
        toml_grpc_port = _toml_int(toml_data, "grpc", "grpc_port", "port")
        grpc_port = int(toml_grpc_port) if toml_grpc_port is not _MISSING else 50051
    ####
    grpc_tls_cert_path = _optional_path_from_env("C2_COMPAT_GRPC_TLS_CERT_PATH")
    if grpc_tls_cert_path is None:
        toml_tls_cert_path = _toml_path(toml_data, "grpc", toml_dir, "grpc_tls_cert_path", "tls_cert_path")
        grpc_tls_cert_path = toml_tls_cert_path if toml_tls_cert_path is not _MISSING else None
    ####
    grpc_tls_key_path = _optional_path_from_env("C2_COMPAT_GRPC_TLS_KEY_PATH")
    if grpc_tls_key_path is None:
        toml_tls_key_path = _toml_path(toml_data, "grpc", toml_dir, "grpc_tls_key_path", "tls_key_path")
        grpc_tls_key_path = toml_tls_key_path if toml_tls_key_path is not _MISSING else None
    ####
    grpc_strict_proto_audit_source = _env_value("C2_COMPAT_GRPC_STRICT_PROTO_AUDIT")
    if grpc_strict_proto_audit_source is not None:
        grpc_strict_proto_audit = _is_truthy(grpc_strict_proto_audit_source)
    else:
        toml_grpc_strict_proto_audit = _toml_bool(toml_data, "grpc", "grpc_strict_proto_audit", "strict_proto_audit")
        grpc_strict_proto_audit = bool(toml_grpc_strict_proto_audit) if toml_grpc_strict_proto_audit is not _MISSING else True
    ####
    grpc_enforce_task_status_version_source = _env_value("C2_COMPAT_GRPC_ENFORCE_TASK_STATUS_VERSION")
    if grpc_enforce_task_status_version_source is not None:
        grpc_enforce_task_status_version = _is_truthy(grpc_enforce_task_status_version_source)
    else:
        toml_grpc_enforce_task_status_version = _toml_bool(toml_data, "grpc", "grpc_enforce_task_status_version", "enforce_task_status_version")
        grpc_enforce_task_status_version = (
            bool(toml_grpc_enforce_task_status_version) if toml_grpc_enforce_task_status_version is not _MISSING else True
        )
    ####

    return AppSettings(
        product_name=product_name,
        compatibility_target=compatibility_target,
        api_prefix=api_prefix,
        auth_mode=auth_mode,  # type: ignore[arg-type]
        static_tokens=static_tokens,
        oauth_dev_token_mode=oauth_dev_token_mode,  # type: ignore[arg-type]
        oauth_dev_token_ttl_seconds=oauth_dev_token_ttl_seconds,
        oauth_dev_signing_secret=oauth_dev_signing_secret,
        oauth_scope_mode=oauth_scope_mode,  # type: ignore[arg-type]
        require_sandbox_header=require_sandbox_header,
        grpc_sandbox_auth_mode=grpc_sandbox_auth_mode,  # type: ignore[arg-type]
        strict_startup=strict_startup,
        database_url=database_url,
        object_root=object_root,
        max_object_bytes=max_object_bytes,
        allow_generated_entity_ids=allow_generated_entity_ids,
        enforce_source_update_time=enforce_source_update_time,
        heartbeat_seconds=heartbeat_seconds,
        poll_interval_seconds=poll_interval_seconds,
        grpc_host=grpc_host,
        grpc_port=grpc_port,
        grpc_tls_mode=grpc_tls_mode,
        grpc_use_tls=grpc_use_tls,
        grpc_tls_cert_path=grpc_tls_cert_path,
        grpc_tls_key_path=grpc_tls_key_path,
        grpc_strict_proto_audit=grpc_strict_proto_audit,
        grpc_enforce_task_status_version=grpc_enforce_task_status_version,
    )
####
