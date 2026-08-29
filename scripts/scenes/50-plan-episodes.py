#!/usr/bin/env python3
"""Plan episode boundaries from real scene-detection cuts.

Two modes, selected with --mode:

`fixed` (default, unchanged): picks evenly-spaced ideal 10-20 minute episode
boundaries, then snaps each one to the nearest real detected cut within
--tolerance-minutes. A boundary with no real cut nearby is left at its ideal
timestamp and flagged as not snapped -- this forces a cut mid-shot whenever a
single continuous take runs longer than the tolerance window around an ideal
boundary. Output columns: video_id, episode_index, start_seconds,
end_seconds, duration_seconds, end_snapped.

`takes`: never forces a boundary. A detected clip at least --target-minutes
long is atomic (its own segment, however long) since there is no real cut
inside it to split on; runs of shorter clips are packed forward until they
reach --target-minutes, always closing on a real cut. Segments shorter than
--min-segment-minutes are absorbed into a neighbor rather than standing alone
as a sliver episode. Output columns: video_id, episode_index, start_seconds,
end_seconds, duration_seconds, segment_kind (`long-take` or `short-run`).

See docs/programmatic-episode-splitting.md for the `fixed` plan's rationale
and docs/take-based-episode-splitting.md for why `takes` exists and how its
segment-length distribution compares.
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
        default=None,
        help="Default: content/transcripts/scenes/episode-plan.tsv for "
        "--mode fixed, episode-plan-takes.tsv for --mode takes.",
    )
    parser.add_argument(
        "--mode",
        choices=["fixed", "takes"],
        default="fixed",
        help="fixed: evenly-spaced boundaries snapped to nearby cuts, "
        "forcing one if none is close enough (default). takes: never "
        "force a boundary -- long single takes stand alone, short clips "
        "get packed to target length.",
    )
    parser.add_argument(
        "--target-minutes",
        type=float,
        default=15.0,
        help="Target episode length in minutes (default: 15). In --mode "
        "takes this also sets the long-take threshold: a clip this long "
        "or longer is never split or packed with neighbors.",
    )
    parser.add_argument(
        "--tolerance-minutes",
        type=float,
        default=3.0,
        help="--mode fixed only: snap an ideal boundary to a real cut "
        "within this many minutes, otherwise force the cut at the ideal "
        "timestamp (default: 3).",
    )
    parser.add_argument(
        "--min-segment-minutes",
        type=float,
        default=1.0,
        help="--mode takes only: segments shorter than this are absorbed "
        "into a neighboring segment instead of standing alone (default: 1).",
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


def plan_video_takes(
    clips: list[dict], target_seconds: float, min_segment_seconds: float
) -> list[dict]:
    total_duration = float(clips[-1]["end_seconds"])
    long_threshold = target_seconds

    segments: list[list] = []  # [start, end, kind]
    seg_start = 0.0
    accumulated = 0.0
    for clip in clips:
        start = float(clip["start_seconds"])
        end = float(clip["end_seconds"])
        duration = end - start
        if duration >= long_threshold:
            if accumulated > 0:
                segments.append([seg_start, start, "short-run"])
            segments.append([start, end, "long-take"])
            seg_start = end
            accumulated = 0.0
        else:
            accumulated += duration
            if accumulated >= target_seconds:
                segments.append([seg_start, end, "short-run"])
                seg_start = end
                accumulated = 0.0
    if accumulated > 0:
        segments.append([seg_start, total_duration, "short-run"])

    # Absorb slivers into a neighbor rather than emitting a micro-episode:
    # extend the following segment backward, or (for a trailing sliver) the
    # previous segment forward.
    merged: list[list] = []
    for index, (start, end, kind) in enumerate(segments):
        if (end - start) < min_segment_seconds and len(segments) > 1:
            if index + 1 < len(segments):
                segments[index + 1][0] = start
            elif merged:
                merged[-1][1] = end
            continue
        merged.append([start, end, kind])

    episodes = []
    for index, (start, end, kind) in enumerate(merged, start=1):
        episodes.append(
            {
                "episode_index": f"{index:02d}",
                "start_seconds": f"{start:.3f}",
                "end_seconds": f"{end:.3f}",
                "duration_seconds": f"{end - start:.3f}",
                "segment_kind": kind,
            }
        )
    return episodes


def main() -> int:
    args = parse_args()
    if args.target_minutes <= 0:
        raise SystemExit("--target-minutes must be positive.")
    if args.tolerance_minutes < 0:
        raise SystemExit("--tolerance-minutes cannot be negative.")
    if args.min_segment_minutes < 0:
        raise SystemExit("--min-segment-minutes cannot be negative.")
    if not args.manifest.is_file():
        raise SystemExit(f"Manifest not found: {args.manifest}")

    output = args.output or Path(
        "content/transcripts/scenes/episode-plan.tsv"
        if args.mode == "fixed"
        else "content/transcripts/scenes/episode-plan-takes.tsv"
    )
    target_seconds = args.target_minutes * 60
    tolerance_seconds = args.tolerance_minutes * 60
    min_segment_seconds = args.min_segment_minutes * 60

    with args.manifest.open(encoding="utf-8", newline="") as handle:
        videos = list(csv.DictReader(handle, delimiter="\t"))

    rows = []
    forced_total = 0
    long_take_total = 0
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

        if args.mode == "fixed":
            episodes = plan_video(clips, target_seconds, tolerance_seconds)
            forced = sum(1 for e in episodes if e["end_snapped"] == "False")
            forced_total += forced
            print(
                f"{video['id']}: {len(episodes)} episode(s), "
                f"{forced} forced boundary(s)"
            )
        else:
            episodes = plan_video_takes(clips, target_seconds, min_segment_seconds)
            long_takes = sum(1 for e in episodes if e["segment_kind"] == "long-take")
            long_take_total += long_takes
            print(
                f"{video['id']}: {len(episodes)} segment(s), "
                f"{long_takes} long-take(s)"
            )
        for episode in episodes:
            rows.append({"video_id": video["id"], **episode})

    fieldnames = (
        [
            "video_id",
            "episode_index",
            "start_seconds",
            "end_seconds",
            "duration_seconds",
            "end_snapped",
        ]
        if args.mode == "fixed"
        else [
            "video_id",
            "episode_index",
            "start_seconds",
            "end_seconds",
            "duration_seconds",
            "segment_kind",
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} episode(s) across {len(videos)} video(s) to {output}")
    if args.mode == "fixed" and forced_total:
        print(
            f"{forced_total} boundary(s) had no real cut within "
            f"{args.tolerance_minutes} min and were forced -- review those before "
            "trusting the split."
        )
    elif args.mode == "takes":
        print(f"{long_take_total} segment(s) are standalone long takes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
