from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from track_it.utils.paths import safe_filename


def export_mask_png(
    path: Path, mask: np.ndarray, *, gray16: bool = False, inverted: bool = False
) -> Path:
    data = np.asarray(mask, dtype=bool)
    if inverted:
        data = ~data
    maximum = 65535 if gray16 else 255
    array = np.where(data, maximum, 0).astype(np.uint16 if gray16 else np.uint8)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.png")
    Image.fromarray(array).save(temporary, format="PNG")
    temporary.replace(path)
    return path


def export_transparent_png(
    path: Path, rgb: np.ndarray, mask: np.ndarray, *, premultiplied: bool = False
) -> Path:
    color = np.asarray(rgb, dtype=np.uint8)[..., :3].copy()
    alpha = np.asarray(mask, dtype=bool).astype(np.uint8) * 255
    if premultiplied:
        color = (color.astype(np.uint16) * alpha[..., None] // 255).astype(np.uint8)
    rgba = np.dstack((color, alpha))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.png")
    Image.fromarray(rgba).save(temporary, format="PNG")
    temporary.replace(path)
    return path


def deterministic_mask_name(
    object_name: str, object_id: str, frame_index: int, bit_depth: int = 8
) -> str:
    return f"{safe_filename(object_name)}_{object_id[:8]}_{frame_index:08d}_gray{bit_depth}.png"
