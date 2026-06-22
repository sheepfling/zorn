from __future__ import annotations

from pathlib import Path

import yaml

from zorn.cert.grpc_wire import build_golden_grpc_requests, request_message_type
from zorn.grpc_api.proto_modules import load_lattice_proto_modules


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "grpc"


def test_golden_grpc_wire_fixtures_exist_and_match_builders() -> None:
    proto_modules = load_lattice_proto_modules()
    expected = build_golden_grpc_requests(proto_modules)
    manifest = yaml.safe_load((FIXTURE_DIR / "manifest.yaml").read_text(encoding="utf-8"))

    for item in manifest["fixtures"]:
        path = item["path"]
        fixture_path = FIXTURE_DIR / path
        assert fixture_path.exists(), path
        fixture_bytes = fixture_path.read_bytes()
        assert fixture_bytes == expected[path].request.SerializeToString(), path
    ####


def test_golden_grpc_wire_fixtures_parse_with_official_request_types() -> None:
    proto_modules = load_lattice_proto_modules()
    manifest = yaml.safe_load((FIXTURE_DIR / "manifest.yaml").read_text(encoding="utf-8"))

    for item in manifest["fixtures"]:
        request_type = request_message_type(proto_modules, item["rpc"])
        message = request_type()
        fixture_bytes = (FIXTURE_DIR / item["path"]).read_bytes()
        message.ParseFromString(fixture_bytes)
        assert message.SerializeToString() == fixture_bytes
    ####
