from __future__ import annotations

from threading import Event

from track_it.errors import TrackingCancelled


class CancellationToken:
    """Thread-safe cooperative cancellation shared by every long-running job."""

    def __init__(self) -> None:
        self._cancelled = Event()

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    def cancel(self) -> None:
        self._cancelled.set()

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled:
            raise TrackingCancelled("The operation was cancelled.")
