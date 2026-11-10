import copy
from pathlib import Path
from unittest.mock import Mock

import pytest

from beatcut.config import Config
from beatcut.project import load_project, save_project
from beatcut.types import BeatGrid

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


def test_timeline_trim_save_undo_snap_and_export(tmp_path, monkeypatch):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fixture")
    rows = [
        {"Keep": True, "Order": 1, "Start (s)": 1.0, "End (s)": 4.0},
        {"Keep": True, "Order": 2, "Start (s)": 10.0, "End (s)": 14.0},
    ]
    project = {
        "video": str(video), "music": str(tmp_path / "song.wav"),
        "duration": 40.0, "music_duration": 80.0,
        "sources": {kind: {"name": name, "sha256": "0" * 64}
                    for kind, name in (("video", "video.mp4"), ("music", "song.wav"))},
        "rows": copy.deepcopy(rows), "history": [],
        "config": Config(music_start_s=25).to_dict(),
    }
    pending = []
    calls = []

    def timeline(**kwargs):
        calls.append(kwargs)
        return pending.pop(0) if pending else None

    monkeypatch.setattr("streamlit.components.v1.declare_component", lambda *a, **k: timeline)
    grid = Mock(return_value=BeatGrid(120, [24.5, 25.2, 25.7, 26.2], []))
    monkeypatch.setattr("beatcut.pipeline.music_beats", grid)
    app = AppTest.from_file(str(
        Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
    )).run()
    app.session_state["edit_project"] = project
    app.session_state["edit_revision"] = 1
    pending.append([{"id": 1, "start": 11.1, "end": 14.4},
                    {"id": 0, "start": 1.2, "end": 3.5}])
    app.run()
    assert not app.exception
    edited = app.session_state["edit_project"]
    restored = load_project(save_project(edited))
    assert restored["rows"][1]["End (s)"] == 14.4
    assert restored["rows"][0]["Order"] == 2
    assert len(edited["history"]) == 1
    next(b for b in app.button if b.label == "Undo edit").click().run()
    assert not app.exception
    assert app.session_state["edit_project"]["rows"] == rows
    app.checkbox[0].check().run()
    assert not app.exception
    assert calls[-1]["beats"] == pytest.approx([0.2, 0.7, 1.2])
    grid.assert_called_once()

    pending.append([{"id": 0, "start": -1, "end": 3},
                    {"id": 1, "start": 10, "end": 14}])
    app.run()
    assert not app.exception
    assert app.error
    assert app.session_state["edit_project"]["rows"] == rows

    pending.append([{"id": 1, "start": 11.1, "end": 14.4},
                    {"id": 0, "start": 1.2, "end": 3.5}])
    app.run()
    exports = []

    def run(video, music, output, cfg, *, segments, progress):
        exports.extend((s.start, s.end) for s in segments)
        output.write_bytes(b"rendered fixture")
        return {"analysis": {"total_duration_s": sum(s.duration for s in segments)}}

    monkeypatch.setattr("beatcut.pipeline.run", run)
    next(b for b in app.button if b.label == "Export edited MP4").click().run()
    assert not app.exception
    assert not app.error
    assert exports == [(11.1, 14.4), (1.2, 3.5)]
    assert app.session_state["last_montage"]["duration"] == pytest.approx(5.6)
