ComfyUI is **not the right tool for audio transcription** by default.

Use **Whisper** instead.

### Simple local option

```bash
pip install -U openai-whisper
```

Transcribe:

```bash
whisper audio.mp3 --model medium --language English
```

Output files will appear beside the audio:

```text
audio.txt
audio.srt
audio.vtt
```

### Better/faster NVIDIA option

```bash
pip install -U faster-whisper
```

Example script:

```python
from faster_whisper import WhisperModel

model = WhisperModel("medium", device="cuda", compute_type="float16")

segments, info = model.transcribe("audio.mp3")

with open("transcript.txt", "w") as f:
    for segment in segments:
        f.write(segment.text.strip() + "\n")
```

### If you specifically want it in ComfyUI

Search/install a custom node for **Whisper / audio transcription**, but I’d keep transcription outside ComfyUI unless your workflow needs audio → prompt → image/video.

Best practical setup:

```text
audio/video file
→ ffmpeg extract audio
→ whisper/faster-whisper transcript
→ use transcript as prompt/context in ComfyUI
```

Extract audio from video:

```bash
ffmpeg -i input.mp4 -vn -acodec copy audio.m4a
```

Then:

```bash
whisper audio.m4a --model medium
```
