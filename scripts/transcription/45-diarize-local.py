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
        import torchaudio

        # torch 2.6+ defaults torch.load(weights_only=True), which rejects
        # several pyannote-internal classes pickled into its checkpoints
        # (TorchVersion, Specifications, ...). Allowlisting them one at a time
        # is whack-a-mole, so default weights_only=False here instead -- these
        # checkpoints come from the official pyannote org on Hugging Face via
        # a gated download the user explicitly accepted terms for.
        _torch_load = torch.load

        def _torch_load_compat(*a, **kw):
            # force, not setdefault: lightning_fabric passes weights_only
            # explicitly (as True), so setdefault would never override it.
            kw["weights_only"] = False
            return _torch_load(*a, **kw)

        torch.load = _torch_load_compat

        if not hasattr(torchaudio, "list_audio_backends"):
            # torchaudio dropped this API; pyannote.audio's io.py still calls it
            # just to pick a default backend. We only ever load audio via
            # soundfile (installed as a dependency), so report that.
            torchaudio.list_audio_backends = lambda: ["soundfile"]

        # Newer torchaudio routes torchaudio.load() through torchcodec, which
        # needs a working native CUDA (nvrtc) install this host doesn't have.
        # pyannote.audio's io.py only needs (waveform, sample_rate) back, so
        # bypass torchcodec entirely and load via soundfile directly.
        import soundfile as _soundfile

        def _torchaudio_load_compat(filepath, backend=None, **kw):
            data, sample_rate = _soundfile.read(str(filepath), dtype="float32", always_2d=True)
            waveform = torch.from_numpy(data.T.copy())
            return waveform, sample_rate

        torchaudio.load = _torchaudio_load_compat

        if not hasattr(torchaudio, "info"):
            # Same removal as torchaudio.load above; pyannote's io.py only
            # reads .num_frames and .sample_rate off the result.
            def _torchaudio_info_compat(filepath, backend=None, **kw):
                sf_info = _soundfile.info(str(filepath))
                return torchaudio.AudioMetaData(
                    num_frames=sf_info.frames, sample_rate=sf_info.samplerate
                )

            torchaudio.info = _torchaudio_info_compat

        if not hasattr(torchaudio, "AudioMetaData"):
            # Also dropped; only referenced at import time by pyannote's
            # (unused, training-only) dataset-preprocessing code path.
            torchaudio.AudioMetaData = type(
                "AudioMetaData", (), {"__init__": lambda self, **kw: self.__dict__.update(kw)}
            )

        import huggingface_hub

        _hf_hub_download = huggingface_hub.hf_hub_download

        def _hf_hub_download_compat(*a, **kw):
            # newer huggingface_hub renamed use_auth_token -> token; pyannote.audio
            # still passes the old name throughout its own internals.
            if "use_auth_token" in kw:
                kw.setdefault("token", kw.pop("use_auth_token"))
            return _hf_hub_download(*a, **kw)

        huggingface_hub.hf_hub_download = _hf_hub_download_compat

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
