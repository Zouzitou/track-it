# Dependency decisions

Runtime bounds follow the specification. NumPy remains below 2.1 for the pinned SAM 2/Cutie
integration surface. SAM 2 and Cutie are adapters to source installed at exact commits from
`third_party/upstreams.lock.json`; no floating upstream dependency is used. Weights remain
external. FFmpeg remains external because distributor build configurations and licenses vary.

PyTorch is capped below 2.13 because 2.13 was still in release-candidate staging on the
implementation date. Windows NVIDIA bootstrap installs the stable official 2.12.1/0.27.1 CUDA
13.0 wheels; CPU and CI environments resolve the same stable versions from the lockfile.
`PYSEC-2025-194` is temporarily allowlisted in the audit command because its published fix is
2.13.0, whose stable release date is after the implementation date. The application does not
use the affected distributed checkpoint-loading path; the exception must be removed as soon as
a stable patched PyTorch release is available. `PYSEC-2026-3447` is also temporarily allowlisted:
PyTorch 2.12.1 requires setuptools below 82 while the advisory fix is 83.0.0. Setuptools is a
build-time dependency and is not imported by Track it at runtime. Pytest was raised to its
published patched version for `PYSEC-2026-1845`.

Host Grotesk is bundled from the pinned Google Fonts distribution of the official Element Type
project and licensed under OFL-1.1. JetBrains Mono is retained only for the data/timecode role.
