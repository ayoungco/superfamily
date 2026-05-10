# Local Video Transcription Workflow

This workflow is intentionally split into small stages. Run one stage, inspect
the output, then continue.

Target machine: Fedora workstation with an NVIDIA GPU, such as a 3060 12 GB.

## 1. Install Tools

```bash
sudo dnf install ffmpeg ffmpeg-free ffmpeg-free-devel python3 python3-pip
python3 -m venv .venv-transcription
source .venv-transcription/bin/activate
pip install -U pip faster-whisper
```

If CUDA is configured correctly, `faster-whisper` can use:

```text
device=cuda
compute_type=float16
model=large-v3
```

For the 3060 12 GB, start with `large-v3`. If memory gets tight, use
`medium` or `large-v3` with a smaller beam size.

## 2. Discover Videos

Pass a directory or an explicit list of files:

```bash
bash scripts/transcription/00-discover-videos.sh -o data/transcription/manifest.tsv data/videos
bash scripts/transcription/00-discover-videos.sh -o data/transcription/manifest.tsv video1.mp4 video2.m4v
```

If you prefer direct execution, run `chmod +x scripts/transcription/*.sh`
once on the Fedora machine.

## 3. Probe Audio Streams

```bash
bash scripts/transcription/10-probe-audio.sh -m data/transcription/manifest.tsv
```

Review `data/transcription/probes/*.ffprobe.txt` before extraction if a video
may have multiple audio tracks.

## 4. Extract Preservation WAVs

```bash
bash scripts/transcription/20-extract-audio.sh -m data/transcription/manifest.tsv --track 0
```

This writes 48 kHz PCM WAVs under `data/transcription/audio/raw`.

## 5. Make Speech-Cleaned WAVs

Start with the default `speech` profile:

```bash
bash scripts/transcription/30-clean-audio.sh -m data/transcription/manifest.tsv --profile speech
```

If the cleaned audio sounds metallic or transcription quality drops, run a
gentler pass:

```bash
bash scripts/transcription/30-clean-audio.sh -m data/transcription/manifest.tsv --profile light
```

For a no-denoise baseline:

```bash
bash scripts/transcription/30-clean-audio.sh -m data/transcription/manifest.tsv --profile normalized
```

## 6. Transcribe Locally

```bash
source .venv-transcription/bin/activate
python scripts/transcription/40-transcribe-local.py \
  -m data/transcription/manifest.tsv \
  --profile speech \
  --model large-v3 \
  --device cuda \
  --compute-type float16 \
  --language en \
  --vad-filter
```

Outputs are written to `data/transcription/transcripts`:

- `.txt`
- `.srt`
- `.vtt`
- `.json`
- `.raw.md`

## Notes

- The scripts skip existing outputs by default. Add `--force` to regenerate a
  stage.
- Keep the raw extraction. Do not overwrite source videos or preservation WAVs.
- Try multiple cleanup profiles for muddy VHS audio. The most pleasant audio to
  hear is not always the best audio for transcription.
