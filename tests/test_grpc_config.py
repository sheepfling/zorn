from __future__ import annotations

from zorn.config import load_settings


def test_grpc_config_is_env_driven(monkeypatch) -> None:
    monkeypatch.setenv("C2_COMPAT_PRODUCT_NAME", "Renamable")
    monkeypatch.setenv("C2_COMPAT_GRPC_HOST", "0.0.0.0")
    monkeypatch.setenv("C2_COMPAT_GRPC_PORT", "50052")
    monkeypatch.setenv("C2_COMPAT_GRPC_USE_TLS", "true")
    monkeypatch.setenv("C2_COMPAT_GRPC_TLS_CERT_PATH", "var/certs/server.pem")
    monkeypatch.setenv("C2_COMPAT_GRPC_TLS_KEY_PATH", "var/certs/server-key.pem")
    monkeypatch.setenv("C2_COMPAT_GRPC_STRICT_PROTO_AUDIT", "false")
    monkeypatch.setenv("C2_COMPAT_GRPC_ENFORCE_TASK_STATUS_VERSION", "false")

    settings = load_settings()

    assert settings.product_name == "Renamable"
    assert settings.grpc_host == "0.0.0.0"
    assert settings.grpc_port == 50052
    assert settings.grpc_use_tls is True
    assert str(settings.grpc_tls_cert_path) == "var/certs/server.pem"
    assert str(settings.grpc_tls_key_path) == "var/certs/server-key.pem"
    assert settings.grpc_strict_proto_audit is False
    assert settings.grpc_enforce_task_status_version is False
####

