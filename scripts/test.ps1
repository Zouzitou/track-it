$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$env:UV_CACHE_DIR = Join-Path $root '.uv-cache'
$env:TEMP = Join-Path $root '.tmp'
$env:TMP = $env:TEMP
$env:QT_QPA_PLATFORM = 'offscreen'
Push-Location $root
try {
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy src/track_it
    uv run pytest -q
    uv run pytest --cov=track_it --cov-report=term-missing --cov-report=xml
    uv run pip-audit --ignore-vuln PYSEC-2025-194 --ignore-vuln PYSEC-2026-3447
} finally { Pop-Location }
