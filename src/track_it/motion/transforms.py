from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from math import atan2, cos, degrees, isfinite, radians, sin

import numpy as np
from scipy.signal import savgol_filter


@dataclass(frozen=True, slots=True)
class MotionTransform:
    frame_index: int
    timestamp: float
    visible: bool
    centroid_x: float | None
    centroid_y: float | None
    width: float
    height: float
    area: int
    scale: float | None
    rotation: float | None
    eccentricity: float | None
    aabb: tuple[float, float, float, float] | None
    corners: tuple[tuple[float, float], ...] | None
    anchor: tuple[float, float] | None
    raw_confidence: float
    smoothed_confidence: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _unwrap_angle(angle: float, previous: float | None) -> float:
    if previous is None:
        return angle
    candidates = (angle - 180.0, angle, angle + 180.0)
    return min(candidates, key=lambda candidate: abs(candidate - previous))


def derive_transform(
    mask: np.ndarray,
    frame_index: int,
    timestamp: float,
    *,
    reference_area: int | None = None,
    previous_rotation: float | None = None,
    model_confidence: float = 1.0,
) -> MotionTransform:
    ys, xs = np.nonzero(np.asarray(mask, dtype=bool))
    area = int(xs.size)
    if area == 0:
        return MotionTransform(
            frame_index,
            timestamp,
            False,
            None,
            None,
            0,
            0,
            area,
            None,
            None,
            None,
            None,
            None,
            None,
            0.0,
            0.0,
        )
    x0, x1, y0, y1 = float(xs.min()), float(xs.max()), float(ys.min()), float(ys.max())
    cx, cy = float(xs.mean()), float(ys.mean())
    width, height = x1 - x0 + 1.0, y1 - y0 + 1.0
    points = np.column_stack((xs - cx, ys - cy)).astype(float)
    rotation: float | None = previous_rotation
    eccentricity = 0.0
    corners: tuple[tuple[float, float], ...] | None = None
    confidence = float(np.clip(model_confidence, 0.0, 1.0))
    if area >= 3 and np.all(np.isfinite(points)):
        covariance = np.cov(points, rowvar=False)
        values, vectors = np.linalg.eigh(covariance)
        order = np.argsort(values)[::-1]
        values = np.maximum(values[order], 0)
        major = vectors[:, order[0]]
        eccentricity = (
            float(np.sqrt(max(0.0, 1.0 - values[1] / values[0]))) if values[0] > 1e-12 else 0.0
        )
        if eccentricity >= 0.2:
            rotation = _unwrap_angle(degrees(atan2(major[1], major[0])), previous_rotation)
        else:
            confidence *= 0.65
        angle = radians(rotation or 0.0)
        axis_x = np.array([cos(angle), sin(angle)])
        axis_y = np.array([-sin(angle), cos(angle)])
        projected_x, projected_y = points @ axis_x, points @ axis_y
        corners_arr = [
            np.array([cx, cy]) + px * axis_x + py * axis_y
            for px, py in (
                (projected_x.min(), projected_y.min()),
                (projected_x.max(), projected_y.min()),
                (projected_x.max(), projected_y.max()),
                (projected_x.min(), projected_y.max()),
            )
        ]
        corners = tuple((float(point[0]), float(point[1])) for point in corners_arr)
    scale = float(np.sqrt(area / reference_area)) if reference_area and reference_area > 0 else 1.0
    finite = all(isfinite(value) for value in (cx, cy, width, height, scale, confidence))
    if not finite:
        raise ValueError("Derived transform contains a non-finite value")
    return MotionTransform(
        frame_index,
        timestamp,
        True,
        cx,
        cy,
        width,
        height,
        area,
        scale,
        rotation,
        eccentricity,
        (x0, y0, x1, y1),
        corners,
        (cx, cy),
        confidence,
        confidence,
    )


def smooth_transforms(
    transforms: list[MotionTransform], scene_cuts: set[int] | None = None, max_gap: int = 3
) -> list[MotionTransform]:
    if not transforms:
        return []
    cuts = scene_cuts or set()
    result = list(transforms)
    segment_start = 0
    boundaries = [i for i, item in enumerate(result) if item.frame_index in cuts and i > 0] + [
        len(result)
    ]
    for segment_end in boundaries:
        segment = result[segment_start:segment_end]
        visible_indices = [i for i, item in enumerate(segment) if item.visible]
        if visible_indices:
            for field in ("centroid_x", "centroid_y", "scale", "rotation", "raw_confidence"):
                values = np.array(
                    [float(getattr(segment[i], field) or 0.0) for i in visible_indices]
                )
                median = np.median(values)
                mad = np.median(np.abs(values - median))
                if mad > 0:
                    values[np.abs(values - median) > 6 * mad] = median
                if len(values) >= 5:
                    window = min(len(values) if len(values) % 2 else len(values) - 1, 9)
                    values = savgol_filter(values, window, min(2, window - 1), mode="interp")
                for local, value in zip(visible_indices, values, strict=True):
                    numeric = float(value)
                    if field == "centroid_x":
                        segment[local] = replace(segment[local], centroid_x=numeric)
                    elif field == "centroid_y":
                        segment[local] = replace(segment[local], centroid_y=numeric)
                    elif field == "scale":
                        segment[local] = replace(segment[local], scale=numeric)
                    elif field == "rotation":
                        segment[local] = replace(segment[local], rotation=numeric)
                    else:
                        segment[local] = replace(
                            segment[local], smoothed_confidence=float(np.clip(value, 0, 1))
                        )
        for index in range(1, len(segment) - 1):
            if segment[index].visible:
                continue
            left, right = index - 1, index + 1
            while left >= 0 and not segment[left].visible:
                left -= 1
            while right < len(segment) and not segment[right].visible:
                right += 1
            if left >= 0 and right < len(segment) and right - left - 1 <= max_gap:
                ratio = (index - left) / (right - left)
                before, after = segment[left], segment[right]
                segment[index] = replace(
                    segment[index],
                    visible=True,
                    centroid_x=_lerp(before.centroid_x, after.centroid_x, ratio),
                    centroid_y=_lerp(before.centroid_y, after.centroid_y, ratio),
                    scale=_lerp(before.scale, after.scale, ratio),
                    rotation=_lerp(before.rotation, after.rotation, ratio),
                    smoothed_confidence=min(before.smoothed_confidence, after.smoothed_confidence)
                    * 0.75,
                )
        result[segment_start:segment_end] = segment
        segment_start = segment_end
    return result


def _lerp(left: float | None, right: float | None, ratio: float) -> float | None:
    return None if left is None or right is None else left + (right - left) * ratio
