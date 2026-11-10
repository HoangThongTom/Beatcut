"""Validation for user-edited highlight selections."""

from __future__ import annotations

import copy
import math
from collections.abc import Sequence

from .types import Segment


def validate_transition(seconds: float, segments: Sequence[Segment] | None = None) -> None:
    """A transition straddles a cut, with half its fade on each side."""
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 <= seconds <= 1:
        raise ValueError("Transition duration must be between 0 and 1 second.")
    if seconds and segments is not None and len(segments) > 1:
        if any(segment.duration + 1e-9 < seconds for segment in segments):
            raise ValueError("Shorten the transition or extend the clips: "
                             "transition duration cannot exceed the shortest kept clip.")


def apply_timeline(rows: list[dict], clips: list[dict], duration: float) -> list[dict]:
    """Validate the component payload before applying order and source trims."""
    try:
        result = reorder_rows(rows, [clip["id"] for clip in clips])
        for clip in clips:
            if any(type(clip[key]) not in (int, float) for key in ("start", "end")):
                raise ValueError("Timeline times must be numbers.")
            result[clip["id"]]["Start (s)"] = clip["start"]
            result[clip["id"]]["End (s)"] = clip["end"]
        rows_to_segments(result, duration)
    except (KeyError, TypeError) as exc:
        raise ValueError("Invalid timeline edits.") from exc
    return result


def reorder_rows(rows: list[dict], order: list[int]) -> list[dict]:
    """Apply a permutation of kept row IDs, retaining removed clips for undo."""
    expected = {index for index, row in enumerate(rows) if row["Keep"]}
    if (not isinstance(order, list) or any(type(index) is not int for index in order)
            or len(order) != len(expected) or set(order) != expected):
        raise ValueError("The timeline order must contain each kept clip exactly once.")
    result = copy.deepcopy(rows)
    for position, index in enumerate(order, 1):
        result[index]["Order"] = position
    return result


def validate_segments(segments: Sequence[Segment], duration: float) -> list[Segment]:
    if not segments:
        raise ValueError("Keep at least one highlight.")
    for index, segment in enumerate(segments, 1):
        if not all(math.isfinite(v) for v in (segment.start, segment.end)):
            raise ValueError(f"Clip {index}: enter valid start and end times.")
        if segment.start < 0 or segment.end > duration:
            raise ValueError(f"Clip {index}: times must stay between 0 and {duration:.2f}s.")
        if segment.end - segment.start < 0.1 - 1e-9:
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
