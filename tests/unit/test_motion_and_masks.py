from __future__ import annotations

import numpy as np

from track_it.domain.confidence import ConfidenceInputs, confidence_band, tracking_confidence
from track_it.domain.models import PostprocessingSettings
from track_it.masking.processing import combined_label_map, process_mask
from track_it.motion.transforms import derive_transform, smooth_transforms


def test_rectangle_transform_and_rotation_continuity() -> None:
    mask = np.zeros((80, 100), dtype=bool)
    mask[20:40, 30:70] = True
    value = derive_transform(mask, 0, 0.0, reference_area=800)
    assert value.visible
    assert value.aabb == (30.0, 20.0, 69.0, 39.0)
    assert value.centroid_x == 49.5
    assert value.scale == 1.0
    assert value.rotation is not None
    continued = derive_transform(mask, 1, 0.04, previous_rotation=value.rotation + 180)
    assert abs((continued.rotation or 0) - (value.rotation + 180)) <= 90


def test_empty_and_circular_masks_never_emit_nonfinite() -> None:
    empty = derive_transform(np.zeros((4, 4), bool), 0, 0)
    assert not empty.visible and empty.rotation is None
    yy, xx = np.ogrid[:51, :51]
    circle = (xx - 25) ** 2 + (yy - 25) ** 2 <= 10**2
    value = derive_transform(circle, 1, 0.1, previous_rotation=32)
    assert value.rotation == 32
    assert value.raw_confidence < 1


def test_smoothing_does_not_cross_scene_cut() -> None:
    masks = []
    for frame, x in enumerate((2, 3, 4, 30, 31, 32)):
        mask = np.zeros((20, 50), bool)
        mask[4:8, x : x + 4] = True
        masks.append(derive_transform(mask, frame, frame / 25))
    result = smooth_transforms(masks, {3})
    assert result[2].centroid_x < 10
    assert result[3].centroid_x > 25


def test_processing_preserves_raw_and_combines_deterministically() -> None:
    raw = np.zeros((10, 10), bool)
    raw[3:7, 3:7] = True
    processed = process_mask(raw, PostprocessingSettings(grow_shrink=1))
    assert processed.sum() > raw.sum()
    assert raw.sum() == 16
    labels, mapping = combined_label_map({"b": raw, "a": processed}, {"a": 0.9, "b": 0.8}, ["b"])
    assert labels.max() == 2
    assert mapping[2] == "b"


def test_confidence_bands() -> None:
    good = tracking_confidence(ConfidenceInputs(model_score=0.95))
    bad = tracking_confidence(
        ConfidenceInputs(model_score=0.4, near_scene_cut=True, duplicate_or_corrupt=True)
    )
    assert confidence_band(good) == "good"
    assert confidence_band(bad) == "bad"
