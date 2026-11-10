"""Cache the expensive, config-independent half of an analysis.

Decoding a 60fps phone recording to build the motion curve is the slow part of
a run, and it depends only on the source file and the sampling settings. Every
selection parameter (window length, weights, target duration) changes what is
*chosen* from those curves, not the curves themselves, so re-running after a
config tweak should not decode the video again.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from .config import Config
from .types import BeatGrid


def fingerprint(path: str | Path, cfg: Config, kind: str = "video") -> str:
    """Identify a source plus the settings that make its curves different."""
    stat = Path(path).stat()
    raw = "|".join(
        [
            str(Path(path).resolve()),
            str(stat.st_size),
            str(stat.st_mtime_ns),
            kind,
            *([f"{cfg.sample_fps}", f"{cfg.frame_width}"] if kind == "video" else []),
            f"{cfg.audio_sr}",
            *([f"{cfg.beats_per_bar}"] if kind == "music" else []),
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def kill_key(base_key: str, crop: list[int] | None) -> str:
    """Kill detections depend on the crop box, not on the curve settings."""
    if not crop:
        return base_key
    return f"{base_key}-{'_'.join(str(int(v)) for v in crop)}"


def load_kills(cache_dir: str | Path, key: str) -> list[float] | None:
    """Kill timestamps are cached separately: the OCR pass is its own slow step."""
    path = Path(cache_dir) / f"{key}.kills.json"
    if not path.exists():
        return None
    try:
        return [float(value) for value in json.loads(path.read_text(encoding="utf-8"))]
    except (OSError, ValueError, TypeError):
        return None


def save_kills(cache_dir: str | Path, key: str, times: list[float]) -> None:
    path = Path(cache_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{key}.kills.json").write_text(
        json.dumps([round(float(t), 2) for t in times]), encoding="utf-8"
    )


def load(
    cache_dir: str | Path,
    key: str,
) -> tuple[dict[str, tuple[np.ndarray, np.ndarray]], BeatGrid | None] | None:
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
    if not curves and "tempo" not in data:
        data.close()
        return None

    grid = BeatGrid(
        tempo=float(data["tempo"]),
        beats=[float(v) for v in data["beats"]],
        downbeats=[float(v) for v in data["downbeats"]],
    ) if "tempo" in data else None
    data.close()
    return curves, grid


def save(
    cache_dir: str | Path,
    key: str,
    curves: dict[str, tuple[np.ndarray, np.ndarray]],
    grid: BeatGrid | None = None,
) -> None:
    path = Path(cache_dir)
    path.mkdir(parents=True, exist_ok=True)
    payload = {
        "tempo": np.asarray(grid.tempo, dtype=float),
        "beats": np.asarray(grid.beats, dtype=float),
        "downbeats": np.asarray(grid.downbeats, dtype=float),
    } if grid is not None else {}
    for name, (times, values) in curves.items():
        payload[f"{name}_times"] = np.asarray(times, dtype=float)
        payload[f"{name}_values"] = np.asarray(values, dtype=float)
    np.savez_compressed(path / f"{key}.npz", **payload)
