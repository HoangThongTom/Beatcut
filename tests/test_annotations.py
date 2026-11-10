import json

import pytest

from beatcut.annotations import agree_annotations, load_annotations, save_annotations
from beatcut.cli import main
from beatcut.evaluate import load_labels


def annotation(annotator="A", highlights=None, **changes):
    return {"format": "beatcut-annotations", "version": 1, "video": "match.mp4",
            "sha256": "a" * 64, "duration_s": 100, "annotator": annotator,
            "highlights": highlights if highlights is not None else [{"start": 10, "end": 14}],
            **changes}


def test_independent_labels_round_trip_including_empty_review():
    for highlights in ([], [{"start": 20, "end": 25}, {"start": 10, "end": 14}]):
        original = annotation(highlights=highlights)
        loaded = load_annotations(b"\xef\xbb\xbf" + save_annotations(original))
        assert loaded["annotator"] == "A"
        assert loaded["highlights"] == sorted(highlights, key=lambda item: item["start"])


@pytest.mark.parametrize("change", [
    {"format": "beatcut-project"}, {"version": True}, {"annotator": ""},
    {"annotator": "../A"}, {"video": "C:\\private\\game.mp4"}, {"sha256": "no"},
    {"duration_s": float("nan")}, {"duration_s": True},
    {"highlights": [{"start": -1, "end": 3}]},
    {"highlights": [{"start": 1, "end": 101}]},
    {"highlights": [{"start": 1, "end": float("inf")}]},
    {"highlights": [{"start": True, "end": 3}]},
    {"highlights": [{"start": 1, "end": 1}]},
    {"highlights": [{"start": 1, "end": 4}, {"start": 3, "end": 5}]},
    {"highlights": [{"start": 1, "end": 4, "score": 0.9}]},
])
def test_bad_annotations_rejected(change):
    with pytest.raises(ValueError):
        load_annotations(json.dumps(annotation(**change)).encode())


@pytest.mark.parametrize("raw", [b"null", b"[]", b"bad", b"x" * 1_000_001])
def test_bad_json_rejected(raw):
    with pytest.raises(ValueError):
        load_annotations(raw)


def test_agreement_uses_both_endpoints_and_averages_unique_pairs():
    left = annotation(highlights=[{"start": 10, "end": 14}, {"start": 40, "end": 45}])
    right = annotation("B", [{"start": 12, "end": 16}, {"start": 70, "end": 75}])
    agreed = agree_annotations(left, right)
    assert agreed["highlights"] == [{"start": 11, "end": 15}]
    assert agreed["annotators"] == ["A", "B"]
    assert agreed["agreement"] == {"tolerance_s": 2, "matched": 1,
                                   "excluded_a": 1, "excluded_b": 1}
    assert not agree_annotations(left, annotation("B", [{"start": 12.001, "end": 16}]))[
        "highlights"
    ]


def test_ambiguous_pairs_are_excluded_instead_of_reusing_one_label():
    left = annotation(highlights=[{"start": 10, "end": 11}, {"start": 12, "end": 13}])
    right = annotation("B", [{"start": 11, "end": 12}])
    assert agree_annotations(left, right)["highlights"] == []


@pytest.mark.parametrize("right", [annotation(), annotation("B", sha256="b" * 64),
                                   annotation("B", duration_s=99)])
def test_agreement_requires_two_annotators_and_the_same_source(right):
    with pytest.raises(ValueError):
        agree_annotations(annotation(), right)


def test_cli_agreement_is_score_compatible_and_never_overwrites_labels(tmp_path):
    left, right, out = [tmp_path / name for name in ("a.json", "b.json", "agreed.json")]
    left.write_bytes(save_annotations(annotation()))
    right.write_bytes(save_annotations(annotation("B")))
    assert main(["agree", str(left), str(right), "-o", str(out)]) == 0
    assert [(s.start, s.end) for s in load_labels(out)] == [(10, 14)]
    before = out.read_bytes()
    assert main(["agree", str(left), str(right), "-o", str(out)]) == 1
    assert out.read_bytes() == before
    original = left.read_bytes()
    assert main(["agree", str(left), str(right), "-o", str(left)]) == 1
    assert left.read_bytes() == original


def test_cli_reports_no_agreement_without_fabricating_scores(tmp_path, capsys):
    left, right, out = [tmp_path / name for name in ("a.json", "b.json", "agreed.json")]
    left.write_bytes(save_annotations(annotation()))
    right.write_bytes(save_annotations(annotation("B", [])))
    assert main(["agree", str(left), str(right), "-o", str(out)]) == 0
    assert json.loads(out.read_text())["highlights"] == []
    assert "not ready for scoring" in capsys.readouterr().out
