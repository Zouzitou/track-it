# Architecture

The dependency direction is UI → controllers/commands → domain/services → inference, media,
persistence, and export adapters → external libraries/processes/files. Domain code has no Qt
dependency. UI code never imports SAM 2 or Cutie. `JobWorker` uses Qt's worker-object/QThread
pattern and emits data-only signals; it never mutates widgets. Exporters consume immutable
project snapshots. Every long operation receives a cooperative cancellation token, and every
subprocess is launched with an argument list rather than a shell string.

The primary `GreenScreenProcessor` workflow is an application service invoked by the window's
background worker. It owns temporary frame extraction, automatic subject seeding, bidirectional
SAM 2 propagation, green compositing, and atomic MP4 completion. Its pure mask-selection and
compositing functions remain independently testable without Qt or a model download.
