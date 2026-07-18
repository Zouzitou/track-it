from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QToolButton

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
    assert window.minimumWidth() == 1100
    assert window.canvas.accessibleName() == "Video canvas"
    buttons = [button for button in window.findChildren(QToolButton) if button.property("iconName")]
    assert buttons and all(button.accessibleName() or button.text() for button in buttons)
    theme.toggle()
    assert theme.effective == "light"
    assert "Host Grotesk" in qapp.font().family()
