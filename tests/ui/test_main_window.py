from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QListWidget, QToolButton

from track_it.ui.theme.manager import ThemeManager, ThemeMode
from track_it.ui.windows.main_window import MainWindow


def test_window_launch_theme_and_accessibility(qtbot, qapp: QApplication) -> None:
    settings = QSettings("TrackItTests", "Theme")
    settings.clear()
    theme = ThemeManager(qapp, settings)
    theme.set_mode(ThemeMode.DARK)
    window = MainWindow(theme)
    qtbot.addWidget(window)
    window.show()
    assert window.minimumWidth() == 900
    assert window.canvas.accessibleName() == "Video canvas"
    assert window.create_button.text() == "Create green screen"
    assert not window.create_button.isEnabled()
    assert not window.findChildren(QListWidget)
    buttons = [button for button in window.findChildren(QToolButton) if button.property("iconName")]
    assert buttons and all(button.accessibleName() or button.text() for button in buttons)
    theme.toggle()
    assert theme.effective == "light"
    assert "Host Grotesk" in qapp.font().family()


def test_loaded_clip_has_one_clear_next_action(qtbot, qapp: QApplication, video_metadata) -> None:
    theme = ThemeManager(qapp, QSettings("TrackItTests", "SimpleFlow"))
    window = MainWindow(theme)
    qtbot.addWidget(window)
    image = QImage(64, 48, QImage.Format.Format_RGB888)

    window._video_indexed((video_metadata, [], image))

    assert window.create_button.isEnabled()
    assert window.create_action.isEnabled()
    assert window.operation.text() == "Ready to create"
    assert window.step_labels[1].objectName() == "activeStep"
    assert "automatically" in window.clip_details.text().lower()
