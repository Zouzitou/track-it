from __future__ import annotations

import sys

from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtWidgets import QApplication

from track_it.constants import APP_NAME, ORGANIZATION
from track_it.ui.theme.manager import ThemeManager
from track_it.ui.windows.main_window import MainWindow
from track_it.version import __version__


def run_gui(argv: list[str] | None = None) -> int:
    QCoreApplication.setOrganizationName(ORGANIZATION)
    QCoreApplication.setApplicationName("TrackIt")
    QCoreApplication.setApplicationVersion(__version__)
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    app = QApplication(argv or sys.argv)
    app.setApplicationDisplayName(APP_NAME)
    theme = ThemeManager(app)
    theme.apply()
    window = MainWindow(theme)
    window.show()
    return app.exec()
