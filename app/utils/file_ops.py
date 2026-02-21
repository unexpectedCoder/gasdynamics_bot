import asyncio
import json
import shutil
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


async def listdir(path: str | Path) -> list[Path]:
    return await asyncio.to_thread(lambda: list(Path(path).iterdir()))


async def listdir_names(path: str | Path) -> list[str]:
    return await asyncio.to_thread(lambda: [p.name for p in Path(path).iterdir()])


async def listdir_names_by_mtime(path: str | Path, reverse: bool = False) -> list[str]:
    def _list() -> list[str]:
        entries = list(Path(path).iterdir())
        entries.sort(key=lambda p: p.stat().st_mtime, reverse=reverse)
        return [p.name for p in entries]

    return await asyncio.to_thread(_list)


async def exists(path: str | Path) -> bool:
    return await asyncio.to_thread(Path(path).exists)


async def is_dir(path: str | Path) -> bool:
    return await asyncio.to_thread(Path(path).is_dir)


async def mkdir(
    path: str | Path, parents: bool = False, exist_ok: bool = False
) -> None:
    await asyncio.to_thread(Path(path).mkdir, parents=parents, exist_ok=exist_ok)


async def remove(path: str | Path) -> None:
    await asyncio.to_thread(Path(path).unlink)


async def move(src: str | Path, dst: str | Path) -> None:
    await asyncio.to_thread(shutil.move, src, dst)


async def read_json(path: str | Path, encoding: str = "utf-8") -> Any:
    def _read() -> Any:
        with open(path, "r", encoding=encoding) as f:
            return json.load(f)

    return await asyncio.to_thread(_read)


async def write_json(
    path: str | Path,
    data: Any,
    encoding: str = "utf-8",
    ensure_ascii: bool = False,
    indent: int | None = 4,
) -> None:
    def _write() -> None:
        with open(path, "w", encoding=encoding) as f:
            json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)

    await asyncio.to_thread(_write)


async def read_excel(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    return await asyncio.to_thread(pd.read_excel, path, **kwargs)


async def filter_files(
    entries: Iterable[str],
    startswith: str | None = None,
    endswith: str | None = None,
) -> list[str]:
    def _match(name: str) -> bool:
        if startswith is not None and not name.startswith(startswith):
            return False
        if endswith is not None and not name.endswith(endswith):
            return False
        return True

    return await asyncio.to_thread(lambda: [e for e in entries if _match(e)])
