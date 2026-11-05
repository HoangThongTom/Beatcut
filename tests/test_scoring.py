"""Unit tests for the scoring helpers."""

from __future__ import annotations

import numpy as np

from beatcut.scoring import fuse, normalize


def test_normalize_maps_to_unit_range():
    values = np.linspace(0.0, 100.0, 101)
    out = normalize(values)

    assert out.min() == 0.0
    assert out.max() == 1.0
    assert np.all(np.diff(out) >= 0)


def test_normalize_handles_a_flat_curve():
    assert np.allclose(normalize(np.full(10, 3.0)), 0.0)


def test_fuse_ignores_zero_weight_curves():
    times = np.linspace(0.0, 10.0, 50)
    motion = np.sin(times)
    audio = np.cos(times)

    both = fuse(times, {"motion": (times, motion), "audio": (times, audio)},
                {"motion": 1.0, "audio": 0.0})
    only_motion = fuse(times, {"motion": (times, motion)}, {"motion": 1.0})

    assert np.allclose(both, only_motion)


def test_fuse_stays_in_unit_range():
    times = np.linspace(0.0, 10.0, 50)
    out = fuse(
        times,
        {"motion": (times, np.random.default_rng(0).random(50)),
         "audio": (times, np.random.default_rng(1).random(50))},
        {"motion": 0.6, "audio": 0.4},
    )

    assert out.min() >= 0.0
    assert out.max() <= 1.0
