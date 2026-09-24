# Raw Footage and Asset Recovery from the Family NAS Archive (research)

Related: [[content/transcripts/README|Transcripts]] |
[[scripts/transcription/README|Local Video Transcription Workflow]] |
[Content Directory Cleanup](content-directory-cleanup.md) |
[Take-Based Episode Splitting](take-based-episode-splitting.md)

## Summary

A classification pass across `/mnt/creative` (prompted by "have we
properly sorted source content?") found that the repo and
`/mnt/creative/worlds/superfamily/` are both cleanly organized, but a
non-trivial amount of genuine Super Family source material lives
entirely outside `worlds/superfamily/`, inside the general family photo
and video archive, and is invisible to every script and doc in this
project.

## What's actually out there

Investigated by reading file contents and existing pipeline output, not
just filenames:

- **112 clips (6.6 GB) explicitly tagged `[SF2]` through `[SF6] Adam's
  SF Movies`, spanning 2001–2008**, sit under
  `/mnt/creative/photos/young_wade_melissa/Photos and Videos by Year/<year>/...`
  — the shared family archive, organized by digiKam
  (`digikam4.db`, `similarity.db`, `_sort-manifest.tsv`). Breakdown:
  47 tagged `[SF2]`, 38 `[SF3]`, 12 `[SF4]`, 14 `[SF5]`, 1 `[SF6]`.
  Nothing tagged `[SF1]` or `[SF7]`–`[SF14]` turned up by filename
  search. The `[SF6]` clip in particular is very likely raw footage
  behind the already-edited "SF6 - Return Home" movie that exists in
  `worlds/superfamily/movies/`.
- **36 more clips from a single digitized tape, "`[039] New Camera,
  Powerteam Stuff`" (Feb–Mar 2001)**, in the same archive. This is a
  tape-level label, not a per-clip one — a spot-check transcript for
  one clip
  (`.../February 2001/[039] New Camera, Powerteam Stuff 2001-02-25
  13.08.32.m4v`) turned out to be ordinary family conversation about a
  wrestling injury, not Powerteam content. **The tape label is not a
  reliable per-clip content guarantee** — some fraction of these 36 are
  likely genuine Powerteam footage and some are not, and that can't be
  resolved by filename alone.
- **This material has already been run through a pipeline once** — just
  not this project's. `/mnt/creative/photos/_pipeline/` (a separate,
  generic family-archive pipeline, distinct from this repo's
  `scripts/scenes` and `scripts/transcription`) has already produced
  `ffprobe` probes, `scenes.tsv` cut detection, and Whisper-style
  `.speech.{txt,srt,vtt,json}` transcripts for much of this footage,
  including several of the `[SF2]`–`[SF6]` and tape-039 clips
  confirmed above. That output is sitting unused from this project's
  point of view.
- **The family-archive manifests are stale on path**: a `[SF2]` row in
  `/mnt/creative/photos/_pipeline/manifest.annotated.tsv` records the
  source as `/mnt/creative/photos/Mom & Dad/Photos and Videos by
  Year/...`, but the folder is `young_wade_melissa/` on disk today — the
  folder was renamed after that manifest was generated. Any registration
  work needs to re-discover paths at run time, not hardcode anything
  from an existing manifest.
- **No existing classification signal** beyond the filename tag itself
  — the family manifests carry technical metadata (duration, codec) but
  no "this is Super Family content" flag. The `[SF#]` tag and the tape
  label are the only markers that exist today.
- **Separately, a handful of single-purpose Super Family assets are
  misplaced in generic NAS buckets** with no competing organizational
  claim on them (unlike the raw footage, which legitimately belongs to
  the family archive's own chronological record):
  - `_unsorted/Larger Than Life - Super Family Theme.mp3` — an actual
    theme song for the show, not referenced anywhere in this repo or
    in `worlds/superfamily/`.
  - `_unsorted/Super Family Portrait (Bad Scan).xcf`.
  - `_unsorted/Super Family Portrait.jpg` — confirmed byte-identical
    (md5) to the copy already correctly filed at
    `worlds/superfamily/art/Super Family Portrait.jpg`; just a stray
    leftover.
  - `brand/highfive/*` — a set of "Dr. Seinyor" branding assets
    (portraits, a suitcase graphic, two `.wav` stingers, PSDs) from what
    looks like an old personal site/brand ("High Five Entertainment").
    Some files in that folder are Seinyor-specific
    (`Dr. Seinyor.bmp`, `Dr. Seinyor's Suitcase.gif`); others
    (`highfivelogo.png`, `HIGH_FIVE_ENT.psd`) may be generic brand
    material not specific to Super Family — needs a look before moving
    the whole folder.
  - `photos/young_adam/2019-jess-caterpillar-peak-rockstar/6 - The
    Super Family_s 6th Movie - Return Home .gif` — a stray SF6 promo
    gif sitting inside an unrelated 2019 photo-event folder.

## The core tension: register in place, don't move the raw footage

`content/transcripts/README.md` already establishes the right precedent
for this project: *"Source video is never copied in here — every
script reads it directly from wherever it actually lives... the
manifest below stores absolute paths."* That principle should extend to
this recovered footage too, for a reason specific to this material: the
family archive is a real, actively-maintained personal archive (not
just a dumping ground — it has its own digiKam catalog, dedup/similarity
database, and its own migration manifests). Moving files out of it would
fragment someone else's organizational system to serve this project.

So: **the raw clips should be indexed and pointed to, not moved or
copied.** The single-purpose stray assets (theme song, brand art, the
duplicate portrait, the stray gif) are the opposite case — they have no
competing organizational home, so those should actually move into
`worlds/superfamily/`, consistent with how [Content Directory
Cleanup](content-directory-cleanup.md) handled the repo side.

## Proposed plan

1. **Build a raw-footage index** — a new tracked file, e.g.
   `content/data/raw-source-footage.tsv`, enumerating every candidate
   clip found above: path, tag (`sf2`/`sf3`/`sf4`/`sf5`/`sf6`/
   `powerteam-039`/none), date, duration, whether existing
   `_pipeline/` output exists for it, and a `status` column
   (`unreviewed` / `keep` / `reject` / `uncertain`) — the same shape as
   the `segment-review.tsv` precedent from take-based splitting.
2. **Spot-check before trusting any of it.** The tape-039 label is
   already proven unreliable per-clip; the `[SF#]`-tagged clips are
   more likely genuine (tagged individually, not tape-wide) but still
   worth a fast pass. Read the existing `_pipeline/raw/*.speech.txt`
   transcripts where they exist instead of watching each clip — that's
   a much faster way to triage 148 clips than opening every one in a
   player.
3. **Reuse existing analysis before regenerating it.** `_pipeline/` has
   already spent the compute on `ffprobe`, scene-cut detection, and
   speech transcription for a lot of this footage. Confirm what tool
   produced those transcripts and at what quality before deciding
   whether to import them directly or treat them only as a triage aid
   and re-run this project's own `scripts/transcription` pipeline for
   anything that survives triage.
4. **Register survivors with this project's pipeline** by pointing
   `scripts/transcription/00-discover-videos.sh` at the triaged path
   list (not the whole family archive) so they flow into
   `content/transcripts/manifest.tsv` alongside the SF1–SF14/Powerteam
   movies already tracked there.
5. **Give triaged raw footage its own bucket**, not `movies/` or
   `episodes/` — it's pre-production/behind-the-scenes material, a
   different category from either. Something like
   `worlds/superfamily/source-footage/` as an index/README pointing at
   the family-archive paths (not copies), grouped by movie number.
6. **Move the handful of single-purpose stray assets**, once confirmed
   they're genuinely Super Family-only and not needed at their current
   location:
   - the theme song `.mp3` → `worlds/superfamily/` (new `audio/` or
     similar subfolder)
   - the `.xcf` bad-scan and the duplicate portrait `.jpg` →
     `worlds/superfamily/art/` (delete the `_unsorted` duplicate once
     confirmed safe)
   - the Seinyor-specific files from `brand/highfive/` →
     `worlds/superfamily/` (leave anything genuinely generic-brand
     behind)
   - the stray SF6 promo gif → `worlds/superfamily/art/` or
     `movies/titles/`

## Open questions

- What fraction of the 148 candidate clips (112 `[SF#]`-tagged + 36
  tape-039) actually contain usable Super Family content vs. incidental
  family footage — unknown until the spot-check pass runs.
- Whether more un-tagged Super Family raw tapes exist in the family
  archive beyond what filename search can catch (it's a 1,611-video
  archive; this recovery only found what happens to be named
  distinctly). A more thorough recovery would need the same
  person/scene-classification approach already run across
  `worlds/superfamily/movies/` (see [Scene Classification
  Results](scene-classification-results.md)) extended across the family
  archive — a bigger undertaking, out of scope for this pass.
- Whether `_pipeline/`'s existing speech transcripts are trustworthy
  enough to import directly into `content/transcripts/raw/`, or should
  only inform triage while this project's own pipeline re-transcribes
  anything that's kept.
- The `brand/highfive/` split between Seinyor-specific and generic
  "High Five Entertainment" material needs an actual look at each file,
  not a guess from filenames.

## Status

Proposed. Nothing has been moved, copied, or registered yet.
