from __future__ import annotations

import os
from pathlib import Path


def atomic_write_bytes(path: Path, data: bytes, *, backup: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if backup and path.exists():
            backup_path = path.with_suffix(path.suffix + ".bak")
            path.replace(backup_path)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_text(path: Path, value: str, *, backup: bool = False) -> None:
    atomic_write_bytes(path, value.encode("utf-8"), backup=backup)
