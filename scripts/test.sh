#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export UV_CACHE_DIR="$ROOT/.uv-cache" TEMP="$ROOT/.tmp" TMP="$ROOT/.tmp" QT_QPA_PLATFORM=offscreen
cd "$ROOT"
uv run ruff check .
uv run ruff format --check .
uv run mypy src/track_it
uv run pytest -q
uv run pytest --cov=track_it --cov-report=term-missing --cov-report=xml
uv run pip-audit --ignore-vuln PYSEC-2025-194 --ignore-vuln PYSEC-2026-3447
