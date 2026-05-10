#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  20-extract-audio.sh [-m manifest.tsv] [-o raw_audio_dir] [-t audio_track_index] [--force]

Extract one preservation WAV per video. The output keeps the selected audio
track at 48 kHz PCM for later cleanup.
USAGE
}

manifest="data/transcription/manifest.tsv"
out_dir="data/transcription/audio/raw"
track_index="0"
force="0"

while [ "$#" -gt 0 ]; do
  case "$1" in
    -m) manifest="$2"; shift 2 ;;
    -o) out_dir="$2"; shift 2 ;;
    -t|--track) track_index="$2"; shift 2 ;;
    --force) force="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required." >&2
  exit 127
fi

if [ ! -f "$manifest" ]; then
  echo "Manifest not found: $manifest" >&2
  exit 2
fi

mkdir -p "$out_dir"

tail -n +2 "$manifest" | while IFS=$'\t' read -r id source_path source_name; do
  out="$out_dir/$id.wav"
  if [ -f "$out" ] && [ "$force" != "1" ]; then
    echo "Skipping existing raw audio: $out"
    continue
  fi

  echo "Extracting audio track $track_index from: $source_name"
  ffmpeg -hide_banner -y -i "$source_path" \
    -map "0:a:$track_index" -vn -c:a pcm_s16le -ar 48000 \
    "$out"
  echo "  wrote $out"
done
