$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'build_windows_msi.ps1') @args
exit $LASTEXITCODE
