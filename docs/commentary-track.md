# Bonus-Features Commentary Track (idea)

Related: [[docs/voice-generative|Voice reconstruction goal]] | `scripts/scenes/94-publish-to-plex.py`

## The idea

A DVD-commentary-style audio layer over specific episodes: present-day
narration (or, if [[docs/voice-generative|the voice reconstruction
work]] pans out, a reconstructed young-you voice) reacting to and
contextualizing what's on screen — "this is the day we broke the
camera," who's behind which figure, what was actually going on off
camera. Pairs naturally with the Plex publish once `/mnt/media` write
access is unblocked, as an optional bonus-features track rather than
something baked into the main episode audio.

## Sketch

- Pilot on a single episode before committing to more: pick one with
  known behind-the-scenes stories, record commentary against it, see
  whether it's actually worth the effort per-episode before scaling.
- Source material for the commentary itself has to come from somewhere
  — most likely a structured self-interview (or an interview with
  whoever else was involved as a kid) prompted by watching the footage
  back, not something an LLM can invent.
- Delivery as a separate audio track (Plex supports multiple audio
  streams) rather than remixed into the original, so the untouched
  original is always available.

## Open questions

- Whether the reconstructed-voice approach is ready in time, or this
  starts as present-day narration and gets a pass with the cloned voice
  later.
- How much anecdotal material actually exists/is rememberable per
  episode — this may only be worth doing for a handful of episodes with
  real stories behind them, not the full catalog.
