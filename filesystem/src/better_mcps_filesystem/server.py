from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fastmcp import FastMCP

mcp = FastMCP("Better Filesystem MCP")

# Configured at runtime (in main) from CLI args.
_ALLOWED_ROOTS: list[Path] = []


def _require_allowed_roots() -> list[Path]:
    if not _ALLOWED_ROOTS:
        raise RuntimeError(
            "No allowed roots configured. Start the server with one or more absolute directory paths."
        )
    return _ALLOWED_ROOTS


def _resolve_allowed_abs_path(user_path: str) -> Path:
    """Resolve a user-supplied path.

    Security model:
    - Client MUST pass an absolute path.
    - The path must resolve (incl. symlinks) under one of the allowed roots.
    """

    roots = _require_allowed_roots()

    up = Path(user_path).expanduser()
    if not up.is_absolute():
        raise ValueError("Path must be absolute")

    candidate = up.resolve()

    for root in roots:
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            continue

    raise ValueError("Path is not under an allowed root")


@mcp.tool
def list_dir(path: str) -> list[str]:
    """List directory entries for an absolute directory path under an allowed root."""

    p = _resolve_allowed_abs_path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    if not p.is_dir():
        raise NotADirectoryError(str(p))

    return sorted([child.name for child in p.iterdir()])


@mcp.tool
def read_text_file(path: str) -> str:
    """Read a UTF-8 text file at an absolute path under an allowed root."""

    p = _resolve_allowed_abs_path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    if not p.is_file():
        raise IsADirectoryError(str(p))

    return p.read_text(encoding="utf-8")


@mcp.resource("resource://roots")
def roots_resource() -> list[str]:
    """List the configured allowed roots."""

    return [str(p) for p in _require_allowed_roots()]


def _parse_args(argv: list[str]) -> list[Path]:
    parser = argparse.ArgumentParser(
        prog="better-mcps-filesystem",
        description="FastMCP server exposing filesystem tools scoped to allowed root directories.",
    )
    parser.add_argument(
        "roots",
        nargs="+",
        help="One or more absolute root directories to allow. All tool paths must be under one of these roots.",
    )

    ns = parser.parse_args(argv)

    roots: list[Path] = []
    for raw in ns.roots:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            raise SystemExit(f"Root must be an absolute path: {raw}")
        p = p.resolve()
        if not p.exists():
            raise SystemExit(f"Root does not exist: {p}")
        if not p.is_dir():
            raise SystemExit(f"Root is not a directory: {p}")
        roots.append(p)

    # Deduplicate while preserving order
    deduped: list[Path] = []
    seen: set[Path] = set()
    for r in roots:
        if r not in seen:
            deduped.append(r)
            seen.add(r)

    return deduped


def main(argv: list[str] | None = None) -> None:
    global _ALLOWED_ROOTS

    argv = list(sys.argv[1:] if argv is None else argv)
    _ALLOWED_ROOTS = _parse_args(argv)

    # Default transport is STDIO (ideal for local MCP usage)
    mcp.run()


if __name__ == "__main__":
    main()
