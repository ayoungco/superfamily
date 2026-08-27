#!/usr/bin/env python3
"""Match diarized speaker clusters against enrolled voiceprints.

Sketch / draft stage. Reads each video's anonymous diarization clusters
(SPEAKER_00, SPEAKER_01, ... from 45-diarize-local.py), computes one
embedding per cluster, and compares it against the named voiceprints from
46-enroll-speakers.py by cosine similarity. A cluster is labeled with the
best-matching name only if the similarity clears --threshold; otherwise it
stays anonymous so a human can review it instead of getting a confident
wrong guess.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Label diarization clusters with enrolled speaker names."
    )
    parser.add_argument("-m", "--manifest", default="content/transcripts/manifest.tsv")
    parser.add_argument("-i", "--audio-dir", default="content/transcripts/audio/cleaned")
    parser.add_argument("-d", "--diarization-dir", default="content/transcripts/diarization")
    parser.add_argument("--voiceprints", default="content/transcripts/speakers/voiceprints.json")
    parser.add_argument("--profile", default="speech")
    parser.add_argument("--model", default="pyannote/embedding")
    parser.add_argument(
        "--hf-token",
        default=None,
        help="Defaults to $HF_TOKEN / $HUGGINGFACE_TOKEN.",
    )
    parser.add_argument("--device", default="cuda")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.75,
        help="Minimum cosine similarity to accept a name match.",
    )
    parser.add_argument("--force", action="store_true")
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

        def _torchaudio_load_compat(filepath, frame_offset=0, num_frames=-1, backend=None, **kw):
            # pyannote's io.py crops windows via frame_offset/num_frames (e.g.
            # one call per embedding window) -- dropping these silently
            # returned the *whole* file every time, corrupting every crop.
            data, sample_rate = _soundfile.read(
                str(filepath),
                start=frame_offset,
                frames=num_frames,
                dtype="float32",
                always_2d=True,
            )
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

        from pyannote.audio import Inference, Model
        from pyannote.core import Segment
    except ImportError:
        print(
            "Missing dependency: pyannote.audio / torch / numpy. "
            "pip install -r scripts/transcription/requirements-diarization.txt",
            file=sys.stderr,
        )
        return 127

    voiceprints_path = Path(args.voiceprints)
    if not voiceprints_path.exists():
        print(f"Voiceprints not found: {voiceprints_path}. Run 46-enroll-speakers.py first.", file=sys.stderr)
        return 2
    voiceprints = json.loads(voiceprints_path.read_text(encoding="utf-8"))
    names = list(voiceprints.keys())
    name_vectors = np.stack([np.asarray(voiceprints[name]["embedding"]) for name in names])

    manifest = Path(args.manifest)
    if not manifest.exists():
        print(f"Manifest not found: {manifest}", file=sys.stderr)
        return 2

    print(f"Loading {args.model} on device={args.device}", flush=True)
    model = Model.from_pretrained(args.model, use_auth_token=hf_token)
    inference = Inference(model, window="whole")
    inference.to(torch.device(args.device))

    audio_dir = Path(args.audio_dir)
    diarization_dir = Path(args.diarization_dir)

    with manifest.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            video_id = row["id"]
            source_name = row["source_name"]
            audio_path = audio_dir / f"{video_id}.{args.profile}.wav"
            diarization_path = diarization_dir / f"{video_id}.{args.profile}.json"
            out_path = diarization_dir / f"{video_id}.{args.profile}.labeled.json"

            if not diarization_path.exists():
                print(f"Skipping missing diarization: {diarization_path}", file=sys.stderr)
                continue
            if not audio_path.exists():
                print(f"Skipping missing cleaned audio: {audio_path}", file=sys.stderr)
                continue
            if out_path.exists() and not args.force:
                print(f"Skipping existing labels: {out_path}")
                continue

            diarization = json.loads(diarization_path.read_text(encoding="utf-8"))
            segments = diarization["segments"]

            by_cluster: dict[str, list[dict]] = {}
            for segment in segments:
                by_cluster.setdefault(segment["speaker"], []).append(segment)

            print(f"Labeling: {source_name}", flush=True)
            cluster_matches = {}
            for cluster, cluster_segments in by_cluster.items():
                # Longest segment is usually the cleanest single sample of this
                # cluster; embedding a concatenation is a possible upgrade.
                longest = max(cluster_segments, key=lambda s: s["end"] - s["start"])
                embedding = np.asarray(
                    inference.crop(str(audio_path), Segment(longest["start"], longest["end"]))
                )
                embedding = embedding / np.linalg.norm(embedding)

                similarities = name_vectors @ embedding
                best_index = int(np.argmax(similarities))
                best_score = float(similarities[best_index])

                if best_score >= args.threshold:
                    cluster_matches[cluster] = {"name": names[best_index], "score": round(best_score, 3)}
                else:
                    cluster_matches[cluster] = {"name": None, "score": round(best_score, 3)}

                label = cluster_matches[cluster]["name"] or "unmatched"
                print(f"  {cluster} -> {label} ({best_score:.3f})", flush=True)

            for segment in segments:
                match = cluster_matches[segment["speaker"]]
                segment["speaker_name"] = match["name"]
                segment["speaker_match_score"] = match["score"]

            out_path.write_text(
                json.dumps(
                    {
                        "source_audio": diarization["source_audio"],
                        "threshold": args.threshold,
                        "cluster_matches": cluster_matches,
                        "segments": segments,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
