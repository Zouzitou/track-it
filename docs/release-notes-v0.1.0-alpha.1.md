# Track it 0.1.0-alpha.1

This source alpha introduces the offline-first Track it desktop workflow for
video object tracking, mask persistence, motion extraction, diagnostics, and
data export. It includes a PySide6 interface using Host Grotesk, bundled
Material Symbols, deterministic test fixtures, documented project formats,
and reproducible dependency metadata.

## Verification

- Python 3.11 on Windows 11
- NVIDIA RTX 4060 CUDA inference smoke test
- FFmpeg 8.1.2 media self-test
- Ruff, mypy, pytest, coverage, manifest, and dependency-audit gates

## Packaging status

This is a draft source prerelease. A Windows standalone binary is intentionally
not attached: the local Nuitka build did not complete successfully because of
an upstream Torch optimizer incompatibility and a subsequent compilation
timeout. The exact status and reproduction commands are recorded in
`docs/packaging-status.md`; release automation remains available for continued
packaging work.
