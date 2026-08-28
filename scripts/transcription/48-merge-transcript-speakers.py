#!/usr/bin/env python3
"""Assign each Whisper transcript segment a diarization speaker label.

For every manifest video, reads content/transcripts/raw/{id}.json (Whisper
segments) and content/transcripts/diarization/{id}.{profile}.json
(diarization turns), and labels each transcript segment with whichever
diarization speaker overlaps it for the most total time. A transcript
segment with no diarization overlap at all is labeled "UNKNOWN".

If content/transcripts/diarization/{id}.{profile}.labeled.json exists (from
47-label-speakers.py), its cluster-to-name matches are used in place of the
raw SPEAKER_NN cluster IDs wherever a match cleared --threshold; unmatched
or unenrolled clusters keep their generic SPEAKER_NN id. Until that
enrollment/labeling step has been run, every speaker in the merged
transcript will be a generic id, not a real name -- see "8. Enroll and
Label Named Speakers" in this directory's README for how to get real names.

Writes content/transcripts/speaker-labeled/{id}.json (segments with a
"speaker" field added) and a plain-text {id}.txt with "SPEAKER_NN: text"
per line for quick reading/review.
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
        "-m",
        "--manifest",
        type=Path,
        default=Path("content/transcripts/manifest.tsv"),
    )
    parser.add_argument(
        "--transcripts-dir",
        type=Path,
        default=Path("content/transcripts/raw"),
    )
    parser.add_argument(
        "--diarization-dir",
        type=Path,
        default=Path("content/transcripts/diarization"),
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("content/transcripts/speaker-labeled"),
    )
    parser.add_argument("--profile", default="speech")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def best_speaker(seg_start: float, seg_end: float, turns: list[dict]) -> str:
    overlap_by_speaker: dict[str, float] = {}
    for turn in turns:
        overlap = min(seg_end, turn["end"]) - max(seg_start, turn["start"])
        if overlap > 0:
            overlap_by_speaker[turn["speaker"]] = (
                overlap_by_speaker.get(turn["speaker"], 0.0) + overlap
            )
    if not overlap_by_speaker:
        return "UNKNOWN"
    return max(overlap_by_speaker, key=overlap_by_speaker.get)


def main() -> int:
    args = parse_args()
    if not args.manifest.is_file():
        raise SystemExit(f"Manifest not found: {args.manifest}")

    with args.manifest.open(encoding="utf-8", newline="") as handle:
        videos = list(csv.DictReader(handle, delimiter="\t"))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    merged = 0
    skipped = 0
    for video in videos:
        video_id = video["id"]
        transcript_path = args.transcripts_dir / f"{video_id}.json"
        diarization_path = args.diarization_dir / f"{video_id}.{args.profile}.json"
        labeled_path = args.diarization_dir / f"{video_id}.{args.profile}.labeled.json"
        out_json = args.output_dir / f"{video_id}.json"
        out_txt = args.output_dir / f"{video_id}.txt"

        if not transcript_path.is_file():
            print(f"Skipping missing transcript: {transcript_path}", file=sys.stderr)
            continue
        if not diarization_path.is_file():
            print(f"Skipping missing diarization: {diarization_path}", file=sys.stderr)
            continue
        if out_json.exists() and not args.force:
            print(f"Skipping existing: {out_json}")
            skipped += 1
            continue

        transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
        diarization = json.loads(diarization_path.read_text(encoding="utf-8"))
        turns = diarization["segments"]

        name_by_cluster: dict[str, str] = {}
        if labeled_path.is_file():
            labeled = json.loads(labeled_path.read_text(encoding="utf-8"))
            for cluster, match in labeled.get("cluster_matches", {}).items():
                if match.get("name"):
                    name_by_cluster[cluster] = match["name"]

        segments = []
        for segment in transcript["segments"]:
            cluster = best_speaker(segment["start"], segment["end"], turns)
            speaker = name_by_cluster.get(cluster, cluster)
            segments.append({**segment, "speaker": speaker, "speaker_cluster": cluster})

        out_json.write_text(
            json.dumps(
                {
                    "source_audio": transcript.get("source_audio"),
                    "diarization_source": str(diarization_path),
                    "named": bool(name_by_cluster),
                    "segments": segments,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        out_txt.write_text(
            "\n".join(f"{s['speaker']}: {s['text'].strip()}" for s in segments) + "\n",
            encoding="utf-8",
        )
        print(f"Merged {video['source_name']}: {len(segments)} segment(s) -> {out_json}")
        merged += 1

    print(f"\nMerged {merged} video(s), skipped {skipped} existing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
