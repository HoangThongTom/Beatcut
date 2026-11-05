"""From a score curve to a handful of non-overlapping candidate clips.

Two stages, both pure functions so they are trivial to test:

1. :func:`window_scores` slides a fixed-width window over the curve.
2. :func:`select_segments` greedily takes the highest-scoring windows while
   refusing to pick two clips that are too close together.
"""

from __future__ import annotations

import numpy as np

from .types import Segment


def window_scores(
    times: np.ndarray,
    scores: np.ndarray,
    window_s: float,
    stride_s: float,
) -> list[tuple[float, float, float]]:
    """Score every `window_s`-wide window, hopping `stride_s` at a time."""
    times = np.asarray(times, dtype=float)
    scores = np.asarray(scores, dtype=float)
    if times.size == 0 or scores.size == 0:
        return []

    first, last = float(times[0]), float(times[-1])
    if last - first < window_s:
        return []

    candidates: list[tuple[float, float, float]] = []
    start = first
    while start + window_s <= last + 1e-9:
        mask = (times >= start) & (times < start + window_s)
        value = float(scores[mask].mean()) if mask.any() else 0.0
        candidates.append((round(start, 3), round(start + window_s, 3), value))
        start += stride_s
    return candidates


def select_segments(
    candidates: list[tuple[float, float, float]],
    target_duration_s: float,
    min_gap_s: float = 1.0,
    max_segments: int = 10,
) -> list[Segment]:
    """Greedy top-k pick with a minimum gap, returned in chronological order."""
    chosen: list[Segment] = []
    total = 0.0

    for start, end, score in sorted(candidates, key=lambda c: c[2], reverse=True):
        if len(chosen) >= max_segments:
            break
        candidate = Segment(start=start, end=end, score=score)
        if any(candidate.overlaps(existing, gap=min_gap_s) for existing in chosen):
            continue
        chosen.append(candidate)
        total += candidate.duration
        if total >= target_duration_s:
            break

    chosen.sort(key=lambda segment: segment.start)
    return chosen
