---
title: BeatCut
emoji: 🎬
colorFrom: purple
colorTo: blue
sdk: gradio
app_file: app/ui.py
python_version: "3.11"
pinned: false
license: mit
---

# BeatCut

Turn a gameplay clip into a short montage that cuts on the beat of a song.

Upload a short clip and a music track, get a montage back. The whole pipeline runs
on CPU: no model, no GPU, no training.

Source, tests and the full pipeline: https://github.com/HoangThongTom/beatcut

## Limits on this Space

Processing is synchronous — the request is held open while ffmpeg renders — so
the demo is capped well below what the pipeline handles:

- video duration: 60 s (set by `BEATCUT_MAX_DURATION_S` under *Settings →
  Variables and secrets*, because the proxy in front of Spaces drops long
  requests)
- one job at a time

For anything longer, run it locally:

```powershell
beatcut run data\raw\match.mp4 data\raw\song.mp3 -o outputs\montage.mp4
```

## What it does

1. decodes the video at 4 fps and builds a motion-energy curve
2. builds an RMS loudness curve from the game audio
3. (locally) reads the kill counter in the HUD with OCR when a crop box is set
4. fuses the signals and slides a scoring window over them
5. picks the top non-overlapping windows
6. quantises each clip to a whole number of musical bars, so cuts land on the beat
7. cuts, concatenates, and mixes game audio under the music with a limiter
