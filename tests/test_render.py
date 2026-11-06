"""Pure render helpers. No ffmpeg runs here — the filter graph is built as a
string first, which is the part that is easy to typo."""

from __future__ import annotations

from beatcut.render import mix_filter


def test_mix_filter_reads_both_inputs():
    graph = mix_filter(0.45, 1.0)

    assert "[0:a]" in graph  # game audio comes from the concatenated montage
    assert "[1:a]" in graph  # music comes from the second input
    assert "amix=inputs=2" in graph


def test_mix_filter_does_not_normalise_levels():
    # amix halves both inputs by default, which would make the montage quiet.
    assert "normalize=0" in mix_filter()


def test_mix_filter_uses_the_requested_volumes():
    graph = mix_filter(0.3, 0.9)

    assert "volume=0.300" in graph
    assert "volume=0.900" in graph


def test_mix_filter_limits_peaks():
    # A mastered track already peaks at 0 dBFS; summing on top clips without it.
    assert "alimiter" in mix_filter()
