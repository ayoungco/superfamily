# Local Scene Detection and Clip Export

Related: [[scripts/transcription/README|Local Video Transcription Workflow]]

This workflow detects visual cuts in large local movie files, writes small TSV
boundary files for review, then exports each detected scene as an MP4 clip.
Detection and export run locally with FFmpeg and no cloud service or AI
model. An optional third stage tags each detected clip with a person-visible
signal using a local object-detection model (see
[3. Classify Scenes](#3-classify-scenes-draft--experimental) below).

Generated boundaries and clips are under `content/transcripts/scenes/` and
ignored by Git. Original movies remain untouched and are never copied into
the repo.

Detection and export need a full FFmpeg build, not Fedora's patent-restricted
`ffmpeg-free` -- this project's source footage includes HEVC-encoded files,
and `ffmpeg-free` can't decode HEVC. Install RPM Fusion's `ffmpeg` package
(`sudo dnf swap ffmpeg-free ffmpeg --allowerasing`) before running stage 1.

## 1. Prepare

```bash
bash scripts/scenes/bootstrap.sh
bash scripts/transcription/00-discover-videos.sh \
  -o content/transcripts/manifest.tsv /mnt/creative/projects/superfamily
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

Review the TSV files in `content/transcripts/scenes/detections/`. Each row contains the clip
number, start, end, and duration in seconds.

Scene detection is visual. It can miss dissolves and fades, and shaky camcorder
footage may create false cuts. Start by testing one representative movie in a
separate manifest.

## 3. Export Clips

Accurate exports re-encode to H.264 video and AAC audio:

```bash
python3 scripts/scenes/20-export-clips.py
```

Outputs are grouped by movie under `content/transcripts/scenes/clips/`. Existing clips are
skipped unless `--force` is supplied.

For a much faster export that avoids re-encoding:

```bash
python3 scripts/scenes/20-export-clips.py --mode copy
```

Copy mode can begin on the nearest keyframe rather than the exact detected
frame. Use the default encode mode when precise scene boundaries matter.

## 3. Classify Scenes (draft / experimental)

`30-classify-scenes.py` samples a few frames per detected clip and runs a
local object detector (YOLO, COCO-pretrained via `ultralytics`) looking for
the `person` class -- a candidate-shot lister for
[Battle Scene Human Removal](../../docs/battle-scene-human-removal.md), not
a finished tagging pipeline.

```bash
source .venv-transcription/bin/activate
pip install -r scripts/scenes/requirements-classification.txt
python3 scripts/scenes/30-classify-scenes.py --device cuda
```

Frame decoding goes through PyAV, not the system FFmpeg, so this stage works
regardless of the `ffmpeg`/`ffmpeg-free` situation above.

Outputs go to `content/transcripts/scenes/classifications/{id}.classifications.json`,
one entry per clip with how many sampled frames had a person, the strongest
detection confidence, and the largest detected box as a fraction of frame
area.

**This does not distinguish a hand/arm manipulating a toy from a full
live-action human scene** -- both trigger the `person` class. Treat the
output as a candidate list for human review (sorted by clip, watch the
flagged ones), not a final answer. A large `max_person_area_fraction` leans
toward a full-body live-action shot; a small one leans toward a partial
hand/arm intrusion, but this is an unverified heuristic -- spot-check before
trusting it.

## Storage Notes

- Keep the source movies as the archival originals.
- Expect encoded clips collectively to use substantial disk space, often near
  the size of the source material.
- Detection and export are CPU-based and do not require the transcription venv
  or RTX 3060 (the scripts may still be run while that venv is active).
  Classification (stage 3) does use that venv and benefits from the GPU.
- Everything under `content/transcripts/scenes/` remains untracked, and source
  movies are read directly from external storage rather than copied in.
