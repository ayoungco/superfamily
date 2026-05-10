#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  10-probe-audio.sh [-m manifest.tsv] [-o probe_dir]

Run ffprobe for every source video in the manifest.
USAGE
}

manifest="data/transcription/manifest.tsv"
out_dir="data/transcription/probes"

while getopts ":m:o:h" opt; do
  case "$opt" in
    m) manifest="$OPTARG" ;;
    o) out_dir="$OPTARG" ;;
    h) usage; exit 0 ;;
    :) echo "Missing value for -$OPTARG" >&2; usage; exit 2 ;;
    \?) echo "Unknown option: -$OPTARG" >&2; usage; exit 2 ;;
  esac
done

if ! command -v ffprobe >/dev/null 2>&1; then
  echo "ffprobe is required. Install ffmpeg first." >&2
  exit 127
fi

if [ ! -f "$manifest" ]; then
  echo "Manifest not found: $manifest" >&2
  exit 2
fi

mkdir -p "$out_dir"

tail -n +2 "$manifest" | while IFS=$'\t' read -r id source_path source_name; do
  log="$out_dir/$id.ffprobe.txt"
  json="$out_dir/$id.streams.json"
  echo "Probing: $source_name"
  ffprobe -hide_banner -i "$source_path" > "$log" 2>&1 || true
  ffprobe -v error -show_streams -show_format -of json "$source_path" > "$json"
  echo "  wrote $log"
  echo "  wrote $json"
done
