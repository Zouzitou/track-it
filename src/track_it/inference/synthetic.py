from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import numpy as np
from PIL import Image

from track_it.domain.models import Prompt
from track_it.inference.protocol import MaskCandidate
from track_it.utils.cancellation import CancellationToken


class SyntheticBackend:
    """Deterministic color-region backend for tests; never selected in production UI."""

    name = "synthetic-test"

    def __init__(self) -> None:
        self.frames: list[Path] = []
        self.prompts: dict[str, Prompt] = {}

    def load(self, model_path: Path, device: str) -> None:
        del model_path, device

    def unload(self) -> None:
        self.close_video()

    def initialize_video(self, frames_directory: Path) -> None:
        self.frames = sorted(frames_directory.glob("*.png")) + sorted(
            frames_directory.glob("*.jpg")
        )

    def close_video(self) -> None:
        self.frames.clear()
        self.prompts.clear()

    def _mask(self, frame_index: int, prompt: Prompt) -> np.ndarray:
        rgb = np.asarray(Image.open(self.frames[frame_index]).convert("RGB"))
        if prompt.positive_points:
            x, y = prompt.positive_points[0]
            sample = rgb[
                int(np.clip(y, 0, rgb.shape[0] - 1)), int(np.clip(x, 0, rgb.shape[1] - 1))
            ].astype(int)
            distance = np.linalg.norm(rgb.astype(int) - sample, axis=2)
            mask = distance < 35
        elif prompt.box:
            x0, y0, x1, y1 = map(int, prompt.box)
            mask = np.zeros(rgb.shape[:2], dtype=bool)
            mask[max(0, y0) : y1, max(0, x0) : x1] = True
        else:
            mask = np.zeros(rgb.shape[:2], dtype=bool)
        for x, y in prompt.negative_points:
            yy, xx = np.ogrid[: mask.shape[0], : mask.shape[1]]
            mask[(xx - x) ** 2 + (yy - y) ** 2 <= 64] = False
        return np.asarray(mask, dtype=bool)

    def add_prompt(self, prompt: Prompt, token: CancellationToken) -> list[MaskCandidate]:
        token.raise_if_cancelled()
        oid = str(prompt.object_id)
        self.prompts[oid] = prompt
        mask = self._mask(prompt.frame_index, prompt)
        return [MaskCandidate(oid, prompt.frame_index, mask, 0.95 if mask.any() else 0.0)]

    def propagate(
        self, object_ids: list[str], start: int, end: int, reverse: bool, token: CancellationToken
    ) -> Iterator[MaskCandidate]:
        indices = range(end, start - 1, -1) if reverse else range(start, end + 1)
        for index in indices:
            token.raise_if_cancelled()
            for oid in object_ids:
                prompt = self.prompts[oid]
                mask = self._mask(index, prompt)
                yield MaskCandidate(oid, index, mask, 0.9 if mask.any() else 0.0)
