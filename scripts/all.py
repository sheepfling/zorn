from __future__ import annotations

import os
import subprocess
import sys

from workflow_bootstrap import CACHE_ROOT, ROOT, ensure_src_on_path


def main() -> int:
    ensure_src_on_path()
    env = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "src"),
        "PYTHONPYCACHEPREFIX": str(CACHE_ROOT / ".pycache"),
    }
    commands = [
        [sys.executable, "scripts/check_env.py"],
        [sys.executable, "scripts/check_plans.py"],
        [sys.executable, "-m", "pytest"],
        [sys.executable, "-m", "zorn"],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, env=env, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
