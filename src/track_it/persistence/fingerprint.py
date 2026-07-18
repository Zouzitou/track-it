from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

_BLOCK = 4 * 1024 * 1024


def source_fingerprint(path: Path, stream_metadata: dict[str, Any] | None = None) -> str:
    stat = path.stat()
    digest = hashlib.sha256()
    digest.update(str(stat.st_size).encode())
    with path.open("rb") as handle:
        digest.update(handle.read(_BLOCK))
        if stat.st_size > _BLOCK * 2:
            handle.seek(max(0, stat.st_size // 2 - _BLOCK // 2))
            digest.update(handle.read(_BLOCK))
        if stat.st_size > _BLOCK:
            handle.seek(max(0, stat.st_size - _BLOCK))
            digest.update(handle.read(_BLOCK))
    digest.update(json.dumps(stream_metadata or {}, sort_keys=True, separators=(",", ":")).encode())
    return digest.hexdigest()
