"""Score a BeatCut selection against human highlight labels.

Implements the metrics described in docs/eval-protocol.md. Deliberately kept
out of the pipeline: evaluation is a development task, not something a user
running a montage should pay for.
"""

from __future__ import annotations

import json
from pathlib import Path

from .types import Segment


def load_selection(path: str | Path) -> list[Segment]:
    """Read a selection from either `analyze --json` or a `run` manifest."""
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    items = payload.get("segments")
    if items is None:
        items = (payload.get("analysis") or {}).get("segments", [])
    return [
        Segment(float(item["start"]), float(item["end"]), float(item.get("score", 0.0)))
        for item in items
    ]


def load_labels(path: str | Path) -> list[Segment]:
    """Read a label file as described in docs/eval-protocol.md."""
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return [
        Segment(float(item["start"]), float(item["end"]))
        for item in payload.get("highlights", [])
    ]


def overlap_seconds(left: Segment, right: Segment) -> float:
    return max(0.0, min(left.end, right.end) - max(left.start, right.start))


def iou(left: Segment, right: Segment) -> float:
    intersection = overlap_seconds(left, right)
    union = left.duration + right.duration - intersection
    return intersection / union if union > 0 else 0.0


def is_hit(clip: Segment, highlights: list[Segment], threshold: float = 0.5) -> bool:
    """A clip counts when it is mostly covered by a labelled highlight."""
    if clip.duration <= 0:
        return False
    return any(overlap_seconds(clip, h) >= threshold * clip.duration for h in highlights)


def precision_at_k(
    picked: list[Segment],
    highlights: list[Segment],
    k: int,
    threshold: float = 0.5,
) -> float:
    """Of the k best-scoring clips, how many are usable? The headline number."""
    ranked = sorted(picked, key=lambda segment: segment.score, reverse=True)[:k]
    if not ranked:
        return 0.0
    return sum(is_hit(clip, highlights, threshold) for clip in ranked) / len(ranked)


def recall(
    picked: list[Segment],
    highlights: list[Segment],
    threshold: float = 0.5,
) -> float:
    """Of all labelled highlights, how many did the selector find at all?"""
    if not highlights:
        return 0.0
    found = sum(
        any(overlap_seconds(highlight, clip) >= threshold * highlight.duration for clip in picked)
        for highlight in highlights
    )
    return found / len(highlights)


def mean_iou(picked: list[Segment], highlights: list[Segment]) -> float:
    """How well the boundaries line up, averaged over the labelled highlights."""
    if not highlights:
        return 0.0
    if not picked:
        return 0.0
    return sum(max(iou(highlight, clip) for clip in picked) for highlight in highlights) / len(
        highlights
    )


def evaluate(
    picked: list[Segment],
    highlights: list[Segment],
    k: int = 5,
    threshold: float = 0.5,
) -> dict:
    return {
        "k": k,
        "n_picked": len(picked),
        "n_highlights": len(highlights),
        "precision_at_k": round(precision_at_k(picked, highlights, k, threshold), 3),
        "recall": round(recall(picked, highlights, threshold), 3),
        "mean_iou": round(mean_iou(picked, highlights), 3),
        "threshold": threshold,
    }


def format_report(metrics: dict) -> str:
    picked = metrics["n_picked"]
    labelled = metrics["n_highlights"]
    return (
        f"picked {picked} clips against {labelled} labelled highlights\n"
        f"  precision@{metrics['k']}  {metrics['precision_at_k']:.3f}\n"
        f"  recall          {metrics['recall']:.3f}\n"
        f"  mean IoU        {metrics['mean_iou']:.3f}"
    )
