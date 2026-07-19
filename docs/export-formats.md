# Export formats

The main workflow produces an H.264 MP4 with the detected subject over pure RGB green
(`0, 255, 0`). Audio is preserved and encoded as AAC when present. The source clip is never
overwritten: the suggested name is `<original>-green-screen.mp4`, rendering happens in a unique
temporary directory beside the destination, and the completed file replaces the temporary output
only after FFmpeg succeeds.

The underlying libraries also support Gray8/Gray16 PNG masks, transparent PNG, FFV1 Matroska mask
video, and JSON/CSV motion data. Those advanced formats are not shown in the simplified main
window.
