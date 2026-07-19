from __future__ import annotations

import gc
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Any
from uuid import uuid4

import av
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

from track_it.domain.models import Prompt
from track_it.errors import ExportConfigurationError, ExportProcessError, ModelIntegrityError
from track_it.inference.models import SAM2_SMALL, ModelManager
from track_it.inference.sam2_backend import Sam2Backend
from track_it.media.ffmpeg import find_ffmpeg
from track_it.utils.cancellation import CancellationToken

Progress = Callable[[int, int, str], None]
GREEN_RGB = np.asarray((0, 255, 0), dtype=np.uint8)
SUPPORTED_VIDEO_SUFFIXES = frozenset({".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"})


@dataclass(frozen=True, slots=True)
class GreenScreenResult:
    output_path: Path
    frame_count: int
    elapsed_seconds: float
    device: str


@dataclass(frozen=True, slots=True)
class SubjectCandidate:
    mask: np.ndarray
    predicted_iou: float


def suggested_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}-green-screen.mp4")


def composite_on_green(frame: np.ndarray, mask: np.ndarray) -> np.ndarray:
    rgb = np.asarray(frame, dtype=np.uint8)
    subject = np.asarray(mask, dtype=bool)
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ExportConfigurationError("A decoded video frame was not RGB.")
    if subject.shape != rgb.shape[:2]:
        resized = Image.fromarray(subject.astype(np.uint8) * 255).resize(
            (rgb.shape[1], rgb.shape[0]), Image.Resampling.NEAREST
        )
        subject = np.asarray(resized, dtype=np.uint8) > 0
    return np.where(subject[..., None], rgb, GREEN_RGB).astype(np.uint8, copy=False)


def choose_subject(candidates: list[SubjectCandidate]) -> tuple[np.ndarray, tuple[float, float]]:
    """Choose a prominent, central mask and return a stable point inside it."""
    ranked: list[tuple[float, np.ndarray]] = []
    for candidate in candidates:
        mask = np.asarray(candidate.mask, dtype=bool)
        if mask.ndim != 2 or not mask.any():
            continue
        height, width = mask.shape
        area_ratio = float(mask.mean())
        if not 0.01 <= area_ratio <= 0.82:
            continue
        ys, xs = np.nonzero(mask)
        center_distance = np.hypot(xs.mean() / width - 0.5, ys.mean() / height - 0.5)
        center_bonus = 1.0 if mask[height // 2, width // 2] else 0.0
        area_score = 1.0 - min(1.0, abs(area_ratio - 0.24) / 0.24)
        score = (
            float(candidate.predicted_iou) * 2.0
            + center_bonus * 1.4
            + max(0.0, 1.0 - center_distance * 1.7)
            + area_score * 0.5
        )
        ranked.append((score, mask))
    if not ranked:
        raise ExportProcessError(
            "Track it could not find one clear main subject. Try a clip where the subject is "
            "visible near the center at the middle of the video."
        )
    mask = max(ranked, key=lambda item: item[0])[1]
    distance = distance_transform_edt(mask)
    y, x = np.unravel_index(int(distance.argmax()), distance.shape)
    return mask, (float(x), float(y))


class GreenScreenProcessor:
    """Automatic local clip-to-green-screen workflow."""

    def __init__(self, model_manager: ModelManager | None = None) -> None:
        self.models = model_manager or ModelManager()

    def create(
        self,
        input_path: Path,
        output_path: Path,
        token: CancellationToken,
        progress: Progress,
    ) -> GreenScreenResult:
        started = monotonic()
        input_path = input_path.resolve()
        output_path = output_path.resolve()
        self._validate_paths(input_path, output_path)
        ffmpeg, _ = find_ffmpeg()
        if not ffmpeg:
            raise ExportProcessError("FFmpeg is missing. Reinstall Track it and try again.")

        work_root = output_path.parent / f".{output_path.stem}.trackit-work-{uuid4().hex}"
        frames_root = work_root / "frames"
        rendered_root = work_root / "rendered"
        partial_output = work_root / "green-screen.mp4"
        frames_root.mkdir(parents=True)
        rendered_root.mkdir(parents=True)
        backend: Sam2Backend | None = None
        try:
            progress(0, 5, "Preparing your clip")
            frame_paths, fps = self._extract_frames(input_path, frames_root, token, progress)
            model_path = self._ensure_model(token, progress)
            device = self._device()

            progress(2, 5, "Finding the main subject")
            middle = len(frame_paths) // 2
            candidates = self._subject_candidates(frame_paths[middle], model_path, device, token)
            _, seed = choose_subject(candidates)

            progress(3, 5, "Following the subject through the clip")
            backend = Sam2Backend(SAM2_SMALL.config)
            backend.load(model_path, device)
            backend.initialize_video(frames_root)
            object_id = uuid4()
            prompt = Prompt(frame_index=middle, object_id=object_id, positive_points=[seed])
            masks: dict[int, np.ndarray] = {}
            for candidate in backend.add_prompt(prompt, token):
                masks[candidate.frame_index] = candidate.mask
            for candidate in backend.propagate(
                [str(object_id)], middle, len(frame_paths) - 1, False, token
            ):
                masks[candidate.frame_index] = candidate.mask
            if middle:
                for candidate in backend.propagate([str(object_id)], 0, middle, True, token):
                    masks[candidate.frame_index] = candidate.mask

            progress(4, 5, "Painting the green background")
            self._render_frames(frame_paths, masks, rendered_root, token, progress)
            backend.unload()
            backend = None
            self._encode(ffmpeg, rendered_root, input_path, partial_output, fps, token)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            partial_output.replace(output_path)
            progress(5, 5, "Green-screen video ready")
            return GreenScreenResult(
                output_path=output_path,
                frame_count=len(frame_paths),
                elapsed_seconds=monotonic() - started,
                device=device,
            )
        finally:
            if backend is not None:
                backend.unload()
            shutil.rmtree(work_root, ignore_errors=True)

    @staticmethod
    def _validate_paths(input_path: Path, output_path: Path) -> None:
        if not input_path.is_file():
            raise ExportConfigurationError("Choose a video file that still exists.")
        if input_path.suffix.lower() not in SUPPORTED_VIDEO_SUFFIXES:
            raise ExportConfigurationError("Choose an MP4, MOV, MKV, AVI, WebM, or M4V clip.")
        if output_path.suffix.lower() != ".mp4":
            raise ExportConfigurationError("The green-screen video must be saved as an MP4.")
        if input_path == output_path:
            raise ExportConfigurationError(
                "Choose a different output name so the clip is preserved."
            )

    @staticmethod
    def _extract_frames(
        input_path: Path, frames_root: Path, token: CancellationToken, progress: Progress
    ) -> tuple[list[Path], float]:
        paths: list[Path] = []
        with av.open(str(input_path)) as container:
            if not container.streams.video:
                raise ExportProcessError("The selected file does not contain a video stream.")
            stream = container.streams.video[0]
            fps = float(stream.average_rate or stream.guessed_rate or 30.0)
            expected = int(stream.frames or 0)
            for index, frame in enumerate(container.decode(stream)):
                token.raise_if_cancelled()
                path = frames_root / f"{index:08d}.jpg"
                Image.fromarray(frame.to_ndarray(format="rgb24")).save(path, quality=92)
                paths.append(path)
                if index % 12 == 0:
                    progress(index, expected, "Preparing your clip")
        if not paths:
            raise ExportProcessError("No readable frames were found in the selected clip.")
        return paths, max(1.0, min(fps, 240.0))

    def _ensure_model(self, token: CancellationToken, progress: Progress) -> Path:
        try:
            self.models.verify(SAM2_SMALL.id)
            return self.models.path_for(SAM2_SMALL.id)
        except ModelIntegrityError:
            progress(1, 5, "First-time setup: downloading the AI model (176 MB)")
            return self.models.download(
                SAM2_SMALL.id,
                token,
                lambda done, total: progress(done, total, "Downloading the AI model"),
            )

    @staticmethod
    def _device() -> str:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"

    @staticmethod
    def _subject_candidates(
        frame_path: Path, model_path: Path, device: str, token: CancellationToken
    ) -> list[SubjectCandidate]:
        token.raise_if_cancelled()
        try:
            import torch
            from sam2.build_sam import build_sam2
            from sam2.sam2_image_predictor import SAM2ImagePredictor
        except ImportError as exc:
            raise ExportProcessError("The bundled subject-detection component is missing.") from exc

        model: Any = None
        predictor: Any = None
        try:
            model = build_sam2(SAM2_SMALL.config, str(model_path), device=device)
            predictor = SAM2ImagePredictor(model)
            image = np.asarray(Image.open(frame_path).convert("RGB")).copy()
            predictor.set_image(image)
            height, width = image.shape[:2]
            results: list[SubjectCandidate] = []
            sample_points = (
                (0.5, 0.5),
                (0.35, 0.35),
                (0.65, 0.35),
                (0.35, 0.65),
                (0.65, 0.65),
                (0.5, 0.28),
                (0.5, 0.72),
                (0.25, 0.5),
                (0.75, 0.5),
            )
            with torch.inference_mode():
                for x_ratio, y_ratio in sample_points:
                    token.raise_if_cancelled()
                    masks, scores, _ = predictor.predict(
                        point_coords=np.asarray([[x_ratio * width, y_ratio * height]]),
                        point_labels=np.asarray([1]),
                        multimask_output=True,
                    )
                    results.extend(
                        SubjectCandidate(np.asarray(mask, dtype=bool), float(score))
                        for mask, score in zip(masks, scores, strict=True)
                    )
            return results
        finally:
            del predictor, model
            gc.collect()
            if device == "cuda":
                import torch

                torch.cuda.empty_cache()

    @staticmethod
    def _render_frames(
        frame_paths: list[Path],
        masks: dict[int, np.ndarray],
        rendered_root: Path,
        token: CancellationToken,
        progress: Progress,
    ) -> None:
        last_mask: np.ndarray | None = None
        for index, frame_path in enumerate(frame_paths):
            token.raise_if_cancelled()
            mask = masks.get(index, last_mask)
            if mask is None:
                raise ExportProcessError(f"The subject was lost at frame {index + 1}.")
            last_mask = mask
            frame = np.asarray(Image.open(frame_path).convert("RGB"))
            Image.fromarray(composite_on_green(frame, mask)).save(
                rendered_root / f"{index:08d}.png", compress_level=2
            )
            if index % 12 == 0:
                progress(index, len(frame_paths), "Painting the green background")

    @staticmethod
    def _encode(
        ffmpeg: str,
        rendered_root: Path,
        input_path: Path,
        output_path: Path,
        fps: float,
        token: CancellationToken,
    ) -> None:
        argv = [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-framerate",
            f"{fps:.8g}",
            "-i",
            str(rendered_root / "%08d.png"),
            "-i",
            str(input_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a?",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(output_path),
        ]
        process = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stderr = ""
        try:
            while True:
                token.raise_if_cancelled()
                try:
                    _, stderr = process.communicate(timeout=0.2)
                    break
                except subprocess.TimeoutExpired:
                    continue
        except Exception:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
            raise
        if process.returncode:
            raise ExportProcessError(stderr.strip() or "FFmpeg could not encode the video.")
