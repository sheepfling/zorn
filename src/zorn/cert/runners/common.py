from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import ssl
import subprocess
import tempfile
import time
from typing import Any
from urllib import error, request


@dataclass(frozen=True, slots=True)
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True, slots=True)
class HttpsServerHandle:
    base_url: str
    cafile: Path | None
    process: subprocess.Popen[str]
    workspace: Path


@dataclass(frozen=True, slots=True)
class RunningProcess:
    args: list[str]
    cwd: Path
    process: subprocess.Popen[str]


@dataclass(frozen=True, slots=True)
class DualTransportServerHandle:
    rest_base_url: str
    grpc_target: str
    virtual_host: str
    cafile: Path | None
    rest_process: subprocess.Popen[str]
    grpc_process: subprocess.Popen[str]
    workspace: Path


def http_json(
    method: str,
    url: str,
    *,
    token: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 10.0,
    cafile: Path | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-api-key": token,
        "x-anduril-sandbox": "zorn-cert",
    }
    if headers:
        request_headers.update(headers)
    ####
    req = request.Request(url, data=body, headers=request_headers, method=method)
    context = ssl.create_default_context(cafile=str(cafile)) if cafile else None
    try:
        with request.urlopen(req, timeout=timeout, context=context) as response:
            text = response.read().decode("utf-8")
            return response.status, json.loads(text) if text else {}
        ####
    except error.HTTPError as exc:
        text = exc.read().decode("utf-8")
        try:
            payload = json.loads(text) if text else {}
        except json.JSONDecodeError:
            payload = {"error": text}
        ####
        return exc.code, payload
    ####
####


def http_bytes(
    method: str,
    url: str,
    *,
    token: str,
    timeout: float = 10.0,
    cafile: Path | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, bytes, dict[str, str]]:
    request_headers = {
        "Authorization": f"Bearer {token}",
        "x-api-key": token,
        "x-anduril-sandbox": "zorn-cert",
    }
    if headers:
        request_headers.update(headers)
    ####
    req = request.Request(url, headers=request_headers, method=method)
    context = ssl.create_default_context(cafile=str(cafile)) if cafile else None
    try:
        with request.urlopen(req, timeout=timeout, context=context) as response:
            return response.status, response.read(), dict(response.headers.items())
        ####
    except error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers.items())
    ####
####


def base_report(*, fixture_id: str, mode: str) -> dict[str, Any]:
    return {
        "fixture": fixture_id,
        "mode": mode,
        "result": "missing",
        "passed": [],
        "failed": [],
        "missing": [],
        "details": {},
    }
####


def ensure_python_venv(fixture_dir: Path) -> Path:
    venv_dir = fixture_dir / ".venv"
    python = venv_dir / "bin" / "python"
    if python.exists():
        return python
    ####
    if venv_dir.exists():
        shutil.rmtree(venv_dir)
    ####
    system_python = shutil.which("python3") or "python3"
    subprocess.run([system_python, "-m", "venv", str(venv_dir)], check=True, cwd=fixture_dir)
    return python
####


def run_command(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> CommandResult:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return CommandResult(
        args=list(command),
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )
####


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
    ####
####


def start_https_zorn_server(
    *,
    repo_root: Path,
    token: str,
    auth_mode: str = "oauth-dev",
    static_tokens: list[str] | None = None,
) -> HttpsServerHandle:
    workspace = Path(tempfile.mkdtemp(prefix="zorn-cert-https-"))
    cert_path = workspace / "cert.pem"
    key_path = workspace / "key.pem"
    db_path = workspace / "zorn.db"
    object_root = workspace / "objects"
    object_root.mkdir(parents=True, exist_ok=True)
    openssl = [
        "openssl",
        "req",
        "-x509",
        "-nodes",
        "-days",
        "1",
        "-newkey",
        "rsa:2048",
        "-keyout",
        str(key_path),
        "-out",
        str(cert_path),
        "-subj",
        "/CN=localhost",
        "-addext",
        "subjectAltName=DNS:localhost,IP:127.0.0.1",
    ]
    subprocess.run(openssl, cwd=repo_root, check=True, capture_output=True, text=True)
    port = find_free_port()
    env = os.environ.copy()
    env.update(
        {
            "C2_COMPAT_AUTH_MODE": auth_mode,
            "C2_COMPAT_STATIC_TOKENS": ",".join(static_tokens or [token]),
            "C2_COMPAT_DATABASE_URL": f"sqlite:///{db_path}",
            "C2_COMPAT_OBJECT_ROOT": str(object_root),
        }
    )
    command = [
        str(repo_root / ".venv" / "bin" / "python"),
        "-m",
        "uvicorn",
        "zorn.app:build_app",
        "--factory",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--ssl-keyfile",
        str(key_path),
        "--ssl-certfile",
        str(cert_path),
    ]
    process = subprocess.Popen(
        command,
        cwd=repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    base_url = f"https://localhost:{port}"
    deadline = time.time() + 15.0
    last_error = ""
    while time.time() < deadline:
        if process.poll() is not None:
            last_error = process.stdout.read() if process.stdout else ""
            raise RuntimeError(f"temporary Zorn HTTPS server exited early: {last_error}")
        ####
        try:
            status, payload = http_json("POST", f"{base_url}/api/v1/oauth/token", token=token, cafile=cert_path, payload={"client_id": "zorn-cert", "client_secret": "zorn-cert"})
            if status == 200 and payload.get("access_token"):
                return HttpsServerHandle(base_url=base_url, cafile=cert_path, process=process, workspace=workspace)
            ####
            last_error = json.dumps(payload)
        except Exception as exc:  # pragma: no cover - transient probe
            last_error = str(exc)
        ####
        time.sleep(0.2)
    ####
    stop_https_zorn_server(HttpsServerHandle(base_url=base_url, cafile=cert_path, process=process, workspace=workspace))
    raise RuntimeError(f"temporary Zorn HTTPS server failed readiness check: {last_error}")
####


def start_http_zorn_server(*, repo_root: Path, token: str) -> HttpsServerHandle:
    workspace = Path(tempfile.mkdtemp(prefix="zorn-cert-http-"))
    db_path = workspace / "zorn.db"
    object_root = workspace / "objects"
    object_root.mkdir(parents=True, exist_ok=True)
    port = find_free_port()
    env = os.environ.copy()
    env.update(
        {
            "C2_COMPAT_AUTH_MODE": "oauth-dev",
            "C2_COMPAT_STATIC_TOKENS": token,
            "C2_COMPAT_DATABASE_URL": f"sqlite:///{db_path}",
            "C2_COMPAT_OBJECT_ROOT": str(object_root),
        }
    )
    command = [
        str(repo_root / ".venv" / "bin" / "python"),
        "-m",
        "uvicorn",
        "zorn.app:build_app",
        "--factory",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    process = subprocess.Popen(
        command,
        cwd=repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 15.0
    last_error = ""
    while time.time() < deadline:
        if process.poll() is not None:
            last_error = process.stdout.read() if process.stdout else ""
            raise RuntimeError(f"temporary Zorn HTTP server exited early: {last_error}")
        ####
        try:
            status, payload = http_json("POST", f"{base_url}/api/v1/oauth/token", token=token, payload={"client_id": "zorn-cert", "client_secret": "zorn-cert"})
            if status == 200 and payload.get("access_token"):
                return HttpsServerHandle(base_url=base_url, cafile=None, process=process, workspace=workspace)
            ####
            last_error = json.dumps(payload)
        except Exception as exc:  # pragma: no cover - transient probe
            last_error = str(exc)
        ####
        time.sleep(0.2)
    ####
    stop_https_zorn_server(HttpsServerHandle(base_url=base_url, cafile=None, process=process, workspace=workspace))
    raise RuntimeError(f"temporary Zorn HTTP server failed readiness check: {last_error}")
####


def start_dual_transport_zorn_server(*, repo_root: Path, token: str) -> DualTransportServerHandle:
    workspace = Path(tempfile.mkdtemp(prefix="zorn-cert-dual-"))
    cert_path = workspace / "cert.pem"
    key_path = workspace / "key.pem"
    db_path = workspace / "zorn.db"
    object_root = workspace / "objects"
    object_root.mkdir(parents=True, exist_ok=True)
    openssl = [
        "openssl",
        "req",
        "-x509",
        "-nodes",
        "-days",
        "1",
        "-newkey",
        "rsa:2048",
        "-keyout",
        str(key_path),
        "-out",
        str(cert_path),
        "-subj",
        "/CN=localhost",
        "-addext",
        "subjectAltName=DNS:localhost,DNS:zorn-cert.local,IP:127.0.0.1",
    ]
    subprocess.run(openssl, cwd=repo_root, check=True, capture_output=True, text=True)
    rest_port = find_free_port()
    grpc_port = find_free_port()
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(repo_root / "src") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""),
            "C2_COMPAT_AUTH_MODE": "oauth-dev",
            "C2_COMPAT_STATIC_TOKENS": token,
            "C2_COMPAT_DATABASE_URL": f"sqlite:///{db_path}",
            "C2_COMPAT_OBJECT_ROOT": str(object_root),
            "C2_COMPAT_GRPC_HOST": "127.0.0.1",
            "C2_COMPAT_GRPC_PORT": str(grpc_port),
            "C2_COMPAT_GRPC_TLS_MODE": "provided",
            "C2_COMPAT_GRPC_TLS_CERT_PATH": str(cert_path),
            "C2_COMPAT_GRPC_TLS_KEY_PATH": str(key_path),
        }
    )
    rest_command = [
        str(repo_root / ".venv" / "bin" / "python"),
        "-m",
        "uvicorn",
        "zorn.app:build_app",
        "--factory",
        "--host",
        "127.0.0.1",
        "--port",
        str(rest_port),
        "--ssl-keyfile",
        str(key_path),
        "--ssl-certfile",
        str(cert_path),
    ]
    grpc_command = [
        str(repo_root / ".venv" / "bin" / "python"),
        "-m",
        "zorn.main_grpc",
    ]
    rest_process = subprocess.Popen(
        rest_command,
        cwd=repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    rest_base_url = f"https://localhost:{rest_port}"
    grpc_target = f"127.0.0.1:{grpc_port}"
    virtual_host = "zorn-cert.local"
    grpc_process: subprocess.Popen[str] | None = None
    rest_deadline = time.time() + 20.0
    rest_last_error = ""
    while time.time() < rest_deadline:
        if rest_process.poll() is not None:
            rest_last_error = rest_process.stdout.read() if rest_process.stdout else ""
            break
        ####
        try:
            status, payload = http_json("POST", f"{rest_base_url}/api/v1/oauth/token", token=token, cafile=cert_path, payload={"client_id": "zorn-cert", "client_secret": "zorn-cert"})
            if status == 200 and payload.get("access_token"):
                break
            ####
            rest_last_error = json.dumps(payload)
        except Exception as exc:  # pragma: no cover - transient probe
            rest_last_error = str(exc)
        ####
        time.sleep(0.2)
    ####
    if rest_process.poll() is not None:
        _terminate_process(rest_process)
        shutil.rmtree(workspace, ignore_errors=True)
        raise RuntimeError(f"temporary Zorn dual transport REST server failed readiness check: {rest_last_error}")
    ####
    grpc_process = subprocess.Popen(
        grpc_command,
        cwd=repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    deadline = time.time() + 20.0
    last_error = ""
    while time.time() < deadline:
        if rest_process.poll() is not None:
            last_error = rest_process.stdout.read() if rest_process.stdout else ""
            break
        ####
        if grpc_process.poll() is not None:
            last_error = grpc_process.stdout.read() if grpc_process.stdout else ""
            break
        ####
        try:
            status, payload = http_json("POST", f"{rest_base_url}/api/v1/oauth/token", token=token, cafile=cert_path, payload={"client_id": "zorn-cert", "client_secret": "zorn-cert"})
            if status == 200 and payload.get("access_token") and _tcp_ready("127.0.0.1", grpc_port):
                return DualTransportServerHandle(
                    rest_base_url=rest_base_url,
                    grpc_target=grpc_target,
                    virtual_host=virtual_host,
                    cafile=cert_path,
                    rest_process=rest_process,
                    grpc_process=grpc_process,
                    workspace=workspace,
                )
            ####
            last_error = json.dumps(payload)
        except Exception as exc:  # pragma: no cover - transient probe
            last_error = str(exc)
        ####
        time.sleep(0.2)
    ####
    stop_dual_transport_zorn_server(
        DualTransportServerHandle(
            rest_base_url=rest_base_url,
            grpc_target=grpc_target,
            virtual_host=virtual_host,
            cafile=cert_path,
            rest_process=rest_process,
            grpc_process=grpc_process,
            workspace=workspace,
        )
    )
    raise RuntimeError(f"temporary Zorn dual transport server failed readiness check: {last_error}")
####


def start_http_insecure_grpc_zorn_server(*, repo_root: Path, token: str) -> DualTransportServerHandle:
    workspace = Path(tempfile.mkdtemp(prefix="zorn-cert-dual-insecure-"))
    db_path = workspace / "zorn.db"
    object_root = workspace / "objects"
    object_root.mkdir(parents=True, exist_ok=True)
    rest_port = find_free_port()
    grpc_port = find_free_port()
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(repo_root / "src") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""),
            "C2_COMPAT_AUTH_MODE": "static",
            "C2_COMPAT_STATIC_TOKENS": token,
            "C2_COMPAT_DATABASE_URL": f"sqlite:///{db_path}",
            "C2_COMPAT_OBJECT_ROOT": str(object_root),
            "C2_COMPAT_GRPC_HOST": "127.0.0.1",
            "C2_COMPAT_GRPC_PORT": str(grpc_port),
            "C2_COMPAT_GRPC_TLS_MODE": "insecure",
        }
    )
    rest_command = [
        str(repo_root / ".venv" / "bin" / "python"),
        "-m",
        "uvicorn",
        "zorn.app:build_app",
        "--factory",
        "--host",
        "127.0.0.1",
        "--port",
        str(rest_port),
    ]
    grpc_command = [
        str(repo_root / ".venv" / "bin" / "python"),
        "-m",
        "zorn.main_grpc",
    ]
    rest_process = subprocess.Popen(
        rest_command,
        cwd=repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    rest_base_url = f"http://127.0.0.1:{rest_port}"
    grpc_target = f"127.0.0.1:{grpc_port}"
    virtual_host = "127.0.0.1"
    grpc_process: subprocess.Popen[str] | None = None
    rest_deadline = time.time() + 20.0
    rest_last_error = ""
    while time.time() < rest_deadline:
        if rest_process.poll() is not None:
            rest_last_error = rest_process.stdout.read() if rest_process.stdout else ""
            break
        ####
        try:
            status, payload = http_json("POST", f"{rest_base_url}/api/v1/oauth/token", token=token, payload={"client_id": "zorn-cert", "client_secret": "zorn-cert"})
            if status == 200 and payload.get("access_token"):
                break
            ####
            rest_last_error = json.dumps(payload)
        except Exception as exc:  # pragma: no cover - transient probe
            rest_last_error = str(exc)
        ####
        time.sleep(0.2)
    ####
    if rest_process.poll() is not None:
        _terminate_process(rest_process)
        shutil.rmtree(workspace, ignore_errors=True)
        raise RuntimeError(f"temporary Zorn HTTP+gRPC REST server failed readiness check: {rest_last_error}")
    ####
    grpc_process = subprocess.Popen(
        grpc_command,
        cwd=repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    deadline = time.time() + 20.0
    last_error = ""
    while time.time() < deadline:
        if rest_process.poll() is not None:
            last_error = rest_process.stdout.read() if rest_process.stdout else ""
            break
        ####
        if grpc_process.poll() is not None:
            last_error = grpc_process.stdout.read() if grpc_process.stdout else ""
            break
        ####
        try:
            status, payload = http_json("POST", f"{rest_base_url}/api/v1/oauth/token", token=token, payload={"client_id": "zorn-cert", "client_secret": "zorn-cert"})
            if status == 200 and payload.get("access_token") and _tcp_ready("127.0.0.1", grpc_port):
                return DualTransportServerHandle(
                    rest_base_url=rest_base_url,
                    grpc_target=grpc_target,
                    virtual_host=virtual_host,
                    cafile=None,
                    rest_process=rest_process,
                    grpc_process=grpc_process,
                    workspace=workspace,
                )
            ####
            last_error = json.dumps(payload)
        except Exception as exc:  # pragma: no cover - transient probe
            last_error = str(exc)
        ####
        time.sleep(0.2)
    ####
    stop_dual_transport_zorn_server(
        DualTransportServerHandle(
            rest_base_url=rest_base_url,
            grpc_target=grpc_target,
            virtual_host=virtual_host,
            cafile=None,
            rest_process=rest_process,
            grpc_process=grpc_process,
            workspace=workspace,
        )
    )
    raise RuntimeError(f"temporary Zorn HTTP+insecure gRPC server failed readiness check: {last_error}")
####


def stop_https_zorn_server(server: HttpsServerHandle) -> str:
    return _terminate_process(server.process)
####


def stop_dual_transport_zorn_server(server: DualTransportServerHandle) -> dict[str, str]:
    outputs = {
        "rest": _terminate_process(server.rest_process),
        "grpc": _terminate_process(server.grpc_process),
    }
    shutil.rmtree(server.workspace, ignore_errors=True)
    return outputs
####


def start_process(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> RunningProcess:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    return RunningProcess(args=list(command), cwd=cwd, process=process)
####


def stop_process(handle: RunningProcess, *, timeout: float = 5.0) -> tuple[int, str]:
    stdout = _terminate_process(handle.process, timeout=timeout)
    return handle.process.returncode or 0, stdout
####


def _tcp_ready(host: str, port: int) -> bool:
    with suppress(OSError):
        with socket.create_connection((host, port), timeout=0.5):
            return True
        ####
    ####
    return False
####


def _terminate_process(process: subprocess.Popen[str], *, timeout: float = 5.0) -> str:
    with suppress(ProcessLookupError, OSError):
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    ####
    try:
        stdout, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        with suppress(ProcessLookupError, OSError):
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        ####
        stdout, _ = process.communicate(timeout=timeout)
    ####
    return stdout
####
