# Scene Classification Results (2026-08-25 run)

Related: [Battle Scene Human Removal](battle-scene-human-removal.md),
[Local Scene Detection and Clip Export](../scripts/scenes/README.md)

## What ran

First real end-to-end run of the scene-detection + classification
pipeline, across the whole 25-video archive (~49.6 hours of footage):

1. `10-detect-scenes.py` against all 25 videos in
   `content/transcripts/manifest.tsv`, parallelized 4-way by chunking the
   manifest. CPU-bound (FFmpeg scene-change detection), ~2 hours wall
   clock. This was the first time this script had been run against real
   data rather than a small manifest slice — it required fixing the host's
   `ffmpeg-free` → `ffmpeg` gap first (see below), since the source
   footage is HEVC-encoded and `ffmpeg-free` can't decode it.
2. `30-classify-scenes.py --device cuda` against all 2,421 detected clips,
   sampling 3 frames per clip and running YOLO (`yolo11n.pt`,
   COCO-pretrained) person detection on each. GPU-bound, finished in
   under 20 minutes.

Both stages completed cleanly with no errors across all 25 videos.

## Results

**977 / 2,421 clips (40.4%)** had a person detected in at least one
sampled frame.

| Movie | Flagged / Total | % |
|---|---|---|
| SF1 - The First Movie | 63/103 | 61.2% |
| SF2 - The Second Movie | 21/59 | 35.6% |
| SF3 - Makuta's Revenge (Part 1) | 38/53 | 71.7% |
| SF3 - Makuta's Revenge (Part 2) | 35/48 | 72.9% |
| SF4 - The Fourth Movie | 43/79 | 54.4% |
| SF5 - Escape From Mata Nui | 66/128 | 51.6% |
| SF6 - Return Home (Part 1) | 73/117 | 62.4% |
| SF6 - Return Home (Part 2) | 3/7 | 42.9% |
| SF7 - The Toa Nuva (Part 1) | 72/121 | 59.5% |
| SF7 - The Toa Nuva (Part 2) | 5/17 | 29.4% |
| SF8 - Kal | 28/46 | 60.9% |
| SF9 - The Beginning (Part 1) | 5/7 | 71.4% |
| SF9 - The Beginning (Part 2) | 39/77 | 50.6% |
| SF9 - The Beginning (Part 3) | 4/220 | 1.8% |
| SF10 - Prepare for the War | 29/47 | 61.7% |
| SF11 - The Universal War | 30/330 | 9.1% |
| SF12 - The Final Battle (Part 1) | 75/125 | 60.0% |
| SF13 - Destiny | 41/249 | 16.5% |
| SF14 - The Great Vacation | 107/191 | 56.0% |
| The Powerteam - Tape 1 | 35/50 | 70.0% |
| The Powerteam - Tape 2 | 13/27 | 48.1% |
| The Powerteam - Tape 3 | 44/68 | 64.7% |
| The Powerteam - Tape 4 | 19/24 | 79.2% |
| The Powerteam - The Green Tapes (Part 1) | 25/91 | 27.5% |
| The Powerteam - The Green Tapes (Part 2) | 64/137 | 46.7% |

Output lives at
`content/transcripts/scenes/classifications/{id}.classifications.json`,
one entry per detected clip with `start_seconds`/`end_seconds`,
`frames_with_person`, `max_person_confidence`, and
`max_person_area_fraction` (untracked, reproducible from source video).

## Reading the spread

The per-movie percentage swings widely (1.8% to 79.2%), which likely
reflects real content differences rather than a detector problem:

- **SF9 Part 3 (1.8%, 4/220) and SF11 (9.1%, 30/330)** have very high
  clip counts and very low flag rates — consistent with long
  dialogue-only or animation-style stretches with few live-action shots.
- **Powerteam tapes and SF3 (70-80%)** skew heavily toward live
  demonstration footage, where a person on camera is the point, not an
  occlusion artifact.

This distinction matters for the next step: a high `frames_with_person`
rate isn't itself informative for the human-removal idea — most of those
977 clips are probably ordinary on-camera human presence, not a hand/arm
intruding into a toy battle. The real target is a small subset.

## What this is not yet

Per the caveat already in `scripts/scenes/README.md` and
`30-classify-scenes.py`'s own docstring: person detection cannot tell a
hand/arm manipulating a figure apart from a full live-action human scene
— both trigger the same COCO `person` class. `max_person_area_fraction`
is an untested heuristic for separating them (small area → partial
hand/arm intrusion; large area → full-body shot) and hasn't been
spot-checked against real clips yet.

**Next step:** filter/rank the 977 flagged clips by
`max_person_area_fraction` (ascending) and spot-check the low end — that
subset is the actual candidate shot list for
[Battle Scene Human Removal](battle-scene-human-removal.md), not the raw
977.

## Incidental infrastructure fix

Running stage 1 against real HEVC footage surfaced that this host's
`ffmpeg-free` package (RPM Fusion's patent-safe build) can't decode HEVC
at all — scene detection failed outright on HEVC-encoded sources like
SF12. Fixed locally via `sudo dnf swap ffmpeg-free ffmpeg --allowerasing`
and mirrored into the `infra` Ansible repo (`roles/common`) so a reimage
of this host won't silently regress this.
