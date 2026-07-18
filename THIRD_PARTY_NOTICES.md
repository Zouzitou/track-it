# Third-party notices

- Meta SAM 2, Apache-2.0, pinned in `third_party/upstreams.lock.json`.
- Cutie, MIT, optional and pinned; it is never loaded concurrently with SAM 2 on an 8 GB GPU.
- Google Material Symbols, Apache-2.0. Only manifest-listed SVGs are bundled.
- Host Grotesk by Element Type, SIL Open Font License 1.1.
- JetBrains Mono, SIL Open Font License 1.1.
- PySide6/Qt is used under the LGPL/commercial dual-licensing framework. Users may replace the
  dynamically linked Qt libraries in source/standalone distributions; Qt notices remain required.
- PyTorch, PyAV, NumPy, SciPy, Pillow, and other dependencies retain their respective licenses.
- PyAV interfaces with FFmpeg. FFmpeg is external and its license/configuration depends on the
  detected distributor build; Track it does not imply all FFmpeg builds have identical terms.
