from __future__ import annotations

import json
from pathlib import Path

import pytest

from zorn.cert import harness
from zorn.cert.harness import Fixture, format_shell_command, inspect_fixture, load_fixtures


ROOT = Path(__file__).resolve().parents[1]


def _fixture(*, fixture_id: str, runner: str) -> Fixture:
    return Fixture(
        id=fixture_id,
        repo="https://example.invalid/repo.git",
        ref="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        priority="P0",
        category="test_fixture",
        runner=runner,
        license_status="unknown",
        surfaces=("entities.publish",),
        modes=("strict",),
        install_command=None,
        run_commands=(),
        config_files=(),
        required_env=(),
        placeholder_tokens=(),
    )


def test_inspect_fixture_detects_python_workspace(tmp_path: Path) -> None:
    root = tmp_path
    clone_dir = root / "cert" / "lattice" / ".fixtures" / "python-fixture"
    (clone_dir / "src").mkdir(parents=True)
    (clone_dir / "var").mkdir(parents=True)
    (clone_dir / "src" / "main.py").write_text("import os\nprint(os.getenv('LATTICE_ENDPOINT'))\n")
    (clone_dir / "requirements.txt").write_text("requests\n")
    (clone_dir / "README.md").write_text("Replace <ENVIRONMENT_TOKEN> and <SANDBOXES_TOKEN>\n")
    (clone_dir / "var" / "config.yml").write_text("endpoint: https://example.test\n")

    inspection = inspect_fixture(root, _fixture(fixture_id="python-fixture", runner="python_sample"))

    assert inspection["cloned"] is True
    assert inspection["language"] == "python"
    assert inspection["install_command"] == ["python", "-m", "pip", "install", "-r", "requirements.txt"]
    assert inspection["run_command"] == ["python", "src/main.py", "--config", "var/config.yml"]
    assert inspection["run_commands"] == [["python", "src/main.py", "--config", "var/config.yml"]]
    assert "var/config.yml" in inspection["config_files"]
    assert "LATTICE_ENDPOINT" in inspection["required_env"]
    assert inspection["placeholder_tokens"] == ["ENVIRONMENT_TOKEN", "SANDBOXES_TOKEN"]


def test_inspect_fixture_detects_node_workspace(tmp_path: Path) -> None:
    root = tmp_path
    clone_dir = root / "cert" / "lattice" / ".fixtures" / "node-fixture"
    clone_dir.mkdir(parents=True)
    (clone_dir / "package-lock.json").write_text("{}\n")
    (clone_dir / "package.json").write_text(json.dumps({"scripts": {"start": "node index.js"}}))
    (clone_dir / ".env.example").write_text("LATTICE_TOKEN=\n")

    inspection = inspect_fixture(root, _fixture(fixture_id="node-fixture", runner="node_sample"))

    assert inspection["language"] == "node"
    assert inspection["install_command"] == ["npm", "ci"]
    assert inspection["run_command"] == ["npm", "run", "start"]
    assert inspection["run_commands"] == [["npm", "run", "start"]]
    assert ".env.example" in inspection["config_files"]


def test_inspect_fixture_reports_uncloned_workspace() -> None:
    inspection = inspect_fixture(ROOT, _fixture(fixture_id="not-present", runner="go_sample"))

    assert inspection["cloned"] is False
    assert inspection["language"] == "go"
    assert inspection["install_command"] is None
    assert inspection["run_command"] is None
    assert inspection["run_commands"] == []


def test_format_shell_command() -> None:
    assert format_shell_command(["python", "src/main.py", "--config", "var/config.yml"]) == "python src/main.py --config var/config.yml"
    assert format_shell_command(None) == "n/a"


def test_manifest_overrides_are_exposed_for_official_fixture() -> None:
    fixtures = load_fixtures(ROOT)
    fixture = next(item for item in fixtures if item.id == "anduril-sample-auto-reconnaissance")

    inspection = inspect_fixture(ROOT, fixture)

    assert inspection["install_command"] == ["python", "-m", "pip", "install", "-r", "requirements.txt"]
    assert inspection["run_commands"] == [
        ["python", "auto-reconnaissance/main.py", "--config", "var/config.yml"],
        ["python", "simulated_asset/asset.py", "--config", "var/config.yml"],
        ["python", "simulated_track/track.py", "--config", "var/config.yml"],
    ]
    assert inspection["config_files"] == ["var/config.yml"]
    assert inspection["placeholder_tokens"] == [
        "LATTICE_ENDPOINT",
        "LATTICE_CLIENT_ID",
        "LATTICE_CLIENT_SECRET",
        "SANDBOXES_TOKEN",
    ]


def test_manifest_overrides_are_exposed_for_dragonsync_fixture() -> None:
    fixtures = load_fixtures(ROOT)
    fixture = next(item for item in fixtures if item.id == "alphafox-dragonsync")

    inspection = inspect_fixture(ROOT, fixture)

    assert inspection["install_command"] == ["python", "-m", "pip", "install", "-r", "requirements.txt", "anduril-lattice-sdk"]
    assert inspection["run_commands"] == [["python", "dragonsync.py", "--lattice-enabled"]]
    assert inspection["required_env"] == ["ENVIRONMENT_TOKEN", "SANDBOXES_TOKEN", "LATTICE_ENDPOINT"]


def test_manifest_overrides_are_exposed_for_maven_fixture() -> None:
    fixtures = load_fixtures(ROOT)
    fixture = next(item for item in fixtures if item.id == "daemon-maven")

    inspection = inspect_fixture(ROOT, fixture)

    assert inspection["install_command"] == ["go", "mod", "download"]
    assert inspection["run_commands"] == [["go", "run", "./cmd/ingest"], ["go", "run", "./cmd/publish"]]
    assert inspection["required_env"] == ["LATTICE_URL", "LATTICE_CLIENT_ID", "LATTICE_CLIENT_SECRET", "SANDBOX_TOKEN"]


def test_manifest_overrides_are_exposed_for_java_adsb_fixture() -> None:
    fixtures = load_fixtures(ROOT)
    fixture = next(item for item in fixtures if item.id == "philippanda-lattice-adsb-bridge")

    inspection = inspect_fixture(ROOT, fixture)

    assert inspection["install_command"] == ["mvn", "-q", "-DskipTests", "package"]
    assert inspection["run_commands"] == [["java", "-jar", "target/lattice-adsb-bridge-1.0.0-SNAPSHOT.jar"]]
    assert inspection["config_files"] == ["pom.xml", "src/main/resources/application.properties"]


def test_manifest_overrides_are_exposed_for_deep_prove_fixture() -> None:
    fixtures = load_fixtures(ROOT)
    fixture = next(item for item in fixtures if item.id == "lagrange-deep-prove-demo")

    inspection = inspect_fixture(ROOT, fixture)

    assert inspection["install_command"] == ["python", "-m", "pip", "install", "-r", "requirements.txt"]
    assert inspection["run_commands"] == [
        ["python", "auto-reconnaissance/main.py", "--config", "var/config.yml"],
        ["python", "simulated_asset/asset.py", "--config", "var/config.yml"],
        ["python", "simulated_track/track.py", "--config", "var/config.yml"],
    ]
    assert inspection["config_files"] == ["var/config.yml"]
    assert inspection["required_env"] == ["LATTICE_ENDPOINT", "ENVIRONMENT_TOKEN", "SANDBOXES_TOKEN"]


def test_manifest_overrides_are_exposed_for_alfred_fixture() -> None:
    fixtures = load_fixtures(ROOT)
    fixture = next(item for item in fixtures if item.id == "tyler-alfred-agent")

    inspection = inspect_fixture(ROOT, fixture)

    assert inspection["install_command"] == ["python", "-m", "pip", "install", "anduril-lattice-sdk"]
    assert inspection["required_env"] == [
        "LATTICE_ENDPOINT",
        "LATTICE_CLIENT_ID",
        "LATTICE_CLIENT_SECRET",
        "LATTICE_SANDBOXES_TOKEN",
        "ENVIRONMENT_TOKEN",
    ]
    assert inspection["placeholder_tokens"] == [
        "LATTICE_ENDPOINT",
        "LATTICE_CLIENT_ID",
        "LATTICE_CLIENT_SECRET",
    ]


def test_install_fixture_uses_fixture_venv_for_python(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    clone_dir = tmp_path / "cert" / "lattice" / ".fixtures" / "python-fixture"
    clone_dir.mkdir(parents=True)
    (clone_dir / "requirements.txt").write_text("requests\n")
    fixture = Fixture(
        id="python-fixture",
        repo="https://example.invalid/repo.git",
        ref="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        priority="P0",
        category="test_fixture",
        runner="python_sample",
        license_status="unknown",
        surfaces=("entities.publish",),
        modes=("strict",),
        install_command=("python", "-m", "pip", "install", "-r", "requirements.txt"),
        run_commands=(),
        config_files=(),
        required_env=(),
        placeholder_tokens=(),
    )
    recorded: dict[str, object] = {}

    def fake_run(command: list[str], root: Path) -> None:
        recorded["command"] = command
        recorded["root"] = root

    monkeypatch.setattr(harness, "_run", fake_run)
    monkeypatch.setattr(harness, "ensure_python_venv", lambda fixture_dir: fixture_dir / ".venv" / "bin" / "python")

    result = harness.install_fixture(tmp_path, fixture)

    assert recorded["command"] == [str(clone_dir / ".venv" / "bin" / "python"), "-m", "pip", "install", "-r", "requirements.txt"]
    assert recorded["root"] == clone_dir
    assert result["status"] == "installed"
