from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import aiofiles

if TYPE_CHECKING:
    from pathlib import Path


async def write_file(path: Path, data: dict[str, Any] | list[dict[str, Any]]) -> None:
    """
    Write data to a file asynchronously.

    :param path: The path to the file.
    :param data: The data to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(path, mode="w", encoding="utf-8") as f:
        await f.write(json.dumps(data, indent=4, sort_keys=True, ensure_ascii=False))
