#!/usr/bin/env python3
"""Tag detected scenes with a person-visible signal (draft / experimental).

Sketch stage: samples a few frames per detected clip (from
10-detect-scenes.py's output) and runs a general-purpose object detector
(YOLO, COCO-pretrained) looking for the "person" class. This does not
distinguish a hand/arm manipulating a toy from a full live-action human
scene -- both trigger "person" -- so treat the output as a candidate list
for human review, not a final answer. See
docs/battle-scene-human-removal.md for why this exists.

Frame decoding goes through PyAV rather than shelling out to ffmpeg, so
this stage works regardless of which ffmpeg build (patent-restricted
ffmpeg-free vs. full ffmpeg) is on the host.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-m", "--manifest", type=Path, default=Path("content/transcripts/manifest.tsv"))
    parser.add_argument(
        "-d",
        "--detections-dir",
        type=Path,
        default=Path("content/transcripts/scenes/detections"),
        help="Output of 10-detect-scenes.py.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("content/transcripts/scenes/classifications"),
    )
    parser.add_argument(
        "--samples-per-clip",
        type=int,
        default=3,
        help="Frames sampled per clip, spread evenly across its duration (default: 3).",
    )
    parser.add_argument("--model", default="yolo11n.pt", help="Ultralytics model checkpoint.")
    parser.add_argument("--conf", type=float, default=0.25, help="Detection confidence threshold.")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def sample_timestamps(start: float, end: float, count: int) -> list[float]:
    if count <= 1:
        return [(start + end) / 2]
    span = end - start
    return [start + span * (i + 0.5) / count for i in range(count)]


def classify_clip(container_path: Path, av, model, timestamps: list[float], conf: float) -> dict:
    best_person_conf = 0.0
    best_person_area_fraction = 0.0
    frames_with_person = 0

    for ts in timestamps:
        container = av.open(str(container_path))
        try:
            stream = container.streams.video[0]
            container.seek(int(ts / stream.time_base), stream=stream)
            frame = next(container.decode(video=0), None)
            if frame is None:
                continue
            image = frame.to_ndarray(format="rgb24")
            frame_area = image.shape[0] * image.shape[1]
        finally:
            container.close()

        results = model.predict(image, verbose=False, conf=conf, device=model_device)
        result = results[0]
        found_person = False
        for cls, box_conf, xyxy in zip(result.boxes.cls, result.boxes.conf, result.boxes.xyxy):
            if result.names[int(cls)] != "person":
                continue
            found_person = True
            x1, y1, x2, y2 = (float(v) for v in xyxy)
            area_fraction = ((x2 - x1) * (y2 - y1)) / frame_area
            best_person_conf = max(best_person_conf, float(box_conf))
            best_person_area_fraction = max(best_person_area_fraction, area_fraction)
        if found_person:
            frames_with_person += 1

    return {
        "frames_sampled": len(timestamps),
        "frames_with_person": frames_with_person,
        "max_person_confidence": round(best_person_conf, 3),
        "max_person_area_fraction": round(best_person_area_fraction, 4),
    }


def main() -> int:
    args = parse_args()
    if args.samples_per_clip < 1:
        raise SystemExit("--samples-per-clip must be at least 1.")

    try:
        import av
        from ultralytics import YOLO
    except ImportError:
        print(
            "Missing dependency: av / ultralytics. "
            "pip install -r scripts/scenes/requirements-classification.txt",
            file=sys.stderr,
        )
        return 127

    global model_device
    model_device = args.device

    if not args.manifest.is_file():
        raise SystemExit(f"Manifest not found: {args.manifest}")
    if not args.detections_dir.is_dir():
        raise SystemExit(f"Detections dir not found: {args.detections_dir} (run 10-detect-scenes.py first)")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with args.manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    print(f"Loading {args.model} on device={args.device}", flush=True)
    model = YOLO(args.model)
    model.to(args.device)

    for row in rows:
        video_id = row["id"]
        detection_path = args.detections_dir / f"{video_id}.scenes.tsv"
        output_path = args.output_dir / f"{video_id}.classifications.json"
        source = Path(row["source_path"])

        if not detection_path.is_file():
            print(f"Skipping missing detections: {detection_path}", file=sys.stderr)
            continue
        if output_path.exists() and not args.force:
            print(f"Skipping existing classification: {output_path}")
            continue
        if not source.is_file():
            print(f"Skipping missing source: {source}", file=sys.stderr)
            continue

        with detection_path.open(encoding="utf-8", newline="") as handle:
            clips = list(csv.DictReader(handle, delimiter="\t"))

        print(f"Classifying {len(clips)} clip(s): {row['source_name']}", flush=True)
        results = []
        for clip in clips:
            start = float(clip["start_seconds"])
            end = float(clip["end_seconds"])
            timestamps = sample_timestamps(start, end, args.samples_per_clip)
            tags = classify_clip(source, av, model, timestamps, args.conf)
            results.append({"clip_index": clip["clip_index"], "start_seconds": start, "end_seconds": end, **tags})

        output_path.write_text(
            json.dumps({"source_video": str(source), "clips": results}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        person_clips = sum(1 for r in results if r["frames_with_person"] > 0)
        print(f"  wrote {output_path} ({person_clips}/{len(results)} clips flagged with a person)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
