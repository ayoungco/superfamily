# Local Media Drop Zone

Everything in this directory except this README is ignored by Git.

- `inbox/`: drop camcorder movies and other source video/audio here.
- `archive/`: optional local holding area after a source has been processed.

The transcription manifest records absolute source paths, so the large files
may also live on an external drive. Pass that directory directly to
`scripts/transcription/00-discover-videos.sh` instead of copying it here.

Do not edit or overwrite original recordings during transcription.
