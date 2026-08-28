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

## 4. Plan and Export Episodes

`50-plan-episodes.py` turns each movie's real detected cuts into 10-20
minute episode boundaries: it picks evenly-spaced ideal boundaries, then
snaps each one to the nearest real cut within `--tolerance-minutes` (default
3). A boundary with no real cut nearby is forced at the ideal timestamp and
flagged `end_snapped=False` for review. See
[Programmatic Episode Splitting](../../docs/programmatic-episode-splitting.md)
for the full rationale, including why the planning CSV's ~55-60 minute
"episode" estimates don't match measured runtimes and aren't used here.

```bash
python3 scripts/scenes/50-plan-episodes.py \
  --target-minutes 15 --tolerance-minutes 3
```

Writes `content/transcripts/scenes/episode-plan.tsv`.

`60-export-episodes.py` cuts each planned episode from its source movie to
`/mnt/creative/projects/superfamily/episodes/{video_id}/`, using stream copy
by default (fast, no re-encode, but starts on the nearest keyframe -- see
"Splitting Without Re-encoding" in
[Media Ingest and Episode Chunking](../../docs/media-ingest-and-chunking.md)).
A single clip's export failure is logged and skipped rather than aborting
the whole batch.

```bash
python3 scripts/scenes/60-export-episodes.py
```

`70-assign-seasons.py` groups the planned episodes into seasons -- Season
1-3 follow `content/data/super_family_episodes_v2.csv`'s existing SF1-4 /
SF5-9 / SF10-14 grouping, with a new Season 0 prequel for the Powerteam
tapes (ordered by tape number; they predate the Super Family movies). It
assigns a continuous, season-scoped episode number, so e.g. SF6 Part 2's
episodes pick up numbering right after SF6 Part 1's instead of restarting.

```bash
python3 scripts/scenes/70-assign-seasons.py
```

Writes `content/transcripts/scenes/season-plan.tsv`.

`80-organize-seasons.py` then moves (not copies) each exported episode file
from its per-video folder into `episodes/season-{NN}/S{NN}E{NN}.mp4`:

```bash
python3 scripts/scenes/80-organize-seasons.py
```

## 5. Episode Metadata and VHS Title Cards

`90-extract-episode-transcripts.py` slices each movie's Whisper transcript
(`content/transcripts/raw/{video_id}.json`) by the planned episode
boundaries in `season-plan.tsv`, writing one plain-text file per episode to
`content/transcripts/scenes/episode-transcripts/{code}.txt`:

```bash
python3 scripts/scenes/90-extract-episode-transcripts.py
```

Writing the actual title and synopsis per episode is a generation step, not
a deterministic one -- there's no script for it. Have an LLM (Claude Code
itself, or an agent) read each `episode-transcripts/{code}.txt` and write a
`{"code": ..., "title": ..., "synopsis": ...}` object per episode into
`content/data/episode-metadata/season-{NN}.json` (one JSON array per
season). For a full-archive run this is naturally parallelizable -- split
the episode list into chunks and run one agent per chunk, since each
episode's transcript is independent of the others.

`92-merge-episode-metadata.py` then folds in everything else already known
about each episode (timing, source movie, approx date from
`content/transcripts/scenes/dates.tsv`) so the season JSON files are
self-contained records, not just title/synopsis:

```bash
python3 scripts/scenes/92-merge-episode-metadata.py
```

`91-generate-title-cards.py` renders a short (4.5s) faux-VHS title card per
episode -- static/grain, scanlines, chromatic-shifted text, a corner
REC/date OSD (using the approx date when known), and a running timecode --
matched to that episode's own resolution and frame rate. It reads the
episode title from `content/data/episode-metadata/` when present (falling
back to the movie's short name otherwise), so it's worth running after the
metadata step. Cards are written alongside each episode as
`episodes/season-{NN}/{code}.intro.mp4` and do **not** modify the exported
episode files -- prepend one in an editor, or use it as a media-server
"trailer" clip, whichever fits your player.

```bash
python3 scripts/scenes/91-generate-title-cards.py
```

## Storage Notes

- Keep the source movies as the archival originals.
- Expect encoded clips collectively to use substantial disk space, often near
  the size of the source material.
- Detection and export are CPU-based and do not require the transcription venv
  or RTX 3060 (the scripts may still be run while that venv is active).
  Classification (stage 3) does use that venv and benefits from the GPU.
- Everything under `content/transcripts/scenes/` remains untracked, and source
  movies are read directly from external storage rather than copied in.
