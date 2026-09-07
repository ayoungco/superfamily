# Content Directory Cleanup

`content/` has grown into a junk drawer: 19 loose files sit directly in
`content/` with no shared naming or type convention (`.md`, `.txt`, `.doc`,
`.docx`, `.xls`, `.html`, `.css`, `.pdf` all mixed together), alongside four
purpose-built subfolders (`lore/`, `data/`, `images/`, `transcripts/`) that
themselves mix unrelated material. A cleanup already in flight (uncommitted
as of this writing) moved five scrap files — `history.txt`, `scraps.txt`,
`ship.md`, `some ideas.txt`, `SFCOMBAT.txt` — from `content/` into
`content/lore/`, and deleted three redundant `.doc`/`.docx` binaries whose
content already exists as `.md` at the content root. That's a step in the
right direction but only touches a fraction of the mess, and it introduced
one broken link (see below).

This doc proposed, and this same pass executed, finishing the job with a
small number of purpose-named subfolders, replacing the flat junk drawer.

## What's actually in there

Investigated by reading file headers/content, not just names:

- **The four-page childhood website** (circa early 2000s, "The Super Family
  for Retards"): `index.html` and `evilies.html` currently sit in
  `content/`, while `battlesystem.html` and `history.html` sit in
  `content/lore/` — split across two directories even though `history.html`
  contains an in-page nav bar with relative links (`href="index.html"`,
  `href="battlesystem.html"`, etc.) that only work if all four pages are
  siblings. **That in-site navigation is already broken right now** because
  the pages aren't co-located. `sf.css` (root) is the shared stylesheet for
  all four. All four pages, plus `sf.css`, load their assets from a sibling
  `images/` folder.
- **`content/images/`** is really the asset folder for that site: 34 of its
  39 non-PDF files are referenced by the four HTML pages or by `sf.css`
  (confirmed by grep, not assumption — e.g. `drive_demo.png`,
  `gauges.png`, `rage_demo.png` etc. looked like unrelated screenshots by
  name alone but are actually UI mockups embedded in `battlesystem.html`).
  Genuinely unreferenced: `nopic.png`, `shield_health_demo.png` (superseded
  by `shield_health_demo2.png`), and `men-wear-masks-eraser-turnabout.png`
  (an *Eraser: Turnabout* reference image tied to the Influences list in
  `README.md`, not part of the site at all). The folder also holds three
  scanned-document PDFs (Bionicle MOCs, a LEGO Island manual, a Pokemon
  scan) that aren't images and don't belong in an `images/` folder.
- **Canonical narrative documents** — the polished pieces `README.md`
  actually points readers to under "Start Here": `The exact details of the
  Super Family.md`, `Super Family Prologue.md`, `The Return of Dr.
  Seinyor.md` (all at content root), plus `Dr. Seinyor.md` (already moved
  into `content/lore/`, inconsistently with the other three).
- **Raw lore/scrap material** — everything else already in `content/lore/`
  (`A.C..txt`, `SET 5936.txt`, `Powerteam Tapes.md`, `SF1 The First
  Movie.md`, the Contract PDF, etc.), plus two root strays that are the same
  kind of material: `The_Super_Family.txt` (a 2014 Zim wiki export) and
  `The Super Family - TV Series.txt` (a 3-line fragment).
- **Worldbuilding/inspiration notes**, mostly AI-chat transcripts or
  brainstorming, not in-universe canon: `Anagrams.md`, `Graph.md`,
  `whimsy.md`, `Iguazu Falls.md`, `LEGO Adventurers Jungle Theme.md`,
  `TOL_info.txt`, and `content/LEGO/rebuild-candidates.txt`.
- **Production/reference data**: `content/data/` (episode lists, CSVs,
  per-season metadata JSON — already reasonably organized), plus two root
  files that belong with it: `A.A. Network Schedule Christmas.xls` (an
  in-universe TV schedule) and the two root PDFs (`SF TV Series Notes
  (2023-08-21).pdf`, `Super Family TV Series.pdf`).
- **`content/transcripts/`** — already well-organized pipeline output with
  its own README; not touched by this proposal.

## Final layout

```
content/
├── narrative/        # The exact details of the Super Family.md
│                      # Super Family Prologue.md
│                      # The Return of Dr. Seinyor.md
│                      # Dr. Seinyor.md, plus Aliases.png, Basement Interior.png,
│                      #   and men-wear-masks-eraser-turnabout.png (see note below)
├── lore/              # everything that was in lore/, minus Dr. Seinyor.md, plus:
│                      # The_Super_Family.txt (from content root), the two
│                      #   scanned personal-creative PDFs (Bionicle MOCs, the
│                      #   Super Family Pokemon scan)
├── site-archive/      # index.html, evilies.html, battlesystem.html,
│                      # history.html, sf.css, images/ (as a subfolder, so all
│                      # existing relative paths keep working unchanged)
├── inspiration/       # Anagrams.md, Graph.md, whimsy.md, Iguazu Falls.md,
│                      # LEGO Adventurers Jungle Theme.md,
│                      # rebuild-candidates.txt (from content/LEGO/, with
│                      #   TOL_info.txt's content merged in), the LEGO Island
│                      #   manual scan
├── data/              # existing contents, plus A.A. Network Schedule
│                      # Christmas.xls, SF TV Series Notes (2023-08-21).pdf,
│                      # Super Family TV Series.pdf
└── transcripts/        # unchanged
```

Nothing here touched `docs/`, `scripts/`, or `content/transcripts/`.

**Deviation from the original proposal:** `Dr. Seinyor.md` embeds three images
via bare relative Markdown paths (`![Basement](Basement%20Interior.png)`,
etc.) — a link style that only works if the images sit in the *same*
directory as the doc, unlike Obsidian's `[[wikilink]]` syntax which resolves
by filename regardless of folder. Those links were already broken before
this cleanup (the doc was in `content/lore/`, the images were in
`content/` and `content/images/`). Rather than perpetuate that, all three
images moved to `content/narrative/` alongside `Dr. Seinyor.md`, including
`men-wear-masks-eraser-turnabout.png` — the earlier plan had that one going
to `inspiration/` on thematic grounds (it's an *Eraser: Turnabout* reference
image), but keeping the embed working took priority over the thematic
grouping.

Two of the three scanned-document PDFs that had been sitting in
`content/images/` (not images at all) went to `content/lore/`
(`Bionicle MOCs printed out and scanned.pdf`, the Super Family Pokemon scan)
as personal creative artifacts; the third, a scanned official LEGO Island
manual, went to `content/inspiration/` as reference material rather than
original creation.

## Snippet consolidation

Several very short, fragmentary files were merged into the larger document
they were thematically part of, rather than kept as standalone files:

- `A.C..txt` → appended to `content/lore/ship.md` (the Ship is explicitly
  the AC's precursor; the two documents describe the same lineage).
- `scraps.txt` and the 4-line `The Super Family - TV Series.txt` → appended
  to `content/lore/The_Super_Family.txt` (both are the same kind of raw
  worldbuilding-notes-dump as that file).
- `TOL_info.txt` (an old LEGO Shop@Home ordering note) → appended to
  `content/inspiration/rebuild-candidates.txt` (same register: practical
  LEGO reference notes).
- `some ideas.txt` was 0 bytes — deleted outright, nothing to merge.

Files that were short but complete and single-purpose (`Anagrams.md`,
`SET 5936.txt`, `SFCOMBAT.txt`) were left standalone rather than
force-merged into unrelated documents.

## Fallout to fix as part of the move

- `README.md` line 83, `[[content/ship|The Ship]]`, is **already broken** —
  `ship.md` moved to `content/lore/ship.md` in the uncommitted change but
  the path-qualified wikilink wasn't updated (path-qualified Obsidian links
  don't auto-follow a move the way bare `[[ship]]` links do). Needs to
  become `[[content/lore/ship|The Ship]]` regardless of whether the rest of
  this proposal is adopted.
- Bare wikilinks (`[[Anagrams]]`, `[[whimsy]]`, `[[Iguazu Falls]]`, `[[The
  exact details of the Super Family]]`, etc.) resolve by filename anywhere
  in the vault, so moving those files into subfolders will **not** break
  them in Obsidian.
- `sf.css`'s `background-image:url(css/images/logo3.png)` is already a
  dead/stale path (no `css/` subfolder exists; the real file is
  `images/logo3.png`) — pre-existing breakage, not something the move
  creates, but worth fixing in the same pass since the file is being
  touched anyway.

## Other decisions made

- `content/images/` moved wholesale to `content/site-archive/images/`.
  `nopic.png` and `shield_health_demo.png` (the two genuinely-unreferenced
  leftovers besides the Eraser: Turnabout image) moved with it rather than
  being deleted.
- `.DS_Store` was untracked (`git rm --cached`); `.gitignore` already
  covered it going forward.
- `.obsidian/` was untracked and added to `.gitignore` — it was judged
  accidental rather than an intentional cross-device sync of vault
  settings.

## Status

Done. Executed in the same session this doc was written, on top of an
already in-flight, uncommitted lore-consolidation move (five scrap files
into `content/lore/`, three redundant `.doc`/`.docx` duplicates deleted).
