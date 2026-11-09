"""Probe-side tests. They feed hand-written ffprobe payloads, so they run
without ffmpeg installed."""

from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

from beatcut.media import _display_size, audio_duration, find_gaps


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"format": {"duration": "193.5"}, "streams": [{}]}, 193.5),
        ({"streams": [{"duration": "40"}]}, 40.0),
    ],
)
def test_audio_duration_accepts_audio_only_files(monkeypatch, payload, expected):
    monkeypatch.setattr(
        "beatcut.media.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(stdout=json.dumps(payload)),
    )
    assert audio_duration("song.mp3") == expected


@pytest.mark.parametrize(
    "payload",
    [{"format": {"duration": "40"}, "streams": []},
     {"streams": [{}]}, {"streams": [{"duration": "nan"}]}],
)
def test_audio_duration_rejects_unusable_music(monkeypatch, payload):
    monkeypatch.setattr(
        "beatcut.media.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(stdout=json.dumps(payload)),
    )
    with pytest.raises(ValueError):
        audio_duration("bad.mp3")


def test_find_gaps_ignores_uniform_frame_spacing():
    assert find_gaps(np.arange(0.0, 3.0, 1 / 30)) == []


def test_find_gaps_detects_a_dropped_frame_run():
    times = np.concatenate([np.arange(0.0, 1.0, 1 / 30), np.arange(1.233, 2.0, 1 / 30)])

    gaps = find_gaps(times)

    assert len(gaps) == 1
    assert 0.95 <= gaps[0][0] <= 1.01
    assert gaps[0][1] - gaps[0][0] > 0.2


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
