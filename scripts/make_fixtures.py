"""Build synthetic fixtures so the pipeline can be smoke-tested without footage.

Creates a 120 BPM click track and a moving-pattern video under ``scratch/``.

    .\\.venv\\Scripts\\python.exe scripts\\make_fixtures.py
    beatcut run scratch\\gameplay.mp4 scratch\\music.wav -o outputs\\smoke.mp4 --target-duration 12
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "scratch"
SR = 22050
BPM = 120
DURATION_S = 40


def make_music(path: Path) -> None:
    samples = np.zeros(int(SR * DURATION_S), dtype=np.float64)
    beat_period = 60.0 / BPM

    for index in range(int(DURATION_S / beat_period)):
        start = int(index * beat_period * SR)
        length = min(int(0.09 * SR), samples.size - start)
        if length <= 0:
            continue
        envelope = np.exp(-np.linspace(0.0, 9.0, length))
        time = np.linspace(0.0, 0.09, length)
        samples[start:start + length] += 0.9 * np.sin(2 * np.pi * 70 * time) * envelope

        # Off-beat hi-hat, so onset detection has something to lock onto.
        hat_start = start + int(beat_period * 0.5 * SR)
        hat_len = min(int(0.03 * SR), samples.size - hat_start)
        if hat_len > 0:
            noise = np.random.default_rng(index).normal(0, 0.25, hat_len)
            samples[hat_start:hat_start + hat_len] += noise * np.exp(-np.linspace(0, 6, hat_len))

    peak = np.max(np.abs(samples)) or 1.0
    sf.write(path, (samples / peak * 0.9).astype(np.float32), SR)
    print(f"wrote {path}")


def make_video(path: Path) -> None:
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc2=size=1280x720:rate=30:duration={DURATION_S}",
        "-f", "lavfi", "-i", f"anoisesrc=d={DURATION_S}:color=pink:amplitude=0.2",
        "-shortest",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        str(path),
    ]
    subprocess.run(cmd, check=True)
    print(f"wrote {path}")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    make_music(OUT / "music.wav")
    make_video(OUT / "gameplay.mp4")
