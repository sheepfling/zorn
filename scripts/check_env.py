from __future__ import annotations

import sys

from workflow_bootstrap import CACHE_ROOT, ROOT, ensure_src_on_path


def main() -> int:
    ensure_src_on_path()
    print(f"repo_root={ROOT}")
    print(f"cache_root={CACHE_ROOT}")
    print(f"python={sys.executable}")
    from zorn.workspace_hygiene import assert_cache_links

    try:
        assert_cache_links(ROOT, CACHE_ROOT)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
