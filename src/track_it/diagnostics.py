from __future__ import annotations

import json
import platform
import subprocess
from typing import Any

import psutil
import torch

from track_it.constants import ASSET_ROOT
from track_it.media.ffmpeg import find_ffmpeg


def collect_diagnostics(*, redact: bool = True) -> str:
    ffmpeg = find_ffmpeg()[0]
    ffmpeg_line = "not found"
    if ffmpeg:
        try:
            result = subprocess.run(
                [ffmpeg, "-version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                check=False,
            )
            ffmpeg_line = result.stdout.splitlines()[0] if result.stdout else "found"
        except subprocess.TimeoutExpired:
            ffmpeg_line = "timed out"
    data: dict[str, Any] = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu_count": psutil.cpu_count(),
        "memory_gb": round(psutil.virtual_memory().total / 2**30, 2),
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "cuda_memory_gb": round(torch.cuda.get_device_properties(0).total_memory / 2**30, 2)
        if torch.cuda.is_available()
        else None,
        "ffmpeg": ffmpeg_line,
        "material_symbols": len(list((ASSET_ROOT / "icons" / "material-symbols").glob("*.svg"))),
        "host_grotesk": (ASSET_ROOT / "fonts" / "HostGrotesk-Variable.ttf").exists(),
        "privacy": "No telemetry, analytics, account, or upload endpoint.",
    }
    if not redact:
        data["ffmpeg_path"] = ffmpeg
    return json.dumps(data, indent=2)


def self_test() -> tuple[bool, list[str]]:
    results: list[str] = []
    tensor = torch.tensor([1.0, 2.0]) * 2
    ok = bool(torch.equal(tensor, torch.tensor([2.0, 4.0])))
    results.append("PASS tensor operation" if ok else "FAIL tensor operation")
    if torch.cuda.is_available():
        try:
            with torch.autocast("cuda", dtype=torch.float16):
                value = torch.ones(4, device="cuda") * 2
            torch.cuda.synchronize()
            ok &= bool(value.sum().item() == 8)
            results.append(f"PASS CUDA autocast ({torch.cuda.get_device_name(0)})")
        except RuntimeError as exc:
            ok = False
            results.append(f"FAIL CUDA autocast: {exc}")
    else:
        results.append("SKIP CUDA autocast: CUDA is unavailable to PyTorch")
    ffmpeg = find_ffmpeg()[0]
    ok &= ffmpeg is not None
    results.append("PASS FFmpeg found" if ffmpeg else "FAIL FFmpeg not found")
    assets = [
        (ASSET_ROOT / "fonts" / "HostGrotesk-Variable.ttf"),
        (ASSET_ROOT / "icons" / "material-symbols" / "folder_open.svg"),
    ]
    assets_ok = all(path.exists() and path.stat().st_size for path in assets)
    ok &= assets_ok
    results.append("PASS offline fonts/icons" if assets_ok else "FAIL offline fonts/icons")
    return ok, results
