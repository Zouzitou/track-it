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


def make_frame() -> QImage:
    height, width = 540, 960
    yy, xx = np.ogrid[:height, :width]
    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    rgb[..., 0] = np.clip(18 + xx / width * 35, 0, 255)
    rgb[..., 1] = np.clip(24 + yy / height * 30, 0, 255)
    rgb[..., 2] = 42
    current = ((xx - 485) / 150) ** 2 + ((yy - 270) / 205) ** 2 <= 1
    rgb[current] = (174, 136, 104)
    rgb[210:330, 432:538] = (42, 58, 76)
    image = QImage(rgb.data, width, height, rgb.strides[0], QImage.Format.Format_RGB888).copy()
    return image


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
    window.resize(1120, 720)
    window.canvas.set_frame(make_frame())
    window.project_title.setText("studio-walkthrough.mp4")
    window.clip_details.setText(
        "1920 x 1080  •  0:12  •  360 frames\n\n"
        "Your clip is ready. Track it will automatically use the main subject."
    )
    window._video_path = root / "studio-walkthrough.mp4"
    window.create_button.setEnabled(True)
    window.create_action.setEnabled(True)
    window.operation.setText("Ready to create")
    window._set_step(2)
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
