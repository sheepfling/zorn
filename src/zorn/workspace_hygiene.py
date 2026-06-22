from __future__ import annotations

from pathlib import Path


REQUIRED_CACHE_LINKS = (
    ".venv",
    ".cache",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "cache",
    "archive",
)

REQUIRED_LOCAL_DIRECTORIES = (
    "artifacts",
    "INTAKE",
)


def cache_link_issues(repo_root: Path, cache_root: Path) -> list[str]:
    issues: list[str] = []
    normalized_cache_root = cache_root.resolve(strict=False)
    for name in REQUIRED_CACHE_LINKS:
        path = repo_root / name
        expected_target = cache_root / name
        normalized_expected_target = normalized_cache_root / name
        resolved_expected_target = expected_target.resolve(strict=False)
        if not path.exists() and not path.is_symlink():
            issues.append(f"{path} is missing")
            continue
        if not path.is_symlink():
            issues.append(f"{path} is not a symlink")
            continue
        resolved = path.resolve(strict=False)
        if resolved != resolved_expected_target:
            issues.append(f"{path} points to {resolved}, expected {resolved_expected_target}")
            continue
        if not normalized_expected_target.exists():
            issues.append(f"{path} target {expected_target} does not exist")
    for name in REQUIRED_LOCAL_DIRECTORIES:
        path = repo_root / name
        if not path.exists():
            issues.append(f"{path} is missing")
            continue
        if path.is_symlink():
            issues.append(f"{path} must be a local directory, not a symlink")
            continue
        if not path.is_dir():
            issues.append(f"{path} is not a directory")
    return issues


def assert_cache_links(repo_root: Path, cache_root: Path) -> None:
    issues = cache_link_issues(repo_root, cache_root)
    if issues:
        raise RuntimeError(
            "workspace hygiene check failed:\n" + "\n".join(f"- {issue}" for issue in issues)
        )
