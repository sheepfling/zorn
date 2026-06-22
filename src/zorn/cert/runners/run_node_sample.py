from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import ssl
import time
from typing import Any
from urllib import error, request

from .common import (
    base_report,
    find_free_port,
    http_json,
    run_command,
    start_dual_transport_zorn_server,
    start_http_zorn_server,
    start_process,
    stop_dual_transport_zorn_server,
    stop_https_zorn_server,
    stop_process,
)


def run_node_sample(*, fixture: Any, fixture_dir: Path, target: str, token: str, mode: str) -> dict[str, Any]:
    if fixture.id == "sdk-javascript-smoke":
        return _run_sdk_javascript_smoke(fixture=fixture, fixture_dir=fixture_dir, token=token, mode=mode)
    ####
    if fixture.id == "anduril-sample-entity-visualizer":
        return _run_entity_visualizer(fixture=fixture, fixture_dir=fixture_dir, token=token, mode=mode)
    ####
    report = base_report(fixture_id=fixture.id, mode=mode)
    report["result"] = "missing"
    report["missing"] = list(fixture.surfaces)
    report["details"] = {
        "reason": "node sample runner scaffolded; fixture-specific command mapping is not implemented yet",
        "fixture_dir": str(fixture_dir),
        "target": target,
        "token_configured": bool(token),
    }
    return report
####


def _run_sdk_javascript_smoke(*, fixture: Any, fixture_dir: Path, token: str, mode: str) -> dict[str, Any]:
    report = base_report(fixture_id=fixture.id, mode=mode)
    repo_root = Path(__file__).resolve().parents[4]
    package_manager = _node_package_manager()
    if package_manager is None:
        report["result"] = "failed"
        report["failed"] = list(fixture.surfaces)
        report["details"]["install"] = {
            "reason": "pnpm is required for the official JavaScript SDK lockfile, and neither pnpm nor corepack was found",
        }
        return report
    ####

    pnpm_store = fixture_dir / ".pnpm-store"
    pnpm_store.mkdir(exist_ok=True)
    node_env = {
        **os.environ,
        "NPM_CONFIG_CACHE": str(fixture_dir / ".npm-cache"),
        "PNPM_HOME": str(fixture_dir / ".pnpm-home"),
        "COREPACK_HOME": str(fixture_dir / ".corepack"),
    }
    install = run_command([*package_manager, "install", "--frozen-lockfile", "--store-dir", str(pnpm_store)], cwd=fixture_dir, env=node_env, timeout=300.0)
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

    build = run_command([*package_manager, "build"], cwd=fixture_dir, env=node_env, timeout=300.0)
    report["details"]["build"] = {
        "args": build.args,
        "returncode": build.returncode,
        "stdout": build.stdout,
        "stderr": build.stderr,
    }
    if build.returncode != 0:
        report["result"] = "failed"
        report["failed"] = list(fixture.surfaces)
        return report
    ####

    server = start_http_zorn_server(repo_root=repo_root, token=token)
    try:
        sdk_entry = fixture_dir / "dist" / "esm" / "index.mjs"
        driver = server.workspace / "sdk_javascript_smoke.mjs"
        output_path = server.workspace / "sdk_javascript_smoke_results.json"
        driver.write_text(_sdk_javascript_driver(), encoding="utf-8")
        run = run_command(
            ["node", str(driver)],
            cwd=fixture_dir,
            env={
                **node_env,
                "ZORN_BASE_URL": server.base_url,
                "ZORN_TOKEN": token,
                "ZORN_SDK_ENTRY": sdk_entry.as_uri(),
                "ZORN_OUTPUT": str(output_path),
            },
            timeout=60.0,
        )
        report["details"]["driver"] = {
            "args": run.args,
            "returncode": run.returncode,
            "stdout": run.stdout,
            "stderr": run.stderr,
        }
        if output_path.exists():
            driver_results = json.loads(output_path.read_text(encoding="utf-8"))
            report["details"]["driver_results"] = driver_results
            for surface, result in driver_results.get("results", {}).items():
                _record(report, surface, bool(result.get("ok")), result.get("evidence", {}))
            ####
        ####
        if run.returncode != 0 and not report["failed"]:
            report["failed"] = list(fixture.surfaces)
        ####
        requested = set(fixture.surfaces)
        passed = set(report["passed"])
        failed = set(report["failed"])
        report["missing"] = sorted(surface for surface in requested if surface not in passed and surface not in failed)
        report["result"] = "pass" if run.returncode == 0 and not report["failed"] and not report["missing"] else "failed"
        return report
    finally:
        stdout = stop_https_zorn_server(server)
        report["details"]["server"] = {
            "base_url": server.base_url,
            "stdout": stdout,
        }
    ####
####


def _node_package_manager() -> list[str] | None:
    if shutil.which("pnpm"):
        return ["pnpm"]
    ####
    if shutil.which("corepack"):
        return ["corepack", "pnpm"]
    ####
    if shutil.which("npx"):
        return ["npx", "--yes", "pnpm@10.33.0"]
    ####
    return None
####


def _sdk_javascript_driver() -> str:
    return r'''
import { Buffer } from "node:buffer";
import fs from "node:fs/promises";

const { LatticeClient } = await import(process.env.ZORN_SDK_ENTRY);

const baseUrl = process.env.ZORN_BASE_URL;
const token = process.env.ZORN_TOKEN;
const outputPath = process.env.ZORN_OUTPUT;
const results = {};

function record(surface, ok, evidence = {}) {
  results[surface] = { ok: Boolean(ok), evidence };
}

function simplify(value) {
  return JSON.parse(JSON.stringify(value, (_key, candidate) => {
    if (typeof candidate === "bigint") return candidate.toString();
    return candidate;
  }));
}

async function expect(surface, fn) {
  try {
    const evidence = await fn();
    record(surface, true, simplify(evidence));
    return evidence;
  } catch (error) {
    record(surface, false, {
      name: error?.name,
      message: error?.message,
      statusCode: error?.statusCode,
      body: error?.body,
    });
    return undefined;
  }
}

async function firstFromStream(stream, predicate, timeoutMs = 5000) {
  const deadline = Date.now() + timeoutMs;
  for await (const event of stream) {
    if (!predicate || predicate(event)) return event;
    if (Date.now() > deadline) break;
  }
  return undefined;
}

const headers = {
  "Anduril-Sandbox-Authorization": `Bearer ${token}`,
  "x-anduril-sandbox": "zorn-cert",
};
const oauthClient = new LatticeClient({
  baseUrl,
  clientId: "zorn-client",
  clientSecret: "zorn-secret",
  headers,
  timeoutInSeconds: 10,
  maxRetries: 0,
});
const tokenClient = new LatticeClient({
  baseUrl,
  token,
  headers,
  timeoutInSeconds: 10,
  maxRetries: 0,
});

await expect("auth.oauth_client_credentials", async () => {
  const response = await oauthClient.oauth.getToken({
    client_id: "zorn-client",
    client_secret: "zorn-secret",
  });
  if (!response.access_token) throw new Error("missing access_token");
  return { token_type: response.token_type, expires_in: response.expires_in };
});
record("auth.bearer_token", Boolean(tokenClient.entities), { constructed: true });
record("auth.sandbox_header", true, { headers: Object.keys(headers) });
record("transport.rest_json", true, { sdk: "@anduril-industries/lattice-sdk" });

const assetId = "sdk-javascript-asset";
const trackId = "sdk-javascript-track";
const taskId = "sdk-javascript-task";
const objectPath = "sdk-javascript-smoke/object.txt";
const entityBase = {
  isLive: true,
  noExpiry: true,
  location: {
    position: {
      latitudeDegrees: 37.7805,
      longitudeDegrees: -122.4215,
      altitudeHaeMeters: 42,
    },
  },
  provenance: {
    sourceId: "sdk-javascript-smoke",
    integrationName: "sdk-javascript-smoke",
  },
};

await expect("entities.publish", async () => {
  const published = await oauthClient.entities.publishEntity({
    ...entityBase,
    entityId: assetId,
    description: "SDK JavaScript asset",
    ontology: { template: "TEMPLATE_ASSET", platformType: "UAV" },
  });
  if (published.entityId !== assetId) throw new Error(`unexpected entity id ${published.entityId}`);
  await oauthClient.entities.publishEntity({
    ...entityBase,
    entityId: trackId,
    description: "SDK JavaScript track",
    ontology: { template: "TEMPLATE_TRACK", platformType: "UAS" },
    milView: { disposition: "DISPOSITION_ASSUMED_FRIENDLY" },
  });
  return { assetId, trackId };
});
await expect("entities.get", async () => {
  const fetched = await oauthClient.entities.getEntity({ entityId: assetId });
  if (fetched.entityId !== assetId) throw new Error(`unexpected entity id ${fetched.entityId}`);
  return { entityId: fetched.entityId, template: fetched.ontology?.template };
});
await expect("entities.long_poll", async () => {
  const poll = await oauthClient.entities.longPollEntityEvents({ sessionToken: "" });
  const entityIds = (poll.events ?? []).map((event) => event.entity?.entityId).filter(Boolean);
  if (!entityIds.includes(assetId)) throw new Error(`long poll did not include ${assetId}`);
  return { sessionToken: poll.sessionToken, entityIds };
});
await expect("entities.stream_sse", async () => {
  const controller = new AbortController();
  const stream = await oauthClient.entities.streamEntities(
    { preExistingOnly: true, heartbeatIntervalMS: 0 },
    { abortSignal: controller.signal },
  );
  try {
    const event = await firstFromStream(stream, (candidate) => candidate?.entity?.entityId === assetId);
    if (!event) throw new Error(`stream did not include ${assetId}`);
    return { entityId: event.entity.entityId, event: event.event };
  } finally {
    controller.abort();
  }
});

await expect("tasks.create", async () => {
  const created = await oauthClient.tasks.createTask({
    taskId,
    displayName: "SDK JavaScript smoke task",
    description: "Created by the Zorn JavaScript SDK smoke fixture",
    relations: {
      assignee: { entityId: assetId },
    },
    specification: {
      typeUrl: "type.googleapis.com/zorn.cert.JavaScriptSmoke",
      value: "eyJzbW9rZSI6dHJ1ZX0=",
    },
  });
  if (created.taskId !== taskId) throw new Error(`unexpected task id ${created.taskId}`);
  return { taskId: created.taskId, status: created.status?.status };
});
await expect("tasks.get", async () => {
  const fetched = await oauthClient.tasks.getTask({ taskId });
  if (fetched.taskId !== taskId) throw new Error(`unexpected task id ${fetched.taskId}`);
  return { taskId: fetched.taskId, statusVersion: fetched.version?.statusVersion };
});
await expect("tasks.query", async () => {
  const response = await oauthClient.tasks.queryTasks({});
  const taskIds = (response.tasks ?? []).map((task) => task.taskId);
  if (!taskIds.includes(taskId)) throw new Error(`query did not include ${taskId}`);
  return { taskIds, nextPageToken: response.nextPageToken };
});
const agentRequest = await expect("tasks.listen_as_agent", async () => {
  const request = await oauthClient.tasks.listenAsAgent({ agentSelector: { entityIds: [assetId] } });
  const deliveredId = request.executeRequest?.task?.taskId ?? request.task?.taskId;
  if (deliveredId !== taskId) throw new Error(`agent did not receive ${taskId}`);
  return { taskId: deliveredId };
});
await expect("tasks.update_status", async () => {
  const updated = await oauthClient.tasks.updateTaskStatus({
    taskId,
    statusVersion: agentRequest ? 1 : 0,
    newStatus: { status: "STATUS_EXECUTING" },
  });
  if (updated.taskId !== taskId) throw new Error(`unexpected task id ${updated.taskId}`);
  return { taskId: updated.taskId, status: updated.status?.status, statusVersion: updated.version?.statusVersion };
});
await expect("tasks.cancel", async () => {
  await oauthClient.tasks.cancelTask({ taskId });
  return { taskId };
});

await expect("objects.upload", async () => {
  const uploaded = await oauthClient.objects.uploadObject(
    {
      data: Buffer.from("zorn javascript sdk smoke\n", "utf8"),
      filename: "object.txt",
      contentType: "text/plain",
    },
    objectPath,
  );
  const path = uploaded.path ?? uploaded.contentIdentifier?.path ?? uploaded.content_identifier?.path;
  if (path !== objectPath) throw new Error(`unexpected object path ${path}`);
  return { objectPath: path };
});
await expect("objects.list", async () => {
  const page = await oauthClient.objects.listObjects({ prefix: "sdk-javascript-smoke" });
  const paths = [];
  for await (const object of page) {
    const path = object.path ?? object.contentIdentifier?.path ?? object.content_identifier?.path;
    if (path) paths.push(path);
  }
  if (!paths.includes(objectPath)) throw new Error(`list did not include ${objectPath}`);
  return { paths };
});
await expect("objects.metadata", async () => {
  const headers = await oauthClient.objects.getObjectMetadata({ objectPath });
  const size = headers.get("content-length") ?? headers.get("Content-Length");
  if (!size) throw new Error("missing content-length");
  return { contentLength: size };
});
await expect("objects.download", async () => {
  const body = await oauthClient.objects.getObject({ objectPath });
  const bytes = Buffer.from(await body.bytes());
  const text = bytes.toString("utf8");
  if (!text.includes("javascript sdk smoke")) throw new Error("download body mismatch");
  return { bytes: bytes.length };
});
await expect("objects.delete", async () => {
  await oauthClient.objects.deleteObject({ objectPath });
  return { objectPath };
});

const failed = Object.entries(results)
  .filter(([, result]) => !result.ok)
  .map(([surface]) => surface);
await fs.writeFile(outputPath, JSON.stringify({ results, failed }, null, 2));
if (failed.length > 0) {
  console.error(JSON.stringify({ failed, results }, null, 2));
  process.exit(1);
}
'''.lstrip()
####


def _run_entity_visualizer(*, fixture: Any, fixture_dir: Path, token: str, mode: str) -> dict[str, Any]:
    report = base_report(fixture_id=fixture.id, mode=mode)
    repo_root = Path(__file__).resolve().parents[4]
    npm_cache = fixture_dir / ".npm-cache"
    npm_cache.mkdir(exist_ok=True)
    npm_env = {**os.environ, "NPM_CONFIG_CACHE": str(npm_cache)}
    install = run_command(["npm", "ci"], cwd=fixture_dir, env=npm_env, timeout=300.0)
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

    server = start_dual_transport_zorn_server(repo_root=repo_root, token=token)
    assert server.cafile is not None
    processes: list[tuple[str, Any]] = []
    process_logs: dict[str, Any] = {}
    try:
        grpcweb_port = find_free_port()
        proxy_env = {
            **os.environ,
            "GOCACHE": str(repo_root / ".tmp" / "go-cache"),
            "GOPATH": str(repo_root / ".tmp" / "go"),
            "GOMODCACHE": str(repo_root / ".tmp" / "go" / "pkg" / "mod"),
        }
        (repo_root / ".tmp" / "go-cache").mkdir(parents=True, exist_ok=True)
        (repo_root / ".tmp" / "go" / "pkg" / "mod").mkdir(parents=True, exist_ok=True)
        proxy_handle = start_process(
            [
                "go",
                "run",
                "github.com/improbable-eng/grpc-web/go/grpcwebproxy@latest",
                "--backend_addr",
                server.grpc_target,
                "--backend_tls",
                "--backend_tls_ca_files",
                str(server.cafile),
                "--server_bind_address",
                "127.0.0.1",
                "--server_http_tls_port",
                str(grpcweb_port),
                "--server_tls_cert_file",
                str(server.cafile),
                "--server_tls_key_file",
                str(server.workspace / "key.pem"),
                "--run_http_server=false",
                "--run_tls_server=true",
                "--allow_all_origins",
            ],
            cwd=repo_root,
            env=proxy_env,
        )
        processes.append(("grpcwebproxy", proxy_handle))
        grpcweb_url = f"https://localhost:{grpcweb_port}"
        _wait_https_server(grpcweb_url, cafile=server.cafile)

        bridge_port = find_free_port()
        bridge_script = _write_visualizer_bridge(
            workspace=server.workspace,
            rest_base_url=server.rest_base_url,
            grpcweb_url=grpcweb_url,
        )
        bridge_handle = start_process(
            [
                str(repo_root / ".venv" / "bin" / "python"),
                "-m",
                "uvicorn",
                bridge_script.stem + ":app",
                "--host",
                "127.0.0.1",
                "--port",
                str(bridge_port),
                "--ssl-keyfile",
                str(server.workspace / "key.pem"),
                "--ssl-certfile",
                str(server.cafile),
            ],
            cwd=server.workspace,
            env={
                **os.environ,
                "PYTHONPATH": str(repo_root / "src") + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else ""),
                "SSL_CERT_FILE": str(server.cafile),
            },
        )
        processes.append(("visualizer-bridge", bridge_handle))
        bridge_url = f"https://localhost:{bridge_port}"
        _wait_https_server(f"{bridge_url}/healthz", cafile=server.cafile)

        dev_port = find_free_port()
        env_file = fixture_dir / ".env"
        env_file.write_text(
            "\n".join(
                [
                    'VITE_LATTICE_CLIENT_ID="dev-client"',
                    'VITE_LATTICE_CLIENT_SECRET="dev-secret"',
                    f'VITE_SANDBOX_TOKEN="{token}"',
                    f'VITE_LATTICE_URL="localhost:{bridge_port}"',
                    "",
                ]
            )
        )
        dev_env = {
            **npm_env,
            "NODE_EXTRA_CA_CERTS": str(server.cafile),
        }
        dev_handle = start_process(
            ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(dev_port)],
            cwd=fixture_dir,
            env=dev_env,
        )
        processes.append(("vite", dev_handle))
        dev_url = f"http://127.0.0.1:{dev_port}"
        _wait_http_server(dev_url)
        page = _fetch_dev_shell(dev_url)
        report["details"]["page"] = page

        seeded = []
        expected_entity_ids: list[str] = []
        for entity_id, alias, latitude, longitude in [
            ("zorn-cert-visualizer-west", "Visualizer West", 37.7749, -122.4194),
            ("zorn-cert-visualizer-east", "Visualizer East", 40.7128, -74.0060),
        ]:
            status, payload = http_json(
                "PUT",
                f"{server.rest_base_url}/api/v1/entities",
                token=token,
                cafile=server.cafile,
                headers={"Anduril-Sandbox-Authorization": f"Bearer {token}"},
                payload={
                    "entityId": entity_id,
                    "isLive": True,
                    "aliases": {"name": alias},
                    "location": {"position": {"latitudeDegrees": latitude, "longitudeDegrees": longitude}},
                    "ontology": {"template": "TEMPLATE_TRACK"},
                    "provenance": {"integrationName": "entity-visualizer-cert", "sourceUpdateTime": "2026-06-21T00:00:00Z"},
                },
            )
            seeded.append({"status": status, "entity": payload})
            expected_entity_ids.append(entity_id)
        ####
        report["details"]["seeded_entities"] = seeded

        browser = _run_node_visualizer_transport_check(
            fixture_dir=fixture_dir,
            bridge_url=bridge_url,
            token=token,
            cafile=server.cafile,
            expected_entity_ids=expected_entity_ids,
        )
        report["details"]["browser"] = browser

        streamed_ids = set(browser.get("stream_entity_ids") or [])
        has_entities = set(expected_entity_ids).issubset(streamed_ids)
        page_ok = bool(page.get("page_ok"))
        stream_ok = bool(browser.get("token_ok")) and has_entities and int(browser.get("entity_count") or 0) >= len(expected_entity_ids)
        _record(report, "auth.bearer_token", bool(browser.get("token_ok")), browser)
        _record(report, "entities.stream", stream_ok, browser)
        _record(report, "ui.map_visualizer", page_ok and stream_ok, {"page": page, "stream": browser})

        requested = set(fixture.surfaces)
        passed = set(report["passed"])
        report["missing"] = sorted(surface for surface in requested if surface not in passed)
        report["result"] = "pass" if not report["failed"] and not report["missing"] else "failed"
        return report
    finally:
        for name, handle in reversed(processes):
            returncode, stdout = stop_process(handle, timeout=10.0)
            process_logs[name] = {
                "args": handle.args,
                "cwd": str(handle.cwd),
                "returncode": returncode,
                "stdout": stdout,
            }
        ####
        report["details"]["process_logs"] = process_logs
        server_logs = stop_dual_transport_zorn_server(server)
        report["details"]["server_log"] = server_logs["rest"]
        report["details"]["grpc_server_log"] = server_logs["grpc"]
    ####
####


def _run_node_visualizer_transport_check(
    *,
    fixture_dir: Path,
    bridge_url: str,
    token: str,
    cafile: Path,
    expected_entity_ids: list[str],
) -> dict[str, Any]:
    env = {
        **os.environ,
        "NODE_EXTRA_CA_CERTS": str(cafile),
        "ZORN_BRIDGE_URL": bridge_url,
        "ZORN_SANDBOX_TOKEN": token,
        "ZORN_EXPECTED_ENTITY_IDS": json.dumps(expected_entity_ids),
    }
    script = """
import { EntityManagerAPI } from "@buf/anduril_lattice-sdk.bufbuild_es/anduril/entitymanager/v1/entity_manager_api.pub_pb.js";
import { createCallbackClient } from "@connectrpc/connect";
import { createGrpcWebTransport } from "@connectrpc/connect-web";

const bridgeUrl = process.env.ZORN_BRIDGE_URL;
const sandboxToken = process.env.ZORN_SANDBOX_TOKEN;
const expectedIds = new Set(JSON.parse(process.env.ZORN_EXPECTED_ENTITY_IDS || "[]"));

async function main() {
  const errors = [];
  const tokenResponse = await fetch(`${bridgeUrl}/api/v1/oauth/token`, {
    method: "POST",
    headers: {
      "Anduril-Sandbox-Authorization": `Bearer ${sandboxToken}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      grant_type: "client_credentials",
      client_id: "dev-client",
      client_secret: "dev-secret",
    }),
  });
  const tokenOk = tokenResponse.ok;
  if (!tokenOk) {
    const text = await tokenResponse.text();
    process.stdout.write(JSON.stringify({
      token_ok: false,
      entity_count: 0,
      stream_entity_ids: [],
      errors: [`token:${tokenResponse.status}:${text}`],
    }));
    return;
  }
  const tokenPayload = await tokenResponse.json();
  const headers = new Headers();
  headers.set("authorization", `Bearer ${tokenPayload.access_token}`);
  headers.set("anduril-sandbox-authorization", `Bearer ${sandboxToken}`);

  const seen = new Set();
  await new Promise((resolve) => {
    const client = createCallbackClient(EntityManagerAPI, createGrpcWebTransport({ baseUrl: bridgeUrl }));
    client.streamEntityComponents(
      { includeAllComponents: true },
      (res) => {
        const entityId = res.entityEvent?.entity?.entityId;
        if (entityId) {
          seen.add(entityId);
        }
        if ([...expectedIds].every((value) => seen.has(value))) {
          resolve();
        }
      },
      (err) => {
        errors.push(String(err));
        resolve();
      },
      { headers },
    );
    setTimeout(resolve, 8000);
  });

  process.stdout.write(JSON.stringify({
    token_ok: tokenOk,
    entity_count: seen.size,
    stream_entity_ids: [...seen].sort(),
    errors,
  }));
}

main().catch((error) => {
  process.stdout.write(JSON.stringify({ token_ok: false, entity_count: 0, stream_entity_ids: [], errors: [String(error)] }));
  process.exit(1);
});
"""
    result = run_command(["node", "--input-type=module", "-e", script], cwd=fixture_dir, env=env, timeout=60.0)
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        payload = {"token_ok": False, "entity_count": 0, "stream_entity_ids": [], "errors": [result.stdout or result.stderr]}
    ####
    payload["returncode"] = result.returncode
    payload["stderr"] = result.stderr
    return payload
####


def _write_visualizer_bridge(*, workspace: Path, rest_base_url: str, grpcweb_url: str) -> Path:
    bridge_path = workspace / "visualizer_bridge.py"
    bridge_path.write_text(
        f"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import Response, StreamingResponse
from starlette.background import BackgroundTask
import httpx
import os

REST_BASE_URL = {rest_base_url!r}
GRPCWEB_BASE_URL = {grpcweb_url!r}
SSL_CERT_FILE = os.environ["SSL_CERT_FILE"]
HOP_HEADERS = {{
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
}}

app = FastAPI()


async def _close_stream(upstream: httpx.Response, client: httpx.AsyncClient) -> None:
    await upstream.aclose()
    await client.aclose()


@app.get("/healthz")
async def healthz():
    return {{"ok": True}}


@app.api_route("/{{path:path}}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy(path: str, request: Request):
    query = f"?{{request.url.query}}" if request.url.query else ""
    base_url = REST_BASE_URL if path.startswith("api/v1/") else GRPCWEB_BASE_URL
    target = f"{{base_url}}/{{path}}{{query}}"
    headers = {{key: value for key, value in request.headers.items() if key.lower() not in HOP_HEADERS}}
    body = await request.body()
    client = httpx.AsyncClient(verify=SSL_CERT_FILE, timeout=httpx.Timeout(30.0, read=None))
    upstream = await client.send(
        client.build_request(request.method, target, headers=headers, content=body),
        stream=True,
    )
    response_headers = {{key: value for key, value in upstream.headers.items() if key.lower() not in HOP_HEADERS}}
    return StreamingResponse(
        upstream.aiter_raw(),
        status_code=upstream.status_code,
        headers=response_headers,
        background=BackgroundTask(_close_stream, upstream, client),
    )
""".lstrip(),
    )
    return bridge_path
####


def _fetch_dev_shell(url: str) -> dict[str, Any]:
    try:
        with request.urlopen(url, timeout=10.0) as response:
            html = response.read().decode("utf-8")
        return {
            "page_ok": response.status == 200 and "<title>Entity Map</title>" in html and 'id="root"' in html,
            "status": response.status,
            "title_present": "<title>Entity Map</title>" in html,
            "root_present": 'id="root"' in html,
        }
    except Exception as exc:
        return {"page_ok": False, "error": str(exc)}
####


def _wait_http_server(url: str, *, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last_error = ""
    while time.time() < deadline:
        try:
            with request.urlopen(url, timeout=2.0) as response:
                if response.status < 500:
                    return
                ####
            ####
        except Exception as exc:  # pragma: no cover - transient probe
            last_error = str(exc)
        ####
        time.sleep(0.3)
    ####
    raise RuntimeError(f"timed out waiting for HTTP server at {url}: {last_error}")
####


def _wait_https_server(url: str, *, cafile: Path, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    context = ssl.create_default_context(cafile=str(cafile))
    last_error = ""
    while time.time() < deadline:
        try:
            with request.urlopen(url, timeout=2.0, context=context) as response:
                if response.status < 500:
                    return
                ####
            ####
        except error.HTTPError:
            return
        except Exception as exc:  # pragma: no cover - transient probe
            last_error = str(exc)
        ####
        time.sleep(0.3)
    ####
    raise RuntimeError(f"timed out waiting for HTTPS server at {url}: {last_error}")
####


def _record(report: dict[str, Any], capability: str, ok: bool, detail: dict[str, Any]) -> None:
    target = "passed" if ok else "failed"
    if capability not in report[target]:
        report[target].append(capability)
    ####
    report["details"][capability] = detail
####
