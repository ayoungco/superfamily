# Local Video Transcription Workflow

This workflow is intentionally split into small stages. Run one stage, inspect
the output, then continue.

The scripts work on macOS and Linux. A CUDA workstation is substantially
faster for the strongest models, but CPU transcription is supported for setup
and smaller jobs.

## 1. Install Tools

Bootstrap the local directories and Python environment:

```bash
bash scripts/transcription/bootstrap.sh
```

This creates ignored local work areas under `media/` and
`data/transcription/`, plus tracked transcript folders under `transcripts/`.
It does not download Python packages unless `--install` is supplied.

```bash
bash scripts/transcription/bootstrap.sh --install
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
bash scripts/transcription/00-discover-videos.sh -o data/transcription/manifest.tsv media/inbox
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

Outputs are written to the tracked `transcripts/raw` directory:

- `.txt`
- `.srt`
- `.vtt`
- `.json`
- `.raw.md`

Pass series vocabulary and likely character names to Whisper:

```bash
python scripts/transcription/40-transcribe-local.py \
  --initial-prompt-file transcripts/context/super-family.txt \
  --device cpu --compute-type int8 --model medium --vad-filter
```

Use `--device cuda --compute-type float16 --model large-v3` on the NVIDIA
workstation. Raw JSON includes word-level timestamps and probabilities for
targeted review of uncertain dialogue.

## Notes

- The scripts skip existing outputs by default. Add `--force` to regenerate a
  stage.
- Keep the raw extraction. Do not overwrite source videos or preservation WAVs.
- Try multiple cleanup profiles for muddy VHS audio. The most pleasant audio to
  hear is not always the best audio for transcription.
- Whisper primarily transcribes speech. Add caption-style cues such as
  `[door closes]`, `[dramatic music]`, or `[indistinct shouting]` during review;
  do not treat automatically invented sound labels as archival fact.
