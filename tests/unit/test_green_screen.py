from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from PIL import Image

from track_it.errors import ExportConfigurationError, ExportProcessError
from track_it.export import green_screen as green_screen_module
from track_it.export.green_screen import (
    GreenScreenProcessor,
    SubjectCandidate,
    choose_subject,
    composite_on_green,
    suggested_output_path,
)
from track_it.inference.protocol import MaskCandidate
from track_it.utils.cancellation import CancellationToken


def test_suggested_output_keeps_original_clip() -> None:
    source = Path("Z:/clips/walkthrough.mov")
    assert suggested_output_path(source) == Path("Z:/clips/walkthrough-green-screen.mp4")


def test_composite_replaces_only_the_background() -> None:
    frame = np.full((4, 5, 3), (80, 90, 100), dtype=np.uint8)
    mask = np.zeros((4, 5), dtype=bool)
    mask[1:3, 2:4] = True

    result = composite_on_green(frame, mask)

    assert np.array_equal(result[1, 2], (80, 90, 100))
    assert np.array_equal(result[0, 0], (0, 255, 0))
    assert np.count_nonzero(np.all(result == (0, 255, 0), axis=2)) == 16


def test_choose_subject_prefers_a_clear_central_candidate() -> None:
    edge = np.zeros((100, 120), dtype=bool)
    edge[20:80, 0:25] = True
    central = np.zeros((100, 120), dtype=bool)
    central[20:85, 35:85] = True

    chosen, point = choose_subject([SubjectCandidate(edge, 0.99), SubjectCandidate(central, 0.92)])

    assert np.array_equal(chosen, central)
    x, y = point
    assert central[round(y), round(x)]
    assert 35 <= x < 85
    assert 20 <= y < 85


def test_choose_subject_explains_when_no_useful_mask_exists() -> None:
    full_frame = np.ones((20, 20), dtype=bool)
    with pytest.raises(ExportProcessError, match="clear main subject"):
        choose_subject([SubjectCandidate(full_frame, 1.0)])


def test_green_screen_paths_protect_the_original(tmp_path: Path) -> None:
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"video")
    GreenScreenProcessor._validate_paths(source, tmp_path / "result.mp4")

    with pytest.raises(ExportConfigurationError, match="preserved"):
        GreenScreenProcessor._validate_paths(source, source)
    with pytest.raises(ExportConfigurationError, match="MP4"):
        GreenScreenProcessor._validate_paths(source, tmp_path / "result.mov")


def test_processor_runs_the_automatic_workflow_and_cleans_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "clip.mp4"
    output = tmp_path / "clip-green-screen.mp4"
    model = tmp_path / "model.pt"
    source.write_bytes(b"source")
    model.write_bytes(b"model")
    frames = [tmp_path / f"source-{index}.jpg" for index in range(3)]
    mask = np.zeros((8, 10), dtype=bool)
    mask[1:7, 2:8] = True
    rendered_masks: dict[int, np.ndarray] = {}
    events: list[str] = []

    class FakeBackend:
        def __init__(self, config: str) -> None:
            assert config

        def load(self, model_path: Path, device: str) -> None:
            assert model_path == model
            assert device == "cpu"

        def initialize_video(self, frames_directory: Path) -> None:
            assert frames_directory.name == "frames"

        def add_prompt(self, prompt, token: CancellationToken) -> list[MaskCandidate]:
            token.raise_if_cancelled()
            return [MaskCandidate(str(prompt.object_id), prompt.frame_index, mask, 0.9)]

        def propagate(self, object_ids, start, end, reverse, token):
            del object_ids
            indices = range(end, start - 1, -1) if reverse else range(start, end + 1)
            for index in indices:
                token.raise_if_cancelled()
                yield MaskCandidate(str(uuid4()), index, mask, 0.9)

        def unload(self) -> None:
            events.append("unloaded")

    processor = GreenScreenProcessor.__new__(GreenScreenProcessor)
    monkeypatch.setattr(green_screen_module, "find_ffmpeg", lambda: ("ffmpeg", "ffprobe"))
    monkeypatch.setattr(green_screen_module, "Sam2Backend", FakeBackend)
    monkeypatch.setattr(processor, "_extract_frames", lambda *_args: (frames, 24.0))
    monkeypatch.setattr(processor, "_ensure_model", lambda *_args: model)
    monkeypatch.setattr(processor, "_device", lambda: "cpu")
    monkeypatch.setattr(
        processor,
        "_subject_candidates",
        lambda *_args: [SubjectCandidate(mask, 0.95)],
    )

    def render(_frames, masks, _root, _token, _progress) -> None:
        rendered_masks.update(masks)

    def encode(_ffmpeg, _rendered, _input, partial, _fps, _token) -> None:
        partial.write_bytes(b"finished-video")

    monkeypatch.setattr(processor, "_render_frames", render)
    monkeypatch.setattr(processor, "_encode", encode)

    result = processor.create(
        source,
        output,
        CancellationToken(),
        lambda _done, _total, message: events.append(message),
    )

    assert result.output_path == output
    assert result.frame_count == 3
    assert output.read_bytes() == b"finished-video"
    assert set(rendered_masks) == {0, 1, 2}
    assert "unloaded" in events
    assert events[-1] == "Green-screen video ready"
    assert not list(tmp_path.glob(".*.trackit-work-*"))


def test_render_frames_reuses_the_last_known_mask(tmp_path: Path) -> None:
    frames: list[Path] = []
    for index in range(2):
        path = tmp_path / f"{index:08d}.jpg"
        Image.fromarray(np.full((6, 8, 3), 100, dtype=np.uint8)).save(path)
        frames.append(path)
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    mask = np.zeros((6, 8), dtype=bool)
    mask[2:4, 3:5] = True

    GreenScreenProcessor._render_frames(
        frames, {0: mask}, rendered, CancellationToken(), lambda *_args: None
    )

    second = np.asarray(Image.open(rendered / "00000001.png").convert("RGB"))
    assert np.array_equal(second[0, 0], (0, 255, 0))
    assert not np.array_equal(second[2, 3], (0, 255, 0))
