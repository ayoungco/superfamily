# Transcripts

Related: [[scripts/transcription/README|Local Video Transcription Workflow]] | [[docs/goals/whisper-transcription|Local Whisper Transcription]] | [[Vault Index]]

Text artifacts in this directory are intended to be committed as searchable
context for the Super Family archive.

- `raw/`: machine output (`.txt`, `.srt`, `.vtt`, `.json`, `.raw.md`).
- `reviewed/`: corrected dialogue and human-verified descriptive captions.
- `context/`: names, terminology, and story hints supplied to transcription.

Keep machine output separate from reviewed transcripts. Mark uncertainty with
labels such as `[unclear]`, `[name?]`, or `[possibly Stacie]` rather than
silently guessing.
