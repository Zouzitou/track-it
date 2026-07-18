from __future__ import annotations

from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from track_it.constants import SCHEMA_VERSION


class FrameRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int = Field(ge=0)
    pts: int | None
    time_base_num: int = Field(gt=0)
    time_base_den: int = Field(gt=0)
    presentation_time: float = Field(ge=0)
    duration: float | None = Field(default=None, ge=0)
    keyframe: bool = False
    decode_index: int = Field(ge=0)
    source_stream: int = Field(ge=0)
    proxy_path: str | None = None
    corrupted: bool = False
    duplicated: bool = False

    @property
    def time_base(self) -> Fraction:
        return Fraction(self.time_base_num, self.time_base_den)


class VideoMetadata(BaseModel):
    path: str
    relative_path: str | None = None
    size: int = Field(ge=0)
    mtime_ns: int = Field(ge=0)
    fingerprint: str
    stream_index: int = Field(ge=0)
    encoded_width: int = Field(gt=0)
    encoded_height: int = Field(gt=0)
    display_width: int = Field(gt=0)
    display_height: int = Field(gt=0)
    rotation: int = 0
    pixel_aspect_ratio: str = "1:1"
    average_rate: float | None = None
    nominal_rate: float | None = None
    vfr: bool = False
    duration: float = Field(ge=0)
    frame_count: int = Field(ge=0)
    audio_streams: list[int] = Field(default_factory=list)


class TrackObject(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    color: str = "#6D87FF"
    visible: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    corrected_at_frame: dict[int, datetime] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def nonempty_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Object name cannot be empty")
        return value


class Prompt(BaseModel):
    frame_index: int = Field(ge=0)
    object_id: UUID
    positive_points: list[tuple[float, float]] = Field(default_factory=list)
    negative_points: list[tuple[float, float]] = Field(default_factory=list)
    box: tuple[float, float, float, float] | None = None
    existing_mask_frame: int | None = None


class PostprocessingSettings(BaseModel):
    grow_shrink: int = Field(default=0, ge=-100, le=100)
    feather: float = Field(default=0, ge=0, le=100)
    fill_holes: bool = True
    minimum_island: int = Field(default=0, ge=0)
    edge_smoothing: float = Field(default=0, ge=0, le=1)
    temporal_smoothing: float = Field(default=0, ge=0, le=1)
    invert_display_export: bool = False


class ProjectModel(BaseModel):
    schema_version: int = SCHEMA_VERSION
    app_version: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    video: VideoMetadata
    backend: str = "sam2"
    model_id: str = "sam2.1-small"
    objects: list[TrackObject] = Field(default_factory=list)
    correction_checkpoints: dict[str, list[int]] = Field(default_factory=dict)
    postprocessing: dict[str, PostprocessingSettings] = Field(default_factory=dict)
    export_presets: dict[str, dict[str, Any]] = Field(default_factory=dict)
    timeline_range: tuple[int, int] | None = None
    cache_valid: bool = True
    ui_state: dict[str, Any] = Field(default_factory=dict)
    proxy_settings: dict[str, Any] = Field(
        default_factory=lambda: {"max_side": 1280, "quality": 92}
    )
    tracking_mode: Literal["position", "position_scale", "position_scale_rotation"] = (
        "position_scale_rotation"
    )

    def object_by_id(self, object_id: UUID) -> TrackObject:
        return next(obj for obj in self.objects if obj.id == object_id)


class ProjectSnapshot(BaseModel):
    """Immutable export input detached from mutable controller/UI state."""

    model_config = ConfigDict(frozen=True)
    root: Path
    project: ProjectModel
