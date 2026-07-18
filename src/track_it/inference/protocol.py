from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from track_it.domain.models import Prompt
from track_it.utils.cancellation import CancellationToken


@dataclass(frozen=True, slots=True)
class MaskCandidate:
    object_id: str
    frame_index: int
    mask: np.ndarray
    confidence: float
    logits: np.ndarray | None = None


class VideoSegmentationBackend(Protocol):
    @property
    def name(self) -> str: ...
    def load(self, model_path: Path, device: str) -> None: ...
    def unload(self) -> None: ...
    def initialize_video(self, frames_directory: Path) -> None: ...
    def close_video(self) -> None: ...
    def add_prompt(self, prompt: Prompt, token: CancellationToken) -> list[MaskCandidate]: ...
    def propagate(
        self, object_ids: list[str], start: int, end: int, reverse: bool, token: CancellationToken
    ) -> Iterator[MaskCandidate]: ...
