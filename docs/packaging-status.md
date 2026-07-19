# Windows packaging status

Track it now builds as a self-contained x64 Windows MSI using PyInstaller 6.21 one-folder
output and WiX Toolset 6.0.2. The package includes the Python runtime, PySide6/Qt, CPU PyTorch,
the pinned SAM 2 source package, offline UI assets, and a pinned FFmpeg 8.1.2 LGPL shared build.
Model checkpoints remain a verified first-use download.

## Verified artifact

- File: `Track-it-0.1.0-alpha.1-windows-x64.msi`
- Size: 320,336,424 bytes (305.5 MiB)
- SHA-256: `a356cba30ea817e5ea91f1a56402db787b9eef4c2fcf8a5612852cc0c490d9d5`
- MSI ICE table validation: passed
- MSI administrative extraction of the same installer authoring: passed
- Final packaged self-test: passed
- Bundled FFmpeg and ffprobe discovery: passed
- Final packaged offscreen GUI launch: passed
- Packaged runtime: 2,635 files

ICE validation reports two non-failing ICE60 warnings for the bundled Host Grotesk variable font
and JetBrains Mono font. Both files are private application assets rather than system-installed
fonts; their exact identities were confirmed by decompiling the MSI file table.

The implementation machine was instructed not to use C: for project data. A non-registering MSI
administrative image rooted on Z: passed before the final runtime-hardening rebuild; the final MSI
then passed ICE table validation and direct packaged-runtime checks without another Windows
Installer invocation. GitHub Actions run
[29667508622](https://github.com/Zouzitou/track-it/actions/runs/29667508622) subsequently built a
fresh MSI on a disposable Windows host and passed administrative extraction, packaged self-test,
offscreen GUI launch, registered per-machine install, repair, uninstall, Start Menu shortcut,
Add/Remove Programs registration, and user-data preservation checks. That hosted artifact contains
2,640 files and has SHA-256
`14f2682c4c5ad947a54b7bff5679cc6eaa26f9fb35faa35a7c77e208adf6301c`.

An upgrade from a previously published Track it MSI remains untested because no earlier MSI exists
with a production UpgradeCode. The MSI is not code-signed; production releases should use a
trusted Authenticode certificate and timestamp service.

The earlier Nuitka attempts are superseded. They failed in Torch optimizer analysis and did not
produce a claimed artifact; PyInstaller was selected after its one-folder bundle passed the
packaged runtime checks.
