from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from track_it.export.data import export_motion_csv, export_motion_json
from track_it.export.images import deterministic_mask_name, export_mask_png, export_transparent_png
from track_it.media.ffmpeg import ffv1_mask_argv
from track_it.media.scenes import detect_scene_cuts
from track_it.motion.transforms import derive_transform
from track_it.utils.paths import safe_filename


def test_scene_cut_detects_black_to_white() -> None:
    frames = [
        np.zeros((32, 32, 3), np.uint8),
        np.zeros((32, 32, 3), np.uint8),
        np.full((32, 32, 3), 255, np.uint8),
    ]
    scores = detect_scene_cuts(frames)
    assert scores[-1].strong


def test_exports_png_transparency_and_motion(tmp_path: Path) -> None:
    mask = np.zeros((8, 9), bool)
    mask[2:6, 3:7] = True
    export_mask_png(tmp_path / "mask.png", mask, gray16=True)
    assert np.asarray(Image.open(tmp_path / "mask.png")).max() == 65535
    export_transparent_png(tmp_path / "alpha.png", np.full((8, 9, 3), 120, np.uint8), mask)
    assert Image.open(tmp_path / "alpha.png").mode == "RGBA"
    transform = derive_transform(mask, 0, 0.0)
    export_motion_json(tmp_path / "motion.json", {"id": [transform]}, {"width": 9, "height": 8})
    export_motion_csv(tmp_path / "motion.csv", {"id": [transform]}, {"id": "Subject"})
    assert json.loads((tmp_path / "motion.json").read_text())["objects"]["id"][0]["visible"]
    assert "Subject" in (tmp_path / "motion.csv").read_text()


def test_safe_names_and_argv_preserve_user_paths() -> None:
    assert safe_filename("CON") == "object"
    name = deterministic_mask_name('a/b:"c"', "123456789", 7)
    assert "/" not in name and name.endswith("00000007_gray8.png")
    path = Path("Z:/ü emoji 🎬 & quoted/input-%08d.png")
    output = Path("Z:/out & final.mkv")
    argv = ffv1_mask_argv("ffmpeg", path, output, 23.976, False)
    assert str(path) in argv and str(output) in argv
