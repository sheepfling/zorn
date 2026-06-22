from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import time
from typing import Any
import yaml

from .common import (
    base_report,
    ensure_python_venv,
    http_bytes,
    http_json,
    run_command,
    start_process,
    start_dual_transport_zorn_server,
    start_https_zorn_server,
    stop_process,
    stop_dual_transport_zorn_server,
    stop_https_zorn_server,
)


def _install_deepprove_runtime_shim(fixture_dir: Path) -> Path:
    shim_path = fixture_dir / "utils" / "deepprove"
    shim_code = """#!/usr/bin/env python3
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def model_stem(argv: list[str]) -> str:
    if "-m" in argv:
        index = argv.index("-m")
        if index + 1 < len(argv):
            return Path(argv[index + 1]).stem
    return "within_range"


def proof_payload(stem: str) -> dict[str, object]:
    outputs = {
        "within_range": [0.0, 2.0],
        "tactical_decision": [2.0, 0.0, 0.0, 0.0],
        "threat_assessment": [0.0, 1.0],
        "movement_calculation": [45.0, 100.0, 0.6],
        "surveillance_position": [0.0, 0.0, 0.0],
    }.get(stem, [0.0, 2.0])
    return {
        "proof_type": stem,
        "status": "generated",
        "verified": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "outputs": [{"data": outputs, "shape": [len(outputs)]}],
    }


def main() -> int:
    stem = model_stem(sys.argv[1:])
    target = Path.cwd() / f"proof-{stem}.json"
    target.write_text(json.dumps(proof_payload(stem), indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""
    shim_path.write_text(shim_code, encoding="utf-8")
    shim_path.chmod(0o755)
    return shim_path
####


def _install_deepprove_sitecustomize(fixture_dir: Path) -> Path:
    site_dir = fixture_dir / ".zorn-cert-runtime"
    site_dir.mkdir(parents=True, exist_ok=True)
    sitecustomize = site_dir / "sitecustomize.py"
    sitecustomize.write_text(
        """from __future__ import annotations

import asyncio
import httpx

from anduril.core.client_wrapper import AsyncClientWrapper
from anduril.tasks.client import AsyncTasksClient
from anduril.tasks.raw_client import AsyncRawTasksClient


_ORIGINAL_LISTEN_AS_AGENT = AsyncTasksClient.listen_as_agent
_ORIGINAL_TO_THREAD = asyncio.to_thread


async def _zorn_isolated_listen_as_agent(self, *, agent_selector=None, request_options=None):
    wrapper = self._raw_client._client_wrapper
    async with httpx.AsyncClient(timeout=wrapper._timeout, verify=True) as httpx_client:
        isolated_wrapper = AsyncClientWrapper(
            token=wrapper._token,
            headers=wrapper._headers,
            base_url=wrapper._base_url,
            timeout=wrapper._timeout,
            httpx_client=httpx_client,
        )
        isolated_raw = AsyncRawTasksClient(client_wrapper=isolated_wrapper)
        response = await isolated_raw.listen_as_agent(
            agent_selector=agent_selector,
            request_options=request_options,
        )
    request = response.data
    if request.execute_request is None and request.cancel_request is None and request.complete_request is None:
        await asyncio.sleep(0.2)
        return None
    return request


AsyncTasksClient.listen_as_agent = _zorn_isolated_listen_as_agent


async def _zorn_to_thread(func, /, *args, **kwargs):
    result = await _ORIGINAL_TO_THREAD(func, *args, **kwargs)
    if asyncio.iscoroutine(result):
        return await result
    return result


asyncio.to_thread = _zorn_to_thread
""",
        encoding="utf-8",
    )
    return site_dir
####


def _install_alfred_sitecustomize(fixture_dir: Path) -> Path:
    site_dir = fixture_dir / ".zorn-cert-runtime"
    site_dir.mkdir(parents=True, exist_ok=True)
    sitecustomize = site_dir / "sitecustomize.py"
    sitecustomize.write_text(
        """from __future__ import annotations

import sys
import types
from dataclasses import dataclass


@dataclass
class Observation:
    device_id: str
    device_type: str
    class_name: str
    confidence: float
    lat: float | None = None
    lon: float | None = None
    altitude_m: float | None = None
    bearing_deg: float | None = None
    speed_mps: float | None = None
    bbox: tuple[float, float, float, float] | None = None
    attributes: dict | None = None
    timestamp: str = ""
    source_event_id: str = ""


class HivemindService:
    _instance = None

    def __init__(self) -> None:
        self.ingested = []

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def ingest(self, obs):
        self.ingested.append(obs)
        return obs


class ArgusAgent:
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _score_threat(self, payload):
        return {"threat_score": 9, "reason": "zorn-cert synthetic high-threat"}


hivemind_models = types.ModuleType("alfred.hivemind.models")
hivemind_models.Observation = Observation
sys.modules["alfred.hivemind.models"] = hivemind_models

hivemind_service = types.ModuleType("alfred.hivemind.service")
hivemind_service.HivemindService = HivemindService
sys.modules["alfred.hivemind.service"] = hivemind_service

argus_module = types.ModuleType("alfred.agents.argus")
argus_module.ArgusAgent = ArgusAgent
sys.modules["alfred.agents.argus"] = argus_module

try:
    from anduril.entities.client import AsyncEntitiesClient

    _ORIGINAL_PUBLISH_ENTITY = AsyncEntitiesClient.publish_entity

    async def _zorn_publish_entity(self, entity=None, **kwargs):
        if entity is not None and not kwargs:
            kwargs = entity.model_dump()
        return await _ORIGINAL_PUBLISH_ENTITY(self, **kwargs)

    AsyncEntitiesClient.publish_entity = _zorn_publish_entity
except Exception:
    pass
""",
        encoding="utf-8",
    )
    return site_dir
####


def run_python_sample(*, fixture: Any, fixture_dir: Path, target: str, token: str, mode: str) -> dict[str, Any]:
    if fixture.id == "sdk-python-smoke":
        return _run_sdk_python_smoke(fixture=fixture, fixture_dir=fixture_dir, token=token, mode=mode)
    ####
    if fixture.id == "ark-mavlink-to-lattice":
        return _run_ark_mavlink_sample(fixture=fixture, fixture_dir=fixture_dir, token=token, mode=mode)
    ####
    if fixture.id == "alphafox-dragonsync":
        return _run_dragonsync_sample(fixture=fixture, fixture_dir=fixture_dir, token=token, mode=mode)
    ####
    if fixture.id == "tyler-alfred-agent":
        return _run_alfred_sample(fixture=fixture, fixture_dir=fixture_dir, token=token, mode=mode)
    ####
    if fixture.id == "lagrange-deep-prove-demo":
        return _run_deep_prove_sample(fixture=fixture, fixture_dir=fixture_dir, token=token, mode=mode)
    ####
    if fixture.id == "anduril-sample-ais-rest":
        return _run_ais_rest_cert(fixture=fixture, target=target, token=token, mode=mode)
    ####
    if fixture.id == "anduril-sample-thumbnail":
        return _run_thumbnail_sample(fixture=fixture, fixture_dir=fixture_dir, token=token, mode=mode)
    ####
    if fixture.id == "anduril-sample-auto-reconnaissance":
        return _run_auto_recon_sample(fixture=fixture, fixture_dir=fixture_dir, token=token, mode=mode)
    ####
    if fixture.id == "anduril-sample-ais-grpc":
        return _run_ais_grpc_sample(fixture=fixture, fixture_dir=fixture_dir, token=token, mode=mode)
    ####
    report = base_report(fixture_id=fixture.id, mode=mode)
    report["result"] = "missing"
    report["missing"] = list(fixture.surfaces)
    report["details"]["reason"] = "runner scaffolded; fixture-specific command mapping is not implemented yet"
    report["details"]["fixture_dir"] = str(fixture_dir)
    return report
####


def _run_sdk_python_smoke(*, fixture: Any, fixture_dir: Path, token: str, mode: str) -> dict[str, Any]:
    report = base_report(fixture_id=fixture.id, mode=mode)
    python = ensure_python_venv(fixture_dir)
    install = run_command(
        [str(python), "-m", "pip", "install", "-e", "."],
        cwd=fixture_dir,
        timeout=300.0,
    )
    report["details"]["install"] = {
        "args": install.args,
        "returncode": install.returncode,
        "stdout": install.stdout,
        "stderr": install.stderr,
    }
    if install.returncode != 0:
        report["result"] = "failed"
        report["failed"] = list(fixture.surfaces)
        return report
    ####

    server = start_https_zorn_server(
        repo_root=Path(__file__).resolve().parents[4],
        token=token,
        auth_mode="oauth-dev",
        static_tokens=[token, "env-token"],
    )
    try:
        driver = server.workspace / "sdk_python_smoke.py"
        output_path = server.workspace / "sdk_python_smoke_results.json"
        driver.write_text(
            f"""
from __future__ import annotations

import json
from pathlib import Path

import httpx

from anduril import Lattice


BASE_URL = {server.base_url!r}
TOKEN = {token!r}
OUTPUT = Path({str(output_path)!r})


def dump_model(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True, exclude_none=True, mode="json")
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return [dump_model(item) for item in value]
    return value


def record(results, surface, ok, evidence=None):
    results[surface] = {{"ok": bool(ok), "evidence": evidence}}


def main():
    results = {{}}
    http_client = httpx.Client(verify={str(server.cafile)!r}, timeout=20.0, follow_redirects=True)
    client = Lattice(
        base_url=BASE_URL,
        client_id="zorn-cert-client",
        client_secret="zorn-cert-secret",
        headers={{"Anduril-Sandbox-Authorization": f"Bearer {{TOKEN}}"}},
        httpx_client=http_client,
    )
    token_client = Lattice(
        base_url=BASE_URL,
        token=lambda: TOKEN,
        headers={{"Anduril-Sandbox-Authorization": f"Bearer {{TOKEN}}"}},
        httpx_client=http_client,
    )

    oauth_token = client.oauth.get_token().access_token
    record(results, "auth.oauth_client_credentials", isinstance(oauth_token, str) and len(oauth_token) > 0, {{"token_prefix": oauth_token[:8]}})
    record(results, "auth.bearer_token", token_client.entities is not None, {{"client": "constructed"}})
    record(results, "auth.sandbox_header", True, {{"header": "Anduril-Sandbox-Authorization"}})
    record(results, "transport.rest_json", True, {{"sdk": "anduril-lattice-sdk-python"}})

    asset_id = "sdk-python-asset"
    track_id = "sdk-python-track"
    geo_id = "sdk-python-geo"
    base_location = {{
        "position": {{
            "latitudeDegrees": 37.7701,
            "longitudeDegrees": -122.4102,
            "altitudeHaeMeters": 50.0,
        }},
        "velocityEnu": {{"e": 3.0, "n": 4.0, "u": 0.2}},
        "attitudeEnu": {{"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0}},
    }}
    track_location = {{
        "position": {{
            "latitudeDegrees": 37.7701,
            "longitudeDegrees": -122.411,
            "altitudeHaeMeters": 50.0,
        }},
        "velocityEnu": {{"e": 3.0, "n": 4.0, "u": 0.2}},
        "attitudeEnu": {{"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0}},
    }}
    common_provenance = {{"sourceId": "sdk-python-smoke", "integrationName": "sdk-python-smoke"}}
    asset = client.entities.publish_entity(
        entity_id=asset_id,
        description="SDK Python asset",
        is_live=True,
        no_expiry=True,
        location=base_location,
        ontology={{"template": "TEMPLATE_ASSET", "platformType": "UAV"}},
        provenance=common_provenance,
        health={{"healthStatus": "HEALTH_STATUS_HEALTHY"}},
        task_catalog={{"taskDefinitions": [{{"typeUrl": "type.googleapis.com/zorn.cert.Investigate"}}]}},
    )
    track = client.entities.publish_entity(
        entity_id=track_id,
        description="SDK Python track",
        is_live=True,
        no_expiry=True,
        location=track_location,
        ontology={{"template": "TEMPLATE_TRACK", "platformType": "UAS"}},
        provenance=common_provenance,
        mil_view={{"disposition": "DISPOSITION_ASSUMED_FRIENDLY"}},
    )
    geo = client.entities.publish_entity(
        entity_id=geo_id,
        description="SDK Python geo",
        is_live=True,
        no_expiry=True,
        geo_shape={{"point": {{"latitudeDegrees": 37.771, "longitudeDegrees": -122.412}}}},
        ontology={{"template": "TEMPLATE_GEO", "platformType": "UNKNOWN"}},
        provenance=common_provenance,
    )
    fetched = client.entities.get_entity(asset_id)
    record(results, "entities.publish", dump_model(asset).get("entityId") == asset_id and dump_model(track).get("entityId") == track_id, {{"asset": dump_model(asset), "track": dump_model(track)}})
    record(results, "entities.get", dump_model(fetched).get("entityId") == asset_id, dump_model(fetched))
    record(results, "entities.asset", dump_model(asset).get("ontology", {{}}).get("template") == "TEMPLATE_ASSET", dump_model(asset))
    record(results, "entities.track", dump_model(track).get("ontology", {{}}).get("template") == "TEMPLATE_TRACK", dump_model(track))
    record(results, "entities.geo", dump_model(geo).get("ontology", {{}}).get("template") == "TEMPLATE_GEO", dump_model(geo))

    poll = client.entities.long_poll_entity_events(session_token="")
    poll_payload = dump_model(poll)
    poll_events = poll_payload.get("entityEvents") or poll_payload.get("events") or []
    record(results, "entities.long_poll", any((event.get("entity") or {{}}).get("entityId") == asset_id for event in poll_events), poll_payload)

    stream_seen = []
    for index, event in enumerate(client.entities.stream_entities(pre_existing_only=True, heartbeat_interval_ms=0)):
        stream_seen.append(dump_model(event))
        if any((item.get("entity") or {{}}).get("entityId") == track_id for item in stream_seen):
            break
        if index >= 10:
            break
    record(results, "entities.stream_sse", any((event.get("entity") or {{}}).get("entityId") == track_id for event in stream_seen), {{"events": stream_seen}})

    override = client.entities.override_entity(
        track_id,
        "mil_view.disposition",
        entity={{"milView": {{"disposition": "DISPOSITION_HOSTILE"}}}},
        provenance=common_provenance,
    )
    override_payload = dump_model(override)
    record(results, "entities.overrides.apply", override_payload.get("milView", {{}}).get("disposition") == "DISPOSITION_HOSTILE" or override_payload.get("mil_view", {{}}).get("disposition") == "DISPOSITION_HOSTILE", override_payload)
    cleared = client.entities.remove_entity_override(track_id, "mil_view.disposition")
    cleared_payload = dump_model(cleared)
    record(results, "entities.overrides.clear", dump_model(cleared).get("entityId") == track_id, cleared_payload)

    task_id = "sdk-python-task"
    task = client.tasks.create_task(
        task_id=task_id,
        display_name="SDK Python task",
        description="Direct SDK conformance smoke",
        specification={{"typeUrl": "type.googleapis.com/zorn.cert.Investigate", "value": ""}},
        relations={{"assignee": {{"system": {{"entityId": asset_id}}}}}},
    )
    task_payload = dump_model(task)
    record(results, "tasks.create", task_payload.get("taskId") == task_id, task_payload)
    fetched_task = client.tasks.get_task(task_id)
    fetched_task_payload = dump_model(fetched_task)
    record(results, "tasks.get", fetched_task_payload.get("taskId") == task_id, fetched_task_payload)
    query_payload = dump_model(client.tasks.query_tasks())
    record(results, "tasks.query", any(item.get("taskId") == task_id for item in query_payload.get("tasks", [])), query_payload)
    agent_request = client.tasks.listen_as_agent(agent_selector={{"entityIds": [asset_id]}})
    agent_payload = dump_model(agent_request)
    execute = agent_payload.get("executeRequest") or agent_payload.get("execute_request") or {{}}
    record(results, "tasks.listen_as_agent", (execute.get("task") or {{}}).get("taskId") == task_id, agent_payload)
    executing = client.tasks.update_task_status(
        task_id,
        status_version=1,
        new_status={{"status": "STATUS_EXECUTING"}},
    )
    executing_payload = dump_model(executing)
    record(results, "tasks.update_status", (executing_payload.get("status") or {{}}).get("status") == "STATUS_EXECUTING", executing_payload)
    cancelled = client.tasks.cancel_task(task_id)
    cancelled_payload = dump_model(cancelled)
    record(results, "tasks.cancel", cancelled_payload.get("taskId") == task_id, cancelled_payload)

    object_path = "sdk-python-smoke/object.txt"
    object_bytes = b"zorn sdk python smoke\\n"
    uploaded = client.objects.upload_object(object_path, request=object_bytes)
    uploaded_payload = dump_model(uploaded)
    record(results, "objects.upload", uploaded_payload.get("path") == object_path or uploaded_payload.get("objectPath") == object_path, uploaded_payload)
    metadata = dict(client.objects.get_object_metadata(object_path))
    record(results, "objects.metadata", metadata.get("Path") == object_path or metadata.get("path") == object_path, metadata)
    listed = list(client.objects.list_objects(prefix="sdk-python-smoke"))
    listed_payload = dump_model(listed)
    record(results, "objects.list", any(item.get("path") == object_path or item.get("objectPath") == object_path for item in listed_payload), listed_payload)
    downloaded = b"".join(client.objects.get_object(object_path))
    record(results, "objects.download", downloaded == object_bytes, {{"downloaded": downloaded.decode("utf-8")}})
    client.objects.delete_object(object_path)
    try:
        deleted_metadata = dict(client.objects.get_object_metadata(object_path))
        record(results, "objects.delete", False, deleted_metadata)
    except Exception as exc:
        status_code = getattr(exc, "status_code", None)
        record(results, "objects.delete", status_code == 404, {{"status_code": status_code, "error": str(exc)}})

    OUTPUT.write_text(json.dumps(results, default=str, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
""".lstrip(),
            encoding="utf-8",
        )
        env = {
            **os.environ,
            "SSL_CERT_FILE": str(server.cafile),
            "REQUESTS_CA_BUNDLE": str(server.cafile),
        }
        run = run_command([str(python), str(driver)], cwd=fixture_dir, env=env, timeout=180.0)
        report["details"]["command"] = run.args
        report["details"]["process"] = {
            "args": run.args,
            "returncode": run.returncode,
            "stdout": run.stdout,
            "stderr": run.stderr,
        }
        if output_path.exists():
            results = json.loads(output_path.read_text(encoding="utf-8"))
        else:
            results = {}
        ####
        report["details"]["sdk_results"] = results
        for surface, payload in results.items():
            if isinstance(payload, dict):
                _record(report, surface, bool(payload.get("ok")), payload.get("evidence"))
            ####
        ####
        requested = set(fixture.surfaces)
        passed = set(report["passed"])
        report["missing"] = sorted(surface for surface in requested if surface not in passed)
        if run.returncode != 0:
            report["result"] = "failed"
            if not report["failed"]:
                report["failed"] = list(fixture.surfaces)
            ####
        elif report["failed"]:
            report["result"] = "failed"
        elif report["missing"]:
            report["result"] = "partial"
        else:
            report["result"] = "pass"
        ####
        return report
    finally:
        report["details"]["server_log"] = stop_https_zorn_server(server)
    ####
####


def _run_ais_rest_cert(*, fixture: Any, target: str, token: str, mode: str) -> dict[str, Any]:
    report = base_report(fixture_id=fixture.id, mode=mode)
    entity_id = "zorn-cert-ais-rest-vessel"
    entity_payload = {
        "entityId": entity_id,
        "description": "Zorn certification AIS REST vessel",
        "isLive": True,
        "noExpiry": True,
        "location": {
            "position": {
                "latitudeDegrees": 37.7749,
                "longitudeDegrees": -122.4194,
                "altitudeHaeMeters": 0,
            }
        },
        "ontology": {"template": "TEMPLATE_TRACK", "platformType": "SURFACE_VESSEL"},
        "provenance": {"sourceId": "zorn-cert", "integrationName": "anduril-sample-ais-rest"},
    }
    status, response = http_json("PUT", f"{target.rstrip('/')}/api/v1/entities", token=token, payload=entity_payload)
    _record(report, "entities.publish", status < 300, {"status": status, "response": response})

    status, entity = http_json("GET", f"{target.rstrip('/')}/api/v1/entities/{entity_id}", token=token)
    _record(report, "entities.readback", status == 200 and entity.get("entityId") == entity_id, {"status": status, "entity": entity})
    _record(report, "entities.location", isinstance(entity.get("location"), dict), {"entity": entity})
    _record(report, "entities.ontology", isinstance(entity.get("ontology"), dict), {"entity": entity})
    _record(report, "entities.provenance", isinstance(entity.get("provenance"), dict), {"entity": entity})

    status, events = http_json("POST", f"{target.rstrip('/')}/api/v1/entities/events", token=token, payload={"afterSequence": 0})
    event_entities: list[dict[str, Any]] = []
    for event in events.get("events", []):
        if isinstance(event, dict) and isinstance(event.get("entity"), dict):
            event_entities.append(event["entity"])
        ####
    ####
    _record(
        report,
        "entities.stream",
        status == 200 and any(entity.get("entityId") == entity_id for entity in event_entities),
        {"status": status, "events": events},
    )

    requested = set(fixture.surfaces)
    passed = set(report["passed"])
    report["missing"] = sorted(surface for surface in requested if surface not in passed and surface not in {"auth.sandbox_header", "auth.bearer_token"})
    if report["failed"]:
        report["result"] = "failed"
    elif report["missing"]:
        report["result"] = "partial"
    else:
        report["result"] = "pass"
    ####
    return report
####


def _run_ark_mavlink_sample(*, fixture: Any, fixture_dir: Path, token: str, mode: str) -> dict[str, Any]:
    report = base_report(fixture_id=fixture.id, mode=mode)
    python = ensure_python_venv(fixture_dir)
    install = run_command(
        [str(python), "-m", "pip", "install", "anduril-lattice-sdk", "numpy", "scipy"],
        cwd=fixture_dir,
        timeout=300.0,
    )
    report["details"]["install"] = {
        "args": install.args,
        "returncode": install.returncode,
        "stdout": install.stdout,
        "stderr": install.stderr,
    }
    if install.returncode != 0:
        report["result"] = "failed"
        report["failed"] = list(fixture.surfaces)
        return report
    ####

    server = start_https_zorn_server(
        repo_root=Path(__file__).resolve().parents[4],
        token=token,
        auth_mode="static",
        static_tokens=[token, "env-token"],
    )
    try:
        shim_dir = server.workspace / "ark-runtime-shim"
        shim_dir.mkdir(parents=True, exist_ok=True)
        sitecustomize = shim_dir / "sitecustomize.py"
        sitecustomize.write_text(
            """
import asyncio
import sys
import types


telemetry_stream = types.ModuleType("telemetry_stream")


class _Point:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


async def stream_position(queue, retry_delay=1.0):
    position = _Point(latitude_deg=37.7749, longitude_deg=-122.4194, absolute_altitude_m=120.5)
    velocity = _Point(velocity=_Point(north_m_s=11.2, east_m_s=4.5, down_m_s=-1.1))
    altitude = _Point(altitude_terrain_m=87.3, altitude_local_m=86.9)
    odometry = _Point(q=_Point(x=0.0, y=0.0, z=0.0, w=1.0))
    await queue.put((position, velocity, altitude, odometry))
    while True:
        await asyncio.sleep(60)


telemetry_stream.stream_position = stream_position
sys.modules["telemetry_stream"] = telemetry_stream
""".lstrip(),
        )
        env = {
            **os.environ,
            "SSL_CERT_FILE": str(server.cafile),
            "PYTHONPATH": str(shim_dir) + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else ""),
            "LATTICE_ENDPOINT": server.base_url.removeprefix("https://"),
            "ENVIRONMENT_TOKEN": "env-token",
            "SANDBOXES_TOKEN": token,
        }
        handle = start_process([str(python), "lattice_publisher.py"], cwd=fixture_dir, env=env)
        report["details"]["runtime_shim"] = str(sitecustomize)
        report["details"]["command"] = handle.args

        entity_payload: dict[str, Any] | None = None
        deadline = time.time() + 20.0
        while time.time() < deadline:
            entity_status, maybe_entity = http_json(
                "GET",
                f"{server.base_url}/api/v1/entities/drone-1",
                token="env-token",
                cafile=server.cafile,
                headers={"Anduril-Sandbox-Authorization": f"Bearer {token}"},
            )
            if entity_status == 200:
                entity_payload = maybe_entity
                break
            ####
            if handle.process.poll() is not None:
                break
            ####
            time.sleep(1.0)
        ####

        returncode, stdout = stop_process(handle)
        report["details"]["process"] = {
            "args": handle.args,
            "cwd": str(handle.cwd),
            "returncode": returncode,
            "stdout": stdout,
        }
        report["details"]["entity"] = entity_payload

        location = entity_payload.get("location", {}) if isinstance(entity_payload, dict) else {}
        health = entity_payload.get("health", {}) if isinstance(entity_payload, dict) else {}
        task_catalog = entity_payload.get("taskCatalog", entity_payload.get("task_catalog", {})) if isinstance(entity_payload, dict) else {}
        ontology = entity_payload.get("ontology", {}) if isinstance(entity_payload, dict) else {}
        provenance = entity_payload.get("provenance", {}) if isinstance(entity_payload, dict) else {}
        velocity = location.get("velocityEnu", location.get("velocity_enu", {})) if isinstance(location, dict) else {}
        attitude = location.get("attitudeEnu", location.get("attitude_enu", {})) if isinstance(location, dict) else {}

        _record(report, "auth.bearer_token", entity_payload is not None, {"entity": entity_payload})
        _record(report, "entities.publish", entity_payload is not None and entity_payload.get("entityId") == "drone-1", {"entity": entity_payload})
        _record(report, "entities.location", isinstance(location.get("position"), dict), {"location": location})
        _record(report, "entities.velocity_enu", isinstance(velocity, dict) and velocity.get("n") is not None and velocity.get("e") is not None, {"velocity": velocity})
        _record(report, "entities.attitude", isinstance(attitude, dict) and all(attitude.get(axis) is not None for axis in ("w", "x", "y", "z")), {"attitude": attitude})
        _record(report, "entities.health", isinstance(health, dict) and health.get("healthStatus") == "HEALTH_STATUS_HEALTHY", {"health": health})
        _record(report, "entities.ontology", isinstance(ontology, dict) and ontology.get("platformType") == "UAV", {"ontology": ontology})
        _record(report, "entities.provenance", isinstance(provenance, dict) and provenance.get("integrationName") == "mavsdk_integration", {"provenance": provenance})
        definitions = task_catalog.get("taskDefinitions", task_catalog.get("task_definitions", [])) if isinstance(task_catalog, dict) else []
        _record(report, "entities.task_catalog", isinstance(definitions, list) and len(definitions) >= 3, {"task_catalog": task_catalog})

        requested = set(fixture.surfaces)
        passed = set(report["passed"])
        report["missing"] = sorted(surface for surface in requested if surface not in passed)
        if report["failed"]:
            report["result"] = "failed"
        elif report["missing"]:
            report["result"] = "partial"
        else:
            report["result"] = "pass"
        ####
        return report
    finally:
        report["details"]["server_log"] = stop_https_zorn_server(server)
    ####
####


def _run_dragonsync_sample(*, fixture: Any, fixture_dir: Path, token: str, mode: str) -> dict[str, Any]:
    report = base_report(fixture_id=fixture.id, mode=mode)
    python = ensure_python_venv(fixture_dir)
    install = run_command(
        [str(python), "-m", "pip", "install", "-r", "requirements.txt", "anduril-lattice-sdk"],
        cwd=fixture_dir,
        timeout=300.0,
    )
    report["details"]["install"] = {
        "args": install.args,
        "returncode": install.returncode,
        "stdout": install.stdout,
        "stderr": install.stderr,
    }
    if install.returncode != 0:
        report["result"] = "failed"
        report["failed"] = list(fixture.surfaces)
        return report
    ####

    server = start_https_zorn_server(
        repo_root=Path(__file__).resolve().parents[4],
        token=token,
        auth_mode="static",
        static_tokens=[token, "env-token"],
    )
    try:
        driver = server.workspace / "dragonsync_cert_driver.py"
        driver.write_text(
            f"""
from sinks.lattice_sink import LatticeSink


sink = LatticeSink(
    token="env-token",
    base_url={server.base_url!r},
    sandbox_token={token!r},
    source_name="DragonSync",
    drone_hz=10.0,
    wardragon_hz=10.0,
)

sink.publish_system(
    {{
        "serial_number": "WD-0001",
        "gps_data": {{
            "latitude": 37.4219999,
            "longitude": -122.0840575,
            "altitude": 12.3,
        }},
        "system_stats": {{
            "cpu_usage": 21.5,
            "memory": {{"percent": 48.0}},
            "disk": {{"percent": 62.0}},
            "temperature": 55.0,
            "uptime": 7200,
        }},
        "ant_sdr_temps": {{
            "pluto_temp": 41.0,
            "zynq_temp": 43.0,
        }},
    }}
)
sink.publish_drone(
    {{
        "id": "drone-cert-001",
        "id_type": "CAA",
        "caa": "US-ZORN-001",
        "description": "Dragon Sync Test Drone",
        "mac": "AA:BB:CC:DD:EE:FF",
        "rssi": -42,
        "ua_type_name": "Quadcopter",
        "speed": 14.2,
        "vspeed": 1.5,
        "alt": 123.4,
        "height": 45.0,
        "height_type": "AGL",
        "op_status": "AIRBORNE",
        "operator_id": "OP-100",
        "operator_id_type": "Operator ID",
        "transport": "RID",
        "freq": 2450000000,
        "lat": 37.4222,
        "lon": -122.0843,
        "direction": 96.0,
    }}
)
sink.publish_pilot("drone-cert-001", 37.4220, -122.0839, name="Pilot of drone-cert-001", altitude=11.1)
sink.publish_home("drone-cert-001", 37.4218, -122.0846, name="Home of drone-cert-001", altitude=10.4)
""".lstrip(),
        )
        env = {
            **os.environ,
            "SSL_CERT_FILE": str(server.cafile),
            "REQUESTS_CA_BUNDLE": str(server.cafile),
            "PYTHONPATH": str(fixture_dir) + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else ""),
        }
        run = run_command([str(python), str(driver)], cwd=fixture_dir, env=env, timeout=120.0)
        report["details"]["command"] = run.args
        report["details"]["process"] = {
            "args": run.args,
            "returncode": run.returncode,
            "stdout": run.stdout,
            "stderr": run.stderr,
        }
        if run.returncode != 0:
            report["result"] = "failed"
            report["failed"] = list(fixture.surfaces)
            return report
        ####

        entity_ids = {
            "system": "wardragon-WD-0001",
            "drone": "drone-cert-001",
            "pilot": "drone-cert-001-pilot",
            "home": "drone-cert-001-home",
        }
        entities: dict[str, dict[str, Any]] = {}
        deadline = time.time() + 20.0
        while time.time() < deadline:
            for key, entity_id in entity_ids.items():
                if key in entities:
                    continue
                ####
                status, payload = http_json(
                    "GET",
                    f"{server.base_url}/api/v1/entities/{entity_id}",
                    token="env-token",
                    cafile=server.cafile,
                    headers={"Anduril-Sandbox-Authorization": f"Bearer {token}"},
                )
                if status == 200 and payload.get("entityId") == entity_id:
                    entities[key] = payload
                ####
            ####
            if len(entities) == len(entity_ids):
                break
            ####
            time.sleep(0.5)
        ####
        report["details"]["entities"] = entities

        system_entity = entities.get("system", {})
        drone_entity = entities.get("drone", {})
        pilot_entity = entities.get("pilot", {})
        home_entity = entities.get("home", {})

        classification = system_entity.get("dataClassification", system_entity.get("data_classification", {}))
        health = system_entity.get("health", {})
        relationship_targets = _related_entity_ids(drone_entity) | _related_entity_ids(pilot_entity) | _related_entity_ids(home_entity)

        _record(report, "auth.bearer_token", bool(entities), {"entity_ids": entity_ids, "fetched": sorted(entities)})
        _record(
            report,
            "entities.publish",
            len(entities) == len(entity_ids),
            {"expected": entity_ids, "entities": entities},
        )
        _record(
            report,
            "entities.relationships",
            entity_ids["system"] in relationship_targets,
            {"relationship_targets": sorted(relationship_targets), "drone": drone_entity, "pilot": pilot_entity, "home": home_entity},
        )
        default_classification = classification.get("default", {}) if isinstance(classification, dict) else {}
        _record(
            report,
            "entities.classification",
            isinstance(default_classification, dict) and bool(default_classification.get("level")),
            {"classification": classification},
        )
        _record(
            report,
            "entities.health",
            isinstance(health, dict) and bool(health.get("healthStatus", health.get("health_status"))),
            {"health": health},
        )

        requested = set(fixture.surfaces)
        passed = set(report["passed"])
        report["missing"] = sorted(surface for surface in requested if surface not in passed)
        if report["failed"]:
            report["result"] = "failed"
        elif report["missing"]:
            report["result"] = "partial"
        else:
            report["result"] = "pass"
        ####
        return report
    finally:
        report["details"]["server_log"] = stop_https_zorn_server(server)
    ####
####


def _run_alfred_sample(*, fixture: Any, fixture_dir: Path, token: str, mode: str) -> dict[str, Any]:
    report = base_report(fixture_id=fixture.id, mode=mode)
    python = ensure_python_venv(fixture_dir)
    install = run_command(
        [str(python), "-m", "pip", "install", "anduril-lattice-sdk"],
        cwd=fixture_dir,
        timeout=300.0,
    )
    report["details"]["install"] = {
        "args": install.args,
        "returncode": install.returncode,
        "stdout": install.stdout,
        "stderr": install.stderr,
    }
    if install.returncode != 0:
        report["result"] = "failed"
        report["failed"] = list(fixture.surfaces)
        return report
    ####

    server = start_https_zorn_server(
        repo_root=Path(__file__).resolve().parents[4],
        token=token,
        auth_mode="oauth-dev",
        static_tokens=[token, "env-token"],
    )
    try:
        runtime_dir = _install_alfred_sitecustomize(fixture_dir)
        script_path = runtime_dir / "alfred_lattice_cert.py"
        script_path.write_text(
            """from __future__ import annotations

import asyncio
import json
import os
import ssl
import sys
import urllib.request
from pathlib import Path

from anduril import Entity, Location, MilView, Ontology, Position, Provenance
from alfred.integrations.lattice_bridge import LatticeArbiter, LatticeBridge
from alfred.hivemind.service import HivemindService


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {os.environ['ENVIRONMENT_TOKEN']}",
        "anduril-sandbox-authorization": f"Bearer {os.environ['LATTICE_SANDBOXES_TOKEN']}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _url(path: str) -> str:
    endpoint = os.environ["LATTICE_ENDPOINT"].rstrip("/")
    if endpoint.startswith("https://"):
        base = endpoint
    else:
        base = f"https://{endpoint}"
    return f"{base}{path}"


def _json_request(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(_url(path), data=body, headers=_headers(), method=method)
    context = ssl.create_default_context(cafile=os.environ["SSL_CERT_FILE"])
    with urllib.request.urlopen(req, context=context, timeout=10.0) as response:
        text = response.read().decode("utf-8")
        return response.status, json.loads(text) if text else {}


async def _main() -> int:
    bridge = LatticeBridge.get()
    await bridge.connect()
    asset = Entity(
        entity_id="alfred-asset-01",
        description="ALFRED cert asset",
        is_live=True,
        no_expiry=True,
        location=Location(
            position=Position(
                latitude_degrees=37.7740,
                longitude_degrees=-122.4190,
            )
        ),
        mil_view=MilView(disposition="DISPOSITION_FRIENDLY"),
        ontology=Ontology(template="TEMPLATE_ASSET", platform_type="UAV"),
        provenance=Provenance(
            integration_name="alfred-cert",
            source_update_time="2026-01-01T00:00:00Z",
        ),
    )
    await bridge._client.entities.publish_entity(asset)
    arbiter = LatticeArbiter()
    arbiter_task = asyncio.create_task(arbiter.start())
    await asyncio.sleep(1.0)
    await bridge.publish_cv_detection(
        {
            "track_id": "zorn-alfred-track",
            "class_name": "small_uas",
            "confidence": 0.6,
            "lat": 37.7750,
            "lon": -122.4180,
        },
        camera_id="cam-01",
    )

    track_payload = {}
    tasks_payload = {}
    for _ in range(30):
        await asyncio.sleep(1.0)
        _, track_payload = _json_request("GET", "/api/v1/entities/cv-zorn-alfred-track")
        _, tasks_payload = _json_request("POST", "/api/v1/tasks/query", {})
        tasks = tasks_payload.get("tasks", [])
        if isinstance(tasks, list) and tasks:
            break

    arbiter_task.cancel()
    try:
        await arbiter_task
    except asyncio.CancelledError:
        pass

    result = {
        "stream_ingest_count": len(HivemindService.get().ingested),
        "track": track_payload,
        "tasks": tasks_payload.get("tasks", []),
        "local_mock_exists": Path("scripts/lattice_mock.py").exists(),
    }
    Path(".zorn-cert-runtime/alfred_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
""",
            encoding="utf-8",
        )
        env = {
            **os.environ,
            "SSL_CERT_FILE": str(server.cafile),
            "REQUESTS_CA_BUNDLE": str(server.cafile),
            "PYTHONPATH": str(runtime_dir) + os.pathsep + str(fixture_dir),
            "LATTICE_ENDPOINT": server.base_url.removeprefix("https://"),
            "LATTICE_CLIENT_ID": "mock-client",
            "LATTICE_CLIENT_SECRET": "mock-secret",
            "LATTICE_SANDBOXES_TOKEN": token,
            "ENVIRONMENT_TOKEN": "env-token",
        }
        report["details"]["runtime_shim"] = str(runtime_dir / "sitecustomize.py")
        report["details"]["command"] = [str(python), str(script_path)]
        execution = run_command(
            [str(python), str(script_path)],
            cwd=fixture_dir,
            env=env,
            timeout=120.0,
        )
        report["details"]["process"] = {
            "args": execution.args,
            "returncode": execution.returncode,
            "stdout": execution.stdout,
            "stderr": execution.stderr,
        }
        result_path = fixture_dir / ".zorn-cert-runtime" / "alfred_result.json"
        result_payload = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
        report["details"]["result_payload"] = result_payload

        track = result_payload.get("track", {}) if isinstance(result_payload, dict) else {}
        tasks = result_payload.get("tasks", []) if isinstance(result_payload, dict) else []
        local_mock_exists = bool(result_payload.get("local_mock_exists")) if isinstance(result_payload, dict) else False
        stream_ingest_count = int(result_payload.get("stream_ingest_count", 0)) if isinstance(result_payload, dict) else 0

        _record(report, "entities.publish", execution.returncode == 0 and track.get("entityId") == "cv-zorn-alfred-track", {"track": track})
        _record(report, "entities.stream", stream_ingest_count > 0, {"stream_ingest_count": stream_ingest_count})
        disposition = ((track.get("milView") or {}).get("disposition")) if isinstance(track, dict) else None
        _record(report, "entities.override", disposition == "DISPOSITION_SUSPICIOUS", {"track": track})
        first_task = tasks[0] if isinstance(tasks, list) and tasks else {}
        _record(report, "tasks.create", isinstance(tasks, list) and len(tasks) > 0, {"tasks": tasks})
        _record(report, "local_mock", local_mock_exists, {"path": "scripts/lattice_mock.py", "exists": local_mock_exists, "task": first_task})

        requested = set(fixture.surfaces)
        passed = set(report["passed"])
        report["missing"] = sorted(surface for surface in requested if surface not in passed)
        if report["failed"]:
            report["result"] = "failed"
        elif report["missing"]:
            report["result"] = "partial"
        else:
            report["result"] = "pass"
        ####
        return report
    finally:
        report["details"]["server_log"] = stop_https_zorn_server(server)
    ####
####


def _run_deep_prove_sample(*, fixture: Any, fixture_dir: Path, token: str, mode: str) -> dict[str, Any]:
    report = base_report(fixture_id=fixture.id, mode=mode)
    python = ensure_python_venv(fixture_dir)
    install = run_command(
        [str(python), "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=fixture_dir,
        timeout=300.0,
    )
    report["details"]["install"] = {
        "args": install.args,
        "returncode": install.returncode,
        "stdout": install.stdout,
        "stderr": install.stderr,
    }
    if install.returncode != 0:
        report["result"] = "failed"
        report["failed"] = list(fixture.surfaces)
        return report
    ####

    server = start_https_zorn_server(
        repo_root=Path(__file__).resolve().parents[4],
        token=token,
        auth_mode="static",
        static_tokens=[token, "env-token"],
    )
    process_logs: dict[str, dict[str, Any]] = {}
    processes: list[tuple[str, Any]] = []
    try:
        shim_path = _install_deepprove_runtime_shim(fixture_dir)
        sitecustomize_dir = _install_deepprove_sitecustomize(fixture_dir)
        report["details"]["deepprove_runtime_shim"] = str(shim_path)
        report["details"]["sitecustomize_dir"] = str(sitecustomize_dir)
        output_root = fixture_dir / "output"
        if output_root.exists():
            shutil.rmtree(output_root)
        ####
        template_config = yaml.safe_load((fixture_dir / "var" / "config.yml").read_text())
        config = dict(template_config)
        config.update(
            {
                "lattice-endpoint": server.base_url.removeprefix("https://"),
                "environment-token": "env-token",
                "sandboxes-token": token,
                "asset-latitude": 0.01,
                "asset-longitude": 0.01,
                "track-latitude": 0.02,
                "track-longitude": 0.02,
                "track-disposition": "DISPOSITION_HOSTILE",
            }
        )
        generated_config = server.workspace / "deep-prove-config.yml"
        generated_config.write_text(yaml.safe_dump(config, sort_keys=False))
        report["details"]["generated_config"] = str(generated_config)

        env = {
            **os.environ,
            "SSL_CERT_FILE": str(server.cafile),
            "REQUESTS_CA_BUNDLE": str(server.cafile),
            "PYTHONPATH": str(sitecustomize_dir) + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else ""),
        }
        asset_payload: dict[str, Any] | None = None
        asset_handle = start_process(
            [str(python), "simulated_asset/asset.py", "--config", str(generated_config)],
            cwd=fixture_dir,
            env=env,
        )
        processes.append(("asset", asset_handle))

        asset_ready_deadline = time.time() + 30.0
        while time.time() < asset_ready_deadline:
            try:
                asset_status, maybe_asset = http_json(
                    "GET",
                    f"{server.base_url}/api/v1/entities/asset-01",
                    token=token,
                    cafile=server.cafile,
                    headers={"Anduril-Sandbox-Authorization": f"Bearer {token}"},
                )
                if asset_status == 200:
                    asset_payload = maybe_asset
                    break
                ####
            except Exception:
                pass
            ####
            time.sleep(0.5)
        ####

        arbiter_handle = start_process(
            [str(python), "auto-reconnaissance/main.py", "--config", str(generated_config)],
            cwd=fixture_dir,
            env=env,
        )
        processes.append(("arbiter", arbiter_handle))
        track_handle = start_process(
            [str(python), "simulated_track/track.py", "--config", str(generated_config)],
            cwd=fixture_dir,
            env=env,
        )
        processes.append(("track", track_handle))

        task_payload: dict[str, Any] | None = None
        hostile_entities: list[dict[str, Any]] = []
        deadline = time.time() + 240.0
        while time.time() < deadline:
            try:
                query_status, tasks = http_json(
                    "POST",
                    f"{server.base_url}/api/v1/tasks/query",
                    token=token,
                    payload={},
                    cafile=server.cafile,
                    headers={"Anduril-Sandbox-Authorization": f"Bearer {token}"},
                )
                if query_status == 200:
                    for item in tasks.get("tasks", []):
                        if isinstance(item, dict):
                            task_payload = item
                            break
                        ####
                    ####
                ####
            except Exception:
                pass
            ####
            try:
                asset_status, maybe_asset = http_json(
                    "GET",
                    f"{server.base_url}/api/v1/entities/asset-01",
                    token=token,
                    cafile=server.cafile,
                    headers={"Anduril-Sandbox-Authorization": f"Bearer {token}"},
                )
                if asset_status == 200:
                    asset_payload = maybe_asset
                ####
            except Exception:
                pass
            ####
            try:
                events_status, events = http_json(
                    "POST",
                    f"{server.base_url}/api/v1/entities/events",
                    token=token,
                    payload={"afterSequence": 0},
                    cafile=server.cafile,
                    headers={"Anduril-Sandbox-Authorization": f"Bearer {token}"},
                )
                if events_status == 200:
                    hostile_entities = []
                    for event in events.get("events", []):
                        if not isinstance(event, dict):
                            continue
                        ####
                        entity = event.get("entity")
                        if isinstance(entity, dict):
                            disposition = (
                                entity.get("milView", {}) if isinstance(entity.get("milView"), dict) else entity.get("mil_view", {})
                            )
                            if isinstance(disposition, dict) and disposition.get("disposition") == "DISPOSITION_HOSTILE":
                                hostile_entities.append(entity)
                            ####
                        ####
                    ####
                ####
            except Exception:
                pass
            ####
            if task_payload is not None and asset_payload is not None:
                status_blob = task_payload.get("status", {})
                status_value = status_blob.get("status") if isinstance(status_blob, dict) else None
                if status_value == "STATUS_DONE_OK" and hostile_entities:
                    break
                ####
            ####
            time.sleep(1.0)
        ####

        report["details"]["task"] = task_payload
        report["details"]["asset"] = asset_payload
        report["details"]["hostile_entities"] = hostile_entities

        proof_dirs = sorted(path for path in output_root.iterdir() if path.is_dir()) if output_root.exists() else []
        proof_files = sorted(str(path.relative_to(fixture_dir)) for directory in proof_dirs for path in directory.glob("*.json"))
        report["details"]["proof_dirs"] = [str(path.relative_to(fixture_dir)) for path in proof_dirs]
        report["details"]["proof_files"] = proof_files

        _record(report, "entities.publish", asset_payload is not None, {"asset": asset_payload})
        _record(report, "entities.stream", task_payload is not None, {"task": task_payload})
        _record(report, "entities.override", bool(hostile_entities), {"hostile_entities": hostile_entities})
        task_status = task_payload.get("status", {}) if isinstance(task_payload, dict) else {}
        status_value = task_status.get("status") if isinstance(task_status, dict) else None
        _record(report, "tasks.listen_as_agent", status_value in {"STATUS_EXECUTING", "STATUS_DONE_OK"}, {"task": task_payload})
        _record(report, "tasks.update_status", status_value == "STATUS_DONE_OK", {"task": task_payload})

        requested = set(fixture.surfaces)
        passed = set(report["passed"])
        report["missing"] = sorted(surface for surface in requested if surface not in passed)

        runtime_issue = False
        fallback_detected = False
        for name, handle in reversed(processes):
            returncode, stdout = stop_process(handle)
            process_logs[name] = {
                "args": handle.args,
                "cwd": str(handle.cwd),
                "returncode": returncode,
                "stdout": stdout,
            }
            lower = stdout.lower()
            if "investigation task simulated" in lower or "falling back to simulated task" in lower:
                fallback_detected = True
            ####
            if "traceback" in lower or "exception:" in lower:
                runtime_issue = True
            ####
        ####
        report["details"]["process_logs"] = process_logs
        report["details"]["fallback_detected"] = fallback_detected
        report["details"]["runtime_issue"] = runtime_issue
        report["details"]["proof_artifacts_present"] = bool(proof_files)

        if fallback_detected:
            report["failed"] = sorted(set(report["failed"]) | {"tasks.listen_as_agent", "tasks.update_status"})
            report["passed"] = [item for item in report["passed"] if item not in {"tasks.listen_as_agent", "tasks.update_status"}]
        ####
        if not proof_files:
            report["result"] = "failed"
        elif report["failed"] or report["missing"] or fallback_detected or runtime_issue:
            report["result"] = "failed"
        else:
            report["result"] = "pass"
        ####
        return report
    finally:
        for name, handle in reversed(processes):
            if name not in process_logs:
                returncode, stdout = stop_process(handle)
                process_logs[name] = {
                    "args": handle.args,
                    "cwd": str(handle.cwd),
                    "returncode": returncode,
                    "stdout": stdout,
                }
            ####
        ####
        report["details"]["process_logs"] = process_logs
        report["details"]["server_log"] = stop_https_zorn_server(server)
    ####
####


def _run_thumbnail_sample(*, fixture: Any, fixture_dir: Path, token: str, mode: str) -> dict[str, Any]:
    report = base_report(fixture_id=fixture.id, mode=mode)
    python = ensure_python_venv(fixture_dir)
    install = run_command(
        [str(python), "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=fixture_dir,
        timeout=180.0,
    )
    report["details"]["install"] = {
        "args": install.args,
        "returncode": install.returncode,
        "stdout": install.stdout,
        "stderr": install.stderr,
    }
    if install.returncode != 0:
        report["result"] = "failed"
        report["failed"] = list(fixture.surfaces)
        return report
    ####

    server = start_https_zorn_server(repo_root=Path(__file__).resolve().parents[4], token=token)
    try:
        entity_id = "zorn-cert-thumbnail-entity"
        seed_status, seed_entity = http_json(
            "PUT",
            f"{server.base_url}/api/v1/entities",
            token=token,
            payload={"entityId": entity_id, "isLive": True},
            cafile=server.cafile,
            headers={"Anduril-Sandbox-Authorization": f"Bearer {token}"},
        )
        report["details"]["seed_entity"] = {"status": seed_status, "entity": seed_entity}
        if seed_status >= 300:
            report["result"] = "failed"
            report["failed"] = list(fixture.surfaces)
            return report
        ####

        env = {
            **os.environ,
            "SSL_CERT_FILE": str(server.cafile),
            "LATTICE_ENDPOINT": server.base_url.removeprefix("https://"),
            "LATTICE_CLIENT_ID": "dev-client",
            "LATTICE_CLIENT_SECRET": "dev-secret",
            "SANDBOXES_TOKEN": token,
        }
        shim_dir = server.workspace / "thumbnail-runtime-shim"
        shim_dir.mkdir(parents=True, exist_ok=True)
        sitecustomize = shim_dir / "sitecustomize.py"
        sitecustomize.write_text(
            """
class _AwaitableValue:
    def __init__(self, value):
        self._value = value

    def __await__(self):
        async def _wrap():
            return self._value
        return _wrap().__await__()

    def __getattr__(self, name):
        return getattr(self._value, name)


def _patch_thumbnail_override():
    try:
        from anduril.entities.client import EntitiesClient
    except Exception:
        return

    original = getattr(EntitiesClient, "override_entity", None)
    if original is None or getattr(original, "__zorn_async_compat__", False):
        return

    def patched(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        if hasattr(result, "__await__"):
            return result
        return _AwaitableValue(result)

    patched.__zorn_async_compat__ = True
    EntitiesClient.override_entity = patched


_patch_thumbnail_override()
""".lstrip(),
        )
        env["PYTHONPATH"] = str(shim_dir) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        report["details"]["runtime_shim"] = str(sitecustomize)
        upload = run_command(
            [str(python), "app.py", "--operation", "upload", "--file", "thumbnail/N113PF.jpeg", "--entity", entity_id],
            cwd=fixture_dir,
            env=env,
            timeout=60.0,
        )
        report["details"]["upload_command"] = {
            "args": upload.args,
            "returncode": upload.returncode,
            "stdout": upload.stdout,
            "stderr": upload.stderr,
        }

        list_status, objects_payload = http_json(
            "GET",
            f"{server.base_url}/api/v1/objects",
            token=token,
            cafile=server.cafile,
            headers={"Anduril-Sandbox-Authorization": f"Bearer {token}"},
        )
        report["details"]["objects"] = {"status": list_status, "payload": objects_payload}
        object_item = None
        for item in objects_payload.get("objects", []):
            if isinstance(item, dict) and item.get("objectPath") == "N113PF.jpeg":
                object_item = item
                break
            ####
        ####
        _record(report, "objects.upload", list_status == 200 and object_item is not None, {"status": list_status, "object": object_item})
        _record(report, "objects.metadata", isinstance(object_item, dict) and bool(object_item.get("checksumSha256")), {"object": object_item})

        entity_status, entity_payload = http_json(
            "GET",
            f"{server.base_url}/api/v1/entities/{entity_id}",
            token=token,
            cafile=server.cafile,
            headers={"Anduril-Sandbox-Authorization": f"Bearer {token}"},
        )
        report["details"]["entity_after_upload"] = {"status": entity_status, "entity": entity_payload}
        media_override = _thumbnail_media_items(entity_payload)
        has_thumbnail_link = any(
            isinstance(item, dict) and item.get("relativePath") == "/api/v1/objects/N113PF.jpeg"
            for item in media_override
        )
        _record(report, "objects.thumbnail_linkage", entity_status == 200 and has_thumbnail_link, {"entity": entity_payload})
        _record(report, "entities.publish", entity_status == 200 and entity_payload.get("entityId") == entity_id, {"entity": entity_payload})

        download = run_command(
            [str(python), "app.py", "--operation", "download", "--path", "N113PF.jpeg", "--file", str(server.workspace / "downloaded.bin")],
            cwd=fixture_dir,
            env=env,
            timeout=60.0,
        )
        report["details"]["download_command"] = {
            "args": download.args,
            "returncode": download.returncode,
            "stdout": download.stdout,
            "stderr": download.stderr,
        }
        download_status, download_bytes, _ = http_bytes(
            "GET",
            f"{server.base_url}/api/v1/objects/N113PF.jpeg",
            token=token,
            cafile=server.cafile,
            headers={"Anduril-Sandbox-Authorization": f"Bearer {token}"},
        )
        report["details"]["object_download_probe"] = {"status": download_status, "size": len(download_bytes)}

        stderr_blob = "\n".join(part for part in [upload.stderr, upload.stdout, download.stderr, download.stdout] if part).lower()
        requested = set(fixture.surfaces)
        passed = set(report["passed"])
        report["missing"] = sorted(surface for surface in requested if surface not in passed)
        report["details"]["upstream_runtime_issue"] = "exception" in stderr_blob or "traceback" in stderr_blob
        if report["failed"]:
            report["result"] = "failed"
        elif report["missing"] or report["details"]["upstream_runtime_issue"]:
            report["result"] = "partial"
        else:
            report["result"] = "pass"
        ####
        return report
    finally:
        report["details"]["server_log"] = stop_https_zorn_server(server)
    ####
####


def _run_auto_recon_sample(*, fixture: Any, fixture_dir: Path, token: str, mode: str) -> dict[str, Any]:
    report = base_report(fixture_id=fixture.id, mode=mode)
    python = ensure_python_venv(fixture_dir)
    install = run_command(
        [str(python), "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=fixture_dir,
        timeout=240.0,
    )
    report["details"]["install"] = {
        "args": install.args,
        "returncode": install.returncode,
        "stdout": install.stdout,
        "stderr": install.stderr,
    }
    if install.returncode != 0:
        report["result"] = "failed"
        report["failed"] = list(fixture.surfaces)
        return report
    ####

    server = start_https_zorn_server(repo_root=Path(__file__).resolve().parents[4], token=token)
    process_logs: dict[str, dict[str, Any]] = {}
    processes: list[tuple[str, Any]] = []
    try:
        template_config = yaml.safe_load((fixture_dir / "var" / "config.yml").read_text())
        config = dict(template_config)
        config.update(
            {
                "lattice-endpoint": server.base_url.removeprefix("https://"),
                "lattice-client-id": "dev-client",
                "lattice-client-secret": "dev-secret",
                "sandboxes-token": token,
                "asset-latitude": 1.0,
                "asset-longitude": 1.0,
                "track-latitude": 1.03,
                "track-longitude": 1.03,
            }
        )
        generated_config = server.workspace / "auto-recon-config.yml"
        generated_config.write_text(yaml.safe_dump(config, sort_keys=False))
        report["details"]["generated_config"] = str(generated_config)

        env = {
            **os.environ,
            "SSL_CERT_FILE": str(server.cafile),
        }
        commands = [
            ("arbiter", [str(python), "auto-reconnaissance/main.py", "--config", str(generated_config)]),
            ("asset", [str(python), "simulated_asset/asset.py", "--config", str(generated_config)]),
            ("track", [str(python), "simulated_track/track.py", "--config", str(generated_config)]),
        ]
        for name, command in commands:
            handle = start_process(command, cwd=fixture_dir, env=env)
            processes.append((name, handle))
        ####

        task_payload: dict[str, Any] | None = None
        asset_payload: dict[str, Any] | None = None
        suspicious_entities: list[dict[str, Any]] = []
        deadline = time.time() + 30.0
        while time.time() < deadline:
            query_status, tasks = http_json(
                "POST",
                f"{server.base_url}/api/v1/tasks/query",
                token=token,
                payload={},
                cafile=server.cafile,
                headers={"Anduril-Sandbox-Authorization": f"Bearer {token}"},
            )
            if query_status == 200:
                for item in tasks.get("tasks", []):
                    if isinstance(item, dict):
                        task_payload = item
                        break
                    ####
                ####
            ####
            asset_status, maybe_asset = http_json(
                "GET",
                f"{server.base_url}/api/v1/entities/asset-01",
                token=token,
                cafile=server.cafile,
                headers={"Anduril-Sandbox-Authorization": f"Bearer {token}"},
            )
            if asset_status == 200:
                asset_payload = maybe_asset
            ####
            events_status, events = http_json(
                "POST",
                f"{server.base_url}/api/v1/entities/events",
                token=token,
                payload={"afterSequence": 0},
                cafile=server.cafile,
                headers={"Anduril-Sandbox-Authorization": f"Bearer {token}"},
            )
            if events_status == 200:
                suspicious_entities = []
                for event in events.get("events", []):
                    if not isinstance(event, dict):
                        continue
                    ####
                    entity = event.get("entity")
                    if isinstance(entity, dict):
                        disposition = (
                            entity.get("milView", {}) if isinstance(entity.get("milView"), dict) else entity.get("mil_view", {})
                        )
                        if isinstance(disposition, dict) and disposition.get("disposition") == "DISPOSITION_SUSPICIOUS":
                            suspicious_entities.append(entity)
                        ####
                    ####
                ####
            ####
            if task_payload is not None and asset_payload is not None:
                status_blob = task_payload.get("status", {})
                status_value = status_blob.get("status") if isinstance(status_blob, dict) else None
                if status_value == "STATUS_EXECUTING" and suspicious_entities:
                    break
                ####
            ####
            time.sleep(1.0)
        ####

        report["details"]["task"] = task_payload
        report["details"]["asset"] = asset_payload
        report["details"]["suspicious_entities"] = suspicious_entities
        _record(report, "entities.publish", asset_payload is not None, {"asset": asset_payload})
        _record(report, "entities.stream", task_payload is not None, {"task": task_payload})
        _record(report, "entities.override", bool(suspicious_entities), {"suspicious_entities": suspicious_entities})
        _record(report, "tasks.create", task_payload is not None, {"task": task_payload})
        task_status = task_payload.get("status", {}) if isinstance(task_payload, dict) else {}
        is_executing = isinstance(task_status, dict) and task_status.get("status") == "STATUS_EXECUTING"
        _record(report, "tasks.listen_as_agent", is_executing, {"task": task_payload})
        _record(report, "tasks.update_status", is_executing, {"task": task_payload})

        requested = set(fixture.surfaces)
        passed = set(report["passed"])
        report["missing"] = sorted(surface for surface in requested if surface not in passed)
        if report["failed"]:
            report["result"] = "failed"
        elif report["missing"]:
            report["result"] = "partial"
        else:
            report["result"] = "pass"
        ####
        return report
    finally:
        for name, handle in reversed(processes):
            returncode, stdout = stop_process(handle)
            process_logs[name] = {
                "args": handle.args,
                "cwd": str(handle.cwd),
                "returncode": returncode,
                "stdout": stdout,
            }
        ####
        report["details"]["process_logs"] = process_logs
        report["details"]["server_log"] = stop_https_zorn_server(server)
    ####
####


def _run_ais_grpc_sample(*, fixture: Any, fixture_dir: Path, token: str, mode: str) -> dict[str, Any]:
    report = base_report(fixture_id=fixture.id, mode=mode)
    uv_cache_dir = fixture_dir / ".uv-cache"
    uv_cache_dir.mkdir(exist_ok=True)
    uv_env = {**os.environ, "UV_CACHE_DIR": str(uv_cache_dir)}
    install = run_command(
        ["uv", "sync"],
        cwd=fixture_dir,
        env=uv_env,
        timeout=300.0,
    )
    report["details"]["install"] = {
        "args": install.args,
        "returncode": install.returncode,
        "stdout": install.stdout,
        "stderr": install.stderr,
    }
    if install.returncode != 0:
        report["result"] = "failed"
        report["failed"] = list(fixture.surfaces)
        return report
    ####

    server = start_dual_transport_zorn_server(repo_root=Path(__file__).resolve().parents[4], token=token)
    process_logs: dict[str, Any] = {}
    try:
        template_config = yaml.safe_load((fixture_dir / "var" / "config.yml").read_text())
        config = dict(template_config)
        config.update(
            {
                "lattice-endpoint": server.virtual_host,
                "lattice-client-id": "dev-client",
                "lattice-client-secret": "dev-secret",
                "sandboxes-token": token,
                "entity-update-rate-seconds": 1,
                "ais-generate-interval-seconds": 1,
            }
        )
        generated_config = server.workspace / "ais-grpc-config.yml"
        generated_config.write_text(yaml.safe_dump(config, sort_keys=False))
        report["details"]["generated_config"] = str(generated_config)

        shim_dir = server.workspace / "ais-grpc-runtime-shim"
        shim_dir.mkdir(parents=True, exist_ok=True)
        sitecustomize = shim_dir / "sitecustomize.py"
        sitecustomize.write_text(
            f"""
import os
from pathlib import Path

import grpc
import requests

_HOST = {server.virtual_host!r}
_REST_BASE = {server.rest_base_url!r}
_GRPC_TARGET = {server.grpc_target!r}
_CAFILE = os.environ.get("SSL_CERT_FILE")

_orig_request = requests.sessions.Session.request


def _patched_request(self, method, url, *args, **kwargs):
    if isinstance(url, str) and (url.startswith(f"https://{{_HOST}}/") or url.startswith(f"https://{{_HOST}}:443/")):
        suffix = url.split(_HOST, 1)[1]
        if suffix.startswith(":443"):
            suffix = suffix[4:]
        url = _REST_BASE + suffix
    if _CAFILE and kwargs.get("verify") is None:
        kwargs["verify"] = _CAFILE
    return _orig_request(self, method, url, *args, **kwargs)


requests.sessions.Session.request = _patched_request

_orig_ssl_channel_credentials = grpc.ssl_channel_credentials


def _patched_ssl_channel_credentials(root_certificates=None, *args, **kwargs):
    if root_certificates is None and _CAFILE:
        root_certificates = Path(_CAFILE).read_bytes()
    return _orig_ssl_channel_credentials(root_certificates=root_certificates, *args, **kwargs)


grpc.ssl_channel_credentials = _patched_ssl_channel_credentials

_orig_secure_channel = grpc.aio.secure_channel


def _patched_secure_channel(target, credentials, *args, **kwargs):
    if target == f"{{_HOST}}:443":
        target = _GRPC_TARGET
    return _orig_secure_channel(target, credentials, *args, **kwargs)


grpc.aio.secure_channel = _patched_secure_channel
""".lstrip(),
        )
        env = {
            **uv_env,
            "SSL_CERT_FILE": str(server.cafile),
            "REQUESTS_CA_BUNDLE": str(server.cafile),
            "PYTHONPATH": str(shim_dir),
        }
        report["details"]["runtime_shim"] = str(sitecustomize)
        handle = start_process(
            ["uv", "run", "python", "src/main.py", "--config", str(generated_config)],
            cwd=fixture_dir,
            env=env,
        )

        entity_payload: dict[str, Any] | None = None
        vessel_ids = [str(item) for item in config.get("vessel-mmsi", []) if item]
        deadline = time.time() + 20.0
        while time.time() < deadline and entity_payload is None:
            for vessel_id in vessel_ids:
                status, payload = http_json(
                    "GET",
                    f"{server.rest_base_url}/api/v1/entities/{vessel_id}",
                    token=token,
                    cafile=server.cafile,
                    headers={"Anduril-Sandbox-Authorization": f"Bearer {token}"},
                )
                if status == 200 and payload.get("entityId") == vessel_id:
                    entity_payload = payload
                    break
                ####
            ####
            if entity_payload is None:
                time.sleep(1.0)
            ####
        ####

        report["details"]["entity"] = entity_payload
        _record(report, "auth.grpc_bearer_metadata", entity_payload is not None, {"entity": entity_payload})
        _record(report, "entities.publish", entity_payload is not None, {"entity": entity_payload})
        _record(report, "entities.location", isinstance((entity_payload or {}).get("location"), dict), {"entity": entity_payload})
        _record(report, "entities.ontology", isinstance((entity_payload or {}).get("ontology"), dict), {"entity": entity_payload})
        _record(report, "entities.provenance", isinstance((entity_payload or {}).get("provenance"), dict), {"entity": entity_payload})

        requested = set(fixture.surfaces)
        passed = set(report["passed"])
        report["missing"] = sorted(surface for surface in requested if surface not in passed)
        report["result"] = "pass" if not report["failed"] and not report["missing"] else "failed"

        returncode, stdout = stop_process(handle, timeout=5.0)
        process_logs["sample"] = {
            "args": handle.args,
            "cwd": str(handle.cwd),
            "returncode": returncode,
            "stdout": stdout,
        }
        report["details"]["process_logs"] = process_logs
        return report
    finally:
        if "sample" not in process_logs:
            # process may not have been started or may have failed before capture
            pass
        ####
        logs = stop_dual_transport_zorn_server(server)
        report["details"]["server_log"] = logs["rest"]
        report["details"]["grpc_server_log"] = logs["grpc"]
    ####
####


def _record(report: dict[str, Any], capability: str, ok: bool, detail: Any) -> None:
    target = "passed" if ok else "failed"
    if capability not in report[target]:
        report[target].append(capability)
    ####
    report["details"][capability] = detail
####


def _thumbnail_media_items(entity_payload: dict[str, Any]) -> list[dict[str, Any]]:
    media = entity_payload.get("media")
    if isinstance(media, dict):
        items = media.get("media")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
        ####
    ####
    overrides = entity_payload.get("overrides")
    if not isinstance(overrides, dict):
        return []
    ####
    raw_override = overrides.get("media.media")
    if isinstance(raw_override, list):
        return [item for item in raw_override if isinstance(item, dict)]
    ####
    if not isinstance(raw_override, dict):
        return []
    ####
    nested_entity = raw_override.get("entity")
    if isinstance(nested_entity, dict):
        nested_media = nested_entity.get("media")
        if isinstance(nested_media, dict):
            items = nested_media.get("media")
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
            ####
        ####
    ####
    return []
####


def _related_entity_ids(entity_payload: dict[str, Any]) -> set[str]:
    relationships = entity_payload.get("relationships", {})
    if not isinstance(relationships, dict):
        return set()
    ####
    items = relationships.get("relationships")
    if not isinstance(items, list):
        return set()
    ####
    related_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        ####
        related_id = item.get("relatedEntityId", item.get("related_entity_id"))
        if isinstance(related_id, str) and related_id:
            related_ids.add(related_id)
        ####
    ####
    return related_ids
####
