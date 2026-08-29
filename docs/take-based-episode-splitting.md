---
title: Take-Based Episode Splitting (Proposal)
tags:
  - transcription
  - archive
  - workflow
---

# Take-Based Episode Splitting (Proposal)

Related: [[docs/programmatic-episode-splitting|Programmatic Episode Splitting]] |
[[docs/episode-metadata-and-title-cards|Episode Metadata and VHS Title Cards]] |
[[scripts/scenes/README|Local Scene Detection and Clip Export]]

**Status: proposed, not yet adopted.** `scripts/scenes/50-plan-episodes.py`
now supports this as `--mode takes` alongside the existing `--mode fixed`
(the default, unchanged). Nothing downstream (`60`-`93`, or the exported
files under `/mnt/creative`) has been re-run against it.

## The problem with fixed-length splitting

The current 196-episode split (`--mode fixed`, `docs/programmatic-episode-splitting.md`)
picks evenly-spaced 15-minute boundaries and snaps each to the nearest real
scene cut within 3 minutes. When no real cut falls in that window it forces
one anyway, at the ideal timestamp, flagged `end_snapped=False` -- 44 of 196
episodes (~22%).

That flag actually undersells the problem, because it's a per-boundary
count, not a per-*take* one. Concretely: `sf4-the-fourth-movie` has one
continuous, uncut camera take running from 7418.9s to 9130.4s (28.5
minutes -- nobody stopped recording or changed shots for that whole
stretch). The fixed splitter has no way to represent "one 28-minute
episode," so it forces a cut at the ideal 15-minute mark, 8217.3s, landing
**mid-take**, and the result is two separate episodes (`S02E09`, `S02E10`)
that are really one unbroken shot sliced in half for no reason connected to
the content.

The other half of the "there's a lot of junk" complaint is separate but
related: some of those 15-minute slots land entirely on footage that isn't
"Super Family" at all. The per-episode synopses already written for the
current split (generated from real Whisper transcripts, one LLM pass per
episode) surface several:

| Episode | Video | What's actually there |
|---|---|---|
| S02E09 "Static Between Scenes" | sf4 | The 28.5-min take above -- unrelated video/TV audio bled through |
| S06E37 "Tuned to the Wrong Channel" / S06E38 "Still Tuned Out" | sf14 | A golf tournament broadcast picked up in the background for the last ~29 minutes of the tape, no Super Family narration at all |
| S01E08 "Please Visit Our Website" | sf2 | A wordless interstitial repeating a website URL |
| S00E01 "Grandma's Birthday, Static and All" | Powerteam tape 1 | A looping subscribe outro plus a birthday snippet, before any toy-battle footage starts |

None of this was caught by scene detection or the splitter -- it was only
visible after transcribing and reading each fixed slot's text. The fixed
split doesn't know these stretches are different in kind from the rest of
the archive, so it can't route them anywhere except into the same
numbered-episode sequence as everything else.

## Proposed algorithm: long takes stand alone, short clips get packed

For each video, walk its detected clips in order and classify each one by
duration against the target episode length (default 15 min, same knob as
today):

- A clip **at or above the target length** ("long-take") is atomic. There
  is no real cut inside it, so it is never split and never packed with
  neighbors -- it becomes its own segment, however long that makes it.
- Consecutive clips **below the target length** ("short-run") are packed
  forward and closed out once their accumulated duration reaches the
  target -- always landing on a real cut, since every clip boundary already
  is one.
- A segment under `--min-segment-minutes` (default 1 min) is absorbed into
  a neighbor rather than standing alone as a sliver episode -- this matters
  at a movie's very start/end, where a long take can begin or end only a
  couple seconds into the file.

No boundary is ever forced at a timestamp that isn't a real cut. The
tradeoff, made explicit: fixed-mode's problem (forced mid-take cuts) is
gone by construction, in exchange for episodes that vary more in length
than a strict 10-20 minute band.

Implemented as `--mode takes` on the existing `50-plan-episodes.py` (not a
new numbered script, since it reuses the same clip-reading and CLI
scaffolding) -- see the script's docstring for the full flag list. It reads
the same `detections/*.tsv` as `--mode fixed` and writes a new file,
`content/transcripts/scenes/episode-plan-takes.tsv` by default, so it
doesn't touch the existing `episode-plan.tsv` that the currently-organized
season files were built from.

```bash
python3 scripts/scenes/50-plan-episodes.py --mode takes
```

## Results on the full archive

Run against all 25 videos at the default 15-minute target:

| | fixed (current) | takes (proposed) |
|---|---|---|
| Total episodes/segments | 196 | 185 |
| Forced (non-real) boundaries | 44 (22%) | 0 |
| Shortest | (15 min target, but see below) | 1.0 min |
| Median | ~15 min | 16.3 min |
| p90 | -- | 20.6 min |
| Longest | 15 min (by construction, forced) | 29.3 min |
| Standalone long-take segments | 0 (concept doesn't exist) | 21 |

The length distribution is close to the current band without a long tail:

| Length | Segments |
|---|---|
| 0-5 min | 7 (3.8%) |
| 5-10 min | 15 (8.1%) |
| 10-15 min | 8 (4.3%) |
| 15-20 min | 130 (70.3%) |
| 20-30 min | 25 (13.5%) |
| 30+ min | 0 |

21 videos' worth of long single takes (one per video that has one, several
videos have none) now show up as their own segment instead of getting
force-split. `sf4-the-fourth-movie`'s 28.5-minute take is one of them --
segment 09, 7418.883s-9130.367s, `segment_kind=long-take` -- no longer cut
into `S02E09`/`S02E10`.

## What this does for the "blank / other recording" content (and what it doesn't)

Take-based segmentation doesn't detect off-content footage by itself -- it
has no idea what's *in* a clip, only where the camera cut. What it changes
is that the boundaries around that footage now line up with where the
*recording* actually starts and stops, rather than an arbitrary 15-minute
tick, which makes downstream content flagging cleaner:

- **The golf broadcast (sf14) and the sf4 bleed-through are still split
  across multiple new segments**, because the content changed
  mid-take -- the camcorder kept rolling while what it was picking up
  changed from toy battle to broadcast TV, so there's no scene cut at the
  actual content boundary for either fixed or takes mode to find. Sf14's
  golf content overlaps a long-take segment (22%), then fills two
  short-run segments completely (100%, 100%). This is an honest limit of
  cut-based segmentation, the same kind of caveat already written into
  `docs/battle-scene-human-removal.md` for the YOLO person-classifier: a
  visual scene cut is not the same signal as a content-type change, and
  nothing here claims otherwise.
- **What does line up cleanly**: the website interstitial (sf2) and the
  outro loop (Powerteam tape 1) are both real single takes with no
  competing content mixed in in the same shot -- one of the 21 long-take
  segments for sf2 (0-1542s) contains the first 887s of interstitial before
  transitioning into real content within the same uncut shot (57%
  overlap), so even here, flagging by segment is a coarser tool than the
  human-legible transcript already produced for the current split.

**Recommendation**: don't try to detect off-content footage from scene
cuts. Keep doing what already worked for the current split -- per-segment
transcript + LLM-written synopsis (`90-extract-episode-transcripts.py` +
the generation step in `docs/episode-metadata-and-title-cards.md`) -- but
add a `content_type` field (`main` / `off_content` / `interstitial` /
`duplicate` / `silent_battle`) to that generation pass, and use it to route
`off_content` and `interstitial` segments into a bonus/extras bucket
instead of the mainline numbered sequence. The existing synopses for the
current split are a free head start here (not authoritative once
boundaries move, but useful context for whoever/whatever re-runs the
generation step) -- they already independently arrived at the same
"golf broadcast" / "bleed-through" / "interstitial" / "outro loop"
judgments called out above, just under the old boundaries.

## Migration cost

Changing the split boundaries invalidates every downstream artifact keyed
to them:

- Every `SxxEyy` code shifts, same as the season renumbering already did.
- Title cards (`91-generate-title-cards.py`) burn the code into pixels and
  would all need regenerating.
- `92-merge-episode-metadata.py` matches existing title/synopsis text back
  by `(video_id, episode_index)`. That worked across the season
  renumbering because episode boundaries didn't move, only which season
  they were grouped into. Under take-based segmentation the boundaries
  themselves change, so `episode_index` no longer means the same slice of
  the movie -- **titles will not survive this migration by that join**, the
  way they did last time.
- Mitigation, if this is adopted: match old episode metadata to new
  segments by time overlap (the same technique used above to project the
  four known off-content stretches onto the new plan) as a first pass, then
  re-run the transcript-extraction + LLM generation step for any new
  segment without a confident single-old-episode match (i.e. most of them,
  since segment boundaries rarely coincide 1:1 with the old ones).

## What this proposal does not do

- It has not run `60-export-episodes.py`, `70-assign-seasons.py`,
  `80-organize-seasons.py`, or anything else that would touch the exported
  files under `/mnt/creative/projects/superfamily/episodes/`. Only
  `content/transcripts/scenes/episode-plan-takes.tsv` (gitignored, local
  planning data) exists so far.
- It has not implemented the `content_type` classification field or the
  extras-bucket routing described above -- that's the recommended next
  step, not something this change built.
