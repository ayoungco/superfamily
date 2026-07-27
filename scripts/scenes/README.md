# Local Scene Detection and Clip Export

Related: [[scripts/transcription/README|Local Video Transcription Workflow]] |
[[media/README|Local Media Drop Zone]]

This workflow detects visual cuts in large local movie files, writes small TSV
boundary files for review, then exports each detected scene as an MP4 clip.
It runs locally with FFmpeg and does not use a cloud service or AI model.

Generated boundaries and clips are under `data/scenes/` and ignored by Git.
Original movies remain untouched.

## 1. Prepare

```bash
bash scripts/scenes/bootstrap.sh
bash scripts/transcription/00-discover-videos.sh \
  -o data/transcription/manifest.tsv media/inbox
```

The existing transcription manifest is reused so each movie has the same stable
ID in both workflows.

## 2. Detect Scenes

```bash
python3 scripts/scenes/10-detect-scenes.py
```

The default FFmpeg scene-change threshold is `0.30`. Lower values detect more
cuts; higher values detect only stronger visual changes. Tune detection before
exporting a large archive:

```bash
python3 scripts/scenes/10-detect-scenes.py \
  --threshold 0.22 \
  --min-duration 3 \
  --force
```

Review the TSV files in `data/scenes/detections/`. Each row contains the clip
number, start, end, and duration in seconds.

Scene detection is visual. It can miss dissolves and fades, and shaky camcorder
footage may create false cuts. Start by testing one representative movie in a
separate manifest.

## 3. Export Clips

Accurate exports re-encode to H.264 video and AAC audio:

```bash
python3 scripts/scenes/20-export-clips.py
```

Outputs are grouped by movie under `data/scenes/clips/`. Existing clips are
skipped unless `--force` is supplied.

For a much faster export that avoids re-encoding:

```bash
python3 scripts/scenes/20-export-clips.py --mode copy
```

Copy mode can begin on the nearest keyframe rather than the exact detected
frame. Use the default encode mode when precise scene boundaries matter.

## Storage Notes

- Keep the source movies as the archival originals.
- Expect encoded clips collectively to use substantial disk space, often near
  the size of the source material.
- Detection itself is CPU-based and does not require the transcription venv or
  RTX 3060. The scripts may still be run while that venv is active.
- Everything under `media/` and `data/scenes/` remains untracked.
