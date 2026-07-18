from __future__ import annotations

import gc
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np

from track_it.domain.models import Prompt
from track_it.errors import BackendCompatibilityError, ModelUnavailableError, TrackingOutOfMemory
from track_it.inference.protocol import MaskCandidate
from track_it.utils.cancellation import CancellationToken


class Sam2Backend:
    """Adapter for Meta's official SAM 2.1 video predictor at the pinned commit."""

    name = "sam2"

    def __init__(self, config: str = "configs/sam2.1/sam2.1_hiera_s.yaml") -> None:
        self.config = config
        self.predictor: Any = None
        self.state: Any = None
        self.device = "cpu"

    def load(self, model_path: Path, device: str) -> None:
        if not model_path.exists():
            raise ModelUnavailableError(f"Model file is missing: {model_path}")
        try:
            from sam2.build_sam import build_sam2_video_predictor
        except ImportError as exc:
            raise BackendCompatibilityError(
                "Install official SAM 2 at the commit recorded in third_party/upstreams.lock.json."
            ) from exc
        self.device = device
        self.predictor = build_sam2_video_predictor(self.config, str(model_path), device=device)

    def unload(self) -> None:
        self.close_video()
        self.predictor = None
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            return

    def initialize_video(self, frames_directory: Path) -> None:
        if self.predictor is None:
            raise ModelUnavailableError("SAM 2 is not loaded.")
        self.state = self.predictor.init_state(video_path=str(frames_directory))

    def close_video(self) -> None:
        if (
            self.predictor is not None
            and self.state is not None
            and hasattr(self.predictor, "reset_state")
        ):
            self.predictor.reset_state(self.state)
        self.state = None

    def add_prompt(self, prompt: Prompt, token: CancellationToken) -> list[MaskCandidate]:
        token.raise_if_cancelled()
        if self.state is None:
            raise ModelUnavailableError("No video is initialized.")
        points = np.asarray(prompt.positive_points + prompt.negative_points, dtype=np.float32)
        labels = np.asarray(
            [1] * len(prompt.positive_points) + [0] * len(prompt.negative_points), dtype=np.int32
        )
        try:
            _, object_ids, logits = self.predictor.add_new_points_or_box(
                inference_state=self.state,
                frame_idx=prompt.frame_index,
                obj_id=str(prompt.object_id),
                points=points if len(points) else None,
                labels=labels if len(labels) else None,
                box=np.asarray(prompt.box, dtype=np.float32) if prompt.box else None,
            )
        except RuntimeError as exc:
            if "out of memory" in str(exc).lower():
                raise TrackingOutOfMemory("The GPU ran out of memory.") from exc
            raise
        return [
            MaskCandidate(
                str(oid),
                prompt.frame_index,
                (logit > 0).detach().cpu().numpy().squeeze().astype(bool),
                float(logit.sigmoid().mean().item()),
                logit.detach().cpu().numpy(),
            )
            for oid, logit in zip(object_ids, logits, strict=True)
        ]

    def propagate(
        self, object_ids: list[str], start: int, end: int, reverse: bool, token: CancellationToken
    ) -> Iterator[MaskCandidate]:
        del object_ids
        if self.state is None:
            raise ModelUnavailableError("No video is initialized.")
        iterator = self.predictor.propagate_in_video(
            self.state,
            start_frame_idx=end if reverse else start,
            max_frame_num_to_track=end - start + 1,
            reverse=reverse,
        )
        for frame_index, ids, logits in iterator:
            token.raise_if_cancelled()
            for oid, logit in zip(ids, logits, strict=True):
                yield MaskCandidate(
                    str(oid),
                    int(frame_index),
                    (logit > 0).detach().cpu().numpy().squeeze().astype(bool),
                    float(logit.sigmoid().mean().item()),
                    logit.detach().cpu().numpy(),
                )
