from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "cert" / "lattice" / "reports"


def test_alpha1_cert_reports_have_only_documented_environment_blocker() -> None:
    non_pass: dict[str, dict[str, object]] = {}
    for report_path in sorted(REPORTS.glob("*.json")):
        report = json.loads(report_path.read_text())
        result = report.get("result")
        if result != "pass":
            non_pass[report_path.stem] = report

    assert set(non_pass) == {"sdk-cpp-grpc-smoke"}

    cpp_blocker = non_pass["sdk-cpp-grpc-smoke"]
    assert cpp_blocker["result"] == "blocked"
    details = cpp_blocker.get("details")
    assert isinstance(details, dict)
    assert details.get("reason") == "system gRPC/protobuf C++ development packages are required for sdk-cpp-grpc-smoke"
    assert details.get("grpc_config") is None
    assert details.get("protobuf_config") is None


def test_alpha1_closeout_checklist_documents_allowed_blocker_and_defers() -> None:
    checklist = (ROOT / "docs" / "design" / "alpha1-closeout-checklist.md").read_text()

    assert "sdk-cpp-grpc-smoke" in checklist
    assert "refresh-token support" in checklist
    assert "richer vendor-like OAuth policy" in checklist
    assert "no `zorn.adapters` namespace in the importable package" in checklist
