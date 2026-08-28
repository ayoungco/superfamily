---
title: Episode Metadata and VHS Title Cards
tags:
  - transcription
  - archive
  - workflow
---

# Episode Metadata and VHS Title Cards

Related: [[docs/programmatic-episode-splitting|Programmatic Episode Splitting]] |
[[scripts/scenes/README|Local Scene Detection and Clip Export]]

Two additions on top of the 196-episode season split: a per-episode title
and synopsis generated from the real transcripts, and a short faux-VHS
title card clip per episode.

## Metadata

`scripts/scenes/90-extract-episode-transcripts.py` slices each movie's
Whisper transcript by the planned episode boundaries in `season-plan.tsv`,
one plain-text file per episode. There's no deterministic script for the
title/synopsis themselves -- that's a generation step. For the full archive
this ran as nine parallel agents (one per season-sized chunk, ~16-25
episodes each), every agent reading its assigned `episode-transcripts/*.txt`
files and writing `{code, title, synopsis}` objects. A handful of episodes
had empty or near-empty transcripts (long dialogue-free battle stretches,
one stretch of unrelated bled-through audio in SF9); those got an honest
"mostly silent action" synopsis rather than an invented one.

`scripts/scenes/92-merge-episode-metadata.py` folds in everything else
already known about each episode -- timing, source movie, approx date from
`dates.tsv` -- so `content/data/episode-metadata/season-{00..03}.json` are
self-contained records:

```json
{
  "code": "S01E01",
  "season": 1,
  "season_episode_number": "01",
  "short_name": "SF1",
  "part": 1,
  "video_id": "sf1-the-first-movie-8818813a7b",
  "episode_index": "01",
  "start_seconds": 0.0,
  "end_seconds": 924.933,
  "duration_seconds": 924.933,
  "end_snapped": true,
  "approx_date": "2001-winter",
  "title": "The Great Morning Football Draft",
  "synopsis": "A chaotic family morning unfolds as Tigger bounces around..."
}
```

## Title Cards

`scripts/scenes/91-generate-title-cards.py` renders a 4.5s faux-VHS intro
per episode, matched to that episode's own resolution and frame rate (the
archive isn't uniform -- 716x478, 720x480, and 712x480 all show up across
different camcorders). The look is built entirely from ffmpeg lavfi
filters, no external assets:

- two `geq` passes for RGB static grain and horizontal scanline banding
- `eq` for a washed-out, desaturated retro color grade
- `rgbashift` for chromatic misalignment (the classic VHS color-bleed look)
- `vignette` for CRT-viewfinder-style corner darkening
- a blinking `drawbox` + "REC" text and an approx-date OSD in the corner
  (from `dates.tsv` when known)
- a running `%{pts:hms}` timecode, bottom-right
- `anoisesrc` pink noise for a faint hiss under the video

Season 0 (the Powerteam prequel) gets "THE POWERTEAM" as the on-card show
name instead of "THE SUPER FAMILY," matching the README's note that the
series was formerly known by that name.

**Cards are standalone files, not burned into the exported episodes.**
Each one is written next to its episode as
`episodes/season-{NN}/{code}.intro.mp4` -- `S01E01.mp4` gets
`S01E01.intro.mp4` alongside it. This was a deliberate choice over
re-encoding the title card onto the front of all 196 already-exported
files: burning in would have meant re-encoding stream-copied exports that
had already come out clean, for a meaningfully longer batch run, to buy
only the convenience of not having a separate file. Prepend it in an
editor, or point a media server's trailer/intro slot at it, whichever
fits.
