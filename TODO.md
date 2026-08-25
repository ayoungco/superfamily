# Tasks

- [x] Separate SF and Powerteam movies into 1-hour episodes
- [ ] Export 1 hour episodes from Premiere, don't worry about intro/outro, just get the content into bite-sized chunks for easier processing and transcription.
- [ ] Meaningful titles for each episode
- [ ] One audio channel drops out in some movies, needs restored

# Ideas

- Battle scenes: mask out the human handlers. Many battle shots are
  side-on with the humans visibly manipulating the characters, to make a
  larger character appear to be attacked. Camera is *believed* static
  (unverified -- check for camcorder drift and VHS time-base jitter before
  assuming a clean-plate approach works).

  Three problems, not one:
  1. Human occluding static background -- solvable with a temporal-median
     clean plate built from other frames of the same shot. Real pixels,
     temporally coherent, no generative model needed.
  2. Hand/arm occluding the character it holds -- no frame shows that pose
     unoccluded, so this needs generative fill or hand-painting.
  3. The hand is the *cause* of the motion. Remove it and the figure must
     read as airborne/self-supported; some shots will look worse. The
     handler's cast shadow is part of the occlusion too.

  Per-shot VFX work, not a batch pipeline. List candidate shots
  (movie + timestamp) before estimating effort.