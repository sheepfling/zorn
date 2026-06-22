from __future__ import annotations

from pathlib import Path


def test_sample_app_objects_harness_script_exists() -> None:
    assert Path("scripts/run_sample_app_objects.sh").exists()
