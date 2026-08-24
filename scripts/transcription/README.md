# Local Video Transcription Workflow

Related: [[docs/whisper-transcription|Local Whisper Transcription]] | [[docs/audio-extraction-and-transcription|Extracting Audio Tracks and Transcribing Muddy VHS Video]] | [[content/transcripts/README|Transcripts]]

This workflow is intentionally split into small stages. Run one stage, inspect
the output, then continue.

Before importing a large archive, read
[[docs/media-ingest-and-chunking|Media Ingest and Episode Chunking]].

The scripts work on macOS and Linux. A CUDA workstation is substantially
faster for the strongest models, but CPU transcription is supported for setup
and smaller jobs.

## 1. Install Tools

Bootstrap the local directories and Python environment:

```bash
bash scripts/transcription/bootstrap.sh
```

This creates ignored local work areas under `content/transcripts/{audio,probes,logs}`,
plus tracked transcript folders at `content/transcripts/{raw,reviewed}`. It
does not copy or stage source video locally — every stage reads directly from
wherever your source files live (for example, `/mnt/creative/projects/superfamily`).
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
bash scripts/transcription/00-discover-videos.sh -o content/transcripts/manifest.tsv /mnt/creative/projects/superfamily
bash scripts/transcription/00-discover-videos.sh -o content/transcripts/manifest.tsv video1.mp4 video2.m4v
```

If you prefer direct execution, run `chmod +x scripts/transcription/*.sh`
once on the Fedora machine.

## 3. Probe Audio Streams

```bash
bash scripts/transcription/10-probe-audio.sh -m content/transcripts/manifest.tsv
```

Review `content/transcripts/probes/*.ffprobe.txt` before extraction if a video
may have multiple audio tracks.

## 4. Extract Preservation WAVs

```bash
bash scripts/transcription/20-extract-audio.sh -m content/transcripts/manifest.tsv --track 0
```

This writes 48 kHz PCM WAVs under `content/transcripts/audio/raw`.

## 5. Make Speech-Cleaned WAVs

Start with the default `speech` profile:

```bash
bash scripts/transcription/30-clean-audio.sh -m content/transcripts/manifest.tsv --profile speech
```

If the cleaned audio sounds metallic or transcription quality drops, run a
gentler pass:

```bash
bash scripts/transcription/30-clean-audio.sh -m content/transcripts/manifest.tsv --profile light
```

For a no-denoise baseline:

```bash
bash scripts/transcription/30-clean-audio.sh -m content/transcripts/manifest.tsv --profile normalized
```

## 6. Transcribe Locally

```bash
source .venv-transcription/bin/activate
python scripts/transcription/40-transcribe-local.py \
  -m content/transcripts/manifest.tsv \
  --profile speech \
  --model large-v3 \
  --device cuda \
  --compute-type float16 \
  --language en \
  --vad-filter
```

Outputs are written to the tracked `content/transcripts/raw` directory:

- `.txt`
- `.srt`
- `.vtt`
- `.json`
- `.raw.md`

Pass series vocabulary and likely character names to Whisper:

```bash
python scripts/transcription/40-transcribe-local.py \
  --initial-prompt-file scripts/transcription/super-family.txt \
  --device cpu --compute-type int8 --model medium --vad-filter
```

Use `--device cuda --compute-type float16 --model large-v3` on the NVIDIA
workstation. Raw JSON includes word-level timestamps and probabilities for
targeted review of uncertain dialogue.

## 7. Diarize Speakers (draft / experimental)

`45-diarize-local.py` is a sketch of a speaker-diarization stage, kept
separate from transcription. It clusters cleaned audio into anonymous
`SPEAKER_00`, `SPEAKER_01`, ... segments with pyannote.audio -- it does not
know real names, and does not yet merge with the Whisper output in
`content/transcripts/raw`.

It needs a heavier, optional dependency set (`torch`, `pyannote.audio`) not
installed by the default bootstrap:

```bash
source .venv-transcription/bin/activate
pip install -r scripts/transcription/requirements-diarization.txt
```

pyannote's pretrained pipeline is gated on Hugging Face: accept the model
terms at huggingface.co/pyannote/speaker-diarization-3.1, create an access
token, then run:

```bash
export HF_TOKEN=hf_...
python scripts/transcription/45-diarize-local.py \
  -m content/transcripts/manifest.tsv \
  --profile speech \
  --device cuda
```

Outputs go to `content/transcripts/diarization/{id}.{profile}.json` (segment
list) and `.rttm` (standard diarization interchange format). Next step, not
yet built: a merge script that assigns each Whisper segment the diarization
label with the most time overlap, plus a small per-video labels file so a
human can map `SPEAKER_00` to an actual name once.

## 8. Enroll and Label Named Speakers (draft / experimental)

Diarization only produces anonymous clusters (`SPEAKER_00`, ...). To turn
those into real names:

1. Listen to a few already-diarized clips and note a handful of seconds per
   person where you're sure who's talking. Record them in
   `content/transcripts/speakers.tsv` (tab-separated: `name`, `source_audio`,
   `start`, `end`).
2. Build voiceprints from those clips:

   ```bash
   export HF_TOKEN=hf_...
   python scripts/transcription/46-enroll-speakers.py --device cuda
   ```

3. Match every video's diarization clusters against the voiceprints:

   ```bash
   python scripts/transcription/47-label-speakers.py --device cuda --threshold 0.75
   ```

   Writes `content/transcripts/diarization/{id}.{profile}.labeled.json` with
   each cluster's best name match and similarity score. Below `--threshold`
   the cluster is left unmatched rather than mislabeled -- review those by
   hand and consider adding more reference clips for that person.

`content/transcripts/speakers.tsv` and `content/transcripts/speakers/` are
gitignored: voiceprints are biometric-ish data, and the manifest may contain
local file paths.

## Notes

- The scripts skip existing outputs by default. Add `--force` to regenerate a
  stage.
- Keep the raw extraction. Do not overwrite source videos or preservation WAVs.
- Try multiple cleanup profiles for muddy VHS audio. The most pleasant audio to
  hear is not always the best audio for transcription.
- Whisper primarily transcribes speech. Add caption-style cues such as
  `[door closes]`, `[dramatic music]`, or `[indistinct shouting]` during review;
  do not treat automatically invented sound labels as archival fact.
- Split multi-episode source movies at known episode boundaries for easier
  retries and review. Long files do not need arbitrary one-hour splits for
  Whisper itself.
