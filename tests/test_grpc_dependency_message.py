from __future__ import annotations

from zorn.grpc_api.proto_modules import (
    MissingLatticeProtoDependency,
    OFFICIAL_BUF_PACKAGES,
    load_lattice_proto_modules,
)


def test_lattice_proto_dependency_message_is_actionable() -> None:
    try:
        modules = load_lattice_proto_modules()
    except MissingLatticeProtoDependency as exc:
        message = str(exc)
        assert "official Buf-generated Python packages" in message
        assert "uv sync --extra grpc" in message
        assert "./scripts/install_grpc_deps.sh" in message
        assert "pinned compatibility contract" in message or "Missing import:" in message
        return
    ####
    assert modules.entity_api is not None
    assert modules.entity_grpcapi is not None
    assert modules.entity_api_grpc is not None
    assert modules.entity is not None
    assert modules.task_api is not None
    assert modules.task_grpcapi is not None
    assert modules.task_api_grpc is not None
####


def test_official_buf_package_pins_include_bsr_commit_suffix() -> None:
    assert OFFICIAL_BUF_PACKAGES["anduril-lattice-sdk-grpc-python"].endswith("+ed34febdefc1")
    assert OFFICIAL_BUF_PACKAGES["anduril-lattice-sdk-protocolbuffers-python"].endswith("+ed34febdefc1")
    assert OFFICIAL_BUF_PACKAGES["anduril-lattice-sdk-protocolbuffers-pyi"].endswith("+ed34febdefc1")
####
