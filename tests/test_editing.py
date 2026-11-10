import pytest

from beatcut.editing import reorder_rows, rows_to_segments


def row(start, end, order=1, keep=True):
    return {"Keep": keep, "Order": order, "Start (s)": start, "End (s)": end}


def test_trim_reorder_and_remove():
    clips = rows_to_segments([row(10, 12, 2), row(3, 6, 1), row(20, 25, 3, False)], 40)
    assert [(s.start, s.end) for s in clips] == [(3, 6), (10, 12)]


@pytest.mark.parametrize("rows", [
    [], [row(0, 3, keep=False)], [row(-1, 2)], [row(3, 2)],
    [row(0, 41)], [row(float("nan"), 3)], [row(0, 3, float("inf"))],
    [row(None, 3)], [row(0, 0.05)],
])
def test_invalid_edits_are_rejected(rows):
    with pytest.raises(ValueError):
        rows_to_segments(rows, 40)


def test_timeline_order_preserves_removed_clips_and_does_not_mutate_input():
    rows = [row(1, 4), row(10, 13, 2, False), row(20, 25, 3)]
    edited = reorder_rows(rows, [2, 0])
    assert [s.start for s in rows_to_segments(edited, 40)] == [20, 1]
    assert edited[1] == rows[1]
    assert rows[0]["Order"] == 1


@pytest.mark.parametrize("order", [[0, 0], [0], [0, 1, 2], [False, 1], [0, "1"], None])
def test_invalid_timeline_permutations_rejected(order):
    with pytest.raises(ValueError):
        reorder_rows([row(1, 4), row(10, 13, 2)], order)
