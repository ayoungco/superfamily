# Extracting Audio Tracks and Transcribing Muddy VHS Video

This document describes a practical workflow for turning `.mp4` and `.m4v` video files into useful transcripts, especially when the source audio may be noisy, muffled, or degraded from VHS.

The basic idea is:

1. Keep the original video untouched.
2. Extract a clean working audio file.
3. Create one or more enhanced audio versions for transcription.
4. Transcribe with timestamps.
5. Review uncertain sections against the audio.
6. Save both the transcript and enough metadata to reproduce the result.

## Recommended Tools

Install these locally if possible:

- `ffmpeg`: extract audio, convert formats, normalize volume, reduce noise.
- `ffprobe`: inspect video and audio streams. Usually included with `ffmpeg`.
- A speech-to-text engine:
  - Local option: Whisper-based tools such as `whisper.cpp`, `faster-whisper`, or WhisperX.
  - Cloud option: a transcription API, useful when you want stronger models or easier automation.
- Optional cleanup tools:
  - Audacity for manual inspection and repair.
  - iZotope RX, Adobe Enhance Speech, or similar tools for difficult tapes.
  - Demucs or another source-separation tool if speech is mixed with music or background audio.

## Suggested Folder Layout

Use a repeatable layout so outputs do not get mixed up:

```text
data/
  videos/
    original-file.m4v
  audio/
    original-file.wav
    original-file.cleaned.wav
  transcripts/
    original-file.raw.srt
    original-file.raw.txt
    original-file.reviewed.md
  logs/
    original-file.ffprobe.txt
    original-file.transcription-notes.md
```

For archival work, never overwrite the source video or the first extracted audio file.

## Step 1: Inspect the Video

Before extracting, check what audio streams exist:

```powershell
ffprobe -hide_banner -i "data/videos/example.m4v"
```

Look for:

- Number of audio streams.
- Codec, such as AAC, AC3, PCM, or MP3.
- Channel layout, such as mono, stereo, or 5.1.
- Sample rate, commonly `44100 Hz` or `48000 Hz`.

If there are multiple audio tracks, inspect them before choosing one. Some files may contain commentary tracks, alternate language tracks, or damaged duplicate streams.

## Step 2: Extract a Preservation WAV

Extract audio to an uncompressed WAV file:

```powershell
ffmpeg -i "data/videos/example.m4v" -vn -acodec pcm_s16le -ar 48000 "data/audio/example.wav"
```

This produces a high-quality working copy. It is larger than MP3 or AAC, but better for cleanup and transcription.

If the audio is stereo but the speech is centered, create a mono transcription copy:

```powershell
ffmpeg -i "data/audio/example.wav" -ac 1 -ar 16000 -acodec pcm_s16le "data/audio/example.mono16.wav"
```

Most speech-to-text systems work well with mono 16 kHz WAV.

## Step 3: Create a Cleaned Transcription Copy

For muddy VHS audio, create a separate cleaned version. Do not destroy the raw extraction.

A useful first-pass cleanup:

```powershell
ffmpeg -i "data/audio/example.wav" `
  -ac 1 -ar 16000 `
  -af "highpass=f=80,lowpass=f=7800,afftdn=nf=-25,loudnorm=I=-16:TP=-1.5:LRA=11" `
  "data/audio/example.cleaned.wav"
```

What this does:

- `highpass=f=80`: removes very low rumble.
- `lowpass=f=7800`: removes high-frequency hiss that rarely helps speech recognition.
- `afftdn=nf=-25`: reduces steady background noise.
- `loudnorm=I=-16:TP=-1.5:LRA=11`: normalizes volume to a speech-friendly level.

If the result sounds metallic or distorted, reduce the noise reduction:

```powershell
ffmpeg -i "data/audio/example.wav" `
  -ac 1 -ar 16000 `
  -af "highpass=f=70,lowpass=f=8500,afftdn=nf=-18,loudnorm=I=-16:TP=-1.5:LRA=11" `
  "data/audio/example.light-clean.wav"
```

For very quiet recordings, normalize first and then transcribe:

```powershell
ffmpeg -i "data/audio/example.wav" `
  -ac 1 -ar 16000 `
  -af "highpass=f=80,lowpass=f=7800,loudnorm=I=-16:TP=-1.5:LRA=11" `
  "data/audio/example.normalized.wav"
```

## Step 4: Batch Extract Audio

From PowerShell, this extracts `.mp4` and `.m4v` files into `data/audio`:

```powershell
Get-ChildItem "data/videos" -Include *.mp4,*.m4v -Recurse | ForEach-Object {
  $base = [System.IO.Path]::GetFileNameWithoutExtension($_.Name)
  ffmpeg -i $_.FullName -vn -acodec pcm_s16le -ar 48000 "data/audio/$base.wav"
}
```

Then create cleaned mono transcription files:

```powershell
Get-ChildItem "data/audio" -Filter *.wav | Where-Object {
  $_.Name -notmatch "\.cleaned\.wav$"
} | ForEach-Object {
  $base = [System.IO.Path]::GetFileNameWithoutExtension($_.Name)
  ffmpeg -i $_.FullName -ac 1 -ar 16000 `
    -af "highpass=f=80,lowpass=f=7800,afftdn=nf=-25,loudnorm=I=-16:TP=-1.5:LRA=11" `
    "data/audio/$base.cleaned.wav"
}
```

## Step 5: Transcribe with Timestamps

Use a transcription tool that can output timestamps. Timestamps are important because muddy audio will need review.

Prefer outputs such as:

- `.srt` for time-aligned captions.
- `.vtt` for web captions.
- `.json` if the transcription engine provides segment confidence, word timings, or speaker metadata.
- `.txt` or `.md` for readable notes.

Example using a local Whisper-style command:

```powershell
whisper "data/audio/example.cleaned.wav" --model large --language English --output_format srt --output_dir "data/transcripts"
```

Exact commands vary by transcription tool. The important settings are:

- Use a strong model for muddy audio.
- Force the expected language if known.
- Preserve timestamps.
- Disable translation unless you actually want translated text.
- Save raw output before editing.

## Step 6: Improve Accuracy with Context

Speech recognition improves when the transcription pass has hints. If your tool supports an initial prompt, provide:

- Family names.
- Place names.
- Repeated phrases.
- Dates or decade.
- Event type, such as wedding, reunion, interview, school play, or home movie.
- Likely speakers.

Example context note:

```text
This is a family VHS recording from the late 1980s or early 1990s.
Likely names include Maria, Robert, Linda, John, Angela, and Michael.
Likely places include Cleveland, Parma, Akron, and Lakewood.
The audio may include overlapping conversation, TV noise, and camcorder handling noise.
```

Keep a small glossary beside the transcript:

```text
Known names:
- Rada
- Antoinette
- Parma

Uncertain names:
- "Miro" might be "Mira" or "Milan"
```

## Step 7: Use Multiple Passes for Muddy Audio

For damaged VHS audio, one pass is often not enough. Run transcription against multiple audio versions:

```text
example.mono16.wav
example.normalized.wav
example.cleaned.wav
example.light-clean.wav
```

Then compare the transcripts. The cleaned file may recover speech hidden under hiss, while the raw or lightly cleaned file may preserve consonants that aggressive denoising damages.

A good review workflow:

1. Generate transcripts for raw, normalized, and cleaned audio.
2. Compare sections where the text differs.
3. Listen to those timestamp ranges manually.
4. Mark uncertain words with `[unclear]` or `[name?]`.
5. Produce a reviewed transcript from the best combined result.

## Step 8: Handle Overlapping Speakers

Home videos often have people talking over each other. If speaker identity matters, use diarization if available.

Recommended labels:

```text
[Speaker 1]
[Speaker 2]
[Child]
[Off camera]
[Unknown]
```

Avoid guessing names unless there is strong evidence. Use:

```text
[possibly Maria]
```

instead of silently turning uncertainty into fact.

## Step 9: Mark Non-Speech Audio

Do not force every sound into words. Mark useful non-speech events:

```text
[music playing]
[laughter]
[applause]
[inaudible conversation]
[camera handling noise]
[TV in background]
```

For archival transcripts, these notes are often valuable context.

## Step 10: Create a Reviewed Markdown Transcript

Final reviewed transcript format:

```markdown
# Example Video Transcript

Source video: `data/videos/example.m4v`
Audio used: `data/audio/example.cleaned.wav`
Transcription date: 2026-04-30
Review status: reviewed once

## Notes

- VHS source with muffled speech and background hiss.
- Speaker names are uncertain unless marked.

## Transcript

00:00:03 - [music playing]

00:00:11 - [Off camera] Are you recording?

00:00:14 - [Unknown] I think so.

00:00:18 - [laughter]
```

Use a status field such as:

- `raw machine transcript`
- `reviewed once`
- `reviewed against source audio`
- `needs speaker identification`
- `too noisy for reliable transcription`

## Quality Checklist

Before treating a transcript as reliable, check:

- Did the transcription use the correct language?
- Are names and places checked against known family context?
- Are uncertain phrases marked instead of guessed?
- Are timestamps preserved?
- Are non-speech events marked where useful?
- Is the audio version used for transcription recorded in the transcript header?
- Is the raw machine transcript saved separately from the reviewed transcript?

## Common Problems

### The transcript invents confident nonsense

This often happens when the audio is too quiet, too noisy, or mostly music. Try:

- A stronger model.
- Less aggressive noise reduction.
- Manual volume normalization.
- Shorter audio chunks.
- Adding a prompt with names and context.

### The transcript misses quiet speech

Try:

- Normalize loudness.
- Split long files into shorter sections.
- Use headphones to identify whether the speech is actually recoverable.
- Create a copy with less high-frequency filtering.

### Denoising makes speech worse

Use the raw or lightly cleaned version. VHS hiss is annoying to humans, but some transcription models tolerate it better than metallic denoising artifacts.

### Multiple people are talking

Use diarization if possible, but still review manually. Speaker labels are helpful, but they can be wrong when voices overlap.

## Automation Plan

A future script could do this for every video:

1. Find `.mp4` and `.m4v` files under `data/videos`.
2. Run `ffprobe` and save stream info to `data/logs`.
3. Extract preservation WAV to `data/audio`.
4. Create mono, normalized, and cleaned transcription WAVs.
5. Run transcription on each candidate audio file.
6. Save raw `.srt`, `.json`, and `.txt` outputs.
7. Generate a Markdown review file with source paths and status.

That script should skip files that already have completed outputs unless explicitly asked to regenerate them.

