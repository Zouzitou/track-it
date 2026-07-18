from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from track_it.domain.models import ProjectModel, ProjectSnapshot
from track_it.errors import ProjectValidationError
from track_it.persistence.atomic import atomic_write_text
from track_it.persistence.migrations import migrate
from track_it.utils.paths import ensure_project_suffix


class ProjectStore:
    def create_layout(self, root: Path) -> Path:
        root = ensure_project_suffix(root)
        for relative in ("logs", "cache/frames", "cache/proxy", "masks", "transforms", "prompts"):
            (root / relative).mkdir(parents=True, exist_ok=True)
        return root

    def save(self, root: Path, project: ProjectModel, *, autosave: bool = False) -> Path:
        root = self.create_layout(root)
        project.updated_at = datetime.now(UTC)
        name = "autosave.json" if autosave else "project.json"
        atomic_write_text(root / name, project.model_dump_json(indent=2), backup=not autosave)
        return root / name

    def load(self, root: Path, *, prefer_autosave: bool = False) -> ProjectModel:
        root = ensure_project_suffix(root)
        path = root / (
            "autosave.json"
            if prefer_autosave and (root / "autosave.json").exists()
            else "project.json"
        )
        try:
            raw = path.read_text(encoding="utf-8")
            data = migrate(__import__("json").loads(raw))
            return ProjectModel.model_validate(data)
        except (OSError, ValueError, ValidationError) as exc:
            raise ProjectValidationError(f"Project validation failed: {path}") from exc

    def snapshot(self, root: Path) -> ProjectSnapshot:
        return ProjectSnapshot(root=root.resolve(), project=self.load(root))
