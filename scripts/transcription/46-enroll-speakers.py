#!/usr/bin/env python3
"""Build voiceprints (speaker embeddings) from manually curated reference clips.

Sketch / draft stage. You listen to some already-transcribed audio, find a
few seconds where you're sure who is talking, and record that as a row in a
small TSV (content/transcripts/speakers.tsv by default):

    name    source_audio                                  start   end
    Dawson  content/transcripts/audio/cleaned/sf4.speech.wav   142.0   146.5
    Dawson  content/transcripts/audio/cleaned/sf7.speech.wav   30.2    33.0
    Stacey  content/transcripts/audio/cleaned/sf1.speech.wav   410.0   414.0

Multiple rows per name are averaged into one voiceprint. More, cleaner clips
per person produce a more reliable voiceprint -- a couple of seconds each is
enough, but noisy VHS audio may need several.

A voiceprint is biometric-ish data (it uniquely characterizes someone's
voice). Keep content/transcripts/speakers/ out of git -- it's listed in
.gitignore for that reason -- even in a private family repo.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build per-speaker voiceprints from reference clips."
    )
    parser.add_argument("-m", "--speakers-manifest", default="content/transcripts/speakers.tsv")
    parser.add_argument("-o", "--output", default="content/transcripts/speakers/voiceprints.json")
    parser.add_argument("--model", default="pyannote/embedding")
    parser.add_argument(
        "--hf-token",
        default=None,
        help="Hugging Face access token with the pyannote gated-model terms accepted. "
        "Defaults to $HF_TOKEN / $HUGGINGFACE_TOKEN.",
    )
    parser.add_argument("--device", default="cuda")
    return parser.parse_args()


def main() -> int:
    import os

    args = parse_args()
    hf_token = args.hf_token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if not hf_token:
        print(
            "No Hugging Face token found (--hf-token / $HF_TOKEN). "
            "pyannote's pretrained models are gated and require one.",
            file=sys.stderr,
        )
        return 2

    try:
        import numpy as np
        import torch
        from pyannote.audio import Inference, Model
        from pyannote.core import Segment
    except ImportError:
        print(
            "Missing dependency: pyannote.audio / torch / numpy. "
            "pip install -r scripts/transcription/requirements-diarization.txt",
            file=sys.stderr,
        )
        return 127

    manifest = Path(args.speakers_manifest)
    if not manifest.exists():
        print(f"Speakers manifest not found: {manifest}", file=sys.stderr)
        return 2

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading {args.model} on device={args.device}", flush=True)
    model = Model.from_pretrained(args.model, use_auth_token=hf_token)
    inference = Inference(model, window="whole")
    inference.to(torch.device(args.device))

    clips_by_name: dict[str, list[np.ndarray]] = {}

    with manifest.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            name = row["name"].strip()
            audio_path = Path(row["source_audio"])
            start = float(row["start"])
            end = float(row["end"])

            if not audio_path.exists():
                print(f"Skipping missing reference audio: {audio_path}", file=sys.stderr)
                continue

            print(f"Embedding {name}: {audio_path} [{start:.1f}-{end:.1f}]", flush=True)
            embedding = inference.crop(str(audio_path), Segment(start, end))
            clips_by_name.setdefault(name, []).append(np.asarray(embedding))

    voiceprints = {}
    for name, embeddings in clips_by_name.items():
        stacked = np.stack(embeddings)
        mean = stacked.mean(axis=0)
        mean = mean / np.linalg.norm(mean)
        voiceprints[name] = {
            "embedding": mean.tolist(),
            "num_clips": len(embeddings),
        }

    output.write_text(json.dumps(voiceprints, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(voiceprints)} voiceprints to {output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
