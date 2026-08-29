#!/usr/bin/env python3
"""Export planned episodes from source movies.

Reads content/transcripts/scenes/episode-plan.tsv (from
50-plan-episodes.py) and cuts each planned episode from its source movie on
the external share, using stream copy by default so an hours-long source
isn't re-encoded just to be chunked -- see "Splitting Without Re-encoding" in
docs/media-ingest-and-chunking.md. Stream copy starts on the nearest
keyframe, so an episode may begin a little before or after the planned
timestamp; use --mode encode for frame-accurate cuts instead.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
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
        "-p",
        "--plan",
        type=Path,
        default=Path("content/transcripts/scenes/episode-plan.tsv"),
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("/mnt/creative/projects/superfamily/episodes"),
    )
    parser.add_argument(
        "--mode",
        choices=("copy", "encode"),
        default="copy",
        help="Fast keyframe-aligned stream copy, or accurate H.264/AAC "
        "re-encode (default: copy).",
    )
    parser.add_argument("--crf", type=int, default=20)
    parser.add_argument("--preset", default="medium")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def probe_video_codec(source: Path) -> str:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "csv=p=0",
            str(source),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def export_command(
    source: Path,
    output: Path,
    start: str,
    duration: str,
    mode: str,
    crf: int,
    preset: str,
    source_codec: str,
) -> list[str]:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-nostdin",
        "-y",
        "-ss",
        start,
        "-i",
        str(source),
        "-t",
        duration,
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
    ]
    if mode == "copy":
        command.extend(["-c", "copy", "-avoid_negative_ts", "make_zero"])
        # ffmpeg stream-copies HEVC into MP4 tagged "hev1" by default, which
        # macOS QuickTime/AVFoundation refuses to open even though it's a
        # valid tag -- it only recognizes "hvc1" for HEVC-in-MP4.
        if source_codec == "hevc":
            command.extend(["-tag:v", "hvc1"])
    else:
        command.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                preset,
                "-crf",
                str(crf),
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
            ]
        )
    command.append(str(output))
    return command


def main() -> int:
    args = parse_args()
    if not 0 <= args.crf <= 51:
        raise SystemExit("--crf must be between 0 and 51.")
    if not args.manifest.is_file():
        raise SystemExit(f"Manifest not found: {args.manifest}")
    if not args.plan.is_file():
        raise SystemExit(f"Episode plan not found: {args.plan} (run 50-plan-episodes.py first)")

    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        raise SystemExit("ffmpeg is required.")

    with args.manifest.open(encoding="utf-8", newline="") as handle:
        sources = {row["id"]: row["source_path"] for row in csv.DictReader(handle, delimiter="\t")}

    with args.plan.open(encoding="utf-8", newline="") as handle:
        plan_rows = list(csv.DictReader(handle, delimiter="\t"))

    episodes_by_video: dict[str, list[dict]] = {}
    for row in plan_rows:
        episodes_by_video.setdefault(row["video_id"], []).append(row)

    exported = 0
    skipped = 0
    failed = 0
    for video_id, episodes in episodes_by_video.items():
        source_path = sources.get(video_id)
        if source_path is None:
            print(f"Skipping unknown video id: {video_id}", file=sys.stderr)
            continue
        source = Path(source_path)
        if not source.is_file():
            print(f"Skipping missing source: {source}", file=sys.stderr)
            continue

        video_dir = args.output_dir / video_id
        video_dir.mkdir(parents=True, exist_ok=True)
        # always write .mp4: some sources are .m4v, which makes ffmpeg pick
        # the strict "ipod" muxer and reject copy-mode streams whose codec
        # parameters don't fit its profile checks.
        source_codec = probe_video_codec(source)

        for episode in episodes:
            output = video_dir / f"{video_id}-episode-{episode['episode_index']}.mp4"
            if output.exists() and not args.force:
                print(f"Skipping existing episode: {output}")
                skipped += 1
                continue
            forced_note = "" if episode["end_snapped"] == "True" else " (forced boundary)"
            print(
                f"Exporting {output.name}: {episode['start_seconds']}s + "
                f"{episode['duration_seconds']}s{forced_note}"
            )
            try:
                subprocess.run(
                    export_command(
                        source,
                        output,
                        episode["start_seconds"],
                        episode["duration_seconds"],
                        args.mode,
                        args.crf,
                        args.preset,
                        source_codec,
                    ),
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as exc:
                output.unlink(missing_ok=True)
                print(f"  FAILED: {exc.stderr.strip()[-500:]}", file=sys.stderr)
                failed += 1
                continue
            exported += 1

    print(f"\nExported {exported} episode(s), skipped {skipped} existing, {failed} failed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
