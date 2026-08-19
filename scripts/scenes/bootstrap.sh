#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"

for tool in ffmpeg ffprobe python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "$tool is required." >&2
    exit 127
  fi
done

mkdir -p \
  "$repo_root/content/transcripts/scenes/detections" \
  "$repo_root/content/transcripts/scenes/clips" \
  "$repo_root/content/transcripts/scenes/logs"

cat <<EOF

Scene workspace is ready.

1. Create or reuse the video manifest, pointed straight at your source media:
   bash scripts/transcription/00-discover-videos.sh /mnt/creative/projects/superfamily
2. Detect scenes:
   python3 scripts/scenes/10-detect-scenes.py
3. Review content/transcripts/scenes/detections, then export:
   python3 scripts/scenes/20-export-clips.py

Source media, scene metadata, logs, and exported clips are ignored by Git.
EOF
