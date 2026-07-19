# Windows packaging status

Track it now builds as a self-contained x64 Windows MSI using PyInstaller 6.21 one-folder
output and WiX Toolset 6.0.2. The package includes the Python runtime, PySide6/Qt, CPU PyTorch,
the pinned SAM 2 source package, offline UI assets, and a pinned FFmpeg 8.1.2 LGPL shared build.
Model checkpoints remain a verified first-use download.

## Verified artifact

- File: `Track-it-0.1.0-alpha.1-windows-x64.msi`
- Size: 320,352,808 bytes (305.5 MiB)
- SHA-256: `f0ae841e9b0598418c4dd9ebea225715883db9e2ce0cf7813c8da8fa78c3a7c6`
- MSI ICE table validation: passed
- MSI administrative extraction of the same installer authoring: passed
- Final packaged self-test: passed
- Bundled FFmpeg and ffprobe discovery: passed
- Final packaged offscreen GUI launch: passed
- Packaged runtime: 2,635 files
- Automatic subject discovery, bidirectional SAM 2 tracking, pure-green H.264 rendering, and
  audio preservation: passed on a 10-frame clip in the exact CPU packaging environment

ICE validation reports two non-failing ICE60 warnings for the bundled Host Grotesk variable font
and JetBrains Mono font. Both files are private application assets rather than system-installed
fonts; their exact identities were confirmed by decompiling the MSI file table.

The implementation machine was instructed not to use C: for project data. A non-registering MSI
administrative image rooted on Z: passed before the final runtime-hardening rebuild; the final MSI
then passed ICE table validation and direct packaged-runtime checks without another Windows
Installer invocation. GitHub Actions run
[29678203674](https://github.com/Zouzitou/track-it/actions/runs/29678203674) built the simplified
green-screen revision on a disposable Windows host and passed administrative extraction, packaged
self-test, offscreen GUI launch, registered per-machine install, repair, uninstall, Start Menu
shortcut, Add/Remove Programs registration, and user-data preservation checks. That hosted
artifact contains 2,640 files and has SHA-256
`e95cc05f02dbf099390510fed3d3b83f1d4f11994a1f0d7a7434419c11436c3b`.

An upgrade from a previously published Track it MSI remains untested because no earlier MSI exists
with a production UpgradeCode. The MSI is not code-signed; production releases should use a
trusted Authenticode certificate and timestamp service.

The earlier Nuitka attempts are superseded. They failed in Torch optimizer analysis and did not
produce a claimed artifact; PyInstaller was selected after its one-folder bundle passed the
packaged runtime checks.
