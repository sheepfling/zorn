from __future__ import annotations

from pathlib import Path

import pytest

from zorn.cert.harness import Fixture
from zorn.cert.runners.run_contract_fixture import run_cpp_sample, run_rust_sample


def test_run_rust_sample_reports_missing_cargo_for_sdk_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = Fixture(
        id="sdk-rust-grpc-smoke",
        repo="https://example.invalid/lattice-sdk-rust.git",
        ref="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        priority="P2",
        category="official_sdk_conformance",
        runner="rust_sample",
        license_status="upstream_terms_review_required",
        adaptation_tier="runtime_shim",
        surfaces=(
            "auth.grpc_bearer_metadata",
            "transport.grpc_protobuf",
            "entities.publish",
            "entities.get",
            "entities.grpc_stream",
            "tasks.create",
            "tasks.listen_as_agent",
            "tasks.update_status",
        ),
        modes=("strict",),
        install_command=None,
        run_commands=(),
        config_files=(),
        required_env=(),
        placeholder_tokens=(),
    )
    monkeypatch.setattr("zorn.cert.runners.run_contract_fixture.shutil.which", lambda tool: None)

    report = run_rust_sample(
        fixture=fixture,
        fixture_dir=tmp_path / "sdk-rust-grpc-smoke",
        target="http://localhost:8080",
        token="dev-token",
        mode="strict",
    )

    assert report["result"] == "blocked"
    assert report["missing"] == list(fixture.surfaces)
    assert report["details"]["required_tools"] == ["cargo"]
    assert report["details"]["reason"] == "cargo is required for sdk-rust-grpc-smoke"
####


def test_run_cpp_sample_reports_missing_cmake_package_configs_for_sdk_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = Fixture(
        id="sdk-cpp-grpc-smoke",
        repo="https://example.invalid/lattice-sdk-cpp.git",
        ref="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        priority="P2",
        category="official_sdk_conformance",
        runner="cpp_sample",
        license_status="upstream_terms_review_required",
        adaptation_tier="runtime_shim",
        surfaces=(
            "auth.grpc_bearer_metadata",
            "transport.grpc_protobuf",
            "entities.publish",
            "entities.get",
            "entities.grpc_stream",
            "tasks.create",
            "tasks.listen_as_agent",
            "tasks.update_status",
        ),
        modes=("strict",),
        install_command=None,
        run_commands=(),
        config_files=(),
        required_env=(),
        placeholder_tokens=(),
    )

    def fake_which(tool: str) -> str | None:
        return "/usr/bin/cmake" if tool == "cmake" else None

    monkeypatch.setattr("zorn.cert.runners.run_contract_fixture.shutil.which", fake_which)
    monkeypatch.setattr(
        "zorn.cert.runners.run_contract_fixture._find_cmake_package_config",
        lambda *, package_dir, filename: None,
    )

    report = run_cpp_sample(
        fixture=fixture,
        fixture_dir=tmp_path / "sdk-cpp-grpc-smoke",
        target="http://localhost:8080",
        token="dev-token",
        mode="strict",
    )

    assert report["result"] == "blocked"
    assert report["missing"] == list(fixture.surfaces)
    assert report["details"]["required_tools"] == ["cmake", "gRPCConfig.cmake", "protobuf-config.cmake"]
    assert report["details"]["reason"] == "system gRPC/protobuf C++ development packages are required for sdk-cpp-grpc-smoke"
####
