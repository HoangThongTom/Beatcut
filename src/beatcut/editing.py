"""Validation for user-edited highlight selections."""

from __future__ import annotations

import math
from collections.abc import Sequence

from .types import Segment


def validate_segments(segments: Sequence[Segment], duration: float) -> list[Segment]:
    if not segments:
        raise ValueError("Keep at least one highlight.")
    for index, segment in enumerate(segments, 1):
        if not all(math.isfinite(v) for v in (segment.start, segment.end)):
            raise ValueError(f"Clip {index}: enter valid start and end times.")
        if segment.start < 0 or segment.end > duration:
            raise ValueError(f"Clip {index}: times must stay between 0 and {duration:.2f}s.")
        if segment.end - segment.start < 0.1:
            raise ValueError(f"Clip {index}: end must be at least 0.1s after start.")
    return [Segment(s.start, s.end, s.score) for s in segments]


def rows_to_segments(rows: list[dict], duration: float) -> list[Segment]:
    kept = [row for row in rows if row.get("Keep", False)]
    try:
        if any(not math.isfinite(float(row["Order"])) for row in kept):
            raise ValueError
        kept.sort(key=lambda row: float(row["Order"]))
        segments = [Segment(float(row["Start (s)"]), float(row["End (s)"])) for row in kept]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Enter a number for order, start and end in each kept clip.") from exc
    return validate_segments(segments, duration)
