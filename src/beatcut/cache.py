"""Cache the expensive, config-independent half of an analysis.

Decoding a 60fps phone recording to build the motion curve is the slow part of
a run, and it depends only on the source file and the sampling settings. Every
selection parameter (window length, weights, target duration) changes what is
*chosen* from those curves, not the curves themselves, so re-running after a
config tweak should not decode the video again.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from .config import Config
from .types import BeatGrid


def fingerprint(path: str | Path, cfg: Config) -> str:
    """Identify a source plus the settings that make its curves different."""
    stat = Path(path).stat()
    raw = "|".join(
        [
            str(Path(path).resolve()),
            str(stat.st_size),
            str(int(stat.st_mtime)),
            f"{cfg.sample_fps}",
            f"{cfg.frame_width}",
            f"{cfg.audio_sr}",
            f"{cfg.beats_per_bar}",
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def load(
    cache_dir: str | Path,
    key: str,
) -> tuple[dict[str, tuple[np.ndarray, np.ndarray]], BeatGrid] | None:
    path = Path(cache_dir) / f"{key}.npz"
    if not path.exists():
        return None
    try:
        data = np.load(path, allow_pickle=False)
    except (OSError, ValueError):
        return None

    curves: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    if "motion_times" in data:
        curves["motion"] = (data["motion_times"], data["motion_values"])
    if "audio_times" in data:
        curves["audio"] = (data["audio_times"], data["audio_values"])
    if "motion" not in curves:
        return None

    grid = BeatGrid(
        tempo=float(data["tempo"]),
        beats=[float(v) for v in data["beats"]],
        downbeats=[float(v) for v in data["downbeats"]],
    )
    return curves, grid


def save(
    cache_dir: str | Path,
    key: str,
    curves: dict[str, tuple[np.ndarray, np.ndarray]],
    grid: BeatGrid,
) -> None:
    path = Path(cache_dir)
    path.mkdir(parents=True, exist_ok=True)
    payload = {
        "tempo": np.asarray(grid.tempo, dtype=float),
        "beats": np.asarray(grid.beats, dtype=float),
        "downbeats": np.asarray(grid.downbeats, dtype=float),
    }
    for name, (times, values) in curves.items():
        payload[f"{name}_times"] = np.asarray(times, dtype=float)
        payload[f"{name}_values"] = np.asarray(values, dtype=float)
    np.savez_compressed(path / f"{key}.npz", **payload)
