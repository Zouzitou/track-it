from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx
from filelock import FileLock
from platformdirs import user_data_path

from track_it.errors import ModelIntegrityError
from track_it.persistence.atomic import atomic_write_text
from track_it.utils.cancellation import CancellationToken


@dataclass(frozen=True, slots=True)
class ModelSpec:
    id: str
    filename: str
    url: str
    config: str
    sha256: str | None
    minimum_size: int
    license: str
    vram_gb: int
    upstream_sha: str


SAM2_SMALL = ModelSpec(
    "sam2.1-small",
    "sam2.1_hiera_small.pt",
    "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_small.pt",
    "configs/sam2.1/sam2.1_hiera_s.yaml",
    None,
    150_000_000,
    "Apache-2.0",
    4,
    "2b90b9f5ceec907a1c18123530e92e794ad901a4",
)
MODELS = {SAM2_SMALL.id: SAM2_SMALL}


def select_sam_model(vram_gb: float | None, device: str) -> str:
    if device == "cpu" or vram_gb is None or vram_gb < 4:
        return "sam2.1-tiny"
    if vram_gb < 10:
        return "sam2.1-small"
    if vram_gb < 16:
        return "sam2.1-base-plus"
    return "sam2.1-large"


class ModelManager:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or user_data_path("TrackIt", "TrackItOpenSource") / "models"
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, model_id: str) -> Path:
        return self.root / MODELS[model_id].filename

    def verify(self, model_id: str) -> str:
        spec, path = MODELS[model_id], self.path_for(model_id)
        if not path.exists() or path.stat().st_size < spec.minimum_size:
            raise ModelIntegrityError(
                "This model file failed verification. Delete it and download it again."
            )
        digest = _sha256(path)
        if spec.sha256 and digest != spec.sha256:
            raise ModelIntegrityError(
                "This model file failed verification. Delete it and download it again."
            )
        return digest

    def download(
        self,
        model_id: str,
        token: CancellationToken,
        progress: Callable[[int, int], None] | None = None,
    ) -> Path:
        spec = MODELS[model_id]
        destination = self.path_for(model_id)
        partial = destination.with_suffix(destination.suffix + ".partial")
        with FileLock(str(destination) + ".lock"):
            offset = partial.stat().st_size if partial.exists() else 0
            headers = {"Range": f"bytes={offset}-"} if offset else {}
            with httpx.stream(
                "GET", spec.url, headers=headers, follow_redirects=True, timeout=60.0
            ) as response:
                response.raise_for_status()
                mode = "ab" if offset and response.status_code == 206 else "wb"
                if mode == "wb":
                    offset = 0
                total = offset + int(response.headers.get("content-length", 0))
                with partial.open(mode) as handle:
                    done = offset
                    for chunk in response.iter_bytes(1024 * 1024):
                        token.raise_if_cancelled()
                        handle.write(chunk)
                        done += len(chunk)
                        if progress:
                            progress(done, total)
                    handle.flush()
                    os.fsync(handle.fileno())
            partial.replace(destination)
            digest = self.verify(model_id)
            atomic_write_text(
                self.root / f"{model_id}.json",
                json.dumps(
                    {**asdict(spec), "sha256_observed": digest, "size": destination.stat().st_size},
                    indent=2,
                ),
            )
        return destination


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
