"""Round-trip tests for the analysis cache."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from beatcut.cache import fingerprint, load, save
from beatcut.config import Config
from beatcut.types import BeatGrid


def test_fingerprint_changes_with_file_size(tmp_path: Path):
    source = tmp_path / "video.mp4"
    source.write_bytes(b"0" * 10)
    cfg = Config()

    first = fingerprint(source, cfg)
    source.write_bytes(b"0" * 20)

    assert fingerprint(source, cfg) != first


def test_fingerprint_changes_with_sampling_settings(tmp_path: Path):
    source = tmp_path / "video.mp4"
    source.write_bytes(b"0" * 10)

    assert fingerprint(source, Config()) != fingerprint(source, Config(sample_fps=2.0))


def test_cache_round_trip(tmp_path: Path):
    times = np.array([0.0, 0.25, 0.5, 0.75])
    curves = {
        "motion": (times, np.array([0.1, 0.4, 0.2, 0.9])),
        "audio": (times, np.array([0.2, 0.2, 0.8, 0.1])),
    }
    grid = BeatGrid(tempo=128.0, beats=[0.0, 0.5, 1.0], downbeats=[0.0, 1.0])

    save(tmp_path, "abc", curves, grid)
    loaded = load(tmp_path, "abc")

    assert loaded is not None
    loaded_curves, loaded_grid = loaded
    assert np.allclose(loaded_curves["motion"][1], curves["motion"][1])
    assert np.allclose(loaded_curves["audio"][0], times)
    assert loaded_grid.tempo == 128.0
    assert loaded_grid.downbeats == [0.0, 1.0]


def test_missing_cache_returns_none(tmp_path: Path):
    assert load(tmp_path, "nope") is None
