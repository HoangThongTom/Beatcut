from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import pytest

from beatcut.types import VideoInfo

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


@pytest.mark.parametrize("local,limit,allowed", [
    (False, None, False), (True, None, True),
    (True, "600", True), (True, "500", False),
])
def test_full_match_is_accepted_locally_and_cloud_limit_remains(monkeypatch, local, limit, allowed):
    class Upload(BytesIO):
        def __init__(self, name):
            super().__init__(b"fixture")
            self.name = name
            self.type = "application/octet-stream"

    uploads = {"Gameplay clip": Upload("game.mp4"), "Music track": Upload("song.wav")}
    monkeypatch.setenv("BEATCUT_LOCAL", "1" if local else "0")
    monkeypatch.delenv("BEATCUT_MAX_DURATION_S", raising=False)
    if limit is not None:
        monkeypatch.setenv("BEATCUT_MAX_DURATION_S", limit)
    monkeypatch.setattr("streamlit.file_uploader", lambda label, **kw: uploads.get(label))
    monkeypatch.setattr("beatcut.media.probe", lambda path: VideoInfo(
        str(path), 590, 1280, 720, 30, True,
    ))
    monkeypatch.setattr("beatcut.media.audio_duration", lambda path: 120)

    def render(video, music, output, cfg, **kwargs):
        output.write_bytes(b"rendered fixture")
        return {"music_start_s": 0, "analysis": {
            "total_duration_s": 6, "segments": [{"start": 120, "end": 126}],
        }}

    run = Mock(side_effect=render)
    monkeypatch.setattr("beatcut.pipeline.run", run)
    app = AppTest.from_file(str(
        Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
    )).run()
    next(b for b in app.button if b.label == "Render montage").click().run()
    assert not app.exception
    if allowed:
        run.assert_called_once()
        assert not app.error
        assert app.session_state["edit_project"]["duration"] == 590
    else:
        run.assert_not_called()
        assert "Video is 590s" in app.error[0].value
