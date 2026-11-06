# BeatCut

Turn an hour-long gameplay VOD into a short montage that cuts on the beat of a song.

`BeatCut` scores every second of a recording for "how much is happening here",
picks the strongest moments, and cuts them into a highlight reel aligned to the
downbeats of a music track. No manual scrubbing, no editing timeline.

> **Status: M1 (model-free vertical slice).** Scoring is currently motion +
> audio energy. A learned highlight detector (YOLO / OCR killfeed) lands in M2.
> See [ROADMAP.md](ROADMAP.md).

<!-- Replace with a real 20-30s before/after GIF once M1 is recorded. -->
<!-- ![demo](docs/assets/demo.gif) -->

## The problem

Editing a highlight montage by hand means watching hours of footage, remembering
timestamps, and then manually cutting clips to the beat. It is the most tedious
part of making gaming content, and it is exactly the kind of repetitive
video-understanding task a model can do.

## How it works

```
video ──► probe ──► motion energy ─┐
                                   ├─► fuse ──► window scoring ──► greedy select
       └─► audio ──► loudness ─────┘                                      │
                                                                          ▼
music ──► beats/downbeats ─────────────────────────────► snap cut points to grid
                                                                          │
                                                                          ▼
                          ffmpeg: cut ─► concat ─► mix game audio + music
```

| Stage | Module | What it does |
|---|---|---|
| Probe | `media.py` | duration, resolution, fps, audio presence via `ffprobe` |
| Frame stream | `media.py` | decodes downscaled gray frames through an ffmpeg pipe |
| Scoring | `scoring.py` | frame-difference motion energy + short-time RMS loudness |
| Beats | `beats.py` | tempo, beats, downbeats (librosa) + snapping helpers |
| Selection | `select.py` | window scores, greedy top-k with a minimum gap |
| Render | `render.py` | re-encoded cuts, concat demuxer, game audio mixed under the music |

More detail, including the design decisions and their trade-offs, is in
[docs/architecture.md](docs/architecture.md).

## Quickstart

```powershell
# 1. ffmpeg is a hard dependency and is not installed by pip
winget install Gyan.FFmpeg
```

Prefer a portable build with no system install? Drop `ffmpeg.exe` and
`ffprobe.exe` anywhere and point the pipeline at them:

```powershell
$env:FFMPEG_BIN = "C:\tools\ffmpeg\ffmpeg.exe"
$env:FFPROBE_BIN = "C:\tools\ffmpeg\ffprobe.exe"
```

```powershell
# 2. create .venv (Python 3.11) and install
.\scripts\bootstrap.ps1

# 3. check the machine can actually run this
.\.venv\Scripts\Activate.ps1
beatcut doctor

# 4. render a montage
beatcut run data\raw\match.mp4 data\raw\song.mp3 -o outputs\montage.mp4
```

Put your own recording in `data/raw/`. Nothing in `data/` is committed: a
one-hour 1080p60 capture is several GB, far above what Git should hold.

### Smoke test without footage

`scripts/make_fixtures.py` builds a synthetic 40-second clip and a 120 BPM click
track, so the install can be checked before recording anything:

```powershell
python scripts\make_fixtures.py
beatcut run scratch\gameplay.mp4 scratch\music.wav -o outputs\smoke.mp4 --target-duration 12
```

A 12-second mp4 with audio means the whole chain (probe, scoring, beats, cut,
concat, mux) works.

## CLI

```text
beatcut doctor                     # environment check
beatcut analyze VIDEO MUSIC        # print the chosen clips, render nothing
beatcut run VIDEO MUSIC -o OUT     # full pipeline
beatcut version
```

Useful flags: `-c configs/default.yaml`, `--target-duration 60`,
`--max-segments 8`, `--keep-work`.

`beatcut analyze` writes nothing except the temp audio; it prints the segment
table and can dump JSON with `--json out.json`. This is the command used by the
evaluation protocol.

## Configuration

Every knob lives in [configs/default.yaml](configs/default.yaml) and maps 1:1 to
a field of `beatcut.config.Config`. Unknown keys are rejected, so a typo cannot
silently fall back to a default.

The two that matter most:

- `window_s` / `target_duration_s` — clip length and total montage length.
- `motion_weight` / `audio_weight` — how much on-screen action versus loud audio
  drives the selection. A quiet stealth game wants more motion; a shooter with a
  loud caster wants more audio.

## Results

Fill this in with numbers from **your** runs — never invent them.

| Metric | Target | Measured |
|---|---|---|
| Highlight selection precision@5 (see [eval protocol](docs/eval-protocol.md)) | ≥ 0.70 | _TBD_ |
| Beat alignment error (mean, ms) | ≤ 50 | _TBD_ |
| End-to-end time, 60 min VOD → 45 s montage | < 10 min | _TBD_ |
| Peak memory | < 2 GB | _TBD_ |

## Project layout

```
src/beatcut/     pipeline library (importable, no CLI side effects)
app/api.py       minimal FastAPI wrapper (M3)
configs/         YAML run configs
scripts/         bootstrap.ps1
tests/           pure-function unit tests (no ffmpeg, no models)
docs/            architecture, evaluation protocol
data/            raw footage and labels — gitignored
outputs/         rendered montages — gitignored
```

## Evaluation

`tests/` covers the pure logic (selection, snapping, config). Measuring whether
the *chosen clips are any good* is a different problem, and it needs human
labels. [docs/eval-protocol.md](docs/eval-protocol.md) describes the labelling
procedure and the precision/recall/IoU metrics.

## Roadmap

M1 (this repo) is model-free by design: it produces a real montage today. M2–M4
add learning, deployment and polish. The full checklist is in
[ROADMAP.md](ROADMAP.md).

## Limitations

- Beat tracking assumes 4/4 music; downbeats are a phase heuristic, not a
  trained downbeat model.
- Cuts are hard cuts. Crossfades and beat-matched transitions are M4.
- Music longer than the montage is fine; shorter music is padded with silence.
- One video in, one montage out — no multi-VOD stitching yet.

## License

MIT
