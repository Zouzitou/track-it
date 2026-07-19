param(
    [Parameter(Mandatory = $true)][string]$MsiPath,
    [switch]$SkipExtraction
)

$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$msi = [System.IO.Path]::GetFullPath($MsiPath)
$testRoot = Join-Path $root '.installer-test'
$image = Join-Path $testRoot 'admin-image'
$log = Join-Path $testRoot 'administrative-install.log'
$env:TEMP = Join-Path $root '.tmp'
$env:TMP = $env:TEMP
$env:HF_HOME = Join-Path $root '.tmp\huggingface'
$env:XDG_CACHE_HOME = Join-Path $root '.tmp\xdg'

if (-not $msi.StartsWith($root + [System.IO.Path]::DirectorySeparatorChar)) {
    throw 'The MSI test only accepts an artifact inside the workspace.'
}
if (-not $SkipExtraction) {
    if (Test-Path -LiteralPath $testRoot) {
        Remove-Item -LiteralPath $testRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $image, $env:TEMP | Out-Null

    $process = Start-Process msiexec.exe -ArgumentList @(
        '/a', "`"$msi`"", '/qn', "TARGETDIR=`"$image`"", '/l*v', "`"$log`""
    ) -Wait -PassThru -WindowStyle Hidden
    if ($process.ExitCode -ne 0) {
        throw "MSI administrative extraction failed with exit code $($process.ExitCode). See $log"
    }
}

$executable = Get-ChildItem -LiteralPath $image -Filter TrackIt.exe -Recurse | Select-Object -First 1
if (-not $executable) { throw 'The administrative image does not contain TrackIt.exe.' }
$ffmpeg = Get-ChildItem -LiteralPath $image -Filter ffmpeg.exe -Recurse | Select-Object -First 1
$ffprobe = Get-ChildItem -LiteralPath $image -Filter ffprobe.exe -Recurse | Select-Object -First 1
if (-not $ffmpeg -or -not $ffprobe) { throw 'The administrative image is missing bundled FFmpeg.' }

$selfTest = Start-Process `
    -FilePath $executable.FullName `
    -ArgumentList 'self-test' `
    -PassThru `
    -WindowStyle Hidden
if (-not $selfTest.WaitForExit(120000)) {
    Stop-Process -Id $selfTest.Id -Force
    throw 'Extracted application self-test timed out after 120 seconds.'
}
if ($selfTest.ExitCode -ne 0) {
    throw "Extracted application self-test failed with exit code $($selfTest.ExitCode)"
}

$env:QT_QPA_PLATFORM = 'offscreen'
$app = Start-Process -FilePath $executable.FullName -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 5
if ($app.HasExited) { throw "Extracted GUI exited early with code $($app.ExitCode)." }
Stop-Process -Id $app.Id

$fileCount = (Get-ChildItem -LiteralPath $image -File -Recurse).Count
Write-Host "MSI administrative extraction, packaged self-test, and GUI launch passed ($fileCount files)."
