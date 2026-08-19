---
title: Media Ingest and Episode Chunking
tags:
  - transcription
  - archive
  - workflow
---

# Media Ingest and Episode Chunking

Related: [[scripts/transcription/README|Local Video Transcription Workflow]] | [[content/transcripts/README|Transcripts]] | [[docs/audio-extraction-and-transcription|Audio extraction notes]]

## Current Readiness

As of June 23, 2026, the local Mac is ready to process media:

- FFmpeg and ffprobe are installed.
- `.venv-transcription` exists and can import `faster-whisper`.
- Source video stays on external storage (for example
  `/mnt/creative/projects/superfamily`); it is never copied into the repo.
- Generated audio, probes, and logs under `content/transcripts/` are ignored
  by Git.
- Text, caption, and JSON outputs under `content/transcripts/raw` and
  `content/transcripts/reviewed` can be committed.

The selected Whisper model is downloaded on the first transcription run. A
model download can be several gigabytes, depending on the model. Keep the Mac
online for that first run.

## Should The Movies Be Split First?

Whisper does not require hour-long chunks; it internally processes long audio
in short windows. However, splitting a multi-episode movie at real episode
boundaries is recommended when those boundaries are known.

Episode-sized sources provide:

- filenames and transcripts that match `content/data/super_family_episodes_v2.csv`;
- smaller retry units if extraction or transcription is interrupted;
- easier review, correction, and comparison with the episode list;
- timestamps that begin at zero for each episode;
- less work lost if one output must be regenerated.

Do not split a recording merely because it exceeds one hour. Preserve a scene
that crosses the nominal boundary, and record the actual boundary used. If the
boundaries are uncertain, transcribe the original first and split the reviewed
transcript later.

Always retain the untouched original recording. Treat episode files as working
derivatives, not replacements.

## Storage Budget

The source video is not the only large file. For each hour of material, expect
approximately:

- raw 48 kHz 16-bit WAV: about 330 MiB per mono channel, or 660 MiB stereo;
- cleaned mono 16 kHz WAV: about 110 MiB;
- stream-copy episode video: approximately the same total size as the source;
- model cache: potentially several gigabytes.

Keeping originals, episode derivatives, and WAVs can temporarily require more
than twice the source-video size. Check free space before processing a batch:

```bash
df -h /mnt/creative
du -sh content/transcripts ~/.cache/huggingface 2>/dev/null
```

Originals live on the external share and are never copied into the
repository; the discovery manifest stores absolute paths to them.

## Preferred Ingest Layout

```text
/mnt/creative/projects/superfamily/   untouched originals and split episodes
                                       (external, not in the repo)
content/transcripts/
  audio/raw/     preservation WAVs (generated, ignored)
  audio/cleaned/ speech-oriented WAVs (generated, ignored)
  probes/        codec and stream metadata (generated, ignored)
  raw/           machine transcripts (tracked)
  reviewed/      corrected archival transcripts (tracked)
```

Everything under `content/transcripts/` except `raw/` and `reviewed/` is
local-only.

## Splitting Without Re-encoding

Use stream copying to avoid generation loss and a long video encode. Split
episodes stay on the external share alongside the source, next to it rather
than in the repo. This example divides a source near one-hour intervals at
safe keyframes:

```bash
mkdir -p /mnt/creative/projects/superfamily/episodes/SF01
ffmpeg -hide_banner -i "/mnt/creative/projects/superfamily/source.mov" \
  -map 0 -c copy -f segment -segment_time 3600 -reset_timestamps 1 \
  "/mnt/creative/projects/superfamily/episodes/SF01/SF01-part-%02d.mov"
```

The segment muxer cuts at available keyframes, so lengths will not be exactly
60 minutes. This is preferable to dropping or duplicating audio at arbitrary
frame boundaries.

For known editorial boundaries, create each episode explicitly. Replace the
timestamps with reviewed start times:

```bash
ffmpeg -hide_banner -ss 00:00:00 -i "/mnt/creative/projects/superfamily/source.mov" \
  -t 00:56:00 -map 0 -c copy "/mnt/creative/projects/superfamily/episodes/SF01-part-1.mov"

ffmpeg -hide_banner -ss 00:56:00 -i "/mnt/creative/projects/superfamily/source.mov" \
  -map 0 -c copy "/mnt/creative/projects/superfamily/episodes/SF01-part-2.mov"
```

Stream-copy cuts may move slightly to a nearby keyframe. Listen around every
boundary before deleting any working derivative or starting a full batch.

## Recommended First Run On This Mac

Start with one representative episode, not the entire archive:

```bash
bash scripts/transcription/bootstrap.sh --install
bash scripts/transcription/00-discover-videos.sh /mnt/creative/projects/superfamily
bash scripts/transcription/10-probe-audio.sh
bash scripts/transcription/20-extract-audio.sh --track 0
bash scripts/transcription/30-clean-audio.sh --profile speech

source .venv-transcription/bin/activate
python scripts/transcription/40-transcribe-local.py \
  --profile speech \
  --model medium \
  --device cpu \
  --compute-type int8 \
  --language en \
  --initial-prompt-file scripts/transcription/super-family.txt \
  --vad-filter
```

The `medium` model is a reasonable Apple Silicon pilot. Compare its output to
a `large-v3` pass on difficult dialogue before committing to a model for every
episode. The NVIDIA workstation remains the better place for large batches
using `--device cuda --compute-type float16`.

## Local NVIDIA Workstation

The workflow can run fully local on an RTX 3060 workstation. No cloud
transcription service is required. `faster-whisper` downloads the selected
model once, then reads local WAV files and writes local transcript files.

For a 12 GB RTX 3060, start with:

```bash
source .venv-transcription/bin/activate
python scripts/transcription/40-transcribe-local.py \
  --profile speech \
  --model large-v3 \
  --device cuda \
  --compute-type float16 \
  --language en \
  --initial-prompt-file scripts/transcription/super-family.txt \
  --vad-filter
```

If GPU memory is tight, retry with `--model medium`, reduce `--beam-size`, or
use `--compute-type int8_float16`. Keep the extracted WAVs and model cache
local to that workstation if the goal is to avoid cloud processing.

## Pilot Checklist

1. Confirm the manifest lists only the intended episode files.
2. Review probe logs for multiple or unusual audio tracks.
3. Listen to the beginning, middle, and end of the raw WAV.
4. Compare `speech`, `light`, and `normalized` cleanup on difficult passages.
5. Review names and invented dialogue against the audio.
6. Add verified sound descriptions manually in the reviewed transcript.
7. Only then process the remaining episodes in a batch.

Whisper is primarily a speech recognizer. It may output occasional bracketed
sounds, but those labels are not reliable enough to treat as streaming-style
descriptive captions without human review.
