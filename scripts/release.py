"""Release utilities for better-mcps.

Implements a minimal subset of the modelcontextprotocol/servers release flow,
adapted to this repo's layout:

- Each package lives at <pkg>/pyproject.toml (e.g. filesystem/pyproject.toml)
- Each package has a __version__ in <pkg>/src/<import_pkg>/__init__.py
- Tags are of the form: better-mcps-<pkg>-vX.Y.Z

This script supports:
- Detecting changed packages since their last tag
- Deriving semver bumps from Conventional Commits
- Applying version bumps + tagging
- Creating GitHub releases for latest tags (manual gating)

No third-party deps (no click) to keep it simple.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal


REPO_ROOT = Path(__file__).resolve().parents[1]


SemverBump = Literal["major", "minor", "patch", "none"]


@dataclass(frozen=True)
class Package:
    name: str  # directory name, e.g. "filesystem"
    path: Path  # absolute path to package dir

    @property
    def tag_prefix(self) -> str:
        return f"better-mcps-{self.name}-v"


SEMVER_RE = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")


def run(*args: str, cwd: Path | None = None) -> str:
    out = subprocess.check_output(list(args), cwd=cwd, stderr=subprocess.STDOUT)
    return out.decode("utf-8").strip()


def list_packages() -> list[Package]:
    pkgs: list[Package] = []
    for pyproject in REPO_ROOT.glob("*/pyproject.toml"):
        # Skip repo-level pyproject.toml
        if pyproject.parent == REPO_ROOT:
            continue
        pkgs.append(Package(name=pyproject.parent.name, path=pyproject.parent.resolve()))
    pkgs.sort(key=lambda p: p.name)
    return pkgs


def latest_tag_for(pkg: Package) -> str | None:
    # Return most recent tag matching prefix.
    try:
        return run("git", "tag", "--list", f"{pkg.tag_prefix}*", "--sort=-creatordate").splitlines()[
            0
        ]
    except Exception:
        return None


def git_range_since(tag: str | None) -> str:
    if not tag:
        return "HEAD"
    return f"{tag}..HEAD"


def changed_files_since(tag: str | None) -> list[str]:
    rng = git_range_since(tag)
    if rng == "HEAD":
        # First release: consider everything.
        return run("git", "ls-files").splitlines()
    return run("git", "diff", "--name-only", rng).splitlines()


def package_changed(pkg: Package, tag: str | None) -> bool:
    prefix = f"{pkg.name}/"
    for f in changed_files_since(tag):
        if f.startswith(prefix):
            return True
    return False


def conventional_bump_from_commits(tag: str | None, pkg: Package) -> SemverBump:
    """Compute bump based on Conventional Commits affecting pkg.

    Rules:
    - any BREAKING CHANGE or type! -> major
    - any feat -> minor
    - any fix -> patch
    - else none

    Only considers commits that touch files under <pkg>/.
    """

    # Collect commits since tag, with subjects and bodies.
    rng = git_range_since(tag)

    # Find commits that touched the package.
    if tag is None:
        commit_list = run("git", "rev-list", "HEAD").splitlines()
    else:
        commit_list = run("git", "rev-list", rng).splitlines()

    bump: SemverBump = "none"

    for sha in commit_list:
        # Check if this commit touched package path
        touched = run("git", "show", "--name-only", "--pretty=format:", sha).splitlines()
        if not any(p.startswith(f"{pkg.name}/") for p in touched if p):
            continue

        subject = run("git", "show", "-s", "--format=%s", sha)
        body = run("git", "show", "-s", "--format=%b", sha)

        # breaking
        if "BREAKING CHANGE" in body or re.match(r"^[a-zA-Z]+\(.+\)!:|^[a-zA-Z]+!:", subject):
            return "major"

        # feat
        if subject.startswith("feat"):
            bump = "minor" if bump in ("none", "patch", "minor") else bump
            continue

        # fix
        if subject.startswith("fix"):
            if bump == "none":
                bump = "patch"

    return bump


def parse_semver(v: str) -> tuple[int, int, int]:
    m = SEMVER_RE.match(v)
    if not m:
        raise ValueError(f"Invalid semver: {v}")
    return int(m.group("major")), int(m.group("minor")), int(m.group("patch"))


def bump_version(v: str, bump: SemverBump) -> str:
    major, minor, patch = parse_semver(v)
    if bump == "none":
        return v
    if bump == "major":
        return f"{major+1}.0.0"
    if bump == "minor":
        return f"{major}.{minor+1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch+1}"
    raise ValueError(bump)


def version_from_tag(tag: str, pkg: Package) -> str:
    if not tag.startswith(pkg.tag_prefix):
        raise ValueError(f"Tag {tag} does not match {pkg.tag_prefix}")
    return tag[len(pkg.tag_prefix) :]


def read_pyproject_version(pyproject: Path) -> str:
    txt = pyproject.read_text(encoding="utf-8")
    m = re.search(r"^version\s*=\s*\"([^\"]+)\"\s*$", txt, flags=re.MULTILINE)
    if not m:
        raise ValueError(f"Could not find version in {pyproject}")
    return m.group(1)


def write_pyproject_version(pyproject: Path, new_version: str) -> None:
    txt = pyproject.read_text(encoding="utf-8")
    new_txt, n = re.subn(
        r"^version\s*=\s*\"([^\"]+)\"\s*$",
        f'version = "{new_version}"',
        txt,
        flags=re.MULTILINE,
    )
    if n != 1:
        raise ValueError(f"Expected to replace exactly 1 version in {pyproject}, replaced {n}")
    pyproject.write_text(new_txt, encoding="utf-8")


def find_init_version_file(pkg: Package) -> Path | None:
    # Prefer src/*/__init__.py inside the package.
    src = pkg.path / "src"
    if not src.exists():
        return None
    candidates = list(src.glob("*/__init__.py"))
    # choose one that contains __version__
    for c in candidates:
        if "__version__" in c.read_text(encoding="utf-8"):
            return c
    return None


def write_init_version(init_py: Path, new_version: str) -> None:
    txt = init_py.read_text(encoding="utf-8")
    new_txt, n = re.subn(
        r"^__version__\s*=\s*\"([^\"]+)\"\s*$",
        f'__version__ = "{new_version}"',
        txt,
        flags=re.MULTILINE,
    )
    if n != 1:
        raise ValueError(f"Expected to replace exactly 1 __version__ in {init_py}, replaced {n}")
    init_py.write_text(new_txt, encoding="utf-8")


def cmd_detect_changed(args: argparse.Namespace) -> int:
    pkgs = list_packages()
    changed: list[str] = []
    for pkg in pkgs:
        tag = latest_tag_for(pkg)
        if package_changed(pkg, tag):
            changed.append(pkg.name)
    print(json.dumps(changed))
    return 0


def cmd_tag_main(args: argparse.Namespace) -> int:
    # For each changed package, compute bump and tag.
    pkgs = list_packages()

    # Plan changes first.
    planned: list[tuple[Package, str]] = []  # (pkg, next_version)
    for pkg in pkgs:
        last_tag = latest_tag_for(pkg)
        if not package_changed(pkg, last_tag):
            continue

        bump = conventional_bump_from_commits(last_tag, pkg)
        if bump == "none":
            # Default to patch if there are changes but no conventional commits.
            bump = "patch"

        pyproject = pkg.path / "pyproject.toml"
        current = read_pyproject_version(pyproject)
        next_v = bump_version(current, bump)
        planned.append((pkg, next_v))

    if not planned:
        print("No packages changed; nothing to tag.")
        return 0

    # Apply file updates.
    for pkg, next_v in planned:
        pyproject = pkg.path / "pyproject.toml"
        write_pyproject_version(pyproject, next_v)
        init_py = find_init_version_file(pkg)
        if init_py:
            write_init_version(init_py, next_v)

        run("git", "add", str(pyproject.relative_to(REPO_ROOT)))
        if init_py:
            run("git", "add", str(init_py.relative_to(REPO_ROOT)))

    # Single commit for all version bumps.
    msg_parts = ", ".join([f"{pkg.name} v{v}" for pkg, v in planned])
    run("git", "commit", "-m", f"chore(release): {msg_parts}")
    run("git", "push", "origin", "HEAD:main")

    # Tag and push each package tag.
    for pkg, next_v in planned:
        tag_name = f"{pkg.tag_prefix}{next_v}"
        run("git", "tag", "-a", tag_name, "-m", f"Release {tag_name}")
        run("git", "push", "origin", tag_name)

    return 0


def cmd_create_releases(args: argparse.Namespace) -> int:
    """Create GitHub Releases for latest tags of each package.

    Requires GH_TOKEN env var.
    """

    pkgs = list_packages()
    for pkg in pkgs:
        tag = latest_tag_for(pkg)
        if not tag:
            continue

        # If release exists, skip.
        # gh release view exits non-zero if missing.
        try:
            run("gh", "release", "view", tag)
            print(f"Release exists for {tag}, skipping")
            continue
        except subprocess.CalledProcessError:
            pass

        run(
            "gh",
            "release",
            "create",
            tag,
            "--title",
            f"{pkg.name} {version_from_tag(tag, pkg)}",
            "--notes",
            f"Automated release for {tag}",
        )
        print(f"Created release {tag}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("detect-changed")

    sub.add_parser("tag-main")

    sub.add_parser("create-releases")

    args = parser.parse_args(argv)

    if args.cmd == "detect-changed":
        return cmd_detect_changed(args)
    if args.cmd == "tag-main":
        return cmd_tag_main(args)
    if args.cmd == "create-releases":
        return cmd_create_releases(args)

    raise AssertionError(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main())
