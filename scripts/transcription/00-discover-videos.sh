#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  00-discover-videos.sh [-o manifest.tsv] FILE_OR_DIR [...]

Find video files and write a manifest for the later transcription stages.

Examples:
  scripts/transcription/00-discover-videos.sh -o data/transcription/manifest.tsv data/videos
  scripts/transcription/00-discover-videos.sh movie1.mp4 movie2.m4v
USAGE
}

output="data/transcription/manifest.tsv"

while getopts ":o:h" opt; do
  case "$opt" in
    o) output="$OPTARG" ;;
    h) usage; exit 0 ;;
    :) echo "Missing value for -$OPTARG" >&2; usage; exit 2 ;;
    \?) echo "Unknown option: -$OPTARG" >&2; usage; exit 2 ;;
  esac
done
shift $((OPTIND - 1))

if [ "$#" -eq 0 ]; then
  echo "Provide at least one video file or directory." >&2
  usage
  exit 2
fi

mkdir -p "$(dirname "$output")"

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

for input in "$@"; do
  if [ -d "$input" ]; then
    find "$input" -type f \( \
      -iname '*.mp4' -o -iname '*.m4v' -o -iname '*.mov' -o -iname '*.mkv' -o -iname '*.avi' -o -iname '*.webm' \
    \) -print
  elif [ -f "$input" ]; then
    printf '%s\n' "$input"
  else
    echo "Skipping missing path: $input" >&2
  fi
done | sort -u > "$tmp"

{
  printf 'id\tsource_path\tsource_name\n'
  while IFS= read -r path; do
    abs="$(readlink -f "$path")"
    name="$(basename "$abs")"
    base="${name%.*}"
    slug="$(printf '%s' "$base" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//')"
    [ -n "$slug" ] || slug="video"
    digest="$(printf '%s' "$abs" | sha1sum | awk '{print substr($1,1,10)}')"
    printf '%s-%s\t%s\t%s\n' "$slug" "$digest" "$abs" "$name"
  done < "$tmp"
} > "$output"

count="$(($(wc -l < "$output") - 1))"
echo "Wrote $count video(s) to $output"
