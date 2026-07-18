from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen, QPolygon
from PySide6.QtWidgets import QWidget


class TimelineWidget(QWidget):
    frameSelected = Signal(int)

    def __init__(self, colors: dict[str, str]) -> None:
        super().__init__()
        self.colors = colors
        self.frame_count = 1
        self.current_frame = 0
        self.corrections: set[int] = set()
        self.scene_cuts: set[int] = set()
        self.confidence: dict[int, float] = {}
        self.setMinimumHeight(120)
        self.setAccessibleName("Tracking timeline")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_frame_count(self, count: int) -> None:
        self.frame_count = max(1, count)
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(self.colors["surface-2"]))
        painter.setPen(QPen(QColor(self.colors["divider"]), 1))
        painter.drawLine(0, 28, self.width(), 28)
        visible = min(self.frame_count, max(1, self.width() // 3))
        step = self.width() / visible
        start = max(0, min(self.current_frame - visible // 2, self.frame_count - visible))
        for offset in range(visible):
            frame = start + offset
            x = int(offset * step)
            value = self.confidence.get(frame)
            if value is not None:
                color = (
                    self.colors["confidence-good"]
                    if value >= 0.75
                    else self.colors["confidence-review"]
                    if value >= 0.45
                    else self.colors["confidence-bad"]
                )
                painter.fillRect(x, 72, max(1, int(step)), 22, QColor(color))
            if frame in self.scene_cuts:
                painter.setPen(QPen(QColor(self.colors["scene-cut"]), 2, Qt.PenStyle.DashLine))
                painter.drawLine(x, 34, x, self.height())
            if frame in self.corrections:
                painter.setBrush(QColor(self.colors["correction"]))
                painter.drawPolygon(QPolygon([QPoint(x, 44), QPoint(x + 5, 54), QPoint(x - 5, 54)]))
        cursor_x = int((self.current_frame - start) * step)
        painter.setPen(QPen(QColor(self.colors["primary"]), 2))
        painter.drawLine(cursor_x, 0, cursor_x, self.height())
        painter.setPen(QColor(self.colors["text-secondary"]))
        painter.drawText(
            12,
            20,
            f"FRAME {self.current_frame + 1:,} / {self.frame_count:,}   • corrections   ┆ scene cuts   ▰ confidence",
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        frame = min(
            self.frame_count - 1,
            max(0, round(event.position().x() / max(1, self.width()) * self.frame_count)),
        )
        self.current_frame = frame
        self.frameSelected.emit(frame)
        self.update()
