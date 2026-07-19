from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest

from track_it.domain.models import ProjectModel
from track_it.errors import CacheCorruptionError, ProjectMigrationError
from track_it.persistence.fingerprint import source_fingerprint
from track_it.persistence.masks import MaskStore
from track_it.persistence.migrations import migrate
from track_it.persistence.project import ProjectStore


def test_fingerprint_uses_content_and_metadata(tmp_path: Path) -> None:
    source = tmp_path / "a & ü.bin"
    source.write_bytes(b"x" * 1024)
    first = source_fingerprint(source, {"stream": 0})
    second = source_fingerprint(source, {"stream": 1})
    assert len(first) == 64
    assert first != second


def test_mask_chunks_roundtrip_and_bounded_clear(tmp_path: Path) -> None:
    store = MaskStore(tmp_path, chunk_size=4)
    oid = uuid4()
    for frame in range(7):
        mask = np.zeros((8, 9), dtype=bool)
        mask[frame % 4 : frame % 4 + 2, 2:6] = True
        store.write(oid, frame, mask)
    assert store.read(oid, 5).sum() == 8
    store.clear_range(oid, 2, 5)
    assert store.read(oid, 1) is not None
    assert store.read(oid, 2) is None
    assert store.read(oid, 5) is None
    assert store.read(oid, 6) is not None


def test_corrupt_mask_chunk_is_rejected(tmp_path: Path) -> None:
    oid = uuid4()
    store = MaskStore(tmp_path)
    store.write(oid, 0, np.ones((2, 2), dtype=bool))
    chunk = tmp_path / "masks" / str(oid) / "chunk-000000.npz.zst"
    chunk.write_bytes(b"bad")
    with pytest.raises(CacheCorruptionError):
        store.read(oid, 0)


def test_mask_store_rejects_path_traversal_and_invalid_ranges(tmp_path: Path) -> None:
    store = MaskStore(tmp_path)
    with pytest.raises(ValueError, match="UUID"):
        store.read("../../outside", 0)
    with pytest.raises(ValueError, match="negative"):
        store.read(uuid4(), -1)
    with pytest.raises(ValueError, match="ordered"):
        store.clear_range(uuid4(), 5, 4)


def test_project_atomic_roundtrip(tmp_path: Path, video_metadata: object) -> None:
    root = tmp_path / "Unicode 🎬 & quotes.trackit"
    model = ProjectModel(app_version="0.1.0-alpha.1", video=video_metadata)
    store = ProjectStore()
    store.save(root, model)
    loaded = store.load(root)
    assert loaded.video.fingerprint == "a" * 64
    assert (root / "cache" / "frames").is_dir()


def test_project_rejects_oversized_metadata(tmp_path: Path, monkeypatch) -> None:
    import track_it.persistence.project as project_module

    root = tmp_path / "oversized.trackit"
    root.mkdir()
    (root / "project.json").write_bytes(b"{}")
    monkeypatch.setattr(project_module, "MAX_PROJECT_JSON_BYTES", 1)
    with pytest.raises(project_module.ProjectValidationError, match="validation failed"):
        ProjectStore().load(root)


def test_unknown_migration_fails_without_mutating() -> None:
    data = {"schema_version": 0, "value": [1]}
    with pytest.raises(ProjectMigrationError):
        migrate(data)
    assert data == {"schema_version": 0, "value": [1]}
