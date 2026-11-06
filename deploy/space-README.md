---
title: BeatCut
emoji: 🎬
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 8000
pinned: false
license: mit
---

# BeatCut

Turn a gameplay VOD into a short montage that cuts on the beat of a song.

This Space runs the FastAPI wrapper around the pipeline: upload a short clip and a
music track, get back a montage.

Source, tests and the full pipeline: https://github.com/HoangThongTom/beatcut

## Limits on this Space

Processing is synchronous — the request is held open while ffmpeg renders — so the
demo is capped well below what the pipeline can handle:

- upload: 256 MB per file
- video duration: 60 s (raised from the pipeline default of 180 s, because the
  proxy in front of Spaces drops long requests)
- one job at a time

Both caps are environment variables (`BEATCUT_MAX_UPLOAD_MB`,
`BEATCUT_MAX_DURATION_S`), set under *Settings → Variables and secrets*.

## What it does

1. decodes the video at 4 fps and builds a motion-energy curve
2. builds an RMS loudness curve from the game audio
3. reads the kill counter in the HUD with OCR, when a crop box is configured
4. fuses the three signals and slides a scoring window over them
5. picks the top non-overlapping windows
6. quantises each clip to a whole number of musical bars, so cuts land on the
   beat
7. cuts, concatenates, and mixes game audio under the music with a limiter

The model-free path means it works on any game without training.
