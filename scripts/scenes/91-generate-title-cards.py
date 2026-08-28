#!/usr/bin/env python3
"""Generate a faux-VHS title card clip for every planned episode.

Reads content/transcripts/scenes/season-plan.tsv (from
70-assign-seasons.py) and, for each episode, renders a short standalone
intro clip -- static/grain, scanlines, chromatic-shifted text, a corner
REC/date OSD, and a running timecode -- matching that episode's own
resolution and frame rate so it can be dropped in front of it later (in an
editor, or a media-server "trailer" slot). It does NOT modify the already
exported episode files; see scripts/scenes/60-export-episodes.py.

Episode titles come from content/data/episode-metadata/season-*.json if
present (falls back to just the short name/part when metadata for that
episode is missing). Corner date OSD comes from
content/transcripts/scenes/dates.tsv when the source movie has an approx
date.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

FONT_DIR = Path("/usr/share/fonts/liberation-sans-fonts")
MONO_DIR = Path("/usr/share/fonts/liberation-mono-fonts")
FONT_TITLE = FONT_DIR / "LiberationSans-Bold.ttf"
FONT_MONO = MONO_DIR / "LiberationMono-Bold.ttf"
FONT_MONO_ITALIC = MONO_DIR / "LiberationMono-BoldItalic.ttf"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-p",
        "--plan",
        type=Path,
        default=Path("content/transcripts/scenes/season-plan.tsv"),
    )
    parser.add_argument(
        "--metadata-dir",
        type=Path,
        default=Path("content/data/episode-metadata"),
    )
    parser.add_argument(
        "--dates",
        type=Path,
        default=Path("content/transcripts/scenes/dates.tsv"),
    )
    parser.add_argument(
        "-d",
        "--episodes-dir",
        type=Path,
        default=Path("/mnt/creative/projects/superfamily/episodes"),
    )
    parser.add_argument("--card-duration", type=float, default=4.5)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def load_metadata(metadata_dir: Path) -> dict[str, dict]:
    metadata = {}
    for path in sorted(metadata_dir.glob("season-*.json")):
        for entry in json.loads(path.read_text(encoding="utf-8")):
            metadata[entry["code"]] = entry
    return metadata


def probe_video(path: Path) -> tuple[int, int, str]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate",
            "-of",
            "csv=p=0",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    width, height, rate = result.stdout.strip().split(",")
    return int(width), int(height), rate


def build_command(
    output: Path,
    width: int,
    height: int,
    rate: str,
    duration: float,
    text_paths: dict[str, Path],
) -> list[str]:
    t = text_paths
    filter_complex = f"""
[0:v]
geq=lum='lum(X,Y)+(128*random(1)-64)*0.30':cb='cb(X,Y)':cr='cr(X,Y)',
geq=lum='if(mod(floor(Y),3),lum(X,Y),lum(X,Y)*0.55)':cb='cb(X,Y)':cr='cr(X,Y)',
eq=contrast=1.2:brightness=0.02:saturation=0.55:gamma=0.9,
rgbashift=rh=-4:bh=4,
vignette=PI/4.2,
drawbox=x=20:y=22:w=16:h=16:color=red@1.0:t=fill:enable='lt(mod(t\\,1),0.6)',
drawtext=fontfile={FONT_MONO}:textfile={t['rec']}:fontcolor=red:fontsize=20:x=44:y=20,
drawtext=fontfile={FONT_MONO}:textfile={t['date']}:fontcolor=white@0.85:fontsize=18:x=20:y=46,
drawtext=fontfile={FONT_TITLE}:textfile={t['show']}:fontcolor=white:fontsize=h*0.11:x=(w-text_w)/2:y=h*0.30,
drawtext=fontfile={FONT_MONO}:textfile={t['season_ep']}:fontcolor=white:fontsize=h*0.055:x=(w-text_w)/2:y=h*0.30+h*0.15,
drawtext=fontfile={FONT_MONO_ITALIC}:textfile={t['title']}:fontcolor=yellow:fontsize=h*0.045:x=(w-text_w)/2:y=h*0.30+h*0.15+h*0.09:line_spacing=6,
drawtext=fontfile={FONT_MONO}:text='%{{pts\\:hms}}':fontcolor=white@0.85:fontsize=h*0.04:x=w-tw-20:y=h-h*0.09,
fade=t=in:st=0:d=0.3,fade=t=out:st={duration - 0.3}:d=0.3
[v]
""".replace("\n", "")

    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=black:s={width}x{height}:d={duration}:r={rate}",
        "-f",
        "lavfi",
        "-i",
        f"anoisesrc=color=pink:amplitude=0.05:duration={duration}",
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
        "-map",
        "1:a",
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(output),
    ]


def main() -> int:
    args = parse_args()
    if not args.plan.is_file():
        raise SystemExit(f"Season plan not found: {args.plan}")

    for font in (FONT_TITLE, FONT_MONO, FONT_MONO_ITALIC):
        if not font.is_file():
            raise SystemExit(f"Font not found: {font}")

    with args.plan.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    metadata = load_metadata(args.metadata_dir) if args.metadata_dir.is_dir() else {}

    approx_dates: dict[str, str] = {}
    if args.dates.is_file():
        with args.dates.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                if row.get("approx_date"):
                    approx_dates[row["video_id"]] = row["approx_date"]

    generated = 0
    skipped = 0
    failed = 0
    missing = 0
    with tempfile.TemporaryDirectory(prefix="vhs-title-cards-") as tmp:
        tmp_dir = Path(tmp)
        for row in rows:
            season = int(row["season"])
            code = f"S{season:02d}E{row['season_episode_number']}"
            episode_file = args.episodes_dir / f"season-{season:02d}" / f"{code}.mp4"
            if not episode_file.is_file():
                print(f"Skipping missing episode: {episode_file}", file=sys.stderr)
                missing += 1
                continue

            output = episode_file.with_suffix("").with_suffix(".intro.mp4")
            if output.exists() and not args.force:
                print(f"Skipping existing card: {output}")
                skipped += 1
                continue

            entry = metadata.get(code)
            title = entry["title"] if entry else f"{row['short_name']} Part {row['part']}"
            show_name = "THE POWERTEAM" if season == 0 else "THE SUPER FAMILY"
            season_ep = f"SEASON {season} . EPISODE {row['season_episode_number']}"
            date = approx_dates.get(row["video_id"], "")

            texts = {
                "rec": "REC",
                "date": date,
                "show": show_name,
                "season_ep": season_ep,
                "title": title,
            }
            text_paths = {}
            for key, value in texts.items():
                path = tmp_dir / f"{code}-{key}.txt"
                path.write_text(value, encoding="utf-8")
                text_paths[key] = path

            width, height, rate = probe_video(episode_file)
            command = build_command(output, width, height, rate, args.card_duration, text_paths)
            print(f"Generating {output.name}: {title!r}")
            try:
                subprocess.run(command, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as exc:
                output.unlink(missing_ok=True)
                print(f"  FAILED: {exc.stderr.strip()[-500:]}", file=sys.stderr)
                failed += 1
                continue
            generated += 1

    print(
        f"\nGenerated {generated} title card(s), skipped {skipped} existing, "
        f"{failed} failed, {missing} episode(s) not yet exported."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
