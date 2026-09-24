# Combat System as a Playable Game (idea)

Related: [[content/lore/SFCOMBAT|SFCOMBAT]] | [Site Archive Wiki Revival](site-archive-wiki-revival.md)

## The idea

`content/lore/SFCOMBAT.txt` is a fully specced turn-based battle system,
written as a kid, with real mechanics rather than vague flavor text:

- a Kingdom-Hearts-style overlapping shield/health gauge
- an Energy bar that locks and force-recharges if drained
- a Rage bar that builds passively from damage/stress and can be spent
  as backup Energy at the cost of recklessness
- a Pulse of Vengeance stack that buffs survivors as teammates fall,
  with damage formulas that explicitly exponentiate for the strongest
  skills (Hyper Supernova Beam: `100^spirits`)
- a Drive Gauge that fills from hits taken/dealt and unlocks
  stronger abilities at threshold ratings

This is a game design document, not just lore. The gauge art already
exists in `content/site-archive/images/`: `energy_demo.png`,
`rage_demo.png`, `pulse_demo.png`, `drive_demo.png`,
`shield_health_demo.png`. Building a browser-playable turn-based battler
around this spec, using the original assets, is a much smaller lift than
it sounds because the hard design work is already done.

## Sketch

- Implement the gauges and turn resolution as specced (shield → health,
  Energy lock/recharge, Rage accumulation, Pulse stacking on KO, Drive
  thresholds).
- Start with a small roster — Dr. Seinyor and a handful of named
  fighters from `content/lore/SFCOMBAT.txt` — rather than the full
  crossover cast.
- Character portraits: reuse `content/site-archive/images/` where a
  fighter already has art, otherwise see
  [Original Character Art](original-character-art.md).

## Open questions

- How literally to implement the more absurd scaling (100 quintillion
  damage numbers) vs. rebalancing for playability.
- Whether this targets a quick browser toy (single page, no backend) or
  something more durable — the former is almost certainly the right
  starting scope.
- Which fighters/movesets to implement first; `SFCOMBAT.txt` doesn't
  give complete stat blocks for every character, so some will need to be
  invented in the spirit of the original.
