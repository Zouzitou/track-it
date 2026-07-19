# Track it — free local AI masking and motion tracking

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue)](LICENSE)

Track it is an open-source desktop tool for selecting any visible subject, propagating a
pixel-level mask through video, correcting mistakes, and exporting both masks and motion
data—all locally on your computer.

![Track it dark workspace](docs/images/main-window-dark.png)

## Privacy and status

There is no account, cloud inference, upload endpoint, telemetry, analytics SDK, advertising,
or watermark. Network access occurs only when you explicitly download a model or update.

The alpha implements PyAV timestamp indexing, VFR-aware project data, multiple independent
mask stores, positive/negative points, boxes, brush-ready prompt storage, SAM 2.1 forward and
reverse propagation, corrections, scene cuts, confidence, mask-derived transforms, PNG and
motion-data exporters, light/dark/system themes, offline Material Symbols, and cancellation.
SAM 2 weights are downloaded separately and never enter the repository or package.

## Requirements

- Windows 10/11 x64 or Linux x86-64; experimental Apple Silicon MPS
- Python 3.11 (3.12 is supported for source development)
- FFmpeg and ffprobe on `PATH` for source installs; the Windows MSI bundles them
- NVIDIA CUDA recommended; an RTX 4060 8 GB selects SAM 2.1 Small

## Install and run

### Windows MSI

Download `Track-it-0.1.0-alpha.1-windows-x64.msi`, double-click it, accept the license,
and choose an install folder. Setup installs a Start Menu shortcut and bundles Python,
SAM 2, Qt, and an LGPL FFmpeg build; only the model weights are downloaded on first use.

The alpha MSI is not yet code-signed, so Windows may show an unknown-publisher warning.
See the [Windows installer guide](docs/windows-installer.md) and
[packaging status](docs/packaging-status.md) for verification details and release limitations.

### Source

```powershell
./scripts/bootstrap.ps1
./scripts/run.ps1
```

On Linux:

```bash
./scripts/bootstrap.sh
./scripts/run.sh
```

The CLI supports `python -m track_it diagnostics`, `self-test`, `models list`,
`models download sam2.1-small`, `models verify`, and `project validate PATH`.

## Workflow

Import a video, pause on a clear frame, add an object, place positive/negative points or a
box, accept the candidate mask, track a selected range in either direction, correct bounded
segments, inspect confidence and motion, then export masks, transparent media, or JSON/CSV.

See [architecture](docs/architecture.md), [project format](docs/project-format.md),
[model management](docs/model-management.md), [export formats](docs/export-formats.md), and
[troubleshooting](docs/troubleshooting.md).

## Development

```powershell
./scripts/test.ps1
uv run ruff check .
uv run mypy src/track_it
uv run pytest --cov=track_it --cov-report=term-missing
```

Contributions are welcome through issues and pull requests. Report vulnerabilities privately
as described in [SECURITY.md](SECURITY.md). Source is Apache-2.0; models and dependencies retain
their own terms in [MODEL_LICENSES.md](MODEL_LICENSES.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
