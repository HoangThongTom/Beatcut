from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import pytest

from beatcut.annotations import load_annotations, save_annotations
from beatcut.types import VideoInfo

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


def test_source_only_labeling_add_resume_and_annotator_isolation(tmp_path, monkeypatch):
    video = tmp_path / "match.mp4"
    video.write_bytes(b"fixture")
    monkeypatch.setattr("beatcut.media.probe", lambda path: VideoInfo(
        str(path), 40, 640, 360, 30, True,
    ))
    analyze = Mock(side_effect=AssertionError("Labeling must not show automatic suggestions"))
    monkeypatch.setattr("beatcut.pipeline.analyze", analyze)
    app = AppTest.from_file(str(
        Path(__file__).resolve().parents[1] / "app" / "labeling_app.py"
    )).run()
    source_input = next(t for t in app.text_input if t.label == "Đường dẫn video gốc trên máy")
    source_input.set_value(str(video))
    next(b for b in app.button if b.label == "Mở video gốc").click().run()
    assert not app.exception
    assert app.session_state["labels"]["highlights"] == []
    next(n for n in app.number_input if n.label == "Bắt đầu (s)").set_value(1.0)
    next(n for n in app.number_input if n.label == "Kết thúc (s)").set_value(4.0)
    next(b for b in app.button if b.label == "Thêm highlight").click().run()
    assert not app.exception
    saved = save_annotations(app.session_state["labels"])
    assert str(tmp_path).encode() not in saved
    assert load_annotations(saved)["highlights"] == [{"start": 1, "end": 4}]
    next(b for b in app.button if b.label == "Mở video gốc").click().run()
    assert app.session_state["labels"]["highlights"] == [{"start": 1, "end": 4}]
    next(n for n in app.number_input if n.label == "Bắt đầu (s)").set_value(2.0)
    next(n for n in app.number_input if n.label == "Kết thúc (s)").set_value(5.0)
    next(b for b in app.button if b.label == "Thêm highlight").click().run()
    assert not app.exception
    assert app.error
    assert len(app.session_state["labels"]["highlights"]) == 1

    next(t for t in app.text_input if t.label == "Mã người chấm").set_value("B").run()
    assert not app.exception
    assert not app.number_input  # A's ranges are not displayed for B.
    next(b for b in app.button if b.label == "Mở video gốc").click().run()
    assert not app.exception
    assert app.session_state["labels"]["highlights"] == []
    monkeypatch.setattr("streamlit.file_uploader", lambda *a, **kw: BytesIO(saved))
    next(b for b in app.button if b.label == "Mở nhãn").click().run()
    assert app.error
    assert app.session_state["labels"]["highlights"] == []
    next(t for t in app.text_input if t.label == "Mã người chấm").set_value("A").run()
    next(b for b in app.button if b.label == "Mở video gốc").click().run()
    assert app.session_state["labels"]["highlights"] == [{"start": 1, "end": 4}]
    next(b for b in app.button if b.label == "Mở nhãn").click().run()
    assert not app.exception
    assert not app.error
    assert app.session_state["labels"]["highlights"] == [{"start": 1, "end": 4}]
    analyze.assert_not_called()
