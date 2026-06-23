# Local Media Drop Zone

Related: [[scripts/transcription/README|Local Video Transcription Workflow]] | [[transcripts/README|Transcripts]]

See [[docs/guides/media-ingest-and-chunking|Media Ingest and Episode Chunking]]
before copying or splitting a large batch.

Everything in this directory except this README is ignored by Git.

- `inbox/`: drop camcorder movies and other source video/audio here.
- `archive/`: optional local holding area after a source has been processed.

The transcription manifest records absolute source paths, so the large files
may also live on an external drive. Pass that directory directly to
`scripts/transcription/00-discover-videos.sh` instead of copying it here.

Do not edit or overwrite original recordings during transcription.
