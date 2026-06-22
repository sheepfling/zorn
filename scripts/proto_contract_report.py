from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
####

from typing import Any  # noqa: E402

from zorn.grpc_api.contract import (  # noqa: E402
    GrpcContractMismatch,
    assert_lattice_grpc_contract,
    build_lattice_grpc_contract_report,
)
from zorn.grpc_api.proto_modules import (  # noqa: E402
    MissingLatticeProtoDependency,
    assert_official_package_versions,
    load_lattice_proto_modules,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect the official Buf-generated Lattice gRPC proto contract.")
    parser.add_argument("--assert", dest="assert_contract", action="store_true", help="exit non-zero when package pins or service descriptors drift")
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON")
    parser.add_argument("--output", type=Path, default=None, help="optional path to write the JSON report")
    return parser
####


def main() -> None:
    args = build_parser().parse_args()
    try:
        if args.assert_contract:
            assert_official_package_versions()
        ####
        modules = load_lattice_proto_modules()
        if args.assert_contract:
            assert_lattice_grpc_contract(modules)
        ####
        report = build_lattice_grpc_contract_report(modules)
    except (MissingLatticeProtoDependency, GrpcContractMismatch) as exc:
        report = {"ok": False, "error": str(exc)}
        _emit(report, args)
        raise SystemExit(1) from exc
    ####
    report["ok"] = not report.get("mismatches")
    _emit(report, args)
####


def _emit(report: dict[str, Any], args: argparse.Namespace) -> None:
    text = json.dumps(report, indent=2 if args.pretty else None, sort_keys=True)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n")
    ####
    print(text)
####


if __name__ == "__main__":
    main()
####
