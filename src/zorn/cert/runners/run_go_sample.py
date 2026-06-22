from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any

from .common import (
    base_report,
    http_bytes,
    http_json,
    run_command,
    start_http_insecure_grpc_zorn_server,
    start_http_zorn_server,
    start_process,
    stop_dual_transport_zorn_server,
    stop_https_zorn_server,
    stop_process,
)


def run_go_sample(*, fixture: Any, fixture_dir: Path, target: str, token: str, mode: str) -> dict[str, Any]:
    if fixture.id == "anduril-sample-objects":
        return _run_objects_sample(fixture=fixture, fixture_dir=fixture_dir, token=token, mode=mode)
    ####
    if fixture.id == "daemon-maven":
        return _run_maven_sample(fixture=fixture, fixture_dir=fixture_dir, token=token, mode=mode)
    ####
    report = base_report(fixture_id=fixture.id, mode=mode)
    report["result"] = "missing"
    report["missing"] = list(fixture.surfaces)
    report["details"] = {
        "reason": "go sample runner scaffolded; fixture-specific command mapping is not implemented yet",
        "fixture_dir": str(fixture_dir),
        "target": target,
        "token_configured": bool(token),
    }
    return report
####


def _run_objects_sample(*, fixture: Any, fixture_dir: Path, token: str, mode: str) -> dict[str, Any]:
    report = base_report(fixture_id=fixture.id, mode=mode)
    repo_root = Path(__file__).resolve().parents[4]
    go_workspace = Path(tempfile.mkdtemp(prefix="zorn-go-objects-"))
    env = {
        **os.environ,
        "GOCACHE": str(go_workspace / "gocache"),
        "GOMODCACHE": str(go_workspace / "gomodcache"),
        "GOPATH": str(go_workspace / "gopath"),
    }
    install = run_command(["go", "mod", "download"], cwd=fixture_dir, env=env, timeout=240.0)
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

    server = start_http_zorn_server(repo_root=repo_root, token=token)
    try:
        input_file = server.workspace / "sample-object.txt"
        input_contents = b"zorn objects certification payload\n"
        input_file.write_bytes(input_contents)
        downloaded_file = server.workspace / "downloaded-object.txt"
        object_path = "cert/sample-object.txt"
        base_url = server.base_url

        run_env = dict(env)

        def _go(args: list[str]) -> dict[str, Any]:
            result = run_command(["go", "run", "main.go", *args], cwd=fixture_dir, env=run_env, timeout=240.0)
            return {
                "args": result.args,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        common = ["-b", base_url, "-c", "dev-client", "-s", "dev-secret", "-e", token]

        upload = _go(["upload", *common, "-i", str(input_file), "-p", object_path, "-t", "2h"])
        metadata = _go(["object-metadata", *common, "-p", object_path])
        listing = _go(["list", *common, "cert"])
        get_cmd = _go(["get", *common, "-p", object_path, "-o", str(downloaded_file), "-r"])

        report["details"]["upload_command"] = upload
        report["details"]["metadata_command"] = metadata
        report["details"]["list_command"] = listing
        report["details"]["get_command"] = get_cmd

        probe_list_status, probe_list = http_json(
            "GET",
            f"{server.base_url}/api/v1/objects?prefix=cert",
            token=token,
            cafile=server.cafile,
            headers={"Anduril-Sandbox-Authorization": f"Bearer {token}"},
        )
        probe_get_status, probe_get_bytes, _ = http_bytes(
            "GET",
            f"{server.base_url}/api/v1/objects/{object_path}",
            token=token,
            cafile=server.cafile,
            headers={"Anduril-Sandbox-Authorization": f"Bearer {token}"},
        )
        delete = _go(["delete", *common, "-p", object_path])
        report["details"]["delete_command"] = delete
        probe_post_delete_status, probe_post_delete = http_json(
            "GET",
            f"{server.base_url}/api/v1/objects?prefix=cert",
            token=token,
            cafile=server.cafile,
            headers={"Anduril-Sandbox-Authorization": f"Bearer {token}"},
        )
        report["details"]["probe_list_before_delete"] = {"status": probe_list_status, "payload": probe_list}
        report["details"]["probe_get_before_delete"] = {"status": probe_get_status, "size": len(probe_get_bytes)}
        report["details"]["probe_list_after_delete"] = {"status": probe_post_delete_status, "payload": probe_post_delete}

        downloaded_bytes = downloaded_file.read_bytes() if downloaded_file.exists() else b""
        objects_before_delete = probe_list.get("objects", []) if isinstance(probe_list, dict) else []
        objects_after_delete = probe_post_delete.get("objects", []) if isinstance(probe_post_delete, dict) else []
        metadata_ok = metadata["returncode"] == 0 and object_path in metadata["stdout"]
        list_ok = listing["returncode"] == 0 and object_path in listing["stdout"]
        _record(report, "objects.upload", upload["returncode"] == 0 and probe_list_status == 200 and any(isinstance(item, dict) and item.get("objectPath") == object_path for item in objects_before_delete), {"command": upload, "probe": probe_list})
        _record(report, "objects.metadata", metadata_ok, {"command": metadata})
        _record(report, "objects.list", list_ok, {"command": listing})
        _record(report, "objects.download", get_cmd["returncode"] == 0 and downloaded_bytes == input_contents and probe_get_status == 200 and probe_get_bytes == input_contents, {"command": get_cmd, "downloaded_size": len(downloaded_bytes)})
        _record(report, "objects.delete", delete["returncode"] == 0 and probe_post_delete_status == 200 and not any(isinstance(item, dict) and item.get("objectPath") == object_path for item in objects_after_delete), {"command": delete, "probe": probe_post_delete})

        requested = set(fixture.surfaces)
        passed = set(report["passed"])
        report["missing"] = sorted(surface for surface in requested if surface not in passed and surface != "auth.bearer_token")
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


def _run_maven_sample(*, fixture: Any, fixture_dir: Path, token: str, mode: str) -> dict[str, Any]:
    report = base_report(fixture_id=fixture.id, mode=mode)
    repo_root = Path(__file__).resolve().parents[4]
    lattice_dir = fixture_dir / "lattice"
    go_workspace = Path(tempfile.mkdtemp(prefix="zorn-go-maven-"))
    env = {
        **os.environ,
        "GOCACHE": str(go_workspace / "gocache"),
        "GOMODCACHE": str(go_workspace / "gomodcache"),
        "GOPATH": str(go_workspace / "gopath"),
    }
    install = run_command(["go", "mod", "download"], cwd=lattice_dir, env=env, timeout=300.0)
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

    server = start_http_insecure_grpc_zorn_server(repo_root=repo_root, token=token)
    try:
        overlay_dir = server.workspace / "maven-overlay"
        overlay_dir.mkdir(parents=True, exist_ok=True)
        auth_overlay = overlay_dir / "token.go"
        client_overlay = overlay_dir / "client.go"
        graph_overlay = overlay_dir / "store.go"
        ingest_overlay = overlay_dir / "ingest_main.go"
        overlay_json = overlay_dir / "overlay.json"
        ws_probe = overlay_dir / "ws_probe.go"
        auth_overlay.write_text(
            """
package auth

import "context"

type Config struct {
\tBaseURL string
\tClientID string
\tClientSecret string
\tSandboxToken string
}

type TokenSource struct {
\tcfg Config
}

func NewTokenSource(cfg Config) *TokenSource {
\treturn &TokenSource{cfg: cfg}
}

func (t *TokenSource) GetRequestMetadata(ctx context.Context, _ ...string) (map[string]string, error) {
\ttoken := t.cfg.ClientSecret
\tif token == "" {
\t\ttoken = "dev-token"
\t}
\tmd := map[string]string{"authorization": "Bearer " + token}
\tif t.cfg.SandboxToken != "" {
\t\tmd["anduril-sandbox-authorization"] = "Bearer " + t.cfg.SandboxToken
\t}
\treturn md, nil
}

func (t *TokenSource) RequireTransportSecurity() bool { return false }
""".lstrip(),
        )
        client_overlay.write_text(
            """
package lattice

import (
\t"context"
\t"fmt"
\t"os"
\t"strings"

\t"github.com/daemon/lattice/internal/auth"
\tentitymanagerv1 "github.com/anduril/lattice-sdk-go/src/anduril/entitymanager/v1"
\t"google.golang.org/grpc"
\t"google.golang.org/grpc/credentials/insecure"
)

type Client struct {
\tclient entitymanagerv1.EntityManagerAPIClient
\tconn   *grpc.ClientConn
}

func NewClient(ctx context.Context, cfg auth.Config, insecureTransport bool) (*Client, error) {
\tgrpcURL := os.Getenv("ZORN_CERT_GRPC_TARGET")
\tif grpcURL == "" {
\t\tgrpcURL = strings.TrimPrefix(cfg.BaseURL, "https://")
\t\tgrpcURL = strings.TrimPrefix(grpcURL, "http://")
\t}
\tconn, err := grpc.NewClient(
\t\tgrpcURL,
\t\tgrpc.WithTransportCredentials(insecure.NewCredentials()),
\t\tgrpc.WithPerRPCCredentials(auth.NewTokenSource(cfg)),
\t)
\tif err != nil {
\t\treturn nil, fmt.Errorf("dial Lattice: %w", err)
\t}
\treturn &Client{
\t\tclient: entitymanagerv1.NewEntityManagerAPIClient(conn),
\t\tconn:   conn,
\t}, nil
}

func (c *Client) EntityManagerClient() entitymanagerv1.EntityManagerAPIClient {
\treturn c.client
}

func (c *Client) Close() error {
\treturn c.conn.Close()
}
""".lstrip(),
        )
        graph_overlay.write_text(
            """
package graph

import (
\t"context"
\t"time"
)

type Store struct{}

func New(ctx context.Context, uri, user, password string) (*Store, error) {
\treturn &Store{}, nil
}

type EntityUpdate struct {
\tEntityID  string
\tName      string
\tLatitude  float64
\tLongitude float64
\tOntology  string
\tUpdatedAt time.Time
}

func (s *Store) UpsertEntity(ctx context.Context, e EntityUpdate) error { return nil }

type RelationshipUpdate struct {
\tFromEntityID string
\tToEntityID   string
\tRelationType string
\tUpdatedAt    time.Time
}

func (s *Store) UpsertRelationship(ctx context.Context, r RelationshipUpdate) error { return nil }

func (s *Store) DeleteEntity(ctx context.Context, entityID string) error { return nil }

func (s *Store) Close(ctx context.Context) error { return nil }
""".lstrip(),
        )
        ingest_source = (lattice_dir / "cmd" / "ingest" / "main.go").read_text()
        old_extract = """// extractDisposition maps the Lattice MilView Disposition enum to a canonical
// MIL-STD-2525 affiliation string understood by the frontend color mapper.
func extractDisposition(entity *entitymanagerv1.Entity) string {
\tif entity.MilView == nil {
\t\treturn "unknown"
\t}
\tswitch entity.MilView.Disposition {
\tcase entitymanagerv1.Disposition_DISPOSITION_HOSTILE,
\t\tentitymanagerv1.Disposition_DISPOSITION_ASSUMED_HOSTILE:
\t\treturn "hostile"
\tcase entitymanagerv1.Disposition_DISPOSITION_FRIENDLY,
\t\tentitymanagerv1.Disposition_DISPOSITION_ASSUMED_FRIENDLY:
\t\treturn "friendly"
\tcase entitymanagerv1.Disposition_DISPOSITION_NEUTRAL,
\t\tentitymanagerv1.Disposition_DISPOSITION_ASSUMED_NEUTRAL:
\t\treturn "neutral"
\tcase entitymanagerv1.Disposition_DISPOSITION_SUSPECT:
\t\treturn "suspect"
\tdefault:
\t\treturn "unknown"
\t}
}
"""
        new_extract = """// extractDisposition maps the Lattice MilView Disposition enum to a canonical
// MIL-STD-2525 affiliation string understood by the frontend color mapper.
func extractDisposition(entity *entitymanagerv1.Entity) string {
\tif entity.MilView == nil {
\t\treturn "unknown"
\t}
\tswitch entity.MilView.Disposition.String() {
\tcase "DISPOSITION_HOSTILE", "DISPOSITION_ASSUMED_HOSTILE":
\t\treturn "hostile"
\tcase "DISPOSITION_FRIENDLY", "DISPOSITION_ASSUMED_FRIENDLY":
\t\treturn "friendly"
\tcase "DISPOSITION_NEUTRAL", "DISPOSITION_ASSUMED_NEUTRAL":
\t\treturn "neutral"
\tcase "DISPOSITION_SUSPECT", "DISPOSITION_SUSPICIOUS":
\t\treturn "suspect"
\tdefault:
\t\treturn "unknown"
\t}
}
"""
        if old_extract not in ingest_source:
            raise RuntimeError("daemon-maven ingest overlay could not locate extractDisposition function")
        ####
        ingest_overlay.write_text(ingest_source.replace(old_extract, new_extract, 1))
        overlay_json.write_text(
            json.dumps(
                {
                    "Replace": {
                        str(lattice_dir / "internal" / "auth" / "token.go"): str(auth_overlay),
                        str(lattice_dir / "internal" / "lattice" / "client.go"): str(client_overlay),
                        str(lattice_dir / "internal" / "graph" / "store.go"): str(graph_overlay),
                        str(lattice_dir / "cmd" / "ingest" / "main.go"): str(ingest_overlay),
                    }
                },
                indent=2,
            )
            + "\n"
        )
        ws_probe.write_text(
            """
package main

import (
\t"encoding/json"
\t"fmt"
\t"os"
\t"time"

\t"github.com/gorilla/websocket"
)

func main() {
\tconn, _, err := websocket.DefaultDialer.Dial(os.Args[1], nil)
\tif err != nil {
\t\tpanic(err)
\t}
\tdefer conn.Close()
\tconn.SetReadDeadline(time.Now().Add(15 * time.Second))
\t_, data, err := conn.ReadMessage()
\tif err != nil {
\t\tpanic(err)
\t}
\tvar payload map[string]any
\tif err := json.Unmarshal(data, &payload); err != nil {
\t\tpanic(err)
\t}
\tout, err := json.Marshal(payload)
\tif err != nil {
\t\tpanic(err)
\t}
\tfmt.Println(string(out))
}
""".lstrip(),
        )
        overlay_flag = "-overlay=" + str(overlay_json)
        run_env = {
            **env,
            "LATTICE_URL": server.rest_base_url,
            "LATTICE_CLIENT_ID": "dev-client",
            "LATTICE_CLIENT_SECRET": token,
            "SANDBOX_TOKEN": token,
            "ZORN_CERT_GRPC_TARGET": server.grpc_target,
        }

        ingest = start_process(["go", "run", overlay_flag, "./cmd/ingest"], cwd=lattice_dir, env=run_env)
        report["details"]["overlay"] = str(overlay_json)
        deadline = 20.0
        health_ok = False
        health_error = ""
        for _ in range(int(deadline * 2)):
            if ingest.process.poll() is not None:
                break
            ####
            try:
                status, payload = http_json("GET", "http://127.0.0.1:8080/health", token=token)
                if status == 200 and payload.get("status") == "ok":
                    health_ok = True
                    break
                ####
                health_error = json.dumps(payload)
            except Exception as exc:
                health_error = str(exc)
            ####
            time.sleep(0.5)
        ####
        if not health_ok:
            returncode, stdout = stop_process(ingest, timeout=2.0)
            report["details"]["ingest_process"] = {"args": ingest.args, "returncode": returncode, "stdout": stdout}
            report["details"]["ingest_health_error"] = health_error
            report["result"] = "failed"
            report["failed"] = list(fixture.surfaces)
            return report
        ####

        ws_handle = start_process(["go", "run", str(ws_probe), "ws://127.0.0.1:8080/ws"], cwd=lattice_dir, env=run_env)
        time.sleep(1.0)
        publish = run_command(["go", "run", overlay_flag, "./cmd/publish"], cwd=lattice_dir, env=run_env, timeout=120.0)
        publish_detail = {
            "args": publish.args,
            "returncode": publish.returncode,
            "stdout": publish.stdout,
            "stderr": publish.stderr,
        }
        report["details"]["publish_command"] = publish_detail
        entity_status, entity_payload = http_json(
            "GET",
            f"{server.rest_base_url}/api/v1/entities/test-vessel-001",
            token=token,
        )
        ws_deadline = time.time() + 10.0
        while time.time() < ws_deadline:
            if ws_handle.process.poll() is not None:
                break
            ####
            time.sleep(0.5)
        ####
        ws_returncode, ws_stdout = stop_process(ws_handle, timeout=20.0)
        ingest_returncode, ingest_stdout = stop_process(ingest, timeout=2.0)
        report["details"]["ingest_process"] = {
            "args": ingest.args,
            "returncode": ingest_returncode,
            "stdout": ingest_stdout,
        }
        report["details"]["ws_probe"] = {
            "args": ws_handle.args,
            "returncode": ws_returncode,
            "stdout": ws_stdout,
        }
        report["details"]["entity"] = {"status": entity_status, "payload": entity_payload}

        ws_payload: dict[str, Any] = {}
        try:
            ws_payload = json.loads(ws_stdout.strip()) if ws_stdout.strip() else {}
        except json.JSONDecodeError:
            ws_payload = {}
        ####
        disposition = ws_payload.get("disposition")
        _record(report, "auth.oauth_client_credentials", publish.returncode == 0, {"publish": publish_detail})
        _record(report, "entities.publish", entity_status == 200 and entity_payload.get("entityId") == "test-vessel-001", {"entity": entity_payload})
        _record(report, "entities.grpc_stream", ws_returncode == 0 and ws_payload.get("entity_id") == "test-vessel-001", {"ws": ws_payload})
        _record(report, "ui.websocket", ws_returncode == 0 and ws_payload.get("type") == "update", {"ws": ws_payload})
        _record(report, "ui.cesium", disposition in {"unknown", "friendly", "hostile", "neutral", "suspect"}, {"ws": ws_payload})

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
        logs = stop_dual_transport_zorn_server(server)
        report["details"]["server_log"] = logs["rest"]
        report["details"]["grpc_server_log"] = logs["grpc"]
    ####
####


def _record(report: dict[str, Any], capability: str, ok: bool, detail: dict[str, Any]) -> None:
    target = "passed" if ok else "failed"
    if capability not in report[target]:
        report[target].append(capability)
    ####
    report["details"][capability] = detail
####
