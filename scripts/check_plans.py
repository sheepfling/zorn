from __future__ import annotations

import sys

from workflow_bootstrap import ROOT


REQUIRED_FILES = (
    ROOT / "README.md",
    ROOT / "docs" / "README.md",
    ROOT / "docs" / "plans" / "README.md",
    ROOT / "docs" / "plans" / "active" / "README.md",
)


def main() -> int:
    missing = [path for path in REQUIRED_FILES if not path.exists()]
    if missing:
        for path in missing:
            print(f"missing required plan doc: {path.relative_to(ROOT)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
