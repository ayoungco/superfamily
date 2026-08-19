# Local Whisper Transcription

Related: [[scripts/transcription/README|Local Video Transcription Workflow]] | [[docs/audio-extraction-and-transcription|Extracting Audio Tracks and Transcribing Muddy VHS Video]] | [[content/transcripts/README|Transcripts]]

ComfyUI is **not the right tool for audio transcription** by default. Use a
local Whisper workflow instead.

This repo now has a staged workflow in `scripts/transcription`:

```text
video files
-> discover manifest
-> ffprobe inspection
-> preservation WAV extraction
-> speech cleanup WAV
-> local faster-whisper transcript
```

The full workflow notes are in `scripts/transcription/README.md`.

## Recommended Local Setup

For the Fedora 44 workstation with an NVIDIA 3060 12 GB GPU, use
`faster-whisper` locally:

```bash
sudo dnf install ffmpeg ffmpeg-free ffmpeg-free-devel python3 python3-pip
python3 -m venv .venv-transcription
source .venv-transcription/bin/activate
pip install -U pip faster-whisper
```

Start with:

```text
model: large-v3
device: cuda
compute_type: float16
language: en
```

If GPU memory gets tight, try `medium` or lower `--beam-size`.

## One Stage at a Time

Discover files:

```bash
bash scripts/transcription/00-discover-videos.sh -o content/transcripts/manifest.tsv /mnt/creative/projects/superfamily
```

Probe audio streams:

```bash
bash scripts/transcription/10-probe-audio.sh -m content/transcripts/manifest.tsv
```

Extract the first audio track:

```bash
bash scripts/transcription/20-extract-audio.sh -m content/transcripts/manifest.tsv --track 0
```

Clean for speech:

```bash
bash scripts/transcription/30-clean-audio.sh -m content/transcripts/manifest.tsv --profile speech
```

Transcribe locally:

```bash
python scripts/transcription/40-transcribe-local.py \
  -m content/transcripts/manifest.tsv \
  --profile speech \
  --model large-v3 \
  --device cuda \
  --compute-type float16 \
  --language en \
  --vad-filter
```

Outputs go to `content/transcripts/raw` as `.txt`, `.srt`, `.vtt`,
`.json`, and `.raw.md`.

## Cleanup Profiles

Use multiple passes when the audio is muddy:

- `speech`: highpass, lowpass, moderate denoise, loudness normalization.
- `light`: gentler denoise when the default creates artifacts.
- `normalized`: no denoise, useful as a baseline.
