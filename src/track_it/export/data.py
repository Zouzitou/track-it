from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from track_it.motion.transforms import MotionTransform
from track_it.persistence.atomic import atomic_write_text


def export_motion_json(
    path: Path, transforms: dict[str, list[MotionTransform]], metadata: dict[str, Any]
) -> Path:
    payload = {
        "schema_version": 1,
        "coordinate_systems": ["pixels", "normalized"],
        "metadata": metadata,
        "objects": {
            object_id: [_with_normalized(item, metadata) for item in values]
            for object_id, values in transforms.items()
        },
    }
    atomic_write_text(path, json.dumps(payload, indent=2, allow_nan=False))
    return path


def export_motion_csv(
    path: Path, transforms: dict[str, list[MotionTransform]], names: dict[str, str]
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    fields = [
        "frame_index",
        "timestamp",
        "object_id",
        "name",
        "visible",
        "x",
        "y",
        "scale",
        "rotation",
        "confidence",
        "aabb",
        "corners",
        "anchor",
    ]
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for object_id in sorted(transforms):
            for item in transforms[object_id]:
                writer.writerow(
                    {
                        "frame_index": item.frame_index,
                        "timestamp": f"{item.timestamp:.9f}",
                        "object_id": object_id,
                        "name": names.get(object_id, object_id),
                        "visible": int(item.visible),
                        "x": item.centroid_x,
                        "y": item.centroid_y,
                        "scale": item.scale,
                        "rotation": item.rotation,
                        "confidence": item.smoothed_confidence,
                        "aabb": json.dumps(item.aabb),
                        "corners": json.dumps(item.corners),
                        "anchor": json.dumps(item.anchor),
                    }
                )
    temporary.replace(path)
    return path


def _with_normalized(item: MotionTransform, metadata: dict[str, Any]) -> dict[str, Any]:
    result = item.to_dict()
    width, height = float(metadata.get("width", 1)), float(metadata.get("height", 1))
    result["normalized"] = {
        "centroid": None
        if item.centroid_x is None or item.centroid_y is None
        else [item.centroid_x / width, item.centroid_y / height],
        "aabb": None
        if item.aabb is None
        else [
            item.aabb[0] / width,
            item.aabb[1] / height,
            item.aabb[2] / width,
            item.aabb[3] / height,
        ],
    }
    return result
