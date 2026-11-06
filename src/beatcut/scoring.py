"""Turn a video into a per-timestamp "how interesting is this" curve.

M1 ships two model-free signals on purpose:

* ``motion`` — mean absolute difference between consecutive downscaled frames.
  Cheap proxy for on-screen action (camera flicks, explosions, movement).
* ``audio`` — short-time RMS of the gameplay audio. Spikes correlate with
  gunfire, hit markers and shoutcasters.

M2 replaces/augments these with a learned detector (see ROADMAP.md). The
pipeline only cares about the (times, values) contract, so a new scorer is a
drop-in.
"""

from __future__ import annotations

import numpy as np

from .media import iter_frames_gray
from .types import VideoInfo


def motion_energy_curve(
    video: str,
    info: VideoInfo,
    sample_fps: float = 4.0,
    frame_width: int = 320,
) -> tuple[np.ndarray, np.ndarray]:
    """Per-frame motion energy sampled at `sample_fps`."""
    times: list[float] = []
    values: list[float] = []
    previous: np.ndarray | None = None

    for timestamp, frame in iter_frames_gray(video, info, sample_fps, frame_width):
        current = frame.astype(np.int16)
        if previous is not None:
            times.append(timestamp)
            values.append(float(np.abs(current - previous).mean()))
        previous = current

    return np.asarray(times, dtype=float), np.asarray(values, dtype=float)


def audio_energy_curve(
    wav_path: str,
    sr: int = 22050,
    hop_length: int = 512,
) -> tuple[np.ndarray, np.ndarray]:
    """Short-time RMS loudness of a wav file."""
    import librosa  # lazy: only needed when audio scoring is enabled

    y, sr = librosa.load(str(wav_path), sr=sr, mono=True)
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    times = librosa.frames_to_time(np.arange(rms.size), sr=sr, hop_length=hop_length)
    return np.asarray(times, dtype=float), np.asarray(rms, dtype=float)


def normalize(values: np.ndarray, low_pct: float = 5.0, high_pct: float = 95.0) -> np.ndarray:
    """Percentile-normalize to [0, 1] so one loud outlier cannot flatten a curve."""
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return arr
    low, high = np.percentile(arr, low_pct), np.percentile(arr, high_pct)
    if high - low < 1e-9:
        return np.zeros_like(arr)
    return np.clip((arr - low) / (high - low), 0.0, 1.0)


def fuse(
    reference_times: np.ndarray,
    curves: dict[str, tuple[np.ndarray, np.ndarray]],
    weights: dict[str, float],
) -> np.ndarray:
    """Interpolate every curve onto `reference_times` and blend them by weight."""
    reference_times = np.asarray(reference_times, dtype=float)
    total = np.zeros_like(reference_times)
    weight_sum = 0.0

    for name, (times, values) in curves.items():
        weight = float(weights.get(name, 0.0))
        if weight <= 0 or np.asarray(times).size == 0:
            continue
        total += weight * np.interp(reference_times, times, normalize(values))
        weight_sum += weight

    return total / weight_sum if weight_sum > 0 else total


def boost_curve(
    times: np.ndarray,
    scores: np.ndarray,
    event_times: list[float],
    window_s: float = 5.0,
    weight: float = 0.6,
) -> np.ndarray:
    """Add a bump to the score curve around each detected event.

    A kill is a strong signal but a very short one; the interesting footage
    starts a second or two before it. A Gaussian bump spreads the signal over
    the surrounding window so whole clips get lifted, not single samples.
    """
    times = np.asarray(times, dtype=float)
    boosted = np.asarray(scores, dtype=float).copy()
    if not event_times:
        return boosted

    sigma = max(0.5, window_s / 2.0)
    for event_time in event_times:
        boosted += weight * np.exp(-0.5 * ((times - event_time) / sigma) ** 2)
    return boosted
