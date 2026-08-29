---
title: Programmatic Episode Splitting
tags:
  - transcription
  - archive
  - workflow
---

# Programmatic Episode Splitting

Related: [[docs/media-ingest-and-chunking|Media Ingest and Episode Chunking]] |
[[scripts/scenes/README|Local Scene Detection and Clip Export]]

**Status: implemented.** `50-plan-episodes.py` through `80-organize-seasons.py`
in `scripts/scenes/` build and run the pipeline sketched below -- see
[[scripts/scenes/README|Local Scene Detection and Clip Export]] for usage.
The open questions section at the end records the calls made where the plan
below left them open.

The README task list calls for turning the monolithic SF/Powerteam movie
files into bite-sized episodes ("Export 1 hour episodes from Premiere,
don't worry about intro/outro, just get the content into bite-sized chunks
for easier processing and transcription"). That task assumed manual cuts in
Premiere at roughly one-hour intervals. This is a plan for doing it
programmatically instead, targeting shorter 10-20 minute episodes, using
data the archive pipeline already has on disk.

## What splitting data already exists

Two different things in the repo both get called "episode data," and only
one of them has real cut points.

**`content/data/super_family_episodes.csv` / `_v2.csv`, and the two
`.xlsx` files it was exported from** are a planning-level episode manifest:
season, episode number, short name (`SF1`...`SF14`), episode title, and a
*target* length in minutes (mostly 52-62 min, i.e. the original one-hour
plan). This is what `content/transcripts/README.md` points reviewed
transcript filenames at. It contains **no timecodes** -- no start/end
seconds, no reference to any specific frame or scene. It's a headcount and
a rough runtime budget, decided before scene detection existed. The
`Movies to Episodes Conversion` workbook's third sheet also carries a small
per-movie checklist (Denoise Video / Audio Denoise / Scene Detection / AVI
Backup), suggesting scene-based splitting was anticipated but never wired
up.

**`content/transcripts/scenes/detections/{id}.scenes.tsv`** (from
`10-detect-scenes.py`) is the real thing: every FFmpeg-detected visual cut
per video, already computed for all 25 videos in the manifest --
2,421 scene boundaries total, with exact `start_seconds`/`end_seconds`/
`duration_seconds` per clip. This is the only place in the repo with actual
cut-point timestamps.

The planning CSV's minute estimates don't reliably match the real per-video
runtime the scene-detection pass measured. Spot-checking a few:

| Movie | CSV target (per part) | Actual measured runtime |
|---|---|---|
| SF6 - Return Home (Part 2) | ~58 min | 5.7 min |
| SF9 - The Beginning (Part 1) | ~58 min | 15.7 min |
| SF7 - The Toa Nuva (Part 2) | ~58/60 min | 33.5 min |
| SF13 - Destiny | ~52 min x7 | 368.7 min total |

The mismatches on the short end suggest the CSV's per-part numbering
doesn't line up 1:1 with the current manifest's file boundaries (some
"parts" in the manifest are already short fragments, not full ~1hr chunks).
Treat the CSV as a naming/numbering convention to reuse, not as ground
truth for actual durations -- the scene-detection totals (measured
directly from the source files) are what any splitting logic should plan
against.

## Proposed algorithm

For each video, using its `.scenes.tsv`:

1. `total_duration` = the last detected clip's `end_seconds`.
2. Pick a target episode length, e.g. 15 min (900s), with an acceptable
   band of 10-20 min.
3. `num_episodes = max(1, round(total_duration / target))`.
4. Ideal boundaries: `k * total_duration / num_episodes` for
   `k = 1 .. num_episodes - 1`.
5. For each ideal boundary, snap to the nearest real scene cut (a clip's
   `start_seconds`) within some tolerance (e.g. ±3 min). This guarantees
   every episode break falls on an actual edit, not mid-shot.
6. Export with FFmpeg stream copy at the resolved boundaries -- same
   `-c copy` approach already used in `20-export-clips.py --mode copy` and
   sketched in [[docs/media-ingest-and-chunking|Media Ingest and Episode
   Chunking]]'s "Splitting Without Re-encoding" section, so an hours-long
   source doesn't get re-encoded just to be cut.

### The gap this doesn't cleanly solve

Some single detected scenes run longer than an entire target episode. The
detection data already on disk shows this isn't a rare edge case:

| Movie | Longest single uncut scene |
|---|---|
| SF4 - The Fourth Movie | 28.5 min |
| SF2 - The Second Movie | 25.7 min |
| SF13 - Destiny | 21.7 min |
| SF12 - The Final Battle (Part 1) | 20.1 min |
| SF8 - Kal | 19.6 min |
| SF10 - Prepare for the War | 18.5 min |

When an ideal boundary lands inside one of these, there is no real cut to
snap to within tolerance. The fallback is a forced cut at the ideal
timestamp (keyframe-snapped via FFmpeg's segment muxer, same as the
existing one-hour-interval example in the ingest doc), flagged for a human
to listen across before treating the split as final -- exactly the caution
already written into that doc ("Listen around every boundary before
deleting any working derivative").

## Implemented shape

Following the existing `scripts/scenes/` numbering and TSV-in/TSV-out
convention (`10-detect-scenes.py` -> `20-export-clips.py` ->
`30-classify-scenes.py` -> `40-select-candidates.py`):

- `50-plan-episodes.py` reads `detections/*.tsv` plus
  `--target-minutes`/`--tolerance-minutes`, and writes
  `content/transcripts/scenes/episode-plan.tsv` with `video_id`,
  `episode_index`, `start_seconds`, `end_seconds`, `duration_seconds`,
  `end_snapped` (whether the boundary hit a real cut or was forced). Running
  it at the default 15/3 split across the full archive produced 196
  episodes across 25 videos, with 44 (~22%) forced boundaries.
- `60-export-episodes.py` stream-copies each planned episode straight from
  its source to
  `/mnt/creative/projects/superfamily/episodes/{video_id}/{video_id}-episode-{NN}.mp4`.
  Always writes `.mp4` regardless of source container -- some sources are
  `.m4v`, which makes ffmpeg pick the strict "ipod" muxer and reject
  copy-mode streams whose codec parameters don't fit its profile checks. A
  single clip's export failure is logged and skipped rather than aborting
  the whole batch.
- `70-assign-seasons.py` and `80-organize-seasons.py` handle the
  season/episode numbering and final layout -- see the "Open questions"
  answers below for what they implement.

## Open questions (resolved)

- **Should the ~55-60 min plan stay canonical?** No -- the short-form
  10-20 minute split is now the primary target.
  `super_family_episodes_v2.csv`'s original Season column (SF1-4 / SF5-9 /
  SF10-14) turned out to group by story arc, not episode count -- once cut
  into real episodes that produced two ~70-episode "seasons." Replaced with
  a 6-season split (`SEASON_BREAKS` in `70-assign-seasons.py`) grouping 2-3
  movies per season for a more even ~25-40 episodes each; see
  [[docs/episode-metadata-and-title-cards|Episode Metadata and VHS Title Cards]]
  for the current per-season counts.
- **Renumber continuously across a movie's parts, or per source file?**
  Continuously -- `70-assign-seasons.py` assigns one running
  `season_episode_number` per season, so e.g. SF6 Part 2's episodes pick up
  numbering right after SF6 Part 1's instead of restarting at 1.
  Powerteam's tapes (which predate the Super Family movies and have no
  Season in the CSV) get a new Season 0, ordered by tape number since only
  Tape 4 and the Green Tapes have confirmed approximate dates (see
  `content/transcripts/scenes/dates.tsv`).
- **How common are forced boundaries?** 44 of 196 (~22%) on the full
  archive at the 15/3 default -- common enough that `60-export-episodes.py`
  logs a `(forced boundary)` note per clip rather than a one-off flag, so
  it's visible in the export log which files to listen across before
  treating the split as final. See
  [[docs/take-based-episode-splitting|Take-Based Episode Splitting]] for a
  proposed alternative that eliminates forced boundaries entirely by never
  splitting a single long take.
