from __future__ import annotations

import importlib


def test_zorn_package_does_not_expose_adapter_namespace() -> None:
    try:
        import zorn
    except ImportError as exc:  # pragma: no cover - import itself should not fail
        raise AssertionError("zorn package should import cleanly") from exc

    assert not hasattr(zorn, "adapters")

    try:
        importlib.import_module("zorn.adapters")
    except ModuleNotFoundError:
        return
    except Exception as exc:  # pragma: no cover - wrong failure mode
        raise AssertionError("zorn.adapters should not be importable") from exc

    raise AssertionError("zorn.adapters should not be importable")
