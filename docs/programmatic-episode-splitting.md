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

## Suggested shape (not yet built)

Following the existing `scripts/scenes/` numbering and TSV-in/TSV-out
convention (`10-detect-scenes.py` -> `20-export-clips.py` ->
`30-classify-scenes.py` -> `40-select-candidates.py`):

- A new `50-plan-episodes.py` reads `detections/*.tsv` plus
  `--target-minutes`/`--tolerance-minutes`, and writes one boundary TSV per
  video (or a single combined manifest) with columns like `video_id`,
  `episode_index`, `start_seconds`, `end_seconds`, `snapped` (whether the
  boundary hit a real cut or was forced). This is the natural analog of
  `40-select-candidates.py`'s "read classification output, write a ranked
  TSV" shape.
- `20-export-clips.py` already accepts `--candidates`; the same
  video_id/clip_index filtering shape doesn't quite fit here since episode
  boundaries aren't existing clip indices, so this likely wants a small
  dedicated export step (or a `--boundaries` mode) that stream-copies each
  planned episode straight from the source, writing to
  `/mnt/creative/projects/superfamily/episodes/{short_name}/` per the
  layout already sketched in the ingest doc.
- Output naming can reuse the CSV's `SFxx` short names and sequential
  episode numbering, but the actual season/episode/title assignment should
  get regenerated from real measured durations rather than hand-typed
  minute estimates -- effectively a `super_family_episodes_v3` grounded in
  the scene-detection data instead of the original plan.

## Open questions

- Should the ~55-60 min plan in `super_family_episodes_v2.csv` stay as the
  canonical hour-scale plan (e.g. for a future edited "movie" cut), with
  10-20 min episodes as a separate bite-sized derivative -- or does the
  short-form version replace it as the primary target?
- Renumber episodes continuously across a whole movie's parts (so SF9's
  three manifest fragments become one shared episode run), or keep
  numbering scoped per source file?
- 10-20 min is wide enough to swallow most of the detected scene lengths
  in the table above except the longest few -- worth deciding whether
  forced (non-cut-aligned) boundaries are rare enough to just flag for
  manual review, or common enough to need a smarter fallback (e.g.
  widening tolerance before forcing a cut).
