"""Read the in-game kill counter to find the moments worth clipping.

Mobile MOBAs draw a fixed K/D/A row at the top of the screen. The kill digit is
rendered in a constant font at a constant place, which makes it a far better
highlight signal than a killfeed banner: a kill *is* the number going up, so
there is nothing to interpret and no text to parse beyond a digit.

The OCR pass is deliberately narrow: one small crop, one digit, sampled a couple
of times per second. Broad OCR over the whole frame was slower and read icons
as letters ('X', 'D'), while a tight crop per counter is clean.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .media import FFMPEG

DIGITS = re.compile(r"\d+")


@dataclass
class KillEvent:
    time: float
    count: int

    def to_dict(self) -> dict:
        return {"time": round(self.time, 2), "count": self.count}


def parse_counter(texts: list[str]) -> int | None:
    """Pull the counter value out of whatever the OCR engine returned.

    The engine decorates its output ('4.', '10'), and junk tokens from the
    neighbouring icons come through too, so every digit run is collected and the
    longest one wins.
    """
    best: int | None = None
    best_len = 0
    for text in texts:
        for token in DIGITS.findall(text):
            if len(token) > best_len:
                best = int(token)
                best_len = len(token)
    return best


def smooth(
    samples: list[tuple[float, int | None]],
    window: int = 5,
) -> list[tuple[float, int | None]]:
    """Median-filter the reading sequence.

    The recogniser occasionally glues a bright background pixel onto the digit
    ('4' becomes '43'), and a single such reading is enough to poison the
    monotonic check that follows. A kill stays on screen, so the true value is
    the one repeated across neighbouring frames; the median recovers it and the
    odd artefact loses the vote.
    """
    if window <= 1 or not samples:
        return samples

    half = window // 2
    values = [value for _, value in samples]
    times = [time_s for time_s, _ in samples]

    smoothed: list[tuple[float, int | None]] = []
    for index in range(len(values)):
        chunk = [
            value
            for value in values[max(0, index - half): index + half + 1]
            if value is not None
        ]
        smoothed.append((times[index], int(np.median(chunk)) if chunk else None))
    return smoothed


def detect_events(
    samples: list[tuple[float, int | None]],
    max_jump: int = 5,
    rebase_after: int = 5,
) -> list[KillEvent]:
    """Turn a noisy counter reading sequence into kill timestamps.

    Readings can glitch (a digit misread, a frame where the HUD is covered), so
    a step is only accepted when it is an increase small enough to be real. The
    counter never goes down, so a decrease is always noise.

    An implausible jump is not adopted as the new baseline: treating a misread
    43 as truth once poisoned every later reading, because the real values then
    looked like they were going backwards. It is only re-baselined after the
    same value repeats `rebase_after` times, which distinguishes a persistent
    offset (the HUD moved) from a one-off spike.
    """
    events: list[KillEvent] = []
    last: int | None = None
    pending: int | None = None
    pending_count = 0

    for time_s, value in samples:
        if value is None:
            continue
        if last is None:
            last = value
            continue
        if value == last:
            pending, pending_count = None, 0
            continue
        if value < last:
            continue  # misread, the counter cannot go backwards
        if value - last > max_jump:
            if value == pending:
                pending_count += 1
            else:
                pending, pending_count = value, 1
            if pending_count >= rebase_after:
                last, pending, pending_count = value, None, 0
            continue
        # One event per kill; two kills inside a single sample is rare and
        # turning one sample into two events would be worse than missing one.
        events.append(KillEvent(time=time_s, count=value))
        last = value
        pending, pending_count = None, 0

    return events


def extract_kills(
    video: str | Path,
    box: tuple[int, int, int, int],
    sample_fps: float = 2.0,
    upscale: int = 3,
    dump_samples: str | Path | None = None,
) -> list[KillEvent]:
    """Stream the counter crop through ffmpeg and OCR it `sample_fps` times a second.

    `box` is (x, y, width, height) in *displayed* pixels, i.e. after the
    rotation ffmpeg applies to phone recordings. Keep it tight around the digit:
    a wider crop drags in the neighbouring icons and the recogniser starts
    inventing digits.

    Detection is disabled (`use_det=False`) because the digit's position is
    fixed. That skips the text-detection model entirely and took a frame from
    240ms to 11ms; detection is only needed when you do not know where the text
    is.
    """
    from rapidocr_onnxruntime import RapidOCR  # lazy: heavy optional dependency

    x, y, width, height = box
    out_w, out_h = width * upscale, height * upscale

    cmd = [
        FFMPEG, "-v", "error",
        "-i", str(video),
        "-vf", f"fps={sample_fps},crop={width}:{height}:{x}:{y},"
               f"scale={out_w}:{out_h}:flags=lanczos",
        "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    engine = RapidOCR()
    frame_bytes = out_w * out_h * 3
    samples: list[tuple[float, int | None]] = []
    index = 0

    try:
        assert proc.stdout is not None
        while True:
            buffer = proc.stdout.read(frame_bytes)
            if not buffer or len(buffer) < frame_bytes:
                break
            frame = np.frombuffer(buffer, dtype=np.uint8).reshape(out_h, out_w, 3)
            result, _ = engine(frame, use_det=False, use_cls=False)
            texts = [entry[0] for entry in (result or [])]
            samples.append((index / sample_fps, parse_counter(texts)))
            index += 1
    finally:
        if proc.stdout is not None:
            proc.stdout.close()
        if proc.poll() is None:
            proc.kill()
        proc.wait()

    if dump_samples is not None:
        path = Path(dump_samples)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                [{"t": round(time_s, 2), "v": value} for time_s, value in samples],
                indent=0,
            ),
            encoding="utf-8",
        )

    return detect_events(smooth(samples))
