from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QImage,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import QWidget


class VideoCanvas(QWidget):
    def __init__(self, colors: dict[str, str]) -> None:
        super().__init__()
        self.colors = colors
        self.frame: QImage | None = None
        self.masks: tuple[np.ndarray | None, np.ndarray | None, np.ndarray | None] = (
            None,
            None,
            None,
        )
        self.points: list[tuple[float, float, bool]] = []
        self.echo_enabled = True
        self.zoom = 1.0
        self.pan = QPoint()
        self.setMinimumSize(400, 260)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Video canvas")
        self.setAccessibleDescription("Video preview and subject selection surface")

    def set_frame(self, image: QImage) -> None:
        self.frame = image.copy()
        self.fit()

    def set_masks(
        self,
        current: np.ndarray | None,
        previous: np.ndarray | None = None,
        next_mask: np.ndarray | None = None,
    ) -> None:
        self.masks = (current, previous, next_mask)
        self.update()

    def fit(self) -> None:
        if self.frame:
            self.zoom = (
                min(self.width() / self.frame.width(), self.height() / self.frame.height()) * 0.92
            )
            self.pan = QPoint()
        self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        self.zoom = min(
            16.0, max(0.05, self.zoom * (1.15 if event.angleDelta().y() > 0 else 1 / 1.15))
        )
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.frame is None:
            return
        point = event.position()
        rect = self._frame_rect()
        if rect.contains(point):
            x = (point.x() - rect.x()) / rect.width() * self.frame.width()
            y = (point.y() - rect.y()) / rect.height() * self.frame.height()
            self.points.append((x, y, bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)))
            self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(self.colors["canvas-background"]))
        if self.frame is None:
            painter.setPen(QColor(self.colors["text-secondary"]))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Drop a clip here\n\nYour video preview will appear here.",
            )
            return
        rect = self._frame_rect()
        painter.drawPixmap(rect.toRect(), QPixmap.fromImage(self.frame))
        if self.echo_enabled:
            for mask, color, width in (
                (self.masks[1], self.colors["mask-previous"], 2),
                (self.masks[2], self.colors["mask-next"], 2),
                (self.masks[0], self.colors["mask-current"], 3),
            ):
                if mask is not None:
                    self._paint_edge(painter, mask, rect, color, width)
        for x, y, negative in self.points:
            px = rect.x() + x / self.frame.width() * rect.width()
            py = rect.y() + y / self.frame.height() * rect.height()
            painter.setPen(
                QPen(QColor(self.colors["danger"] if negative else self.colors["success"]), 3)
            )
            painter.drawEllipse(QPoint(round(px), round(py)), 6, 6)

    def _frame_rect(self) -> QRectF:
        assert self.frame is not None
        width, height = self.frame.width() * self.zoom, self.frame.height() * self.zoom
        return QRectF(
            (self.width() - width) / 2 + self.pan.x(),
            (self.height() - height) / 2 + self.pan.y(),
            width,
            height,
        )

    def _paint_edge(
        self, painter: QPainter, mask: np.ndarray, rect: QRectF, color: str, width: int
    ) -> None:
        array = np.asarray(mask, dtype=bool)
        edges = array & ~(
            np.roll(array, 1, 0)
            & np.roll(array, -1, 0)
            & np.roll(array, 1, 1)
            & np.roll(array, -1, 1)
        )
        ys, xs = np.nonzero(edges)
        painter.setPen(QPen(QColor(color), width))
        path = QPainterPath()
        for x, y in zip(
            xs[:: max(1, len(xs) // 2000 + 1)], ys[:: max(1, len(ys) // 2000 + 1)], strict=False
        ):
            px = rect.x() + x / array.shape[1] * rect.width()
            py = rect.y() + y / array.shape[0] * rect.height()
            path.addEllipse(px, py, 1.2, 1.2)
        painter.drawPath(path)
