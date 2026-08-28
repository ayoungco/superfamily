#!/usr/bin/env python3
"""Move exported episode files into season folders with SxxEyy names.

Reads content/transcripts/scenes/season-plan.tsv (from
70-assign-seasons.py) and, for each row, moves the file
60-export-episodes.py already wrote at
{episodes-dir}/{video_id}/{video_id}-episode-{episode_index}.mp4 to
{episodes-dir}/season-{season:02d}/S{season:02d}E{season_episode_number}.mp4.
This is a rename, not a copy or re-encode -- it doesn't touch pixel data and
doesn't need a second copy of the footage on disk.
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
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
        "-d",
        "--episodes-dir",
        type=Path,
        default=Path("/mnt/creative/projects/superfamily/episodes"),
        help="Directory 60-export-episodes.py wrote per-video episode files into.",
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.plan.is_file():
        raise SystemExit(f"Season plan not found: {args.plan} (run 70-assign-seasons.py first)")

    with args.plan.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    moved = 0
    skipped = 0
    missing = 0
    for row in rows:
        season = int(row["season"])
        source = (
            args.episodes_dir
            / row["video_id"]
            / f"{row['video_id']}-episode-{row['episode_index']}.mp4"
        )
        if not source.is_file():
            print(f"Skipping missing export: {source}", file=sys.stderr)
            missing += 1
            continue

        season_dir = args.episodes_dir / f"season-{season:02d}"
        season_dir.mkdir(parents=True, exist_ok=True)
        dest = season_dir / f"S{season:02d}E{row['season_episode_number']}.mp4"
        if dest.exists() and not args.force:
            print(f"Skipping existing: {dest}")
            skipped += 1
            continue

        shutil.move(str(source), str(dest))
        moved += 1

    print(f"\nMoved {moved} episode(s), skipped {skipped} existing, {missing} not yet exported.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
