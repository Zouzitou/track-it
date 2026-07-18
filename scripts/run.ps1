$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$env:UV_CACHE_DIR = Join-Path $root '.uv-cache'
$env:TEMP = Join-Path $root '.tmp'
$env:TMP = $env:TEMP
Push-Location $root
try { uv run python -m track_it gui } finally { Pop-Location }
