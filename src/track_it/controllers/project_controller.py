from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from track_it.domain.models import ProjectModel, TrackObject
from track_it.persistence.masks import MaskStore
from track_it.persistence.project import ProjectStore


class ProjectController:
    def __init__(self, root: Path, project: ProjectModel) -> None:
        self.root = root
        self.project = project
        self.projects = ProjectStore()
        self.masks = MaskStore(root)
        self.dirty = False

    def add_object(self, name: str) -> TrackObject:
        obj = TrackObject(name=name)
        self.project.objects.append(obj)
        self.dirty = True
        return obj

    def rename_object(self, object_id: UUID, name: str) -> None:
        self.project.object_by_id(object_id).name = name.strip()
        self.dirty = True

    def remove_object(self, object_id: UUID) -> TrackObject:
        obj = self.project.object_by_id(object_id)
        self.project.objects.remove(obj)
        self.dirty = True
        return obj

    def add_correction(self, object_id: UUID, frame_index: int) -> tuple[int, int]:
        key = str(object_id)
        checkpoints = sorted(set(self.project.correction_checkpoints.get(key, [])) | {frame_index})
        self.project.correction_checkpoints[key] = checkpoints
        position = checkpoints.index(frame_index)
        start = checkpoints[position - 1] + 1 if position > 0 else 0
        end = (
            checkpoints[position + 1] - 1
            if position + 1 < len(checkpoints)
            else self.project.video.frame_count - 1
        )
        self.masks.clear_range(object_id, start, end)
        self.project.object_by_id(object_id).corrected_at_frame[frame_index] = datetime.now(UTC)
        self.dirty = True
        return start, end

    def save(self, *, autosave: bool = False) -> Path:
        path = self.projects.save(self.root, self.project, autosave=autosave)
        if not autosave:
            self.dirty = False
        return path
