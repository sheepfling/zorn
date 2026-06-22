from __future__ import annotations

from pathlib import Path

import pytest

from zorn.cert.harness import Fixture
from zorn.cert.runners import run_java_sample as java_runner
from zorn.cert.runners.run_java_sample import run_java_sample


def test_java_runner_reports_missing_prerequisites(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture_dir = tmp_path / "fixture"
    mock_config = fixture_dir / "src" / "main" / "java" / "com" / "example" / "lattice" / "config"
    mock_dir = fixture_dir / "src" / "main" / "java" / "com" / "example" / "lattice" / "mock"
    mock_config.mkdir(parents=True)
    mock_dir.mkdir(parents=True)
    (mock_config / "LatticeClientConfig.java").write_text(
        'private static final String MOCK_SERVER_URL = "http://localhost:8080";\n',
        encoding="utf-8",
    )
    (mock_dir / "MockEntityController.java").write_text("class MockEntityController {}\n", encoding="utf-8")
    (mock_dir / "MockStreamController.java").write_text("class MockStreamController {}\n", encoding="utf-8")
    monkeypatch.setattr(java_runner, "_discover_java_home", lambda tooling_root: None)
    monkeypatch.setattr(java_runner, "_discover_maven", lambda tooling_root: None)

    fixture = Fixture(
        id="philippanda-lattice-adsb-bridge",
        repo="https://example.invalid/repo.git",
        ref="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        priority="P1",
        category="third_party_real",
        runner="java_sample",
        license_status="no_license_found",
        adaptation_tier="runtime_env_translation",
        surfaces=("auth.bearer_token", "entities.publish", "entities.transponder_codes", "ui.sse"),
        modes=("strict", "stress"),
        install_command=("mvn", "-q", "-DskipTests", "package"),
        run_commands=(("java", "-jar", "target/lattice-adsb-bridge-1.0.0-SNAPSHOT.jar"),),
        config_files=("pom.xml", "src/main/resources/application.properties"),
        required_env=(),
        placeholder_tokens=(),
    )

    report = run_java_sample(
        fixture=fixture,
        fixture_dir=fixture_dir,
        target="http://localhost:8080",
        token="dev-token",
        mode="strict",
    )

    assert report["result"] == "blocked"
    assert report["missing"] == list(fixture.surfaces)
    assert report["details"]["hardcoded_mock_url"] is True
    assert "MockEntityController.java" in report["details"]["embedded_mock_controllers"]
    assert "local prerequisites missing for Java fixture" == report["details"]["reason"]
####
