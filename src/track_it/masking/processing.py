from __future__ import annotations

import numpy as np
from scipy import ndimage

from track_it.domain.models import PostprocessingSettings


def process_mask(raw: np.ndarray, settings: PostprocessingSettings) -> np.ndarray:
    """Apply nondestructive postprocessing to a copy of the immutable raw mask."""
    result = np.asarray(raw, dtype=bool).copy()
    if settings.grow_shrink > 0:
        result = ndimage.binary_dilation(result, iterations=settings.grow_shrink)
    elif settings.grow_shrink < 0:
        result = ndimage.binary_erosion(result, iterations=-settings.grow_shrink)
    if settings.fill_holes:
        result = ndimage.binary_fill_holes(result)
    if settings.minimum_island:
        labels, count = ndimage.label(result)
        sizes = np.bincount(labels.ravel())
        keep = sizes >= settings.minimum_island
        keep[0] = False
        result = keep[labels] if count else result
    if settings.edge_smoothing:
        sigma = max(0.1, settings.edge_smoothing * 2.0)
        result = ndimage.gaussian_filter(result.astype(float), sigma=sigma) >= 0.5
    return np.asarray(result, dtype=bool)


def combined_label_map(
    masks: dict[str, np.ndarray], confidence: dict[str, float], corrected_order: list[str]
) -> tuple[np.ndarray, dict[int, str]]:
    if not masks:
        raise ValueError("At least one mask is required")
    shape = next(iter(masks.values())).shape
    labels = np.zeros(shape, dtype=np.uint16)
    mapping: dict[int, str] = {}
    corrected_rank = {object_id: index for index, object_id in enumerate(corrected_order)}
    ordered = sorted(
        masks,
        key=lambda oid: (
            corrected_rank.get(oid, -1),
            confidence.get(oid, 0.0),
            -int(np.count_nonzero(masks[oid])),
            oid,
        ),
    )
    for value, object_id in enumerate(ordered, start=1):
        mask = np.asarray(masks[object_id], dtype=bool)
        if mask.shape != shape:
            raise ValueError("All masks must share a shape")
        labels[mask] = value
        mapping[value] = object_id
    return labels, mapping
