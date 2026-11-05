"""Unit tests for the evaluation metrics. Synthetic segments only."""

from __future__ import annotations

import json

from beatcut.evaluate import (
    evaluate,
    iou,
    is_hit,
    load_labels,
    load_selection,
    mean_iou,
    overlap_seconds,
    precision_at_k,
    recall,
)
from beatcut.types import Segment


def test_overlap_seconds_is_zero_when_disjoint():
    assert overlap_seconds(Segment(0, 5), Segment(6, 9)) == 0.0


def test_overlap_seconds_counts_the_shared_part():
    assert overlap_seconds(Segment(0, 10), Segment(4, 20)) == 6.0


def test_iou_of_identical_segments_is_one():
    assert iou(Segment(2, 8), Segment(2, 8)) == 1.0


def test_iou_penalises_a_drifting_clip():
    # 6s clip, 4s of it inside the highlight -> 4/8 = 0.5
    assert iou(Segment(0, 6), Segment(2, 8)) == 0.5


def test_is_hit_needs_half_the_clip_inside():
    highlight = [Segment(0, 10)]
    assert is_hit(Segment(2, 8), highlight)
    assert not is_hit(Segment(8, 14), highlight)  # only 2 of 6 seconds overlap


def test_precision_at_k_ranks_by_score():
    highlights = [Segment(0, 10)]
    picked = [
        Segment(100, 110, score=0.9),  # wrong, but highest score
        Segment(0, 10, score=0.5),     # right
        Segment(200, 210, score=0.1),
    ]

    assert precision_at_k(picked, highlights, k=1) == 0.0
    assert precision_at_k(picked, highlights, k=2) == 0.5
    assert precision_at_k(picked, highlights, k=3) == 1 / 3


def test_precision_at_k_counts_only_the_top_k():
    highlights = [Segment(0, 10)]
    picked = [Segment(0, 10, score=1.0), Segment(50, 60, score=0.5)]

    assert precision_at_k(picked, highlights, k=1) == 1.0
    assert precision_at_k(picked, highlights, k=2) == 0.5


def test_recall_counts_found_highlights():
    highlights = [Segment(0, 10), Segment(50, 60), Segment(100, 110)]
    picked = [Segment(0, 10), Segment(50, 60)]

    assert recall(picked, highlights) == 2 / 3


def test_recall_is_zero_without_highlights():
    assert recall([Segment(0, 1)], []) == 0.0


def test_mean_iou_averages_the_best_match_per_highlight():
    highlights = [Segment(0, 10), Segment(50, 60)]
    picked = [Segment(0, 10), Segment(50, 55)]

    # first pair IoU 1.0, second 5/10 = 0.5
    assert mean_iou(picked, highlights) == 0.75


def test_evaluate_reports_every_metric():
    metrics = evaluate([Segment(0, 10, score=0.9)], [Segment(0, 10)], k=5)

    assert metrics["precision_at_k"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["mean_iou"] == 1.0
    assert metrics["n_picked"] == 1


def test_load_selection_reads_a_run_manifest(tmp_path):
    manifest = {"analysis": {"segments": [{"start": 1.0, "end": 4.0, "score": 0.5}]}}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    picked = load_selection(path)

    assert len(picked) == 1
    assert picked[0].start == 1.0
    assert picked[0].end == 4.0


def test_load_labels_tolerates_a_byte_order_mark(tmp_path):
    body = json.dumps({"highlights": [{"start": 0.0, "end": 5.0}]}).encode("utf-8")
    path = tmp_path / "labels.json"
    path.write_bytes(b"\xef\xbb\xbf" + body)

    assert len(load_labels(path)) == 1
