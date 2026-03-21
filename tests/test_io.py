from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from catholic_mass_readings._io import write_file

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.asyncio
async def test_write_file_dict(tmp_path: Path) -> None:
    path = tmp_path / "output.json"
    data: dict[str, Any] = {"key": "value", "number": 42}
    await write_file(path, data)
    content = json.loads(path.read_text(encoding="utf-8"))
    assert content == data


@pytest.mark.asyncio
async def test_write_file_list(tmp_path: Path) -> None:
    path = tmp_path / "output.json"
    data: list[dict[str, Any]] = [{"a": 1}, {"b": 2}]
    await write_file(path, data)
    content = json.loads(path.read_text(encoding="utf-8"))
    assert content == data


@pytest.mark.asyncio
async def test_write_file_creates_parent_dir(tmp_path: Path) -> None:
    path = tmp_path / "new_dir" / "output.json"
    await write_file(path, {"key": "value"})
    assert path.exists()


@pytest.mark.asyncio
async def test_write_file_sorted_keys(tmp_path: Path) -> None:
    path = tmp_path / "output.json"
    data: dict[str, Any] = {"z_key": 1, "a_key": 2}
    await write_file(path, data)
    raw = path.read_text(encoding="utf-8")
    assert raw.index('"a_key"') < raw.index('"z_key"')


@pytest.mark.asyncio
async def test_write_file_indented(tmp_path: Path) -> None:
    path = tmp_path / "output.json"
    await write_file(path, {"key": "value"})
    raw = path.read_text(encoding="utf-8")
    assert "    " in raw


@pytest.mark.asyncio
async def test_write_file_unicode(tmp_path: Path) -> None:
    """Non-ASCII characters should not be escaped."""
    path = tmp_path / "output.json"
    data: dict[str, Any] = {"text": "café résumé"}
    await write_file(path, data)
    raw = path.read_text(encoding="utf-8")
    assert "café résumé" in raw
