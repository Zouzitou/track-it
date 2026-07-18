from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class ConfidenceInputs:
    model_score: float
    area_ratio: float = 1.0
    centroid_delta: float = 0.0
    fragmentation: int = 1
    near_scene_cut: bool = False
    duplicate_or_corrupt: bool = False
    touches_frame_boundary: bool = False
    visible: bool = True


def tracking_confidence(values: ConfidenceInputs) -> float:
    if not values.visible:
        return 0.0
    score = float(np.clip(values.model_score, 0, 1)) * 0.55 + 0.45
    score -= min(abs(np.log(max(values.area_ratio, 1e-6))) * 0.16, 0.35)
    score -= min(values.centroid_delta * 0.15, 0.25)
    score -= min(max(0, values.fragmentation - 1) * 0.05, 0.2)
    score -= 0.2 if values.near_scene_cut else 0
    score -= 0.3 if values.duplicate_or_corrupt else 0
    score -= 0.08 if values.touches_frame_boundary else 0
    return float(np.clip(score, 0, 1))


def confidence_band(value: float) -> str:
    return "good" if value >= 0.75 else "review" if value >= 0.45 else "bad"
