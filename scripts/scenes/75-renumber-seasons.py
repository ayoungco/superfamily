#!/usr/bin/env python3
"""Move already-exported/organized episode files after a season regrouping.

If you change SEASON_BREAKS in 70-assign-seasons.py and re-run it, the
season and season_episode_number for most episodes shift even though the
underlying episode content (same video_id + episode_index, same
start/end_seconds) doesn't change at all. This script moves each episode
file from its old season/code path to its new one, using a two-phase move
through a staging directory (keyed by video_id+episode_index, which is
unambiguous) so that old and new paths can safely collide -- e.g. season-02
exists in both the old and new numbering with different content.

Stale title cards (season/episode number is burned into the pixels) are
deleted rather than moved; regenerate them with 91-generate-title-cards.py
after this runs. Episode metadata JSON should be regenerated separately
with 92-merge-episode-metadata.py, which matches by video_id+episode_index
and so doesn't care about the code renumbering.

Run 70-assign-seasons.py to write the NEW content/transcripts/scenes/
season-plan.tsv *before* running this script, and keep a copy of the OLD
one (e.g. season-plan.OLD.tsv) to diff against.
"""
from __future__ import annotations

import argparse
import csv
import shutil
import tempfile
from pathlib import Path


def load_plan(path: Path) -> dict[tuple[str, str], dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    return {(row["video_id"], row["episode_index"]): row for row in rows}


def code_of(row: dict) -> tuple[int, str]:
    season = int(row["season"])
    return season, f"S{season:02d}E{row['season_episode_number']}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-plan", type=Path, required=True)
    parser.add_argument(
        "--new-plan",
        type=Path,
        default=Path("content/transcripts/scenes/season-plan.tsv"),
    )
    parser.add_argument(
        "-d",
        "--episodes-dir",
        type=Path,
        default=Path("/mnt/creative/projects/superfamily/episodes"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    old_plan = load_plan(args.old_plan)
    new_plan = load_plan(args.new_plan)

    if old_plan.keys() != new_plan.keys():
        only_old = old_plan.keys() - new_plan.keys()
        only_new = new_plan.keys() - old_plan.keys()
        raise SystemExit(
            f"Old and new plan cover different episodes -- only in old: "
            f"{only_old}, only in new: {only_new}"
        )

    moved = 0
    unchanged = 0
    intros_removed = 0
    with tempfile.TemporaryDirectory(prefix="season-renumber-", dir=args.episodes_dir) as staging:
        staging_dir = Path(staging)

        # phase 1: old path -> staging, keyed by (video_id, episode_index)
        staged: dict[tuple[str, str], Path] = {}
        for key, old_row in old_plan.items():
            old_season, old_code = code_of(old_row)
            old_path = args.episodes_dir / f"season-{old_season:02d}" / f"{old_code}.mp4"
            if not old_path.is_file():
                print(f"Skipping missing file: {old_path}")
                continue
            staged_path = staging_dir / f"{key[0]}__{key[1]}.mp4"
            shutil.move(str(old_path), str(staged_path))
            staged[key] = staged_path

            old_intro = args.episodes_dir / f"season-{old_season:02d}" / f"{old_code}.intro.mp4"
            if old_intro.is_file():
                old_intro.unlink()
                intros_removed += 1

        # phase 2: staging -> new path
        for key, new_row in new_plan.items():
            staged_path = staged.get(key)
            if staged_path is None:
                continue
            new_season, new_code = code_of(new_row)
            new_dir = args.episodes_dir / f"season-{new_season:02d}"
            new_dir.mkdir(parents=True, exist_ok=True)
            new_path = new_dir / f"{new_code}.mp4"
            shutil.move(str(staged_path), str(new_path))
            old_season, old_code = code_of(old_plan[key])
            if (old_season, old_code) == (new_season, new_code):
                unchanged += 1
            else:
                moved += 1

    # clean up any now-empty season directories left over from the old layout
    for child in sorted(args.episodes_dir.glob("season-*")):
        if child.is_dir() and not any(child.iterdir()):
            child.rmdir()
            print(f"Removed empty directory: {child}")

    print(
        f"\nRenumbered {moved} episode(s), {unchanged} unchanged, "
        f"removed {intros_removed} stale title card(s). "
        f"Run 91-generate-title-cards.py to regenerate them."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
