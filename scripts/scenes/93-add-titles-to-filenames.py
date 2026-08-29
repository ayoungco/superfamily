#!/usr/bin/env python3
"""Rename exported episode files to include their titles.

Reads content/data/episode-metadata/season-*.json (from
92-merge-episode-metadata.py) and renames each already-exported
episodes/season-{NN}/S{NN}E{NN}.mp4 (and its S{NN}E{NN}.intro.mp4 title
card, if present) to "S{NN}E{NN} - {title}.mp4" -- the "SxxEyy - Title"
form Plex/Jellyfin/Kodi already parse for episode matching, so this also
gets media servers to display real titles instead of bare codes.

A rename, not a copy or re-encode -- it doesn't touch pixel data. Safe to
re-run: matches the current file by code regardless of whether it's still
bare or already carries a (possibly stale, after a title was edited)
title suffix, and skips a code with no title yet rather than leaving it
unrenamed forever only if you never re-run this after writing metadata.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CODE_PREFIX_RE = re.compile(r"^(S\d{2}E\d{2})")
INTRO_SUFFIX = ".intro.mp4"
# Windows/macOS-unsafe filename characters, plus control chars.
UNSAFE_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def parse_filename(name: str) -> tuple[str, str] | None:
    """Return (code, intro_suffix) for a bare or already-titled episode
    filename, or None if it doesn't look like one. Matches by prefix/suffix
    rather than a single regex so a greedy middle section (the title, once
    present) can't swallow the ".intro" marker."""
    if name.endswith(INTRO_SUFFIX):
        stem, intro_suffix = name[: -len(INTRO_SUFFIX)], ".intro"
    elif name.endswith(".mp4"):
        stem, intro_suffix = name[: -len(".mp4")], ""
    else:
        return None
    match = CODE_PREFIX_RE.match(stem)
    return (match.group(1), intro_suffix) if match else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metadata-dir",
        type=Path,
        default=Path("content/data/episode-metadata"),
    )
    parser.add_argument(
        "-d",
        "--episodes-dir",
        type=Path,
        default=Path("/mnt/creative/projects/superfamily/episodes"),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned renames without touching any files.",
    )
    parser.add_argument(
        "--strip-titles",
        action="store_true",
        help="Reverse: rename '{code} - {title}.mp4' back to bare "
        "'{code}.mp4'. Needed before re-running 75-renumber-seasons.py or "
        "91-generate-title-cards.py, which both look for the bare name.",
    )
    return parser.parse_args()


def sanitize_title(title: str) -> str:
    # ":" reads as a separator, not noise -- keep it visible as " -" instead
    # of just dropping it (e.g. "Roll Call: The Powerteam Assembles").
    cleaned = title.replace(":", " -")
    cleaned = UNSAFE_CHARS.sub("", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def load_titles(metadata_dir: Path) -> dict[str, str]:
    titles: dict[str, str] = {}
    for path in sorted(metadata_dir.glob("season-*.json")):
        for entry in json.loads(path.read_text(encoding="utf-8")):
            if entry.get("title"):
                titles[entry["code"]] = entry["title"]
    return titles


def main() -> int:
    args = parse_args()

    titles: dict[str, str] = {}
    if not args.strip_titles:
        if not args.metadata_dir.is_dir():
            raise SystemExit(f"Metadata directory not found: {args.metadata_dir}")
        titles = load_titles(args.metadata_dir)

    renamed = 0
    unchanged = 0
    missing_title = 0
    for season_dir in sorted(args.episodes_dir.glob("season-*")):
        if not season_dir.is_dir():
            continue
        for existing in sorted(season_dir.glob("S??E??*.mp4")):
            parsed = parse_filename(existing.name)
            if parsed is None:
                print(f"Skipping unrecognized filename: {existing}", file=sys.stderr)
                continue
            code, intro_suffix = parsed

            if args.strip_titles:
                desired = season_dir / f"{code}{intro_suffix}.mp4"
            else:
                title = titles.get(code)
                if not title:
                    missing_title += 1
                    continue
                desired = season_dir / f"{code} - {sanitize_title(title)}{intro_suffix}.mp4"

            if existing == desired:
                unchanged += 1
                continue
            if desired.exists():
                print(f"Skipping, destination already exists: {desired}", file=sys.stderr)
                continue

            print(f"{existing.name}  ->  {desired.name}")
            if not args.dry_run:
                existing.rename(desired)
            renamed += 1

    verb = "Would rename" if args.dry_run else "Renamed"
    print(
        f"\n{verb} {renamed} file(s), {unchanged} already correct, "
        f"{missing_title} code(s) with no title yet."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
