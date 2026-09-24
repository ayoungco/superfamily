# Continuity Bible / Canon Consistency Pass (idea)

Related: [[The exact details of the Super Family]] | [[content/lore/SFCOMBAT|SFCOMBAT]] | [Crossover Universe Knowledge Graph](crossover-knowledge-graph.md)

## The idea

The narrative spans years of writing at different ages (the earliest
narrative doc is dated 2008, `content/lore/ship.md` has a scrap merged
in from 2014) and was never written with a bible to check against. It
almost certainly contradicts itself, especially in the stat/power
scaling — `content/lore/SFCOMBAT.txt` gives exact formulas (Hyper
Supernova Beam's damage exponentiating per Pulse charge) that a kid
writing over multiple years is unlikely to have applied consistently
scene to scene.

## Sketch

- LLM-assisted pass across `content/narrative/`, `content/lore/`, and
  the reviewed transcripts, flagging apparent contradictions: power
  levels, timeline order, character relationships, retcons (the
  Powerteam → Super Family rename is a known one; there are likely
  others).
- Produce one canonical reference document, Marvel-handbook style: per
  character stat blocks, timeline, world rules — with contradictions
  either resolved with a judgment call or explicitly noted as "varies by
  source, no ruling made."
- This pairs well with
  [Crossover Universe Knowledge Graph](crossover-knowledge-graph.md) —
  the entity/relationship extraction for the graph and the contradiction
  search for the bible can likely share the same source pass.

## Open questions

- Some "contradictions" are probably deliberate in-universe retcons
  (the team renaming itself) rather than errors — the pass needs to
  distinguish those, which requires judgment, not just diffing.
- Whether this is a one-time cleanup document or something that gets
  re-run as more transcripts get reviewed and more canon material
  surfaces.
