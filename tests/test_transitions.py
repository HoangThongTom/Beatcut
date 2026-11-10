from unittest.mock import Mock

import pytest

from beatcut.config import Config
from beatcut.editing import validate_transition
from beatcut.pipeline import run
from beatcut.render import cut
from beatcut.types import Segment, VideoInfo


@pytest.mark.parametrize("seconds", [-1, 1.1, True, "0.4", None, float("inf"), float("nan")])
def test_invalid_transition_rejected(seconds):
    with pytest.raises(ValueError, match="Transition duration"):
        Config(transition_s=seconds)


def test_transition_cannot_cover_an_entire_short_clip():
    clips = [Segment(0, 0.2), Segment(1, 3)]
    with pytest.raises(ValueError, match="shortest"):
        validate_transition(0.4, clips)
    validate_transition(0.2, clips)
    validate_transition(0, clips)
    validate_transition(1, clips[:1])  # A single clip has no join to fade.


def test_default_cut_keeps_existing_hard_cut_command(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("beatcut.render.subprocess.run", lambda cmd, **kw: calls.append(cmd))
    cut("source.mp4", Segment(0, 2), tmp_path / "part.mp4")
    assert "-vf" not in calls[0]
    assert "-af" not in calls[0]


@pytest.mark.parametrize("with_audio", [False, True])
def test_cut_fades_picture_and_only_existing_game_audio(tmp_path, monkeypatch, with_audio):
    calls = []
    monkeypatch.setattr("beatcut.render.subprocess.run", lambda cmd, **kw: calls.append(cmd))
    cut("source.mp4", Segment(10, 13), tmp_path / "part.mp4", with_audio=with_audio,
        fade_in_s=0.2, fade_out_s=0.2)
    cmd = calls[0]
    assert cmd[cmd.index("-t") + 1] == "3.000"
    assert cmd[cmd.index("-vf") + 1] == (
        "fade=t=in:st=0.0000:d=0.2000,fade=t=out:st=2.8000:d=0.2000"
    )
    if with_audio:
        assert cmd[cmd.index("-af") + 1] == (
            "afade=t=in:st=0.0000:d=0.2000,afade=t=out:st=2.8000:d=0.2000"
        )
    else:
        assert "-af" not in cmd
        assert "-an" in cmd


@pytest.mark.parametrize("durations", [[2, 2, 2], [0.2]])
def test_pipeline_fades_only_joins_and_preserves_duration(tmp_path, monkeypatch, durations):
    monkeypatch.setattr("beatcut.pipeline.probe", lambda path: VideoInfo(
        str(path), 40, 1280, 720, 30, True,
    ))
    renderer = Mock(side_effect=lambda video, segment, out, *args, **kw: out)
    monkeypatch.setattr("beatcut.pipeline.cut", renderer)
    monkeypatch.setattr("beatcut.pipeline.concat", lambda parts, out: out)
    mixed = Mock()
    monkeypatch.setattr("beatcut.pipeline.mux_mixed", mixed)
    segments = [Segment(i * 4, i * 4 + duration) for i, duration in enumerate(durations)]
    manifest = run("video", "music", tmp_path / "out.mp4",
                   Config(transition_s=0.4, music_start_s=25), segments=segments)
    assert manifest["analysis"]["total_duration_s"] == sum(durations)
    assert mixed.call_args.args[3] == 25
    expected = [(0, 0.2), (0.2, 0.2), (0.2, 0)] if len(durations) > 1 else [(0, 0)]
    assert [(c.kwargs["fade_in_s"], c.kwargs["fade_out_s"])
            for c in renderer.call_args_list] == expected
    renderer.reset_mock()
    with pytest.raises(ValueError, match="shortest"):
        run("video", "music", tmp_path / "out.mp4", Config(transition_s=0.4),
            segments=[Segment(0, 0.2), Segment(1, 3)])
    renderer.assert_not_called()
