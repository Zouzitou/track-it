# Export formats

Track it supports Gray8/Gray16 PNG masks, transparent PNG, FFV1 Matroska mask video, ProRes 4444
or QTRLE alpha video when detected, composited backgrounds, and JSON/CSV motion data. Exporters
use deterministic safe names, temporary outputs, cancellation, overwrite checks, and ffprobe
validation. Audio copy/re-encode/no-audio behavior must be selected before video export.
