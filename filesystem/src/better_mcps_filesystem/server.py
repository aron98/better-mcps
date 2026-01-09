from __future__ import annotations

import argparse
import sys
from pathlib import Path
from stat import filemode
from typing import Literal

from fastmcp import FastMCP

mcp: FastMCP = FastMCP("better-mcps-filesystem")

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
def list_dir(
    path: str,
    max: int = 200,
    format: Literal["text", "json"] = "text",
    detailed: bool = False,
) -> str | dict:
    """List directory entries for an absolute directory path under an allowed root.

    Defaults are intentionally conservative to avoid dumping extremely large
    directory listings into context.

    Args:
        path: Absolute directory path to list.
        max: Maximum number of entries to return. Clamped to 2000 server-side.
        format: "text" (default) or "json".
        detailed: If true, include permissions and size.
    """

    p = _resolve_allowed_abs_path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    if not p.is_dir():
        raise NotADirectoryError(str(p))

    return _list_dir_impl(p, max=max, format=format, detailed=detailed)


def _list_dir_impl(
    directory: Path,
    *,
    max: int = 200,
    format: Literal["text", "json"] = "text",
    detailed: bool = False,
) -> str | dict:
    """Implementation for list_dir.

    This is separated from the FastMCP tool wrapper so it can be unit tested.
    """

    if not directory.exists():
        raise FileNotFoundError(str(directory))
    if not directory.is_dir():
        raise NotADirectoryError(str(directory))

    max_allowed = 2000
    try:
        max_n = int(max)
    except Exception as e:
        raise ValueError("max must be an integer") from e
    if max_n < 0:
        raise ValueError("max must be >= 0")
    max_n = min(max_n, max_allowed)

    # Collect entries (including dotfiles), sort by name.
    entries: list[tuple[str, int, int]] = []
    for child in directory.iterdir():
        try:
            st = child.lstat()
        except FileNotFoundError:
            # Entry disappeared between iterdir and stat.
            continue
        entries.append((child.name, st.st_mode, st.st_size))

    entries.sort(key=lambda t: t[0])
    total = len(entries)
    shown = entries[:max_n]
    truncated = total > len(shown)

    if format == "text":
        if detailed:
            lines = [f"{filemode(mode)} {size} {name}" for name, mode, size in shown]
        else:
            lines = [name for name, _mode, _size in shown]

        if truncated:
            lines.append(
                f"... truncated (showing {len(shown)} of {total}). "
                f"Increase max to see more (max {max_allowed})."
            )

        return "\n".join(lines)

    if format == "json":
        if detailed:
            entries_json = [
                {"name": name, "mode": filemode(mode), "size": size}
                for name, mode, size in shown
            ]
        else:
            entries_json = [{"name": name} for name, _mode, _size in shown]

        return {
            "entries": entries_json,
            "total": total,
            "shown": len(shown),
            "truncated": truncated,
            "max_allowed": max_allowed,
        }

    raise ValueError('format must be "text" or "json"')


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
