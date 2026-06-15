#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  30-clean-audio.sh [-m manifest.tsv] [-i raw_audio_dir] [-o cleaned_audio_dir] [--profile speech|light|normalized] [--force]

Create mono 16 kHz WAV files for local Whisper transcription.

Profiles:
  speech      highpass + lowpass + moderate denoise + loudness normalize
  light       gentler denoise for audio where artifacts hurt recognition
  normalized  highpass + lowpass + loudness normalize, no denoise
USAGE
}

manifest="data/transcription/manifest.tsv"
in_dir="data/transcription/audio/raw"
out_dir="data/transcription/audio/cleaned"
profile="speech"
force="0"

while [ "$#" -gt 0 ]; do
  case "$1" in
    -m) manifest="$2"; shift 2 ;;
    -i) in_dir="$2"; shift 2 ;;
    -o) out_dir="$2"; shift 2 ;;
    --profile) profile="$2"; shift 2 ;;
    --force) force="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

case "$profile" in
  speech) filter="highpass=f=80,lowpass=f=7800,afftdn=nf=-25,loudnorm=I=-16:TP=-1.5:LRA=11" ;;
  light) filter="highpass=f=70,lowpass=f=8500,afftdn=nf=-18,loudnorm=I=-16:TP=-1.5:LRA=11" ;;
  normalized) filter="highpass=f=80,lowpass=f=7800,loudnorm=I=-16:TP=-1.5:LRA=11" ;;
  *) echo "Unknown profile: $profile" >&2; usage; exit 2 ;;
esac

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
  input="$in_dir/$id.wav"
  output="$out_dir/$id.$profile.wav"

  if [ ! -f "$input" ]; then
    echo "Skipping missing raw audio: $input" >&2
    continue
  fi

  if [ -f "$output" ] && [ "$force" != "1" ]; then
    echo "Skipping existing cleaned audio: $output"
    continue
  fi

  echo "Cleaning for speech ($profile): $source_name"
  ffmpeg -hide_banner -y -i "$input" \
    -ac 1 -ar 16000 -c:a pcm_s16le -af "$filter" \
    "$output"
  echo "  wrote $output"
done
