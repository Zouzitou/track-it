# Architecture

The dependency direction is UI → controllers/commands → domain/services → inference, media,
persistence, and export adapters → external libraries/processes/files. Domain code has no Qt
dependency. UI code never imports SAM 2 or Cutie. `JobWorker` uses Qt's worker-object/QThread
pattern and emits data-only signals; it never mutates widgets. Exporters consume immutable
project snapshots. Every long operation receives a cooperative cancellation token, and every
subprocess is launched with an argument list rather than a shell string.
