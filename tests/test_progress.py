from pathlib import Path
from unittest.mock import Mock

import pytest

from beatcut.config import Config
from beatcut.pipeline import Analysis, run
from beatcut.types import BeatGrid, Segment, VideoInfo


@pytest.mark.parametrize("fail", [False, True])
def test_progress_counts_only_completed_clips(tmp_path, monkeypatch, fail):
    analysis = Analysis(
        VideoInfo("video.mp4", 40, 1280, 720, 30, True),
        BeatGrid(120, [0, 1], [0]),
        [Segment(0, 6, 1), Segment(10, 16, 1)],
    )
    monkeypatch.setattr("beatcut.pipeline.analyze", lambda *args, **kwargs: analysis)
    cut = Mock(side_effect=[tmp_path / "one.mp4", RuntimeError("cut failed")]
               if fail else [tmp_path / "one.mp4", tmp_path / "two.mp4"])
    monkeypatch.setattr("beatcut.pipeline.cut", cut)
    monkeypatch.setattr("beatcut.pipeline.concat", lambda parts, out: Path(out))
    monkeypatch.setattr("beatcut.pipeline.mux_mixed", lambda *args: None)
    messages = []
    if fail:
        with pytest.raises(RuntimeError, match="cut failed"):
            run("video.mp4", "music.mp3", tmp_path / "out.mp4", progress=messages.append)
        assert messages[-1] == "Rendering highlights: 1/2 completed."
        assert "Montage ready." not in messages
    else:
        run("video.mp4", "music.mp3", tmp_path / "out.mp4", progress=messages.append)
        assert messages[:3] == [
            "Rendering highlights: 0/2 completed.",
            "Rendering highlights: 1/2 completed.",
            "Rendering highlights: 2/2 completed.",
        ]
        assert messages[-1] == "Montage ready."


def test_manual_export_skips_analysis_and_preserves_clip_order(tmp_path, monkeypatch):
    monkeypatch.setattr("beatcut.pipeline.probe", lambda path: VideoInfo(
        str(path), 40, 1280, 720, 30, False,
    ))
    analyze = Mock(side_effect=AssertionError("Manual export must not select highlights again"))
    monkeypatch.setattr("beatcut.pipeline.analyze", analyze)
    cut = Mock(side_effect=lambda video, segment, out, *args, **kwargs: out)
    monkeypatch.setattr("beatcut.pipeline.cut", cut)
    monkeypatch.setattr("beatcut.pipeline.concat", lambda parts, out: out)
    monkeypatch.setattr("beatcut.pipeline.mux_music", lambda *args: None)
    result = run("video", "music", tmp_path / "manual.mp4",
                 segments=[Segment(20, 22), Segment(1, 4)])
    assert [(c.args[1].start, c.args[1].end) for c in cut.call_args_list] == [(20, 22), (1, 4)]
    assert result["analysis"]["total_duration_s"] == 5
    analyze.assert_not_called()


@pytest.mark.parametrize("has_audio,keep_game", [(False, True), (True, False), (True, True)])
def test_export_applies_music_volume_with_or_without_game_audio(
    tmp_path, monkeypatch, has_audio, keep_game,
):
    monkeypatch.setattr("beatcut.pipeline.probe", lambda path: VideoInfo(
        str(path), 40, 1280, 720, 30, has_audio,
    ))
    monkeypatch.setattr("beatcut.pipeline.cut", lambda video, segment, out, *a, **kw: out)
    monkeypatch.setattr("beatcut.pipeline.concat", lambda parts, out: out)
    music_only, mixed = Mock(), Mock()
    monkeypatch.setattr("beatcut.pipeline.mux_music", music_only)
    monkeypatch.setattr("beatcut.pipeline.mux_mixed", mixed)
    cfg = Config(keep_game_audio=keep_game, music_volume=0.25, game_audio_volume=0.15)
    run("video", "music", tmp_path / "mix.mp4", cfg, segments=[Segment(1, 4)])
    if has_audio and keep_game:
        mixed.assert_called_once()
        assert mixed.call_args.args[-2:] == (0.15, 0.25)
        music_only.assert_not_called()
    else:
        music_only.assert_called_once()
        assert music_only.call_args.args[-1] == 0.25
        mixed.assert_not_called()
