from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import av
from PySide6.QtCore import QSettings, Qt, QThread, QUrl
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QDesktopServices,
    QDragEnterEvent,
    QDropEvent,
    QImage,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStatusBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from track_it.domain.models import FrameRecord, VideoMetadata
from track_it.export.green_screen import (
    SUPPORTED_VIDEO_SUFFIXES,
    GreenScreenProcessor,
    GreenScreenResult,
    suggested_output_path,
)
from track_it.media.index import index_video
from track_it.ui.icons.provider import MaterialIconProvider
from track_it.ui.theme.manager import ThemeManager
from track_it.ui.widgets.canvas import VideoCanvas
from track_it.utils.cancellation import CancellationToken
from track_it.workers.base import JobWorker


class MainWindow(QMainWindow):
    def __init__(self, theme: ThemeManager) -> None:
        super().__init__()
        self.theme = theme
        self.icons = MaterialIconProvider()
        self.settings = QSettings()
        self._threads: set[QThread] = set()
        self._workers: set[JobWorker] = set()
        self._active_worker: JobWorker | None = None
        self._close_requested = False
        self._video_path: Path | None = None
        self._output_path: Path | None = None
        self.setWindowTitle("Track it — Green screen maker")
        self.setMinimumSize(900, 620)
        self.resize(1120, 720)
        self.setAcceptDrops(True)
        self._build_actions()
        self._build_menu()
        self._build_ui()
        self.theme.themeChanged.connect(self._theme_changed)
        self._restore_layout()
        self._theme_changed(self.theme.effective, self.theme.revision)

    def _build_actions(self) -> None:
        self.open_action = QAction("Choose clip…", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.import_video)
        self.theme_action = QAction("Switch theme", self)
        self.theme_action.triggered.connect(self.theme.toggle)
        self.create_action = QAction("Create green screen…", self)
        self.create_action.setEnabled(False)
        self.create_action.triggered.connect(self.create_green_screen)
        self.export_action = self.create_action

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.create_action)
        file_menu.addSeparator()
        file_menu.addAction("E&xit", self.close)
        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction(self.theme_action)
        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction("Diagnostics", self._show_diagnostics)
        help_menu.addAction("About Track it", self._about)

    def _button(self, icon: str, text: str, tooltip: str) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        button.setToolTip(tooltip)
        button.setAccessibleName(text or tooltip)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setMinimumSize(42, 42)
        button.setProperty("iconName", icon)
        return button

    def _build_ui(self) -> None:
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(28, 20, 28, 24)
        outer.setSpacing(20)

        header = QHBoxLayout()
        brand = QVBoxLayout()
        brand.setSpacing(0)
        title = QLabel("Track it")
        title.setObjectName("brandTitle")
        subtitle = QLabel("Turn any clip into a green-screen video")
        subtitle.setObjectName("secondary")
        brand.addWidget(title)
        brand.addWidget(subtitle)
        header.addLayout(brand)
        header.addStretch()
        local = QLabel("100% local  •  no uploads")
        local.setObjectName("privacyPill")
        header.addWidget(local)
        self.theme_button = self._button("light_mode", "", "Switch color theme")
        self.theme_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.theme_button.clicked.connect(self.theme.toggle)
        header.addWidget(self.theme_button)
        outer.addLayout(header)

        step_row = QHBoxLayout()
        step_row.setSpacing(8)
        self.step_labels: list[QLabel] = []
        for number, text in ((1, "Choose clip"), (2, "Create"), (3, "Done")):
            label = QLabel(f"{number}  {text}")
            label.setObjectName("activeStep" if number == 1 else "step")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            step_row.addWidget(label)
            self.step_labels.append(label)
        outer.addLayout(step_row)

        content = QHBoxLayout()
        content.setSpacing(24)
        preview_card = QFrame()
        preview_card.setObjectName("previewCard")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(10, 10, 10, 10)
        self.canvas = VideoCanvas(self.theme.colors)
        preview_layout.addWidget(self.canvas, 1)
        content.addWidget(preview_card, 3)

        controls = QFrame()
        controls.setObjectName("controlCard")
        controls.setMinimumWidth(330)
        controls.setMaximumWidth(410)
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(28, 28, 28, 28)
        controls_layout.setSpacing(14)
        self.project_title = QLabel("Drop your clip here")
        self.project_title.setObjectName("panelTitle")
        self.project_title.setWordWrap(True)
        controls_layout.addWidget(self.project_title)
        self.clip_details = QLabel(
            "MP4, MOV, MKV, AVI, WebM, or M4V\n\nTrack it automatically finds the main subject."
        )
        self.clip_details.setObjectName("secondary")
        self.clip_details.setWordWrap(True)
        controls_layout.addWidget(self.clip_details)

        self.choose_button = QPushButton("Choose a clip")
        self.choose_button.setObjectName("secondaryButton")
        self.choose_button.setMinimumHeight(48)
        self.choose_button.clicked.connect(self.import_video)
        controls_layout.addWidget(self.choose_button)

        self.create_button = QPushButton("Create green screen")
        self.create_button.setObjectName("primaryButton")
        self.create_button.setAccessibleDescription(
            "Automatically isolate the main subject and save an MP4 with a green background"
        )
        self.create_button.setMinimumHeight(56)
        self.create_button.setEnabled(False)
        self.create_button.clicked.connect(self.create_green_screen)
        controls_layout.addWidget(self.create_button)

        self.progress = QProgressBar()
        self.progress.setRange(0, 5)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        controls_layout.addWidget(self.progress)
        self.operation = QLabel("Ready when you are")
        self.operation.setObjectName("statusText")
        self.operation.setWordWrap(True)
        controls_layout.addWidget(self.operation)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_processing)
        self.cancel_button.hide()
        controls_layout.addWidget(self.cancel_button)

        self.open_folder_button = QPushButton("Show finished video")
        self.open_folder_button.setMinimumHeight(44)
        self.open_folder_button.clicked.connect(self.open_output_folder)
        self.open_folder_button.hide()
        controls_layout.addWidget(self.open_folder_button)
        controls_layout.addStretch()

        first_run = QLabel(
            "First use downloads a verified 176 MB AI model. Processing stays on this computer."
        )
        first_run.setObjectName("finePrint")
        first_run.setWordWrap(True)
        controls_layout.addWidget(first_run)
        content.addWidget(controls, 2)
        outer.addLayout(content, 1)
        self.setCentralWidget(root)

        status = QStatusBar()
        status.setFixedHeight(26)
        status.showMessage("Tip: you can drag and drop a video anywhere in this window")
        self.setStatusBar(status)

    def import_video(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose a clip",
            "",
            "Video files (*.mp4 *.mov *.mkv *.avi *.webm *.m4v);;All files (*)",
        )
        if filename:
            self._begin_import(Path(filename))

    def _begin_import(self, path: Path) -> None:
        if path.suffix.lower() not in SUPPORTED_VIDEO_SUFFIXES:
            QMessageBox.warning(
                self, "That file is not a video", "Choose an MP4, MOV, MKV, AVI, WebM, or M4V clip."
            )
            return
        self._set_busy(True, "Reading your clip…", cancellable=False)

        def job(
            _token: CancellationToken, progress: Callable[[int, int, str], None]
        ) -> tuple[VideoMetadata, list[FrameRecord], QImage]:
            progress(0, 0, "Reading your clip")
            metadata, records = index_video(path)
            with av.open(str(path)) as container:
                frame = next(container.decode(video=metadata.stream_index))
                array = frame.to_ndarray(format="rgb24")
                image = QImage(
                    array.data,
                    array.shape[1],
                    array.shape[0],
                    array.strides[0],
                    QImage.Format.Format_RGB888,
                ).copy()
            return metadata, records, image

        self._run_job(job, self._video_indexed, self._import_failed)

    def _video_indexed(self, result: object) -> None:
        metadata, records, image = cast(tuple[VideoMetadata, list[FrameRecord], QImage], result)
        self._video_path = Path(metadata.path)
        self._output_path = None
        self.project_title.setText(self._video_path.name)
        duration = self._duration_text(metadata.duration)
        self.clip_details.setText(
            f"{metadata.display_width} x {metadata.display_height}  •  {duration}  •  "
            f"{len(records):,} frames\n\nYour clip is ready. Track it will automatically use the main subject."
        )
        self.canvas.set_frame(image)
        self.create_button.setEnabled(True)
        self.create_action.setEnabled(True)
        self.choose_button.setText("Choose a different clip")
        self.operation.setText("Ready to create")
        self.open_folder_button.hide()
        self._set_step(2)
        self._set_busy(False)

    def create_green_screen(self) -> None:
        if self._video_path is None:
            return
        default = suggested_output_path(self._video_path)
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save your green-screen video",
            str(default),
            "MP4 video (*.mp4)",
        )
        if not filename:
            return
        output = Path(filename)
        if output.suffix.lower() != ".mp4":
            output = output.with_suffix(".mp4")
        self._start_green_screen(output)

    def _start_green_screen(self, output: Path) -> None:
        if self._video_path is None:
            return
        input_path = self._video_path
        self._output_path = output
        self._set_busy(True, "Starting…", cancellable=True)
        self.progress.setRange(0, 5)
        self.progress.setValue(0)
        self.progress.show()

        def job(
            token: CancellationToken, progress: Callable[[int, int, str], None]
        ) -> GreenScreenResult:
            return GreenScreenProcessor().create(input_path, output, token, progress)

        self._run_job(job, self._green_screen_ready, self._processing_failed)

    def _run_job(
        self,
        job: Callable[[CancellationToken, Callable[[int, int, str], None]], Any],
        completed: Callable[[object], None],
        failed: Callable[[str], None],
    ) -> None:
        thread = QThread(self)
        worker = JobWorker(job)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._job_progress)
        worker.completed.connect(completed)
        worker.failed.connect(failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(lambda: self._workers.discard(worker))
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._thread_finished(thread))
        self._threads.add(thread)
        self._workers.add(worker)
        self._active_worker = worker
        thread.start()

    def _job_progress(self, done: int, total: int, message: str) -> None:
        self.operation.setText(message)
        if total > 0:
            self.progress.setRange(0, total)
            self.progress.setValue(done)
        else:
            self.progress.setRange(0, 0)

    def _green_screen_ready(self, result: object) -> None:
        created = cast(GreenScreenResult, result)
        self._output_path = created.output_path
        self.project_title.setText("Your green-screen video is ready")
        self.clip_details.setText(
            f"{created.output_path.name}\n\n{created.frame_count:,} frames processed locally."
        )
        self.operation.setText("Done — your original clip was not changed")
        self.progress.setRange(0, 5)
        self.progress.setValue(5)
        self.open_folder_button.show()
        self._set_step(3)
        self._set_busy(False)

    def _import_failed(self, message: str) -> None:
        self.operation.setText("That clip could not be opened")
        self._set_busy(False)
        QMessageBox.critical(self, "Clip could not be opened", message)

    def _processing_failed(self, message: str) -> None:
        cancelled = "cancel" in message.lower()
        self.operation.setText(
            "Cancelled — your original clip was not changed"
            if cancelled
            else "Could not create the green-screen video"
        )
        self.progress.hide()
        self._set_busy(False)
        if not cancelled:
            QMessageBox.critical(self, "Green-screen creation stopped", message)

    def _set_busy(
        self, busy: bool, message: str | None = None, *, cancellable: bool = False
    ) -> None:
        self.open_action.setEnabled(not busy)
        self.choose_button.setEnabled(not busy)
        self.create_button.setEnabled(not busy and self._video_path is not None)
        self.create_action.setEnabled(not busy and self._video_path is not None)
        self.cancel_button.setVisible(busy and cancellable)
        if not busy:
            self._active_worker = None
        if message:
            self.operation.setText(message)

    def cancel_processing(self) -> None:
        if self._active_worker is not None:
            self._active_worker.token.cancel()
            self.cancel_button.setEnabled(False)
            self.operation.setText("Stopping safely…")

    def _thread_finished(self, thread: QThread) -> None:
        self._threads.discard(thread)
        if self._close_requested and not self._threads:
            self._close_requested = False
            self.close()

    def open_output_folder(self) -> None:
        if self._output_path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._output_path.parent)))

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        if len(paths) == 1 and paths[0].suffix.lower() in SUPPORTED_VIDEO_SUFFIXES:
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        if len(paths) == 1:
            event.acceptProposedAction()
            self._begin_import(paths[0])

    def _set_step(self, active: int) -> None:
        for index, label in enumerate(self.step_labels, start=1):
            label.setObjectName(
                "activeStep" if index == active else "completeStep" if index < active else "step"
            )
            label.style().unpolish(label)
            label.style().polish(label)

    @staticmethod
    def _duration_text(seconds: float) -> str:
        rounded = max(0, round(seconds))
        minutes, secs = divmod(rounded, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"

    def _show_diagnostics(self) -> None:
        from track_it.diagnostics import collect_diagnostics

        QMessageBox.information(self, "Diagnostics", collect_diagnostics(redact=True))

    def _about(self) -> None:
        QMessageBox.about(
            self,
            "About Track it",
            "Track it 0.1.0-alpha.1\nAutomatic local green-screen video maker.\nApache License 2.0",
        )

    def _theme_changed(self, _effective: str, _revision: int) -> None:
        self.icons.clear()
        colors = self.theme.colors
        self.canvas.colors = colors
        self.theme_button.setProperty(
            "iconName", "light_mode" if self.theme.effective == "dark" else "dark_mode"
        )
        self.theme_button.setToolTip(
            "Use light theme" if self.theme.effective == "dark" else "Use dark theme"
        )
        for button in self.findChildren(QToolButton):
            name = button.property("iconName")
            if name:
                button.setIcon(
                    self.icons.icon(
                        str(name),
                        colors["on-surface"],
                        20,
                        self.devicePixelRatioF(),
                        self.theme.revision,
                    )
                )
        self.canvas.update()

    def _restore_layout(self) -> None:
        geometry = self.settings.value("window/simple_geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._threads:
            answer = QMessageBox.question(
                self,
                "Operation in progress",
                "Stop the current operation and close Track it?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            for worker in self._workers:
                worker.token.cancel()
            self._close_requested = True
            self.operation.setText("Stopping safely before closing…")
            event.ignore()
            return
        self.settings.setValue("window/simple_geometry", self.saveGeometry())
        event.accept()
