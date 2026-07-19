from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path
from typing import Any
from uuid import UUID

import numpy as np
import zstandard as zstd

from track_it.constants import MASK_CHUNK_SIZE
from track_it.errors import CacheCorruptionError
from track_it.persistence.atomic import atomic_write_bytes, atomic_write_text

MAX_COMPRESSED_CHUNK_BYTES = 512 * 1024 * 1024
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_MASK_PIXELS_PER_CHUNK = 512 * 1024 * 1024
MAX_META_ENTRY_BYTES = 128 * 1024


class MaskStore:
    """Checksummed, packed, independently rewritable 32-frame mask chunks."""

    def __init__(self, project_root: Path, chunk_size: int = MASK_CHUNK_SIZE) -> None:
        self.root = project_root / "masks"
        self.chunk_size = chunk_size
        self._compressor = zstd.ZstdCompressor(level=9)
        self._decompressor = zstd.ZstdDecompressor()

    def _object_root(self, object_id: UUID | str) -> Path:
        try:
            normalized = str(UUID(str(object_id)))
        except ValueError as exc:
            raise ValueError("Mask object IDs must be UUIDs") from exc
        return self.root / normalized

    def _chunk_path(self, object_id: UUID | str, chunk: int) -> Path:
        return self._object_root(object_id) / f"chunk-{chunk:06d}.npz.zst"

    def write(self, object_id: UUID | str, frame_index: int, mask: np.ndarray) -> None:
        if frame_index < 0:
            raise ValueError("Frame indices cannot be negative")
        mask = np.asarray(mask, dtype=np.bool_)
        if mask.ndim != 2:
            raise ValueError("Masks must be two-dimensional")
        chunk = frame_index // self.chunk_size
        slot = frame_index % self.chunk_size
        frames = self._read_chunk(object_id, chunk, tolerate_missing=True)
        frames[slot] = mask.copy()
        payload = self._encode(frames)
        path = self._chunk_path(object_id, chunk)
        atomic_write_bytes(path, payload)
        self._update_index(object_id, chunk, path, frames)

    def read(self, object_id: UUID | str, frame_index: int) -> np.ndarray | None:
        if frame_index < 0:
            raise ValueError("Frame indices cannot be negative")
        frames = self._read_chunk(object_id, frame_index // self.chunk_size, tolerate_missing=True)
        mask = frames.get(frame_index % self.chunk_size)
        return None if mask is None else mask.copy()

    def clear_range(self, object_id: UUID | str, start: int, end: int) -> None:
        if start < 0 or end < start:
            raise ValueError("Mask ranges must be ordered, non-negative frame indices")
        for chunk in range(start // self.chunk_size, end // self.chunk_size + 1):
            frames = self._read_chunk(object_id, chunk, tolerate_missing=True)
            changed = False
            for absolute in range(
                max(start, chunk * self.chunk_size), min(end, (chunk + 1) * self.chunk_size - 1) + 1
            ):
                changed |= frames.pop(absolute % self.chunk_size, None) is not None
            if changed:
                path = self._chunk_path(object_id, chunk)
                if frames:
                    atomic_write_bytes(path, self._encode(frames))
                else:
                    path.unlink(missing_ok=True)
                self._update_index(object_id, chunk, path, frames)

    def _encode(self, frames: dict[int, np.ndarray]) -> bytes:
        arrays: dict[str, np.ndarray] = {}
        meta: dict[str, list[int]] = {}
        for slot, mask in sorted(frames.items()):
            arrays[str(slot)] = np.packbits(mask.reshape(-1))
            meta[str(slot)] = list(mask.shape)
        buffer = io.BytesIO()
        np.savez(
            buffer, __meta__=np.frombuffer(json.dumps(meta).encode(), dtype=np.uint8), **arrays
        )
        return self._compressor.compress(buffer.getvalue())

    def _read_chunk(
        self, object_id: UUID | str, chunk: int, *, tolerate_missing: bool
    ) -> dict[int, np.ndarray]:
        path = self._chunk_path(object_id, chunk)
        if not path.exists():
            return {} if tolerate_missing else self._missing(path)
        try:
            if path.stat().st_size > MAX_COMPRESSED_CHUNK_BYTES:
                raise ValueError("Compressed mask chunk exceeds the safety limit")
            payload = self._decompressor.decompress(
                path.read_bytes(), max_output_size=MAX_ARCHIVE_BYTES
            )
            with zipfile.ZipFile(io.BytesIO(payload)) as zip_archive:
                entries = zip_archive.infolist()
                if sum(entry.file_size for entry in entries) > MAX_ARCHIVE_BYTES:
                    raise ValueError("Mask archive exceeds the safety limit")
                meta_entry = next(
                    (entry for entry in entries if entry.filename == "__meta__.npy"), None
                )
                if meta_entry is None or meta_entry.file_size > MAX_META_ENTRY_BYTES:
                    raise ValueError("Mask metadata is missing or too large")
            with np.load(io.BytesIO(payload), allow_pickle=False) as archive:
                meta_array = archive["__meta__"]
                if meta_array.dtype != np.uint8 or meta_array.ndim != 1:
                    raise ValueError("Mask metadata has an invalid representation")
                meta = json.loads(bytes(meta_array).decode())
                if not isinstance(meta, dict) or len(meta) > self.chunk_size:
                    raise ValueError("Mask metadata has an invalid frame count")
                if set(archive.files) != {"__meta__", *meta}:
                    raise ValueError("Mask archive contains unexpected arrays")
                decoded: dict[int, np.ndarray] = {}
                total_pixels = 0
                for raw_slot, shape in meta.items():
                    slot = int(raw_slot)
                    if raw_slot != str(slot) or not 0 <= slot < self.chunk_size:
                        raise ValueError("Mask metadata contains an invalid frame slot")
                    if (
                        not isinstance(shape, list)
                        or len(shape) != 2
                        or any(type(dimension) is not int or dimension <= 0 for dimension in shape)
                    ):
                        raise ValueError("Mask metadata contains an invalid shape")
                    pixels = shape[0] * shape[1]
                    total_pixels += pixels
                    if total_pixels > MAX_MASK_PIXELS_PER_CHUNK:
                        raise ValueError("Mask chunk exceeds the decoded pixel safety limit")
                    packed = archive[raw_slot]
                    if (
                        packed.dtype != np.uint8
                        or packed.ndim != 1
                        or packed.size != (pixels + 7) // 8
                    ):
                        raise ValueError("Mask data does not match its declared shape")
                    decoded[slot] = np.unpackbits(packed, count=pixels).reshape(shape).astype(bool)
                return decoded
        except (
            OSError,
            TypeError,
            ValueError,
            zstd.ZstdError,
            zipfile.BadZipFile,
            KeyError,
        ) as exc:
            raise CacheCorruptionError(f"Mask chunk is corrupt: {path}") from exc

    def _missing(self, path: Path) -> dict[int, np.ndarray]:
        raise CacheCorruptionError(f"Mask chunk is missing: {path}")

    def _update_index(
        self, object_id: UUID | str, chunk: int, path: Path, frames: dict[int, np.ndarray]
    ) -> None:
        root = self._object_root(object_id)
        root.mkdir(parents=True, exist_ok=True)
        index_path = root / "index.json"
        index: dict[str, Any] = (
            json.loads(index_path.read_text(encoding="utf-8"))
            if index_path.exists()
            else {"chunk_size": self.chunk_size, "chunks": {}}
        )
        if frames and path.exists():
            index["chunks"][str(chunk)] = {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "frames": sorted(frames),
            }
        else:
            index["chunks"].pop(str(chunk), None)
        atomic_write_text(index_path, json.dumps(index, indent=2, sort_keys=True))
