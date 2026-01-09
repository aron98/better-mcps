from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _git_diff_names(base: str, head: str) -> list[str]:
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", base, head], stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        sys.stderr.write(e.output.decode("utf-8", errors="replace"))
        raise

    return [line for line in out.decode("utf-8").splitlines() if line.strip()]


def _load_modules(manifest_path: Path) -> list[str]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Manifest must be a JSON object")

    # Keys are module directory names.
    return [str(k) for k in data.keys()]


def _is_under_any_module(path: str, modules: list[str]) -> bool:
    # Any change outside the known module directories forces a full re-check.
    return any(path.startswith(f"{m}/") for m in modules)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=".release-please-manifest.json")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)

    args = parser.parse_args(argv)

    manifest = Path(args.manifest)
    if not manifest.exists():
        raise SystemExit(f"manifest not found: {manifest}")

    all_modules = _load_modules(manifest)
    changed_files = _git_diff_names(args.base, args.head)

    if not changed_files:
        sys.stdout.write("[]")
        return 0

    # Rule:
    # - If ANY changed file is outside the set of module directories, run CI for ALL modules.
    # - Otherwise, run CI only for the modules that changed.
    test_all = any(not _is_under_any_module(p, all_modules) for p in changed_files)

    if test_all:
        selected = all_modules
    else:
        selected: list[str] = []
        for m in all_modules:
            prefix = f"{m}/"
            if any(p.startswith(prefix) for p in changed_files):
                selected.append(m)

    sys.stdout.write(json.dumps(selected))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
