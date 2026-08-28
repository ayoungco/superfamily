#!/usr/bin/env python3
"""Slice each movie's Whisper transcript into per-episode text files.

Reads content/transcripts/scenes/season-plan.tsv (from 70-assign-seasons.py)
and content/transcripts/raw/{video_id}.json (Whisper segments with
start/end timestamps), and writes one plain-text transcript per planned
episode -- segments whose start time falls in [episode_start, episode_end).
This is the input for generating a per-episode synopsis; it does no
summarization itself.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-p",
        "--plan",
        type=Path,
        default=Path("content/transcripts/scenes/season-plan.tsv"),
    )
    parser.add_argument(
        "-t",
        "--transcripts-dir",
        type=Path,
        default=Path("content/transcripts/raw"),
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("content/transcripts/scenes/episode-transcripts"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.plan.is_file():
        raise SystemExit(f"Season plan not found: {args.plan}")

    with args.plan.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    by_video: dict[str, list[dict]] = {}
    for row in rows:
        by_video.setdefault(row["video_id"], []).append(row)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    empty = 0
    for video_id, episodes in by_video.items():
        transcript_path = args.transcripts_dir / f"{video_id}.json"
        if not transcript_path.is_file():
            print(f"Skipping missing transcript: {transcript_path}")
            continue
        data = json.loads(transcript_path.read_text(encoding="utf-8"))
        segments = data["segments"]

        for episode in episodes:
            start = float(episode["start_seconds"])
            end = float(episode["end_seconds"])
            code = f"S{int(episode['season']):02d}E{episode['season_episode_number']}"
            lines = [
                s["text"].strip()
                for s in segments
                if start <= s["start"] < end and s["text"].strip()
            ]
            text = " ".join(lines)
            if not text:
                empty += 1
            output = args.output_dir / f"{code}.txt"
            output.write_text(text, encoding="utf-8")
            written += 1

    print(f"Wrote {written} episode transcript(s) to {args.output_dir} ({empty} empty)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
