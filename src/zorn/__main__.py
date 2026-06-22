from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapters.dis import replay_entity_state_jsonl_with_public_api
from .replay import UrlLibPublicApiTransport, replay_api_log


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zorn", description="Run Zorn local surrogate commands.")
    subparsers = parser.add_subparsers(dest="command")

    replay_parser = subparsers.add_parser("replay", help="Replay fixtures through Zorn's existing public API.")
    replay_subparsers = replay_parser.add_subparsers(dest="replay_command", required=True)

    api_parser = replay_subparsers.add_parser("api", help="Replay Entity/Task/Object API JSONL operations.")
    api_parser.add_argument("fixture", type=Path)
    api_parser.add_argument("--target", default="http://127.0.0.1:8080")
    api_parser.add_argument("--token", default=None)
    api_parser.add_argument("--report", type=Path)
    api_parser.add_argument("--json", action="store_true", dest="as_json")

    dis_parser = replay_subparsers.add_parser("dis", help="Replay DIS Entity State JSONL fixtures.")
    dis_parser.add_argument("fixture", type=Path)
    dis_parser.add_argument("--target", default="http://127.0.0.1:8080")
    dis_parser.add_argument("--token", default=None)
    dis_parser.add_argument("--report", type=Path)
    dis_parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command is None:
        repo_root = Path(__file__).resolve().parents[2]
        print("Zorn surrogate workspace is ready.")
        print(f"repo_root={repo_root}")
        print("next_step=zorn replay dis tests/fixtures/dis/entity_state_replay.jsonl --target http://127.0.0.1:8080")
        return 0
    ####
    if args.command == "replay" and args.replay_command == "dis":
        transport = UrlLibPublicApiTransport(args.target, token=args.token)
        result = replay_entity_state_jsonl_with_public_api(args.fixture, transport)
        report = result.to_report()
        _emit_report(report, args.report, args.as_json)
        return 0 if report["result"] == "passed" else 1
    ####
    if args.command == "replay" and args.replay_command == "api":
        transport = UrlLibPublicApiTransport(args.target, token=args.token)
        api_result = replay_api_log(args.fixture, transport)
        report = api_result.to_report()
        _emit_report(report, args.report, args.as_json)
        return 0 if report["result"] == "passed" else 1
    ####
    parser.error("unsupported command")
    return 2


def _emit_report(report: dict[str, object], report_path: Path | None, as_json: bool) -> None:
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    ####
    if as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    ####
    print(f"fixture: {report['fixture']}")
    print(f"result: {report['result']}")
    if "entities" in report and isinstance(report["entities"], list):
        print(f"entities: {len(report['entities'])}")
    ####
    if "events" in report and isinstance(report["events"], list):
        print(f"events: {len(report['events'])}")
    ####
    if "operations" in report and isinstance(report["operations"], list):
        print(f"operations: {len(report['operations'])}")
    ####
    if report_path:
        print(f"report: {report_path}")
    ####


if __name__ == "__main__":
    raise SystemExit(main())
