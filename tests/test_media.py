"""Probe-side tests. They feed hand-written ffprobe payloads, so they run
without ffmpeg installed."""

from __future__ import annotations

from beatcut.media import _display_size


def test_plain_stream_keeps_coded_size():
    assert _display_size({"width": 1920, "height": 1080}) == (1920, 1080)


def test_side_data_rotation_swaps_dimensions():
    stream = {
        "width": 1920,
        "height": 1080,
        "side_data_list": [{"rotation": -90}],
    }
    assert _display_size(stream) == (1080, 1920)


def test_legacy_rotate_tag_swaps_dimensions():
    stream = {"width": 1920, "height": 1080, "tags": {"rotate": "90"}}
    assert _display_size(stream) == (1080, 1920)


def test_half_turn_does_not_swap():
    stream = {"width": 1920, "height": 1080, "tags": {"rotate": "180"}}
    assert _display_size(stream) == (1920, 1080)


def test_unparsable_rotation_is_ignored():
    stream = {"width": 1920, "height": 1080, "tags": {"rotate": "n/a"}}
    assert _display_size(stream) == (1920, 1080)
