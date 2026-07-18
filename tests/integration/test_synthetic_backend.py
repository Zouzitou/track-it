from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import numpy as np
from PIL import Image

from track_it.domain.models import Prompt
from track_it.inference.synthetic import SyntheticBackend
from track_it.utils.cancellation import CancellationToken


def test_prompt_and_bidirectional_tracking(tmp_path: Path) -> None:
    for frame in range(8):
        image = np.zeros((40, 60, 3), dtype=np.uint8)
        image[12:22, 5 + frame : 17 + frame] = (220, 40, 40)
        Image.fromarray(image).save(tmp_path / f"{frame:08d}.png")
    backend = SyntheticBackend()
    backend.initialize_video(tmp_path)
    oid = uuid4()
    prompt = Prompt(frame_index=3, object_id=oid, positive_points=[(10, 15)])
    candidates = backend.add_prompt(prompt, CancellationToken())
    assert candidates[0].mask.sum() == 120
    forward = list(backend.propagate([str(oid)], 3, 7, False, CancellationToken()))
    backward = list(backend.propagate([str(oid)], 0, 3, True, CancellationToken()))
    assert [item.frame_index for item in forward] == [3, 4, 5, 6, 7]
    assert [item.frame_index for item in backward] == [3, 2, 1, 0]
    assert all(item.mask.any() for item in forward + backward)
