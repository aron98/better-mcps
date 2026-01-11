#!/usr/bin/env python3
"""Tag packages when their versions change on main.

Designed to be run from GitHub Actions on push to main.

It examines a commit range, finds any top-level packages whose
`<pkg>/pyproject.toml` changed, verifies that the corresponding
`__init__.__version__` matches (if present), and creates/pushes annotated tags:

  better-mcps-<pkg>-v<version>

It fails closed:
- if a package changed but version cannot be read
- if __init__.py exists with __version__ and it doesn't match pyproject

Usage:
  python scripts/tag_on_merge.py <before_sha> <after_sha>
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, cwd: Path | None = None) -> str:
    out = subprocess.check_output(list(args), cwd=cwd, stderr=subprocess.STDOUT)
    return out.decode("utf-8").strip()


def read_project_version(pyproject: Path) -> str:
    text = pyproject.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"\s*$', text, flags=re.M)
    if not m:
        raise ValueError(f"Could not find version in {pyproject}")
    return m.group(1)


def find_init_with_version(pkg_dir: Path) -> Path | None:
    src = pkg_dir / "src"
    if not src.exists():
        return None
    for init_py in src.glob("*/__init__.py"):
        txt = init_py.read_text(encoding="utf-8")
        if "__version__" in txt:
            return init_py
    return None


def read_init_version(init_py: Path) -> str:
    text = init_py.read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*"([^"]+)"\s*$', text, flags=re.M)
    if not m:
        raise ValueError(f"Could not find __version__ in {init_py}")
    return m.group(1)


def tag_exists(tag: str) -> bool:
    try:
        run("git", "rev-parse", tag)
        return True
    except subprocess.CalledProcessError:
        return False


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: python scripts/tag_on_merge.py <before_sha> <after_sha>", file=sys.stderr)
        return 2

    before, after = argv[1], argv[2]

    # Ensure we are in repo root
    os.chdir(REPO_ROOT)

    changed = run("git", "diff", "--name-only", before, after) if before != after else ""

    pkgs: set[str] = set()
    for line in changed.splitlines():
        m = re.match(r"^([^/]+)/pyproject\.toml$", line.strip())
        if m:
            pkgs.add(m.group(1))

    if not pkgs:
        print("No package pyproject.toml changes detected; nothing to tag.")
        return 0

    for pkg in sorted(pkgs):
        pkg_dir = (REPO_ROOT / pkg).resolve()
        pyproject = pkg_dir / "pyproject.toml"
        if not pyproject.exists():
            continue

        version = read_project_version(pyproject)
        init_py = find_init_with_version(pkg_dir)
        if init_py is not None:
            init_version = read_init_version(init_py)
            if init_version != version:
                raise SystemExit(
                    f"Version mismatch for {pkg}: pyproject={version} init={init_version} ({init_py})"
                )

        tag = f"better-mcps-{pkg}-v{version}"
        if tag_exists(tag):
            print(f"Tag already exists: {tag}")
            continue

        run("git", "tag", "-a", tag, "-m", f"Release {tag}")
        run("git", "push", "origin", tag)
        print(f"Tagged {tag}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
