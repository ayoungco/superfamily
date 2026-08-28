#!/usr/bin/env python3
"""Plan 10-20 minute episode boundaries from real scene-detection cuts.

Reads content/transcripts/scenes/detections/*.scenes.tsv (from
10-detect-scenes.py) and, for each video, picks evenly-spaced ideal episode
boundaries, then snaps each one to the nearest real detected cut within
--tolerance-minutes. A boundary with no real cut nearby is left at its ideal
timestamp and flagged as not snapped, so 60-export-episodes.py (and a human)
can tell which cuts are exact and which were forced.

See docs/programmatic-episode-splitting.md for the full plan this implements.

Output columns: video_id, episode_index, start_seconds, end_seconds,
duration_seconds, end_snapped.
"""
from __future__ import annotations

import argparse
import csv
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
        "--output",
        type=Path,
        default=Path("content/transcripts/scenes/episode-plan.tsv"),
    )
    parser.add_argument(
        "--target-minutes",
        type=float,
        default=15.0,
        help="Target episode length in minutes (default: 15).",
    )
    parser.add_argument(
        "--tolerance-minutes",
        type=float,
        default=3.0,
        help="Snap an ideal boundary to a real cut within this many minutes, "
        "otherwise force the cut at the ideal timestamp (default: 3).",
    )
    return parser.parse_args()


def plan_video(clips: list[dict], target_seconds: float, tolerance_seconds: float) -> list[dict]:
    total_duration = float(clips[-1]["end_seconds"])
    # every real cut point is a clip's start except the first, which is 0.0
    # and isn't a cut -- it's the start of the movie.
    real_cuts = sorted({float(c["start_seconds"]) for c in clips[1:]})

    num_episodes = max(1, round(total_duration / target_seconds))
    boundaries = [0.0]
    end_snapped = []
    for k in range(1, num_episodes):
        ideal = k * total_duration / num_episodes
        nearest = min(real_cuts, key=lambda c: abs(c - ideal)) if real_cuts else None
        if nearest is not None and abs(nearest - ideal) <= tolerance_seconds:
            boundaries.append(nearest)
            end_snapped.append(True)
        else:
            boundaries.append(ideal)
            end_snapped.append(False)
    boundaries.append(total_duration)
    end_snapped.append(True)  # the movie's real end is always exact

    episodes = []
    for index, (start, end, snapped) in enumerate(
        zip(boundaries, boundaries[1:], end_snapped), start=1
    ):
        episodes.append(
            {
                "episode_index": f"{index:02d}",
                "start_seconds": f"{start:.3f}",
                "end_seconds": f"{end:.3f}",
                "duration_seconds": f"{end - start:.3f}",
                "end_snapped": str(snapped),
            }
        )
    return episodes


def main() -> int:
    args = parse_args()
    if args.target_minutes <= 0:
        raise SystemExit("--target-minutes must be positive.")
    if args.tolerance_minutes < 0:
        raise SystemExit("--tolerance-minutes cannot be negative.")
    if not args.manifest.is_file():
        raise SystemExit(f"Manifest not found: {args.manifest}")

    target_seconds = args.target_minutes * 60
    tolerance_seconds = args.tolerance_minutes * 60

    with args.manifest.open(encoding="utf-8", newline="") as handle:
        videos = list(csv.DictReader(handle, delimiter="\t"))

    rows = []
    forced_total = 0
    for video in videos:
        detection = args.detections_dir / f"{video['id']}.scenes.tsv"
        if not detection.is_file():
            print(f"Skipping missing detection: {detection}")
            continue
        with detection.open(encoding="utf-8", newline="") as handle:
            clips = list(csv.DictReader(handle, delimiter="\t"))
        if not clips:
            print(f"Skipping empty detection: {detection}")
            continue

        episodes = plan_video(clips, target_seconds, tolerance_seconds)
        forced = sum(1 for e in episodes if e["end_snapped"] == "False")
        forced_total += forced
        print(
            f"{video['id']}: {len(episodes)} episode(s), "
            f"{forced} forced boundary(s)"
        )
        for episode in episodes:
            rows.append({"video_id": video["id"], **episode})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "video_id",
                "episode_index",
                "start_seconds",
                "end_seconds",
                "duration_seconds",
                "end_snapped",
            ],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} episode(s) across {len(videos)} video(s) to {args.output}")
    if forced_total:
        print(
            f"{forced_total} boundary(s) had no real cut within "
            f"{args.tolerance_minutes} min and were forced -- review those before "
            "trusting the split."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
