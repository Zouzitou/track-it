# Project format

A project is a `.trackit` directory containing `project.json`, optional `autosave.json`, a
thumbnail, logs, cached frame index/proxies/cuts, checksummed per-object mask chunks, transforms,
and prompts. Schema 1 stores authoritative PyAV stream/timestamp/orientation metadata and a
partial SHA-256 source fingerprint. JSON writes and mask chunk replacements are atomic; normal
project writes retain a backup. Raw AI masks are immutable inputs to nondestructive settings.
