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
  "$repo_root/media/inbox" \
  "$repo_root/media/archive" \
  "$repo_root/data/transcription/audio/raw" \
  "$repo_root/data/transcription/audio/cleaned" \
  "$repo_root/data/transcription/probes" \
  "$repo_root/data/transcription/logs" \
  "$repo_root/transcripts/raw" \
  "$repo_root/transcripts/reviewed" \
  "$repo_root/transcripts/context"

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

1. Drop source files into: $repo_root/media/inbox
2. Activate the environment: source $venv/bin/activate
3. Discover files:
   bash scripts/transcription/00-discover-videos.sh media/inbox

Source media, extracted audio, probes, logs, and the venv are ignored by Git.
Files under transcripts/ are intended to be reviewed and committed.
EOF
