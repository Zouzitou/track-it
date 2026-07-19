from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_write_bytes(path: Path, data: bytes, *, backup: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    backup_path = path.with_suffix(path.suffix + ".bak")
    moved_to_backup = False
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if backup and path.exists():
            path.replace(backup_path)
            moved_to_backup = True
        try:
            temporary.replace(path)
        except OSError:
            if moved_to_backup and backup_path.exists() and not path.exists():
                backup_path.replace(path)
            raise
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_text(path: Path, value: str, *, backup: bool = False) -> None:
    atomic_write_bytes(path, value.encode("utf-8"), backup=backup)
