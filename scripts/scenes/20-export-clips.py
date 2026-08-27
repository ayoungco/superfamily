#!/usr/bin/env python3
"""Export clips from scene-boundary TSV files."""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-m",
        "--manifest",
        type=Path,
        default=Path("content/transcripts/manifest.tsv"),
    )
    parser.add_argument(
        "-d",
        "--detections-dir",
        type=Path,
        default=Path("content/transcripts/scenes/detections"),
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("content/transcripts/scenes/clips"),
    )
    parser.add_argument(
        "--mode",
        choices=("encode", "copy"),
        default="encode",
        help="Accurate H.264/AAC clips, or fast keyframe-aligned stream copies.",
    )
    parser.add_argument("--crf", type=int, default=20)
    parser.add_argument("--preset", default="medium")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--candidates",
        type=Path,
        default=None,
        help="TSV with video_id/clip_index columns (e.g. from "
        "40-select-candidates.py). If given, only those clips are exported.",
    )
    parser.add_argument(
        "--dates",
        type=Path,
        default=None,
        help="TSV with video_id/approx_date columns. If given, exported clips "
        "are prefixed with the movie's approximate date instead of its id.",
    )
    return parser.parse_args()


def export_command(
    source: Path,
    output: Path,
    start: str,
    duration: str,
    mode: str,
    crf: int,
    preset: str,
) -> list[str]:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-nostdin",
        "-y",
        "-ss",
        start,
        "-i",
        str(source),
        "-t",
        duration,
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
    ]
    if mode == "copy":
        command.extend(["-c", "copy", "-avoid_negative_ts", "make_zero"])
    else:
        command.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                preset,
                "-crf",
                str(crf),
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
            ]
        )
    command.append(str(output))
    return command


def main() -> int:
    args = parse_args()
    if not 0 <= args.crf <= 51:
        raise SystemExit("--crf must be between 0 and 51.")
    if not args.manifest.is_file():
        raise SystemExit(f"Manifest not found: {args.manifest}")

    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        raise SystemExit("ffmpeg is required.")

    with args.manifest.open(encoding="utf-8", newline="") as handle:
        videos = list(csv.DictReader(handle, delimiter="\t"))

    wanted_clips: dict[str, set[str]] | None = None
    if args.candidates is not None:
        wanted_clips = {}
        with args.candidates.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                wanted_clips.setdefault(row["video_id"], set()).add(row["clip_index"])

    approx_dates: dict[str, str] = {}
    if args.dates is not None:
        with args.dates.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                if row.get("approx_date"):
                    approx_dates[row["video_id"]] = row["approx_date"]

    for video in videos:
        if wanted_clips is not None and video["id"] not in wanted_clips:
            continue

        source = Path(video["source_path"])
        detection = args.detections_dir / f"{video['id']}.scenes.tsv"
        if not source.is_file():
            print(f"Skipping missing source: {source}", file=sys.stderr)
            continue
        if not detection.is_file():
            print(f"Skipping missing detection: {detection}", file=sys.stderr)
            continue

        label = approx_dates.get(video["id"], video["id"])
        clip_dir = args.output_dir / label
        clip_dir.mkdir(parents=True, exist_ok=True)
        with detection.open(encoding="utf-8", newline="") as handle:
            clips = list(csv.DictReader(handle, delimiter="\t"))

        if wanted_clips is not None:
            clips = [c for c in clips if c["clip_index"] in wanted_clips[video["id"]]]

        for clip in clips:
            output = clip_dir / f"{label}-scene-{clip['clip_index']}.mp4"
            if output.exists() and not args.force:
                print(f"Skipping existing clip: {output}")
                continue
            print(
                f"Exporting {output.name}: "
                f"{clip['start_seconds']}s + {clip['duration_seconds']}s"
            )
            subprocess.run(
                export_command(
                    source,
                    output,
                    clip["start_seconds"],
                    clip["duration_seconds"],
                    args.mode,
                    args.crf,
                    args.preset,
                ),
                check=True,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
