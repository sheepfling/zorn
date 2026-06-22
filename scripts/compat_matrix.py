from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


CHECKS: tuple[tuple[str, list[str]], ...] = (
    ("pytest", [sys.executable, "-m", "pytest"]),
    ("ruff", [str(ROOT / ".venv" / "bin" / "ruff"), "check", "."]),
    ("mypy", [str(ROOT / ".venv" / "bin" / "mypy"), "src", "tests", "scripts"]),
    (
        "proto-contract",
        [sys.executable, "scripts/proto_contract_report.py", "--assert", "--pretty"],
    ),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Zorn compatibility checks and emit a JSON report.")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "compat_matrix.json")
    return parser
####


def main() -> int:
    args = build_parser().parse_args()
    results: list[dict[str, Any]] = []
    overall_status = 0
    for name, command in CHECKS:
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            overall_status = result.returncode
        ####
        results.append(
            {
                "name": name,
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
    ####
    report = {"ok": overall_status == 0, "checks": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"ok": report["ok"], "output": str(args.output)}, sort_keys=True))
    return overall_status
####


if __name__ == "__main__":
    raise SystemExit(main())
