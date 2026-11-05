"""Unit tests for clip selection. No ffmpeg, no models, no I/O."""

from __future__ import annotations

import numpy as np

from beatcut.select import select_segments, window_scores
from beatcut.types import Segment


def test_window_scores_respects_window_and_stride():
    times = np.arange(0.0, 10.0, 0.25)
    scores = np.linspace(0.0, 1.0, times.size)

    windows = window_scores(times, scores, window_s=2.0, stride_s=1.0)

    assert windows, "expected at least one window"
    for start, end, _ in windows:
        assert end - start == 2.0
    starts = [round(start, 3) for start, _, _ in windows]
    assert starts[:3] == [0.0, 1.0, 2.0]


def test_window_scores_returns_nothing_for_short_curve():
    times = np.arange(0.0, 1.0, 0.25)
    assert window_scores(times, np.ones_like(times), window_s=5.0, stride_s=1.0) == []


def test_select_segments_takes_the_best_windows_first():
    candidates = [
        (0.0, 6.0, 0.1),
        (10.0, 16.0, 0.9),
        (30.0, 36.0, 0.5),
    ]

    picked = select_segments(candidates, target_duration_s=30.0, max_segments=2)

    assert [round(s.start, 1) for s in picked] == [10.0, 30.0]


def test_select_segments_never_overlaps_and_keeps_the_gap():
    candidates = [(float(t), float(t) + 6.0, 1.0 - t / 100.0) for t in range(0, 60, 2)]

    picked = select_segments(candidates, target_duration_s=60.0, min_gap_s=1.0)

    for left, right in zip(picked, picked[1:], strict=False):
        assert left.end + 1.0 <= right.start


def test_select_segments_stops_at_target_duration():
    candidates = [(float(t), float(t) + 6.0, 1.0) for t in range(0, 600, 10)]

    picked = select_segments(candidates, target_duration_s=20.0, max_segments=10)

    assert sum(s.duration for s in picked) >= 20.0
    assert len(picked) == 4


def test_segment_overlap_helper():
    assert Segment(0.0, 5.0).overlaps(Segment(4.0, 9.0))
    assert not Segment(0.0, 5.0).overlaps(Segment(5.0, 9.0))
    assert Segment(0.0, 5.0).overlaps(Segment(4.0, 9.0), gap=1.0)
    assert Segment(0.0, 5.0).overlaps(Segment(5.5, 9.0), gap=1.0)
    assert not Segment(0.0, 5.0).overlaps(Segment(6.5, 9.0), gap=1.0)
