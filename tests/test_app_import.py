from dataclasses import fields, make_dataclass
from pathlib import Path

import pytest

from beatcut import config as config_module
from beatcut import editing, pipeline, render

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


@pytest.mark.parametrize("helper", ["reorder_rows", "apply_timeline", "validate_transition"])
def test_app_recovers_a_cached_pre_timeline_module(monkeypatch, helper):
    monkeypatch.delattr(editing, helper)
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")
    ).run(timeout=30)
    assert not app.exception
    assert callable(editing.reorder_rows)
    assert any(button.label == "Render montage" for button in app.button)
    app.run(timeout=30)
    assert not app.exception


def test_export_recovers_pre_transition_config_without_losing_project(tmp_path, monkeypatch):
    from beatcut.project import load_project, save_project

    original_config = config_module.Config
    cfg = original_config(music_start_s=25, transition_s=0.4).to_dict()
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fixture")
    project = {
        "video": str(video), "music": str(tmp_path / "song.wav"),
        "duration": 40, "music_duration": 80,
        "sources": {kind: {"name": name, "sha256": "0" * 64}
                    for kind, name in (("video", "video.mp4"), ("music", "song.wav"))},
        "rows": [{"Keep": True, "Order": 1, "Start (s)": 1.0, "End (s)": 4.0},
                 {"Keep": True, "Order": 2, "Start (s)": 10.0, "End (s)": 13.0}],
        "history": [], "config": cfg,
    }
    legacy = make_dataclass("Config", [(f.name, f.type, f)
                                     for f in fields(original_config) if f.name != "transition_s"])
    monkeypatch.setattr(config_module, "Config", legacy)
    with pytest.raises(TypeError, match="transition_s"):
        config_module.Config(**cfg)
    app = AppTest.from_file(str(
        Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
    ))
    app.session_state["edit_project"] = project
    app.session_state["edit_revision"] = 1
    app.run(timeout=30)
    assert not app.exception
    assert pipeline.Config is config_module.Config
    assert pipeline.cut is render.cut
    assert config_module.Config(**cfg).transition_s == 0.4
    captured = []

    def export(video, music, output, config, **kwargs):
        captured.append(config)
        output.write_bytes(b"rendered fixture")
        return {"analysis": {"total_duration_s": 6}}

    monkeypatch.setattr(pipeline, "run", export)
    next(b for b in app.button if b.label == "Export edited MP4").click().run(timeout=30)
    assert not app.exception
    assert not app.error
    assert captured[0].transition_s == 0.4
    assert app.session_state["edit_project"]["rows"] == project["rows"]
    saved = load_project(save_project(app.session_state["edit_project"]))
    assert saved["settings"]["transition_s"] == 0.4
