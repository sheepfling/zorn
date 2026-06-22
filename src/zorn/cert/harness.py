from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import shlex
import subprocess
from typing import Any

import yaml

from .runners.run_python_sample import run_python_sample
from .runners.run_go_sample import run_go_sample
from .runners.run_java_sample import run_java_sample
from .runners.run_node_sample import run_node_sample
from .runners.run_contract_fixture import (
    run_cpp_sample,
    run_postman_rest,
    run_rust_sample,
    run_schema_proto,
    run_spec_rest,
)
from .runners.common import ensure_python_venv


CERT_ROOT = Path("cert") / "lattice"
FIXTURES_FILE = CERT_ROOT / "fixtures.yaml"
CAPABILITIES_FILE = CERT_ROOT / "capabilities.yaml"
DOMAINS_FILE = CERT_ROOT / "domains.yaml"
COVERAGE_FILE = CERT_ROOT / "coverage.yaml"
LEVELS_FILE = CERT_ROOT / "levels.yaml"
SCENARIOS_FILE = CERT_ROOT / "scenarios.yaml"
ARTIFACTS_FILE = CERT_ROOT / "artifacts.yaml"
ADAPTATION_TIERS_FILE = CERT_ROOT / "adaptation-tiers.yaml"
ASSERTIONS_FILE = CERT_ROOT / "assertions.yaml"
UI_REQUIREMENTS_FILE = Path("cert") / "ui" / "requirements.yaml"
REPORTS_DIR = CERT_ROOT / "reports"
CLONES_DIR = CERT_ROOT / ".fixtures"


@dataclass(frozen=True, slots=True)
class Fixture:
    id: str
    repo: str
    ref: str
    priority: str
    category: str
    runner: str
    license_status: str
    adaptation_tier: str
    surfaces: tuple[str, ...]
    modes: tuple[str, ...]
    install_command: tuple[str, ...] | None
    run_commands: tuple[tuple[str, ...], ...]
    config_files: tuple[str, ...]
    required_env: tuple[str, ...]
    placeholder_tokens: tuple[str, ...]


TEXT_SUFFIXES = {
    ".env",
    ".go",
    ".gradle",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".kts",
    ".md",
    ".properties",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}


def load_fixtures(root: Path) -> list[Fixture]:
    data = _load_yaml(root / FIXTURES_FILE)
    fixtures = data.get("fixtures", [])
    if not isinstance(fixtures, list):
        raise ValueError("fixtures.yaml must contain a fixtures list")
    ####
    return [_fixture_from_payload(item) for item in fixtures]
####


def load_contract(root: Path, name: str) -> dict[str, Any]:
    paths = {
        "adaptation_tiers": ADAPTATION_TIERS_FILE,
        "artifacts": ARTIFACTS_FILE,
        "assertions": ASSERTIONS_FILE,
        "capabilities": CAPABILITIES_FILE,
        "coverage": COVERAGE_FILE,
        "domains": DOMAINS_FILE,
        "levels": LEVELS_FILE,
        "scenarios": SCENARIOS_FILE,
        "ui_requirements": UI_REQUIREMENTS_FILE,
    }
    path = paths.get(name)
    if path is None:
        raise ValueError(f"unknown contract: {name}")
    ####
    return _load_yaml(root / path)
####


def contract_capabilities(root: Path) -> set[str]:
    capabilities = load_contract(root, "capabilities").get("capabilities", {})
    return set(capabilities) if isinstance(capabilities, dict) else set()
####


def contract_adaptation_tiers(root: Path) -> set[str]:
    tiers = load_contract(root, "adaptation_tiers").get("adaptation_tiers", {})
    return set(tiers) if isinstance(tiers, dict) else set()
####


def validate_contracts(root: Path) -> list[str]:
    known = contract_capabilities(root)
    known_tiers = contract_adaptation_tiers(root)
    errors: list[str] = []
    for contract_name in ("domains", "scenarios", "coverage", "levels", "assertions"):
        _validate_capability_references(load_contract(root, contract_name), known, errors, context=contract_name)
    ####
    for fixture in load_fixtures(root):
        if fixture.adaptation_tier not in known_tiers:
            errors.append(f"fixtures: {fixture.id} references unknown adaptation tier {fixture.adaptation_tier}")
        ####
        for surface in fixture.surfaces:
            if surface not in known:
                errors.append(f"fixtures: {fixture.id} references unknown capability {surface}")
            ####
        ####
    ####
    return errors
####


def fixture_by_id(fixtures: list[Fixture], fixture_id: str) -> Fixture:
    for fixture in fixtures:
        if fixture.id == fixture_id:
            return fixture
        ####
    ####
    raise SystemExit(f"unknown fixture: {fixture_id}")
####


def clone_all_fixtures(root: Path, fixtures: list[Fixture]) -> list[Path]:
    return [clone_fixture(root, fixture) for fixture in fixtures]
####


def clone_fixture(root: Path, fixture: Fixture) -> Path:
    clone_dir = fixture_clone_dir(root, fixture)
    clone_dir.parent.mkdir(parents=True, exist_ok=True)
    if clone_dir.exists():
        _run(["git", "-C", str(clone_dir), "fetch", "--all", "--tags"], root)
    else:
        _run(["git", "clone", fixture.repo, str(clone_dir)], root)
    ####
    _run(["git", "-C", str(clone_dir), "checkout", "--detach", fixture.ref], root)
    return clone_dir
####


def inspect_fixture(root: Path, fixture: Fixture) -> dict[str, Any]:
    clone_dir = fixture_clone_dir(root, fixture)
    workspace = _inspect_workspace(clone_dir, fixture.runner)
    install_command = list(fixture.install_command) if fixture.install_command else workspace["install_command"]
    run_commands = [list(command) for command in fixture.run_commands] if fixture.run_commands else workspace["run_commands"]
    config_files = list(fixture.config_files) if fixture.config_files else workspace["config_files"]
    required_env = list(fixture.required_env) if fixture.required_env else workspace["required_env"]
    placeholder_tokens = list(fixture.placeholder_tokens) if fixture.placeholder_tokens else workspace["placeholder_tokens"]
    return {
        "fixture": fixture.id,
        "priority": fixture.priority,
        "category": fixture.category,
        "runner": fixture.runner,
        "adaptation_tier": fixture.adaptation_tier,
        "repo": fixture.repo,
        "ref": fixture.ref,
        "clone_dir": str(clone_dir),
        "cloned": clone_dir.exists(),
        "language": workspace["language"],
        "install_command": install_command,
        "run_command": run_commands[0] if run_commands else None,
        "run_commands": run_commands,
        "config_files": config_files,
        "required_env": required_env,
        "placeholder_tokens": placeholder_tokens,
        "surfaces": list(fixture.surfaces),
        "modes": list(fixture.modes),
    }
####


def install_fixture(root: Path, fixture: Fixture) -> dict[str, Any]:
    clone_dir = fixture_clone_dir(root, fixture)
    cloned = clone_dir.exists()
    if not cloned:
        clone_dir = clone_fixture(root, fixture)
    ####
    inspection = inspect_fixture(root, fixture)
    install_command = list(inspection["install_command"]) if inspection["install_command"] else None
    if install_command is None:
        raise SystemExit(f"no install command detected for fixture {fixture.id}")
    ####
    if fixture.runner == "python_sample" and install_command and install_command[0] == "python":
        python = ensure_python_venv(clone_dir)
        install_command[0] = str(python)
    ####
    _run(install_command, clone_dir)
    return {
        "fixture": fixture.id,
        "cloned": cloned or clone_dir.exists(),
        "clone_dir": str(clone_dir),
        "language": inspection["language"],
        "install_command": install_command,
        "run_command": inspection["run_command"],
        "run_commands": inspection["run_commands"],
        "config_files": inspection["config_files"],
        "required_env": inspection["required_env"],
        "status": "installed",
    }
####


def run_fixture(root: Path, fixture: Fixture, *, target: str, token: str, mode: str) -> Path:
    clone_dir = fixture_clone_dir(root, fixture)
    if not clone_dir.exists():
        clone_fixture(root, fixture)
    ####
    if mode not in fixture.modes:
        raise SystemExit(f"fixture {fixture.id} does not support mode {mode}; supported: {', '.join(fixture.modes)}")
    ####
    runner = {
        "python_sample": run_python_sample,
        "go_sample": run_go_sample,
        "java_sample": run_java_sample,
        "node_sample": run_node_sample,
        "cpp_sample": run_cpp_sample,
        "rust_sample": run_rust_sample,
        "schema_proto": run_schema_proto,
        "spec_rest": run_spec_rest,
        "postman_rest": run_postman_rest,
    }.get(fixture.runner)
    if runner is None:
        raise SystemExit(f"unsupported runner for {fixture.id}: {fixture.runner}")
    ####
    report = runner(fixture=fixture, fixture_dir=clone_dir, target=target, token=token, mode=mode)
    report.setdefault("fixture", fixture.id)
    report.setdefault("zorn_version", _zorn_version(root))
    report.setdefault("mode", mode)
    report.setdefault("adaptation_tier", fixture.adaptation_tier)
    report_path = report_file(root, fixture)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report_path
####


def reports_summary(root: Path, *, as_json: bool) -> str:
    reports = []
    tiers_by_fixture = {fixture.id: fixture.adaptation_tier for fixture in load_fixtures(root)}
    reports_dir = root / REPORTS_DIR
    for path in sorted(reports_dir.glob("*.json")):
        report = json.loads(path.read_text())
        report.setdefault("adaptation_tier", tiers_by_fixture.get(str(report.get("fixture")), "unreported"))
        reports.append(report)
    ####
    if as_json:
        return json.dumps({"reports": reports}, indent=2, sort_keys=True)
    ####
    if not reports:
        return "no certification reports found"
    ####
    return "\n".join(
        f"{report.get('fixture')}: {report.get('result')} "
        f"tier={report.get('adaptation_tier', 'unreported')} "
        f"passed={len(report.get('passed', []))} failed={len(report.get('failed', []))} missing={len(report.get('missing', []))}"
        for report in reports
    )
####


def fixture_clone_dir(root: Path, fixture: Fixture) -> Path:
    return root / CLONES_DIR / fixture.id
####


def report_file(root: Path, fixture: Fixture) -> Path:
    return root / REPORTS_DIR / f"{fixture.id}.json"
####


def _fixture_from_payload(payload: dict[str, Any]) -> Fixture:
    surfaces = payload.get("surfaces", [])
    modes = payload.get("modes", ["strict"])
    return Fixture(
        id=str(payload["id"]),
        repo=str(payload["repo"]),
        ref=str(payload["ref"]),
        priority=str(payload["priority"]),
        category=str(payload["category"]),
        runner=str(payload["runner"]),
        license_status=str(payload["license_status"]),
        adaptation_tier=str(payload.get("adaptation_tier", "endpoint_token_only")),
        surfaces=tuple(str(surface) for surface in surfaces),
        modes=tuple(str(mode) for mode in modes),
        install_command=_command_tuple(payload.get("install_command")),
        run_commands=tuple(command for command in _command_list(payload.get("run_commands"))),
        config_files=tuple(str(path) for path in payload.get("config_files", [])),
        required_env=tuple(str(name) for name in payload.get("required_env", [])),
        placeholder_tokens=tuple(str(token) for token in payload.get("placeholder_tokens", [])),
    )
####


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        data = yaml.safe_load(handle)
    ####
    return data if isinstance(data, dict) else {}
####


def format_shell_command(command: list[str] | None) -> str:
    if not command:
        return "n/a"
    ####
    return shlex.join(command)
####


def _validate_capability_references(value: Any, known: set[str], errors: list[str], *, context: str) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in {"capabilities", "required_capabilities"}:
                values = [nested] if isinstance(nested, str) else nested
                if isinstance(values, list):
                    for capability in values:
                        if isinstance(capability, str) and capability not in known:
                            errors.append(f"{context}: unknown capability {capability}")
                        ####
                    ####
                ####
            else:
                _validate_capability_references(nested, known, errors, context=context)
            ####
        ####
    elif isinstance(value, list):
        for nested in value:
            _validate_capability_references(nested, known, errors, context=context)
        ####
    ####
####


def _inspect_workspace(clone_dir: Path, runner: str) -> dict[str, Any]:
    if not clone_dir.exists():
        return {
            "language": _language_for_runner(runner),
            "install_command": None,
            "run_commands": [],
            "config_files": [],
            "required_env": [],
            "placeholder_tokens": [],
        }
    ####

    relative_paths = sorted(path.relative_to(clone_dir).as_posix() for path in clone_dir.rglob("*") if path.is_file())
    config_files = [path for path in relative_paths if _looks_like_config_file(path)]
    text_files = [clone_dir / path for path in relative_paths if _text_candidate(path)]
    env_names, placeholders = _scan_text_files(text_files)
    language = _detect_language(clone_dir, runner, relative_paths)
    install_command = _detect_install_command(clone_dir, language, relative_paths)
    run_commands = _detect_run_commands(clone_dir, language, relative_paths)
    return {
        "language": language,
        "install_command": install_command,
        "run_commands": run_commands,
        "config_files": config_files,
        "required_env": env_names,
        "placeholder_tokens": placeholders,
    }
####


def _detect_language(clone_dir: Path, runner: str, relative_paths: list[str]) -> str:
    del clone_dir
    if runner == "python_sample" or any(path.endswith(".py") for path in relative_paths):
        return "python"
    ####
    if runner == "go_sample" or "go.mod" in relative_paths:
        return "go"
    ####
    if runner == "node_sample" or "package.json" in relative_paths:
        return "node"
    ####
    if runner == "java_sample" or any(path.endswith((".java", ".kt", ".kts")) for path in relative_paths):
        return "java"
    ####
    if runner == "cpp_sample" or any(path.endswith((".cc", ".cpp", ".cxx", ".h", ".hpp")) for path in relative_paths):
        return "cpp"
    ####
    if runner == "rust_sample" or "Cargo.toml" in relative_paths:
        return "rust"
    ####
    if runner in {"spec_rest", "postman_rest", "schema_proto", "reference_only"}:
        return runner
    ####
    return _language_for_runner(runner)
####


def _language_for_runner(runner: str) -> str:
    return {
        "python_sample": "python",
        "go_sample": "go",
        "node_sample": "node",
        "java_sample": "java",
        "cpp_sample": "cpp",
        "rust_sample": "rust",
        "spec_rest": "spec",
        "postman_rest": "postman",
        "schema_proto": "proto",
        "reference_only": "reference",
    }.get(runner, "unknown")
####


def _detect_install_command(clone_dir: Path, language: str, relative_paths: list[str]) -> list[str] | None:
    del clone_dir
    if language == "python":
        if "requirements.txt" in relative_paths:
            return ["python", "-m", "pip", "install", "-r", "requirements.txt"]
        ####
        if "pyproject.toml" in relative_paths or "setup.py" in relative_paths:
            return ["python", "-m", "pip", "install", "-e", "."]
        ####
        return None
    ####
    if language == "go":
        return ["go", "mod", "download"] if "go.mod" in relative_paths else None
    ####
    if language == "node":
        if "package-lock.json" in relative_paths:
            return ["npm", "ci"]
        ####
        if "pnpm-lock.yaml" in relative_paths:
            return ["pnpm", "install", "--frozen-lockfile"]
        ####
        if "yarn.lock" in relative_paths:
            return ["yarn", "install", "--frozen-lockfile"]
        ####
        if "package.json" in relative_paths:
            return ["npm", "install"]
        ####
        return None
    ####
    if language == "java":
        if "pom.xml" in relative_paths:
            return ["mvn", "-q", "-DskipTests", "package"]
        ####
        if "gradlew" in relative_paths:
            return ["./gradlew", "build", "-x", "test"]
        ####
        if "build.gradle" in relative_paths or "build.gradle.kts" in relative_paths:
            return ["gradle", "build", "-x", "test"]
        ####
        return None
    ####
    if language == "cpp":
        if "CMakeLists.txt" in relative_paths:
            return ["cmake", "-S", ".", "-B", "build"]
        ####
        return None
    ####
    if language == "rust":
        return ["cargo", "fetch"] if "Cargo.toml" in relative_paths else None
    ####
    return None
####


def _detect_run_commands(clone_dir: Path, language: str, relative_paths: list[str]) -> list[list[str]]:
    if language == "python":
        if "src/main.py" in relative_paths:
            command = ["python", "src/main.py"]
            if "var/config.yml" in relative_paths:
                command.extend(["--config", "var/config.yml"])
            ####
            return [command]
        ####
        if "main.py" in relative_paths:
            return [["python", "main.py"]]
        ####
        return []
    ####
    if language == "go":
        if "main.go" in relative_paths:
            return [["go", "run", "."]]
        ####
        for path in relative_paths:
            if path.endswith("/main.go") and path.count("/") >= 1:
                return [["go", "run", f"./{Path(path).parent.as_posix()}"]]
            ####
        ####
        return []
    ####
    if language == "node":
        package_json = clone_dir / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text())
            except json.JSONDecodeError:
                data = {}
            ####
            scripts = data.get("scripts", {})
            if isinstance(scripts, dict):
                if "start" in scripts:
                    return [["npm", "run", "start"]]
                ####
                if "dev" in scripts:
                    return [["npm", "run", "dev"]]
                ####
            ####
        ####
        return []
    ####
    if language == "java":
        if "pom.xml" in relative_paths:
            return [["mvn", "exec:java"]]
        ####
        if "gradlew" in relative_paths:
            return [["./gradlew", "run"]]
        ####
        return []
    ####
    if language == "cpp":
        return [["cmake", "--build", "build"]] if "CMakeLists.txt" in relative_paths else []
    ####
    if language == "rust":
        return [["cargo", "test"]] if "Cargo.toml" in relative_paths else []
    ####
    return []
####


def _looks_like_config_file(path: str) -> bool:
    lower = path.lower()
    if lower.startswith(".git/") or lower.startswith(".github/"):
        return False
    ####
    name = Path(lower).name
    return (
        name.startswith(".env")
        or "config" in name
        or lower.endswith((".json", ".properties", ".toml", ".yaml", ".yml"))
    )
####


def _text_candidate(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    name = Path(path).name.lower()
    return suffix in TEXT_SUFFIXES or name in {"dockerfile", "makefile"}
####


def _scan_text_files(paths: list[Path]) -> tuple[list[str], list[str]]:
    env_names: set[str] = set()
    placeholders: set[str] = set()
    env_patterns = [
        re.compile(r"os\.getenv\(\s*[\"']([A-Z0-9_]+)[\"']"),
        re.compile(r"process\.env\.([A-Z0-9_]+)"),
        re.compile(r"System\.getenv\(\s*[\"']([A-Z0-9_]+)[\"']"),
        re.compile(r"\bgetenv\(\s*[\"']([A-Z0-9_]+)[\"']"),
    ]
    placeholder_pattern = re.compile(r"<([A-Z0-9_]+)>")
    for path in paths:
        try:
            if path.stat().st_size > 256_000:
                continue
            ####
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        ####
        for pattern in env_patterns:
            env_names.update(pattern.findall(text))
        ####
        placeholders.update(placeholder_pattern.findall(text))
    ####
    return sorted(env_names), sorted(placeholders)
####


def _command_tuple(value: Any) -> tuple[str, ...] | None:
    if not isinstance(value, list):
        return None
    ####
    return tuple(str(part) for part in value)
####


def _command_list(value: Any) -> list[tuple[str, ...]]:
    if not isinstance(value, list):
        return []
    ####
    commands: list[tuple[str, ...]] = []
    for item in value:
        if isinstance(item, list):
            commands.append(tuple(str(part) for part in item))
        ####
    ####
    return commands
####


def _run(command: list[str], root: Path) -> None:
    result = subprocess.run(command, cwd=root, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    ####
####


def _zorn_version(root: Path) -> str:
    data = (root / "pyproject.toml").read_text()
    for line in data.splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
        ####
    ####
    return "unknown"
####
