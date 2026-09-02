#!/usr/bin/env python3
"""Enrich take-based segments with old-episode content context for review.

Reads content/transcripts/scenes/episode-plan-takes.tsv (from
`50-plan-episodes.py --mode takes`) and, for each new segment, projects the
existing per-episode titles/synopses in content/data/episode-metadata/ onto
it by time overlap -- those were written against the old fixed-length
boundaries, so this is a best-effort content preview, not authoritative for
the new boundaries (see docs/take-based-episode-splitting.md's "Migration
cost" section).

A lightweight keyword match over the overlapping synopsis/title text
suggests a `flag` for segments that read as off-content, an interstitial,
duplicate footage, or a dialogue-free stretch -- these are exactly the kind
of segments the archive has "a lot of that's just blank or other VHS
recordings" of. The `decision` column is left blank for a human to fill in
(e.g. keep / delete / maybe) while reviewing in a spreadsheet.

Output columns: video_id, episode_index, start_seconds, end_seconds,
duration_minutes, segment_kind, flag, decision, context.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
from pathlib import Path

OFF_CONTENT_KEYWORDS = [
    "unrelated video", "unrelated television", "bled into", "bled through",
    "bleed-through", "bleed through", "golf broadcast", "golf tournament",
    "tuned to the wrong channel", "tuned out", "tape cuts out",
    "please visit our website", "subscribe", "outro",
]
SILENT_KEYWORDS = [
    "mostly silent", "silent stretch", "silent skirmish", "silent battle",
    "wordless", "dialogue-free", "dialogue-light", "no narration",
    "no narrated dialogue", "no dialogue captured",
]
DUPLICATE_KEYWORDS = [
    "garbled repeat", "plays out again", "repeat of the hero introduction",
    "encore", "callback", "another round",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-s", "--segments", type=Path,
        default=Path("content/transcripts/scenes/episode-plan-takes.tsv"),
    )
    parser.add_argument(
        "-m", "--metadata-dir", type=Path,
        default=Path("content/data/episode-metadata"),
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        default=Path("content/transcripts/scenes/segment-review.tsv"),
    )
    parser.add_argument(
        "--context-episodes", type=int, default=3,
        help="Max number of overlapping old episodes to summarize per segment (default: 3).",
    )
    return parser.parse_args()


def suggest_flag(text: str) -> str:
    lowered = text.lower()
    if any(k in lowered for k in OFF_CONTENT_KEYWORDS):
        return "off_content"
    if any(k in lowered for k in DUPLICATE_KEYWORDS):
        return "duplicate"
    if any(k in lowered for k in SILENT_KEYWORDS):
        return "silent_battle"
    return ""


def main() -> int:
    args = parse_args()
    if not args.segments.is_file():
        raise SystemExit(
            f"Segments file not found: {args.segments} "
            "(run 50-plan-episodes.py --mode takes first)"
        )

    old_episodes_by_video: dict[str, list[dict]] = {}
    for path in sorted(glob.glob(str(args.metadata_dir / "season-*.json"))):
        for ep in json.loads(Path(path).read_text(encoding="utf-8")):
            old_episodes_by_video.setdefault(ep["video_id"], []).append(ep)

    with args.segments.open(encoding="utf-8", newline="") as handle:
        segments = list(csv.DictReader(handle, delimiter="\t"))

    rows = []
    for seg in segments:
        video_id = seg["video_id"]
        start = float(seg["start_seconds"])
        end = float(seg["end_seconds"])

        overlaps = []
        for ep in old_episodes_by_video.get(video_id, []):
            ep_start, ep_end = float(ep["start_seconds"]), float(ep["end_seconds"])
            overlap = min(end, ep_end) - max(start, ep_start)
            if overlap > 0:
                overlaps.append((overlap, ep))
        overlaps.sort(key=lambda pair: pair[0], reverse=True)

        combined_text = " ".join(
            f"{ep['title']} {ep['synopsis']}" for _, ep in overlaps
        )
        context_parts = []
        for overlap, ep in overlaps[: args.context_episodes]:
            pct = round(100 * overlap / (end - start))
            synopsis = ep["synopsis"].replace("\t", " ").replace("\n", " ")
            context_parts.append(
                f"{ep['code']} ({pct}% overlap) \"{ep['title']}\": {synopsis[:150]}"
            )

        rows.append(
            {
                "video_id": video_id,
                "episode_index": seg["episode_index"],
                "start_seconds": seg["start_seconds"],
                "end_seconds": seg["end_seconds"],
                "duration_minutes": f"{float(seg['duration_seconds']) / 60:.1f}",
                "segment_kind": seg["segment_kind"],
                "flag": suggest_flag(combined_text),
                "decision": "",
                "context": " | ".join(context_parts),
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "video_id", "episode_index", "start_seconds", "end_seconds",
                "duration_minutes", "segment_kind", "flag", "decision", "context",
            ],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)

    flagged = sum(1 for r in rows if r["flag"])
    print(f"Wrote {len(rows)} segment(s) to {args.output} ({flagged} pre-flagged for review)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
