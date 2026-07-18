from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from track_it.constants import ASSET_ROOT

log = logging.getLogger(__name__)


class MaterialIconProvider:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or ASSET_ROOT / "icons" / "material-symbols"
        self._cache: dict[tuple[object, ...], QIcon] = {}

    def clear(self) -> None:
        self._cache.clear()

    def icon(
        self, name: str, color: str, size: int = 20, dpr: float = 1.0, revision: int = 0
    ) -> QIcon:
        key = (name, color, size, round(dpr, 2), revision)
        if key in self._cache:
            return self._cache[key]
        source = self.root / f"{name}.svg"
        physical = max(1, round(size * dpr))
        pixmap = QPixmap(physical, physical)
        pixmap.setDevicePixelRatio(dpr)
        pixmap.fill(Qt.GlobalColor.transparent)
        if source.exists():
            renderer = QSvgRenderer(QByteArray(source.read_bytes()))
            painter = QPainter(pixmap)
            renderer.render(painter, QRectF(0, 0, size, size))
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(QRectF(0, 0, size, size), QColor(color))
            painter.end()
        else:
            log.warning("Missing Material Symbol: %s", name)
            painter = QPainter(pixmap)
            painter.setPen(QColor(color))
            painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "?")
            painter.end()
        icon = QIcon(pixmap)
        self._cache[key] = icon
        return icon
