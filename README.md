# Super Family TV Series

The Super Family is a crossover universe I created in my youth.

The Super Family is one of my childhood personal universes. The origins are a long story, maybe I should be creating a VitePress or Obsidian repo about them as well.

Lots of crossovers to "worlds" ala Kingdom Hearts, but predating that concept... unless it occurred in parallel thinking?

## Drive mounts

```
sudo mount -t cifs //10.0.0.3/creative /mnt/creative -o username=YOUR_USERNAME,password=YOUR_PASSWORD,vers=3.0
```



## Work notes

- Use scanned drawings and other assets
- Try a good text to speech narration using voice clips from young me
- Train young me as an AI voice - this would be absolutely bonkers
- [Text-to-speech model](https://www.reddit.com/r/singularity/comments/1l46lz5/introducing_eleven_v3_alpha_the_most_expressive/?share_id=hnjoc5hin-HDZBnVmmJN9&utm_medium=ios_app&utm_name=ioscss&utm_source=share&utm_term=1) - may be good for producing additional narration in segments that are under-explained
- Use Sora

Formerly known as "The Powerteam"

The adventures of Dr. Seinyor and Stacie.

- Extract dialogue from movies, transfer to Voice Memos and transcribe for text content `scripts`
- Does a utility/model exist for generating a screenplay from video files or extracted auto?

Text-only archive of my writings for the Super Family

Open [[Vault Index]] for the Obsidian-oriented map of the archive.

## Project Goals

- Generatively iterate this universe based on retrieved archival context.
- Reconnect with this universe by using agents as a creative tool for self-learning.
- Recover dialogue and story context through [[transcripts/README|Transcripts]] and the
  [[scripts/transcription/README|Local Video Transcription Workflow]].
- Detect visual cuts and export local clips with the
  [[scripts/scenes/README|Scene Detection and Clip Export Workflow]].

## Status

### Tasks

- [x] Separate SF and Powerteam movies into 1-hour episodes
- [ ] Export 1 hour episodes from Premiere, don't worry about intro/outro, just get the content into bite-sized chunks for easier processing and transcription. See [Programmatic Episode Splitting](docs/programmatic-episode-splitting.md) for a plan to do this with 10-20 minute episodes using the scene-detection data instead of manual Premiere cuts.
- [ ] Meaningful titles for each episode
- [ ] One audio channel drops out in some movies, needs restored

### Ideas

- Battle scenes: mask out the human handlers. Many battle shots are
  side-on with the humans visibly manipulating the characters, to make a
  larger character appear to be attacked. Camera is *believed* static
  (unverified). See
  [Battle Scene Human Removal](docs/battle-scene-human-removal.md) for
  the full research: why this splits into three sub-problems of very
  different difficulty, where reference imagery per character would come
  from, and the 2D-inpainting vs. 3D-render tradeoff. Scene detection +
  person-classification has since been run across the full archive; see
  [Scene Classification Results](docs/scene-classification-results.md).


# Super Family Vault Index

This vault collects the history, stories, production notes, research, and
archival material for [[The exact details of the Super Family|The Super Family]],
formerly known as the Powerteam.

## Start Here

- [[The exact details of the Super Family]] - the origin and early history.
- [[Super Family Prologue]] - the cosmological framing for the setting.
- [[The Return of Dr. Seinyor]] - a later continuation after the team's disappearance.
- [[Dr. Seinyor]] - current character and reconstruction notes.

## World And Design

- [[content/ship|The Ship]] - precursor to the AC.
- [[Iguazu Falls]] - AC design, environments, and reconstruction ideas.
- [[LEGO Adventurers Jungle Theme]] - visual and historical inspiration.
- [[whimsy|Whimsical locations]] - real-world fantasy landscape references.
- [[Anagrams]] - name and phrase experiments.

## Archive Workflow

- [[docs/media-ingest-and-chunking|Media Ingest and Episode Chunking]] - readiness, storage, and split guidance.
- [[content/transcripts/README|Transcripts]] - tracked raw and reviewed transcript organization, and pipeline output layout.
- [[scripts/transcription/README|Local Video Transcription Workflow]] - executable local workflow.
- [[scripts/scenes/README|Local Scene Detection and Clip Export]] - detect visual cuts and export ignored local clips.
- [[docs/whisper-transcription|Local Whisper Transcription]] - workstation setup and model notes.
- [[docs/audio-extraction-and-transcription|Extracting Audio Tracks and Transcribing Muddy VHS Video]] - detailed archival guidance.
- [[docs/voice-generative|Voice reconstruction goal]] - possible later use of cleaned speech.
- [Battle Scene Human Removal](docs/battle-scene-human-removal.md) - research on masking human handlers out of battle shots.
- [Programmatic Episode Splitting](docs/programmatic-episode-splitting.md) - plan for cutting movies into 10-20 minute episodes using scene-detection data.

## Project Notes

- [Repository overview](README.md)
- [[Graph]] - notes on using Markdown and Obsidian as a knowledge graph.


## Influences

- LEGO Island
- Gateway 2000
- Eraser: Turnabout
- Descent
- Redwall
- Harry Potter
- Barbie Stacie
- 1990s LEGO Aircraft and Spacecraft
- Star Wars Episode I: The Phantom Menace
- Bionicle
- Armored Core
- Pokemon
- The Powerpuff Girls
- Dragonball Z
- Kingdom Hearts
- The New Adventures of Winnie the Pooh
- The Backstreet Boys
- Britney Spears
- Crash Bandicoot
- Spyro the Dragon
- Gex
- Transformers Armada

# Rules 