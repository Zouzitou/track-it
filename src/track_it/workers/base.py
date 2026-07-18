from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from track_it.utils.cancellation import CancellationToken


class JobWorker(QObject):
    """Worker-object for use with QThread; it never references or mutates widgets."""

    progress = Signal(int, int, str)
    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(
        self, job: Callable[[CancellationToken, Callable[[int, int, str], None]], Any]
    ) -> None:
        super().__init__()
        self.job = job
        self.token = CancellationToken()

    @Slot()
    def run(self) -> None:
        try:
            self.completed.emit(self.job(self.token, self._progress))
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()

    @Slot()
    def cancel(self) -> None:
        self.token.cancel()

    def _progress(self, done: int, total: int, message: str) -> None:
        self.progress.emit(done, total, message)
