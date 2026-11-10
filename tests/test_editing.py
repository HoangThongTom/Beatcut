import pytest

from beatcut.editing import rows_to_segments


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
