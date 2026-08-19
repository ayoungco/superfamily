# Transcripts

Related: [[scripts/transcription/README|Local Video Transcription Workflow]] |
[[scripts/scenes/README|Local Scene Detection and Clip Export]] |
[[docs/whisper-transcription|Local Whisper Transcription]]

This directory holds everything the transcription and scene-detection
pipelines produce. Source video is never copied in here — every script reads
it directly from wherever it actually lives (for example
`/mnt/creative/projects/superfamily`); the manifest below stores absolute
paths.

- `manifest.tsv`: video discovery output. Generated, ignored by Git.
- `probes/`: `ffprobe` logs and stream metadata. Generated, ignored by Git.
- `audio/raw/`, `audio/cleaned/`: preservation and speech-cleaned WAVs.
  Generated, ignored by Git.
- `logs/`: pipeline run logs. Generated, ignored by Git.
- `scenes/`: visual-cut detections and exported clips from the scene
  workflow. Generated, ignored by Git.
- `raw/`: machine transcripts (`.txt`, `.srt`, `.vtt`, `.json`, `.raw.md`).
  Tracked.
- `reviewed/`: corrected dialogue and human-verified descriptive captions.
  Tracked.

Keep machine output in `raw/` separate from `reviewed/`. Mark uncertainty in
reviewed transcripts with labels such as `[unclear]`, `[name?]`, or
`[possibly Stacie]` rather than silently guessing.

A practical filename for a reviewed transcript is
`SF01-makutas-reign-part-1.reviewed.md`, matching the short names and
ordering in [[content/data/super_family_episodes_v2.csv|the episode list]].
