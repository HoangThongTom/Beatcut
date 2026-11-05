"""Beat and downbeat estimation, plus snapping cut points onto the grid.

librosa gives us beat positions in seconds. Downbeats (the "1" of each bar) are
not provided, so we pick the bar phase whose onsets are strongest — a cheap
heuristic that is good enough for the 4/4 electronic music people usually cut
montages to. Swap in BeatNet or madmom later without touching the pipeline:
only `detect_beats` would change.
"""

from __future__ import annotations

import numpy as np

from .types import BeatGrid


def detect_beats(
    audio_path: str,
    sr: int = 22050,
    beats_per_bar: int = 4,
) -> BeatGrid:
    """Estimate tempo, beats and downbeats for a music file."""
    import librosa  # imported lazily: keeps unit tests fast and dependency-light

    y, sr = librosa.load(str(audio_path), sr=sr, mono=True)
    if y.size == 0:
        raise ValueError(f"no audio samples decoded from {audio_path}")

    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, trim=False)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset_times = librosa.frames_to_time(np.arange(onset_env.size), sr=sr)

    bpm = float(np.atleast_1d(tempo)[0]) if np.size(tempo) else 0.0
    downbeats = pick_downbeats(beat_times, onset_env, onset_times, beats_per_bar)

    return BeatGrid(
        tempo=bpm,
        beats=[round(float(t), 4) for t in beat_times],
        downbeats=[round(float(t), 4) for t in downbeats],
    )


def pick_downbeats(
    beat_times: np.ndarray,
    onset_env: np.ndarray,
    onset_times: np.ndarray,
    beats_per_bar: int = 4,
) -> np.ndarray:
    """Choose the bar phase (0..beats_per_bar-1) with the strongest mean onset."""
    beat_times = np.asarray(beat_times, dtype=float)
    if beat_times.size == 0:
        return np.empty(0)
    if beats_per_bar <= 1:
        return beat_times

    strength = np.interp(beat_times, onset_times, onset_env)
    best_phase, best_value = 0, -np.inf
    for phase in range(beats_per_bar):
        idx = np.arange(phase, beat_times.size, beats_per_bar)
        if idx.size == 0:
            continue
        value = float(strength[idx].mean())
        if value > best_value:
            best_phase, best_value = phase, value
    return beat_times[best_phase::beats_per_bar]


def snap(time_s: float, grid: list[float] | np.ndarray, tol_s: float) -> float:
    """Move `time_s` to the nearest grid point, but only if it is within `tol_s`."""
    arr = np.asarray(grid, dtype=float)
    if arr.size == 0:
        return time_s
    nearest = int(np.argmin(np.abs(arr - time_s)))
    return float(arr[nearest]) if abs(arr[nearest] - time_s) <= tol_s else time_s


def align_segment(
    start: float,
    end: float,
    grid: BeatGrid,
    snap_tol_s: float = 0.25,
    min_clip_s: float = 2.5,
    max_clip_s: float = 10.0,
) -> tuple[float, float]:
    """Snap a cut to the beat grid and clamp its length.

    Starts prefer downbeats (a cut on the "1" feels intentional); ends prefer
    any beat so the clip keeps its natural length.
    """
    downbeats = grid.downbeats if grid and grid.downbeats else []
    beats = grid.beats if grid else []

    snapped_start = snap(start, downbeats, snap_tol_s)
    if snapped_start == start:
        snapped_start = snap(start, beats, snap_tol_s)

    wanted = min(max(end - start, min_clip_s), max_clip_s)
    snapped_end = snap(snapped_start + wanted, beats, snap_tol_s)
    if snapped_end - snapped_start < min_clip_s:
        snapped_end = snapped_start + min_clip_s
    return snapped_start, snapped_end
