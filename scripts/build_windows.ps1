$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$env:UV_CACHE_DIR = Join-Path $root '.uv-cache'
$env:TEMP = Join-Path $root '.tmp'
$env:TMP = $env:TEMP
Push-Location $root
try {
    $python = Join-Path $root '.venv\Scripts\python.exe'
    & $python -m nuitka --standalone --assume-yes-for-downloads --enable-plugin=pyside6 `
        --module-parameter=torch-disable-jit=yes `
        --nofollow-import-to=torch._dynamo,torch._inductor,torch.distributed `
        --windows-console-mode=disable --output-filename=TrackIt.exe --output-dir=dist `
        --include-data-dir=assets=assets --include-data-dir=third_party=third_party `
        src/track_it
    if ($LASTEXITCODE -ne 0) { throw "Nuitka failed with exit code $LASTEXITCODE" }
    & (Join-Path $root 'dist\track_it.dist\TrackIt.exe') self-test
    if ($LASTEXITCODE -ne 0) { throw "Packaged self-test failed with exit code $LASTEXITCODE" }
    Compress-Archive -Path 'dist\track_it.dist\*' -DestinationPath 'dist\TrackIt-windows-x64.zip' -Force
    (Get-FileHash 'dist\TrackIt-windows-x64.zip' -Algorithm SHA256).Hash.ToLowerInvariant() + '  TrackIt-windows-x64.zip' | Set-Content -Encoding ascii 'dist\TrackIt-windows-x64.zip.sha256'
} finally { Pop-Location }
