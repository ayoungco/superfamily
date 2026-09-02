#!/usr/bin/env python3
"""Split a take-based episode plan by human review decisions.

Reads content/transcripts/scenes/episode-plan-takes.tsv (from
`50-plan-episodes.py --mode takes`) and the `decision` column filled in by
hand in content/transcripts/scenes/segment-review.tsv (written by
`55-flag-segments-for-review.py`), then writes two filtered plans in the
same schema `70-assign-seasons.py`/`60-export-episodes.py` already expect
(video_id, episode_index, start_seconds, end_seconds, duration_seconds,
end_snapped -- end_snapped is always written as True, since take-based
segments never force a boundary by construction):

- episode-plan-takes-main.tsv: the mainline numbered sequence.
- episode-plan-takes-extras.tsv: routed to a separate bonus container
  instead of the mainline (real footage, just not Super Family content --
  see docs/take-based-episode-splitting.md's content_type recommendation).

A segment whose decision is `trim` is dropped from both -- it's cut
entirely, the same as a Premiere ripple-delete, saving both export time and
the runtime of whatever season it would have landed in.

Recognized decision values (case/whitespace-insensitive): blank or `keep`
(default -- mainline), `extras` (bonus container), `trim` (dropped
entirely). Anything else is treated as an error so a typo in the review
sheet doesn't silently keep footage that was meant to be cut.

Run 60-export-episodes.py against each output plan, then 70-assign-seasons.py
+ 80-organize-seasons.py against the main one as usual and with
--flat-season/--container extras against the extras one -- see
scripts/scenes/README.md.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

KEEP_VALUES = {"", "keep"}
EXTRAS_VALUES = {"extras"}
TRIM_VALUES = {"trim"}

PLAN_FIELDNAMES = (
    "video_id",
    "episode_index",
    "start_seconds",
    "end_seconds",
    "duration_seconds",
    "end_snapped",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-p",
        "--plan",
        type=Path,
        default=Path("content/transcripts/scenes/episode-plan-takes.tsv"),
    )
    parser.add_argument(
        "-r",
        "--review",
        type=Path,
        default=Path("content/transcripts/scenes/segment-review.tsv"),
    )
    parser.add_argument(
        "--main-output",
        type=Path,
        default=Path("content/transcripts/scenes/episode-plan-takes-main.tsv"),
    )
    parser.add_argument(
        "--extras-output",
        type=Path,
        default=Path("content/transcripts/scenes/episode-plan-takes-extras.tsv"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.plan.is_file():
        raise SystemExit(f"Plan not found: {args.plan} (run 50-plan-episodes.py --mode takes first)")
    if not args.review.is_file():
        raise SystemExit(f"Review sheet not found: {args.review} (run 55-flag-segments-for-review.py first)")

    with args.plan.open(encoding="utf-8", newline="") as handle:
        plan_rows = list(csv.DictReader(handle, delimiter="\t"))

    with args.review.open(encoding="utf-8", newline="") as handle:
        review_rows = list(csv.DictReader(handle, delimiter="\t"))
    decisions = {
        (row["video_id"], row["episode_index"]): row["decision"].strip().lower()
        for row in review_rows
    }

    main_rows, extras_rows = [], []
    trimmed = 0
    errors = []
    for row in plan_rows:
        key = (row["video_id"], row["episode_index"])
        if key not in decisions:
            errors.append(f"No review decision for {key[0]} episode {key[1]} -- re-run 55 first.")
            continue
        decision = decisions[key]
        out_row = {name: row[name] for name in PLAN_FIELDNAMES if name in row}
        out_row["end_snapped"] = "True"

        if decision in KEEP_VALUES:
            main_rows.append(out_row)
        elif decision in EXTRAS_VALUES:
            extras_rows.append(out_row)
        elif decision in TRIM_VALUES:
            trimmed += 1
        else:
            errors.append(
                f"Unrecognized decision {decision!r} for {key[0]} episode {key[1]} "
                f"(expected blank/keep, extras, or trim)."
            )

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        raise SystemExit(f"\n{len(errors)} problem(s) found; fix segment-review.tsv and re-run.")

    for output, rows in ((args.main_output, main_rows), (args.extras_output, extras_rows)):
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=PLAN_FIELDNAMES, delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)

    total = len(plan_rows)
    print(f"{total} segment(s) reviewed: {len(main_rows)} main, {len(extras_rows)} extras, {trimmed} trimmed.")
    print(f"Wrote {args.main_output} and {args.extras_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
