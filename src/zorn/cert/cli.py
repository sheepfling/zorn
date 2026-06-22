from __future__ import annotations

import argparse
import json
from pathlib import Path

from .harness import (
    clone_all_fixtures,
    clone_fixture,
    format_shell_command,
    fixture_by_id,
    inspect_fixture,
    install_fixture,
    load_contract,
    load_fixtures,
    reports_summary,
    run_fixture,
    validate_contracts,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zorn-cert", description="Run Zorn Lattice certification fixtures.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List pinned certification fixtures.")
    subparsers.add_parser("domains", help="List top-level Zorn capability domains.")
    subparsers.add_parser("coverage", help="Print the capability coverage matrix.")
    subparsers.add_parser("levels", help="List certification levels.")
    subparsers.add_parser("artifacts", help="List required self-checking run artifacts.")
    subparsers.add_parser("validate-contracts", help="Validate capability contract references.")

    clone_parser = subparsers.add_parser("clone", help="Clone a pinned fixture.")
    clone_parser.add_argument("fixture_id", nargs="?")
    clone_parser.add_argument("--all", action="store_true")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect a fixture workspace.")
    inspect_parser.add_argument("fixture_id")
    inspect_parser.add_argument("--json", action="store_true", dest="as_json")

    install_parser = subparsers.add_parser("install", help="Install fixture dependencies in its clone workspace.")
    install_parser.add_argument("fixture_id")
    install_parser.add_argument("--json", action="store_true", dest="as_json")

    run_parser = subparsers.add_parser("run", help="Run a certification fixture.")
    run_parser.add_argument("fixture_id")
    run_parser.add_argument("--target", default="http://localhost:8080")
    run_parser.add_argument("--token", default="dev-token")
    run_parser.add_argument("--mode", choices=("strict", "stress"), default="strict")

    report_parser = subparsers.add_parser("report", help="Summarize certification reports.")
    report_parser.add_argument("--json", action="store_true", dest="as_json")
    return parser
####


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    fixtures = load_fixtures(root)

    if args.command == "list":
        for fixture in fixtures:
            print(f"{fixture.id}\t{fixture.priority}\t{fixture.runner}\t{fixture.repo}@{fixture.ref[:12]}")
        ####
        return 0
    ####
    if args.command == "domains":
        domains = load_contract(root, "domains").get("domains", {})
        for domain_id, payload in domains.items():
            print(f"{domain_id}\t{payload.get('proves', '')}")
        ####
        return 0
    ####
    if args.command == "coverage":
        rows = load_contract(root, "coverage").get("coverage", [])
        for row in rows:
            print(f"{row.get('capability')}\t{row.get('status')}\t{row.get('synthetic_scenario')}")
        ####
        return 0
    ####
    if args.command == "levels":
        levels = load_contract(root, "levels").get("levels", [])
        for level in levels:
            print(f"L{level.get('level')}\t{level.get('name')}\t{level.get('pass_condition')}")
        ####
        return 0
    ####
    if args.command == "artifacts":
        artifacts = load_contract(root, "artifacts").get("run_artifacts", {})
        for item in artifacts.get("required", []):
            print(item)
        ####
        return 0
    ####
    if args.command == "validate-contracts":
        errors = validate_contracts(root)
        if errors:
            for error in errors:
                print(error)
            ####
            return 1
        ####
        print("capability contracts valid")
        return 0
    ####
    if args.command == "clone":
        if args.all:
            for path in clone_all_fixtures(root, fixtures):
                print(path)
            ####
            return 0
        ####
        if not args.fixture_id:
            raise SystemExit("clone requires a fixture_id or --all")
        ####
        fixture = fixture_by_id(fixtures, args.fixture_id)
        print(clone_fixture(root, fixture))
        return 0
    ####
    if args.command == "inspect":
        fixture = fixture_by_id(fixtures, args.fixture_id)
        inspection = inspect_fixture(root, fixture)
        if args.as_json:
            print(json.dumps(inspection, indent=2, sort_keys=True))
            return 0
        ####
        print(f"fixture: {inspection['fixture']}")
        print(f"cloned: {inspection['cloned']}")
        print(f"language: {inspection['language']}")
        print(f"install: {format_shell_command(inspection['install_command'])}")
        print(f"run: {format_shell_command(inspection['run_command'])}")
        if len(inspection["run_commands"]) > 1:
            print("run_commands:")
            for command in inspection["run_commands"]:
                print(f"  {format_shell_command(command)}")
            ####
        print(f"config_files: {', '.join(inspection['config_files']) or 'none'}")
        print(f"required_env: {', '.join(inspection['required_env']) or 'none'}")
        print(f"placeholder_tokens: {', '.join(inspection['placeholder_tokens']) or 'none'}")
        return 0
    ####
    if args.command == "install":
        fixture = fixture_by_id(fixtures, args.fixture_id)
        result = install_fixture(root, fixture)
        if args.as_json:
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        ####
        print(f"fixture: {result['fixture']}")
        print(f"status: {result['status']}")
        print(f"clone_dir: {result['clone_dir']}")
        print(f"install: {format_shell_command(result['install_command'])}")
        print(f"run: {format_shell_command(result['run_command'])}")
        if len(result["run_commands"]) > 1:
            print("run_commands:")
            for command in result["run_commands"]:
                print(f"  {format_shell_command(command)}")
            ####
        return 0
    ####
    if args.command == "run":
        fixture = fixture_by_id(fixtures, args.fixture_id)
        report_path = run_fixture(
            root,
            fixture,
            target=args.target,
            token=args.token,
            mode=args.mode,
        )
        print(report_path)
        return 0
    ####
    if args.command == "report":
        print(reports_summary(root, as_json=args.as_json))
        return 0
    ####
    return 2
####
