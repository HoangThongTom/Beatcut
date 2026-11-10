from pathlib import Path
from unittest.mock import Mock

import pytest

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
