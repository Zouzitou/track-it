#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export UV_CACHE_DIR="$ROOT/.uv-cache" TEMP="$ROOT/.tmp" TMP="$ROOT/.tmp"
mkdir -p "$TEMP"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
uv python find 3.11 >/dev/null
uv sync --extra dev --python 3.11
command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null || { echo 'FFmpeg and ffprobe are required.' >&2; exit 1; }
uv run python -m track_it self-test
