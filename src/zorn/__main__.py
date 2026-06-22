from __future__ import annotations

from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    print("Zorn surrogate workspace is ready.")
    print(f"repo_root={repo_root}")
    print("next_step=replace placeholder lattice logic as the real surface becomes available")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
