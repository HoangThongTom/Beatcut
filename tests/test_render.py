"""Pure render helpers. No ffmpeg runs here — the filter graph is built as a
string first, which is the part that is easy to typo."""

from __future__ import annotations

from beatcut.render import mix_filter, mux_music


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


def test_music_only_export_applies_volume_and_limiter(tmp_path, monkeypatch):
    commands = []
    monkeypatch.setattr("beatcut.render.subprocess.run", lambda cmd, **kw: commands.append(cmd))
    mux_music("video.mp4", "song.wav", tmp_path / "out.mp4", 25, 0.25)
    cmd = commands[0]
    assert cmd[cmd.index("-ss") + 1] == "25.000"
    assert cmd[cmd.index("-af") + 1] == (
        "volume=0.250,alimiter=limit=0.95:level=false,apad"
    )
