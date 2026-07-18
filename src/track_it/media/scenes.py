from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage


@dataclass(frozen=True, slots=True)
class SceneScore:
    frame_index: int
    luma_mad: float
    histogram_distance: float
    edge_change: float
    strong: bool


def _features(frame: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    rgb = np.asarray(frame, dtype=np.float32)[..., :3] / 255.0
    luma = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
    hist = np.concatenate(
        [np.histogram(rgb[..., channel], 32, (0, 1), density=True)[0] for channel in range(3)]
    )
    edges = np.hypot(ndimage.sobel(luma, axis=0), ndimage.sobel(luma, axis=1))
    return luma, hist / max(hist.sum(), 1e-9), float((edges > 0.15).mean())


def detect_scene_cuts(frames: list[np.ndarray]) -> list[SceneScore]:
    if len(frames) < 2:
        return []
    features = [_features(frame) for frame in frames]
    scores: list[SceneScore] = []
    for index in range(1, len(features)):
        previous, current = features[index - 1], features[index]
        mad = float(np.mean(np.abs(current[0] - previous[0])))
        histogram = float(0.5 * np.abs(current[1] - previous[1]).sum())
        edge = abs(current[2] - previous[2])
        combined = 0.50 * mad + 0.35 * histogram + 0.15 * min(edge * 4, 1)
        scores.append(
            SceneScore(
                index, mad, histogram, edge, combined >= 0.26 and (mad >= 0.12 or histogram >= 0.32)
            )
        )
    return scores
