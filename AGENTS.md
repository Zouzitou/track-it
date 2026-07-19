# Track it agent guide

These instructions apply to the entire repository. Keep changes focused, reviewable, and verified.

## Mandatory session startup

1. From the repository root, run `graphify . --watch --code-only` before doing project work. Graphify 0.9.20 currently performs the initial code-only update and exits despite the `--watch` flag, so also start its persistent equivalent, `graphify watch .`, as a background process until that compatibility bug is fixed.
2. Verify that the persistent watcher is still running after its initial scan and after each meaningful change wave. Keep its environment, cache, graph output, and logs on the `Z:` drive.
3. Query the existing graph before tracing architecture or cross-file behavior. Rebuild or update it regularly, especially after structural changes. The watcher handles code changes; run a manual code-only update when the graph is stale.
4. Do not place project data, build products, package caches, temporary files, or model data on `C:`. System executables installed on `C:` may be invoked, but their task-specific output and caches must be redirected to `Z:`.

## Project map

Track it is a Windows-first PySide6 desktop application for creating tracked-subject video effects with SAM 2 and FFmpeg. Source code lives in `src/track_it`, tests in `tests`, installer sources in `installer`, build automation in `scripts`, and third-party notices and pinned upstream metadata in `third_party`.

The native project directory suffix is `.trackit`. Project persistence, media probing/decoding, inference, mask storage, rendering, and UI code are separate boundaries; preserve those boundaries instead of moving application logic into widgets.

## Development workflow

- Use Python 3.11 and `uv`; keep the lockfile synchronized with `pyproject.toml`.
- Read relevant code and tests before editing. Match existing type annotations, naming, and error-handling patterns.
- Prefer the smallest language/runtime set that solves the problem. Python is the default; another language is welcome when it provides a concrete performance, packaging, or safety benefit. Do not introduce C#.
- Use Host Grotesk for product UI and installer branding. Use JetBrains Mono only where a monospace face improves technical data.
- Treat user project files as valuable. Use atomic writes, validate paths and sizes, bound decompression and subprocess execution, and never invoke subprocesses through a shell with user-controlled input.
- Verify downloaded executables and model artifacts with pinned hashes. Keep licenses and `third_party/upstreams.lock.json` accurate whenever bundled or fetched components change.
- Never commit secrets, model weights, virtual environments, caches, generated package trees, or local Graphify output.

## Verification

Run checks directly from the repository environment so `uv` does not unexpectedly replace a specialized local Torch build:

```powershell
.venv\Scripts\ruff.exe format --check .
.venv\Scripts\ruff.exe check .
.venv\Scripts\mypy.exe src
.venv\Scripts\pytest.exe
.venv\Scripts\python.exe scripts\verify_manifests.py
```

For installer changes, build with `scripts\build_windows_msi.ps1` and verify with `scripts\test_windows_msi.ps1`. Keep all build, temporary, NuGet, PyInstaller, Hugging Face, and package caches under the repository on `Z:`. A release is not ready until the packaged self-test, bundled FFmpeg discovery, administrative extraction, and GUI launch smoke test pass.

## Git and documentation

- Work on a feature branch, preserve unrelated user changes, and use small commits with clear intent.
- Do not use destructive Git commands or rewrite shared history. Do not push, merge, tag, or publish a release unless the current task authorizes it.
- Update user-facing documentation and tests in the same change as behavior. Record limitations honestly, especially unsigned installer status, first-use model downloads, and validation that still requires a disposable Windows VM.
- After meaningful code changes, confirm the Graphify watcher picked them up before relying on graph answers.
