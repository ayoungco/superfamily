#!/usr/bin/env python3
"""Group planned episodes (from 50-plan-episodes.py) into seasons.

Season 1-3 follow content/data/super_family_episodes_v2.csv's existing
grouping (SF1-4, SF5-9, SF10-14) -- that CSV has no real timecodes, but its
Season column is still the intended story grouping, so it's reused here
rather than re-derived. Season 0 is a new prequel season for the Powerteam
tapes, which predate the Super Family movies by the user's account ("years
before"); Powerteam Tape 1/2/3 have no confirmed date (see
content/transcripts/scenes/dates.tsv), but tape numbering gives a reliable
recording order on its own.

Reads content/transcripts/scenes/episode-plan.tsv and the manifest, and
writes one row per planned episode with its season and a season-scoped,
continuously-numbered episode index -- so e.g. SF6 Part 2's episodes pick up
numbering right after SF6 Part 1's, instead of restarting per source file.
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

# (movie_order, short_name) for each SF number -- season is derived from
# movie_order via SEASON_BREAKS below, matching super_family_episodes_v2.csv.
SEASON_BREAKS = [(4, 1), (9, 2), (14, 3)]  # (max sf_number, season)

POWERTEAM_TAPE = re.compile(r"^The Powerteam - Tape (\d+)", re.IGNORECASE)
POWERTEAM_GREEN = re.compile(r"^The Powerteam - The Green Tapes Part (\d+)", re.IGNORECASE)
SF_MOVIE = re.compile(r"^SF(\d+)\b")
PART = re.compile(r"Part (\d+)", re.IGNORECASE)


def sf_season(sf_number: int) -> int:
    for max_number, season in SEASON_BREAKS:
        if sf_number <= max_number:
            return season
    return SEASON_BREAKS[-1][1]


def classify(source_name: str) -> tuple[int, str, tuple, int]:
    """Return (season, short_name, sort_key, part) for a source filename."""
    match = POWERTEAM_TAPE.match(source_name)
    if match:
        tape = int(match.group(1))
        return 0, f"Powerteam Tape {tape}", (0, tape), 1

    match = POWERTEAM_GREEN.match(source_name)
    if match:
        part = int(match.group(1))
        return 0, "Powerteam Green Tapes", (1, part), part

    match = SF_MOVIE.match(source_name)
    if match:
        sf_number = int(match.group(1))
        part_match = PART.search(source_name)
        part = int(part_match.group(1)) if part_match else 1
        return sf_season(sf_number), f"SF{sf_number}", (sf_number, part), part

    raise ValueError(f"Unrecognized source name, add a pattern: {source_name!r}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-m",
        "--manifest",
        type=Path,
        default=Path("content/transcripts/manifest.tsv"),
    )
    parser.add_argument(
        "-p",
        "--plan",
        type=Path,
        default=Path("content/transcripts/scenes/episode-plan.tsv"),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("content/transcripts/scenes/season-plan.tsv"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.manifest.is_file():
        raise SystemExit(f"Manifest not found: {args.manifest}")
    if not args.plan.is_file():
        raise SystemExit(f"Episode plan not found: {args.plan} (run 50-plan-episodes.py first)")

    with args.manifest.open(encoding="utf-8", newline="") as handle:
        videos = {row["id"]: row for row in csv.DictReader(handle, delimiter="\t")}

    with args.plan.open(encoding="utf-8", newline="") as handle:
        plan_rows = list(csv.DictReader(handle, delimiter="\t"))

    episodes_by_video: dict[str, list[dict]] = {}
    for row in plan_rows:
        episodes_by_video.setdefault(row["video_id"], []).append(row)

    classified = []
    for video_id, episodes in episodes_by_video.items():
        video = videos.get(video_id)
        if video is None:
            print(f"Skipping unknown video id in plan: {video_id}")
            continue
        season, short_name, sort_key, part = classify(video["source_name"])
        episodes.sort(key=lambda e: int(e["episode_index"]))
        classified.append((season, sort_key, video_id, short_name, part, episodes))

    classified.sort(key=lambda c: (c[0], c[1]))

    rows = []
    season_counters: dict[int, int] = {}
    for season, _sort_key, video_id, short_name, part, episodes in classified:
        for episode in episodes:
            season_counters[season] = season_counters.get(season, 0) + 1
            rows.append(
                {
                    "season": season,
                    "season_episode_number": f"{season_counters[season]:02d}",
                    "short_name": short_name,
                    "part": part,
                    "video_id": video_id,
                    "episode_index": episode["episode_index"],
                    "start_seconds": episode["start_seconds"],
                    "end_seconds": episode["end_seconds"],
                    "duration_seconds": episode["duration_seconds"],
                    "end_snapped": episode["end_snapped"],
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "season",
                "season_episode_number",
                "short_name",
                "part",
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

    for season in sorted(season_counters):
        label = "Powerteam (prequel)" if season == 0 else f"Season {season}"
        print(f"{label}: {season_counters[season]} episode(s)")
    print(f"\nWrote {len(rows)} episode(s) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
