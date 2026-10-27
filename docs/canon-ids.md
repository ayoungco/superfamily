# Canon IDs

Related: [Continuity Bible](continuity-bible.md) | [Crossover Universe Knowledge Graph](crossover-knowledge-graph.md)

Every canon thing (character, world, machine, era, movie, or real-world inspiration) gets one
stable ID. The canon pages, the [knowledge graph](crossover-knowledge-graph.md) and the
[continuity bible](continuity-bible.md) all use these IDs. A private real-life timeline, kept
outside this public repo, refers to them too. That way this repo never holds life data,
and the two can still be joined.

## Rules

- **Form:** `lore:<slug>`, with a lowercase kebab-case slug, for example `lore:dr-seinyor`.
- **Stable:** once used, an ID never changes meaning and is never reused. If a thing is
  renamed in-universe (Powerteam → Super Family), the ID stays the same and the new name
  becomes an alias.
- **Kind** goes in the canon page's front matter, not the ID: `character`, `world`, `place`,
  `machine`, `artifact`, `attack`, `era`, `work` (a movie, tape or episode) or `real-world`
  (a real game, toy line or show that inspired the canon).
- **Movies** use their series number: `lore:sf1` … `lore:sf14`.
- **Real-world inspirations** get a slug that names the thing: `lore:ac-silent-line`.
- **Aliases and spellings** are listed on the page, not split into new IDs (Stacie / Stacey).
- **No life data here:** no real names of family members, addresses or dates from the family archive. Those
  live in the private timeline, which points at these IDs.

## Seed list

| ID | Kind | Name | Source |
|---|---|---|---|
| `lore:era-powerteam` | era | The Powerteam (the series' original name) | README, `content/lore/history.txt` |
| `lore:era-super-family` | era | The Super Family | `content/lore/history.txt` |
| `lore:powerteam-show` | work | Powerteam, the pre-LEGO show hosted by Dr. Seinyor | `content/lore/Powerteam Tapes.md` |
| `lore:dr-seinyor` | character | Dr. Seinyor, Raven AC pilot, the Powerteam's best | `content/narrative/Dr. Seinyor.md`, `history.txt` |
| `lore:stacie` | character | Stacie (also spelled Stacey), Dr. Seinyor's sidekick | README, Powerteam |
| `lore:nell-aulter` | character | Nell Aulter, manager of the Raven Arena | `history.txt` |
| `lore:raven-arena` | place | The Raven Arena, AC vs AC sport | `history.txt` |
| `lore:ac-battle-station` | machine | The AC battle station: house in the head, army in the legs | `history.txt`, `content/lore/ship.md` |
| `lore:the-ship` | machine | The Powerteam's ship | `content/lore/ship.md` |
| `lore:mata-nui` | world | Mata Nui | `ship.md`, the movies |
| `lore:makuta` | character | Makuta | the movies |
| `lore:sf1` | work | The First Movie (Makuta's Reign) | `content/data/super_family_episodes_v2.csv` |
| `lore:sf2` | work | The Second Movie | transcripts |
| `lore:sf3` | work | Makuta's Revenge | transcripts |
| `lore:sf4` | work | The Fourth Movie | transcripts |
| `lore:sf5` | work | Escape from Mata Nui | transcripts |
| `lore:sf6` | work | Return Home | transcripts |
| `lore:sf7` | work | The Toa Nuva | transcripts |
| `lore:sf8` | work | Kal | transcripts |
| `lore:sf9` | work | The Beginning | transcripts |
| `lore:sf10` | work | Prepare for the War | transcripts |
| `lore:sf11` | work | The Universal War | transcripts, `The Universal War [SF11].prproj` |
| `lore:sf12` | work | The Final Battle | transcripts |
| `lore:sf13` | work | Destiny | transcripts |
| `lore:sf14` | work | The Great Vacation | transcripts |
| `lore:ac-1` | real-world | Armored Core (PS1), first played from a demo disc | Adam |
| `lore:ac-project-phantasma` | real-world | Armored Core: Project Phantasma | Adam (the PS1 trilogy) |
| `lore:ac-master-of-arena` | real-world | Armored Core: Master of Arena | Adam (the PS1 trilogy) |
| `lore:ac-2` | real-world | Armored Core 2 | Adam |
| `lore:ac-another-age` | real-world | Armored Core 2: Another Age | Adam |
| `lore:ac-3` | real-world | Armored Core 3 | Adam |
| `lore:ac-silent-line` | real-world | Silent Line: Armored Core | Adam |
| `lore:ac-6` | real-world | Armored Core VI: Fires of Rubicon | Adam |
| `lore:bionicle` | real-world | LEGO Bionicle | the movies |
| `lore:lego-island` | real-world | LEGO Island | `content/inspiration/` |
| `lore:kingdom-hearts` | real-world | Kingdom Hearts (crossover worlds, in parallel) | README |

Add IDs as the canon pages are written. This table is the register; check it before
minting a new one.
