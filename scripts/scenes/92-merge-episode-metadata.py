#!/usr/bin/env python3
"""Merge season-plan.tsv, dates.tsv, and generated title/synopsis chunks
into one self-contained metadata record per episode.

The title/synopsis are written by hand (or by an LLM working through
content/transcripts/scenes/episode-transcripts/*.txt) into
content/data/episode-metadata/season-*.json as bare {code, title, synopsis}
objects -- this script folds in the rest of what's already known about each
episode (timing, source movie, approx date) so the final file doesn't
require cross-referencing season-plan.tsv separately. Overwrites the input
season-*.json files in place with the enriched records.

Existing title/synopsis text is matched back to plan rows by
(video_id, episode_index), not by "code" -- code depends on the season
grouping, which can change (see 70-assign-seasons.py's SEASON_BREAKS) even
though the underlying episode content doesn't. This lets previously
generated text survive a season renumbering without regenerating it.
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
        "--dates",
        type=Path,
        default=Path("content/transcripts/scenes/dates.tsv"),
    )
    parser.add_argument(
        "--metadata-dir",
        type=Path,
        default=Path("content/data/episode-metadata"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.plan.is_file():
        raise SystemExit(f"Season plan not found: {args.plan}")

    with args.plan.open(encoding="utf-8", newline="") as handle:
        plan_rows = list(csv.DictReader(handle, delimiter="\t"))

    approx_dates: dict[str, str] = {}
    if args.dates.is_file():
        with args.dates.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                if row.get("approx_date"):
                    approx_dates[row["video_id"]] = row["approx_date"]

    written_texts: dict[tuple[str, str], dict] = {}
    for path in sorted(args.metadata_dir.glob("season-*.json")):
        for entry in json.loads(path.read_text(encoding="utf-8")):
            # older files may predate video_id/episode_index enrichment and
            # only have {code, title, synopsis} -- skip those, they'll show
            # up as missing_text below rather than mismatching silently.
            if "video_id" in entry and "episode_index" in entry:
                written_texts[(entry["video_id"], entry["episode_index"])] = entry

    by_season: dict[int, list[dict]] = {}
    missing_text = 0
    for row in plan_rows:
        season = int(row["season"])
        code = f"S{season:02d}E{row['season_episode_number']}"
        text = written_texts.get((row["video_id"], row["episode_index"]))
        if text is None:
            missing_text += 1
            title, synopsis = "", ""
        else:
            title, synopsis = text["title"], text["synopsis"]

        by_season.setdefault(season, []).append(
            {
                "code": code,
                "season": season,
                "season_episode_number": row["season_episode_number"],
                "short_name": row["short_name"],
                "part": int(row["part"]),
                "video_id": row["video_id"],
                "episode_index": row["episode_index"],
                "start_seconds": float(row["start_seconds"]),
                "end_seconds": float(row["end_seconds"]),
                "duration_seconds": float(row["duration_seconds"]),
                "end_snapped": row["end_snapped"] == "True",
                "approx_date": approx_dates.get(row["video_id"], ""),
                "title": title,
                "synopsis": synopsis,
            }
        )

    for season, entries in by_season.items():
        entries.sort(key=lambda e: int(e["season_episode_number"]))
        output = args.metadata_dir / f"season-{season:02d}.json"
        output.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        print(f"{output}: {len(entries)} episode(s)")

    if missing_text:
        print(f"\n{missing_text} episode(s) have no title/synopsis yet (left blank).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
