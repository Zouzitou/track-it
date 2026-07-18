from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from track_it.ui.theme.manager import ThemeManager, ThemeMode
from track_it.ui.windows.main_window import MainWindow


def make_frame() -> tuple[QImage, np.ndarray, np.ndarray, np.ndarray]:
    height, width = 540, 960
    yy, xx = np.ogrid[:height, :width]
    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    rgb[..., 0] = np.clip(18 + xx / width * 35, 0, 255)
    rgb[..., 1] = np.clip(24 + yy / height * 30, 0, 255)
    rgb[..., 2] = 42
    current = ((xx - 485) / 150) ** 2 + ((yy - 270) / 205) ** 2 <= 1
    previous = ((xx - 462) / 150) ** 2 + ((yy - 272) / 205) ** 2 <= 1
    next_mask = ((xx - 508) / 150) ** 2 + ((yy - 268) / 205) ** 2 <= 1
    rgb[current] = (174, 136, 104)
    rgb[210:330, 432:538] = (42, 58, 76)
    image = QImage(rgb.data, width, height, rgb.strides[0], QImage.Format.Format_RGB888).copy()
    return image, current, previous, next_mask


def main() -> None:
    root = Path(__file__).parents[1]
    output = root / "docs" / "images"
    output.mkdir(parents=True, exist_ok=True)
    settings_root = root / ".tmp" / "screenshot-settings"
    settings_root.mkdir(parents=True, exist_ok=True)
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(settings_root))
    QCoreApplication.setOrganizationName("TrackItScreenshots")
    QCoreApplication.setApplicationName("TrackIt")
    app = QApplication([])
    theme = ThemeManager(app, QSettings("TrackItScreenshots", "Theme"))
    window = MainWindow(theme)
    window.resize(1440, 900)
    image, current, previous, next_mask = make_frame()
    window.canvas.set_frame(image)
    window.canvas.set_masks(current, previous, next_mask)
    window.canvas.points = [(478, 265, False), (420, 180, True)]
    window.project_title.setText("STUDIO WALKTHROUGH")
    window.objects.clear()
    window.objects.addItems(["01  Person  •  Tracking complete", "02  Jacket  •  Review 3 frames"])
    window.timeline.set_frame_count(360)
    window.timeline.current_frame = 148
    window.timeline.corrections = {72, 148, 244}
    window.timeline.scene_cuts = {210}
    window.timeline.confidence = {frame: 0.92 if frame % 17 else 0.61 for frame in range(360)}
    for mode, filename in (
        (ThemeMode.DARK, "main-window-dark.png"),
        (ThemeMode.LIGHT, "main-window-light.png"),
    ):
        theme.set_mode(mode)
        window.show()
        app.processEvents()
        if not window.grab().save(str(output / filename), "PNG"):
            raise RuntimeError(f"Could not save {filename}")
    window.close()


if __name__ == "__main__":
    main()
