from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import textwrap

import pytest
from google.protobuf.descriptor_pb2 import FileDescriptorProto

from zorn.cert.runners.common import start_http_zorn_server, stop_https_zorn_server
from zorn.grpc_api.proto_modules import load_lattice_proto_modules


ROOT = Path(__file__).resolve().parents[2]
GO_SDK_VERSION = "v4.14.0"


@pytest.mark.skipif(shutil.which("go") is None, reason="Go toolchain is not installed")
def test_official_go_sdk_entity_and_task_calls(tmp_path: Path) -> None:
    server = start_http_zorn_server(repo_root=ROOT, token="dev-token")
    try:
        fixture_dir = tmp_path / "go-sdk-smoke"
        fixture_dir.mkdir()
        (fixture_dir / "go.mod").write_text(
            textwrap.dedent(
                f"""
                module zorn-go-sdk-smoke

                go 1.23.0

                require github.com/anduril/lattice-sdk-go/v4 {GO_SDK_VERSION}
                """
            ).strip()
            + "\n"
        )
        (fixture_dir / "main.go").write_text(
            textwrap.dedent(
                """
                package main

                import (
                  "context"
                  "encoding/json"
                  "net/http"
                  "os"

                  Lattice "github.com/anduril/lattice-sdk-go/v4"
                  "github.com/anduril/lattice-sdk-go/v4/client"
                  "github.com/anduril/lattice-sdk-go/v4/option"
                )

                type result struct {
                  EntityID         string `json:"entity_id"`
                  TaskID           string `json:"task_id"`
                  ListenHasExecute bool   `json:"listen_has_execute"`
                }

                func strValue(value *string) string {
                  if value == nil {
                    return ""
                  }
                  return *value
                }

                func main() {
                  token := os.Getenv("ZORN_TOKEN")
                  baseURL := os.Getenv("ZORN_BASE_URL")
                  sandbox := http.Header{}
                  sandbox.Add("anduril-sandbox-authorization", "Bearer "+token)

                  cli := client.NewClient(
                    option.WithBaseURL(baseURL),
                    option.WithClientCredentials("dev-client", "dev-secret"),
                    option.WithHTTPHeader(sandbox),
                  )

                  entityID := "compat-go-sdk-entity"
                  taskID := "compat-go-sdk-task"
                  agentID := "compat-go-sdk-agent"

                  entity, err := cli.Entities.PublishEntity(
                    context.Background(),
                    &Lattice.Entity{
                      EntityID:    Lattice.String(entityID),
                      Description: Lattice.String("official Go SDK entity"),
                      IsLive:      Lattice.Bool(true),
                      NoExpiry:    Lattice.Bool(true),
                    },
                  )
                  if err != nil {
                    panic(err)
                  }

                  fetched, err := cli.Entities.GetEntity(
                    context.Background(),
                    &Lattice.GetEntityRequest{EntityID: entityID},
                  )
                  if err != nil {
                    panic(err)
                  }

                  task, err := cli.Tasks.CreateTask(
                    context.Background(),
                    &Lattice.TaskCreation{
                      TaskID:      Lattice.String(taskID),
                      DisplayName: Lattice.String("Go SDK compatibility task"),
                      Description: Lattice.String("created by go sdk smoke"),
                      Relations: &Lattice.Relations{
                        Assignee: &Lattice.Principal{
                          System: &Lattice.System{EntityID: Lattice.String(agentID)},
                        },
                      },
                    },
                  )
                  if err != nil {
                    panic(err)
                  }

                  listen, err := cli.Tasks.ListenAsAgent(
                    context.Background(),
                    &Lattice.AgentListener{
                      AgentSelector: &Lattice.EntityIDsSelector{EntityIDs: []string{agentID}},
                    },
                  )
                  if err != nil {
                    panic(err)
                      }

                      response := result{
                        EntityID: strValue(entity.GetEntityID()),
                        TaskID:   strValue(task.GetVersion().GetTaskID()),
                        ListenHasExecute: listen.GetExecuteRequest() != nil &&
                          listen.GetExecuteRequest().GetTask() != nil &&
                          listen.GetExecuteRequest().GetTask().GetVersion() != nil &&
                      listen.GetExecuteRequest().GetTask().GetVersion().GetTaskID() != nil &&
                      *listen.GetExecuteRequest().GetTask().GetVersion().GetTaskID() == taskID &&
                      fetched.GetEntityID() != nil &&
                      *fetched.GetEntityID() == entityID,
                  }

                  if err := json.NewEncoder(os.Stdout).Encode(response); err != nil {
                    panic(err)
                  }
                }
                """
            ).strip()
            + "\n"
        )

        env = {
            **os.environ,
            "GOCACHE": str(tmp_path / "gocache"),
            "GOMODCACHE": str(tmp_path / "gomodcache"),
            "GOPATH": str(tmp_path / "gopath"),
            "ZORN_BASE_URL": server.base_url,
            "ZORN_TOKEN": "dev-token",
        }
        subprocess.run(["go", "mod", "tidy"], cwd=fixture_dir, env=env, check=True, capture_output=True, text=True)
        run = subprocess.run(["go", "run", "."], cwd=fixture_dir, env=env, check=True, capture_output=True, text=True)
        payload = json.loads(run.stdout)
    finally:
        stop_https_zorn_server(server)
    ####

    assert payload["entity_id"] == "compat-go-sdk-entity"
    assert payload["task_id"] == "compat-go-sdk-task"
    assert payload["listen_has_execute"] is True


def test_public_proto_go_package_is_private_for_generated_grpc_clients() -> None:
    proto_modules = load_lattice_proto_modules()
    for module in (proto_modules.entity_api, proto_modules.task_api):
        descriptor = FileDescriptorProto.FromString(module.DESCRIPTOR.serialized_pb)
        assert descriptor.options.go_package.startswith("ghe.anduril.dev/")
