from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    product_name: str = "Zorn"
    compatibility_target: str = "Public SDK-style workflows"
    api_prefix: str = "/api/v1"
    auth_mode: Literal["none", "static", "oauth-dev"] = "none"
    static_tokens: list[str] = Field(default_factory=lambda: ["dev-token"])
    require_sandbox_header: bool = False
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


def _split_tokens(raw_tokens: str) -> list[str]:
    return [token.strip() for token in raw_tokens.split(",") if token.strip()]
####


def _optional_path_from_env(name: str) -> Path | None:
    value = os.getenv(name)
    return Path(value) if value else None
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


def load_settings() -> AppSettings:
    grpc_tls_mode = _grpc_tls_mode_from_env()
    return AppSettings(
        product_name=os.getenv("C2_COMPAT_PRODUCT_NAME", "Zorn"),
        compatibility_target=os.getenv(
            "C2_COMPAT_COMPATIBILITY_TARGET",
            "Public SDK-style workflows",
        ),
        api_prefix=os.getenv("C2_COMPAT_API_PREFIX", "/api/v1"),
        auth_mode=os.getenv("C2_COMPAT_AUTH_MODE", "none"),  # type: ignore[arg-type]
        static_tokens=_split_tokens(os.getenv("C2_COMPAT_STATIC_TOKENS", "dev-token")),
        require_sandbox_header=os.getenv("C2_COMPAT_REQUIRE_SANDBOX_HEADER", "false").lower() in {"1", "true", "yes"},
        database_url=os.getenv("C2_COMPAT_DATABASE_URL", "sqlite:///./var/zorn.db"),
        object_root=Path(os.getenv("C2_COMPAT_OBJECT_ROOT", "./var/objects")),
        max_object_bytes=int(os.getenv("C2_COMPAT_MAX_OBJECT_BYTES", str(64 * 1024 * 1024))),
        allow_generated_entity_ids=os.getenv("C2_COMPAT_ALLOW_GENERATED_ENTITY_IDS", "true").lower() in {"1", "true", "yes"},
        enforce_source_update_time=os.getenv("C2_COMPAT_ENFORCE_SOURCE_UPDATE_TIME", "true").lower() in {"1", "true", "yes"},
        heartbeat_seconds=float(os.getenv("C2_COMPAT_HEARTBEAT_SECONDS", "15")),
        poll_interval_seconds=float(os.getenv("C2_COMPAT_POLL_INTERVAL_SECONDS", "0.25")),
        grpc_host=os.getenv("C2_COMPAT_GRPC_HOST", "127.0.0.1"),
        grpc_port=int(os.getenv("C2_COMPAT_GRPC_PORT", "50051")),
        grpc_tls_mode=grpc_tls_mode,
        grpc_use_tls=grpc_tls_mode != "insecure",
        grpc_tls_cert_path=_optional_path_from_env("C2_COMPAT_GRPC_TLS_CERT_PATH"),
        grpc_tls_key_path=_optional_path_from_env("C2_COMPAT_GRPC_TLS_KEY_PATH"),
        grpc_strict_proto_audit=os.getenv("C2_COMPAT_GRPC_STRICT_PROTO_AUDIT", "true").lower() in {"1", "true", "yes"},
        grpc_enforce_task_status_version=os.getenv("C2_COMPAT_GRPC_ENFORCE_TASK_STATUS_VERSION", "true").lower() in {"1", "true", "yes"},
    )
####
