# Windows installer

## User experience

The x64 MSI uses a familiar Windows wizard with Track it branding, the Apache-2.0 license,
install-folder selection, upgrade detection, Start Menu integration, Add/Remove Programs metadata,
repair support, and complete MSI-managed removal. It installs per-machine under `Program Files` by
default and therefore requests elevation once.

Model weights are not embedded. Keeping them in the user's platform data directory prevents a
large installer, supports resumable verified downloads, and ensures uninstalling the application
does not silently delete user-created projects or downloaded model data.

## Build

```powershell
./scripts/build_windows_msi.ps1
./scripts/test_windows_msi.ps1 -MsiPath ./dist/Track-it-0.1.0-alpha.1-windows-x64.msi
```

The build pins PyInstaller, WiX, the SAM 2 commit and checkpoint hash, and the FFmpeg archive plus
SHA-256. Project build caches, temporary files, and tool installations stay under the repository
root. `test_windows_msi.ps1` places its administrative image there too, but Windows Installer itself
uses Windows system services and caches; run it in a disposable Windows VM when the host has a
strict no-C:-data policy. Use that VM for registered install/repair/upgrade/uninstall acceptance as
well.

Pass `-RegisteredCycle` in that disposable environment to verify a quiet per-machine install,
repair, uninstall, all-users Start Menu shortcut, Add/Remove Programs entry, and user-data
preservation. CI enables this switch on its disposable Windows runner.

## Release checklist

1. Run source tests, manifest verification, and dependency audit.
2. Build from a clean checkout on `windows-latest`.
3. Verify the MSI checksum and administrative extraction.
4. Install, repair, upgrade from the previous version, and uninstall in Windows Sandbox.
5. Confirm shortcuts, Add/Remove Programs metadata, app launch, and preservation of user data.
6. Authenticode-sign and timestamp the MSI when a trusted certificate is available.
