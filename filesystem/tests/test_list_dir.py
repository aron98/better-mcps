from __future__ import annotations

from pathlib import Path

import pytest

from better_mcps_filesystem.server import _list_dir_impl


def test_list_dir_impl_text_basic(tmp_path: Path) -> None:
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / ".hidden").write_text("h", encoding="utf-8")
    (tmp_path / "adir").mkdir()

    out = _list_dir_impl(tmp_path, format="text", detailed=False)
    lines = out.splitlines()

    # Sorted by name, includes dotfiles.
    assert lines[:3] == [".hidden", "adir", "b.txt"]


def test_list_dir_impl_json_detailed_truncation(tmp_path: Path) -> None:
    for i in range(5):
        (tmp_path / f"f{i}.txt").write_text("x", encoding="utf-8")

    out = _list_dir_impl(tmp_path, format="json", detailed=True, max=2)

    assert out["shown"] == 2
    assert out["total"] == 5
    assert out["truncated"] is True
    assert out["max_allowed"] == 2000

    entry = out["entries"][0]
    assert set(entry.keys()) == {"name", "mode", "size"}


def test_list_dir_impl_max_clamped(tmp_path: Path) -> None:
    for i in range(3):
        (tmp_path / f"f{i}.txt").write_text("x", encoding="utf-8")

    out = _list_dir_impl(tmp_path, format="json", detailed=False, max=10_000)
    assert out["shown"] == 3


def test_list_dir_impl_invalid_format(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _list_dir_impl(tmp_path, format="nope")  # type: ignore[arg-type]
