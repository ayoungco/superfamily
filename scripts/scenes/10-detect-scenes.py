#!/usr/bin/env python3
"""Detect visual cuts in videos and write clip boundaries as TSV files."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path


PTS_TIME = re.compile(r"\bpts_time:([0-9]+(?:\.[0-9]+)?)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-m",
        "--manifest",
        type=Path,
        default=Path("content/transcripts/manifest.tsv"),
        help="Video manifest created by 00-discover-videos.sh.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("content/transcripts/scenes/detections"),
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.30,
        help="FFmpeg scene-change score from 0 to 1 (default: 0.30).",
    )
    parser.add_argument(
        "--min-duration",
        type=float,
        default=2.0,
        help="Ignore cuts closer than this many seconds (default: 2).",
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def require_tool(name: str) -> None:
    try:
        subprocess.run(
            [name, "-version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        raise SystemExit(f"{name} is required.")


def video_duration(source: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(source),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def detect_cuts(source: Path, threshold: float) -> list[float]:
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(source),
            "-an",
            "-vf",
            f"select='gt(scene,{threshold})',showinfo",
            "-f",
            "null",
            "-",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    return [float(match.group(1)) for match in PTS_TIME.finditer(result.stderr)]


def boundaries(cuts: list[float], duration: float, minimum: float) -> list[float]:
    accepted = [0.0]
    for cut in cuts:
        if cut - accepted[-1] >= minimum and duration - cut >= minimum:
            accepted.append(cut)
    accepted.append(duration)
    return accepted


def write_detection(path: Path, points: list[float]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["clip_index", "start_seconds", "end_seconds", "duration_seconds"])
        for index, (start, end) in enumerate(zip(points, points[1:]), start=1):
            writer.writerow(
                [
                    f"{index:04d}",
                    f"{start:.3f}",
                    f"{end:.3f}",
                    f"{end - start:.3f}",
                ]
            )


def main() -> int:
    args = parse_args()
    if not 0 < args.threshold < 1:
        raise SystemExit("--threshold must be between 0 and 1.")
    if args.min_duration < 0:
        raise SystemExit("--min-duration cannot be negative.")

    require_tool("ffmpeg")
    require_tool("ffprobe")
    if not args.manifest.is_file():
        raise SystemExit(f"Manifest not found: {args.manifest}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with args.manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    for row in rows:
        source = Path(row["source_path"])
        output = args.output_dir / f"{row['id']}.scenes.tsv"
        if output.exists() and not args.force:
            print(f"Skipping existing detection: {output}")
            continue
        if not source.is_file():
            print(f"Skipping missing source: {source}", file=sys.stderr)
            continue

        print(f"Detecting scenes: {row['source_name']}")
        try:
            duration = video_duration(source)
            cuts = detect_cuts(source, args.threshold)
            points = boundaries(cuts, duration, args.min_duration)
            write_detection(output, points)
        except subprocess.CalledProcessError as exc:
            print(f"  FAILED (skipping): {exc}", file=sys.stderr)
            continue
        print(f"  wrote {len(points) - 1} clip boundary(s) to {output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
