# Auto-Generated Season Highlight Reels (idea)

Related: [Scene Classification Results](scene-classification-results.md) | [Take-Based Episode Splitting](take-based-episode-splitting.md) | [Season Supercuts](season-supercuts.md)

## The idea

Distinct from Season Supercuts (which trims *dead* footage down to a
condensed cut of everything real): this is a short, punchy trailer per
season built from the *best* moments, not just the non-dead ones.

## Sketch

- Reuse signals already computed rather than building new ones: the
  per-segment `dead_pct` and speech-density outlier data from
  `content/transcripts/scenes/segment-review.tsv`, and the
  person/scene classification from
  [Scene Classification Results](scene-classification-results.md).
- Define an "epic" score per segment from things that likely correlate
  with it: transcript exclamations/all-caps, speech-density spikes,
  battle-scene classification, proximity to other high-scoring segments
  (so the reel doesn't grab isolated one-liners).
- Auto-cut the top-ranked segments per season into a 1-2 minute reel,
  ordered by in-story sequence rather than by score, so it still reads
  as a trailer instead of a random-clips supercut.

## Open questions

- The "epic" heuristic is unvalidated — same caveat as the "nothing's
  moving" activity signal noted in Season Supercuts: it needs
  calibration against a few manually-judged segments before trusting it
  at scale.
- Whether music/audio needs a hard cut or a crossfade pass to not sound
  jarring — likely needs at least a basic audio ducking/crossfade step.
- Whether this replaces or supplements a manually curated trailer for
  the seasons that matter most.
