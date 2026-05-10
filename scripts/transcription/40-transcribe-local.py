#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe cleaned audio files locally with faster-whisper."
    )
    parser.add_argument("-m", "--manifest", default="data/transcription/manifest.tsv")
    parser.add_argument("-i", "--audio-dir", default="data/transcription/audio/cleaned")
    parser.add_argument("-o", "--output-dir", default="data/transcription/transcripts")
    parser.add_argument("--profile", default="speech")
    parser.add_argument("--model", default="large-v3")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--compute-type", default="float16")
    parser.add_argument("--language", default="en")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--initial-prompt", default=None)
    parser.add_argument("--vad-filter", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def srt_timestamp(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def vtt_timestamp(seconds: float) -> str:
    return srt_timestamp(seconds).replace(",", ".")


def write_outputs(out_base: Path, segments: list[dict], info: object, source_audio: Path) -> None:
    txt_path = out_base.with_suffix(".txt")
    srt_path = out_base.with_suffix(".srt")
    vtt_path = out_base.with_suffix(".vtt")
    json_path = out_base.with_suffix(".json")
    md_path = out_base.with_suffix(".raw.md")

    txt_path.write_text(
        "\n".join(segment["text"].strip() for segment in segments if segment["text"].strip()) + "\n",
        encoding="utf-8",
    )

    with srt_path.open("w", encoding="utf-8") as handle:
        for index, segment in enumerate(segments, start=1):
            handle.write(f"{index}\n")
            handle.write(f"{srt_timestamp(segment['start'])} --> {srt_timestamp(segment['end'])}\n")
            handle.write(f"{segment['text'].strip()}\n\n")

    with vtt_path.open("w", encoding="utf-8") as handle:
        handle.write("WEBVTT\n\n")
        for segment in segments:
            handle.write(f"{vtt_timestamp(segment['start'])} --> {vtt_timestamp(segment['end'])}\n")
            handle.write(f"{segment['text'].strip()}\n\n")

    metadata = {
        "source_audio": str(source_audio),
        "language": getattr(info, "language", None),
        "language_probability": getattr(info, "language_probability", None),
        "duration": getattr(info, "duration", None),
        "segments": segments,
    }
    json_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with md_path.open("w", encoding="utf-8") as handle:
        handle.write(f"# {out_base.name} Transcript\n\n")
        handle.write(f"Source audio: `{source_audio}`\n")
        handle.write("Review status: raw machine transcript\n\n")
        handle.write("## Transcript\n\n")
        for segment in segments:
            start = vtt_timestamp(segment["start"]).replace(".", ",")
            text = segment["text"].strip()
            if text:
                handle.write(f"{start} - {text}\n\n")


def main() -> int:
    args = parse_args()

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print(
            "Missing dependency: faster-whisper. Install it in your local transcription environment.",
            file=sys.stderr,
        )
        return 127

    manifest = Path(args.manifest)
    audio_dir = Path(args.audio_dir)
    out_dir = Path(args.output_dir)

    if not manifest.exists():
        print(f"Manifest not found: {manifest}", file=sys.stderr)
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"Loading faster-whisper model={args.model} device={args.device} compute_type={args.compute_type}",
        flush=True,
    )
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)

    with manifest.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            video_id = row["id"]
            source_name = row["source_name"]
            audio_path = audio_dir / f"{video_id}.{args.profile}.wav"
            out_base = out_dir / f"{video_id}.{args.profile}"

            if not audio_path.exists():
                print(f"Skipping missing cleaned audio: {audio_path}", file=sys.stderr)
                continue

            if out_base.with_suffix(".json").exists() and not args.force:
                print(f"Skipping existing transcript: {out_base.with_suffix('.json')}")
                continue

            print(f"Transcribing locally: {source_name}", flush=True)
            segment_iter, info = model.transcribe(
                str(audio_path),
                language=args.language,
                beam_size=args.beam_size,
                initial_prompt=args.initial_prompt,
                vad_filter=args.vad_filter,
            )
            segments = [
                {
                    "id": segment.id,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "avg_logprob": segment.avg_logprob,
                    "no_speech_prob": segment.no_speech_prob,
                }
                for segment in segment_iter
            ]
            write_outputs(out_base, segments, info, audio_path)
            print(f"  wrote {out_base}.txt/.srt/.vtt/.json/.raw.md", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
