from __future__ import annotations

import re
from pathlib import Path

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def safe_filename(value: str, fallback: str = "object") -> str:
    cleaned = _ILLEGAL.sub("_", value).strip().rstrip(". ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned or cleaned.upper() in _WINDOWS_RESERVED:
        cleaned = fallback
    return cleaned[:120]


def ensure_project_suffix(path: Path) -> Path:
    return (
        path if path.name.lower().endswith(".trackit") else path.with_name(path.name + ".trackit")
    )
