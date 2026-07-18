from __future__ import annotations

import os
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
SETTINGS_ROOT = Path(__file__).parents[1] / ".tmp" / "qsettings"
SETTINGS_ROOT.mkdir(parents=True, exist_ok=True)
QSettings.setDefaultFormat(QSettings.Format.IniFormat)
QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(SETTINGS_ROOT))


@pytest.fixture
def video_metadata():
    from track_it.domain.models import VideoMetadata

    return VideoMetadata(
        path="Z:/sample.mp4",
        size=100,
        mtime_ns=1,
        fingerprint="a" * 64,
        stream_index=0,
        encoded_width=64,
        encoded_height=48,
        display_width=64,
        display_height=48,
        duration=1.0,
        frame_count=30,
    )
