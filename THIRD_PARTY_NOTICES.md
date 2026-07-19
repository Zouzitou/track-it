# Third-party notices

- Meta SAM 2, Apache-2.0, pinned in `third_party/upstreams.lock.json`.
- Cutie, MIT, optional and pinned; it is never loaded concurrently with SAM 2 on an 8 GB GPU.
- Google Material Symbols, Apache-2.0. Only manifest-listed SVGs are bundled.
- Host Grotesk by Element Type, SIL Open Font License 1.1.
- JetBrains Mono, SIL Open Font License 1.1.
- PySide6/Qt is used under the LGPL/commercial dual-licensing framework. Users may replace the
  dynamically linked Qt libraries in source/standalone distributions; Qt notices remain required.
- PyTorch, PyAV, NumPy, SciPy, Pillow, and other dependencies retain their respective licenses.
- The Windows MSI bundles the pinned BtbN FFmpeg 8.1 shared LGPL build recorded in
  `scripts/build_windows_msi.ps1`. Its license is bundled with the application and copied to
  `third_party/licenses/FFmpeg-LICENSE.txt`. Source installs may use another FFmpeg distribution,
  whose configuration and license can differ.
