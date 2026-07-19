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
    sha256: str
    expected_size: int
    license: str
    vram_gb: int
    upstream_sha: str


SAM2_SMALL = ModelSpec(
    "sam2.1-small",
    "sam2.1_hiera_small.pt",
    "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_small.pt",
    "configs/sam2.1/sam2.1_hiera_s.yaml",
    "6d1aa6f30de5c92224f8172114de081d104bbd23dd9dc5c58996f0cad5dc4d38",
    184_416_285,
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
        return _verify_file(spec, path)

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
            if partial.exists() and partial.stat().st_size > spec.expected_size:
                partial.unlink()
            offset = partial.stat().st_size if partial.exists() else 0
            if offset < spec.expected_size:
                headers = {"Range": f"bytes={offset}-"} if offset else {}
                with httpx.stream(
                    "GET", spec.url, headers=headers, follow_redirects=False, timeout=60.0
                ) as response:
                    response.raise_for_status()
                    if response.status_code not in {200, 206}:
                        raise ModelIntegrityError(
                            "The model server returned an unexpected response."
                        )
                    if response.status_code == 206:
                        expected_range = (
                            f"bytes {offset}-{spec.expected_size - 1}/{spec.expected_size}"
                        )
                        if response.headers.get("content-range") != expected_range:
                            raise ModelIntegrityError(
                                "The model server returned an invalid resume range."
                            )
                    mode = "ab" if offset and response.status_code == 206 else "wb"
                    if mode == "wb":
                        offset = 0
                    expected_response_size = spec.expected_size - offset
                    response_size = response.headers.get("content-length")
                    if response_size is not None:
                        try:
                            response_size_value = int(response_size)
                        except ValueError as exc:
                            raise ModelIntegrityError(
                                "The model server returned an invalid file size."
                            ) from exc
                        if response_size_value != expected_response_size:
                            raise ModelIntegrityError(
                                "The model server returned an unexpected file size."
                            )
                    with partial.open(mode) as handle:
                        done = offset
                        for chunk in response.iter_bytes(1024 * 1024):
                            token.raise_if_cancelled()
                            handle.write(chunk)
                            done += len(chunk)
                            if done > spec.expected_size:
                                raise ModelIntegrityError(
                                    "The model download exceeded its expected size."
                                )
                            if progress:
                                progress(done, spec.expected_size)
                        handle.flush()
                        os.fsync(handle.fileno())
            try:
                digest = _verify_file(spec, partial)
            except ModelIntegrityError:
                if partial.exists() and partial.stat().st_size == spec.expected_size:
                    partial.unlink()
                raise
            partial.replace(destination)
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


def _verify_file(spec: ModelSpec, path: Path) -> str:
    if not path.is_file() or path.stat().st_size != spec.expected_size:
        raise ModelIntegrityError(
            "This model file failed verification. Delete it and download it again."
        )
    digest = _sha256(path)
    if digest != spec.sha256:
        raise ModelIntegrityError(
            "This model file failed verification. Delete it and download it again."
        )
    return digest
