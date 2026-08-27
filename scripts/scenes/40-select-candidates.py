#!/usr/bin/env python3
"""Select battle-scene candidate clips from classification output.

Reads content/transcripts/scenes/classifications/*.json (from
30-classify-scenes.py) and writes a TSV of clips whose largest detected
person box is small relative to the frame -- the low end of
max_person_area_fraction is where a hand/arm reaching into frame to
manipulate a toy is more likely than a full live-action human scene. This
is a ranked candidate list for human review, not a finished tagging.

Output columns match what 20-export-clips.py --candidates expects:
video_id, clip_index.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-c",
        "--classifications-dir",
        type=Path,
        default=Path("content/transcripts/scenes/classifications"),
    )
    parser.add_argument(
        "-m",
        "--manifest",
        type=Path,
        default=Path("content/transcripts/manifest.tsv"),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("content/transcripts/scenes/candidates.tsv"),
    )
    parser.add_argument(
        "--max-area-fraction",
        type=float,
        default=0.10,
        help="Only include clips whose max_person_area_fraction is below this.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.manifest.is_file():
        raise SystemExit(f"Manifest not found: {args.manifest}")
    with args.manifest.open(encoding="utf-8", newline="") as handle:
        source_by_name = {
            row["source_name"]: row["id"]
            for row in csv.DictReader(handle, delimiter="\t")
        }

    rows = []
    for path in sorted(args.classifications_dir.glob("*.classifications.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        source_name = Path(data["source_video"]).name
        video_id = source_by_name.get(source_name)
        if video_id is None:
            print(f"Skipping unmatched source video: {source_name}", file=sys.stderr)
            continue

        for clip in data["clips"]:
            if clip["frames_with_person"] == 0:
                continue
            if clip["max_person_area_fraction"] >= args.max_area_fraction:
                continue
            rows.append(
                {
                    "video_id": video_id,
                    "clip_index": clip["clip_index"],
                    "start_seconds": clip["start_seconds"],
                    "end_seconds": clip["end_seconds"],
                    "max_person_area_fraction": clip["max_person_area_fraction"],
                    "max_person_confidence": clip["max_person_confidence"],
                }
            )

    rows.sort(key=lambda r: r["max_person_area_fraction"])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [
            "video_id", "clip_index", "start_seconds", "end_seconds",
            "max_person_area_fraction", "max_person_confidence",
        ], delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} candidates (area fraction < {args.max_area_fraction}) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
