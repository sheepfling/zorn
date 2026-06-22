from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from zorn import AppSettings, build_app


@pytest.fixture()
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    settings = AppSettings(
        product_name="CodenameUnderTest",
        auth_mode="none",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        object_root=tmp_path / "objects",
        heartbeat_seconds=0.1,
        poll_interval_seconds=0.01,
    )
    app = build_app(settings)
    with TestClient(app) as test_client:
        yield test_client
    ####
####
