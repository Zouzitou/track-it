from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from track_it.constants import TOOLS_ROOT
from track_it.errors import ExportProcessError


def find_ffmpeg() -> tuple[str | None, str | None]:
    return _find_executable("ffmpeg"), _find_executable("ffprobe")


def _find_executable(name: str) -> str | None:
    suffix = ".exe" if os.name == "nt" else ""
    bundled = TOOLS_ROOT / "ffmpeg" / f"{name}{suffix}"
    return str(bundled) if bundled.is_file() else shutil.which(name)


def run_process(
    argv: list[str], *, timeout: float | None = None
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ExportProcessError("The media process timed out.") from exc
    if result.returncode:
        raise ExportProcessError(
            result.stderr.strip() or f"Process failed with exit code {result.returncode}"
        )
    return result


def probe(path: Path, ffprobe: str | None = None) -> dict[str, Any]:
    executable = ffprobe or find_ffmpeg()[1]
    if not executable:
        raise ExportProcessError(
            "FFmpeg was not found. Install FFmpeg or choose its folder in Settings."
        )
    result = run_process(
        [
            executable,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            "-i",
            str(path),
        ],
        timeout=30,
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ExportProcessError("FFprobe returned invalid media metadata.") from exc
    if not isinstance(data, dict):
        raise ExportProcessError("FFprobe returned invalid media metadata.")
    return data


def ffv1_mask_argv(
    ffmpeg: str, input_pattern: Path, output: Path, fps: float, gray16: bool
) -> list[str]:
    return [
        ffmpeg,
        "-y",
        "-framerate",
        f"{fps:.8g}",
        "-i",
        str(input_pattern),
        "-an",
        "-c:v",
        "ffv1",
        "-level",
        "3",
        "-pix_fmt",
        "gray16le" if gray16 else "gray",
        str(output),
    ]
