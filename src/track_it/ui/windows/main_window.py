from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import av
from PySide6.QtCore import QSettings, Qt, QThread
from PySide6.QtGui import QAction, QCloseEvent, QImage, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from track_it.domain.models import FrameRecord, VideoMetadata
from track_it.media.index import index_video
from track_it.ui.icons.provider import MaterialIconProvider
from track_it.ui.theme.manager import ThemeManager
from track_it.ui.widgets.canvas import VideoCanvas
from track_it.ui.widgets.timeline import TimelineWidget
from track_it.utils.cancellation import CancellationToken
from track_it.workers.base import JobWorker


class MainWindow(QMainWindow):
    def __init__(self, theme: ThemeManager) -> None:
        super().__init__()
        self.theme = theme
        self.icons = MaterialIconProvider()
        self.settings = QSettings()
        self._threads: set[QThread] = set()
        self._video_path: Path | None = None
        self.setWindowTitle("Track it — Untitled")
        self.setMinimumSize(1100, 700)
        self.resize(1440, 900)
        self._build_actions()
        self._build_menu()
        self._build_ui()
        self.theme.themeChanged.connect(self._theme_changed)
        self._restore_layout()
        self._theme_changed(self.theme.effective, self.theme.revision)

    def _build_actions(self) -> None:
        self.open_action = QAction("Import video", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.import_video)
        self.theme_action = QAction("Switch theme", self)
        self.theme_action.triggered.connect(self.theme.toggle)
        self.export_action = QAction("Export", self)
        self.export_action.setEnabled(False)
        self.export_action.triggered.connect(self._export_explained)

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.export_action)
        file_menu.addSeparator()
        file_menu.addAction("E&xit", self.close)
        edit_menu = self.menuBar().addMenu("&Edit")
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.setEnabled(False)
        edit_menu.addAction(undo_action)
        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction(self.theme_action)
        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction("Open diagnostics", self._show_diagnostics)
        help_menu.addAction("About Track it", self._about)

    def _button(
        self, icon: str, text: str, tooltip: str, *, checkable: bool = False
    ) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        button.setToolTip(tooltip)
        button.setAccessibleName(text or tooltip.split("(", 1)[0].split("·", 1)[0].strip())
        button.setCheckable(checkable)
        button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextUnderIcon
            if not text
            else Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        button.setMinimumSize(44, 44)
        button.setProperty("iconName", icon)
        return button

    def _build_ui(self) -> None:
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(52)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 4, 12, 4)
        import_button = self._button("folder_open", "Import video", "Import video (Ctrl+O)")
        import_button.clicked.connect(self.import_video)
        self.project_title = QLabel("UNTITLED WORKBENCH")
        self.project_title.setObjectName("panelTitle")
        header_layout.addWidget(import_button)
        header_layout.addWidget(self.project_title)
        header_layout.addStretch()
        self.model_label = QLabel("SAM 2.1 Small • model not downloaded")
        self.model_label.setObjectName("secondary")
        header_layout.addWidget(self.model_label)
        self.theme_button = self._button("light_mode", "", "Use light theme · Theme settings")
        self.theme_button.clicked.connect(self.theme.toggle)
        header_layout.addWidget(self.theme_button)
        export_button = self._button("upload_file", "Export", "Export masks or motion data")
        export_button.clicked.connect(self._export_explained)
        header_layout.addWidget(export_button)
        outer.addWidget(header)

        workspace_split = QSplitter(Qt.Orientation.Horizontal)
        left = QFrame()
        left.setFixedWidth(56)
        tool_layout = QVBoxLayout(left)
        tool_layout.setContentsMargins(4, 8, 4, 8)
        tool_layout.setSpacing(8)
        self.tool_buttons: list[QToolButton] = []
        for icon, name, tip in (
            ("ads_click", "Add", "Add to selection"),
            ("do_not_disturb_on", "Remove", "Remove from selection (Alt+click)"),
            ("crop_free", "Box", "Box prompt"),
            ("brush", "Brush", "Add-mask brush"),
            ("ink_eraser", "Erase", "Erase-mask brush"),
            ("pan_tool", "Pan", "Pan canvas"),
        ):
            button = self._button(icon, "", tip, checkable=True)
            button.setAccessibleName(name)
            button.setFixedSize(48, 48)
            tool_layout.addWidget(button)
            self.tool_buttons.append(button)
        self.tool_buttons[0].setChecked(True)
        tool_layout.addStretch()

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        self.canvas = VideoCanvas(self.theme.colors)
        center_layout.addWidget(self.canvas, 1)
        transport = QWidget()
        transport.setFixedHeight(48)
        transport_layout = QHBoxLayout(transport)
        transport_layout.setContentsMargins(12, 2, 12, 2)
        for icon, text, tip in (
            ("skip_previous", "", "Previous frame (Left)"),
            ("play_arrow", "", "Play or pause (Space)"),
            ("skip_next", "", "Next frame (Right)"),
            ("arrow_back", "Track backward", "Track backward"),
            ("arrow_forward", "Track forward", "Track forward"),
            ("swap_horiz", "Track both ways", "Track both ways"),
            ("stop_circle", "Stop", "Stop tracking"),
        ):
            button = self._button(icon, text, tip)
            if text.startswith("Track") or text == "Stop":
                button.setEnabled(False)
            transport_layout.addWidget(button)
        transport_layout.addStretch()
        self.timecode = QLabel("00:00:00.000  •  F 00000001")
        self.timecode.setFont(self.theme.data_font())
        transport_layout.addWidget(self.timecode)
        center_layout.addWidget(transport)

        inspector = QWidget()
        inspector.setMinimumWidth(280)
        inspector.setMaximumWidth(460)
        inspector_layout = QVBoxLayout(inspector)
        inspector_layout.setContentsMargins(16, 16, 16, 16)
        title = QLabel("OBJECTS & MASK")
        title.setObjectName("panelTitle")
        inspector_layout.addWidget(title)
        self.objects = QListWidget()
        self.objects.setAccessibleName("Tracked objects")
        self.objects.addItem("Objects appear here after you select and accept a subject.")
        inspector_layout.addWidget(self.objects)
        add_object = QPushButton("Add object")
        add_object.clicked.connect(self._add_object)
        inspector_layout.addWidget(add_object)
        onion = self._button(
            "layers", "Onion skin", "Show previous and next mask edges", checkable=True
        )
        onion.setChecked(True)
        onion.toggled.connect(self._toggle_echo)
        inspector_layout.addWidget(onion)
        inspector_layout.addStretch()

        workspace_split.addWidget(left)
        workspace_split.addWidget(center)
        workspace_split.addWidget(inspector)
        workspace_split.setSizes([56, 1000, 320])

        vertical = QSplitter(Qt.Orientation.Vertical)
        vertical.addWidget(workspace_split)
        self.timeline = TimelineWidget(self.theme.colors)
        vertical.addWidget(self.timeline)
        vertical.setSizes([620, 196])
        self.workspace_split = workspace_split
        self.vertical_split = vertical
        outer.addWidget(vertical, 1)
        self.setCentralWidget(root)

        status = QStatusBar()
        status.setFixedHeight(28)
        self.operation = QLabel("Ready")
        status.addWidget(QLabel("SAM 2 • Small • CUDA • 8 GB"))
        status.addPermanentWidget(self.operation, 1)
        privacy = QLabel("Local only")
        privacy.setAccessibleDescription("Videos and tracking data are never uploaded")
        status.addPermanentWidget(privacy)
        self.setStatusBar(status)

    def import_video(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import video", "", "Video files (*.mp4 *.mov *.mkv *.avi *.webm);;All files (*)"
        )
        if not filename:
            return
        path = Path(filename)
        self.operation.setText("Indexing video…")
        self.open_action.setEnabled(False)

        def job(
            _token: CancellationToken, progress: Callable[[int, int, str], None]
        ) -> tuple[VideoMetadata, list[FrameRecord], QImage]:
            progress(0, 0, "Reading presentation timestamps")
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

        thread = QThread(self)
        worker = JobWorker(job)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.completed.connect(self._video_indexed)
        worker.failed.connect(self._job_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._threads.discard(thread))
        self._threads.add(thread)
        thread.start()

    def _video_indexed(self, result: object) -> None:
        metadata, records, image = cast(tuple[VideoMetadata, list[FrameRecord], QImage], result)
        self._video_path = Path(metadata.path)
        self.project_title.setText(self._video_path.stem.upper())
        self.setWindowTitle(f"Track it — {self._video_path.stem}")
        self.canvas.set_frame(image)
        self.timeline.set_frame_count(len(records))
        self.export_action.setEnabled(True)
        self.operation.setText(
            f"Indexed {len(records):,} frames • {'VFR' if metadata.vfr else 'CFR'}"
        )
        self.open_action.setEnabled(True)

    def _job_failed(self, message: str) -> None:
        self.open_action.setEnabled(True)
        self.operation.setText("Import failed")
        QMessageBox.critical(self, "Video could not be opened", message)

    def _add_object(self) -> None:
        if self.objects.count() == 1 and self.objects.item(0).text().startswith("Objects appear"):
            self.objects.clear()
        self.objects.addItem(f"Subject {self.objects.count() + 1}  •  No mask on this frame")

    def _toggle_echo(self, checked: bool) -> None:
        self.canvas.echo_enabled = checked
        self.canvas.update()

    def _export_explained(self) -> None:
        QMessageBox.information(
            self,
            "Export",
            "Open a saved project to export masks, transparent media, or motion data. Audio handling and output validation are shown before encoding.",
        )

    def _show_diagnostics(self) -> None:
        from track_it.diagnostics import collect_diagnostics

        QMessageBox.information(self, "Diagnostics", collect_diagnostics(redact=True))

    def _about(self) -> None:
        QMessageBox.about(
            self,
            "About Track it",
            "Track it 0.1.0-alpha.1\nFree local AI masking and motion tracking.\nApache License 2.0",
        )

    def _theme_changed(self, _effective: str, _revision: int) -> None:
        self.icons.clear()
        colors = self.theme.colors
        self.canvas.colors = colors
        self.timeline.colors = colors
        self.theme_button.setProperty(
            "iconName", "light_mode" if self.theme.effective == "dark" else "dark_mode"
        )
        self.theme_button.setToolTip(
            "Use light theme · Theme settings"
            if self.theme.effective == "dark"
            else "Use dark theme · Theme settings"
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
        self.timeline.update()

    def _restore_layout(self) -> None:
        geometry = self.settings.value("window/geometry")
        state = self.settings.value("window/state")
        if geometry:
            self.restoreGeometry(geometry)
        if state:
            self.restoreState(state)
        horizontal = self.settings.value("window/horizontal_split")
        vertical = self.settings.value("window/vertical_split")
        if horizontal:
            self.workspace_split.restoreState(horizontal)
        if vertical:
            self.vertical_split.restoreState(vertical)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._threads:
            answer = QMessageBox.question(
                self, "Operation in progress", "Stop the current operation and close Track it?"
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            for thread in self._threads:
                thread.requestInterruption()
        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("window/state", self.saveState())
        self.settings.setValue("window/horizontal_split", self.workspace_split.saveState())
        self.settings.setValue("window/vertical_split", self.vertical_split.saveState())
        event.accept()
