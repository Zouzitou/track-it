from __future__ import annotations

from pathlib import Path

import av
import numpy as np
from av import VideoFrame

from track_it.cli import main
from track_it.diagnostics import collect_diagnostics, self_test
from track_it.media.ffmpeg import find_ffmpeg, probe, run_process
from track_it.media.index import index_video


def _video(path: Path) -> None:
    with av.open(str(path), "w") as container:
        stream = container.add_stream("mpeg4", rate=25)
        stream.width = 64
        stream.height = 48
        stream.pix_fmt = "yuv420p"
        for index in range(6):
            array = np.zeros((48, 64, 3), dtype=np.uint8)
            array[10:25, 5 + index : 18 + index] = (230, 80, 40)
            for packet in stream.encode(VideoFrame.from_ndarray(array, format="rgb24")):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)


def test_real_pyav_index_and_ffprobe(tmp_path: Path) -> None:
    source = tmp_path / "timestamps ü & test.mp4"
    _video(source)
    metadata, frames = index_video(source)
    assert metadata.frame_count == 6
    assert metadata.encoded_width == 64
    assert [item.index for item in frames] == list(range(6))
    ffmpeg, ffprobe = find_ffmpeg()
    assert ffmpeg and ffprobe
    assert run_process([ffmpeg, "-version"]).returncode == 0
    result = probe(source, ffprobe)
    assert result["streams"][0]["width"] == 64


def test_diagnostics_and_cli(capsys) -> None:
    diagnostics = collect_diagnostics(redact=True)
    assert "privacy" in diagnostics and "ffmpeg_path" not in diagnostics
    ok, results = self_test()
    assert ok and any("tensor" in item for item in results)
    assert main(["diagnostics"]) == 0
    assert "cuda_available" in capsys.readouterr().out
    assert main(["self-test"]) == 0
