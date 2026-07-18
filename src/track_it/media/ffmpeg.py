from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from track_it.errors import ExportProcessError


def find_ffmpeg() -> tuple[str | None, str | None]:
    return shutil.which("ffmpeg"), shutil.which("ffprobe")


def run_process(
    argv: list[str], *, timeout: float | None = None
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
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
        [executable, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]
    )
    data: dict[str, Any] = json.loads(result.stdout)
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
