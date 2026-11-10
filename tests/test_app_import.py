from pathlib import Path

import pytest

from beatcut import editing

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


def test_app_recovers_a_cached_pre_timeline_module(monkeypatch):
    monkeypatch.delattr(editing, "reorder_rows")
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")
    ).run(timeout=30)
    assert not app.exception
    assert callable(editing.reorder_rows)
    assert any(button.label == "Render montage" for button in app.button)
    app.run(timeout=30)
    assert not app.exception
