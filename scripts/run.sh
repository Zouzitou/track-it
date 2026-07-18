#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export UV_CACHE_DIR="$ROOT/.uv-cache" TEMP="$ROOT/.tmp" TMP="$ROOT/.tmp"
cd "$ROOT"
uv run python -m track_it gui
