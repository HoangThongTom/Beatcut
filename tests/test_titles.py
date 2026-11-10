from pathlib import Path
from unittest.mock import Mock

import pytest

from beatcut.config import Config
from beatcut.pipeline import run
from beatcut.render import overlay_title
from beatcut.titles import validate_title
from beatcut.types import Segment, VideoInfo


def title(**changes):
    return {"text": "Pha xử lý đẹp! 100% %{n}: [a] 'x'", "start": 1.0, "end": 3.0,
            "position": "bottom", "color": "#A78BFA", "size": 5.0, **changes}


@pytest.mark.parametrize("changes", [
    {"text": " "}, {"text": "x" * 121}, {"text": "a\x00b"},
    {"start": -1}, {"end": 1.05}, {"end": float("inf")}, {"start": True},
    {"size": float("nan")}, {"size": 20}, {"position": "left"},
    {"color": "red:box=0"}, {"color": None},
])
def test_config_rejects_invalid_titles(changes):
    with pytest.raises(ValueError):
        Config(title=title(**changes))


def test_title_timing_is_relative_to_montage():
    validate_title(title(), 3)
    with pytest.raises(ValueError, match="montage"):
        validate_title(title(), 2)


def test_literal_unicode_text_is_written_separately_from_filter(tmp_path, monkeypatch):
    commands = []

    def execute(cmd, **kwargs):
        commands.append(cmd)
        contents = (Path(kwargs["cwd"]) / "beatcut-title.txt").read_text(encoding="utf-8")
        assert "Pha xử lý đẹp!" in contents
        assert "%{n}" in contents
        graph = cmd[cmd.index("-vf") + 1]
        assert "expansion=none" in graph
        assert "Pha" not in graph
        assert "gte(t,1.0000)*lt(t,3.0000)" in graph
        assert cmd[cmd.index("-c:a") + 1] == "copy"

    monkeypatch.setattr("beatcut.render.subprocess.run", execute)
    overlay_title(tmp_path / "source.mp4", tmp_path / "titled.mp4", title())
    assert len(commands) == 1
    assert not (tmp_path / "beatcut-title.txt").exists()


def test_pipeline_adds_title_before_audio_mix_and_rejects_shortened_montage(tmp_path, monkeypatch):
    monkeypatch.setattr("beatcut.pipeline.probe", lambda path: VideoInfo(
        str(path), 40, 1280, 720, 30, True,
    ))
    cut = Mock(side_effect=lambda video, segment, out, *a, **kw: out)
    monkeypatch.setattr("beatcut.pipeline.cut", cut)
    monkeypatch.setattr("beatcut.pipeline.concat", lambda parts, out: out)
    overlay = Mock(side_effect=lambda video, out, *args: out)
    mixed = Mock()
    monkeypatch.setattr("beatcut.pipeline.overlay_title", overlay)
    monkeypatch.setattr("beatcut.pipeline.mux_mixed", mixed)
    cfg = Config(title=title(), music_start_s=25)
    run("video", "music", tmp_path / "out.mp4", cfg, segments=[Segment(10, 16)])
    overlay.assert_called_once()
    assert mixed.call_args.args[0].name == "montage_titled.mp4"
    cut.reset_mock()
    with pytest.raises(ValueError, match="montage"):
        run("video", "music", tmp_path / "out.mp4", cfg, segments=[Segment(10, 12)])
    cut.assert_not_called()
