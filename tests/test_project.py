import json

import pytest

from beatcut.config import Config
from beatcut.project import load_project, save_project


def project():
    return {
        "video": "C:/private/game.mp4", "music": "C:/private/music.mp3",
        "sources": {kind: {"name": f"{kind}.mp4", "sha256": "a" * 64}
                    for kind in ("video", "music")},
        "duration": 40.0,
        "rows": [{"Keep": True, "Order": 2, "Start (s)": 20.0, "End (s)": 25.0},
                 {"Keep": False, "Order": 1, "Start (s)": 1.0, "End (s)": 3.0}],
        "config": Config(music_start_s=25.0).to_dict(),
    }


def test_project_round_trip_excludes_server_paths_and_cache_config():
    original = project()
    raw = save_project(original)
    loaded = load_project(raw)
    assert loaded["rows"] == original["rows"]
    assert loaded["sources"] == original["sources"]
    assert loaded["settings"]["music_start_s"] == 25
    assert b"private" not in raw
    assert b"cache_dir" not in raw


def test_project_saves_title_and_rejects_times_beyond_edited_length():
    original = project()
    original["config"]["title"] = {
        "text": "Hạ gục!", "start": 1, "end": 3, "position": "top",
        "color": "#67E8DF", "size": 4,
    }
    assert load_project(save_project(original))["settings"]["title"] == original["config"]["title"]
    original["config"]["title"]["end"] = 6
    with pytest.raises(ValueError):
        save_project(original)


@pytest.mark.parametrize("change", [
    lambda p: p.update(version=99),
    lambda p: p.update(rows=[]),
    lambda p: p["rows"][0].update({"End (s)": 99}),
    lambda p: p["rows"][1].update({"End (s)": 99}),
    lambda p: p["rows"][0].update({"Keep": "yes"}),
    lambda p: p["settings"].update(music_start_s=-1),
    lambda p: p["settings"].update(music_volume=float("nan")),
    lambda p: p["settings"].update(cache_dir="/tmp/other"),
    lambda p: p["sources"]["music"].update(sha256="not-a-hash"),
])
def test_invalid_project_rejected(change):
    data = json.loads(save_project(project()))
    change(data)
    with pytest.raises(ValueError):
        load_project(json.dumps(data).encode())


@pytest.mark.parametrize("raw", [b"bad json", b"[]", b"null", b"x" * 1_000_001])
def test_invalid_or_oversized_file_rejected(raw):
    with pytest.raises(ValueError):
        load_project(raw)
