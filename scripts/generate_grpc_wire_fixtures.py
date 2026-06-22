from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
####

from zorn.cert.grpc_wire import build_golden_grpc_requests  # noqa: E402
from zorn.grpc_api.proto_modules import load_lattice_proto_modules  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate pinned golden gRPC wire fixtures from official Buf-generated Python packages.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT_DIR / "tests" / "fixtures" / "grpc",
    )
    return parser
####


def main() -> int:
    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    proto_modules = load_lattice_proto_modules()
    fixtures = build_golden_grpc_requests(proto_modules)
    for path, fixture in fixtures.items():
        (args.output_dir / path).write_bytes(fixture.request.SerializeToString())
        print(path)
    ####
    return 0
####


if __name__ == "__main__":
    raise SystemExit(main())
