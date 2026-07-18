$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$env:UV_CACHE_DIR = Join-Path $root '.uv-cache'
$env:TEMP = Join-Path $root '.tmp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host 'uv was not found. Installing uv for the current user.'
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
}
uv python find 3.11 | Out-Null
uv sync --extra dev --python 3.11

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue) -or -not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id Gyan.FFmpeg --exact --accept-source-agreements --accept-package-agreements
    } else {
        throw 'FFmpeg was not found. Install FFmpeg or choose its folder in Settings.'
    }
}

if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    Write-Host 'NVIDIA GPU found. Installing the stable official CUDA 13.0 PyTorch wheels.'
    uv pip install torch==2.12.1 torchvision==0.27.1 --index-url https://download.pytorch.org/whl/cu130
} else {
    Write-Host 'No NVIDIA GPU found; CPU-compatible PyTorch will be used.'
}
uv run python -m track_it self-test
