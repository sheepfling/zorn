from __future__ import annotations

from pathlib import Path

import pytest

from zorn.config import load_settings


def test_load_settings_from_toml_profile(tmp_path: Path) -> None:
    secret_file = tmp_path / "secrets" / "oauth-dev.seed"
    secret_file.parent.mkdir(parents=True, exist_ok=True)
    secret_file.write_text("toml-secret", encoding="utf-8")

    config_file = tmp_path / "zorn.toml"
    config_file.write_text(
        """
[app]
product_name = "Toml Zorn"
compatibility_target = "TOML profile"
api_prefix = "/compat/v1"

[auth]
mode = "oauth-dev"
static_tokens = ["alpha-token", "beta-token"]
oauth_dev_token_ttl_seconds = 1234
oauth_dev_token_mode = "strict"
oauth_dev_signing_secret_file = "./secrets/oauth-dev.seed"
oauth_scope_mode = "informational"
require_sandbox_header = true
grpc_sandbox_auth_mode = "strict_separate"
strict_startup = true

[storage]
database_url = "sqlite:///./var/toml.db"
object_root = "./objects"
max_object_bytes = 4096

[behavior]
allow_generated_entity_ids = false
enforce_source_update_time = false
heartbeat_seconds = 0.5
poll_interval_seconds = 0.05

[grpc]
host = "0.0.0.0"
port = 50055
tls_mode = "provided"
tls_cert_path = "./tls/server.pem"
tls_key_path = "./tls/server-key.pem"
strict_proto_audit = true
enforce_task_status_version = false
""".strip(),
        encoding="utf-8",
    )

    settings = load_settings(config_path=config_file)

    assert settings.product_name == "Toml Zorn"
    assert settings.compatibility_target == "TOML profile"
    assert settings.api_prefix == "/compat/v1"
    assert settings.auth_mode == "oauth-dev"
    assert settings.static_tokens == ["alpha-token", "beta-token"]
    assert settings.oauth_dev_token_mode == "strict"
    assert settings.oauth_dev_token_ttl_seconds == 1234
    assert settings.oauth_dev_signing_secret == "toml-secret"
    assert settings.oauth_scope_mode == "informational"
    assert settings.require_sandbox_header is True
    assert settings.grpc_sandbox_auth_mode == "strict_separate"
    assert settings.strict_startup is True
    assert settings.database_url == "sqlite:///./var/toml.db"
    assert settings.object_root == tmp_path / "objects"
    assert settings.max_object_bytes == 4096
    assert settings.allow_generated_entity_ids is False
    assert settings.enforce_source_update_time is False
    assert settings.heartbeat_seconds == 0.5
    assert settings.poll_interval_seconds == 0.05
    assert settings.grpc_host == "0.0.0.0"
    assert settings.grpc_port == 50055
    assert settings.grpc_tls_mode == "provided"
    assert settings.grpc_use_tls is True
    assert settings.grpc_tls_cert_path == tmp_path / "tls" / "server.pem"
    assert settings.grpc_tls_key_path == tmp_path / "tls" / "server-key.pem"
    assert settings.grpc_strict_proto_audit is True
    assert settings.grpc_enforce_task_status_version is False


def test_env_overrides_toml_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_file = tmp_path / "zorn.toml"
    config_file.write_text(
        """
[app]
product_name = "Toml Zorn"

[auth]
mode = "static"
static_tokens = ["toml-token"]
oauth_dev_token_mode = "compat_static"

[grpc]
port = 50055
tls_mode = "provided"
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setenv("C2_COMPAT_PRODUCT_NAME", "Env Zorn")
    monkeypatch.setenv("C2_COMPAT_STATIC_TOKENS", "env-a,env-b")
    monkeypatch.setenv("C2_COMPAT_GRPC_PORT", "50099")
    monkeypatch.setenv("C2_COMPAT_GRPC_USE_TLS", "false")

    settings = load_settings(config_path=config_file)

    assert settings.product_name == "Env Zorn"
    assert settings.static_tokens == ["env-a", "env-b"]
    assert settings.oauth_dev_token_mode == "compat_static"
    assert settings.grpc_port == 50099
    assert settings.grpc_tls_mode == "insecure"
    assert settings.grpc_use_tls is False


def test_default_zorn_toml_is_discovered(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "zorn.toml").write_text(
        """
[app]
product_name = "Discovered Zorn"
""".strip(),
        encoding="utf-8",
    )

    settings = load_settings()

    assert settings.product_name == "Discovered Zorn"
