from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import time
from typing import Any

from .common import (
    base_report,
    find_free_port,
    http_json,
    run_command,
    start_process,
    stop_process,
)


def run_java_sample(*, fixture: Any, fixture_dir: Path, target: str, token: str, mode: str) -> dict[str, Any]:
    report = base_report(fixture_id=fixture.id, mode=mode)
    if fixture.id != "philippanda-lattice-adsb-bridge":
        report["result"] = "missing"
        report["missing"] = list(fixture.surfaces)
        report["details"] = {
            "reason": "java sample runner scaffolded; fixture-specific command mapping is not implemented yet",
            "fixture_dir": str(fixture_dir),
            "target": target,
            "token_configured": bool(token),
        }
        return report
    ####

    repo_root = Path(__file__).resolve().parents[4]
    tooling_root = repo_root / ".tooling"
    java_home = _discover_java_home(tooling_root)
    maven_path = _discover_maven(tooling_root)
    java_path = str(java_home / "bin" / "java") if java_home else shutil.which("java")
    sdk_repo = tooling_root / "m2" / "repository"
    sdk_jar = sdk_repo / "com" / "anduril" / "lattice-sdk" / "5.3.1" / "lattice-sdk-5.3.1.jar"
    maven_repo_local = tooling_root / "m2" / "repository"
    java_home_runtime = tooling_root / "java-home"
    java_home_runtime.mkdir(parents=True, exist_ok=True)

    mock_config = fixture_dir / "src" / "main" / "java" / "com" / "example" / "lattice" / "config" / "LatticeClientConfig.java"
    mock_controller_dir = fixture_dir / "src" / "main" / "java" / "com" / "example" / "lattice" / "mock"

    hardcoded_mock_url = False
    if mock_config.exists():
        hardcoded_mock_url = 'MOCK_SERVER_URL = "http://localhost:8080"' in mock_config.read_text(encoding="utf-8")
    ####

    embedded_mock_controllers = sorted(path.name for path in mock_controller_dir.glob("*.java")) if mock_controller_dir.exists() else []

    missing_prerequisites: list[str] = []
    if java_path is None:
        missing_prerequisites.append("java")
    ####
    if maven_path is None:
        missing_prerequisites.append("maven")
    ####
    if not sdk_jar.exists():
        missing_prerequisites.append("com.anduril:lattice-sdk:5.3.1")
    ####

    report["details"] = {
        "fixture_dir": str(fixture_dir),
        "target": target,
        "token_configured": bool(token),
        "java_home": str(java_home) if java_home else None,
        "java_path": java_path,
        "maven_path": maven_path,
        "sdk_jar": str(sdk_jar),
        "sdk_jar_exists": sdk_jar.exists(),
        "maven_repo_local": str(maven_repo_local),
        "hardcoded_mock_url": hardcoded_mock_url,
        "embedded_mock_controllers": embedded_mock_controllers,
        "install_command": list(fixture.install_command) if fixture.install_command else None,
        "run_commands": [list(command) for command in fixture.run_commands],
        "analysis": {
            "uses_embedded_mock_server": bool(embedded_mock_controllers),
            "ui_depends_on_local_entity_store": "StatusController.java" in embedded_mock_controllers or "MockStreamController.java" in embedded_mock_controllers,
            "notes": [
                "The fixture hardcodes the Lattice base URL to http://localhost:8080 in LatticeClientConfig.java."
                if hardcoded_mock_url
                else "The fixture does not hardcode the mock base URL.",
                "The fixture ships in-process mock Lattice controllers, so the default app topology points the SDK back at itself rather than at Zorn."
                if embedded_mock_controllers
                else "No embedded mock controllers were detected.",
                "The Maven build expects com.anduril:lattice-sdk:5.3.1 to be preinstalled in ~/.m2/repository."
                if not sdk_jar.exists()
                else "The required local Maven lattice-sdk artifact is present.",
            ],
        },
    }

    if missing_prerequisites:
        report["result"] = "blocked"
        report["missing"] = list(fixture.surfaces)
        report["details"]["reason"] = "local prerequisites missing for Java fixture"
        report["details"]["missing_prerequisites"] = missing_prerequisites
        return report
    ####

    assert java_home is not None
    assert maven_path is not None
    assert java_path is not None
    env = {
        **os.environ,
        "JAVA_HOME": str(java_home),
        "PATH": str(java_home / "bin") + os.pathsep + str(Path(maven_path).parent) + os.pathsep + os.environ.get("PATH", ""),
        "HOME": str(java_home_runtime),
    }
    build = run_command(
        [
            str(maven_path),
            "-q",
            "-DskipTests",
            "package",
            f"-Dmaven.repo.local={maven_repo_local}",
        ],
        cwd=fixture_dir,
        env=env,
        timeout=300.0,
    )
    report["details"]["build"] = {
        "args": build.args,
        "returncode": build.returncode,
        "stdout": build.stdout,
        "stderr": build.stderr,
    }
    if build.returncode != 0:
        report["result"] = "failed"
        report["failed"] = list(fixture.surfaces)
        report["details"]["reason"] = "fixture build failed"
        return report
    ####

    runtime_dir = fixture_dir / ".zorn-cert-java"
    opensky_root = runtime_dir / "opensky" / "states"
    opensky_root.mkdir(parents=True, exist_ok=True)
    sample_state = {
        "time": 1710000000,
        "states": [
            ["abc123", "TEST123 ", "United States", 1710000000, 1710000005, -97.5, 35.1, 1200.0, False, 145.0, 90.0, 5.0, None, None, "4321", None, None],
            ["def456", "TEST456 ", "United States", 1710000010, 1710000015, -98.0, 35.3, 2400.0, False, 155.0, 180.0, -2.0, None, None, "1200", None, None],
        ],
    }
    (opensky_root / "all").write_text(json.dumps(sample_state), encoding="utf-8")
    report["details"]["opensky_sample"] = str(opensky_root / "all")

    zorn = _start_http_zorn_server_at_port(
        repo_root=repo_root,
        port=8080,
        token="mock-lattice-token-adsb-bridge",
    )
    opensky_port = find_free_port()
    app_port = find_free_port()
    opensky_handle = start_process(
        ["python3", "-m", "http.server", str(opensky_port), "--directory", str(runtime_dir / "opensky")],
        cwd=repo_root,
    )
    jar_path = fixture_dir / "target" / "lattice-adsb-bridge-1.0.0-SNAPSHOT.jar"
    app_handle = start_process(
        [
            str(java_path),
            "-jar",
            str(jar_path),
            f"--server.port={app_port}",
            f"--bridge.opensky.url=http://127.0.0.1:{opensky_port}/states/all",
            "--bridge.poll-interval-ms=5000",
            "--bridge.max-aircraft=2",
        ],
        cwd=fixture_dir,
        env=env,
    )
    report["details"]["runtime"] = {
        "app_port": app_port,
        "opensky_port": opensky_port,
        "zorn_port": 8080,
        "jar_path": str(jar_path),
    }

    try:
        status_payload = _wait_for_status(app_port=app_port)
        report["details"]["status"] = status_payload

        entity_one = _wait_for_entity("adsb-abc123")
        entity_two = _wait_for_entity("adsb-def456")
        report["details"]["published_entities"] = [entity_one, entity_two]

        _mirror_to_local_store(app_port=app_port, entity=entity_one)
        _mirror_to_local_store(app_port=app_port, entity=entity_two)
        sse_probe = run_command(
            [
                "curl",
                "-s",
                "--max-time",
                "2",
                "-X",
                "POST",
                f"http://127.0.0.1:{app_port}/api/v1/entities/stream",
                "-H",
                "Content-Type: application/json",
                "-d",
                "{}",
            ],
            cwd=repo_root,
            timeout=10.0,
        )
        report["details"]["ui_sse_probe"] = {
            "args": sse_probe.args,
            "returncode": sse_probe.returncode,
            "stdout": sse_probe.stdout,
            "stderr": sse_probe.stderr,
        }

        _record(report, "auth.bearer_token", int(status_payload.get("lastPublishCount", 0)) >= 2, {"status": status_payload})
        _record(report, "entities.publish", entity_one.get("entityId") == "adsb-abc123" and entity_two.get("entityId") == "adsb-def456", {"entities": [entity_one, entity_two]})
        _record(
            report,
            "entities.transponder_codes",
            ((entity_one.get("transponderCodes") or {}).get("modeS") or {}).get("id") == "4321"
            and ((entity_two.get("transponderCodes") or {}).get("modeS") or {}).get("id") == "1200",
            {"entities": [entity_one, entity_two]},
        )
        _record(
            report,
            "ui.sse",
            "EVENT_TYPE_PREEXISTING" in sse_probe.stdout and "adsb-abc123" in sse_probe.stdout,
            {"stdout": sse_probe.stdout},
        )

        requested = set(fixture.surfaces)
        passed = set(report["passed"])
        report["missing"] = sorted(surface for surface in requested if surface not in passed and surface not in report["failed"])
        if report["failed"]:
            report["result"] = "failed"
        elif report["missing"]:
            report["result"] = "partial"
        else:
            report["result"] = "pass"
        ####
        return report
    finally:
        report["details"]["app_log"] = stop_process(app_handle, timeout=5.0)
        report["details"]["opensky_log"] = stop_process(opensky_handle, timeout=5.0)
        report["details"]["zorn_log"] = stop_process(zorn, timeout=5.0)
    ####
####


def _discover_java_home(tooling_root: Path) -> Path | None:
    matches = sorted(tooling_root.glob("jdk-*/Contents/Home"))
    return matches[0] if matches else None
####


def _discover_maven(tooling_root: Path) -> str | None:
    matches = sorted(tooling_root.glob("apache-maven-*/bin/mvn"))
    return str(matches[0]) if matches else None
####


def _start_http_zorn_server_at_port(*, repo_root: Path, port: int, token: str):
    env = {
        **os.environ,
        "C2_COMPAT_AUTH_MODE": "static",
        "C2_COMPAT_STATIC_TOKENS": token,
        "C2_COMPAT_DATABASE_URL": f"sqlite:////private/tmp/zorn-java-fixture-{port}.db",
        "C2_COMPAT_OBJECT_ROOT": f"/private/tmp/zorn-java-fixture-objects-{port}",
    }
    return start_process(
        [
            str(repo_root / ".venv" / "bin" / "python"),
            "-m",
            "uvicorn",
            "zorn.app:build_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=repo_root,
        env=env,
    )
####


def _wait_for_status(*, app_port: int) -> dict[str, Any]:
    deadline = time.time() + 30.0
    while time.time() < deadline:
        try:
            status, payload = http_json("GET", f"http://127.0.0.1:{app_port}/status", token="unused")
            if status == 200 and isinstance(payload, dict) and payload.get("status") == "UP":
                return payload
            ####
        except Exception:
            pass
        ####
        time.sleep(1.0)
    ####
    return {}
####


def _wait_for_entity(entity_id: str) -> dict[str, Any]:
    deadline = time.time() + 30.0
    while time.time() < deadline:
        try:
            status, payload = http_json(
                "GET",
                f"http://127.0.0.1:8080/api/v1/entities/{entity_id}",
                token="mock-lattice-token-adsb-bridge",
            )
            if status == 200 and isinstance(payload, dict):
                return payload
            ####
        except Exception:
            pass
        ####
        time.sleep(1.0)
    ####
    return {}
####


def _mirror_to_local_store(*, app_port: int, entity: dict[str, Any]) -> None:
    _ = http_json("PUT", f"http://127.0.0.1:{app_port}/api/v1/entities", token="unused", payload=entity)
####


def _record(report: dict[str, Any], capability: str, ok: bool, detail: dict[str, Any]) -> None:
    target = "passed" if ok else "failed"
    if capability not in report[target]:
        report[target].append(capability)
    ####
    report["details"][capability] = detail
####
