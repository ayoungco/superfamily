#!/usr/bin/env python3
"""Diarize cleaned audio locally with pyannote.audio.

Sketch / draft stage: produces per-video speaker segments (who spoke when),
independent of the Whisper word transcript. It does not yet merge diarization
output with the transcription output in content/transcripts/raw -- that's a
separate follow-on step (assign each Whisper segment the diarization label
with the most time overlap, then let a human map SPEAKER_00 -> a real name
once per video).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diarize cleaned audio files locally with pyannote.audio."
    )
    parser.add_argument("-m", "--manifest", default="content/transcripts/manifest.tsv")
    parser.add_argument("-i", "--audio-dir", default="content/transcripts/audio/cleaned")
    parser.add_argument("-o", "--output-dir", default="content/transcripts/diarization")
    parser.add_argument("--profile", default="speech")
    parser.add_argument("--model", default="pyannote/speaker-diarization-3.1")
    parser.add_argument(
        "--hf-token",
        default=os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN"),
        help="Hugging Face access token with the pyannote gated-model terms accepted. "
        "Defaults to $HF_TOKEN / $HUGGINGFACE_TOKEN.",
    )
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--num-speakers", type=int, default=None)
    parser.add_argument("--min-speakers", type=int, default=None)
    parser.add_argument("--max-speakers", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def write_outputs(out_base: Path, annotation, source_audio: Path) -> set[str]:
    json_path = out_base.with_suffix(".json")
    rttm_path = out_base.with_suffix(".rttm")

    segments = [
        {"start": round(turn.start, 3), "end": round(turn.end, 3), "speaker": speaker}
        for turn, _, speaker in annotation.itertracks(yield_label=True)
    ]
    speakers = {segment["speaker"] for segment in segments}

    json_path.write_text(
        json.dumps(
            {
                "source_audio": str(source_audio),
                "num_speakers_detected": len(speakers),
                "segments": segments,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    with rttm_path.open("w", encoding="utf-8") as handle:
        annotation.write_rttm(handle)

    return speakers


def main() -> int:
    args = parse_args()

    if not args.hf_token:
        print(
            "No Hugging Face token found (--hf-token / $HF_TOKEN). "
            "pyannote's pretrained pipelines are gated and require one.",
            file=sys.stderr,
        )
        return 2

    try:
        import torch
        from pyannote.audio import Pipeline
    except ImportError:
        print(
            "Missing dependency: pyannote.audio (and torch). "
            "Install them in your local transcription environment.",
            file=sys.stderr,
        )
        return 127

    manifest = Path(args.manifest)
    audio_dir = Path(args.audio_dir)
    out_dir = Path(args.output_dir)

    if not manifest.exists():
        print(f"Manifest not found: {manifest}", file=sys.stderr)
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading {args.model} on device={args.device}", flush=True)
    pipeline = Pipeline.from_pretrained(args.model, use_auth_token=args.hf_token)
    pipeline.to(torch.device(args.device))

    diarize_kwargs = {}
    if args.num_speakers is not None:
        diarize_kwargs["num_speakers"] = args.num_speakers
    if args.min_speakers is not None:
        diarize_kwargs["min_speakers"] = args.min_speakers
    if args.max_speakers is not None:
        diarize_kwargs["max_speakers"] = args.max_speakers

    with manifest.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            video_id = row["id"]
            source_name = row["source_name"]
            audio_path = audio_dir / f"{video_id}.{args.profile}.wav"
            out_base = out_dir / f"{video_id}.{args.profile}"

            if not audio_path.exists():
                print(f"Skipping missing cleaned audio: {audio_path}", file=sys.stderr)
                continue

            if out_base.with_suffix(".json").exists() and not args.force:
                print(f"Skipping existing diarization: {out_base.with_suffix('.json')}")
                continue

            print(f"Diarizing locally: {source_name}", flush=True)
            annotation = pipeline(str(audio_path), **diarize_kwargs)
            speakers = write_outputs(out_base, annotation, audio_path)
            print(f"  wrote {out_base}.json/.rttm ({len(speakers)} speakers detected)", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
