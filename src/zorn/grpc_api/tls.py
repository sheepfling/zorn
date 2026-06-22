from __future__ import annotations

from pathlib import Path

import grpc

from ..config import AppSettings


def bind_server(server: grpc.aio.Server, *, address: str, settings: AppSettings) -> None:
    if settings.grpc_tls_mode == "insecure":
        server.add_insecure_port(address)
        return
    ####
    server.add_secure_port(address, server_credentials(settings))
####


def server_credentials(settings: AppSettings) -> grpc.ServerCredentials:
    cert_file = _require_path(settings.grpc_tls_cert_path, "C2_COMPAT_GRPC_TLS_CERT_PATH")
    key_file = _require_path(settings.grpc_tls_key_path, "C2_COMPAT_GRPC_TLS_KEY_PATH")
    private_key = key_file.read_bytes()
    certificate_chain = cert_file.read_bytes()
    return grpc.ssl_server_credentials(((private_key, certificate_chain),))
####


def _require_path(path: Path | None, env_name: str) -> Path:
    if path is None:
        raise RuntimeError(f"{env_name} must be set when C2_COMPAT_GRPC_TLS_MODE requires TLS")
    ####
    if not path.exists():
        raise RuntimeError(f"{env_name} does not exist: {path}")
    ####
    return path
####
