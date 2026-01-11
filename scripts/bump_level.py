#!/usr/bin/env python3
"""Compute semver bump level for a package using Conventional Commits.

Rules:
- major if commit has 'BREAKING CHANGE' in body OR subject contains '!:' (e.g. feat!:)
- minor if any subject starts with 'feat'
- patch if any subject starts with 'fix' or 'perf'
- none otherwise

Important: we only consider commits that touch files under <package>/.

Usage:
  python scripts/bump_level.py <package> <since_ref>

Examples:
  python scripts/bump_level.py filesystem better-mcps-filesystem-v0.3.0
  python scripts/bump_level.py filesystem HEAD~50

Outputs one of: none|patch|minor|major
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, cwd: Path | None = None) -> str:
    out = subprocess.check_output(list(args), cwd=cwd, stderr=subprocess.STDOUT)
    return out.decode("utf-8").strip()


def commits_since(since_ref: str) -> list[str]:
    if since_ref == "" or since_ref.lower() == "none":
        return run("git", "rev-list", "HEAD").splitlines()
    return run("git", "rev-list", f"{since_ref}..HEAD").splitlines()


def touched_package(sha: str, package: str) -> bool:
    files = run("git", "show", "--name-only", "--pretty=format:", sha).splitlines()
    prefix = f"{package}/"
    return any(f.startswith(prefix) for f in files if f)


def subject_body(sha: str) -> tuple[str, str]:
    subject = run("git", "show", "-s", "--format=%s", sha)
    body = run("git", "show", "-s", "--format=%b", sha)
    return subject, body


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: python scripts/bump_level.py <package> <since_ref>", file=sys.stderr)
        return 2

    package, since_ref = argv[1], argv[2]

    # Ensure we're in repo root.
    os_cwd = Path.cwd().resolve()
    try:
        import os

        os.chdir(REPO_ROOT)

        bump = "none"
        for sha in commits_since(since_ref):
            if not touched_package(sha, package):
                continue

            subj, body = subject_body(sha)

            if "BREAKING CHANGE" in body or re.match(r"^[a-zA-Z]+\(.+\)!:|^[a-zA-Z]+!:", subj):
                print("major")
                return 0

            if subj.startswith("feat"):
                bump = "minor"
                continue

            if subj.startswith("fix") or subj.startswith("perf"):
                if bump == "none":
                    bump = "patch"

        print(bump)
        return 0
    finally:
        try:
            import os

            os.chdir(os_cwd)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
