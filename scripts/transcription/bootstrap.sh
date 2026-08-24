#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
venv="$repo_root/.venv-transcription"
install="0"

if [ "${1:-}" = "--install" ]; then
  install="1"
elif [ "$#" -gt 0 ]; then
  echo "Usage: $0 [--install]" >&2
  exit 2
fi

mkdir -p \
  "$repo_root/content/transcripts/audio/raw" \
  "$repo_root/content/transcripts/audio/cleaned" \
  "$repo_root/content/transcripts/probes" \
  "$repo_root/content/transcripts/logs" \
  "$repo_root/content/transcripts/raw" \
  "$repo_root/content/transcripts/reviewed" \
  "$repo_root/content/transcripts/diarization"

if [ ! -x "$venv/bin/python" ]; then
  python3 -m venv "$venv"
  echo "Created $venv"
else
  echo "Using existing $venv"
fi

if [ "$install" = "1" ]; then
  "$venv/bin/python" -m pip install --upgrade pip
  "$venv/bin/python" -m pip install -r "$repo_root/scripts/transcription/requirements.txt"
fi

cat <<EOF

Transcription workspace is ready.

1. Point discovery straight at your source media (no need to copy it into the
   repo): bash scripts/transcription/00-discover-videos.sh /mnt/creative/projects/superfamily
2. Activate the environment: source $venv/bin/activate

Extracted audio, probes, logs, and the venv are ignored by Git. Source video
is never copied locally; the manifest stores absolute paths. Files under
content/transcripts/raw and content/transcripts/reviewed are intended to be
reviewed and committed.
EOF
