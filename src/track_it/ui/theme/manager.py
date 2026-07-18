from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

from track_it.constants import ASSET_ROOT, ORGANIZATION


class ThemeMode(StrEnum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


_BASE = {
    "dark": {
        "canvas": "#090B10",
        "workspace": "#11151B",
        "surface": "#191E27",
        "text": "#F2F5F8",
        "trace": "#6D87FF",
        "previous": "#FF8278",
        "next": "#43CEBA",
        "muted": "#98A3B3",
        "border": "#303846",
        "danger": "#FF6675",
        "warning": "#F1B84B",
        "success": "#4BC58A",
    },
    "light": {
        "canvas": "#DDE3EC",
        "workspace": "#EEF2F7",
        "surface": "#FFFFFF",
        "text": "#171B23",
        "trace": "#3658D6",
        "previous": "#C94E48",
        "next": "#087F73",
        "muted": "#5E6979",
        "border": "#C8D0DC",
        "danger": "#B82439",
        "warning": "#8B5D00",
        "success": "#147447",
    },
}


class ThemeManager(QObject):
    themeAboutToChange = Signal()
    themeChanged = Signal(str, int)

    def __init__(self, app: QApplication, settings: QSettings | None = None) -> None:
        super().__init__()
        self.app = app
        self.settings = settings or QSettings(ORGANIZATION, "TrackIt")
        self.mode = ThemeMode(str(self.settings.value("preferences/theme", ThemeMode.SYSTEM.value)))
        self.reduced_motion = self.settings.value("preferences/reduced_motion", False, bool)
        self.revision = 0
        self._font_families = self._load_fonts(ASSET_ROOT / "fonts")
        self.effective = self._resolve()
        app.styleHints().colorSchemeChanged.connect(self._system_changed)

    def _load_fonts(self, root: Path) -> dict[str, str]:
        families: dict[str, str] = {}
        for role, filename in (
            ("ui", "HostGrotesk-Variable.ttf"),
            ("data", "JetBrainsMono-Medium.ttf"),
        ):
            font_id = QFontDatabase.addApplicationFont(str(root / filename))
            names = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
            families[role] = names[0] if names else ("Segoe UI" if role == "ui" else "Consolas")
        return families

    def _resolve(self) -> str:
        if self.mode is ThemeMode.SYSTEM:
            return "dark" if self.app.styleHints().colorScheme().name.lower() == "dark" else "light"
        return self.mode.value

    @property
    def colors(self) -> dict[str, str]:
        base = _BASE[self.effective]
        return {
            "background": base["workspace"],
            "canvas-background": base["canvas"],
            "surface-1": base["surface"],
            "surface-2": base["workspace"],
            "on-background": base["text"],
            "on-surface": base["text"],
            "text-secondary": base["muted"],
            "divider": base["border"],
            "focus-ring": base["trace"],
            "primary": base["trace"],
            "on-primary": "#FFFFFF",
            "selected": base["trace"],
            "hover": base["border"],
            "pressed": base["muted"],
            "disabled": base["muted"],
            "danger": base["danger"],
            "warning": base["warning"],
            "success": base["success"],
            "mask-current": base["trace"],
            "mask-previous": base["previous"],
            "mask-next": base["next"],
            "confidence-good": base["success"],
            "confidence-review": base["warning"],
            "confidence-bad": base["danger"],
            "scene-cut": base["danger"],
            "processing": base["trace"],
            "correction": base["previous"],
        }

    def set_mode(self, mode: ThemeMode) -> None:
        self.themeAboutToChange.emit()
        self.mode = mode
        self.settings.setValue("preferences/theme", mode.value)
        self.effective = self._resolve()
        self.apply()

    def toggle(self) -> None:
        self.set_mode(ThemeMode.LIGHT if self.effective == "dark" else ThemeMode.DARK)

    def apply(self) -> None:
        colors = self.colors
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(colors["background"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(colors["on-background"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(colors["surface-1"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(colors["on-surface"]))
        palette.setColor(QPalette.ColorRole.Button, QColor(colors["surface-1"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors["on-surface"]))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["primary"]))
        self.app.setPalette(palette)
        self.app.setFont(QFont(self._font_families["ui"], 10))
        self.app.setStyleSheet(self._qss(colors))
        self.revision += 1
        self.themeChanged.emit(self.effective, self.revision)

    def data_font(self, size: int = 10) -> QFont:
        return QFont(self._font_families["data"], size)

    def _system_changed(self) -> None:
        if self.mode is ThemeMode.SYSTEM:
            self.effective = self._resolve()
            self.apply()

    def _qss(self, c: dict[str, str]) -> str:
        return f"""
        QWidget {{ color: {c["on-background"]}; background: {c["background"]}; }}
        QMainWindow, QDialog {{ background: {c["background"]}; }}
        QToolBar, QMenuBar, QMenu, QStatusBar {{ background: {c["surface-1"]}; border-color: {c["divider"]}; }}
        QPushButton, QToolButton, QComboBox, QSpinBox {{ background: {c["surface-1"]}; border: 1px solid {c["divider"]}; border-radius: 4px; padding: 6px 10px; min-height: 28px; }}
        QPushButton:hover, QToolButton:hover {{ border-color: {c["primary"]}; }}
        QPushButton:pressed, QToolButton:pressed, QToolButton:checked {{ background: {c["hover"]}; }}
        QPushButton:focus, QToolButton:focus, QComboBox:focus {{ border: 2px solid {c["focus-ring"]}; }}
        QPushButton:disabled, QToolButton:disabled {{ color: {c["disabled"]}; }}
        QSplitter::handle {{ background: {c["divider"]}; width: 1px; height: 1px; }}
        QListWidget, QTreeView {{ background: {c["surface-1"]}; border: none; }}
        QLabel#secondary {{ color: {c["text-secondary"]}; }}
        QLabel#panelTitle {{ font-size: 18px; font-weight: 600; }}
        """
