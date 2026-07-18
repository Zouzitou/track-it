#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export UV_CACHE_DIR="$ROOT/.uv-cache" TEMP="$ROOT/.tmp" TMP="$ROOT/.tmp"
cd "$ROOT"
uv run python -m nuitka --standalone --enable-plugin=pyside6 --output-filename=TrackIt --output-dir=dist --include-data-dir=assets=assets --include-data-dir=third_party=third_party src/track_it/__main__.py
./dist/__main__.dist/TrackIt self-test
