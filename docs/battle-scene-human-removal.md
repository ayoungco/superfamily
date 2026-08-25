# Battle Scene Human Removal (research)

Related: [Local Scene Detection and Clip Export](../scripts/scenes/README.md)

## The idea

Many battle scenes are shot side-on with the human actors visibly
manipulating the action figures to make a larger character appear to
attack. If the humans could be masked out of frame, the battles would
read as far more convincing.

Camera is *believed* static in these shots — unverified. Check for
camcorder drift and VHS time-base jitter before assuming a clean-plate
approach works; a locked-off tripod shot on paper can still defeat this
if the transfer has enough jitter.

## Three sub-problems, not one

The original framing ("masking is easy, inpainting the occluded parts is
hard") collapses three problems of very different difficulty:

1. **Human occluding static background.** Solvable without any generative
   model — build a temporal-median clean plate from other frames in the
   same shot where that background region is unoccluded. Real pixels,
   temporally coherent.
2. **Hand/arm occluding the character it's holding.** No other frame in
   that shot shows the character in that exact pose unoccluded, so the
   clean-plate trick doesn't apply. Needs either generative fill
   conditioned on reference images of that character, or a rendered
   3D stand-in (see below).
3. **The hand is the *cause* of the motion.** Removing it can make the
   figure look unsupported mid-swing rather than convincingly animated.

## Resolved: the "floating" failure mode is not a failure mode here

Per-user direction: unsupported/floating motion after removal is fine —
it reads as charming and "something cool was done to make this happen"
rather than as a bug. This removes sub-problem 3 as a blocker entirely;
the remaining work is sub-problems 1 and 2.

## Sourcing reference samples for sub-problem 2

Getting sub-problem 2 right (not just plausible, but accurate to the
actual toy) needs reference imagery of each character, since a generic
inpainting model has no way to know what a specific figure's paint job
looks like. Two sources:

- **Mine frames from elsewhere in the footage.** Same physical toy
  recurs across many shots and angles throughout the whole series — a
  similarity-search / re-identification pass across all footage could
  collect a reference bank per character automatically.
- **Photograph the surviving physical toys, if they still exist.** Clean
  modern multi-angle stills would beat anything mineable from grainy
  VHS, and it's cheap if the actual figures are still around.

## 2D exemplar-conditioned inpainting vs. 3D reconstruction

Two viable technical approaches for sub-problem 2, given these are
rigid-ish physical objects rather than deforming humans:

- **2D, reference-conditioned inpainting.** Feed reference photos of the
  character as conditioning to an image inpainting model to fill the
  masked region. Lower upfront cost; risk of frame-to-frame
  inconsistency/flicker and imperfect angle-matching.
- **3D reconstruction + render.** Scan or photogrammetry the physical
  figure, roughly track its pose per frame, and render+composite it
  directly into the masked region. No hallucination — the actual object
  is being rendered — at the cost of doing pose tracking. Given the bar
  here is "charming," not photoreal, this is probably overkill unless
  the 2D approach turns out too inconsistent frame-to-frame.

## Scope

This is per-shot VFX work, not a batch pipeline — every shot needs a
mask, and sub-problem 2 needs a per-character reference bank. Before
estimating effort, build a candidate shot list (movie + timestamp) of
shots that actually have a visible human handler. See
[Local Scene Detection and Clip Export](../scripts/scenes/README.md) for
the (already written, not yet run) shot-boundary tool this candidate
list should build on.
