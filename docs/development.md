# Development

Use Python 3.11 and uv. Run `uv sync --extra dev`, then Ruff, mypy, pytest, coverage, pip-audit,
and the license scripts. Synthetic tests are deterministic and require no model weights. A real
SAM 2 smoke test runs only when the official package and checkpoint are present, otherwise it
records a precise skip reason.
