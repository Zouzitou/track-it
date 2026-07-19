param(
    [string]$Version,
    [switch]$SkipDependencySync,
    [switch]$SkipRuntimeBuild,
    [switch]$SkipMsiBuild
)

$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$env:UV_CACHE_DIR = Join-Path $root '.uv-cache'
$env:DOTNET_CLI_HOME = Join-Path $root '.dotnet'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:NUGET_PACKAGES = Join-Path $root '.nuget\packages'
$env:PYINSTALLER_CONFIG_DIR = Join-Path $root '.tmp\pyinstaller-cache'
$env:HF_HOME = Join-Path $root '.tmp\huggingface'
$env:XDG_CACHE_HOME = Join-Path $root '.tmp\xdg'
$env:TEMP = Join-Path $root '.tmp'
$env:TMP = $env:TEMP
$env:WIX_EXTENSION = Join-Path $root '.wix'
$env:UV_PROJECT_ENVIRONMENT = Join-Path $root '.venv-package'
New-Item -ItemType Directory -Force -Path $env:TEMP, $env:NUGET_PACKAGES, $env:WIX_EXTENSION | Out-Null

function Reset-WorkspaceDirectory([string]$Path) {
    $resolved = [System.IO.Path]::GetFullPath($Path)
    if (-not $resolved.StartsWith($root + [System.IO.Path]::DirectorySeparatorChar)) {
        throw "Refusing to reset a directory outside the workspace: $resolved"
    }
    if (Test-Path -LiteralPath $resolved) {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $resolved | Out-Null
}

if (-not $Version) {
    $versionText = Get-Content -Raw (Join-Path $root 'src\track_it\version.py')
    if ($versionText -notmatch '__version__\s*=\s*"([^"]+)"') {
        throw 'Unable to read the application version.'
    }
    $Version = $Matches[1]
}
$msiVersion = ($Version -split '-')[0]
$python = Join-Path $root '.venv-package\Scripts\python.exe'
$runtime = Join-Path $root 'dist\TrackIt'
$assets = Join-Path $root 'build\installer-assets'
$wix = Join-Path $root '.tools\wix.exe'

Push-Location $root
try {
    if (-not $SkipDependencySync) {
        uv sync --group package --locked --python 3.11
        if ($LASTEXITCODE -ne 0) { throw "Packaging dependency sync failed with exit code $LASTEXITCODE" }
    }

    $ffmpegName = 'ffmpeg-n8.1.2-22-g94138f6973-win64-lgpl-shared-8.1.zip'
    $ffmpegHash = '8f92bde43723cd37140c787c560afdc08cc3ea486a10ee112ad201339762aa04'
    $ffmpegUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-07-18-13-13/$ffmpegName"
    $ffmpegCache = Join-Path $root '.tmp-upstream\ffmpeg'
    $ffmpegArchive = Join-Path $ffmpegCache $ffmpegName
    $ffmpegExpanded = Join-Path $ffmpegCache 'expanded'
    New-Item -ItemType Directory -Force -Path $ffmpegCache | Out-Null
    if ((Test-Path -LiteralPath $ffmpegArchive) -and
        ((Get-FileHash -LiteralPath $ffmpegArchive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ffmpegHash)) {
        Remove-Item -LiteralPath $ffmpegArchive -Force
    }
    if (-not (Test-Path -LiteralPath $ffmpegArchive)) {
        Invoke-WebRequest -Uri $ffmpegUrl -OutFile $ffmpegArchive
    }
    if ((Get-FileHash -LiteralPath $ffmpegArchive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ffmpegHash) {
        throw 'The pinned FFmpeg archive failed SHA-256 verification.'
    }
    if (-not (Test-Path -LiteralPath $ffmpegExpanded)) {
        New-Item -ItemType Directory -Force -Path $ffmpegExpanded | Out-Null
        Expand-Archive -LiteralPath $ffmpegArchive -DestinationPath $ffmpegExpanded
    }
    $ffmpegRoot = Get-ChildItem -LiteralPath $ffmpegExpanded -Directory | Select-Object -First 1
    if (-not $ffmpegRoot) { throw 'The FFmpeg archive did not contain an application directory.' }
    $ffmpegBin = Join-Path $ffmpegRoot.FullName 'bin'

    Reset-WorkspaceDirectory $assets
    & $python scripts\generate_installer_assets.py --output $assets --version $Version
    if ($LASTEXITCODE -ne 0) { throw "Installer asset generation failed with exit code $LASTEXITCODE" }

    if (-not $SkipRuntimeBuild) {
        Reset-WorkspaceDirectory (Join-Path $root 'build\pyinstaller')
        if (Test-Path -LiteralPath $runtime) {
            Remove-Item -LiteralPath $runtime -Recurse -Force
        }
        $pyinstallerArgs = @(
            '--noconfirm', '--clean', '--onedir', '--windowed',
            '--name', 'TrackIt',
            '--distpath', (Join-Path $root 'dist'),
            '--workpath', (Join-Path $root 'build\pyinstaller'),
            '--specpath', (Join-Path $root 'build\pyinstaller'),
            '--paths', (Join-Path $root 'src'),
            '--icon', (Join-Path $assets 'track-it.ico'),
            '--version-file', (Join-Path $assets 'version-info.txt'),
            '--add-data', "$(Join-Path $root 'assets');assets",
            '--add-data', "$(Join-Path $root 'third_party');third_party",
            '--add-binary', "$ffmpegBin\*.exe;tools\ffmpeg",
            '--add-binary', "$ffmpegBin\*.dll;tools\ffmpeg",
            '--hidden-import', 'sam2.build_sam',
            '--collect-data', 'sam2',
            '--copy-metadata', 'sam-2',
            '--exclude-module', 'torch._dynamo',
            '--exclude-module', 'torch._inductor',
            '--exclude-module', 'matplotlib',
            '--exclude-module', 'pandas',
            '--exclude-module', 'tkinter',
            (Join-Path $root 'src\track_it\__main__.py')
        )
        & $python -m PyInstaller @pyinstallerArgs
        if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
        Copy-Item LICENSE, NOTICE, THIRD_PARTY_NOTICES.md, MODEL_LICENSES.md -Destination $runtime
        $selfTest = Start-Process `
            -FilePath (Join-Path $runtime 'TrackIt.exe') `
            -ArgumentList 'self-test' `
            -PassThru `
            -WindowStyle Hidden
        if (-not $selfTest.WaitForExit(120000)) {
            Stop-Process -Id $selfTest.Id -Force
            throw 'Packaged self-test timed out after 120 seconds.'
        }
        if ($selfTest.ExitCode -ne 0) {
            throw "Packaged self-test failed with exit code $($selfTest.ExitCode)"
        }
    }

    if (-not $SkipMsiBuild) {
        if (-not (Test-Path -LiteralPath $wix)) {
            dotnet tool install wix --version 6.0.2 --tool-path (Join-Path $root '.tools')
        }
        & $wix extension add 'WixToolset.UI.wixext/6.0.2'
        if ($LASTEXITCODE -ne 0) { throw "WiX extension restore failed with exit code $LASTEXITCODE" }
        Reset-WorkspaceDirectory (Join-Path $root 'build\wix')
        $msi = Join-Path $root "dist\Track-it-$Version-windows-x64.msi"
        & $wix build installer\Product.wxs `
            -arch x64 `
            -ext 'WixToolset.UI.wixext/6.0.2' `
            -bindpath "Payload=$runtime" `
            -define "ProductVersion=$msiVersion" `
            -define "InstallerAssets=$assets" `
            -intermediateFolder (Join-Path $root 'build\wix') `
            -pdbtype full `
            -out $msi
        if ($LASTEXITCODE -ne 0) { throw "WiX failed with exit code $LASTEXITCODE" }
        & $wix msi validate `
            -intermediateFolder (Join-Path $root 'build\wix\validate') `
            $msi
        if ($LASTEXITCODE -ne 0) { throw "MSI validation failed with exit code $LASTEXITCODE" }
        $checksum = (Get-FileHash -LiteralPath $msi -Algorithm SHA256).Hash.ToLowerInvariant()
        "$checksum  $([System.IO.Path]::GetFileName($msi))" |
            Set-Content -Encoding ascii -NoNewline "$msi.sha256"
        Write-Host "Built $msi"
        Write-Host "SHA-256 $checksum"
    }
} finally {
    Pop-Location
}
