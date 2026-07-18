from __future__ import annotations

from fractions import Fraction
from itertools import pairwise
from pathlib import Path
from typing import Any

import av

from track_it.domain.models import FrameRecord, VideoMetadata
from track_it.errors import UnsupportedVideoError, VideoOpenError
from track_it.persistence.fingerprint import source_fingerprint


def _rotation(stream: Any) -> int:
    value = stream.metadata.get("rotate", "0")
    try:
        return int(float(value)) % 360
    except (TypeError, ValueError):
        return 0


def index_video(path: Path) -> tuple[VideoMetadata, list[FrameRecord]]:
    try:
        container = av.open(str(path))
    except (av.error.FFmpegError, OSError) as exc:
        raise VideoOpenError(f"The video could not be opened: {path}") from exc
    with container:
        streams = [
            stream
            for stream in container.streams.video
            if not stream.metadata.get("mimetype", "").startswith("image/")
        ]
        if not streams:
            raise UnsupportedVideoError("The file contains no usable video stream.")
        stream = streams[0]
        rotation = _rotation(stream)
        width, height = stream.codec_context.width, stream.codec_context.height
        display_width, display_height = (
            (height, width) if rotation in (90, 270) else (width, height)
        )
        records: list[FrameRecord] = []
        previous_time = 0.0
        for decode_index, frame in enumerate(container.decode(stream)):
            time_base = Fraction(frame.time_base or stream.time_base or Fraction(1, 1000))
            presentation = float(frame.pts * time_base) if frame.pts is not None else previous_time
            duration = float(frame.duration * time_base) if frame.duration else None
            records.append(
                FrameRecord(
                    index=len(records),
                    pts=frame.pts,
                    time_base_num=time_base.numerator,
                    time_base_den=time_base.denominator,
                    presentation_time=max(0.0, presentation),
                    duration=duration,
                    keyframe=bool(frame.key_frame),
                    decode_index=decode_index,
                    source_stream=stream.index,
                )
            )
            previous_time = presentation + (duration or 0.0)
        if not records:
            raise UnsupportedVideoError("The selected stream contains zero decoded frames.")
        times = [record.presentation_time for record in records]
        deltas = [right - left for left, right in pairwise(times) if right > left]
        average_rate = float(stream.average_rate) if stream.average_rate else None
        vfr = bool(
            deltas and max(deltas) - min(deltas) > max(1e-5, (sum(deltas) / len(deltas)) * 0.01)
        )
        stream_meta = {
            "codec": stream.codec_context.name,
            "width": width,
            "height": height,
            "rotation": rotation,
            "frames": len(records),
        }
        stat = path.stat()
        metadata = VideoMetadata(
            path=str(path.resolve()),
            size=stat.st_size,
            mtime_ns=stat.st_mtime_ns,
            fingerprint=source_fingerprint(path, stream_meta),
            stream_index=stream.index,
            encoded_width=width,
            encoded_height=height,
            display_width=display_width,
            display_height=display_height,
            rotation=rotation,
            pixel_aspect_ratio=str(stream.sample_aspect_ratio or "1:1"),
            average_rate=average_rate,
            nominal_rate=float(stream.base_rate) if stream.base_rate else average_rate,
            vfr=vfr,
            duration=max(times[-1], float(container.duration or 0) / av.time_base),
            frame_count=len(records),
            audio_streams=[item.index for item in container.streams.audio],
        )
        return metadata, records
