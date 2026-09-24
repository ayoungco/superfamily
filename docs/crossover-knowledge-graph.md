# Crossover Universe Knowledge Graph (idea)

Related: [[Graph]] | [[The exact details of the Super Family]] | [Continuity Bible](continuity-bible.md)

## The idea

The narrative casually links a dozen outside franchises into one
continuity — Bionicle, Star Wars, Pokémon, the Powerpuff Girls, Crash
Bandicoot, Armored Core, Redwall, and more all show up as visiting
characters or crossover arcs in
[[The exact details of the Super Family]] alone. `content/inspiration/Graph.md`
already muses about using Obsidian's built-in graph view for this, but
that graph is just wikilinks between documents — it can't show *who
fought whom*, *who joined the team when*, or *which artifact came from
which world*.

## Sketch

- Extract entities (characters, worlds/franchises, artifacts, named
  attacks, locations) and relationships (joined-team, fought,
  adopted-by, portal-to, gave-power-to) from `content/narrative/`,
  `content/lore/`, and the transcripts.
- Render as an interactive force-directed graph (e.g. a D3-based
  artifact) rather than Obsidian's generic doc-to-doc graph — nodes
  typed and colored by kind (character / world / artifact), edges
  labeled by relationship.
- Time-slice if the extraction captures enough chronology: watching the
  crossover network grow arc-by-arc (Crash Bandicoot → Star Wars →
  Powerpuff Girls → Pokémon → Redwall → Armored Core, per the order in
  [[The exact details of the Super Family]]) would visualize the
  universe's expansion, not just its final state.

## Open questions

- Extraction is the real work here — the source prose is long-form
  narrative, not structured data, so entities/relationships need an
  LLM pass with spot-checking rather than a clean parse.
- Where the extracted graph data lives: a one-time JSON artifact vs.
  something regenerated as more transcripts/lore get processed.
- Whether this stands alone as a shareable artifact or becomes a page
  inside [Site Archive Wiki Revival](site-archive-wiki-revival.md).
