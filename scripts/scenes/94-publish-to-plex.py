#!/usr/bin/env python3
"""Publish exported/organized Super Family episodes to a Plex-scannable
library layout under /mnt/media/video, with generated subtitles and
Kodi/Jellyfin-style NFO metadata (Plex reads NFO for local/personal media
too, and honors .plexmatch to skip online TheTVDB matching for a show
that will never have a real match).

Reads:
  - content/transcripts/scenes/season-plan.tsv (season/episode -> source
    video_id + time range within that source)
  - content/data/episode-metadata/season-{NN}.json (title/synopsis/approx_date)
  - /mnt/creative/projects/superfamily/episodes/season-{NN}/S{NN}E{YY} - *.mp4
    (the already-exported episode files -- this script does not re-export,
    just republishes what 60-/70-/80- already produced)
  - content/transcripts/raw/{video_id}*.srt (the source movie's full
    transcript) -- sliced and time-shifted per episode to make a real
    per-episode subtitle file, since 90-extract-episode-transcripts.py only
    produced plain text, not timed subtitles.

Writes, per episode, to /mnt/media/video/Super Family/Season {NN}/:
  Super Family - S{NN}E{YY} - {Title}.mp4  (copied, not moved -- the
    original export under projects/superfamily/episodes/ is left alone)
  Super Family - S{NN}E{YY} - {Title}.srt
  Super Family - S{NN}E{YY} - {Title}.nfo
Plus at the show root: tvshow.nfo, poster.jpg, .plexmatch.

Copies (not symlinks): /mnt/media is a separate CIFS share from
/mnt/creative on the NAS side, and a symlink written through this client's
mount of one share isn't guaranteed to resolve for whatever actually
serves the media share to Plex.

Usage:
    python3 94-publish-to-plex.py [--force]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from pathlib import Path
from xml.sax.saxutils import escape

REPO_ROOT = Path(__file__).resolve().parents[2]
SEASON_PLAN = REPO_ROOT / "content/transcripts/scenes/season-plan.tsv"
EPISODE_METADATA_DIR = REPO_ROOT / "content/data/episode-metadata"
RAW_TRANSCRIPTS_DIR = REPO_ROOT / "content/transcripts/raw"
SOURCE_EPISODES_DIR = Path("/mnt/creative/projects/superfamily/episodes")
TARGET_ROOT = Path("/mnt/media/video/Super Family")
LOGO_CANDIDATES = [
    REPO_ROOT / "content/site-archive/images/logo.png",
    REPO_ROOT / "content/site-archive/images/logo2.png",
]

SHOW_SUMMARY = (
    "A homemade action-figure stop-motion/live-action series created and "
    "shot by Adam Young starting in childhood, following an ensemble cast "
    "through the Powerteam tapes and the Super Family movies. Republished "
    "here from the original tapes/movies, split into episodes and "
    "organized into seasons programmatically from real scene-detection data."
)

SRT_TIME_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
)


def srt_time_to_seconds(h, m, s, ms) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def seconds_to_srt_time(t: float) -> str:
    if t < 0:
        t = 0.0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_srt(path: Path) -> list[tuple[float, float, str]]:
    """Return list of (start_seconds, end_seconds, text)."""
    entries = []
    text = path.read_text(encoding="utf-8", errors="ignore")
    blocks = re.split(r"\n\s*\n", text.strip())
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue
        m = None
        idx = 0
        for i, line in enumerate(lines[:2]):
            m = SRT_TIME_RE.search(line)
            if m:
                idx = i
                break
        if not m:
            continue
        start = srt_time_to_seconds(*m.group(1, 2, 3, 4))
        end = srt_time_to_seconds(*m.group(5, 6, 7, 8))
        body = "\n".join(lines[idx + 1:]).strip()
        if body:
            entries.append((start, end, body))
    return entries


def slice_srt(entries: list[tuple[float, float, str]], ep_start: float, ep_end: float) -> str:
    out_lines = []
    n = 0
    for start, end, text in entries:
        # keep any entry that overlaps the episode window at all
        if end <= ep_start or start >= ep_end:
            continue
        n += 1
        rel_start = max(start, ep_start) - ep_start
        rel_end = min(end, ep_end) - ep_start
        out_lines.append(str(n))
        out_lines.append(f"{seconds_to_srt_time(rel_start)} --> {seconds_to_srt_time(rel_end)}")
        out_lines.append(text)
        out_lines.append("")
    return "\n".join(out_lines)


def find_source_video(season: int, ep_num: str) -> Path | None:
    season_dir = SOURCE_EPISODES_DIR / f"season-{season:02d}"
    if not season_dir.is_dir():
        return None
    prefix = f"S{season:02d}E{ep_num}"
    for f in season_dir.glob(f"{prefix} - *.mp4"):
        if not f.name.endswith(".intro.mp4"):
            return f
    return None


def find_raw_srt(video_id: str) -> Path | None:
    matches = list(RAW_TRANSCRIPTS_DIR.glob(f"{video_id}*.srt"))
    return matches[0] if matches else None


def write_episode_nfo(path: Path, title: str, synopsis: str, season: int, ep_num: str, approx_date: str | None):
    premiered = ""
    if approx_date and re.match(r"^\d{4}-\d{2}-\d{2}$", approx_date):
        premiered = f"  <aired>{approx_date}</aired>\n"
    xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\" ?>\n"
        "<episodedetails>\n"
        f"  <title>{escape(title)}</title>\n"
        f"  <season>{season}</season>\n"
        f"  <episode>{int(ep_num)}</episode>\n"
        f"  <plot>{escape(synopsis)}</plot>\n"
        f"{premiered}"
        "</episodedetails>\n"
    )
    path.write_text(xml, encoding="utf-8")


def write_show_nfo(path: Path):
    xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\" ?>\n"
        "<tvshow>\n"
        "  <title>Super Family</title>\n"
        f"  <plot>{escape(SHOW_SUMMARY)}</plot>\n"
        "  <genre>Animation</genre>\n"
        "  <genre>Family</genre>\n"
        "  <studio>Adam Young</studio>\n"
        "</tvshow>\n"
    )
    path.write_text(xml, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true", help="Re-copy/regenerate even if the target already exists.")
    args = parser.parse_args()

    if not SEASON_PLAN.is_file():
        raise SystemExit(f"Missing {SEASON_PLAN}")

    metadata_by_code: dict[str, dict] = {}
    for f in sorted(EPISODE_METADATA_DIR.glob("season-*.json")):
        for ep in json.loads(f.read_text(encoding="utf-8")):
            metadata_by_code[ep["code"]] = ep

    with SEASON_PLAN.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))

    TARGET_ROOT.mkdir(parents=True, exist_ok=True)

    show_nfo = TARGET_ROOT / "tvshow.nfo"
    if not show_nfo.is_file() or args.force:
        write_show_nfo(show_nfo)
        print(f"wrote {show_nfo}")

    plexmatch = TARGET_ROOT / ".plexmatch"
    if not plexmatch.is_file():
        plexmatch.write_text("title: Super Family\n", encoding="utf-8")
        print(f"wrote {plexmatch}")

    poster = TARGET_ROOT / "poster.jpg"
    if not poster.is_file():
        for cand in LOGO_CANDIDATES:
            if cand.is_file():
                shutil.copy2(cand, poster)
                print(f"wrote {poster} (from {cand.name})")
                break

    published, skipped, missing_source, missing_srt = 0, 0, [], []
    srt_cache: dict[str, list] = {}

    for row in rows:
        season = int(row["season"])
        ep_num = row["season_episode_number"]
        code = f"S{season:02d}E{ep_num}"
        meta = metadata_by_code.get(code)
        title = meta["title"] if meta else code
        synopsis = meta.get("synopsis", "") if meta else ""
        approx_date = meta.get("approx_date") if meta else None

        source_video = find_source_video(season, ep_num)
        if not source_video:
            missing_source.append(code)
            continue

        season_dir = TARGET_ROOT / f"Season {season:02d}"
        season_dir.mkdir(parents=True, exist_ok=True)
        safe_title = title.replace("/", "-")
        base_name = f"Super Family - {code} - {safe_title}"
        target_video = season_dir / f"{base_name}.mp4"
        target_srt = season_dir / f"{base_name}.srt"
        target_nfo = season_dir / f"{base_name}.nfo"

        if target_video.is_file() and not args.force:
            skipped += 1
            continue

        shutil.copy2(source_video, target_video)
        write_episode_nfo(target_nfo, title, synopsis, season, ep_num, approx_date)

        video_id = row["video_id"]
        if video_id not in srt_cache:
            srt_path = find_raw_srt(video_id)
            srt_cache[video_id] = parse_srt(srt_path) if srt_path else None
        entries = srt_cache[video_id]
        if entries is None:
            missing_srt.append(code)
        else:
            ep_start = float(row["start_seconds"])
            ep_end = float(row["end_seconds"])
            target_srt.write_text(slice_srt(entries, ep_start, ep_end), encoding="utf-8")

        published += 1
        print(f"  published {code} - {title}")

    print(f"\nPublished {published}, already up to date {skipped}, "
          f"missing source video {len(missing_source)}, missing subtitle source {len(missing_srt)}")
    if missing_source:
        print(f"  no exported .mp4 found for: {', '.join(missing_source)}")
    if missing_srt:
        print(f"  no source transcript found for: {', '.join(missing_srt)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
