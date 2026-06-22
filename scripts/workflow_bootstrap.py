from __future__ import annotations

import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DEFAULT_CACHE_ROOT = (
    Path.home() / "LocalStorage" / "GIT_LOCAL" / "active" / "CACHE" / ROOT.name
)
CACHE_ROOT = Path(os.environ.get("ZORN_CACHE_ROOT", DEFAULT_CACHE_ROOT))


def ensure_src_on_path() -> None:
    src = str(SRC)
    if src not in sys.path:
        sys.path.insert(0, src)
