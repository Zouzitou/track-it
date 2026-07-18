from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from track_it.domain.models import PostprocessingSettings
from track_it.inference.models import ModelManager, select_sam_model
from track_it.masking.processing import process_mask
from track_it.utils.cancellation import CancellationToken
from track_it.workers.base import JobWorker


def test_model_selection_and_local_manager(tmp_path: Path) -> None:
    assert select_sam_model(8, "cuda") == "sam2.1-small"
    assert select_sam_model(12, "cuda") == "sam2.1-base-plus"
    assert select_sam_model(24, "cuda") == "sam2.1-large"
    assert select_sam_model(None, "cpu") == "sam2.1-tiny"
    manager = ModelManager(tmp_path)
    assert manager.path_for("sam2.1-small").parent == tmp_path


def test_cancellation_and_worker_signals(qtbot) -> None:
    token = CancellationToken()
    token.cancel()
    assert token.is_cancelled
    with pytest.raises(Exception, match="cancelled"):
        token.raise_if_cancelled()

    worker = JobWorker(lambda _token, progress: (progress(1, 1, "done"), 42)[1])
    with qtbot.waitSignal(worker.completed, timeout=1000) as signal:
        worker.run()
    assert signal.args == [42]


def test_processing_all_branches() -> None:
    mask = np.zeros((20, 20), bool)
    mask[3:8, 3:8] = True
    mask[4, 4] = False
    mask[15, 15] = True
    result = process_mask(
        mask,
        PostprocessingSettings(
            grow_shrink=-1, fill_holes=True, minimum_island=5, edge_smoothing=0.5
        ),
    )
    assert result.dtype == np.bool_
    assert not result[15, 15]
