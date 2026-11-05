"""Unit tests for beat alignment. Pure numpy — no audio files needed."""

from __future__ import annotations

import numpy as np

from beatcut.beats import align_segment, pick_downbeats, snap
from beatcut.types import BeatGrid


def test_pick_downbeats_chooses_the_strongest_phase():
    beat_times = np.arange(0.0, 8.0, 0.5)
    onset_env = np.zeros_like(beat_times)
    onset_env[2::4] = 1.0

    downbeats = pick_downbeats(beat_times, onset_env, beat_times, beats_per_bar=4)

    assert np.allclose(downbeats, beat_times[2::4])


def test_pick_downbeats_handles_empty_input():
    empty = np.empty(0)
    assert pick_downbeats(empty, empty, empty).size == 0


def test_snap_only_moves_within_tolerance():
    assert snap(10.1, [10.0, 10.5], 0.25) == 10.0
    assert snap(10.5, [10.0], 0.25) == 10.5


def test_align_segment_prefers_downbeats_for_the_start():
    grid = BeatGrid(
        tempo=120.0,
        beats=[round(0.5 * i, 3) for i in range(20)],
        downbeats=[0.0, 2.0, 4.0, 6.0, 8.0],
    )

    start, end = align_segment(4.05, 7.0, grid, snap_tol_s=0.25)

    assert start == 4.0
    assert end == 7.0


def test_align_segment_enforces_minimum_length():
    grid = BeatGrid(tempo=120.0, beats=[0.0, 0.5, 1.0], downbeats=[0.0])

    start, end = align_segment(0.0, 0.4, grid, min_clip_s=2.5, max_clip_s=10.0)

    assert start == 0.0
    assert end - start >= 2.5


def test_align_segment_clamps_maximum_length():
    grid = BeatGrid(
        tempo=120.0,
        beats=[round(0.5 * i, 3) for i in range(60)],
        downbeats=[0.0],
    )

    start, end = align_segment(0.0, 25.0, grid, min_clip_s=2.5, max_clip_s=10.0)

    assert start == 0.0
    assert end - start <= 10.0
